"""Inventory EVERY multi-reading character in the pinned Unihan fields.

This is an offline coverage ledger, not a pronunciation model or an assertion
that historic/regional/surname readings are mandatory in contemporary prose.
No data from the unverified cc-table reference is included.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tests.core_loader import PLUGIN_PATH, load  # noqa: E402
from tools.import_cedict import PINS, UNIHAN, read_unihan  # noqa: E402

OUTPUT = ROOT / "data/polyphone-coverage.json"


def generate() -> bytes:
	if hashlib.sha256(gzip.decompress(UNIHAN.read_bytes())).hexdigest() != PINS["unihan"]:
		raise ValueError("Unreviewed Unihan source snapshot")
	with gzip.open(UNIHAN, "rt", encoding="utf-8") as stream:
		defaults, attested, common = read_unihan(stream)
	polyphones = {ch: values for ch, values in attested.items() if len(values) > 1}
	data = json.loads((PLUGIN_PATH / "data/lexicon_zh_CN.json").read_text("utf-8"))
	rules = load("rules").load_default_rules(extended=False)
	# Keep small deterministic samples plus full counts, not a second word DB.
	evidence = defaultdict(lambda: {"headwords": 0, "examples": []})
	for word, value in sorted(data["words"].items()):
		if not value:
			continue
		for ch, reading in set(zip(word, value.split(), strict=True)):
			if ch in polyphones and reading != "?":
				item = evidence[ch, reading]
				item["headwords"] += 1
				if len(item["examples"]) < 5:
					item["examples"].append(word)
	curated = defaultdict(set)
	for bucket in rules._buckets.values():
		for rule in bucket:
			if not rule.protect:
				curated[rule.target, rule.reading_id].add(rule.id)
	for target, names in rules._structural_rules.items():
		for name in names:
			reading = load("rules")._STRUCTURAL_REQUIREMENTS[name][1]
			curated[target, reading].add(name)
	for target, entries in rules.templates.buckets.items():
		for entry in entries:
			if entry.reading:
				curated[target, entry.reading].add(entry.id)
	characters = {}
	for ch, readings in sorted(polyphones.items()):
		items = {}
		for reading in sorted(readings):
			item = dict(evidence.get((ch, reading), {"headwords": 0, "examples": []}))
			item["curatedRuleIds"] = sorted(curated.get((ch, reading), ()))
			item["homophoneCandidate"] = rules.renderings.get(reading)
			item["automaticLexiconSpeechEligible"] = bool(
				item["headwords"]
				and ch in data["speechTargets"]
				and reading != data["defaults"].get(ch)
				and reading in data["renderings"]
			)
			item["status"] = (
				"curated_contexts"
				if item["curatedRuleIds"]
				else "lexicon_candidates"
				if item["automaticLexiconSpeechEligible"]
				else "annotation_evidence_only"
				if item["headwords"]
				else "needs_context_evidence"
			)
			items[reading] = item
		characters[ch] = {"unihanCNDefault": defaults.get(ch), "inTGHZ2013": ch in common, "readings": items}
	counts = {
		"unihanPolyphonicCharacters": len(characters),
		"inTGHZ2013": sum(item["inTGHZ2013"] for item in characters.values()),
		"readingPairs": sum(len(item["readings"]) for item in characters.values()),
		"charactersWithPhraseEvidence": sum(
			any(r["headwords"] for r in i["readings"].values()) for i in characters.values()
		),
	}
	statuses = defaultdict(int)
	for item in characters.values():
		for reading in item["readings"].values():
			statuses[reading["status"]] += 1
	report = {
		"schemaVersion": 1,
		"sourceSha256": PINS,
		"scope": "all multiple normalized readings in Unihan 17 kMandarin/kHanyuPinyin/kTGHZ2013; not all dictionaries",
		"limitations": [
			"Historical, regional, surname and variant readings are inventory, not automatic rules.",
			"Counts are source evidence and matching candidates, not sentence accuracy or acoustic validation.",
			"Runtime imports exact source-authored simplified/traditional headwords; no inferred conversion.",
			"Unihan default is a dictionary field, not an observed default for every speech engine.",
			"Static GF 0019-2018 output-table coverage is reported separately in braille_coverage.json.",
		],
		"counts": counts,
		"readingStatuses": dict(sorted(statuses.items())),
		"characters": characters,
	}
	return (json.dumps(report, ensure_ascii=False, indent=2) + "\n").encode()


def main() -> int:
	parser = argparse.ArgumentParser(description=__doc__)
	parser.add_argument("--check", action="store_true")
	parser.add_argument("--query", help="Show one character's source coverage")
	args = parser.parse_args()
	content = generate()
	if args.query:
		print(json.dumps(json.loads(content)["characters"].get(args.query), ensure_ascii=False, indent=2))
	elif args.check:
		if OUTPUT.read_bytes() != content:
			raise ValueError("Stale polyphone coverage ledger")
	else:
		OUTPUT.write_bytes(content)
		print(json.dumps(json.loads(content)["counts"], ensure_ascii=False))
	return 0


if __name__ == "__main__":
	raise SystemExit(main())
