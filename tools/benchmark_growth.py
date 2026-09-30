"""Required local growth/length latency gate; synthesis and startup excluded."""

from __future__ import annotations

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
	"projectedGrower": "菖蒲又长了",
	"resultQuantity": "长胖一点",
	"ageComparison": "他比我长三岁",
	"bare8k": "长" * 8192,
	"locations8k": "背上长了。" * 1638,
	"mixed8k": "头发长长了。" * 1365,
	"roles8k": "给我长脸了，各自长了。" * 744,
	"adversarial8k": ("我的" * 64 + "背上长了。") * 62,
	"ellipsis8k": "长个了。" * 2048,
	"age8k": "长我两岁。" * 1638,
}


def validate(report):
	if set(report["modes"]) != {"default", "extended"}:
		raise ValueError("Missing growth benchmark mode")
	for mode, rows in report["modes"].items():
		if set(rows) != set(SCENARIOS):
			raise ValueError("Missing growth benchmark scenario")
		for name, row in rows.items():
			budget = 30_000 if len(SCENARIOS[name]) > 1000 else 200
			if row["samples"] < 100 or row["codepoints"] != len(SCENARIOS[name]):
				raise ValueError("Invalid growth benchmark sampling")
			if not math.isfinite(row["medianUs"]) or not 0 < row["medianUs"] <= budget:
				raise ValueError(f"Growth latency exceeded: {mode}/{name}: {row['medianUs']} > {budget} us")


def run():
	report = {
		"scope": "Local reading engine; excludes startup, actual synthesis and audio playback",
		"budgetsUs": {"shortMedian": 200, "page8kMedian": 30_000},
		"modes": {},
		"sourceSha256": {
			p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
			for p in sorted(PLUGIN_PATH.rglob("*"))
			if p.is_file() and p.suffix in {".py", ".json", ".toml"}
		},
	}
	for extended in (False, True):
		rules = load("rules").load_default_rules(extended=extended)
		rows = report["modes"]["extended" if extended else "default"] = {}
		for name, text in SCENARIOS.items():
			rows[name] = {
				"codepoints": len(text),
				**measure(lambda rules=rules, text=text: rules.transform(text), 100 if len(text) > 1000 else 250),
			}
	try:
		validate(report)
		report["passed"] = True
	except ValueError as error:
		report.update(passed=False, error=str(error))
	return report


if __name__ == "__main__":
	report = run()
	output = ROOT / "artifacts/growth-performance.json"
	output.parent.mkdir(exist_ok=True)
	output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", "utf-8")
	print(json.dumps({k: v for k, v in report.items() if k != "sourceSha256"}, ensure_ascii=False, indent=2))
	raise SystemExit(0 if report["passed"] else 1)
