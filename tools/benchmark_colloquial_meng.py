"""Fail-closed latency budgets for the contextual 懵 policy in both engine modes.

Median per-call wall time, not audio latency. Budgets match existing hot-path
short/8K guardrails (200 us / 30 ms); no old scenario or limit is relaxed.
"""

from __future__ import annotations

import hashlib
import json
import math
import platform
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tests.core_loader import PLUGIN_PATH, load  # noqa: E402

SCENARIOS = {
	"bare": "懵",
	"facial": "一脸懵逼，一脸懵",
	"resultative": "新来的老师把坐在后排的所有同学问懵了",
	"complement": "懵得说不出话，看完要求大家都懵到忘了回复",
	"mixed": "懵，懵懂，懵的读音，我懵了，别懵",
	"reiterated": "越想越懵，懵归懵，你懵不懵",
	"bare8k": "懵" * 8192,
	"mixed8k": ("一脸懵，懵懂，懵。" * 1000)[:8192],
	"predicates8k": ("越想越懵，懵不懵，懵懵的，" * 1000)[:8192],
	"mentions8k": ("请问懵的读音，看懵懂的人，" * 1000)[:8192],
	"boundedNoise8k": ("越" + "甲" * 60 + "越懵，懵" + "乙" * 60 + "了，") * 62,
}


def validate(report: dict) -> None:
	for mode in ("default", "extended"):
		rows = report["modes"][mode]
		if set(rows) != set(SCENARIOS):
			raise ValueError("Incomplete colloquial-meng performance report")
		for name, text in SCENARIOS.items():
			row = rows[name]
			budget = 30_000 if len(text) > 1000 else 200
			value = row["medianUs"]
			if (
				row["samples"] < 100
				or row["codepoints"] != len(text)
				or not math.isfinite(value)
				or not 0 < value <= budget
			):
				raise ValueError(f"Colloquial-meng latency budget exceeded: {mode}/{name}: {row}; budget {budget} us")


def run() -> dict:
	from tests.test_pipeline import CharacterModeCommand

	pipeline = load("pipeline")
	report = {
		"scope": "Speech sequence normalizer, per-call wall time; excludes NVDA dispatch, startup and audio",
		"python": platform.python_version(),
		"platform": platform.platform(),
		"budgetsUs": {"shortMedian": 200, "page8kMedian": 30_000},
		"modes": {},
		"sourceSha256": {
			p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
			for p in sorted(PLUGIN_PATH.glob("*.py"))
		},
	}
	for extended in (False, True):
		rules = load("rules").load_default_rules(extended=extended)
		normalizer = pipeline.SpeechSequenceNormalizer(rules=rules, character_mode_command_type=CharacterModeCommand)
		options = pipeline.RuntimeOptions()
		rows = report["modes"]["extended" if extended else "default"] = {}
		for name, text in SCENARIOS.items():
			sequence = [text]
			for _ in range(10):
				normalizer.normalize(sequence, options=options)
			samples = []
			for _ in range(100 if len(text) > 1000 else 250):
				start = time.perf_counter_ns()
				normalizer.normalize(sequence, options=options)
				samples.append((time.perf_counter_ns() - start) / 1000)
			samples.sort()
			rows[name] = {
				"codepoints": len(text),
				"samples": len(samples),
				"medianUs": round(statistics.median(samples), 3),
				"p95Us": round(samples[int(len(samples) * 0.95)], 3),
				"maxUs": round(samples[-1], 3),
			}
	return report


if __name__ == "__main__":
	report = run()
	try:
		validate(report)
		report["passed"] = True
	except ValueError as error:
		report["passed"] = False
		report["error"] = str(error)
	output = ROOT / "artifacts/colloquial-meng-performance.json"
	output.parent.mkdir(exist_ok=True)
	output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", "utf-8")
	print(json.dumps(report, ensure_ascii=False, indent=2))
	raise SystemExit(0 if report["passed"] else 1)
