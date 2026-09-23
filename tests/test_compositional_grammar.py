from __future__ import annotations

import itertools
import json
import unittest
from pathlib import Path
from unittest import mock

from tests.core_loader import load
from tests.grammar_cases import CASES


class CompositionalGrammarTests(unittest.TestCase):
	@classmethod
	def setUpClass(cls):
		cls.rules = load("rules").load_default_rules(extended=False)
		cls.syntax = load("syntax")

	def test_reading_and_preservation_oracles_in_both_modes(self):
		for extended in (False, True):
			rules = load("rules").load_default_rules(extended=extended)
			for text, target, expected in CASES:
				with self.subTest(text=text, extended=extended):
					i = text.index(target)
					if expected is None:
						self.assertEqual(target, rules.transform(text)[i])
					else:
						decision = rules.resolve(text).get(i)
						self.assertIsNotNone(decision)
						self.assertEqual(expected, decision.reading_id)

	def test_productive_predicates_are_not_enumerated_prefixed_words(self):
		for verb in ("扫描", "剪辑", "分配", "拷贝", "配音", "校对"):
			for prefix, suffix in itertools.product(("", "请", "需要", "把这个文件"), ("", "一次", "之后继续")):
				text = prefix + "重" + verb + suffix
				i = len(prefix)
				self.assertEqual("chong2", self.rules.resolve(text)[i].reading_id, text)
				self.assertEqual("syntax-repeat-predicate", self.rules.resolve(text)[i].rule_id)

	def test_compositional_head_substitution_changes_the_decision(self):
		for modifier, head in itertools.product(
			("非常透明而且已经冷却的", "孩子刚刚买的", "小名的朋友的"),
			("液体", "豆角", "红豆粥"),
		):
			text = "盛" + modifier + head
			self.assertEqual("cheng2", self.rules.resolve(text)[0].reading_id, text)
			self.assertEqual("盛", self.rules.transform(text + "公司的价格")[0], text)

	def test_nested_dependencies_point_to_the_right_constituents(self):
		text = "😀量住在那条非常安静的街道旁边的小名的身高"
		p = self.rules.syntax.analyze(text, 1)
		self.assertEqual("身高", text[p.head_start : p.head_end])
		self.assertTrue(any(d.relation == "amod" and d.head == text.index("街道") for d in p.dependencies))
		self.assertTrue(any(d.relation == "acl" and d.head == text.index("小名") for d in p.dependencies))
		self.assertTrue(any(d.relation == "nmod" and d.head == text.index("身高") for d in p.dependencies))
		text = "😀请把文件重转一次"
		p = self.rules.syntax.analyze(text, text.index("重"))
		self.assertEqual("转", text[p.head_start : p.head_end])
		self.assertEqual("advmod", p.dependencies[0].relation)
		annotation = next(a for a in load("braille_readings").annotate(text, self.rules) if a.character == "重")
		self.assertEqual(text.index("重") + 1, annotation.utf16_start)

	def test_preposed_argument_relation_does_not_cross_punctuation(self):
		text = "把小名的身高再仔细地量一下"
		p = self.rules.syntax.analyze(text, text.index("量"))
		self.assertEqual("ba-preposed", p.construction)
		self.assertEqual("身高", text[p.head_start : p.head_end])
		for delimiter in ("，", "。", "；", "\n", "😀", "|", "\u200b"):
			text = "把小名的身高" + delimiter + "量未知事情"
			self.assertEqual("量", self.rules.transform(text)[text.index("量")])

	def test_user_keep_and_disabled_frame_override_generalization(self):
		for kwargs in (
			{"custom_templates": "[重:keep]转"},
			{"custom_entries": "重转|重|keep"},
			{"disabled_rules": "syntax-repeat-predicate"},
		):
			rules = load("rules").load_default_rules(extended=False, **kwargs)
			self.assertEqual("重转", rules.transform("重转"))
			self.assertEqual("呈红豆粥", rules.transform("盛红豆粥"))

	def test_explicit_surname_context_is_not_an_object_gap_relative(self):
		for prefix in ("姓", "姓氏为", "姓名为"):
			text = prefix + "盛的孩子的红豆粥"
			self.assertEqual(text, self.rules.transform(text))

	def test_speech_commands_spelling_and_unrelated_calls_are_isolated(self):
		class CharacterMode:
			def __init__(self, state):
				self.state = state

		pipe = load("pipeline")
		n = pipe.SpeechSequenceNormalizer(rules=self.rules, character_mode_command_type=CharacterMode)
		marker = object()
		seq = ["重", marker, "转", "重转", CharacterMode(True), "重转", CharacterMode(False)]
		out = n.normalize(seq, options=pipe.RuntimeOptions())
		self.assertEqual(["重", marker, "转", "崇转"], out[:4])
		self.assertEqual("重转", out[5])
		self.assertIs(marker, out[1])
		self.assertEqual("重", self.rules.transform("重"))
		self.assertEqual("转", self.rules.transform("转"))

	def test_speech_item_prefilter_is_semantically_equivalent(self):
		for text, target, _reading in CASES:
			i = text.index(target)
			parser = self.rules.syntax
			self.assertEqual(parser.analyze(text, i), parser.analyze(text, i, parser.context(text)), text)

	def test_short_productions_agree_with_the_constituent_chart(self):
		parser = self.rules.syntax
		for text, frame in (
			("盛豆角", parser.buckets["盛"][0]),
			("量小名的身高", parser.buckets["量"][0]),
			("盛透明的液体", parser.buckets["盛"][0]),
			("系孩子的鞋带", parser.buckets["系"][0]),
		):
			tokens = parser.lexicon.tokenize(text, 1)
			chart = self.syntax._NounParser(tokens).parse()
			self.assertEqual((chart, ()), parser._object(tokens, frame, 0))

	def test_expanded_budget_and_pathological_input_abstain_without_partial_head(self):
		text = next(t for t, _c, reading in CASES if reading == "liang2" and len(t) > 48)
		self.assertEqual("liang2", self.rules.resolve(text)[0].reading_id)
		for text in (
			"盛" + "新" * 600 + "红豆粥",
			"量" + "孩子的" * 100 + "身高",
			"盛" + "而且" * 300 + "液体",
			"量" + "龘" * 9 + "的身高",
		):
			self.assertIsNone(self.rules.syntax.analyze(text, 0))
		with mock.patch.object(self.syntax, "MAX_CHART_STATES", 1):
			self.assertIsNone(self.rules.syntax.analyze("盛孩子刚刚煮好的红豆粥", 0))

	def test_data_is_reproducible_with_explicit_provenance_and_no_hot_path_io(self):
		from tools.build_grammar_data import OUTPUT, generate

		self.assertEqual(OUTPUT.read_bytes(), generate())
		data = json.loads(OUTPUT.read_bytes())
		self.assertGreater(data["counts"]["words"], 350000)
		self.assertGreater(data["counts"]["verbCandidates"], 80000)
		self.assertGreaterEqual(len(data["sources"]), 3)
		self.assertIn(0, data["repeatBlockers"]["重击"])
		with (
			mock.patch("builtins.open", side_effect=AssertionError("speech path I/O")),
			mock.patch.object(Path, "open", side_effect=AssertionError("speech path I/O")),
		):
			self.assertEqual("崇转码", self.rules.transform("重转码"))
			self.assertEqual("梁孩子的朋友的妹妹的身高", self.rules.transform("量孩子的朋友的妹妹的身高"))

	def test_work_budget_is_local_and_preserves_other_reading_paths(self):
		text = "量孩子的朋友的妹妹的身高，重转，盛汤"
		with mock.patch.object(self.syntax, "MAX_ITEM_WORK", 1):
			out = self.rules.transform(text)
			self.assertTrue(out.startswith("量"))
			self.assertTrue(out.endswith("崇转，呈汤"))
		self.assertTrue(self.rules.transform(text).startswith("梁"))

	def test_new_performance_gate_rejects_missing_and_over_budget_measurements(self):
		from scripts.evidence import validate_grammar_performance

		with self.assertRaises(KeyError):
			validate_grammar_performance({})
		row = {"samples": 100, "codepoints": 10, "medianUs": 1000000}
		with self.assertRaises(ValueError):
			validate_grammar_performance({"modes": {"default": {"measurements": {"repeat": row}}}})
