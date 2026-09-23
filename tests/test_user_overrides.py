from __future__ import annotations

import unittest

from tests.core_loader import load

rules_module = load("rules")


class UserOverridesTests(unittest.TestCase):
	def test_literal_force_keep_and_disable(self):
		rules = rules_module.load_default_rules(
			custom_entries="同行评审|行|hang2\n盛汤|盛|keep",
			disabled_rules="tan-elastic-ui",
		)
		self.assertEqual("同航评审，盛汤，弹窗", rules.transform("同行评审，盛汤，弹窗"))
		self.assertEqual("呈饭", rules.transform("盛饭"))

	def test_explicit_user_force_has_priority_over_builtin_protection(self):
		rules = rules_module.load_default_rules(custom_entries="重新重试|试|chong2\n一行人|行|hang2")
		# Intentionally user-chosen, not a linguistically correct built-in rule.
		self.assertEqual("一航人", rules.transform("一行人"))

	def test_keep_preserves_a_word_for_the_downstream_nvda_dictionary(self):
		rules = rules_module.load_default_rules(custom_entries="重读一遍|重|keep")
		self.assertEqual("请重读一遍", rules.transform("请重读一遍"))

	def test_structural_rule_can_be_disabled(self):
		rules = rules_module.load_default_rules(disabled_rules="rowLabel,rankOrder")
		self.assertEqual("行二，行 12", rules.transform("行二，行 12"))

	def test_rejects_unknown_ids_duplicate_or_unbounded_input(self):
		for entries in (
			"行|行|hang2",
			"行首|行|invented",
			"行首|行|hang2\n行首|行|keep",
			"行首|首|hang2|extra",
			"行首\t|行|hang2" * 4000,
			"行行|行|hang2",
		):
			with self.subTest(entries=entries[:40]), self.assertRaises(rules_module.RuleDataError):
				rules_module.load_default_rules(custom_entries=entries)
		with self.assertRaises(rules_module.RuleDataError):
			rules_module.load_default_rules(disabled_rules="not-a-rule")

	def test_comment_lines_and_empty_configuration_are_safe(self):
		rules = rules_module.load_default_rules(custom_entries="# comment\n\n同行评审|行|hang2")
		self.assertEqual("同航评审", rules.transform("同行评审"))
