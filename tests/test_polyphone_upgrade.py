"""Regression examples for productive travel, night and rotation readings."""

from __future__ import annotations

import unittest

from tests.core_loader import load
from tests.test_global_plugin_integration import _load_plugin


class PolyphoneUpgradeTests(unittest.TestCase):
	@classmethod
	def setUpClass(cls):
		cls.rules = load("rules").load_default_rules()

	def test_travel_duration_and_classifiers(self):
		for source, expected in (
			("出了个差", "出了个钗"),
			("出几个月的差", "出几个月的钗"),
			("他下周要出三天差", "他下周要出三天钗"),
			("出两个小时的差", "出两个小时的钗"),
			("出好几天的差", "出好几天的钗"),
			("出十几天差", "出十几天钗"),
			("这次出差错了", "这次出差错了"),
		):
			self.assertEqual(expected, self.rules.transform(source), source)
		text = "这两组数据出三天差异"
		self.assertNotEqual("chai1", self.rules.resolve(text)[text.index("差")].reading_id)

	def test_stubborn_compound_forces_both_syllables(self):
		for source, expected in (("倔强", "觉匠"), ("他脾气很倔强", "他脾气很觉匠"), ("倔強", "觉匠")):
			self.assertEqual(expected, self.rules.transform(source), source)
			self.assertEqual("jue2", self.rules.resolve(source)[source.index("倔")].reading_id)

	def test_night_and_constellation_senses(self):
		for source, expected in (
			("住了三宿", "住了三朽"),
			("熬了一宿", "熬了一朽"),
			("整宿没睡", "整朽没睡"),
			("二十八宿", "二十八嗅"),
			("星宿", "星嗅"),
			("宿舍", "宿慑"),
		):
			self.assertEqual(expected, self.rules.transform(source), source)

	def test_rotational_predicate_in_sentences(self):
		for source, expected in (
			("让车轮转一转", "让车轮篆一篆"),
			("这台机器卡住不能转", "这台机器卡住不能篆"),
			("请让已经检查过轴承而且刚换过轮胎的车轮转一转", "请让已经检查过轴承而且刚换过轮胎的车轮篆一篆"),
			("虽然车轮很旧，但卡住不能转的原因是轴承坏了", "虽然车轮很旧，但卡住不能篆的原因是轴承坏了"),
			("车轮向左转一转", "车轮向左转一转"),
			("车轮向左慢慢转一转", "车轮向左慢慢转一转"),
			("车轮旁边的文件不能转", "车轮旁边的文件不能转"),
			("把文件转一转", "把文件转一转"),
			("旋转", "旋转"),
		):
			self.assertEqual(expected, self.rules.transform(source), source)

	def test_legacy_expansion_flag_does_not_gate_runtime(self):
		environment = _load_plugin()
		self.addCleanup(environment.plugin.terminate)
		section = environment.config.conf[environment.settings.CONFIG_SECTION]
		self.assertNotIn("extendedLexiconEnabled", environment.settings.CONFIG_SPEC)
		section["extendedLexiconEnabled"] = False
		environment.settings.options_changed.notify()
		self.assertIsNotNone(environment.plugin._rules.lexicon)
		self.assertEqual(["出了个钗，觉匠"], environment.filter_point.apply(["出了个差，倔强"]))


if __name__ == "__main__":
	unittest.main()
