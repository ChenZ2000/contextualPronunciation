"""Run isolated tests, validate evidence hashes, and record package checksums."""

from __future__ import annotations

import hashlib
import json
import sys
import unittest
from datetime import UTC, datetime
from pathlib import Path
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def sha256(path: Path) -> str:
	return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
	from build_addon import build
	from build_source_archive import build as build_source
	from evidence import validate_grammar_performance, validate_hashes, validate_performance, validate_xml
	from prepare_nvda import NVDA, NVDA_COMMIT, NVDA_VERSION, git
	from run_tests import source_hashes

	from tools import boundary_acoustics, sentence_acoustics
	from tools.summarize_final_renderer import FIXTURE, REPORT, summarize

	workflow = json.loads((ROOT / "artifacts/workflow-report.json").read_text("utf-8"))
	required = {
		"prepare-nvda",
		"prepare-worldvoice",
		"lexicon-reproducibility",
		"segmentation-reproducibility",
		"syntax-reproducibility",
		"grammar-reproducibility",
		"grammar-evaluation",
		"grammar-benchmark",
		"polyphone-coverage-reproducibility",
		"dictionary-database-reproducibility",
		"braille-table-reproducibility",
		"contribution-audit",
		"prepare-cpp",
		"cpp-evaluation",
		"lint",
		"format",
		"workflow-lint",
		"workflow-tool",
		"addon-tests",
		"nvda-build",
		"nvda-tests",
		"nvda-integration",
		"benchmark",
		"startup-benchmark",
		"ve-renderer",
		"ve-boundaries",
		"ve-renderer-audit",
		"ve-boundaries-audit",
		"ve-sentences",
		"ve-sentences-audit",
	}
	stages = {stage["name"]: stage for stage in workflow["stages"]}
	if workflow.get("installedWorldVoiceRequested"):
		required.add("installed-worldvoice-tests")
	if workflow.get("crossEngineProbesRequested"):
		required.add("cross-engine-observations")
	if NVDA_VERSION == "2026.3beta2":
		required.add("nvda-native-segmentation")
	if not required.issubset(stages) or workflow["nvdaCommit"] != NVDA_COMMIT:
		raise ValueError("Run the complete native + Vocalizer workflow before release")
	for name in required:
		stage = stages[name]
		if stage["exitCode"] != 0 or sha256(ROOT / stage["log"]) != stage["logSha256"]:
			raise ValueError(f"Failed or stale workflow stage: {name}")
	if git("rev-parse", "HEAD", capture=True) != NVDA_COMMIT:
		raise ValueError("NVDA source pin changed after tests")
	nvda_xml = NVDA / "testOutput/unit/unitTests.xml"
	nvda_tests = validate_xml(
		nvda_xml,
		allow_external_screen_effect=workflow.get("allowExternalScreenEffect", False),
		nvda_version=NVDA_VERSION,
	)
	if sha256(nvda_xml) != workflow["nvdaUnitTests"]["xmlSha256"]:
		raise ValueError("Official NVDA XML was replaced after tests")
	validate_hashes(ROOT, workflow["nativeOutputsSha256"])
	native = json.loads((ROOT / "artifacts/nvda-native-integration.json").read_text("utf-8"))
	if not native["passed"] or native["testsRun"] < 9:
		raise ValueError("Native add-on integration did not pass")
	validate_hashes(ROOT, native["sourceSha256"])
	cpp = json.loads((ROOT / "artifacts/cpp-evaluation.json").read_text("utf-8"))
	validate_hashes(ROOT, cpp["sourceSha256"])
	grammar = json.loads((ROOT / "artifacts/grammar-evaluation.json").read_text("utf-8"))
	if not all(row["passed"] for row in grammar["current"].values()):
		raise ValueError("Grammar regression did not pass")
	validate_hashes(ROOT, grammar["sourceSha256"])
	grammar_perf = json.loads((ROOT / "artifacts/grammar-performance.json").read_text("utf-8"))
	validate_grammar_performance(grammar_perf)
	validate_hashes(ROOT, grammar_perf["sourceSha256"])
	startup = json.loads((ROOT / "artifacts/startup-report.json").read_text("utf-8"))
	validate_hashes(ROOT, startup["sourceSha256"])
	unit_evidence = json.loads((ROOT / "artifacts/addon-tests.json").read_text("utf-8"))
	if not unit_evidence["passed"] or unit_evidence["sourceSha256"] != source_hashes():
		raise ValueError("Add-on source or test workflow changed since the strict test run")
	installed = None
	if workflow.get("installedWorldVoiceRequested"):
		installed = json.loads((ROOT / "artifacts/installed-worldvoice.json").read_text("utf-8"))
		if not installed["passed"] or not installed["upstreamTextMatches"] or installed["testsRun"] < 10:
			raise ValueError("Installed WorldVoice source-chain regression did not pass")
		validate_hashes(ROOT, installed["sourceSha256"])
		installed_root = Path(installed["sourceDirectory"])
		for relative, expected in installed["installedFilesSha256"].items():
			if sha256(installed_root / relative) != expected:
				raise ValueError("Installed WorldVoice source changed after regression")
		if sha256(ROOT / "artifacts/installed-worldvoice-tests.log") != installed["logSha256"]:
			raise ValueError("Installed WorldVoice log changed after regression")
	probes = None
	if workflow.get("crossEngineProbesRequested"):
		probes = json.loads((ROOT / "artifacts/global-voice-probes/report.json").read_text("utf-8"))
		if not probes["completed"] or not probes["observations"]:
			raise ValueError("Cross-engine observation run incomplete")
		validate_hashes(ROOT, probes["sourceSha256"])
	suite = unittest.defaultTestLoader.discover(str(ROOT / "tests"))
	result = unittest.TextTestRunner(verbosity=1).run(suite)
	if not result.wasSuccessful() or result.skipped:
		print("Release verification requires all tests to run without failures or skips", file=sys.stderr)
		return 1
	acoustic = summarize(json.loads(FIXTURE.read_text("utf-8")), json.loads(REPORT.read_text("utf-8")))
	if not acoustic["passed"]:
		raise ValueError("Acoustic anchor regression did not pass")
	boundary = boundary_acoustics.summarize(
		json.loads(boundary_acoustics.FIXTURE.read_text("utf-8")),
		json.loads(boundary_acoustics.REPORT.read_text("utf-8")),
	)
	if not boundary["passed"]:
		raise ValueError("Boundary acoustic regression did not pass")
	sentences = sentence_acoustics.summarize(
		json.loads(sentence_acoustics.FIXTURE.read_text("utf-8")),
		json.loads(sentence_acoustics.REPORT.read_text("utf-8")),
	)
	if not sentences["passed"]:
		raise ValueError("Sentence acoustic regression did not pass")
	performance = json.loads((ROOT / "artifacts/performance-report.json").read_text("utf-8"))
	validate_performance(performance)
	if performance["benchmarkSha256"] != sha256(ROOT / "tools/benchmark_hot_path.py"):
		raise ValueError("Benchmark tool changed after performance measurement")
	for path, expected in performance["sourceSha256"].items():
		if sha256(ROOT / path) != expected:
			raise ValueError(f"Stale performance evidence: {path}")
	addon_path = build()
	addon_first = addon_path.read_bytes()
	build()
	if addon_first != addon_path.read_bytes():
		raise ValueError("Add-on build is not byte-reproducible")
	source_path = build_source()
	source_first = source_path.read_bytes()
	build_source()
	if source_first != source_path.read_bytes():
		raise ValueError("Source build is not byte-reproducible")
	with ZipFile(addon_path) as archive:
		names = archive.namelist()
		if len(names) != len(set(names)):
			raise ValueError("Duplicate add-on archive entries")
		if any(name.endswith((".dll", ".exe", ".wav", ".pyc")) for name in names):
			raise ValueError("Unexpected vendor/generated binaries in add-on archive")
		archive_entries = len(names)
	record = {
		"verifiedAtUtc": datetime.now(UTC).isoformat(),
		"tests": {
			"run": result.testsRun,
			"failures": len(result.failures),
			"errors": len(result.errors),
			"skipped": len(result.skipped),
		},
		"acousticAnchorRegression": acoustic["counts"],
		"boundaryAcousticRegression": {
			key: boundary[key] for key in ("groups", "cases", "phonemeMatches", "pcmMatches")
		},
		"sentenceAcousticRegression": {
			key: sentences[key] for key in ("groups", "cases", "phonemeMatches", "pcmMatches")
		},
		"unicodeBoundaryRegression": {
			"unicodeVersion": unit_evidence["unicodeVersion"],
			"codepointsExhausted": unit_evidence["boundaryCodepointsExhausted"],
			"acceptedBoundariesByCategory": unit_evidence["acceptedBoundariesByCategory"],
		},
		"nvdaCommit": NVDA_COMMIT,
		"nativeNVDATests": nvda_tests,
		"nativeAddonIntegrationTests": native["testsRun"],
		"installedWorldVoiceSourceTests": None
		if installed is None
		else {
			"version": installed["version"],
			"testsRun": installed["testsRun"],
			"passed": installed["passed"],
			"scope": installed["scope"],
		},
		"crossEngineObservations": None
		if probes is None
		else {
			"scope": probes["scope"],
			"voices": [
				{key: voice[key] for key in ("engine", "voice", "comparisons", "anchorMatches")}
				for voice in probes["observations"]
			],
		},
		"cppEvaluation": {
			key: cpp[key]
			for key in (
				"samples",
				"counts",
				"decisionCoveragePercent",
				"labelAgreementOnDecisionsPercent",
				"speechSubstitutionCounts",
			)
		},
		"nativeOutputHashesMatch": True,
		"performanceGuardrailsPassed": True,
		"grammarRegression": {
			mode: {key: value for key, value in row.items() if key != "cases"}
			for mode, row in grammar["current"].items()
		},
		"grammarPerformanceGuardrailsPassed": True,
		"coldCompileMedianMilliseconds": startup["coldCompileMedianMilliseconds"],
		"pythonDefaultPeakMiB": startup["tracedMemory"]["pythonPeakMiB"],
		"extendedLexiconStartup": startup["extendedLexicon"],
		"performanceSourceHashesMatch": True,
		"byteReproducibleBuilds": True,
		"addonArchiveEntries": archive_entries,
		"packages": [
			{"path": str(path.relative_to(ROOT)), "bytes": path.stat().st_size, "sha256": sha256(path)}
			for path in (addon_path, source_path)
		],
		"notPerformed": [
			"Live WorldVoice audio/GUI acceptance (installed-source regression uses substitute voices)",
			"Physical braille display acceptance or full GF 0019-2018 compliance certification",
			"Installing into running NVDA",
			"Human listening",
			"Word/Notepad UI acceptance",
			"All voices certification",
			"End-to-end p99 latency",
		],
	}
	(ROOT / "artifacts/release-verification.json").write_text(
		json.dumps(record, ensure_ascii=False, indent=2) + "\n", "utf-8"
	)
	print(json.dumps(record, ensure_ascii=False, indent=2))
	return 0


if __name__ == "__main__":
	raise SystemExit(main())
