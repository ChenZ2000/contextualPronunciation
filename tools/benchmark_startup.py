"""Measure cold compilation in fresh processes; trace Python allocations separately."""

from __future__ import annotations

import json
import statistics
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def worker(trace: bool = False, extended: bool = False):
	if trace:
		import tracemalloc

		tracemalloc.start()
	start = time.perf_counter()
	from tests.core_loader import load

	rules = load("rules").load_default_rules(extended=extended)
	result = {
		"compileMilliseconds": (time.perf_counter() - start) * 1000,
		"speechTriggerCharacters": len(rules.triggers),
	}
	if trace:
		current, peak = tracemalloc.get_traced_memory()
		result.update(pythonLiveMiB=current / 1048576, pythonPeakMiB=peak / 1048576)
	print(json.dumps(result))


if __name__ == "__main__":
	if "--worker" in sys.argv:
		worker("--trace" in sys.argv, "--extended" in sys.argv)
	else:
		from scripts.run_tests import source_hashes

		samples = [
			json.loads(subprocess.check_output([sys.executable, __file__, "--worker"], text=True)) for _ in range(5)
		]
		memory = json.loads(subprocess.check_output([sys.executable, __file__, "--worker", "--trace"], text=True))
		extended_samples = [
			json.loads(subprocess.check_output([sys.executable, __file__, "--worker", "--extended"], text=True))
			for _ in range(5)
		]
		extended_memory = json.loads(
			subprocess.check_output([sys.executable, __file__, "--worker", "--trace", "--extended"], text=True)
		)
		report = {
			"coldCompileMedianMilliseconds": statistics.median(item["compileMilliseconds"] for item in samples),
			"samples": samples,
			"tracedMemory": memory,
			"extendedLexicon": {
				"samples": extended_samples,
				"tracedMemory": extended_memory,
				"coldCompileMedianMilliseconds": statistics.median(
					item["compileMilliseconds"] for item in extended_samples
				),
			},
			"sourceSha256": source_hashes(),
			"method": "Fresh Python processes, OS file cache may be warm. Tracing timing is NOT runtime latency; "
			"Python allocation memory excludes NVDA/voices/native memory. No synth is started.",
		}
		(ROOT / "artifacts/startup-report.json").write_text(json.dumps(report, indent=2) + "\n", "utf-8")
		print(json.dumps({key: value for key, value in report.items() if key != "sourceSha256"}, indent=2))
