"""Contrastive event frames: morphology, argument head, recipient and ellipsis."""

from __future__ import annotations

import json
import unittest
from unittest import mock

from tests.core_loader import load


class EventRoleTests(unittest.TestCase):
	@classmethod
	def setUpClass(cls):
		cls.rules = load("rules").load_default_rules()
		cls.g = load("syntax")

	def assert_reading(self, text, reading, index=None):
		index = max(text.rfind("转"), text.rfind("轉")) if index is None else index
		decision = self.rules.resolve(text).get(index)
		self.assertIsNotNone(decision, text)
		self.assertEqual(reading, decision.reading_id, text)
		self.assertEqual("篆" if reading == "zhuan4" else text[index], self.rules.transform(text)[index], text)
		full = self.rules.resolve(text)
		self.assertEqual({i: d for i, d in full.items() if d.speech}, self.rules.resolve(text, speech_only=True), text)
		return self.rules.syntax.analyze(text, index)

	def test_reported_rotation_and_transfer_contrasts(self):
		for text in ("让风车转起来", "风车会转", "汽轮机会转", "发动机转起来了", "轴承能转起来吗"):
			with self.subTest(text=text):
				self.assert_reading(text, "zhuan4")
		for text in ("邮件能转给经理吗", "附件能给他转吗", "钱给他转了吗", "我转了好多给客户"):
			with self.subTest(text=text):
				self.assert_reading(text, "zhuan3")

	def test_dictionary_heads_generalize_across_modal_and_complement_forms(self):
		# Neither these sentences nor these combinations are runtime entries.
		for noun in ("风车", "汽轮机", "涡轮", "电动机", "柴油机", "叶轮", "螺旋桨", "离心机", "转子", "陀螺仪"):
			for modal in ("", "能", "会", "可以", "不能", "不会"):
				for tail in ("", "起来", "起来了", "不起来", "得起来", "不动"):
					text = f"{noun}{modal}转{tail}吗"
					with self.subTest(text=text):
						self.assert_reading(text, "zhuan4")

	def test_theme_heads_recipients_and_indefinite_quantity_ellipsis(self):
		for theme in ("邮件", "附件", "文件", "钱", "资金", "数据", "资料", "文档"):
			for text in (f"{theme}能给他转吗", f"把{theme}给客户转一下", f"我给经理转了{theme}", f"{theme}转不出去"):
				with self.subTest(text=text):
					self.assert_reading(text, "zhuan3")
		for quantity in ("好多", "很多", "不少", "一些", "少量", "若干", "两个"):
			with self.subTest(quantity=quantity):
				p = self.assert_reading(f"我转了{quantity}给客户", "zhuan3")
				self.assertTrue(any(d.relation == "obj:ellipsis" for d in p.dependencies))
		for text in ("我给他转了好多钱", "我给他转了很多钱吗", "我转了两份文件给客户"):
			with self.subTest(text=text):
				self.assert_reading(text, "zhuan3")

	def test_recipient_beneficiary_and_purpose_are_distinct(self):
		for text in ("把风车转给经理", "把车轮转了给客户", "车轮转给他", "去公园转了好多给客户"):
			with self.subTest(text=text):
				self.assert_reading(text, "zhuan3")
		for text in (
			"给我转一转车轮",
			"发动机转起来给大家看",
			"让风车转起来给客户看",
			"给他把车轮转起来",
			"车轮给我转起来",
			"转一转车轮给大家看",
		):
			with self.subTest(text=text):
				self.assert_reading(text, "zhuan4")

	def test_modifiers_never_borrow_their_heads_semantics(self):
		for text in (
			"邮件旁边的风车能转起来吗",
			"让刚修好的汽轮机慢慢转起来",
			"那两个新装的轴承会转吗",
			"虽然邮件已经发出，但是发动机还不能转起来",
		):
			with self.subTest(text=text):
				self.assert_reading(text, "zhuan4")
		for text in (
			"风车旁边的邮件能给他转吗",
			"发动机旁边的钱给他转了吗",
			"车轮给他的文件不能转起来",
			"汽轮机旁边的附件转不出去",
		):
			with self.subTest(text=text):
				self.assert_reading(text, "zhuan3")
		for text in (
			"风车旁边的桌子转起来",
			"汽轮机厂会转",
			"发动机说明书会转",
			"轴承包装箱能转起来吗",
			"车轮向左转起来",
			"车轮坏了邮件能转吗",
			"我转了快给客户",
			"我转了好多给客户旁边的机器",
			"飞机会转弯",
			"去公园转了转账",
		):
			with self.subTest(text=text):
				self.assertNotIn("篆", self.rules.transform(text))

	def test_original_role_offsets_and_preserved_reading_annotation(self):
		text = "附件能给他转起来吗"
		p = self.assert_reading(text, "zhuan3")
		roles = {(d.relation, text[d.start : d.end]) for d in p.dependencies}
		self.assertLessEqual(
			{("obj:topic", "附件"), ("obl:recipient", "他"), ("aux", "能"), ("compound:phase", "起来")}, roles
		)
		self.assertNotIn(("obl:beneficiary", "他"), roles)
		for sentence in (text, "我转了好多给客户", "轴承能转不起来吗", "发动机转起来给大家看"):
			p = self.rules.syntax.analyze(sentence, sentence.index("转"))
			for dep in p.dependencies:
				self.assertTrue(0 <= dep.head < len(sentence))
				self.assertTrue(0 <= dep.start < dep.end <= len(sentence))
		annotations = load("braille_readings").annotate("附件能给他转吗", self.rules)
		self.assertTrue(any(a.reading == "zhuan3" for a in annotations))

	def test_coordination_topicalization_and_temporal_clause_boundaries(self):
		for text in (
			"风车和汽轮机会转",
			"风车和刚修好的发动机会转起来",
			"车轮我转了转",
			"发动机转起来后我再把邮件转给经理",
		):
			with self.subTest(text=text):
				self.assert_reading(text, "zhuan4", text.index("转"))
		for text in ("钱我已经给他转了", "我给他转了很多", "我给他转了很多吗", "我把钱给他转了"):
			with self.subTest(text=text):
				self.assert_reading(text, "zhuan3")
		for text in ("风车和邮件会转", "邮件和风车能转起来吗", "发动机转后轮"):
			with self.subTest(text=text):
				self.assertNotIn("篆", self.rules.transform(text))

	def test_traditional_user_override_disabled_competing_frame_and_budget(self):
		for text in ("讓風車轉起來", "汽輪機會轉", "發動機轉起來了", "軸承能轉起來嗎"):
			self.assert_reading(text, "zhuan4")
		for text in ("附件能給他轉嗎", "錢給他轉了嗎", "我轉了好多給客戶"):
			self.assert_reading(text, "zhuan3")
		rules = load("rules").load_default_rules(custom_entries="风车转起来|转|keep")
		self.assertEqual("风车转起来", rules.transform("风车转起来"))
		rules = load("rules").load_default_rules(disabled_rules="syntax-transfer-predicate")
		self.assertNotIn("篆", rules.transform("把风车转了给客户"))
		rules = load("rules").load_default_rules(disabled_rules="syntax-motion-predicate")
		self.assertEqual("风车转起来", rules.transform("风车转起来"))
		context = self.rules.syntax.context("风车转起来")
		context.remaining_work = 0
		self.assertIsNone(self.rules.syntax.analyze("风车转起来", 2, context))
		# A true verb boundary is not a tokenizer budget truncation. Bounding
		# the original string must preserve both lexical decisions and offsets.
		for sentence in ("风车会转起来", "我想出去转转", "那两台新机器转起来", "一大圈转", "唱和转交"):
			stop = sentence.index("转")
			lexicon = self.rules.syntax.lexicon
			self.assertEqual(lexicon.tokenize(sentence[:stop], 0), lexicon.tokenize(sentence, 0, stop))

	def test_generated_semantic_classes_have_evidence_not_machine_substrings(self):
		data = json.loads(
			self.g.Path(self.g.__file__).with_name("data").joinpath("grammar_lexicon.json").read_text("utf-8")
		)
		for name in ("rotorNoun", "transferTheme", "indefiniteQuantity", "actionMeasure"):
			self.assertEqual(set(data["selection"][name]), set(data["selectionEvidence"][name]))
			self.assertTrue(all(data["selectionEvidence"][name].values()))
		self.assertLessEqual({"风车", "汽轮机", "离心机", "螺旋桨"}, set(data["selection"]["rotorNoun"]))
		self.assertTrue({"机壳", "机器厂", "飞机", "机器零件"}.isdisjoint(data["selection"]["rotorNoun"]))

	def test_event_extent_and_duration_do_not_become_transfer_theme_ellipsis(self):
		for extent in ("三次", "两遍", "三圈", "三天", "两个小时"):
			for text in (f"我转了{extent}给客户看", f"我给他转了{extent}"):
				with self.subTest(text=text):
					proposal = self.rules.syntax.analyze(text, text.index("转"))
					self.assertTrue(proposal is None or proposal.reading != "zhuan3")

	def test_closed_action_extent_rejects_before_building_a_prefix_chart(self):
		motion = load("motion")
		for prefix in ("请把文件重", "风车", "我给他", "引擎"):
			for quantity in ("一", "三", "5"):
				for unit in ("次", "遍", "圈"):
					text = prefix + "转" + quantity + unit
					with (
						self.subTest(text=text),
						mock.patch.object(motion, "_prefix", side_effect=AssertionError("unnecessary chart")),
					):
						self.assertIsNone(self.rules.syntax.analyze(text, text.index("转")))
		for text, reading in (
			("重转一次", "chong2"),
			("风车转了两天", "zhuan4"),
			("转一份文件给经理", "zhuan3"),
			("转一个螺丝", "zhuan4"),
		):
			index = 0 if text.startswith("重") else text.index("转")
			self.assertEqual(reading, self.rules.resolve(text)[index].reading_id)


if __name__ == "__main__":
	unittest.main()
