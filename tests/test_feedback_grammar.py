"""Structural regressions for quantity selection and nominal-role evidence."""

from __future__ import annotations

import unittest
from unittest import mock

from tests.core_loader import load


class FeedbackGrammarTests(unittest.TestCase):
	@classmethod
	def setUpClass(cls):
		cls.rules = load("rules").load_default_rules(extended=False)
		cls.g = load("syntax")

	def test_every_target_in_the_original_feedback(self):
		text = "重吸收，盛了一碗饭，重捏，重飞，虾兵和蟹将，天兵和天将"
		expected = {"重": "chong2", "盛": "cheng2", "将": "jiang4"}
		decisions = self.rules.resolve(text)
		for i, c in enumerate(text):
			if c in expected:
				self.assertEqual(expected[c], decisions[i].reading_id)
		self.assertEqual("崇吸收，呈了一碗饭，崇捏，崇飞，虾兵和蟹匠，天兵和天匠", self.rules.transform(text))

	def test_numeral_classifier_and_modifier_attach_to_the_actual_head(self):
		for quantity in ("一碗", "一大碗", "三小碗", "那两碗", "2碗", "２碗"):
			text = "😀盛了" + quantity + "刚煮好的饭"
			p = self.rules.syntax.analyze(text, 1)
			self.assertIsNotNone(p, text)
			self.assertEqual("饭", text[p.head_start : p.head_end])
			clf = next(d for d in p.dependencies if d.relation == "clf")
			self.assertEqual("碗", text[clf.start : clf.end])
			self.assertEqual(p.head_start, clf.head)
			self.assertTrue(any(d.relation == "nummod" and d.head == clf.head for d in p.dependencies))
			self.assertIsNone(self.rules.syntax.analyze(text + "的价格", 1))

	def test_classifiers_select_senses_instead_of_any_nearby_food_keyword(self):
		for clf in ("碗", "盆", "锅", "勺", "杯"):
			self.assertEqual("cheng2", self.rules.resolve("盛了一" + clf + "汤")[0].reading_id)
		for text in ("盛了一位老师的饭", "盛了买过一碗饭的老师", "盛了一碗饭的包装设计"):
			self.assertIsNone(self.rules.syntax.analyze(text, 0), text)

	def test_unknown_compounds_and_explicit_conflicting_readings_have_distinct_weight(self):
		g = self.g
		frame = self.rules.syntax.buckets["重"][0]
		for sources, hard, expected in ((3 << 12, False, "chong2"), (1 << 12, False, None), (3 << 12, True, None)):
			lex = g.SyntaxLexicon(
				{"编校": g.VERB},
				evidence={"编校": sources | g.VERB},
				repeat_blockers={"重编校": [0]} if hard else {},
				opaque_repeat_blockers={} if hard else {"重编校": [0]},
			)
			p = g.ArgumentParser(lex, (frame,)).analyze("重编校", 0)
			self.assertEqual(expected, p.reading if p else None)

	def test_parallel_noun_dependency_and_classifier_dependency(self):
		for text in ("虾兵和蟹将", "蟹将和虾兵", "士兵和守卫边关的将"):
			p = self.rules.syntax.analyze(text, text.index("将"))
			self.assertEqual("coordinated-nominal", p.construction)
			self.assertEqual("将", text[p.head_start : p.head_end])
			self.assertTrue(any(d.relation == "conj" for d in p.dependencies))
		text = "一员守卫边关的将"
		p = self.rules.syntax.analyze(text, text.index("将"))
		self.assertEqual("classified-nominal", p.construction)
		self.assertTrue(any(d.relation == "clf" and d.head == text.index("将") for d in p.dependencies))

	def test_nominal_role_does_not_cross_commands_punctuation_or_unknowns(self):
		for delimiter in ("，", "。", "\n", "😀", "\u200b"):
			text = "虾兵" + delimiter + "和蟹将"
			self.assertEqual(text, self.rules.transform(text))
		for text in ("士兵和龘靐将", "士兵和老师将离开", "老师将和士兵离开", "兵和蟹将军"):
			self.assertEqual(text, self.rules.transform(text))
		pipe = load("pipeline")
		n = pipe.SpeechSequenceNormalizer(rules=self.rules, character_mode_command_type=type("CharacterMode", (), {}))
		marker = object()
		seq = ["虾兵和蟹", marker, "将"]
		self.assertEqual(seq, n.normalize(seq, options=pipe.RuntimeOptions()))

	def test_keep_disable_and_annotation_use_the_same_nominal_decision(self):
		text = "😀虾兵和蟹将"
		for kwargs in ({"custom_entries": "蟹将|将|keep"}, {"disabled_rules": "syntax-general-nominal"}):
			r = load("rules").load_default_rules(extended=False, **kwargs)
			self.assertEqual(text, r.transform(text))
		a = next(a for a in load("braille_readings").annotate(text, self.rules) if a.character == "将")
		self.assertEqual("jiang4", a.reading)
		self.assertEqual(text.index("将") + 1, a.utf16_start)

	def test_nominal_work_budget_abstains_without_consuming_future_calls(self):
		text = "士兵和" + "孩子的" * 200 + "将"
		with mock.patch.object(self.g, "MAX_ITEM_WORK", 1):
			self.assertEqual(text, self.rules.transform(text))
		self.assertEqual("虾兵和蟹匠", self.rules.transform("虾兵和蟹将"))

	def test_elliptical_quantity_has_a_surface_head_and_no_invented_noun(self):
		text = "😀也给我盛了一大碗"
		p = self.rules.syntax.analyze(text, text.index("盛"))
		self.assertEqual("一大碗", text[p.object_start : p.object_end])
		self.assertEqual("碗", text[p.head_start : p.head_end])
		self.assertTrue(any(d.relation == "ellipsis" and d.head == p.head_start for d in p.dependencies))
		self.assertTrue(all(0 <= d.start < d.end <= len(text) for d in p.dependencies))
		self.assertEqual("😀也给我呈了一大碗", self.rules.transform(text))

	def test_adverb_segmentation_and_subject_predicate_dependencies(self):
		lex = self.rules.syntax.lexicon
		self.assertEqual(["训练有素", "的", "士兵"], [t.text for t in lex.tokenize("训练有素的士兵", 0)])
		self.assertIn("的士", [t.text for t in lex.tokenize("我坐的士回家", 0)])
		for subject in ("天兵和天将", "蟹将和虾兵"):
			text = subject + "一起去吃饭"
			words = [t.text for t in self.rules.syntax.lexicon.tokenize(text, 0)]
			self.assertIn("一起", words)
			p = self.rules.syntax.analyze(text, text.index("将"))
			subj = next(d for d in p.dependencies if d.relation == "nsubj")
			self.assertEqual(subject, text[subj.start : subj.end])
			self.assertEqual("去", text[subj.head])
			adv = next(d for d in p.dependencies if d.relation == "advmod")
			self.assertEqual("一起", text[adv.start : adv.end])
			self.assertEqual(subj.head, adv.head)

	def test_compound_evidence_is_required_for_a_competing_future_parse(self):
		g = self.g
		original = self.rules.syntax.lexicon
		without = g.SyntaxLexicon(dict(original.words), general_nouns=())
		parser = g.ArgumentParser(without, self.rules.syntax.frames)
		self.assertIsNone(parser.analyze("天兵和天将一起去吃饭", 4))
		self.assertIsNotNone(self.rules.syntax.analyze("天兵和天将一起去吃饭", 4))

	def test_new_structures_respect_speech_command_boundaries_and_preferences(self):
		pipe = load("pipeline")
		n = pipe.SpeechSequenceNormalizer(rules=self.rules, character_mode_command_type=type("CharacterMode", (), {}))
		marker = object()
		for seq in (["也给我盛了", marker, "一碗"], ["天兵和天", marker, "将一起去吃饭"]):
			self.assertEqual(seq, n.normalize(seq, options=pipe.RuntimeOptions()))
		for text, entry in (("也给我盛了一碗", "盛了|盛|keep"), ("天兵和天将一起去吃饭", "天将|将|keep")):
			r = load("rules").load_default_rules(extended=False, custom_entries=entry)
			self.assertEqual(text, r.transform(text))

	def test_modal_overlap_uses_structure_without_overriding_user_keep(self):
		for extended in (False, True):
			r = load("rules").load_default_rules(extended=extended)
			for text in ("天兵和天将要去吃饭", "天兵和天将会一起出发", "蟹将和虾兵会一起出发"):
				i = text.index("将")
				self.assertEqual("jiang4", r.resolve(text)[i].reading_id)
				self.assertEqual(r.resolve(text)[i], r.resolve(text, speech_only=True)[i])
			for text in ("士兵和老师将要去吃饭", "老师将会一起出发", "士兵和老师的将来", "天兵和天将军"):
				self.assertEqual(text[text.index("将")], r.transform(text)[text.index("将")])
			for kwargs in ({"custom_entries": "将要|将|keep"}, {"disabled_rules": "syntax-general-nominal"}):
				kept = load("rules").load_default_rules(extended=extended, **kwargs)
				text = "天兵和天将要去吃饭"
				self.assertEqual(text, kept.transform(text))
