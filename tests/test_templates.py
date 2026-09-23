from __future__ import annotations

import unittest

from tests.core_loader import load

templates = load("templates")
rules_module = load("rules")
allowed = load("lexicon").load_default_lexicon().allowed_readings


class TemplateTests(unittest.TestCase):
	def test_literal_classes_remain_bounded_at_64_values(self):
		entry = {"id": "bounded", "pattern": "[系:ji4]{objects}"}
		values = [str(i) for i in range(64)]
		compiled = templates.compile_template(entry, {"objects": values}, allowed)
		self.assertTrue(compiled.matches("系63", 0))
		with self.assertRaises(ValueError):
			templates.compile_template(entry, {"objects": values + ["64"]}, allowed)
		with self.assertRaises(ValueError):
			templates.compile_template(entry, {"objects": ["a" * 9]}, allowed)

	def test_all_contributed_positive_and_negative_examples(self):
		compiled = templates.load_templates(allowed)
		for bucket in compiled.buckets.values():
			for rule in bucket:
				self.assertTrue(rule.source and rule.positive and rule.negative, rule.id)
				for text in rule.positive:
					self.assertTrue(any(rule.matches(text, i) for i in range(len(text))), (rule.id, text))
				for text in rule.negative:
					self.assertFalse(any(rule.matches(text, i) for i in range(len(text))), (rule.id, text))

	def test_accented_and_numbered_custom_templates_have_identical_meaning(self):
		for pattern in ("仙[乐:yuè]", "仙[乐:yue4]"):
			rules = rules_module.load_default_rules(custom_templates=pattern)
			self.assertEqual("仙月飘飘", rules.transform("仙乐飘飘"))

	def test_number_class_is_bounded_and_rejects_partial_overlong_numbers(self):
		rules = rules_module.load_default_rules(custom_templates="[行:háng]{space}{number}列")
		self.assertEqual("航 123列", rules.transform("行 123列"))
		text = "行 " + "1" * 13 + "列"
		self.assertIs(text, rules.transform(text))
		with self.assertRaises(ValueError):
			templates.load_templates(allowed, "[行:háng]{unknown}")

	def test_conflicts_abstain_independent_of_contribution_order(self):
		for custom in ("仙[乐:yue4]\n仙[乐:le4]", "仙[乐:le4]\n仙[乐:yue4]"):
			rules = rules_module.load_default_rules(custom_templates=custom)
			self.assertEqual("仙乐飘飘", rules.transform("仙乐飘飘"))
			self.assertTrue(rules.resolve("仙乐飘飘")[1].protect)

	def test_keep_is_local_and_user_rules_override_builtin_rules(self):
		rules = rules_module.load_default_rules(custom_templates="仙[乐:keep]\n[盛:keep]汤")
		self.assertEqual("仙乐飘飘，音月，盛汤", rules.transform("仙乐飘飘，音乐，盛汤"))

	def test_no_renderer_is_needed_to_resolve_readings_for_braille(self):
		rules = rules_module.load_default_rules()
		for text, index, reading in (("孩子睡着了", 3, "zhao2"), ("我得赶快走", 1, "dei3")):
			self.assertEqual(reading, rules.resolve(text)[index].reading_id)
			self.assertIs(text, rules.transform(text, renderings={}))

	def test_regex_metacharacters_are_literal_not_executable_syntax(self):
		rules = rules_module.load_default_rules(custom_templates="a.*仙[乐:yue4]")
		self.assertEqual("a.*仙月", rules.transform("a.*仙乐"))
		# Disable imported data so a shorter dictionary phrase cannot obscure the test.
		template = templates.compile_template({"id": "test", "pattern": "a.*仙[乐:yue4]"}, {}, allowed)
		self.assertFalse(template.matches("abcdef仙乐", 7))

	def test_malformed_unbounded_or_unknown_readings_are_rejected(self):
		for pattern in (
			"[乐:yue4]",
			"[乐:zzzz9]曲",
			"[乐:yue4][曲:qu3]",
			"仙[乐:yue4]{number}" * 5,
			"a" * 65 + "[乐:yue4]",
			"{space}{space}{space}{space}{space}[乐:yue4]",
			"仙[乐:yue4]{.*}",
		):
			with self.subTest(pattern=pattern), self.assertRaises(ValueError):
				templates.load_templates(allowed, pattern)
