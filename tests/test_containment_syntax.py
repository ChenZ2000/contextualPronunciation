"""Independent containment oracles: readings AND argument/relative attachment.

Generated combinations exercise a reviewed local grammar, not a representative
corpus or a claim of open-domain semantic accuracy.
"""

from __future__ import annotations

import copy
import itertools
import json
import unittest

from tests.core_loader import PLUGIN_PATH, load

syntax = load("syntax")
rules_module = load("rules")
HEADS = (
	"液体",
	"食物",
	"食品",
	"饮品",
	"酒精",
	"废水",
	"废液",
	"污泥",
	"化学品",
	"药品",
	"燃料",
	"气体",
	"粉末",
	"颗粒",
	"沙子",
	"物料",
	"货物",
	"物品",
	"装饰品",
	"红豆粥",
)
EXAMPLES = (
	"盛液体",
	"盛装液体",
	"盛装食物",
	"盛装液体的容器",
	"盛装液体的试管",
	"盛装了酒精",
	"盛了半瓶透明液体",
	"盛装三桶透明液体",
	"盛装腐蚀性液体",
	"盛装液态化学品",
	"盛装小名准备的液体",
	"盛装某公司生产的液体",
	"盛有液体",
	"盛装有液体的容器",
	"盛装的液体",
	"盛好的液体",
	"盛装饰品",
	"盛好看的红豆粥",
	"盛不了这么多液体",
	"盛不下三升液体",
	"盛裝液體",
	"盛裝液體的容器",
	"盛了固体颗粒",
	"盛装液体燃料",
)
NEGATIVES = (
	"盛装",
	"盛装出席",
	"盛装出席典礼",
	"盛装打扮",
	"盛装的样子",
	"身穿盛装",
	"她身穿盛装衣料昂贵",
	"穿上盛装衣服很华丽",
	"盛裝出席",
	"盛装液体公司的代表",
	"盛液体公司的代表",
	"盛豆角公司的产品",
	"盛红豆粥公司的产品",
	"盛红豆粥的价格",
	"盛装液体的价格",
	"盛装液体包装设备",
	"盛先生的液体",
	"盛大的宴会",
	"旺盛的食欲",
	"茂盛的豆角",
	"盛开在液体旁边的花",
	"盛未知液体",
	"盛龘靐液体",
)


