"""Pinned, attributed KFCD dictionary senses; never imported by the add-on.

The published simplified TSV is used directly. No character-by-character
conversion or first-reading selection is used to invent phrase pronunciations.
"""

from __future__ import annotations

import hashlib
from collections import Counter, defaultdict
from pathlib import Path

from tests.core_loader import load

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data/sources/hyzd-simplified-0498775.tsv"
COMMIT = "04987755b16264636c01d28df4d96fa14dadd210"
SOURCE_SHA256 = "d01a52ac466f9feb6c24ec28f0eea064556577606b8eb60c6731ed47c08ed1ee"
SOURCE_URL = f"https://github.com/kfcd/hyzd/blob/{COMMIT}/dist/tsv/简体/汉语字典_(汉语拼音_带数).txt"
numbered = load("pinyin").numbered


def records(lines):
	for line_number, line in enumerate(lines, 1):
		if not line.strip():
			continue
		fields = line.rstrip("\r\n").split("\t")
		if len(fields) != 6:
			raise ValueError(f"Invalid KFCD TSV field count at source line {line_number}")
		simplified, traditional, raw, examples, gloss, variants = fields
		yield {
			"id": f"kfcd-hyzd:{line_number}",
			"source": "kfcd-hyzd",
			"sourceLine": line_number,
			"kind": "characterSense",
			"forms": {"simplified": simplified, "traditional": traditional},
			"rawPinyin": raw,
			# Keep every attested alternative and invalid raw token for review.
			"readings": sorted({p for value in raw.split("/") if (p := numbered(value)) is not None}),
			"readingStatus": "parsed" if all(numbered(value) for value in raw.split("/")) else "unparsed",
			"examples": [value.strip() for value in examples.split("，") if value.strip()],
			"gloss": gloss,
			"variants": variants,
			"license": "CC-BY-3.0",
		}


def read_snapshot() -> list[str]:
	content = SOURCE.read_bytes()
	if hashlib.sha256(content).hexdigest() != SOURCE_SHA256:
		raise ValueError("KFCD snapshot differs from its reviewed pin")
	return content.decode("utf-8").splitlines()


def merge_examples(words, lines, *, han_pattern, character_readings, defaults, max_length):
	"""Merge partial target readings without guessing surrounding syllables.

	All source alternatives survive as conflicts. Existing CEDICT blockers
	cannot be rescued by a selected KFCD sense. Only exact complete examples
	are added; grammatical clauses and repeated-target examples are deferred.
	"""
	counts = Counter()
	candidates = defaultdict(lambda: defaultdict(set))
	provenance = defaultdict(set)
	for record in records(lines):
		counts["kfcdSenses"] += 1
		target = record["forms"]["simplified"]
		readings = record["readings"]
		if len(target) != 1 or not han_pattern.fullmatch(target):
			counts["kfcdInvalidTargetSenses"] += 1
			continue
		if len(character_readings.get(target, ())) < 2:
			continue
		for phrase in record["examples"]:
			counts["kfcdPolyphonicExamples"] += 1
			if not 2 <= len(phrase) <= max_length or not han_pattern.fullmatch(phrase) or phrase.count(target) != 1:
				counts["kfcdNonLiteralOrRepeatedExamplesDeferred"] += 1
				continue
			index = phrase.index(target)
			provenance[phrase].add(record["id"])
			if (
				record["readingStatus"] != "parsed"
				or len(readings) != 1
				or readings[0] not in character_readings.get(target, ())
				or defaults.get(target, "").endswith("5")
				or any(label in record["gloss"] for label in ("人名", "地名", "姓氏", "（姓）", "音译"))
			):
				candidates[phrase][index].add(None)
			else:
				candidates[phrase][index].add(readings[0])
	for phrase, positions in sorted(candidates.items()):
		existing = words.get(phrase)
		if existing is not None:
			provenance[phrase].add("CC-CEDICT")
		if existing is not None and (None in existing or len(existing) != 1):
			counts["kfcdExistingBlockersPreserved"] += 1
			continue
		conflict = False
		current = list(next(iter(existing))) if existing else [None] * len(phrase)
		for index, values in positions.items():
			if None in values or len(values) != 1:
				current[index] = None
				conflict = True
				continue
			reading = next(iter(values))
			if current[index] is not None and current[index] != reading:
				conflict = True
				current[index] = None
			else:
				current[index] = reading
		if not any(current):
			words[phrase] = {None}
			counts["kfcdConflictOrRiskBlocked"] += 1
		else:
			words[phrase] = {tuple(current)}
			counts["kfcdCorroboratedHeadwords" if existing else "kfcdAddedPartialHeadwords"] += 1
			if conflict:
				counts["kfcdPartialConflictHeadwords"] += 1
	return {phrase: sorted(ids) for phrase, ids in sorted(provenance.items())}, counts
