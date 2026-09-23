from __future__ import annotations

import json
import unittest
from unittest import mock

from tests.core_loader import PLUGIN_PATH, load
from tests.sentence_cases import (
	PROTECTED_CASES,
	REPORTED_CASES,
	SENTENCE_CASES,
	SERVING_PHRASES,
	serving_sentence_matrix,
)
from tests.test_pipeline import CharacterModeCommand, LangChangeCommand

rules_module = load("rules")


class SentenceRegressionTests(unittest.TestCase):
	@classmethod
	def setUpClass(cls):
		cls.rules = rules_module.load_default_rules()

	def test_reported_sentences_correct_every_target_not_only_the_last(self):
		for source, expected in REPORTED_CASES:
			with self.subTest(source=source):
				self.assertEqual(expected, self.rules.transform(source))

	def test_independent_sentence_oracles_and_protections(self):
		for strict in (True, False):
			for source, expected in SENTENCE_CASES:
				with self.subTest(source=source, strict=strict):
					self.assertEqual(expected, self.rules.transform(source, strict=strict))
			for source in PROTECTED_CASES:
				with self.subTest(protected=source, strict=strict):
					self.assertIs(source, self.rules.transform(source, strict=strict))

	def test_all_serving_objects_at_multiple_positions_and_in_both_orders(self):
		count = 0
		for source, expected in serving_sentence_matrix():
			self.assertEqual(expected, self.rules.transform(source), source)
			self.assertIs(expected, self.rules.transform(expected), "Normalization must be idempotent")
			count += 1
		self.assertEqual(18_144, count)

	def test_global_mapping_covers_sentence_matrix(self):
		self.assertEqual("呈", self.rules.renderings["cheng2"])
		for source, expected in (*SENTENCE_CASES, *serving_sentence_matrix()):
			self.assertEqual(expected, self.rules.transform(source))

	def test_serving_lexemes_do_not_use_delimiter_classifier(self):
		# A lexical match is sufficient: no suffix whitelist and no promotion of
		# arbitrary Chinese characters into punctuation boundaries is permitted.
		with mock.patch.object(rules_module, "_is_boundary", side_effect=AssertionError("Not a token boundary")):
			for source, expected in REPORTED_CASES:
				self.assertEqual(expected, self.rules.transform(source))

	def test_restoring_old_delimiter_policy_is_caught_by_each_reported_sentence(self):
		data = json.loads((PLUGIN_PATH / "data/rules_zh_CN.json").read_text("utf-8"))
		group = next(g for g in data["characters"]["盛"]["phraseGroups"] if g["id"] == "cheng-serving-object-bounded")
		self.assertEqual(set(SERVING_PHRASES), set(group["phrases"]))
		self.assertFalse(group.get("leftBoundary", False))
		self.assertFalse(group.get("rightBoundary", False))
		group["rightBoundary"] = True
		old_rules = rules_module.CompiledRules.from_mapping(data)
		with mock.patch.object(self.__class__, "rules", old_rules):
			result = unittest.TestResult()
			self.__class__("test_reported_sentences_correct_every_target_not_only_the_last").run(result)
		self.assertEqual(4, len(result.failures))
		self.assertFalse(result.errors)

	def test_protection_is_local_to_each_occurrence_and_uses_original_context(self):
		for source, expected in (
			("丰盛饭菜之后盛饭盛汤", "丰盛饭菜之后呈饭呈汤"),
			("盛汤盛饭之后是丰盛饭菜", "呈汤呈饭之后是丰盛饭菜"),
			("盛汤姆盛汤盛汤姆", "盛汤姆呈汤盛汤姆"),
		):
			self.assertEqual(expected, self.rules.transform(source))

	def test_explicit_user_keep_and_disabled_legacy_id_remain_authoritative(self):
		keep = rules_module.load_default_rules(custom_entries="盛汤|盛|keep")
		self.assertEqual("盛汤之后呈饭", keep.transform("盛汤之后盛饭"))
		disabled = rules_module.load_default_rules(disabled_rules="cheng-serving-object-bounded")
		self.assertEqual("盛汤之后盛饭", disabled.transform("盛汤之后盛饭"))

	def test_sentence_normalizer_keeps_input_commands_language_and_character_mode(self):
		pipeline = load("pipeline")
		normalizer = pipeline.SpeechSequenceNormalizer(
			rules=self.rules, character_mode_command_type=CharacterModeCommand
		)
		for source, expected in SENTENCE_CASES:
			sequence = [source]
			self.assertEqual([expected], normalizer.normalize(sequence, options=pipeline.RuntimeOptions()))
			self.assertEqual([source], sequence)
		start, end, english = CharacterModeCommand(True), CharacterModeCommand(False), LangChangeCommand("en_US")
		text = "盛饭盛汤很好"
		sequence = [start, text, end, text, english, text]
		self.assertEqual(
			[start, text, end, "呈饭呈汤很好", english, "呈饭呈汤很好"],
			normalizer.normalize(sequence, options=pipeline.RuntimeOptions()),
		)

	def test_incomplete_words_do_not_trigger_cross_command_or_cross_call_guessing(self):
		pipeline = load("pipeline")
		normalizer = pipeline.SpeechSequenceNormalizer(
			rules=self.rules, character_mode_command_type=CharacterModeCommand
		)
		for sequence in (["盛", "汤很好"], ["盛", LangChangeCommand("zh_CN"), "汤很好"]):
			self.assertIs(sequence, normalizer.normalize(sequence, options=pipeline.RuntimeOptions()))
		for text in ("盛", "汤很好", "盛"):
			self.assertIs(text, self.rules.transform(text))
