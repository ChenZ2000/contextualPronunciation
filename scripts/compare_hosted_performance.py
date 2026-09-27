"""Compare current and immutable baseline timings on the same hosted runner.

Absolute workstation gates remain in evidence.py and the local --release path.
This comparison detects relative regressions; it is not a latency guarantee.
"""

from __future__ import annotations

import json
import math
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASELINE = "82bdb20ae72a849f9cefac6073a1111d82bc52fc"
BASE = ROOT / "vendor/performance-baseline"
RATIO = 1.30
NOISE_FLOOR_US = 5.0
MOTION_ADDITIONS = frozenset(
	f"{prefix}shortMotion{kind}"
	for prefix in ("", "pluginFilterWithStubs_")
	for kind in (
		"Location",
		"Serial",
		"Object",
		"Distractor",
		"Phase",
		"Recipient",
		"Ellipsis",
		"Purpose",
		"Reiteration",
	)
) | {"longMotionCandidates8k", "longMotionSentences8k", "longMotionRoles8k", "longMotionReiterations8k"}


def compare(current: dict, baseline: dict, metric: str) -> list[dict]:
	if not current or set(current) != set(baseline):
		raise ValueError("Performance scenario sets must be nonempty and identical")
	rows = []
	for name, row in current.items():
		value, reference = row[metric], baseline[name][metric]
		if not all(isinstance(v, (int, float)) and math.isfinite(v) and v > 0 for v in (value, reference)):
			raise ValueError(f"Invalid timing: {name}")
		for field in ("inputCodePoints", "codepoints", "samples", "iterationsPerRound", "rounds"):
			if row.get(field) != baseline[name].get(field):
				raise ValueError(f"Different benchmark inputs/sampling: {name}/{field}")
		limit = max(reference * RATIO, reference + NOISE_FLOOR_US)
		rows.append(
			{
				"scenario": name,
				"currentUs": value,
				"baselineUs": reference,
				"ratio": value / reference,
				"limitUs": limit,
				"passed": value <= limit,
			}
		)
	return rows


def compare_hot_path(current: dict, baseline: dict) -> tuple[list[dict], dict]:
	"""Keep comparable workloads strict and explicitly budget new capabilities.

	The retired false-config cases now load the dictionary, so compare them
	to the baseline's identical dictionary-enabled plugin scenario. The new
	motion capability has no older semantic equivalent: on hosted hardware
	it gets at most twice the cost of the baseline's slowest existing short
	plugin or long-page scenario. Local absolute gates remain unchanged.
	"""
	aligned = dict(baseline)
	aliases = {}
	for name in baseline:
		if name.startswith("defaultPlugin_"):
			reference = name.replace("defaultPlugin_", "pluginFilterWithStubs_", 1)
			if reference not in baseline:
				raise ValueError(f"Missing dictionary-enabled baseline: {name}")
			aligned[name] = baseline[reference]
			aliases[name] = reference
	if set(current) - set(aligned) != MOTION_ADDITIONS or set(aligned) - set(current):
		raise ValueError("Unexpected changed hot-path scenario schema")
	metric = "medianMicrosecondsPerCall"
	rows = compare({k: v for k, v in current.items() if k not in MOTION_ADDITIONS}, aligned, metric)
	for name in sorted(MOTION_ADDITIONS):
		prefix = "long" if name.startswith("long") else "pluginFilterWithStubs_short"
		candidates = [k for k in baseline if k.startswith(prefix)]
		if not candidates:
			raise ValueError(f"Missing comparable size envelope: {name}")
		reference_name = max(candidates, key=lambda k: baseline[k][metric])
		value, reference = current[name][metric], baseline[reference_name][metric]
		if not all(isinstance(v, (int, float)) and math.isfinite(v) and v > 0 for v in (value, reference)):
			raise ValueError(f"Invalid new-feature timing: {name}")
		limit = max(reference * 2, reference + NOISE_FLOOR_US)
		rows.append(
			{
				"scenario": name,
				"comparisonType": "new-feature-envelope",
				"referenceScenario": reference_name,
				"currentUs": value,
				"baselineUs": reference,
				"ratio": value / reference,
				"limitUs": limit,
				"passed": value <= limit,
			}
		)
	return rows, aliases


def main() -> None:
	def git(*args, cwd=ROOT, check=True):
		return subprocess.run(["git", "-C", str(cwd), *args], check=check, capture_output=True, text=True)

	if git("cat-file", "-e", f"{BASELINE}^{{commit}}", check=False).returncode:
		git("fetch", "--depth=1", "origin", BASELINE)
	if not BASE.exists():
		git("worktree", "add", "--detach", str(BASE), BASELINE)
	if git("rev-parse", "HEAD", cwd=BASE).stdout.strip() != BASELINE:
		raise ValueError("Preserving an unexpected performance baseline checkout")
	if git("status", "--porcelain", "--untracked-files=no", cwd=BASE).stdout.strip():
		raise ValueError("Preserving modified baseline source")
	artifacts = ROOT / "artifacts"
	base_hot = artifacts / "baseline-performance.json"
	base_grammar = artifacts / "baseline-grammar-performance.json"
	with (artifacts / "hosted-baseline-benchmark.log").open("w", encoding="utf-8") as log:
		for command in (
			[
				sys.executable,
				"tools/benchmark_hot_path.py",
				"--short-iterations",
				"10000",
				"--long-iterations",
				"20",
				"--rounds",
				"7",
				"--output",
				str(base_hot),
			],
			[sys.executable, "tools/benchmark_grammar.py", "--output", str(base_grammar)],
		):
			subprocess.run(
				command,
				cwd=BASE,
				env=dict(os.environ, PYTHONHASHSEED="0"),
				check=True,
				stdout=log,
				stderr=subprocess.STDOUT,
			)

	def read(path):
		return json.loads(path.read_text("utf-8"))

	current_hot, baseline_hot = read(artifacts / "performance-report.json"), read(base_hot)
	current_grammar, baseline_grammar = read(artifacts / "grammar-performance.json"), read(base_grammar)
	rows, aliases = compare_hot_path(current_hot["measurements"], baseline_hot["measurements"])
	for mode in ("default", "extended"):
		for row in compare(
			current_grammar["modes"][mode]["measurements"], baseline_grammar["modes"][mode]["measurements"], "medianUs"
		):
			rows.append({**row, "scenario": mode + "/" + row["scenario"]})
	report = {
		"baselineCommit": BASELINE,
		"ratioLimit": RATIO,
		"noiseFloorUs": NOISE_FLOOR_US,
		"baselineModeAliases": aliases,
		"newMotionEnvelopeMultiplier": 2,
		"scope": "Same-runner relative regression gate; raw absolute timings are retained separately",
		"passed": all(row["passed"] for row in rows),
		"comparisons": rows,
	}
	(artifacts / "hosted-performance-comparison.json").write_text(json.dumps(report, indent=2) + "\n", "utf-8")
	if not report["passed"]:
		raise ValueError("Hosted performance regression: " + str([r for r in rows if not r["passed"]]))
	print(f"Same-runner performance comparison passed: {len(rows)} scenarios against {BASELINE}")


if __name__ == "__main__":
	main()
