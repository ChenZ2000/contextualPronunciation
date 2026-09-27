"""Productive predicate groups, dictionary projections and reinstall defaults."""

import json
import unittest
from pathlib import Path

from tests.core_loader import load
from tools.build_grammar_data import projected_families, projection_rules


class ReiteratedPredicateTests(unittest.TestCase):
	@classmethod
	def setUpClass(cls):
		cls.rules = load("rules").load_default_rules()

	def assert_group(self, text, character, reading, start=0):
		decisions = self.rules.resolve(text)
		for index, ch in enumerate(text):
			if ch == character and index >= start:
				self.assertIn(index, decisions, text)
				self.assertEqual(reading, decisions[index].reading_id, text)
		return decisions

	def test_dictionary_families_generalize_across_productive_groups(self):
		for noun in (
			"螺丝",
			"螺丝刀",
			"引擎",
			"发电机",
			"电机",
			"螺栓",
			"螺母",
			"旋钮",
			"曲柄",
			"曲轴",
			"电钻",
			"钻头",
			"扳手",
			"十字螺丝刀",
			"套筒扳手",
			"内六角圆柱头螺钉",
			"心轴",
			"转椅",
		):
			for modal in ("", "能", "会", "不能"):
				for form in ("转", "转起来", "转不起来", "转呀转", "转啊转啊", "转着转着停了", "转了又转", "转了再转"):
					text = noun + modal + form
					with self.subTest(text=text):
						self.assert_group(text, "转", "zhuan4", len(noun))

	def test_closed_durative_and_traditional_forms(self):
		for text in ("转呀转", "转啊转啊", "转呀转呀转", "出去转呀转", "去公园转着转着", "螺丝刀转呀转起来"):
			self.assert_group(text, "转", "zhuan4")
		for text in ("螺絲刀轉呀轉", "發電機會轉", "電機轉著轉著", "轉呀轉"):
			self.assert_group(text, "轉", "zhuan4")

	def test_shared_arguments_transfer_direction_and_lexical_boundaries(self):
		for text in (
			"把螺丝刀转呀转给经理",
			"文件转呀转",
			"螺丝刀旁边的文件转了又转",
			"我转着转着给客户",
			"钱给他转呀转",
		):
			self.assert_group(text, "转", "zhuan3")
		for text in (
			"向左转呀转",
			"车轮向右转啊转",
			"转呀转账",
			"转呀转身",
			"转了又转交文件",
			"引擎说明书转呀转",
			"发电机厂会转",
			"螺丝刀包装箱会转",
		):
			with self.subTest(text=text):
				self.assertNotIn("篆", self.rules.transform(text))
		for text in (
			"让文件旁边的螺丝刀转呀转",
			"转呀转车轮",
			"那两个新装的螺母会转",
			"引擎和发电机会转",
			"螺丝刀转呀转给大家看",
		):
			with self.subTest(text=text):
				self.assert_group(text, "转", "zhuan4")

	def test_shared_morphology_applies_to_other_typed_verbs(self):
		for character, reading, obj in (("盛", "cheng2", "红豆粥"), ("量", "liang2", "身高"), ("系", "ji4", "鞋带")):
			for link in ("呀", "啊", "着", "了又", "了再"):
				text = character + link + character + obj
				with self.subTest(text=text):
					self.assert_group(text, character, reading)
		for text in ("盛呀盛会", "量呀量子", "系呀系主任", "盛呀盛红豆粥公司的产品"):
			self.assertIsNone(self.rules.resolve(text).get(0), text)

	def test_projection_uses_nominal_heads_and_retains_record_ids(self):
		rules = projection_rules()
		for gloss in (
			"engine (loanword)",
			"electricity generator",
			"Phillips screwdriver (with a cross-shaped tip)",
			"nut (female component of nut and bolt)",
		):
			self.assertTrue(projected_families([gloss], rules), gloss)
		for gloss in (
			"wheel factory",
			"search engine",
			"thread of screw",
			"screwdriver (cocktail)",
			"to screw",
			"nut",
			"drill; exercise",
			"crank; crackpot",
		):
			self.assertFalse(projected_families([gloss], rules), gloss)
		data = json.loads(
			Path("addon/globalPlugins/contextualPronunciation/data/grammar_lexicon.json").read_text("utf-8")
		)
		families = data["semanticProjection"]["families"]
		for family, noun in (
			("rotary-power", "引擎"),
			("rotary-power", "发电机"),
			("threaded-fastener", "螺丝"),
			("rotary-tool", "螺丝刀"),
			("rotating-part-control", "旋钮"),
		):
			self.assertTrue(families[family][noun])
			self.assertLessEqual(set(families[family][noun]), set(data["selectionEvidence"]["rotorNoun"][noun]))

	def test_original_offsets_budget_overrides_and_projection(self):
		text = "让新装的螺丝刀转呀转呀转"
		indices = [i for i, ch in enumerate(text) if ch == "转"]
		for index in indices:
			parsed = self.rules.syntax.analyze(text, index)
			self.assertEqual(index, parsed.target)
			self.assertEqual("螺丝刀", text[parsed.head_start : parsed.head_end])
			self.assertEqual(set(indices[1:]), {d.start for d in parsed.dependencies if d.relation == "redup"})
			for dep in parsed.dependencies:
				self.assertTrue(0 <= dep.start < dep.end <= len(text))
		for sentence in (text, "把螺丝刀转呀转给经理", "盛呀盛红豆粥"):
			full = self.rules.resolve(sentence)
			self.assertEqual(
				{i: d for i, d in full.items() if d.speech}, self.rules.resolve(sentence, speech_only=True)
			)
		context = self.rules.syntax.context(text)
		context.remaining_work = 0
		self.assertIsNone(self.rules.syntax.analyze(text, indices[0], context))
		self.assertNotIn("篆", self.rules.transform("转呀" * 4096))
		for text in ("转呀转", "盛呀盛红豆粥"):
			r = load("rules").load_default_rules(custom_entries=f"{text[:2]}|{text[0]}|keep")
			self.assertEqual(text[0], r.transform(text)[0])
			self.assertNotEqual(text[2], r.transform(text)[2])
		r = load("rules").load_default_rules(disabled_rules="syntax-motion-predicate")
		self.assertEqual("螺丝刀转呀转", r.transform("螺丝刀转呀转"))

	def test_reinstall_default_and_heavy_equipment_protections(self):
		for text in (
			"重装",
			"重裝",
			"需要重装吗",
			"电脑重装后恢复了",
			"卸载后重装插件",
			"重装驱动",
			"一键重装",
			"重装了三次",
		):
			self.assert_group(text, "重", "chong2")
			self.assertIn("崇", self.rules.transform(text))
		for text in ("重装步兵", "重裝騎兵", "重装部队", "重裝上陣", "重装甲", "重装徒步", "尊重装修工人"):
			self.assertEqual(text, self.rules.transform(text))
		for options in ({"custom_entries": "重装|重|keep"}, {"disabled_rules": "chong-reinstall-default"}):
			r = load("rules").load_default_rules(**options)
			self.assertEqual("重装", r.transform("重装"))
