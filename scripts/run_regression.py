"""One-command local/CI workflow. --release requires native NVDA and licensed VE gates."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

from evidence import sha256, validate_grammar_performance, validate_performance, validate_xml
from prepare_actionlint import EXECUTABLE as ACTIONLINT
from prepare_nvda import NVDA, NVDA_COMMIT, NVDA_VERSION

ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / "artifacts"


def main() -> int:
	parser = argparse.ArgumentParser(description=__doc__)
	parser.add_argument("--native", action="store_true", help="Compile NVDA source and run all its unit tests")
	parser.add_argument("--vocalizer", action="store_true", help="Use locally installed/licensed VE in offline mode")
	parser.add_argument("--release", action="store_true", help="Fail unless every release gate runs successfully")
	parser.add_argument(
		"--hosted-performance", action="store_true", help="Use a same-runner fixed baseline for CI timings"
	)
	parser.add_argument("--llvm-bin", type=Path)
	parser.add_argument("--spectre-atl-fallback", action="store_true")
	parser.add_argument(
		"--installed-worldvoice", type=Path, help="Test installed source without loading live configuration"
	)
	parser.add_argument("--cross-engine-probes", action="store_true", help="Record offline eSpeak/SAPI observations")
	parser.add_argument(
		"--allow-external-screen-effect",
		action="store_true",
		help="Record only upstream's protective screen-curtain skip; never alter the current screen effect",
	)
	parser.add_argument("--jobs", type=int, default=2)
	args = parser.parse_args()
	if args.release and not (args.native and args.vocalizer):
		parser.error("--release requires both --native and --vocalizer")
	if args.release and args.hosted_performance:
		parser.error("Local --release retains absolute performance gates; hosted comparison is a separate CI policy")
	if args.jobs < 1:
		parser.error("--jobs must be positive")
	if args.cross_engine_probes and not args.native:
		parser.error("--cross-engine-probes requires --native")
	ARTIFACTS.mkdir(exist_ok=True)
	logs = ARTIFACTS / "workflow-logs"
	logs.mkdir(exist_ok=True)
	record = {
		"startedAtUtc": datetime.now(UTC).isoformat(),
		"nvdaCommit": NVDA_COMMIT,
		"nvdaVersion": NVDA_VERSION,
		"nativeRequested": args.native,
		"vocalizerRequested": args.vocalizer,
		"releaseRequested": args.release,
		"performancePolicy": "same-runner-baseline" if args.hosted_performance else "absolute",
		"allowExternalScreenEffect": args.allow_external_screen_effect,
		"installedWorldVoiceRequested": args.installed_worldvoice is not None,
		"crossEngineProbesRequested": args.cross_engine_probes,
		"passed": False,
		"stages": [],
	}
	output = ARTIFACTS / "workflow-report.json"

	def save():
		output.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", "utf-8")

	def stage(name: str, command: list[str], *, cwd: Path = ROOT, env: dict | None = None):
		print(f"[{name}] starting; log: {logs / (name + '.log')}", flush=True)
		started = time.monotonic()
		log_path = logs / (name + ".log")
		with log_path.open("w", encoding="utf-8") as stream:
			result = subprocess.run(command, cwd=cwd, env=env, stdout=stream, stderr=subprocess.STDOUT)
		record["stages"].append(
			{
				"name": name,
				"command": command,
				"exitCode": result.returncode,
				"seconds": round(time.monotonic() - started, 3),
				"log": log_path.relative_to(ROOT).as_posix(),
				"logSha256": sha256(log_path),
			}
		)
		save()
		if result.returncode:
			print(log_path.read_text("utf-8", errors="replace")[-8000:], file=sys.stderr)
			raise RuntimeError(f"Stage failed: {name} (exit {result.returncode})")
		print(f"[{name}] passed", flush=True)

	save()
	py = sys.executable
	try:
		stage("prepare-nvda", [py, "scripts/prepare_nvda.py", *(["--submodules"] if args.native else [])])
		if NVDA_VERSION != "2026.2":
			# Acoustic fixture oracles intentionally bind the stable symbol
			# processor even when native integration targets a beta build.
			stage(
				"prepare-fixture-nvda",
				[py, "scripts/prepare_nvda.py"],
				env=dict(os.environ, CONTEXTUAL_PRONUNCIATION_NVDA_VERSION="2026.2"),
			)
		stage("prepare-worldvoice", [py, "scripts/prepare_worldvoice.py"])
		stage("lexicon-reproducibility", [py, "tools/import_cedict.py", "--check"])
		stage("segmentation-reproducibility", [py, "tools/build_segmentation_data.py", "--check"])
		stage("syntax-reproducibility", [py, "tools/build_syntax_data.py", "--check"])
		stage("grammar-reproducibility", [py, "tools/build_grammar_data.py", "--check"])
		stage("polyphone-coverage-reproducibility", [py, "tools/build_polyphone_coverage.py", "--check"])
		stage("dictionary-database-reproducibility", [py, "tools/build_dictionary_database.py", "--check"])
		stage("braille-table-reproducibility", [py, "tools/build_braille_table.py", "--check"])
		stage("contribution-audit", [py, "tools/pronunciation.py", "--check-contributions"])
		stage("prepare-cpp", [py, "scripts/prepare_cpp.py"])
		ruff = ["uv", "tool", "run", "--from", "ruff==0.15.9", "ruff"]
		targets = ["addon", "tests", "tools", "scripts", "buildVars.py"]
		stage("lint", [*ruff, "check", *targets])
		stage("format", [*ruff, "format", "--check", *targets])
		stage("workflow-tool", [py, "scripts/prepare_actionlint.py"])
		stage("workflow-lint", [str(ACTIONLINT), *[str(p) for p in sorted((ROOT / ".github/workflows").glob("*.yml"))]])
		stage("addon-tests", [py, "scripts/run_tests.py"])
		if args.installed_worldvoice:
			stage(
				"installed-worldvoice-tests",
				[py, "scripts/run_installed_worldvoice.py", "--addon", str(args.installed_worldvoice.resolve())],
			)
		stage("cpp-evaluation", [py, "tools/evaluate_cpp.py"])
		stage("grammar-evaluation", [py, "tools/evaluate_grammar.py"])
		if args.native:
			build = [
				"powershell.exe",
				"-NoProfile",
				"-ExecutionPolicy",
				"Bypass",
				"-File",
				str(ROOT / "scripts/build_nvda.ps1"),
				"-NvdaVersion",
				NVDA_VERSION,
				"-Jobs",
				str(args.jobs),
			]
			if args.llvm_bin:
				build.extend(("-LlvmBin", str(args.llvm_bin.resolve())))
			if args.spectre_atl_fallback:
				build.append("-UseSpectreAtlFallback")
			stage("nvda-build", build)
			native_python = str(NVDA / ".venv/Scripts/python.exe")
			native_env = dict(os.environ, UV_FROZEN="true", UV_PYTHON=native_python, UV_LINK_MODE="copy")
			stage("nvda-tests", [native_python, "scripts/run_nvda_unit_tests.py"], env=native_env)
			xml = NVDA / "testOutput/unit/unitTests.xml"
			record["nvdaUnitTests"] = {
				**validate_xml(
					xml, allow_external_screen_effect=args.allow_external_screen_effect, nvda_version=NVDA_VERSION
				),
				"xmlSha256": sha256(xml),
			}
			if record["nvdaUnitTests"]["environmentalSkips"]:
				print(
					"[nvda-tests] 1 upstream protective screen-effect skip recorded; "
					"no display settings changed by the workflow adapter",
					flush=True,
				)
			stage("nvda-integration", [native_python, "scripts/run_nvda_integration.py"])
			if NVDA_VERSION == "2026.3beta2":
				stage("nvda-native-segmentation", [native_python, "scripts/run_nvda_segmentation.py"])
			if args.cross_engine_probes:
				stage("cross-engine-observations", [py, "tools/probe_global_voices.py"])
			dlls = list((NVDA / "source/lib").rglob("*.dll"))
			dlls.extend((NVDA / "source/liblouis.dll", NVDA / "source/synthDrivers/espeak.dll"))
			record["nativeOutputsSha256"] = {p.relative_to(ROOT).as_posix(): sha256(p) for p in dlls}
			save()
		benchmark_args = (
			["--short-iterations", "10000", "--long-iterations", "20", "--rounds", "7"]
			if args.hosted_performance
			else []
		)
		stage(
			"benchmark",
			[py, "tools/benchmark_hot_path.py", *benchmark_args, "--output", "artifacts/performance-report.json"],
			env=dict(os.environ, PYTHONHASHSEED="0") if args.hosted_performance else None,
		)
		stage("startup-benchmark", [py, "tools/benchmark_startup.py"])
		stage(
			"grammar-benchmark",
			[py, "tools/benchmark_grammar.py"],
			env=dict(os.environ, PYTHONHASHSEED="0") if args.hosted_performance else None,
		)
		for name, validator in (
			("performance-report.json", validate_performance),
			("grammar-performance.json", validate_grammar_performance),
		):
			try:
				validator(json.loads((ARTIFACTS / name).read_text("utf-8")))
			except ValueError as error:
				if not args.hosted_performance:
					raise
				record.setdefault("absolutePerformanceObservations", []).append(str(error))
				print(f"[absolute timing observation] {error}", flush=True)
		if args.hosted_performance:
			stage("hosted-performance-comparison", [py, "scripts/compare_hosted_performance.py"])
		if args.vocalizer:
			for name, fixture, directory in (
				("renderer", "final_renderer_regression.json", "final-renderer-ting-ting"),
				("boundaries", "boundary_regression.json", "boundary-ting-ting"),
				("sentences", "sentence_regression.json", "sentence-ting-ting"),
			):
				stage(
					f"ve-{name}",
					[
						py,
						"tools/probe_vocalizer_expressive2.py",
						"render",
						"--voice",
						"Ting-Ting",
						"--fixture",
						f"tests/fixtures/vocalizer_expressive2/{fixture}",
						"--output-dir",
						f"artifacts/{directory}",
						"--report",
						f"artifacts/{directory}/report.json",
					],
				)
			stage("ve-renderer-audit", [py, "tools/summarize_final_renderer.py"])
			stage("ve-boundaries-audit", [py, "tools/boundary_acoustics.py", "summarize"])
			stage("ve-sentences-audit", [py, "tools/sentence_acoustics.py", "summarize"])
		if args.release:
			stage("release", [py, "scripts/verify_release.py"])
		else:
			stage("ci-candidate-addon", [py, "scripts/build_addon.py"])
			stage("ci-candidate-source", [py, "scripts/build_source_archive.py"])
		record["passed"] = True
		return 0
	except Exception as error:
		record["error"] = str(error)
		print(str(error), file=sys.stderr)
		return 1
	finally:
		record["finishedAtUtc"] = datetime.now(UTC).isoformat()
		save()
		print(f"Workflow report: {output}", flush=True)


if __name__ == "__main__":
	raise SystemExit(main())
