"""Regression contract for pronunciation boundaries, not a Unicode word segmenter."""

from __future__ import annotations

import json
import sys
import unicodedata
import unittest

from tests.core_loader import PLUGIN_PATH, load

rules_module = load("rules")
REPORTED_SYMBOLS = "|$^+=<>`~"
# Spell out the categories independently of the implementation's first-letter test.
BOUNDARY_CATEGORIES = frozenset({"Pc", "Pd", "Pe", "Pf", "Pi", "Po", "Ps", "Sc", "Sk", "Sm", "So", "Zl", "Zp", "Zs"})
SCENARIOS = (
	("盛汤", "呈汤"),
	("第12行", "第12航"),
	("12行", "12航"),
	("行二", "航二"),
	("同辈中行三", "同辈中航三"),
	("行：12", "航：12"),
	("行 12", "航 12"),
)


def boundary_characters():
	for codepoint in range(sys.maxunicode + 1):
		character = chr(codepoint)
		if character.isspace() or unicodedata.category(character) in BOUNDARY_CATEGORIES:
			yield character


class BoundaryRegressionTests(unittest.TestCase):
	@classmethod
	def setUpClass(cls):
		cls.rules = rules_module.load_default_rules()
		cls.boundaries = tuple(boundary_characters())

	def test_reported_nine_symbols_after_soup(self):
		self.assertEqual(9, len(REPORTED_SYMBOLS))
		for symbol in REPORTED_SYMBOLS:
			with self.subTest(symbol=symbol, category=unicodedata.category(symbol)):
				self.assertEqual("呈汤" + symbol, self.rules.transform("盛汤" + symbol))

	def test_every_unicode_codepoint_obeys_shared_left_and_right_contract(self):
		for codepoint in range(sys.maxunicode + 1):
			character = chr(codepoint)
			expected = character.isspace() or unicodedata.category(character) in BOUNDARY_CATEGORIES
			if (
				rules_module._is_boundary(character, 0) != expected
				or rules_module._is_left_boundary(character, 1) != expected
			):
				self.fail(f"Boundary contract mismatch at U+{codepoint:04X} ({unicodedata.category(character)})")

	def test_serving_lexemes_and_bounded_phrases_with_every_unicode_separator(self):
		data = json.loads((PLUGIN_PATH / "data/rules_zh_CN.json").read_text("utf-8"))
		tested = 0
		for target, definition in data["characters"].items():
			for group in definition["phraseGroups"]:
				if not (
					group.get("leftBoundary")
					or group.get("rightBoundary")
					or group["id"] == "cheng-serving-object-bounded"
				):
					continue
				for phrase in group["phrases"]:
					expected_phrase = (
						phrase
						if group.get("protect")
						else phrase.replace(target, data["readings"][group["reading"]]["replacement"])
					)
					for symbol in self.boundaries:
						# Both sides, including repeated and paired punctuation; retain bytes/codepoints.
						source = symbol + phrase + symbol * 2
						expected = symbol + expected_phrase + symbol * 2
						if self.rules.transform(source, strict=False) != expected:
							self.fail(f"{group['id']} / {phrase!r} / U+{ord(symbol):04X}")
					tested += 1
		self.assertGreater(tested, 0, "This regression must not silently become an empty test")
		self.assertGreaterEqual(tested, 12, "All twelve serving lexemes must retain Unicode suffix coverage")

	def test_reported_nine_symbols_after_numeric_row(self):
		for symbol in REPORTED_SYMBOLS:
			with self.subTest(symbol=symbol):
				self.assertEqual("12航" + symbol, self.rules.transform("12行" + symbol))

	def test_all_structural_boundary_consumers_with_every_unicode_separator(self):
		for symbol in self.boundaries:
			for source, expected in SCENARIOS[1:]:
				if self.rules.transform(source + symbol) != expected + symbol:
					self.fail(f"Structural right boundary: {source!r} / U+{ord(symbol):04X}")
			if self.rules.transform(symbol + "行 12" + symbol) != symbol + "航 12" + symbol:
				self.fail(f"Row label left boundary: U+{ord(symbol):04X}")

	def test_declared_phrase_left_and_right_boundaries_share_the_contract(self):
		# Serving lexemes no longer need boundaries. Keep an explicit delimited
		# fixture so both boundary flags still have real coverage independently.
		data = {
			"schemaVersion": 1,
			"readings": {"cheng2": {"replacement": "呈"}},
			"characters": {
				"盛": {
					"phraseGroups": [
						{
							"id": "both-edges",
							"reading": "cheng2",
							"phrases": ["盛汤"],
							"leftBoundary": True,
							"rightBoundary": True,
						}
					]
				}
			},
		}
		isolated = rules_module.CompiledRules.from_mapping(data)
		for symbol in self.boundaries:
			self.assertEqual(symbol + "呈汤" + symbol, isolated.transform(symbol + "盛汤" + symbol))
		for source in ("张盛汤", "盛汤姆", "张盛汤姆"):
			self.assertIs(source, isolated.transform(source))

	def test_non_boundaries_are_not_promoted_to_punctuation(self):
		# Letters, numeric continuations, combining/variation marks, format controls,
		# private/unassigned codepoints and surrogates remain conservative, never deleted.
		for character in (
			"姆",
			"A",
			"é",
			"1",
			"\u0301",
			"\ufe0f",
			"\U000e0100",
			"\u200b",
			"\u200d",
			"\u2060",
			"\ufeff",
			"\x00",
			"\x1b",
			"\ue000",
			"\u0378",
			"\ud800",
		):
			with self.subTest(codepoint=f"U+{ord(character):04X}"):
				source = "12行" + character
				self.assertIs(source, self.rules.transform(source))
				self.assertFalse(rules_module._is_boundary(character, 0))
				# A complete lexical match must not depend on classifying its suffix
				# as a separator; preserve every suffix exactly, including controls.
				expected = "盛汤姆" if character == "姆" else "呈汤" + character
				self.assertEqual(expected, self.rules.transform("盛汤" + character))

	def test_protections_and_unknown_context_survive_adjacent_symbols(self):
		for symbol in REPORTED_SYMBOLS + "￥＋＝＜＞｜＾｀～×÷→★😀":
			for phrase in (
				"盛开",
				"盛汤姆",
				"盛饭店",
				"盛水准",
				"第一行星",
				"日行二百里",
				"重读音节",
				"重载卡车",
				"炮弹出膛",
				"显示屏住院部",
			):
				source = symbol + phrase + symbol
				self.assertIs(source, self.rules.transform(source))

	def test_edges_empty_strings_and_repeat_application(self):
		self.assertTrue(rules_module._is_boundary("", 0))
		self.assertTrue(rules_module._is_left_boundary("", 0))
		for source, expected in SCENARIOS:
			self.assertEqual(expected, self.rules.transform(source))
			self.assertIs(expected, self.rules.transform(expected))


if __name__ == "__main__":
	unittest.main()
