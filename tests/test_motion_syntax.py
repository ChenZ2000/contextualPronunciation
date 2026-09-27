"""Sentence-level motion contrasts, including unseen heads and distractors."""

from __future__ import annotations

import json
import unittest

from tests.core_loader import load


class MotionSyntaxTests(unittest.TestCase):
	@classmethod
	def setUpClass(cls):
		cls.rules = load("rules").load_default_rules()

	def assert_motion(self, text):
		decisions = self.rules.resolve(text)
		rendered = self.rules.transform(text)
		for index, ch in enumerate(text):
			if ch in "转轉":
				self.assertIn(index, decisions, text)
				self.assertEqual("zhuan4", decisions[index].reading_id, text)
				self.assertTrue(decisions[index].rule_id.startswith("syntax-motion-"), text)
				self.assertEqual("篆", rendered[index], text)

	def test_productive_location_heads_and_reduplication(self):
		# The parser never receives this test vocabulary as sentence rules.
		for place in ("公园", "博物馆", "咖啡馆", "图书馆", "医院", "小区", "超市", "楼下", "家"):
			for form in ("转", "转转", "转一转", "转了转"):
				with self.subTest(place=place, form=form):
					self.assert_motion(f"我们去{place}{form}")

	def test_modifiers_quantifiers_negation_and_serial_motion(self):
		for text in (
			"出去转一转",
			"今天出去转转",
			"我想出去随便转一转",
			"不想出去转转",
			"出门转转",
			"下楼转转",
			"上街转一转",
			"他想去转一转",
			"让他出去转转",
			"让他到公园转转",
			"他想去刚开放的博物馆慢慢转一转",
			"请陪孩子去附近新建的公园转一转",
			"我们去两家新开的商场转转",
			"去公园随意地转一转",
			"去公园里新开的咖啡馆转转",
			"请到小区转一转",
			"我们去公园转转吧",
			"去公园转一转就回来",
			"在公园转了两个小时",
			"虽然车轮坏了，但是我们还想出去转一转",
			"文件已经处理好了。出去转转",
		):
			with self.subTest(text=text):
				self.assert_motion(text)

	def test_argument_heads_override_incidental_nouns(self):
		for text in (
			"让车轮转一转",
			"让刚修好的车轮转一转",
			"转一转刚修好的车轮",
			"把文件旁边的车轮转转",
			"车轮还在转",
			"屋里的风扇还在转",
			"机器卡住不能转",
			"卡住不能转",
			"卡住无法转",
			"我转了转车轮",
			"请让已经检查过轴承而且刚换过轮胎的车轮转一转",
		):
			with self.subTest(text=text):
				self.assert_motion(text)

	def test_no_borrowed_location_or_rotor_evidence(self):
		for text in (
			"去公园的文件转转",
			"公园里的文件转一转",
			"去公园里那家公司的文件转转",
			"让车轮旁边的文件转转",
			"车轮旁边的文件不能转转",
			"文件卡住不能转",
			"去公园转转文件",
			"去公园把文件转转",
			"在公园把文件转出去",
			"车轮向左转一转",
			"车轮向右缓慢地转一转",
			"到公园门口向左转转",
			"车轮坏了文件不能转",
			"我们出去转移文件",
			"去公园转交文件",
			"去公园转了转账",
		):
			with self.subTest(text=text):
				self.assertNotIn("篆", self.rules.transform(text))
				self.assertFalse(any(d.rule_id.startswith("syntax-motion-") for d in self.rules.resolve(text).values()))

	def test_original_offset_dependencies_and_head_attachment(self):
		text = "请让文件旁边刚修好的车轮慢慢转一转"
		index = text.index("转")
		parsed = self.rules.syntax.analyze(text, index)
		self.assertIsNotNone(parsed)
		self.assertEqual("车轮", text[parsed.head_start : parsed.head_end])
		self.assertEqual("caused-rotation", parsed.construction)
		self.assertIn(("redup", index + 2, index + 3), [(d.relation, d.start, d.end) for d in parsed.dependencies])
		self.assertTrue(any(d.relation == "obj" and "文件" in text[d.start : d.end] for d in parsed.dependencies))
		for dep in parsed.dependencies:
			self.assertTrue(0 <= dep.head < len(text))
			self.assertTrue(0 <= dep.start < dep.end <= len(text))

	def test_traditional_and_user_overrides(self):
		for text in ("出去轉一轉", "去公園轉轉", "讓車輪轉一轉", "到商場轉轉"):
			self.assert_motion(text)
		rules = load("rules").load_default_rules(custom_entries="去公园转|转|keep")
		self.assertEqual("去公园转", rules.transform("去公园转"))
		rules = load("rules").load_default_rules(disabled_rules="syntax-motion-predicate")
		self.assertEqual("去公园转转", rules.transform("去公园转转"))

	def test_source_evidence_and_dense_budget(self):
		g = load("syntax")
		data = json.loads(g.Path(g.__file__).with_name("data").joinpath("grammar_lexicon.json").read_text("utf-8"))
		for name in ("placeNoun", "pathMotion"):
			self.assertEqual(set(data["selection"][name]), set(data["selectionEvidence"][name]))
			self.assertTrue(all(data["selectionEvidence"][name].values()))
		text = "转" * 8192
		self.assertEqual(text, self.rules.transform(text))
		context = self.rules.syntax.context("去公园转一转")
		context.remaining_work = 0
		self.assertIsNone(self.rules.syntax.analyze("去公园转一转", 3, context))

	def test_lexical_boundaries_and_speech_projection(self):
		for text in ("掉轉", "掉转", "好转", "逆转", "去公园转转", "转转", "转转文件"):
			full = self.rules.resolve(text)
			self.assertEqual({i: d for i, d in full.items() if d.speech}, self.rules.resolve(text, speech_only=True))
		for text in ("掉轉", "掉转", "好转", "逆转"):
			self.assertNotIn("篆", self.rules.transform(text))


if __name__ == "__main__":
	unittest.main()
