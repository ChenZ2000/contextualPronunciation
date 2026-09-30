"""Productive growth, length, nominal words and deliberate ambiguity."""

from __future__ import annotations

import unittest

from tests.core_loader import load
from tests.growth_cases import GROWTH, LENGTH, LEXICAL, PRESERVED, generated_locations


class GrowthTests(unittest.TestCase):
	@classmethod
	def setUpClass(cls):
		cls.modes = {extended: load("rules").load_default_rules(extended=extended) for extended in (False, True)}

	def test_independent_context_readings(self):
		for rules in self.modes.values():
			for reading, texts in (("zhang3", GROWTH), ("chang2", LENGTH)):
				for text in texts:
					with self.subTest(text=text, reading=reading):
						for i, char in enumerate(text):
							if char == "长":
								decision = rules.resolve(text).get(i)
								self.assertIsNotNone(decision)
								self.assertEqual(reading, decision.reading_id)
								self.assertEqual(rules.renderings[reading], rules.transform(text)[i])

	def test_productive_locations_outside_phrase_inventory(self):
		for rules in self.modes.values():
			for text in generated_locations():
				with self.subTest(text=text):
					i = text.index("长")
					self.assertEqual("zhang3", rules.resolve(text)[i].reading_id)
					self.assertEqual("掌", rules.transform(text)[i])

	def test_ambiguous_and_distant_evidence_does_not_supply_readings(self):
		for rules in self.modes.values():
			for text in PRESERVED:
				with self.subTest(text=text):
					self.assertEqual(text, rules.transform(text, targets=frozenset("长長")))
					for i, d in rules.resolve(text).items():
						if text[i] in "长長":
							self.assertTrue(d.protect or not d.speech)

	def test_source_lexical_growth_elder_chief_and_length_readings_are_locked(self):
		rules = self.modes[True]
		for text, reading in LEXICAL:
			with self.subTest(text=text):
				i = text.index("长")
				self.assertEqual(reading, rules.resolve(text)[i].reading_id)
				self.assertEqual(rules.renderings[reading], rules.transform(text)[i])

	def test_growth_followed_by_length_has_two_different_readings(self):
		for rules in self.modes.values():
			for text in ("头发长长了", "指甲长长了", "小草长长了"):
				with self.subTest(text=text):
					positions = [i for i, ch in enumerate(text) if ch == "长"]
					self.assertEqual(["zhang3", "chang2"], [rules.resolve(text)[i].reading_id for i in positions])
					self.assertEqual(text.replace("长长", "掌偿"), rules.transform(text, targets=frozenset("长")))
			text = "头发长得很长"
			self.assertEqual("头发掌得很偿", rules.transform(text, targets=frozenset("长")))

	def test_traditional_punctuation_and_original_offsets(self):
		braille = load("braille_readings")
		for rules in self.modes.values():
			for base, reading in (("胸前長了", "zhang3"), ("頭髮很長", "chang2"), ("背上长", "zhang3")):
				for suffix in ("", "。", "！", "？", ".", "…", "；", "\n", "😀"):
					text = "😀" + base + suffix
					i = next(i for i, ch in enumerate(text) if ch in "长長")
					with self.subTest(text=text):
						self.assertEqual(reading, rules.resolve(text)[i].reading_id)
						self.assertEqual(
							{i: d for i, d in rules.resolve(text).items() if d.speech},
							rules.resolve(text, speech_only=True),
						)
						a = next(a for a in braille.annotate(text, rules) if a.start == i)
						self.assertEqual((text[i], reading, i + 1), (a.character, a.reading, a.utf16_start))

	def test_dependencies_identify_argument_heads_and_locations(self):
		rules = self.modes[True]
		text = "我的脸上又长了两个痘痘"
		proposal = rules.syntax.analyze(text, text.index("长"))
		self.assertEqual("痘痘", text[proposal.head_start : proposal.head_end])
		self.assertEqual(
			{"obl:location", "case:localizer", "obj", "aspect", "advmod"},
			{d.relation for d in proposal.dependencies} & {"obl:location", "case:localizer", "obj", "aspect", "advmod"},
		)
		from tools.pronunciation import explain

		self.assertTrue(explain(text, rules)["syntaxProposals"][0]["selected"])

	def test_speech_projection_preserves_all_detailed_reading_decisions(self):
		for rules in self.modes.values():
			for text in (*GROWTH, *LENGTH, *PRESERVED, "头发长长了", "给我长脸了，各自长了。"):
				with self.subTest(text=text):
					self.assertEqual(
						{i: d for i, d in rules.resolve(text).items() if d.speech},
						rules.resolve(text, speech_only=True),
					)

	def test_user_keep_disabled_senses_and_speech_items(self):
		for extended in (False, True):
			for kwargs in (
				{"custom_entries": "背上长|长|keep"},
				{"custom_templates": "背上[长:keep]"},
				{"disabled_rules": "syntax-growth"},
			):
				rules = load("rules").load_default_rules(extended=extended, **kwargs)
				self.assertEqual("背上长了", rules.transform("背上长了", targets=frozenset("长")))
				self.assertEqual("头发很偿", rules.transform("头发很长", targets=frozenset("长")))
			from tests.test_pipeline import CharacterModeCommand

			p = load("pipeline")
			n = p.SpeechSequenceNormalizer(rules=self.modes[extended], character_mode_command_type=CharacterModeCommand)
			marker = object()
			sequence = [
				"背上",
				marker,
				"长",
				CharacterModeCommand(True),
				"胸前长了",
				CharacterModeCommand(False),
				"胸前长了",
			]
			actual = n.normalize(sequence, options=p.RuntimeOptions())
			self.assertEqual(sequence[:5], actual[:5])
			self.assertEqual("胸前掌了", actual[-1])

	def test_work_and_repetition_limits(self):
		g = load("syntax")
		rules = self.modes[False]
		for text in ("长" * 8192, "孩子长" + "呀长" * 12, "我的" * 120 + "背上长了"):
			self.assertEqual(text, rules.transform(text))
		context = rules.syntax.context("胸前长了")
		context.remaining_work = 0
		self.assertIsNone(rules.syntax.analyze("胸前长了", 2, context))
		self.assertLessEqual(context.remaining_work, g.MAX_ITEM_WORK)

	def test_growth_latency_gate_requires_all_scenarios_and_valid_samples(self):
		from copy import deepcopy

		from tools.benchmark_growth import SCENARIOS, validate

		report = {
			"modes": {
				mode: {
					name: {"medianUs": 1, "samples": 100, "codepoints": len(text)} for name, text in SCENARIOS.items()
				}
				for mode in ("default", "extended")
			}
		}
		validate(report)
		for value in (201, float("nan"), float("inf"), 0):
			bad = deepcopy(report)
			bad["modes"]["default"]["bodyLocation"]["medianUs"] = value
			with self.assertRaises(ValueError):
				validate(bad)
		bad = deepcopy(report)
		del bad["modes"]["extended"]["mixed8k"]
		with self.assertRaises(ValueError):
			validate(bad)
		bad = deepcopy(report)
		bad["modes"]["extended"]["roles8k"]["samples"] = 99
		with self.assertRaises(ValueError):
			validate(bad)
