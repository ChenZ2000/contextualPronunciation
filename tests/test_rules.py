from __future__ import annotations

import unittest

from tests.core_loader import PLUGIN_PATH, load

rules_module = load("rules")


class ChineseRulesTests(unittest.TestCase):
	@classmethod
	def setUpClass(cls):
		cls.rules = rules_module.CompiledRules.from_json_file(PLUGIN_PATH / "data" / "rules_zh_CN.json")

	def assertNormalized(self, expected: str, source: str, *, strict: bool = True):  # noqa: N802
		self.assertEqual(expected, self.rules.transform(source, strict=strict))

	def test_row_layout_phrases(self):
		self.assertNormalized("航首、航尾、航号和航数", "行首、行尾、行号和行数")

	def test_numbered_row(self):
		self.assertNormalized("第12航", "第12行")
		self.assertNormalized("第十二航内容", "第十二行内容")
		self.assertNormalized("第 12 航", "第 12 行")
		self.assertNormalized("12 航 8 列", "12 行 8 列")
		self.assertNormalized("航 12，航：１２，航12列3", "行 12，行：１２，行12列3")
		self.assertNormalized("第 12 行星，日行 200 里", "第 12 行星，日行 200 里")

	def test_row_column_count(self):
		self.assertNormalized("20航8列", "20行8列")

	def test_bounded_row_count(self):
		self.assertNormalized("表格共有12航。", "表格共有12行。")
		self.assertNormalized("共十二航代码", "共十二行代码")
		self.assertNormalized("第十二行星", "第十二行星")

	def test_rank_context(self):
		self.assertNormalized("排航第二，家中航二", "排行第二，家中行二")
		self.assertNormalized("航二", "行二")
		self.assertNormalized("夜行二百里，急行二公里", "夜行二百里，急行二公里")

	def test_xing_protection_has_priority(self):
		self.assertNormalized("一行人步行二公里，上行列车", "一行人步行二公里，上行列车")
		self.assertNormalized("行当浮桂棹，第一行星", "行当浮桂棹，第一行星")

	def test_formation_reading(self):
		self.assertNormalized("一航白鹭，儿女成航，两航泪", "一行白鹭，儿女成行，两行泪")

	def test_repeat_reading(self):
		self.assertNormalized("崇新崇试并崇复执行", "重新重试并重复执行")
		self.assertNormalized("他获得崇生并崇生归来", "他获得重生并重生归来")

	def test_zhong_protection(self):
		self.assertNormalized("重要、重视、重装部队、重重地摔", "重要、重视、重装部队、重重地摔")
		self.assertNormalized(
			"体重选择困难、权重选择器、举重选手、着重选择、偏重选择、郑重写下承诺",
			"体重选择困难、权重选择器、举重选手、着重选择、偏重选择、郑重写下承诺",
		)
		self.assertNormalized("体重返回正常，不重生男重生女", "体重返回正常，不重生男重生女")
		self.assertNormalized(
			"不重生男，只重生女；重生育质量、重生活品质、重生产轻消费、重生态建设、重生存能力、重生意",
			"不重生男，只重生女；重生育质量、重生活品质、重生产轻消费、重生态建设、重生存能力、重生意",
		)

	def test_ambiguous_technical_compounds_use_bounded_context(self):
		self.assertNormalized("请崇读一遍，执行热崇载", "请重读一遍，执行热重载")
		self.assertNormalized("重读音节，重载卡车，重名誉", "重读音节，重载卡车，重名誉")

	def test_cheng_serving_reading(self):
		self.assertNormalized("呈汤、呈饭、呈水、呈粥、呈菜", "盛汤、盛饭、盛水、盛粥、盛菜")

	def test_sheng_protection(self):
		self.assertNormalized("盛开、盛大、旺盛、盛行", "盛开、盛大、旺盛、盛行")
		self.assertNormalized("盛满枝头，百花盛放食物旁", "盛满枝头，百花盛放食物旁")
		self.assertNormalized("用来呈满水，用来呈放食物", "用来盛满水，用来盛放食物")

	def test_serving_quantity(self):
		self.assertNormalized("呈两碗汤", "盛两碗汤")
		self.assertNormalized("呈半碗饭，呈 2 碗汤", "盛半碗饭，盛 2 碗汤")

	def test_bounded_number_rules_do_not_accept_partial_long_numbers(self):
		for text in ("第" + "1" * 13 + "行", "行" + "1" * 13, "盛" + "1" * 9 + "碗"):
			self.assertNormalized(text, text)

	def test_renderer_selection_is_independent_of_reading_decisions(self):
		text = "行首与盛汤，重复"
		self.assertIs(text, self.rules.transform(text, renderings={}))
		self.assertEqual("杭首与盛汤，重复", self.rules.transform(text, renderings={"hang2": "杭"}))

	def test_single_character_and_overlong_custom_phrases_are_rejected(self):
		import json

		data = json.loads((PLUGIN_PATH / "data" / "rules_zh_CN.json").read_text("utf-8"))
		for phrase in ("行", "行" * 65):
			data["characters"]["行"]["phraseGroups"][0]["phrases"] = [phrase]
			with self.assertRaises(rules_module.RuleDataError):
				rules_module.CompiledRules.from_mapping(data)

	def test_engine_verified_p1_corrections(self):
		self.assertNormalized("打开调试器，远程调试", "打开调试器，远程调试")
		self.assertNormalized("丙住呼吸并丙息", "屏住呼吸并屏息")
		self.assertNormalized("回谈效果，谈出窗口，关闭谈窗", "回弹效果，弹出窗口，关闭弹窗")
		self.assertNormalized("密钥库、公钥、私钥和密钥对", "密钥库、公钥、私钥和密钥对")
		self.assertNormalized("密月库、公月、私月和密月对", "密钥库、公钥、私钥和密钥对", strict=False)

	def test_engine_verified_p1_counterexamples(self):
		self.assertNormalized("协调试验、调整设置、大屏住院、投屏住户", "协调试验、调整设置、大屏住院、投屏住户")
		self.assertNormalized("炮弹出膛、子弹出膛、弹药库、金钥匙", "炮弹出膛、子弹出膛、弹药库、金钥匙")
		self.assertNormalized(
			"空调试验、单调试验、音调试验、显示屏住院部、电子屏住院部、中弹窗口期",
			"空调试验、单调试验、音调试验、显示屏住院部、电子屏住院部、中弹窗口期",
		)

	def test_serving_object_rules_preserve_explicit_cross_word_protections(self):
		self.assertNormalized("呈汤。呈饭；呈水", "盛汤。盛饭；盛水")
		self.assertNormalized("请呈汤给客人，再呈水喝", "请盛汤给客人，再盛水喝")
		self.assertNormalized("盛汤姆来了、盛饭店里的菜、盛水准很高", "盛汤姆来了、盛饭店里的菜、盛水准很高")

	def test_unknown_context_is_left_unchanged(self):
		self.assertNormalized("同行、重读、盛着", "同行、重读、盛着")

	def test_no_trigger_fast_path_preserves_identity(self):
		text = "没有目标字符"
		self.assertIs(text, self.rules.transform(text))

	def test_invalid_schema_is_rejected(self):
		with self.assertRaises(rules_module.RuleDataError):
			rules_module.CompiledRules.from_mapping({"schemaVersion": 999})


if __name__ == "__main__":
	unittest.main()