class ContainmentSyntaxTests(unittest.TestCase):
	@classmethod
	def setUpClass(cls):
		cls.rules = rules_module.load_default_rules(extended=False)
		cls.parser = cls.rules.syntax

	def test_both_dictionary_modes_and_original_input_offsets(self):
		for extended in (False, True):
			rules = rules_module.load_default_rules(extended=extended)
			for phrase in EXAMPLES:
				for prefix, suffix in (("", ""), ("😀请用容器", "之后继续"), ("", "很好")):
					text = prefix + phrase + suffix
					i = text.index("盛")
					self.assertEqual("cheng2", rules.resolve(text)[i].reading_id, (text, extended))
					self.assertEqual("呈", rules.transform(text)[i], (text, extended))
					annotation = next(a for a in load("braille_readings").annotate(text, rules) if a.start == i)
					self.assertEqual(("cheng2", i + int(bool(prefix))), (annotation.reading, annotation.utf16_start))

	def test_noun_class_cross_product_not_sentence_enumeration(self):
		for verb, aspect, head in itertools.product(("盛", "盛装"), ("", "了", "过", "着", "有", "不了"), HEADS):
			text = verb + aspect + head
			decision = self.rules.resolve(text).get(0)
			self.assertIsNotNone(decision, text)
			self.assertEqual("cheng2", decision.reading_id, text)
			# A noun somewhere inside a company name is not the argument head.
			self.assertIsNone(self.parser.analyze(text + "公司的代表", 0), text)

	def test_attire_abstract_and_unknown_arguments_preserved(self):
		for extended in (False, True):
			rules = rules_module.load_default_rules(extended=extended)
			for text in NEGATIVES:
				self.assertEqual("盛", rules.transform(text)[text.index("盛")], (text, extended))

	def test_semantic_object_head_is_not_the_relative_container(self):
		for text, obj, outer in (
			("😀盛装液体的容器", "液体", "容器"),
			("盛装有液体的试管", "液体", "试管"),
			("盛小名的液体的容器", "小名的液体", "容器"),
			("量小名的身高的尺子", "小名的身高", "尺子"),
		):
			i = 1 if text.startswith("😀") else 0
			proposal = self.parser.analyze(text, i)
			self.assertIsNotNone(proposal, text)
			self.assertEqual(obj, text[proposal.object_start : proposal.object_end])
			acl = next(d for d in proposal.dependencies if d.relation == "acl" and d.start == i)
			self.assertEqual(text.index(outer), acl.head)
			self.assertEqual(text.index(outer), acl.end)
			self.assertEqual("transitive", proposal.construction)

	def test_object_gap_relative_does_not_invent_an_overt_object(self):
		for text in ("盛装的液体", "盛好的液体", "盛的液体", "量过的身高", "系好的鞋带"):
			proposal = self.parser.analyze(text, 0)
			self.assertIsNotNone(proposal, text)
			self.assertEqual("object-relative", proposal.construction)
			self.assertFalse(any(d.relation == "obj" for d in proposal.dependencies))
			acl = next(d for d in proposal.dependencies if d.relation == "acl")
			self.assertEqual((proposal.head_start, 0, text.index("的") + 1), (acl.head, acl.start, acl.end))

	def test_morphology_does_not_split_nouns_and_quantifiers_do_not_become_heads(self):
		for text, expected_object, expected_head in (
			("盛装饰品", "装饰品", "装饰品"),
			("盛好看的衣服", "好看的衣服", "衣服"),
			("盛有液体", "液体", "液体"),
			("盛装有液体", "液体", "液体"),
			("盛过气体", "气体", "气体"),
			("盛了半瓶透明液体", "半瓶透明液体", "液体"),
			("盛装三桶透明液体", "三桶透明液体", "液体"),
			("量三位孩子的身高", "三位孩子的身高", "身高"),
		):
			proposal = self.parser.analyze(text, 0)
			self.assertIsNotNone(proposal, text)
			self.assertEqual(expected_object, text[proposal.object_start : proposal.object_end])
			self.assertEqual(expected_head, text[proposal.head_start : proposal.head_end])

	def test_precise_user_protection_and_disabled_rules_still_win(self):
		for kwargs in (
			{"custom_entries": "盛装液体|盛|keep"},
			{"custom_templates": "[盛:keep]装液体"},
			{"disabled_rules": "syntax-serving-object"},
			{"disabled_rules": "sheng-protection"},
		):
			rules = rules_module.load_default_rules(extended=False, **kwargs)
			self.assertEqual("盛装液体", rules.transform("盛装液体"), kwargs)
		rules = rules_module.load_default_rules(extended=False, custom_entries="盛装液体|盛|sheng4")
		self.assertEqual("sheng4", rules.resolve("盛装液体")[0].reading_id)

	def test_conditional_protection_is_explicit_and_cannot_be_injected_as_a_reading(self):
		original = json.loads((PLUGIN_PATH / "data/rules_zh_CN.json").read_bytes())
		# Only explicitly reviewed core keep entries may yield to syntax.
		for mutate in ("unknown phrase", "non-list", "positive"):
			data = copy.deepcopy(original)
			group = next(g for g in data["characters"]["盛"]["phraseGroups"] if g["id"] == "sheng-protection")
			if mutate == "unknown phrase":
				group["contextualPhrases"] = ["非既有保护词"]
			elif mutate == "non-list":
				group["contextualPhrases"] = "盛装"
			else:
				group["protect"] = False
				group["reading"] = "cheng2"
			with self.assertRaises(rules_module.RuleDataError):
				rules_module.CompiledRules.from_mapping(data)

	def test_taxonomy_inheritance_does_not_flatten_semantic_roles(self):
		from tools.build_syntax_data import container_sense, contents_sense, descendants, food_sense

		self.assertEqual(
			frozenset(("a", "b", "c")),
			descendants("a hyponym b\nb hyponym c\nc hyponym a\na related d\ne hypernym a", {"a"}),
		)
		for definition in ("{edible|食物}", "{food|食品}", "{drinks|饮品}"):
			self.assertTrue(food_sense(definition), definition)
		for definition in ("{liquid|液}", "{gas|气}", "{chemical|化学物}"):
			self.assertTrue(contents_sense(definition), definition)
		for definition in (
			"{place|地方:domain={liquid|液}}",
			"{human|人:domain={chemical|化学物}}",
			"{artifact|人工物}",
			"{information|信息:domain={food|食品}}",
			"malformed",
		):
			self.assertFalse(contents_sense(definition), definition)
		self.assertTrue(container_sense("{tool|用具:{store|保存:location={~}}}"))
		words = self.parser.lexicon.words
		self.assertTrue(words["食物"] & syntax.FOOD)
		self.assertTrue(words["液体"] & syntax.CONTENTS)
		self.assertFalse(words["产品"] & (syntax.FOOD | syntax.CONTENTS))
		self.assertTrue(words["材料"] & syntax.POSSIBLE_CONTENTS)
		self.assertFalse(words["材料"] & syntax.CONTENTS)

	def test_compiled_morphology_index_matches_exhaustive_alternatives(self):
		reference = syntax.ArgumentParser(self.parser.lexicon, self.parser.frames)
		reference.morphologies = {f.id: {"": f.prefixes} for f in reference.frames}
		samples = [*EXAMPLES, *NEGATIVES, "盛过气体", "盛" * 50, "量小名的身高", "系小名的鞋带"]
		for verb, aspect, head in itertools.product(("盛", "盛装"), ("", "了", "过", "着", "有", "不了"), HEADS):
			samples.extend((verb + aspect + head, verb + aspect + head + "公司的代表"))
		for text in samples:
			self.assertEqual(reference.analyze(text, 0), self.parser.analyze(text, 0), text)

	def test_symbols_and_speech_items_do_not_cancel_or_create_containment(self):
		from tests.test_boundaries import boundary_characters

		for boundary in boundary_characters():
			for phrase in ("盛液体", "盛装液体", "盛装液体的容器"):
				text = "😀" + phrase + boundary
				self.assertEqual("cheng2", self.rules.resolve(text)[1].reading_id, repr(text))
			if boundary not in syntax._SPACES:
				self.assertIsNone(self.parser.analyze("盛装" + boundary + "液体", 0), repr(boundary))
		pipe = load("pipeline")
		normalizer = pipe.SpeechSequenceNormalizer(rules=self.rules, character_mode_command_type=type(None))
		marker = object()
		sequence = ["盛装", marker, "液体", "盛装液体"]
		self.assertEqual(
			["盛装", marker, "液体", "呈装液体"], normalizer.normalize(sequence, options=pipe.RuntimeOptions())
		)
		self.assertEqual(["盛装", marker, "液体", "盛装液体"], sequence)
