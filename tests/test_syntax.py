"""Compositional grammar tests, not a claim of open-domain semantic accuracy."""

from __future__ import annotations

import io
import itertools
import json
import pickle
import unittest
from dataclasses import replace
from pathlib import Path
from unittest import mock

from tests.core_loader import load

ROOT = Path(__file__).resolve().parents[1]
syntax = load("syntax")
POSITIVE = (
	("盛豆角", "盛", "cheng2"),
	("盛红豆粥", "盛", "cheng2"),
	("盛刚煮好的红豆粥", "盛", "cheng2"),
	("盛了孩子刚煮好的红豆粥", "盛", "cheng2"),
	("盛这锅热乎乎的八宝粥", "盛", "cheng2"),
	("盛小名的红豆粥", "盛", "cheng2"),
	("量小名的身高", "量", "liang2"),
	("量住在隔壁的小名的身高", "量", "liang2"),
	("量这张桌子的长度", "量", "liang2"),
	("量那根绳子的长度", "量", "liang2"),
	("量刚买的桌子的宽度", "量", "liang2"),
	("量祁沐澄的身高", "量", "liang2"),
	("量一下祁沐澄的身高", "量", "liang2"),
	("量這張桌子的長度", "量", "liang2"),
	("系小名的鞋带", "系", "ji4"),
	("系这条红色的丝带", "系", "ji4"),
	("系紧孩子新买的红领巾", "系", "ji4"),
)
NEGATIVE = (
	"盛先生",
	"盛女士",
	"盛豆角公司的产品",
	"盛红豆粥的价格",
	"盛苹果公司的产品",
	"丰盛的红豆粥",
	"盛大的宴会",
	"盛开的花",
	"茂盛的豆角",
	"旺盛的食欲",
	"量小名的身高标准",
	"量未知的事情",
	"量小名说话然后记录身高",
	"商量小名的身高",
	"估量小名的身高",
	"校量小名的身高",
	"考量小名的身高",
	"数量小名的身高",
	"力量小名的身高",
	"关系小名的前途",
	"联系小名的鞋带厂家",
)


