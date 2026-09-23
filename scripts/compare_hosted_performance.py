"""Compare current and immutable baseline timings on the same hosted runner.

Absolute workstation gates remain in evidence.py and the local --release path.
This comparison detects relative regressions; it is not a latency guarantee.
"""

from __future__ import annotations

import json
import math
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASELINE = "82bdb20ae72a849f9cefac6073a1111d82bc52fc"
BASE = ROOT / "vendor/performance-baseline"
RATIO = 1.30
NOISE_FLOOR_US = 5.0


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
				"1000",
				"--long-iterations",
				"20",
				"--rounds",
				"5",
				"--output",
				str(base_hot),
			],
			[sys.executable, "tools/benchmark_grammar.py", "--output", str(base_grammar)],
		):
			subprocess.run(command, cwd=BASE, check=True, stdout=log, stderr=subprocess.STDOUT)

	def read(path):
		return json.loads(path.read_text("utf-8"))

	current_hot, baseline_hot = read(artifacts / "performance-report.json"), read(base_hot)
	current_grammar, baseline_grammar = read(artifacts / "grammar-performance.json"), read(base_grammar)
	rows = compare(current_hot["measurements"], baseline_hot["measurements"], "medianMicrosecondsPerCall")
	for mode in ("default", "extended"):
		for row in compare(
			current_grammar["modes"][mode]["measurements"], baseline_grammar["modes"][mode]["measurements"], "medianUs"
		):
			rows.append({**row, "scenario": mode + "/" + row["scenario"]})
	report = {
		"baselineCommit": BASELINE,
		"ratioLimit": RATIO,
		"noiseFloorUs": NOISE_FLOOR_US,
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
