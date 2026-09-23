from __future__ import annotations

import unittest

from tests.core_loader import load


class BrailleReadingTests(unittest.TestCase):
	def test_factoring_preserves_finite_template_language(self):
		import itertools
		import re

		from tools.build_braille_table import _template_context

		classes = {"object": ["领结", "鞋带", "鞋带儿"], "result": ["上", "上了", "好"]}
		for before in (False, True):
			pattern = _template_context("{result}{object}", classes, before=before)
			pattern = re.sub(r"\\x([0-9a-f]{4})", lambda m: chr(int(m[1], 16)), pattern)
			for a, b in itertools.product(classes["result"], classes["object"]):
				text = a + b
				for value in (text, " ".join(text)):
					self.assertIsNotNone(re.fullmatch(pattern, value))
			for text in ("上", "领结", "上\n领结", "上  领结", "结果领结", "上了鞋"):
				self.assertIsNone(re.fullmatch(pattern, text))

	def test_conflicting_readings_cannot_be_reordered_by_factoring(self):
		from tools.build_braille_table import _compact_templates

		data = {"classes": {"word": ["乐曲"]}, "rules": [{"id": "test", "pattern": "{word}[乐:yue4]"}]}
		entries = {("乐曲乐", 2): ("yue4", False, "test", 100), ("快乐", 1): ("le4", False, "other", 100)}
		self.assertEqual({}, _compact_templates(data, entries, []))

	def test_generated_optional_table_reproduces_and_cannot_become_default(self):
		import json
		from pathlib import Path

		from tools.build_braille_table import COVERAGE, TABLE, generate

		content, coverage = generate()
		self.assertEqual(content, TABLE.read_bytes())
		self.assertEqual(coverage, json.loads(COVERAGE.read_text("utf-8")))
		self.assertGreater(coverage["correctionContexts"], 100)
		self.assertGreater(coverage["factoredTemplateRules"], 0)
		self.assertLess(coverage["compiledMatchRules"], coverage["literalContexts"] // 2)
		manifest = (Path(__file__).resolve().parents[1] / "manifest.ini").read_text("utf-8")
		self.assertIn("[[zhcn-contextual-2018.ctb]]", manifest)
		self.assertNotIn("outputForLangs", manifest)
		self.assertRegex(manifest, r"(?s)\[brailleTables\].*?input = false")

	def test_independent_full_tone_phonetic_examples(self):
		encode = load("braille_readings").full_tone_dots
		for reading, dots in {
			"xiān": ("125", "146", "1"),
			"yuè": ("23456", "23"),
			"chéng": ("12345", "3456", "2"),
			"háng": ("125", "236", "2"),
			"zhǐ": ("34", "3"),
			"qún": ("13", "456", "2"),
			"liú": ("123", "1256", "2"),
			"guī": ("1245", "2456", "1"),
			"wèn": ("25", "23"),
			"lǜ": ("123", "346", "23"),
			"de5": ("145", "26"),
			"er2": ("1235", "2"),
		}.items():
			self.assertEqual(dots, encode(reading), reading)
		self.assertIsNone(encode("xx5"))
		self.assertIsNone(encode("ng2"))

	def test_original_offsets_utf16_and_cells_never_use_homophone_characters(self):
		rules = load("rules").load_default_rules()
		text = "😀仙乐飘飘，盛汤"
		annotations = load("braille_readings").annotate(text, rules)
		by_offset = {value.start: value for value in annotations}
		self.assertEqual(
			("乐", "yue4", 3, 4),
			(by_offset[2].character, by_offset[2].reading, by_offset[2].utf16_start, by_offset[2].utf16_end),
		)
		self.assertEqual("⠾⠆", by_offset[2].cells)
		self.assertEqual("cheng2", by_offset[6].reading)
		self.assertEqual("盛", by_offset[6].character)
		self.assertEqual("😀仙乐飘飘，盛汤", text)

	def test_keep_conflict_unknown_and_no_speech_anchor_do_not_invent_readings(self):
		rules = load("rules").load_default_rules(custom_templates="仙[乐:keep]")
		annotate = load("braille_readings").annotate
		self.assertFalse(any(value.character == "乐" for value in annotate("仙乐", rules)))
		self.assertEqual((), annotate("龘龘", rules))
		self.assertEqual("zhao2", next(value.reading for value in annotate("睡着了", rules) if value.character == "着"))

	def test_contribution_audit_and_explainer(self):
		from tools.pronunciation import audit_contributions, explain

		rules = load("rules").load_default_rules()
		self.assertGreaterEqual(audit_contributions(rules)["contributionRules"], 6)
		report = explain("仙乐飘飘", rules)
		self.assertEqual("仙月飘飘", report["speechText"])
		self.assertIn("NOT full", report["brailleMode"])
