"""Distribute unchanged benchmark workloads across paired hosted process rounds.

The immutable baseline uses its own benchmark and runtime files. Only sampling
counts are divided: five process rounds retain the original timed-call totals.
Normal benchmark warmups run in every process; no samples or outliers are dropped.
"""

from __future__ import annotations

import argparse
import copy
import ctypes
import hashlib
import importlib.util
import json
import math
import os
import statistics
import sys
from pathlib import Path

PROCESS_ROUNDS = 5


def pin_process() -> dict:
	"""Pin only this benchmark process and inherited children, before measuring."""
	if os.name == "nt":
		from ctypes import wintypes

		kernel = ctypes.WinDLL("kernel32", use_last_error=True)
		kernel.GetCurrentProcess.restype = wintypes.HANDLE
		kernel.GetProcessAffinityMask.argtypes = (
			wintypes.HANDLE,
			ctypes.POINTER(ctypes.c_size_t),
			ctypes.POINTER(ctypes.c_size_t),
		)
		kernel.SetProcessAffinityMask.argtypes = (wintypes.HANDLE, ctypes.c_size_t)
		process = kernel.GetCurrentProcess()
		allowed, system = ctypes.c_size_t(), ctypes.c_size_t()
		if not kernel.GetProcessAffinityMask(process, ctypes.byref(allowed), ctypes.byref(system)):
			raise ctypes.WinError(ctypes.get_last_error())
		mask = allowed.value & -allowed.value
		if not mask or not kernel.SetProcessAffinityMask(process, mask):
			raise ctypes.WinError(ctypes.get_last_error())
		return {"originalAllowedMask": allowed.value, "selectedMask": mask}
	allowed = os.sched_getaffinity(0)
	cpu = min(allowed)
	os.sched_setaffinity(0, {cpu})
	return {"originalAllowedCpus": sorted(allowed), "selectedCpu": cpu}


def sample(checkout: Path, kind: str) -> dict:
	path = checkout / "tools" / f"benchmark_{kind}.py"
	spec = importlib.util.spec_from_file_location("_hosted_benchmark", path)
	assert spec is not None and spec.loader is not None
	module = importlib.util.module_from_spec(spec)
	spec.loader.exec_module(module)
	if kind == "growth":
		report = module.run(process_rounds=PROCESS_ROUNDS)
		report["modes"] = {mode: {"measurements": rows} for mode, rows in report["modes"].items()}
		return report
	if kind == "hot_path":
		return module.run(short_iterations=10_000 // PROCESS_ROUNDS, long_iterations=20 // PROCESS_ROUNDS, rounds=7)
	original_measure = module.measure

	def distributed_measure(call, count):
		if count % PROCESS_ROUNDS:
			raise ValueError("Grammar samples must divide evenly across process rounds")
		return original_measure(call, count // PROCESS_ROUNDS)

	module.measure = distributed_measure
	return module.run()


def aggregate(reports: list[dict], kind: str) -> dict:
	if len(reports) != PROCESS_ROUNDS:
		raise ValueError("Every predetermined process round is required")
	for report in reports[1:]:
		for field in ("sourceSha256", "benchmarkSha256", "measurementEnvironment"):
			if report.get(field) != reports[0].get(field):
				raise ValueError(f"Benchmark source changed during sampling: {field}")
	result = copy.deepcopy(reports[0])
	groups = (None,) if kind == "hot_path" else ("default", "extended")
	metric = "medianMicrosecondsPerCall" if kind == "hot_path" else "medianUs"
	for mode in groups:
		measurements = [r["measurements"] if mode is None else r["modes"][mode]["measurements"] for r in reports]
		target = result["measurements"] if mode is None else result["modes"][mode]["measurements"]
		if any(set(m) != set(measurements[0]) for m in measurements[1:]):
			raise ValueError("Benchmark scenario set changed during sampling")
		for name, row in list(target.items()):
			metadata = {
				key: row[key]
				for key in ("inputCodePoints", "codepoints", "samples", "iterationsPerRound", "rounds")
				if key in row
			}
			if any(any(m[name].get(k) != v for k, v in metadata.items()) for m in measurements):
				raise ValueError(f"Different workload/sampling within process rounds: {name}")
			values = [m[name][metric] for m in measurements]
			if not all(isinstance(v, (int, float)) and math.isfinite(v) and v > 0 for v in values):
				raise ValueError(f"Invalid process timing: {name}")
			# Quantiles are retained in each raw process report; the median of
			# per-process medians must not be labelled as a pooled p95/p99.
			target[name] = {
				**metadata,
				metric: statistics.median(values),
				"processRounds": PROCESS_ROUNDS,
				"processMediansUs": values,
				"totalTimedCalls": PROCESS_ROUNDS
				* row.get("samples", row.get("iterationsPerRound", 0) * row.get("rounds", 1)),
			}
	result["aggregation"] = "Median of all five process medians; no discarded rounds; raw quantiles stored separately"
	if kind == "growth":
		from tools.benchmark_growth import validate

		result.pop("error", None)
		try:
			validate(
				{"modes": {mode: data["measurements"] for mode, data in result["modes"].items()}},
				minimum_samples=100 // PROCESS_ROUNDS,
			)
			result["passed"] = True
		except ValueError as error:
			result.update(passed=False, error=str(error))
	return result


if __name__ == "__main__":
	parser = argparse.ArgumentParser(description=__doc__)
	parser.add_argument("--checkout", type=Path, required=True)
	parser.add_argument("--kind", choices=("hot_path", "grammar", "growth"), required=True)
	parser.add_argument("--output", type=Path, required=True)
	args = parser.parse_args()
	affinity = pin_process()
	report = sample(args.checkout.resolve(), args.kind)
	report["benchmarkSha256"] = hashlib.sha256(
		(args.checkout / "tools" / f"benchmark_{args.kind}.py").read_bytes()
	).hexdigest()
	report["measurementEnvironment"] = {
		"python": sys.version,
		"executable": sys.executable,
		"hashSeed": os.environ.get("PYTHONHASHSEED"),
	}
	report["measurementAffinity"] = affinity
	args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", "utf-8")