class SyntaxTests(unittest.TestCase):
	@classmethod
	def setUpClass(cls):
		cls.rules = load("rules").load_default_rules(extended=False)
		cls.parser = cls.rules.syntax

	def test_compositional_examples_default_and_extended(self):
		for extended in (False, True):
			rules = load("rules").load_default_rules(extended=extended)
			for text, target, reading in POSITIVE:
				for prefix, suffix in (("", ""), ("我给孩子", "之后继续"), ("😀", "|$^+=<>`~")):
					value = prefix + text + suffix
					index = value.index(target)
					with self.subTest(text=value, extended=extended):
						self.assertEqual(reading, rules.resolve(value)[index].reading_id)
						self.assertEqual(rules.renderings[reading], rules.transform(value)[index])

	def test_negative_heads_lexical_protections_and_no_keyword_skipping(self):
		for text in NEGATIVE:
			for i, ch in enumerate(text):
				if ch in self.parser.triggers:
					self.assertEqual(ch, self.rules.transform(text)[i], text)
		for text in ("盛未知红豆粥", "量𠀀的身高", "盛豆角龘靐", "量小名的身高标准"):
			self.assertIsNone(self.parser.analyze(text, 0), text)

	def test_unseen_possessors_are_variables_not_registered_phrases(self):
		# These names are deliberately absent from the data, not new dictionary entries.
		for name in ("祁沐澄", "霁苒晞", "龘靐齉", "昕玥桐"):
			self.assertNotIn(name, self.parser.lexicon.words)
			for target, head, reading in (("量", "身高", "liang2"), ("系", "鞋带", "ji4"), ("盛", "红豆粥", "cheng2")):
				text = target + name + "的" + head
				self.assertEqual(reading, self.rules.resolve(text)[0].reading_id, text)

	def test_noun_heads_compose_instead_of_enumerating_dishes(self):
		for ingredient, head in itertools.product(("红豆", "绿豆", "南瓜", "银耳", "山药"), ("粥", "汤", "羹")):
			text = "盛" + ingredient + head
			proposal = self.parser.analyze(text, 0)
			self.assertIsNotNone(proposal, text)
			self.assertEqual("cheng2", proposal.reading)
			self.assertEqual("cheng2", self.rules.resolve(text)[0].reading_id)
			# Swapping the final head changes the construction's semantic type.
			self.assertIsNone(self.parser.analyze(text + "公司的产品", 0), text)

	def test_nested_dependency_attachment_and_original_offsets(self):
		text = "😀量住在隔壁的小名的身高"
		proposal = self.parser.analyze(text, 1)
		self.assertEqual("身高", text[proposal.head_start : proposal.head_end])
		acl = next(dep for dep in proposal.dependencies if dep.relation == "acl")
		nmod = next(dep for dep in proposal.dependencies if dep.relation == "nmod")
		self.assertEqual(text.index("小名"), acl.head)
		self.assertEqual(text.index("身高"), nmod.head)
		self.assertEqual("住在隔壁的", text[acl.start : acl.end])
		annotations = load("braille_readings").annotate(text, self.rules)
		self.assertEqual(
			(1, 2, 2, 3, "liang2"),
			(
				annotations[0].start,
				annotations[0].end,
				annotations[0].utf16_start,
				annotations[0].utf16_end,
				annotations[0].reading,
			),
		)
		self.assertEqual(text, "😀量住在隔壁的小名的身高")

	def test_lexicalized_numeral_nouns_are_not_split_as_numbers(self):
		for word in ("三明治", "八宝粥"):
			text = "盛" + word
			tokens = self.parser.lexicon.tokenize(text, 1)
			self.assertEqual(word, tokens[0].text)
			self.assertEqual("cheng2", self.parser.analyze(text, 0).reading)
		self.assertEqual(syntax.NUMBER, self.parser.lexicon.tokenize("十二个孩子的身高", 0)[0].features)

	def test_precise_user_rules_and_disabling_win_over_generalization(self):
		module = load("rules")
		for kwargs in (
			{"custom_entries": "盛豆角|盛|keep"},
			{"custom_templates": "[盛:keep]豆角"},
			{"disabled_rules": "syntax-serving-object"},
		):
			rules = module.load_default_rules(extended=False, **kwargs)
			self.assertEqual("盛豆角", rules.transform("盛豆角"))
			self.assertEqual("梁小名的身高", rules.transform("量小名的身高"))
		# Disabling an old positive or a protection is not permission for a
		# new, more general frame to reinstate that reading behind the user's back.
		rules = module.load_default_rules(extended=False, disabled_rules="cheng-serving-object-bounded")
		self.assertEqual("盛汤", rules.transform("盛汤"))
		self.assertEqual("呈豆角", rules.transform("盛豆角"))
		rules = module.load_default_rules(extended=False, custom_entries="盛豆角|盛|sheng4")
		self.assertEqual("sheng4", rules.resolve("盛豆角")[0].reading_id)

	def test_unknown_names_clauses_and_token_depth_budgets_abstain(self):
		for text in (
			"量" + "龘" * 9 + "的身高",
			"量" + "孩子的" * (syntax.MAX_DEPTH + 1) + "身高",
			"盛" + "新" * (syntax.MAX_CHARS + 1) + "红豆粥",
			"量" + "小名" * (syntax.MAX_TOKENS + 1) + "的身高",
			"量" + " " * 5 + "小名的身高",
			"量1234567890123个孩子的身高",
			"量买龘靐的身高",
		):
			self.assertIsNone(self.parser.analyze(text, 0), text)

	def test_all_unicode_delimiters_preserve_completed_objects_without_crossing(self):
		from tests.test_boundaries import boundary_characters

		for boundary in boundary_characters():
			for text, _target, reading in POSITIVE[:2] + POSITIVE[6:7]:
				value = "😀" + text + boundary
				self.assertEqual(reading, self.rules.resolve(value)[1].reading_id, repr(value))
			if boundary not in syntax._SPACES:
				self.assertIsNone(self.parser.analyze("量小名" + boundary + "的身高", 0), repr(boundary))

	def test_sequence_commands_spelling_and_item_boundaries(self):
		class CharacterMode:
			def __init__(self, state):
				self.state = state

		pipe = load("pipeline")
		normalizer = pipe.SpeechSequenceNormalizer(rules=self.rules, character_mode_command_type=CharacterMode)
		options = pipe.RuntimeOptions()
		marker = object()
		sequence = ["量小名的", marker, "身高", "盛", "红豆粥"]
		self.assertEqual(sequence, normalizer.normalize(iter(sequence), options=options))
		sequence = [CharacterMode(True), "盛红豆粥", CharacterMode(False), "量小名的身高"]
		result = normalizer.normalize(iter(sequence), options=options)
		self.assertEqual("盛红豆粥", result[1])
		self.assertEqual("梁小名的身高", result[3])
		self.assertIs(sequence[0], result[0])
		self.assertIs(sequence[2], result[2])

	def test_no_io_and_no_cross_call_document_cache(self):
		with (
			mock.patch("builtins.open", side_effect=AssertionError("hot path I/O")),
			mock.patch.object(Path, "open", side_effect=AssertionError("hot path I/O")),
		):
			for _ in range(10):
				self.assertEqual("呈红豆粥", self.rules.transform("盛红豆粥"))
				self.assertEqual("呈装液体", self.rules.transform("盛装液体"))
				self.assertEqual("梁小名的身高", self.rules.transform("量小名的身高"))
				self.assertEqual("量小名的", self.rules.transform("量小名的"))
				self.assertEqual("身高", self.rules.transform("身高"))
		self.assertEqual({"lexicon", "frames", "triggers", "buckets", "morphologies"}, set(vars(self.parser)))

	def test_food_sememes_do_not_treat_restaurants_trees_or_ambiguous_brands_as_food(self):
		from tools.build_syntax_data import food_sense

		self.assertTrue(food_sense("{food|食品}"))
		self.assertTrue(food_sense("{part|部件:whole={vegetable|蔬菜},{eat|吃:patient={~}}}"))
		for kdml in (
			"{place|地方:domain={food|食品}}",
			"{tree|树:{reproduce|生殖:PatientProduct={fruit|水果}}}",
			"malformed",
		):
			self.assertFalse(food_sense(kdml))
		words = self.parser.lexicon.words
		self.assertTrue(words["豆角"] & syntax.FOOD)
		self.assertTrue(words["苹果"] & syntax.POSSIBLE_FOOD)
		self.assertFalse(words["苹果"] & syntax.FOOD)
		with self.assertRaises(TypeError):
			words["假词"] = syntax.FOOD

	def test_reproducible_data_and_executable_pickle_rejection(self):
		from tools.build_syntax_data import OUTPUT, DataOnlyUnpickler, generate

		self.assertEqual(OUTPUT.read_bytes(), generate())
		self.assertEqual({"rows": ["豆角"]}, DataOnlyUnpickler(io.BytesIO(pickle.dumps({"rows": ["豆角"]}))).load())
		with self.assertRaises(ValueError):
			DataOnlyUnpickler(io.BytesIO(b"cbuiltins\neval\n.")).load()
		data = json.loads(OUTPUT.read_bytes())
		self.assertEqual(117464, data["counts"]["words"])
		self.assertEqual(2760, data["counts"]["unanimousFoodHeads"])

	def test_frame_conflicts_abstain_in_both_orders(self):
		frame = self.parser.frames[0]
		other = replace(frame, id="conflicting-test-frame", reading="sheng4")
		for frames in ((frame, other), (other, frame)):
			parser = syntax.ArgumentParser(self.parser.lexicon, frames)
			self.assertIsNone(parser.analyze("盛豆角", 0))

	def test_head_tail_optimization_never_changes_a_successful_parse(self):
		# The tail prefilter is necessary, not evidence. A reference with every
		# Han character admitted must make the same decisions.
		lexicon = syntax.SyntaxLexicon(dict(self.parser.lexicon.words), self.parser.lexicon.head_classes)
		lexicon.head_tails = {name: frozenset(chr(c) for c in range(0x3400, 0xA000)) for name in lexicon.head_classes}
		reference = syntax.ArgumentParser(lexicon, self.parser.frames)
		for text in [*(t for t, _, _ in POSITIVE), *NEGATIVE, "盛" * 50, "量" * 50, "系" * 50]:
			for i, ch in enumerate(text):
				if ch in self.parser.triggers:
					self.assertEqual(reference.analyze(text, i), self.parser.analyze(text, i), text)

	def test_completed_object_is_not_lost_when_following_predicate_is_long(self):
		for text, _target, reading in POSITIVE[:2] + POSITIVE[6:7]:
			for suffix in ("很好", "很好" * 1000, "的时候", "的时候很好" * 1000):
				value = text + suffix
				self.assertEqual(reading, self.rules.resolve(value)[0].reading_id, value[:60])

	def test_first_last_template_index_is_exactly_equivalent_to_original_regex(self):
		compiled = self.rules.templates
		samples = set(t for t, _, _ in POSITIVE) | set(NEGATIVE)
		for entries in compiled.buckets.values():
			for entry in entries:
				samples.update(entry.positive)
				samples.update(entry.negative)
		for original in samples:
			for text in (original, "😀" + original + "$", original.replace("一", "１２")):
				for index, ch in enumerate(text):
					if ch not in compiled.triggers:
						continue
					matches = []
					for entry in compiled.buckets[ch]:
						plain = bool(
							entry.left.search(text[max(0, index - 65) : index])
							and entry.right.match(text[index + 1 : index + 66])
						)
						self.assertEqual(plain, entry.matches(text, index), (entry.id, text))
						if plain:
							matches.append(entry)
					if not matches:
						self.assertIsNone(compiled.decision(text, index))
					else:
						priority = max((e.user, e.priority) for e in matches)
						best = [e for e in matches if (e.user, e.priority) == priority]
						expected = (
							(None, "template_conflict", priority[0])
							if len({e.reading for e in best}) != 1
							else (best[0].reading, best[0].id, best[0].user)
						)
						self.assertEqual(expected, compiled.decision(text, index))
