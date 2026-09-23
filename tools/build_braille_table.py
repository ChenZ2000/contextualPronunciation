"""Compile reviewed literal rules into an OPTIONAL GF 0019-2018 braille overlay.

Uses liblouis match on ONE original character, preserving character-to-cell
routing. Dynamic structures, boundary predicates and user settings are not
silently approximated. The base table's spacing/unknown text remain unchanged.
"""

from __future__ import annotations

import argparse
import itertools
import json
import re
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tests.core_loader import PLUGIN_PATH, load  # noqa: E402

TABLE = ROOT / "addon/brailleTables/zhcn-contextual-2018.ctb"
COVERAGE = ROOT / "data/braille_coverage.json"
# GF 0019-2018, sections 7-10: unlike the full-tone annotation API, apply
# abbreviation here. These non-syllabic-initial readings have been reviewed.
# New readings MUST be reviewed explicitly, never guessed from a homophone.
DOTS = {
	"hang2": "125-236",
	"chong2": "12345-256",
	"cheng2": "12345-3456",
	"bing3": "12-16-3",
	"tan2": "2345-1236",
	"yue4": "23456",
	"zhao1": "34-235-1",
	"zhang3": "34-236-3",
	"zhao2": "34-235-2",
	"huan2": "125-12456",
	"dei3": "145-2346-3",
	"qu3": "13-346-3",
	# j + i omits tone 4; l + iang retains tone 2. Independently checked
	# against the base table's 系好/测量/衡量 entries, not speech anchors.
	"ji4": "1245-24",
	"liang2": "123-1346-2",
}


def _han(text):
	return all("\u3400" <= ch <= "\u9fff" for ch in text)


def _escape(text):
	return "".join(f"\\x{ord(ch):04x}" for ch in text) or "-"


def _context(text, *, before):
	"""Accept at most one ASCII separator per boundary, as inserted by NVDA CWS.

	No wildcard, newline crossing or unbounded repetition. Protection and
	correction contexts use the SAME boundary grammar. Target stays one raw char.
	"""
	if not text:
		return "-"
	separator = r"\x0020?"
	pattern = separator.join(_escape(ch) for ch in text)
	return pattern + separator if before else separator + pattern


def _template_context(text, classes, *, before):
	"""Factor a finite Cartesian product without changing its accepted strings."""
	if not text:
		return "-"
	separator = r"\x0020?"
	parts = []
	for token in re.split(r"(\{\w+\})", text):
		if not token:
			continue
		values = sorted(set(classes[token[1:-1]])) if token.startswith("{") else [token]
		if not all(_han(value) for value in values):
			raise ValueError("Only finite Han contexts can be factored")
		alternatives = [separator.join(_escape(ch) for ch in value) for value in values]
		parts.append("(" + "|".join(alternatives) + ")" if len(values) > 1 else alternatives[0])
	pattern = separator.join(parts)
	return pattern + separator if before else separator + pattern


def _compact_templates(data, entries, excluded):
	# Moving equivalent outputs across one another is safe. If a target ever
	# has different corrective readings, keep its exact original ordered rules.
	readings = {}
	for (phrase, pivot), (reading, protect, _identifier, _priority) in entries.items():
		if not protect:
			readings.setdefault(phrase[pivot], set()).add(reading)
	blocked_ids = {identifier for identifier, _ in excluded}
	result = {}
	for entry in data["rules"]:
		if entry["id"] in blocked_ids or "{" not in entry["pattern"]:
			continue
		match = re.search(r"\[([^:]):[^\]]+\]", entry["pattern"])
		if len(readings.get(match[1], ())) > 1:
			continue
		compiled = load("templates").compile_template(
			entry, data["classes"], load("lexicon").load_default_lexicon().allowed_readings
		)
		before = _template_context(entry["pattern"][: match.start()], data["classes"], before=True)
		after = _template_context(entry["pattern"][match.end() :], data["classes"], before=False)
		dots = "=" if compiled.reading is None else DOTS[compiled.reading]
		line = f"noback match {before} {_escape(match[1])} {after} {dots}"
		# Pinned Liblouis MAXSTRING is 2048, including the complete input line.
		if len(line) < 2000:
			result[entry["id"]] = line
	return result


