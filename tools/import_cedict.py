"""Reproducibly derive a conservative Mandarin lexicon from licensed snapshots.

This is a data compiler, never imported on NVDA's speech path. No web scraping,
implicit downloads, arbitrary first-reading choice, sandhi or traditional-to-
simplified character substitution is performed.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tests.core_loader import load  # noqa: E402
from tools.open_dictionary import COMMIT as KFCD_COMMIT  # noqa: E402
from tools.open_dictionary import SOURCE_SHA256 as KFCD_SHA256  # noqa: E402
from tools.open_dictionary import SOURCE_URL as KFCD_URL  # noqa: E402
from tools.open_dictionary import merge_examples, read_snapshot  # noqa: E402

numbered = load("pinyin").numbered
DATA = ROOT / "addon/globalPlugins/contextualPronunciation/data"
CEDICT = ROOT / "data/sources/cedict-20260907.txt.gz"
UNIHAN = ROOT / "data/sources/Unihan_Readings-17.0.0.txt.gz"
PINS = {
	"cedict": "cd81c0d253c82d4b1dc3ca2cfe4cd5fc46ca10b753743a80d783f3969ae11a23",
	"unihan": "575e69c9ad85a4737a889a4f94cbd987042a90a1a6cc16dd3f4ed995c715b17c",
}
LINE = re.compile(r"^(\S+) (\S+) \[([^\[\]]+)\] /(.*)/$")
HAN = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\U00020000-\U000323af]+\Z")
MAX_WORD_LENGTH = 32
# The hand-reviewed rule families retain exclusive speech authority. Broad
# imports must not revive disabled rules or override existing negative cases.
RESERVED = "行重盛屏弹钥"


def read_unihan(lines) -> tuple[dict, dict, set]:
	defaults, readings, common = {}, defaultdict(set), set()
	for line in lines:
		if line.startswith("#") or not line.strip():
			continue
		codepoint, field, value = line.rstrip("\r\n").split("\t", 2)
		character = chr(int(codepoint[2:], 16))
		if field == "kMandarin":
			values = value.split()
			defaults[character] = numbered(values[0])
		elif field in {"kHanyuPinyin", "kTGHZ2013"}:
			values = [p for group in value.split() for p in group.partition(":")[2].split(",")]
			if field == "kTGHZ2013":
				common.add(character)
		else:
			continue
		readings[character].update(p for raw in values if (p := numbered(raw)) is not None)
	return defaults, readings, common


def parse_cedict(lines) -> tuple[dict, dict, Counter]:
	"""Keep all homographic alternatives. Ineligible entries remain blockers."""
	words, single_readings, counts = defaultdict(set), defaultdict(set), Counter()
	for line in lines:
		if line.startswith("#") or not line.strip():
			continue
		counts["sourceEntries"] += 1
		match = LINE.fullmatch(line.rstrip("\r\n"))
		if match is None:
			raise ValueError(f"Invalid CC-CEDICT v1 record at entry {counts['sourceEntries']}")
		traditional, word, raw, _definition = match.groups()
		if not HAN.fullmatch(word):
			counts["nonHanHeadwords"] += 1
			continue
		tokens = raw.split()
		readings = tuple(numbered(token) for token in tokens)
		aligned = len(readings) == len(word) and all(readings)
		if raw != raw.lower():
			counts["properNameEntriesBlocked"] += len(word) > 1
		elif not aligned:
			counts["unalignedEntriesBlocked"] += len(word) > 1
		# These are two source-authored headwords, NOT character substitution.
		# Cross-form collisions retain all alternatives, independent of order.
		for form in sorted({word, traditional}):
			if not HAN.fullmatch(form):
				continue
			counts["sourceHeadwordForms"] += 1
			form_aligned = len(readings) == len(form) and all(readings)
			if len(form) == 1:
				if form_aligned:
					single_readings[form].update(readings)
				continue
			if len(form) > MAX_WORD_LENGTH:
				raise ValueError("Headword exceeds the reviewed matching bound; update policy explicitly")
			words[form].add(readings if raw == raw.lower() and form_aligned else None)
	return words, single_readings, counts


def compile_lexicon(cedict_lines, unihan_lines, hyzd_lines=()) -> tuple[dict, dict]:
	defaults, character_readings, common = read_unihan(unihan_lines)
	words, singles, counts = parse_cedict(cedict_lines)
	word_sources, source_counts = merge_examples(
		words,
		hyzd_lines,
		han_pattern=HAN,
		character_readings=character_readings,
		defaults=defaults,
		max_length=MAX_WORD_LENGTH,
	)
	counts.update(source_counts)
	# Candidate renderers need two independent kinds of evidence: a common
	# character with exactly one Unihan reading, and no CC-CEDICT disagreement.
	anchors = defaultdict(list)
	for character in sorted(common):
		values = character_readings[character] | singles.get(character, set())
		if len(values) != 1 or len(character) != 1:
			continue
		reading = next(iter(values))
		if reading.endswith("5") or not defaults.get(character) == reading:
			continue
		try:
			encoded = character.encode("gb2312")
		except UnicodeEncodeError:
			continue
		# GB2312 level 1 first, then deterministic code-point order. This is a
		# legibility heuristic, not a word-frequency or engine-validation claim.
		anchors[reading].append((0 if b"\xb0\xa1" <= encoded <= b"\xd7\xf9" else 1, character))
	renderings = {reading: min(values)[1] for reading, values in sorted(anchors.items())}
	compiled, blocked, targets = {}, {}, defaultdict(set)
	unknown_positions = {}
	for word, alternatives in sorted(words.items()):
		if None in alternatives or len(alternatives) != 1:
			compiled[word] = ""
			blocked[word] = "ineligible_entry" if None in alternatives else "multiple_readings"
			continue
		readings = next(iter(alternatives))
		# Neutral-default changes can signal a DIFFERENT grammatical parse of
		# the entire word, not merely a missing syllable. E.g. 中的 (hit a target)
		# cannot supply zhong4 for 文中的词语. Retain this whole-word blocker.
		if any(
			p is not None and defaults.get(ch, "").endswith("5") and p != defaults[ch]
			for ch, p in zip(word, readings, strict=True)
		):
			compiled[word] = ""
			blocked[word] = "neutral_default_requires_grammar"
			continue
		# A syllable must also be attested for that character in Unihan. A
		# neutral tone is accepted for annotation but never given a made-up anchor.
		# Cross-check each aligned position independently. One unknown character
		# does not invalidate another character's attested reading. Keep the whole
		# word for segmentation; never split around an unknown position. Homograph
		# and proper-name blockers above remain opaque, not partially rescued.
		checked, reasons = [], {}
		for index, (ch, p) in enumerate(zip(word, readings, strict=True)):
			if p is not None and p not in character_readings[ch] and not p.endswith("5"):
				reasons[str(index)] = "unihan_disagreement_or_missing"
			checked.append(None if str(index) in reasons else p)
		readings = tuple(checked)
		if reasons:
			unknown_positions[word] = reasons
		if not any(readings):
			compiled[word] = ""
			blocked[word] = "no_verified_positions"
			continue
		compiled[word] = " ".join(p or "?" for p in readings)
		for character, reading in zip(word, readings, strict=True):
			if reading is not None and defaults.get(character) and reading != defaults[character]:
				targets[character].add(reading)
	counts.update(
		{
			"headwords": len(compiled),
			"annotatableHeadwords": sum(bool(v) for v in compiled.values()),
			"blockedHeadwords": len(blocked),
			"polyphonicCharactersInLexicon": len(targets),
			"homophoneReadings": len(renderings),
			"headwordsWithCrossCheckAbstentions": len(unknown_positions),
			"crossCheckAbstainedPositions": sum(map(len, unknown_positions.values())),
		}
	)
	speech_targets = sorted(
		ch
		for ch, values in targets.items()
		if ch not in RESERVED and not defaults[ch].endswith("5") and values & renderings.keys()
	)
	counts["automaticLexiconSpeechCharacters"] = len(speech_targets)
	counts["headwordsWithRenderableAlternatives"] = sum(
		any(
			ch in speech_targets and reading != defaults[ch] and reading in renderings
			for ch, reading in zip(word, value.split(), strict=True)
		)
		for word, value in compiled.items()
		if value
	)
	runtime = {
		"schemaVersion": 2,
		"maxWordLength": MAX_WORD_LENGTH,
		"source": {
			"name": "CC-CEDICT (MDBG); KFCD open Chinese dictionary; Unicode Unihan 17.0.0",
			"cedictDate": "2026-09-07T08:01:26Z",
			"cedictUrl": "https://www.mdbg.net/chinese/export/cedict/cedict_1_0_ts_utf-8_mdbg.txt.gz",
			"unihanUrl": "https://www.unicode.org/Public/17.0.0/ucd/Unihan.zip",
			"sha256": PINS,
			"kfcdUrl": KFCD_URL,
			"kfcdCommit": KFCD_COMMIT,
			"kfcdSha256": KFCD_SHA256,
			"licenses": ["CC-BY-SA-4.0.txt", "KFCD-LICENSE.txt", "UNICODE-LICENSE.txt"],
			"modifications": (
				"Exact source-authored simplified AND traditional headwords; no character conversion; "
				"KFCD partial example readings (? means unknown); "
				"conflicting positions abstain; opaque CEDICT blockers retained; "
				"Per-position Unihan cross-check (? for unverified positions); no definitions."
			),
		},
		"reservedTargets": RESERVED,
		"speechTargets": speech_targets,
		"allowedReadings": sorted(set().union(*character_readings.values())),
		"defaults": {ch: defaults[ch] for ch in sorted(targets)},
		"renderings": renderings,
		"words": compiled,
		"wordSources": word_sources,
	}
	coverage = {
		"schemaVersion": 2,
		"source": runtime["source"],
		"counts": dict(sorted(counts.items())),
		"blockReasons": dict(sorted(Counter(blocked.values()).items())),
		"blockedHeadwords": blocked,
		"unknownPositions": unknown_positions,
		"characters": {
			ch: {
				"default": defaults[ch],
				"alternativeReadings": sorted(values),
				"renderableAlternatives": sorted(values & renderings.keys()),
				"speechAuthority": (
					"curated_rules"
					if ch in RESERVED
					else "deferred_neutral_default_grammar"
					if defaults[ch].endswith("5")
					else "lexicon_consensus"
				),
			}
			for ch, values in sorted(targets.items())
		},
	}
	return runtime, coverage


def generate() -> dict[Path, bytes]:
	for name, content in (("cedict", CEDICT.read_bytes()), ("unihan", gzip.decompress(UNIHAN.read_bytes()))):
		if hashlib.sha256(content).hexdigest() != PINS[name]:
			raise ValueError(f"Unreviewed {name} snapshot; expected pinned SHA-256")
	with gzip.open(CEDICT, "rt", encoding="utf-8") as stream:
		cedict = stream.readlines()
	if "#! license=https://creativecommons.org/licenses/by-sa/4.0/\n" not in cedict:
		raise ValueError("Unexpected source license; do not redistribute automatically")
	with gzip.open(UNIHAN, "rt", encoding="utf-8") as stream:
		runtime, coverage = compile_lexicon(cedict, stream, read_snapshot())
	return {
		DATA / "lexicon_zh_CN.json": (json.dumps(runtime, ensure_ascii=False, separators=(",", ":")) + "\n").encode(),
		DATA / "readings_zh_CN.json": (
			json.dumps(
				{key: runtime[key] for key in ("schemaVersion", "source", "allowedReadings", "renderings")},
				ensure_ascii=False,
				separators=(",", ":"),
			)
			+ "\n"
		).encode(),
		ROOT / "data/lexicon_coverage.json": (json.dumps(coverage, ensure_ascii=False, indent=2) + "\n").encode(),
	}


def main() -> int:
	parser = argparse.ArgumentParser(description=__doc__)
	parser.add_argument("--check", action="store_true", help="Compare all generated bytes without modifying files")
	args = parser.parse_args()
	for path, content in generate().items():
		if args.check:
			if path.read_bytes() != content:
				raise ValueError(f"Stale generated data: {path}")
		else:
			path.write_bytes(content)
		print(f"{path.relative_to(ROOT)}: {len(content)} bytes, SHA256 {hashlib.sha256(content).hexdigest()}")
	return 0


if __name__ == "__main__":
	raise SystemExit(main())
