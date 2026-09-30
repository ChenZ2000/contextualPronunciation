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
sys.path.insert(0, str(ROOT))

from scripts.sample_hosted_performance import PROCESS_ROUNDS, aggregate, pin_process  # noqa: E402
from tools.benchmark_growth import SCENARIOS as GROWTH_SCENARIOS  # noqa: E402
from tools.benchmark_growth import validate as validate_growth  # noqa: E402

BASELINE = "82bdb20ae72a849f9cefac6073a1111d82bc52fc"
BASE = ROOT / "vendor/performance-baseline"
RATIO = 1.30
NOISE_FLOOR_US = 5.0
NEW_FEATURE_MULTIPLIER = 2
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
		for field in (
			"inputCodePoints",
			"codepoints",
			"samples",
			"iterationsPerRound",
			"rounds",
			"processRounds",
			"totalTimedCalls",
		):
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
		limit = max(reference * NEW_FEATURE_MULTIPLIER, reference + NOISE_FLOOR_US)
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


def compare_growth(current: dict, baseline: dict) -> list[dict]:
	"""New growth/neutral paths use the existing same-size feature envelope.

	The immutable baseline predates these senses and has no growth benchmark.
	Its own grammar benchmark supplies a measured short/page cost envelope,
	separately sampled adjacent to current growth on the same processor.
	This is a capability budget, not an identical-workload regression ratio.
	"""
	if set(current["modes"]) != {"default", "extended"} or set(baseline["modes"]) != {"default", "extended"}:
		raise ValueError("Missing growth/reference benchmark mode")
	validate_growth(
		{"modes": {mode: data["measurements"] for mode, data in current["modes"].items()}},
		check_latency=False,
		minimum_samples=100 // PROCESS_ROUNDS,
	)
	rows = []
	for mode in ("default", "extended"):
		references = baseline["modes"][mode]["measurements"]
		for reference in references.values():
			expected_calls = 100 if reference["codepoints"] > 1000 else 1000
			if (
				not math.isfinite(reference["medianUs"])
				or reference["medianUs"] <= 0
				or reference["codepoints"] <= 0
				or reference["processRounds"] != PROCESS_ROUNDS
				or reference["samples"] * PROCESS_ROUNDS != expected_calls
				or reference["totalTimedCalls"] != expected_calls
			):
				raise ValueError("Invalid growth reference timing/sampling")
		for name, text in GROWTH_SCENARIOS.items():
			row = current["modes"][mode]["measurements"][name]
			long = len(text) > 1000
			expected_calls = 100 if long else 250
			if (
				row["processRounds"] != PROCESS_ROUNDS
				or row["samples"] * PROCESS_ROUNDS != expected_calls
				or row["totalTimedCalls"] != expected_calls
			):
				raise ValueError("Different growth benchmark sampling")
			candidates = [key for key, value in references.items() if (value["codepoints"] > 1000) == long]
			if not candidates:
				raise ValueError(f"Missing comparable size envelope: growth/{mode}/{name}")
			reference_name = max(candidates, key=lambda key: references[key]["medianUs"])
			value, reference = row["medianUs"], references[reference_name]["medianUs"]
			limit = max(reference * NEW_FEATURE_MULTIPLIER, reference + NOISE_FLOOR_US)
			rows.append(
				{
					"scenario": f"growth/{mode}/{name}",
					"comparisonType": "new-feature-envelope",
					"referenceScenario": f"grammar/{mode}/{reference_name}",
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
	affinity = pin_process()
	samples = artifacts / "hosted-performance-samples"
	samples.mkdir(exist_ok=True)
	collected = {(kind, label): [] for kind in ("hot_path", "grammar", "growth") for label in ("current", "baseline")}
	order = []
	environment = None
	with (artifacts / "hosted-baseline-benchmark.log").open("w", encoding="utf-8") as log:
		for round_index in range(PROCESS_ROUNDS):
			for kind_index, kind in enumerate(("hot_path", "grammar", "growth")):
				labels = ("current", "baseline") if (round_index + kind_index) % 2 == 0 else ("baseline", "current")
				for label in labels:
					checkout = ROOT if label == "current" else BASE
					sample_kind = "grammar" if kind == "growth" and label == "baseline" else kind
					output = samples / f"{round_index + 1}-{kind}-{label}.json"
					print(f"Paired sampling {round_index + 1}/{PROCESS_ROUNDS}: {kind}/{label}", flush=True)
					subprocess.run(
						[
							sys.executable,
							str(ROOT / "scripts/sample_hosted_performance.py"),
							"--checkout",
							str(checkout),
							"--kind",
							sample_kind,
							"--output",
							str(output),
						],
						cwd=checkout,
						env=dict(os.environ, PYTHONHASHSEED="0"),
						check=True,
						stdout=log,
						stderr=subprocess.STDOUT,
					)
					sample = json.loads(output.read_text("utf-8"))
					if environment is None:
						environment = sample["measurementEnvironment"]
					if sample["measurementEnvironment"] != environment:
						raise ValueError("Benchmark child used a different interpreter/configuration")
					for key in ("selectedMask", "selectedCpu"):
						if sample["measurementAffinity"].get(key) != affinity.get(key):
							raise ValueError("Benchmark child used a different processor")
					collected[kind, label].append(sample)
					order.append(output.relative_to(ROOT).as_posix())
	current_hot = aggregate(collected["hot_path", "current"], "hot_path")
	baseline_hot = aggregate(collected["hot_path", "baseline"], "hot_path")
	current_grammar = aggregate(collected["grammar", "current"], "grammar")
	baseline_grammar = aggregate(collected["grammar", "baseline"], "grammar")
	current_growth = aggregate(collected["growth", "current"], "growth")
	baseline_growth_reference = aggregate(collected["growth", "baseline"], "grammar")
	for path, data in (
		(artifacts / "paired-current-performance.json", current_hot),
		(artifacts / "paired-current-grammar-performance.json", current_grammar),
		(base_hot, baseline_hot),
		(base_grammar, baseline_grammar),
		(artifacts / "paired-current-growth-performance.json", current_growth),
		(artifacts / "baseline-growth-reference.json", baseline_growth_reference),
	):
		path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", "utf-8")
	rows, aliases = compare_hot_path(current_hot["measurements"], baseline_hot["measurements"])
	for mode in ("default", "extended"):
		for row in compare(
			current_grammar["modes"][mode]["measurements"], baseline_grammar["modes"][mode]["measurements"], "medianUs"
		):
			rows.append({**row, "scenario": mode + "/" + row["scenario"]})
	rows.extend(compare_growth(current_growth, baseline_growth_reference))
	report = {
		"baselineCommit": BASELINE,
		"ratioLimit": RATIO,
		"noiseFloorUs": NOISE_FLOOR_US,
		"baselineModeAliases": aliases,
		"newMotionEnvelopeMultiplier": NEW_FEATURE_MULTIPLIER,
		"newGrowthEnvelopeMultiplier": NEW_FEATURE_MULTIPLIER,
		"growthReference": "Immutable baseline's own grammar workloads, paired by size and mode; not identical senses",
		"growthAbsoluteObservation": {"passed": current_growth["passed"], "error": current_growth.get("error")},
		"scope": (
			"Same-core alternating five-process median comparison; original timed-call totals and thresholds retained"
		),
		"affinity": affinity,
		"measurementEnvironment": environment,
		"processRounds": PROCESS_ROUNDS,
		"sampleOrder": order,
		"passed": all(row["passed"] for row in rows),
		"comparisons": rows,
	}
	(artifacts / "hosted-performance-comparison.json").write_text(json.dumps(report, indent=2) + "\n", "utf-8")
	if not report["passed"]:
		raise ValueError("Hosted performance regression: " + str([r for r in rows if not r["passed"]]))
	print(f"Same-runner performance comparison passed: {len(rows)} scenarios against {BASELINE}")


if __name__ == "__main__":
	main()
