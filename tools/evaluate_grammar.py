"""Evaluate explicit grammar oracles and optionally a previous source archive.

This measures reading decisions and intentional preservation, not audible speech
accuracy or open-domain Chinese comprehension. The corpus is project-authored.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import sys
import tempfile
from pathlib import Path
from types import ModuleType
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tests.core_loader import PLUGIN_PATH, load  # noqa: E402
from tests.grammar_cases import CASES  # noqa: E402


def evaluate(module):
	results = {}
	for extended in (False, True):
		rules = module.load_default_rules(extended=extended)
		rows = []
		for text, target, reading in CASES:
			i = text.index(target)
			decision = rules.resolve(text).get(i)
			observed = decision.reading_id if decision is not None and not decision.protect else None
			preserved = rules.transform(text)[i] == target
			rows.append(
				{
					"text": text,
					"offset": i,
					"expected": reading,
					"observed": observed,
					"passed": preserved if reading is None else observed == reading,
					"rule": decision.rule_id if decision else None,
				}
			)
		results["extended" if extended else "default"] = {
			"positiveCases": sum(r["expected"] is not None for r in rows),
			"correctPositiveReadings": sum(r["expected"] is not None and r["passed"] for r in rows),
			"preservationCases": sum(r["expected"] is None for r in rows),
			"correctPreservations": sum(r["expected"] is None and r["passed"] for r in rows),
			"passed": all(r["passed"] for r in rows),
			"cases": rows,
		}
	return results


def baseline(path):
	with tempfile.TemporaryDirectory() as directory, ZipFile(path) as archive:
		base = Path(directory)
		for name in archive.namelist():
			marker = "/addon/globalPlugins/contextualPronunciation/"
			if marker not in name:
				continue
			relative = name.split(marker, 1)[1]
			target = (base / relative).resolve()
			if not target.is_relative_to(base) or target.suffix not in {".py", ".json", ".toml"}:
				continue
			target.parent.mkdir(parents=True, exist_ok=True)
			target.write_bytes(archive.read(name))
		package = ModuleType("_grammarBaseline")
		package.__path__ = [str(base)]
		package.__package__ = package.__name__
		sys.modules[package.__name__] = package
		return evaluate(importlib.import_module(package.__name__ + ".rules"))


if __name__ == "__main__":
	parser = argparse.ArgumentParser(description=__doc__)
	parser.add_argument("--baseline", type=Path)
	parser.add_argument("--output", type=Path, default=ROOT / "artifacts/grammar-evaluation.json")
	args = parser.parse_args()
	report = {
		"scope": "Project-authored targeted regression, not open-domain accuracy",
		"current": evaluate(load("rules")),
	}
	if args.baseline:
		report["baseline"] = baseline(args.baseline)
	report["sourceSha256"] = {
		p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
		for p in [
			*sorted(PLUGIN_PATH.rglob("*.py")),
			*sorted((PLUGIN_PATH / "data").glob("*.json")),
			*sorted((PLUGIN_PATH / "data").glob("*.toml")),
			ROOT / "tests/grammar_cases.py",
			Path(__file__),
		]
	}
	args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", "utf-8")
	print(
		json.dumps(
			{
				k: {m: {key: v for key, v in result.items() if key != "cases"} for m, result in value.items()}
				for k, value in report.items()
				if k in {"current", "baseline"}
			},
			ensure_ascii=False,
			indent=2,
		)
	)
	raise SystemExit(0 if all(v["passed"] for v in report["current"].values()) else 1)
