"""Required local growth/length latency gate; synthesis and startup excluded."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tests.core_loader import PLUGIN_PATH, load  # noqa: E402
from tools.benchmark_grammar import measure  # noqa: E402

SCENARIOS = {
	"bodyLocation": "背上长了。",
	"ownedProduct": "我的脸上又长了两个痘痘",
	"length": "这条绳子长三米",
	"mixedResult": "头发长长了",
	"honor": "给我长脸了",
	"stature": "长个子了",
	"distributed": "各自长了",
	"clippedStature": "长个了",
	"classifiedProduct": "长个新的痘痘",
	"classifiedGeneric": "长个奇怪的东西",
	"classifiedLocation": "树上长个奇怪的东西",
	"classifiedQuantity": "长了两个黑色的东西",
	"measurementContrast": "绳子长个三米，长个三米的东西",
	"neutralClassifier": "一个东西，这个东西",
	"neutralLexical": "数落，亲家，朋友，妈妈，桌子",
	"projectedGrower": "菖蒲又长了",
	"resultQuantity": "长胖一点",
	"ageComparison": "他比我长三岁",
	"bare8k": "长" * 8192,
	"locations8k": "背上长了。" * 1638,
	"mixed8k": "头发长长了。" * 1365,
	"roles8k": "给我长脸了，各自长了。" * 744,
	"adversarial8k": ("我的" * 64 + "背上长了。") * 62,
	"ellipsis8k": "长个了。" * 2048,
	"generic8k": "长个东西。" * 1638,
	"age8k": "长我两岁。" * 1638,
	"neutral8k": "数落亲家，朋友的妈妈买了一个桌子。" * 482,
}


def validate(report, *, check_latency=True, minimum_samples=100):
	if set(report["modes"]) != {"default", "extended"}:
		raise ValueError("Missing growth benchmark mode")
	for mode, rows in report["modes"].items():
		if set(rows) != set(SCENARIOS):
			raise ValueError("Missing growth benchmark scenario")
		for name, row in rows.items():
			budget = 30_000 if len(SCENARIOS[name]) > 1000 else 200
			if row["samples"] < minimum_samples or row["codepoints"] != len(SCENARIOS[name]):
				raise ValueError("Invalid growth benchmark sampling")
			if not math.isfinite(row["medianUs"]) or row["medianUs"] <= 0:
				raise ValueError("Invalid growth benchmark timing")
			if check_latency and row["medianUs"] > budget:
				raise ValueError(f"Growth latency exceeded: {mode}/{name}: {row['medianUs']} > {budget} us")


def run(*, process_rounds=1):
	if process_rounds not in (1, 5):
		raise ValueError("Growth sampling requires one local or five hosted rounds")
	report = {
		"scope": "Local reading engine; excludes startup, actual synthesis and audio playback",
		"budgetsUs": {"shortMedian": 200, "page8kMedian": 30_000},
		"modes": {},
		"sourceSha256": {
			p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
			for p in sorted(PLUGIN_PATH.rglob("*"))
			if p.is_file() and p.suffix in {".py", ".json", ".toml"}
		},
		"benchmarkSha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
	}
	for extended in (False, True):
		rules = load("rules").load_default_rules(extended=extended)
		rows = report["modes"]["extended" if extended else "default"] = {}
		for name, text in SCENARIOS.items():
			rows[name] = {
				"codepoints": len(text),
				**measure(
					lambda rules=rules, text=text: rules.transform(text),
					(100 if len(text) > 1000 else 250) // process_rounds,
				),
			}
	validate(report, check_latency=False, minimum_samples=100 // process_rounds)
	try:
		validate(report, minimum_samples=100 // process_rounds)
		report["passed"] = True
	except ValueError as error:
		report.update(passed=False, error=str(error))
	return report


if __name__ == "__main__":
	parser = argparse.ArgumentParser(description=__doc__)
	parser.add_argument(
		"--observe-absolute", action="store_true", help="Record absolute failures for hosted comparison"
	)
	args = parser.parse_args()
	report = run()
	report["absolutePolicy"] = "observation" if args.observe_absolute else "required"
	output = ROOT / "artifacts/growth-performance.json"
	output.parent.mkdir(exist_ok=True)
	output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", "utf-8")
	print(json.dumps({k: v for k, v in report.items() if k != "sourceSha256"}, ensure_ascii=False, indent=2))
	raise SystemExit(0 if report["passed"] or args.observe_absolute else 1)
