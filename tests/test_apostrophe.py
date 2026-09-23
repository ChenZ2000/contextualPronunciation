from __future__ import annotations

import unittest

from tests.core_loader import load

apostrophe = load("apostrophe")


class ApostropheTests(unittest.TestCase):
	def test_normalizes_curly_apostrophe_inside_latin_word(self):
		self.assertEqual("Doesn't and Mike's", apostrophe.normalize_lexical_apostrophes("Doesn’t and Mike’s"))

	def test_accepts_non_ascii_latin_letters(self):
		self.assertEqual("l'amour d'été", apostrophe.normalize_lexical_apostrophes("l’amour d’été"))

	def test_does_not_change_quotation_marks(self):
		text = "‘hello’ and 中文’引号"
		self.assertIs(text, apostrophe.normalize_lexical_apostrophes(text))

	def test_does_not_change_word_final_possessive(self):
		text = "the students’ books"
		self.assertIs(text, apostrophe.normalize_lexical_apostrophes(text))

	def test_returns_same_object_on_fast_path(self):
		text = "plain ASCII text"
		self.assertIs(text, apostrophe.normalize_lexical_apostrophes(text))

	def test_prepares_both_word_apostrophe_forms_for_nvda(self):
		self.assertEqual(
			"Doesn't and Mike's",
			apostrophe.prepare_apostrophes_for_nvda("Doesn’t and Mike's"),
		)

	def test_guards_closing_quotes_from_nvda_complex_symbol(self):
		self.assertEqual("'hello ' and ‘world ’", apostrophe.prepare_apostrophes_for_nvda("'hello' and ‘world’"))
		self.assertEqual("中文 ’引号", apostrophe.prepare_apostrophes_for_nvda("中文’引号"))

	def test_word_final_possessive_is_guarded_not_treated_as_a_joiner(self):
		self.assertEqual(
			"the students ’ books",
			apostrophe.prepare_apostrophes_for_nvda("the students’ books"),
		)

	def test_preparation_is_idempotent(self):
		once = apostrophe.prepare_apostrophes_for_nvda("'hello' Doesn't")
		self.assertEqual(once, apostrophe.prepare_apostrophes_for_nvda(once))


if __name__ == "__main__":
	unittest.main()
