"""Explain original-text decisions and export engine-neutral/braille annotations.

This is an explicit offline contributor tool, not a background document logger.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tests.core_loader import load  # noqa: E402


def audit_contributions(rules) -> dict:
	checked = 0
	for entries in rules.templates.buckets.values():
		for entry in entries:
			if entry.user:
				continue
			if not entry.source or not entry.positive or not entry.negative:
				raise ValueError(f"Missing source, positive or negative examples: {entry.id}")
			for text in entry.positive:
				if not any(entry.matches(text, index) for index in range(len(text))):
					raise ValueError(f"Positive example does not match: {entry.id}")
			for text in entry.negative:
				if any(entry.matches(text, index) for index in range(len(text))):
					raise ValueError(f"Negative example matched: {entry.id}")
			checked += 1
	frames = 0
	for frame in rules.syntax.frames:
		for text in frame.positive:
			index = text.index(frame.target)
			proposal = rules.syntax.analyze(text, index)
			if proposal is None or proposal.reading != frame.reading:
				raise ValueError(f"Positive argument example does not parse: {frame.id}")
		for text in frame.negative:
			index = text.index(frame.target)
			proposal = rules.syntax.analyze(text, index)
			decision = rules.resolve(text).get(index)
			if proposal is not None and decision is not None and decision.rule_id == frame.id:
				raise ValueError(f"Negative argument example selected fallback: {frame.id}")
		frames += 1
	return {"passed": True, "contributionRules": checked, "argumentFrames": frames}


def explain(text: str, rules) -> dict:
	decisions = rules.resolve(text)
	return {
		"original": text,
		"speechText": rules.transform(text),
		"lexicalSpans": [asdict(span) for span in rules.lexicon.annotate(text)] if rules.lexicon is not None else [],
		"decisions": [
			{"offset": index, "character": text[index], **asdict(value)} for index, value in sorted(decisions.items())
		],
		"brailleAnnotations": [asdict(value) for value in load("braille_readings").annotate(text, rules)],
		"brailleMode": "phonetic full citation tones, NOT full GF 0019-2018 translation",
		"syntaxProposals": [
			{
				**asdict(proposal),
				"selected": decisions.get(index) is not None and decisions[index].rule_id == proposal.rule_id,
			}
			for index, character in enumerate(text)
			if rules.syntax is not None
			and character in rules.syntax.triggers
			and (proposal := rules.syntax.analyze(text, index)) is not None
		],
		"unknownPolicy": "Absent annotations are unknown, not inferred defaults",
	}


def main() -> int:
	parser = argparse.ArgumentParser(description=__doc__)
	parser.add_argument("text", nargs="?")
	parser.add_argument("--templates", type=Path, help="UTF-8 file with one readable template per line")
	parser.add_argument("--check-contributions", action="store_true")
	parser.add_argument("--output", type=Path)
	args = parser.parse_args()
	if args.text is None and not args.check_contributions:
		parser.error("Supply text or --check-contributions")
	custom = ""
	if args.templates:
		if args.templates.stat().st_size > 131072:
			parser.error("Template file exceeds the safe byte limit")
		custom = args.templates.read_text("utf-8-sig")
	rules = load("rules").load_default_rules(custom_templates=custom)
	report = audit_contributions(rules) if args.check_contributions else explain(args.text, rules)
	serialized = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
	if args.output:
		args.output.write_text(serialized, "utf-8")
	print(serialized)
	return 0


if __name__ == "__main__":
	raise SystemExit(main())