def generate(*, compact=True) -> tuple[bytes, dict]:
	rules = load("rules").CompiledRules.from_json_file(PLUGIN_PATH / "data/rules_zh_CN.json")
	entries, excluded = {}, []
	for rule in {item for bucket in rules._buckets.values() for item in bucket}:
		if rule.confidence != "high" or rule.left_boundary or rule.right_boundary or not _han(rule.phrase):
			excluded.append((rule.id, rule.phrase))
			continue
		key = (rule.phrase, rule.pivot)
		value = (rule.reading_id, rule.protect, rule.id, rule.priority)
		if key in entries and entries[key][:2] != value[:2]:
			raise ValueError(f"Conflicting braille phrase: {key}")
		entries[key] = value
	with (PLUGIN_PATH / "data/contributions.toml").open("rb") as stream:
		data = tomllib.load(stream)
	for entry in data["rules"]:
		pattern = entry["pattern"]
		classes = re.findall(r"\{(\w+)\}", pattern)
		if any(name not in data["classes"] for name in classes):
			excluded.append((entry["id"], "dynamic template"))
			continue
		for values in itertools.product(*(data["classes"][name] for name in classes)):
			expanded = pattern
			for name, value in zip(classes, values, strict=True):
				expanded = expanded.replace("{" + name + "}", value, 1)
			compiled = load("templates").compile_template(
				entry | {"pattern": expanded}, {}, load("lexicon").load_default_lexicon().allowed_readings
			)
			match = re.search(r"\[([^:]):[^\]]+\]", expanded)
			phrase = expanded[: match.start()] + match[1] + expanded[match.end() :]
			if not _han(phrase):
				excluded.append((entry["id"], phrase))
				continue
			key = (phrase, match.start())
			value = (compiled.reading, compiled.reading is None, entry["id"], compiled.priority)
			if key in entries and entries[key][:2] != value[:2]:
				raise ValueError(f"Conflicting braille contribution: {key}")
			entries.setdefault(key, value)
	lines = [
		"# Generated by tools/build_braille_table.py; do not hand-edit.",
		"# ContextualPronunciation contributors; phrase data: CC-BY-SA-4.0; see ../THIRD-PARTY-NOTICES.txt",
		"# Optional Chinese Common Braille 2018 fixed-phrase pronunciation overlay.",
		"# Not a complete segmentation/abbreviation engine; no user rules or dynamic number rules.",
		"# The NVDA-supplied base table retains its own LGPL-2.1-or-later license.",
		"include zhcn-cbs.ctb",
	]
	# Liblouis tests entries of the same target in order. Protection wins,
	# then longer contexts, just as in the runtime's reviewed phrase engine.
	ordered = sorted(entries.items(), key=lambda item: (-int(item[1][1]), -len(item[0][0]), -item[1][3], item[0]))
	factored = _compact_templates(data, entries, excluded) if compact else {}
	emitted = set()
	for (phrase, pivot), (reading, protect, identifier, _priority) in ordered:
		if identifier in factored:
			if identifier not in emitted:
				lines.extend((f"# Factored finite template: {identifier}", factored[identifier]))
				emitted.add(identifier)
			continue
		dots = "=" if protect else DOTS[reading]
		lines.append(f"# {identifier}: {phrase} ({'keep' if protect else reading})")
		lines.append(
			f"noback match {_context(phrase[:pivot], before=True)} {_escape(phrase[pivot])} "
			f"{_context(phrase[pivot + 1 :], before=False)} {dots}"
		)
	with (PLUGIN_PATH / "data/braille_contexts.toml").open("rb") as stream:
		grouped = tomllib.load(stream)
	if grouped.get("schemaVersion") != 1:
		raise ValueError("Invalid grouped braille context schema")
	for context in grouped["contexts"]:
		chars = context["characters"]
		if not 2 <= len(chars) <= 4 or not _han(chars) or not re.fullmatch(r"[1-6]+(?:-[1-6]+)*", context["dots"]):
			raise ValueError("Invalid grouped braille characters/dots")
		for after in context["after"]:
			if not 1 <= len(after) <= 8 or not _han(after):
				raise ValueError("Invalid grouped braille suffix")
			lines.append(f"# {context['id']}: {context['source']}")
			lines.append(
				f"noback match {_context(context['before'], before=True)} {_escape(chars)} "
				f"{_context(after, before=False)} {context['dots']}"
			)
	report = {
		"schemaVersion": 1,
		"baseTable": "zhcn-cbs.ctb",
		"scheme": "GF 0019-2018",
		"literalContexts": len(entries),
		"correctionContexts": sum(not value[1] for value in entries.values()),
		"protectionContexts": sum(value[1] for value in entries.values()),
		"compiledMatchRules": sum(line.startswith("noback match ") for line in lines),
		"factoredTemplateRules": len(emitted),
		"readings": DOTS,
		"separatorPolicy": "At most one ASCII space at each context boundary; no newline crossing",
		"baseWordGroupOverrides": grouped["contexts"],
		"excludedContexts": [list(value) for value in sorted(excluded)],
		"notCompiled": [
			"structural number rules",
			"user configuration",
			"extended CC-CEDICT matching",
			"full word segmentation",
			"full GF 0019-2018 translation",
		],
	}
	return ("\n".join(lines) + "\n").encode("utf-8"), report


if __name__ == "__main__":
	parser = argparse.ArgumentParser(description=__doc__)
	mode = parser.add_mutually_exclusive_group()
	mode.add_argument("--check", action="store_true")
	mode.add_argument("--reference-output", type=Path, help="Expanded differential-test table; never installed")
	args = parser.parse_args()
	if args.reference_output:
		content, _report = generate(compact=False)
		with args.reference_output.open("xb") as stream:
			stream.write(content)
		raise SystemExit(0)
	content, report = generate()
	for path, data in (
		(TABLE, content),
		(COVERAGE, (json.dumps(report, ensure_ascii=False, indent=2) + "\n").encode()),
	):
		if args.check:
			if not path.exists() or path.read_bytes() != data:
				raise ValueError(f"Stale generated braille data: {path}")
		else:
			path.parent.mkdir(parents=True, exist_ok=True)
			path.write_bytes(data)
	print(f"Braille overlay: {report['literalContexts']} literal contexts; {report['correctionContexts']} corrections")
