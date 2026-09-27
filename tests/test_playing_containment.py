"""New argument frames must respect attachment, overrides and parser budgets."""

from __future__ import annotations

import itertools
import unittest

from tests.core_loader import load


class PlayingAndContainmentTests(unittest.TestCase):
	@classmethod
	def setUpClass(cls):
		cls.rules = load("rules").load_default_rules()

	def assertReading(self, text, target, reading):  # noqa: N802
		i = text.index(target)
		decision = self.rules.resolve(text).get(i)
		self.assertIsNotNone(decision, text)
		self.assertEqual(reading, decision.reading_id, text)
		self.assertEqual(self.rules.renderings[reading], self.rules.transform(text)[i], text)
		annotation = next(a for a in load("braille_readings").annotate(text, self.rules) if a.start == i)
		self.assertEqual(reading, annotation.reading, text)

	def test_instrument_objects_accept_quantities_possessors_and_nested_modifiers(self):
		for verb, aspect, noun in itertools.product(
			("弹", "彈"), ("", "了", "过", "着"), ("琴", "钢琴", "鋼琴", "古琴", "琵琶", "吉他")
		):
			for modifier in ("这架", "12架", "三百架", "小明的", "小明昨天买的那架", "两位大师制作的"):
				text = "😀孩子正在" + verb + aspect + modifier + noun
				with self.subTest(text=text):
					self.assertReading(text, verb, "tan2")
		for text in (
			"弹了123遍琴",
			"弹了一下午的琴",
			"弹了两小时琴",
			"弹那个摆在客厅角落里的钢琴",
			"弹又新又漂亮的琴",
			"弹呀弹小明的琴",
			"把小明昨天买的那架钢琴再弹一下",
		):
			with self.subTest(text=text):
				self.assertReading(text, "弹", "tan2")

	def test_instrument_mention_does_not_imply_object_attachment(self):
		for text in (
			"子弹击中了钢琴",
			"弹药放在钢琴上",
			"炮弹落在琴旁",
			"弹钢琴公司的招牌",
			"弹小明的琴盒",
			"弹完以后他搬走了琴",
			"弹未知琴",
			"弹龘靐琴",
			"弹，琴在那边",
		):
			with self.subTest(text=text):
				p = self.rules.syntax.analyze(text, text.index("弹"))
				self.assertIsNone(p, text)
		for text in ("子弹击中了钢琴", "弹药放在钢琴上", "炮弹落在琴旁"):
			self.assertEqual("弹", self.rules.transform(text)[text.index("弹")])

	def test_containment_default_event_nominal_and_container_goal(self):
		for text in ("装盛", "裝盛", "装盛动作", "裝盛的動作", "装盛到容器里", "装盛东西", "装盛大米", "装盛大量液体"):
			self.assertReading(text, "盛", "cheng2")
		for text in (
			"盛装动作",
			"盛裝動作",
			"盛装的动作很熟练",
			"盛装这个动作",
			"盛装到容器里",
			"盛装在小明买的碗里",
			"盛装进那三个新容器里",
			"盛装的容器",
			"盛装东西",
			"盛装了三桶液体",
			"盛装了的动作",
			"盛装在試管內",
		):
			with self.subTest(text=text):
				self.assertReading(text, "盛", "cheng2")
		goal = self.rules.syntax.analyze("盛装在小明买的碗里", 0)
		self.assertEqual("container-goal", goal.construction)
		self.assertTrue(any(d.relation == "obl:goal" for d in goal.dependencies))

	def test_attire_and_unrelated_heads_remain_protected(self):
		for text in (
			"盛装出席",
			"盛装赴会",
			"身穿盛装的动作",
			"穿上盛装的动作",
			"盛装动作公司的代表",
			"盛装到容器公司的总部",
			"盛装到未知容器里",
			"盛装的样子",
			"服装盛行",
			"盛装，动作很慢",
		):
			with self.subTest(text=text):
				self.assertEqual("盛", self.rules.transform(text)[text.index("盛")])

	def test_user_overrides_disabled_frames_and_work_limits(self):
		for text, target, rule in (
			("弹小明的琴", "弹", "syntax-played-instrument"),
			("盛装动作", "盛", "syntax-serving-object"),
		):
			rules = load("rules").load_default_rules(custom_entries=f"{text}|{target}|keep")
			self.assertEqual(text, rules.transform(text))
			rules = load("rules").load_default_rules(disabled_rules=rule)
			self.assertEqual(text, rules.transform(text))
			context = self.rules.syntax.context(text)
			context.remaining_work = 0
			self.assertIsNone(self.rules.syntax.analyze(text, 0, context))
		self.assertIsNone(self.rules.syntax.analyze("弹" + "刚买的" * 300 + "琴", 0))


if __name__ == "__main__":
	unittest.main()
