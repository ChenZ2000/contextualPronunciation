"""Evaluate independent constructed policy cases; no corpus/audio accuracy claim."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tests.core_loader import PLUGIN_PATH, load  # noqa: E402
from tests.meng_cases import (  # noqa: E402
	MIXED,
	NEGATIVE,
	POSITIVE,
	generated_mentions,
	generated_negatives,
	generated_positives,
)


def run() -> dict:
	cases: dict[str, str] = {}
	for text, expected in (
		*[(s, s.replace("懵", "擝")) for group in POSITIVE.values() for s in group],
		*[(s, s.replace("懵", "擝")) for s in generated_positives()],
		*[(s, s) for group in NEGATIVE.values() for s in group],
		*[(s, s) for s in generated_negatives()],
		*[(s, s) for s in generated_mentions()],
		*MIXED,
	):
		if text in cases and cases[text] != expected:
			raise ValueError(f"Conflicting expectations: {text}")
		cases[text] = expected
	report = {
		"scope": "Constructed policy regression, not naturally sampled corpus accuracy or acoustic verification",
		"uniqueTexts": len(cases),
		"positiveTexts": sum(source != expected for source, expected in cases.items()),
		"preservedTexts": sum(source == expected for source, expected in cases.items()),
		"families": {name: len(values) for name, values in POSITIVE.items()},
		"matrix": [],
		"sourceSha256": {
			p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
			for p in (PLUGIN_PATH / "colloquial_meng.py", PLUGIN_PATH / "rules.py", ROOT / "tests/meng_cases.py")
		},
	}
	for extended in (False, True):
		rules = load("rules").load_default_rules(extended=extended)
		for strict in (False, True):
			failures = []
			for source, expected in cases.items():
				actual = rules.transform(source, strict=strict, targets=frozenset("懵"))
				if actual != expected:
					failures.append({"source": source, "expected": expected, "actual": actual})
			report["matrix"].append(
				{"extended": extended, "strict": strict, "tested": len(cases), "failures": failures}
			)
	report["passed"] = all(not row["failures"] for row in report["matrix"])
	return report


if __name__ == "__main__":
	report = run()
	output = ROOT / "artifacts/colloquial-meng-evaluation.json"
	output.parent.mkdir(exist_ok=True)
	output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", "utf-8")
	print(json.dumps(report, ensure_ascii=False, indent=2))
	raise SystemExit(0 if report["passed"] else 1)
