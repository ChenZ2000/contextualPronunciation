from __future__ import annotations

import unittest

from tests.core_loader import load

pipeline = load("pipeline")
rules_module = load("rules")


class LangChangeCommand:
	def __init__(self, lang):
		self.lang = lang


class CharacterModeCommand:
	def __init__(self, state):
		self.state = state


class IndexCommand:
	pass


class PipelineTests(unittest.TestCase):
	def setUp(self):
		self.normalizer = pipeline.SpeechSequenceNormalizer(
			rules=rules_module.load_default_rules(),
			character_mode_command_type=CharacterModeCommand,
		)
		self.options = pipeline.RuntimeOptions()

	def normalize(self, sequence, *, options=None):
		return self.normalizer.normalize(sequence, options=options or self.options)

	def test_preserves_commands_and_changes_only_strings(self):
		index = IndexCommand()
		language = LangChangeCommand("zh_CN")
		sequence = [language, "第2行", index, "盛汤"]
		result = self.normalize(sequence)
		self.assertEqual("第2航", result[1])
		self.assertIs(language, result[0])
		self.assertIs(index, result[2])
		self.assertEqual("呈汤", result[3])

	def test_character_mode_disables_normalization_until_reset(self):
		sequence = [CharacterModeCommand(True), "行首", CharacterModeCommand(False), "行尾"]
		result = self.normalize(sequence)
		self.assertEqual("行首", result[1])
		self.assertEqual("航尾", result[3])

	def test_all_language_tags_are_opaque_preserved_commands(self):
		for tag in ("zh_CN", "en_US", "zh_HK", "yue", "zh_TW", "ja", "", None):
			with self.subTest(tag=tag):
				command = LangChangeCommand(tag)
				result = self.normalize([command, "行首、重复、盛汤"])
				self.assertIs(command, result[0])
				self.assertEqual("航首、崇复、呈汤", result[1])

	def test_language_properties_are_never_read(self):
		class OpaqueLanguageCommand:
			@property
			def lang(self):
				raise AssertionError("No language property access")

		command = OpaqueLanguageCommand()
		self.assertEqual([command, "仙月飘飘"], self.normalize([command, "仙乐飘飘"]))

	def test_commands_do_not_join_context(self):
		command = IndexCommand()
		self.assertEqual(["盛", command, "汤"], self.normalize(["盛", command, "汤"]))

	def test_apostrophe_normalization_is_safe_in_mixed_language(self):
		sequence = [LangChangeCommand("en_US"), "Doesn’t", LangChangeCommand("zh_CN"), "Mike’s 朋友"]
		result = self.normalize(sequence)
		self.assertEqual("Doesn't", result[1])
		self.assertEqual("Mike's 朋友", result[3])

	def test_closing_apostrophe_is_guarded_for_nvda_symbol_processing(self):
		sequence = [LangChangeCommand("en_US"), "'Mike' and students’ books"]
		self.assertEqual("'Mike ' and students ’ books", self.normalize(sequence)[1])

	def test_disabled_leaves_contextual_rewrites_off(self):
		sequence = ["第2行 Doesn't"]
		self.assertIs(sequence, self.normalize(sequence, options=pipeline.RuntimeOptions(enabled=False)))

	def test_disabled_still_guards_closing_quote_required_by_dictionary(self):
		self.assertEqual(
			["第2行 'quoted '"],
			self.normalize(["第2行 'quoted'"], options=pipeline.RuntimeOptions(enabled=False)),
		)

	def test_no_trigger_returns_same_sequence(self):
		sequence = [IndexCommand(), "普通文本"]
		self.assertIs(sequence, self.normalize(sequence))

	def test_fail_open_returns_buffered_original_and_survives_reporter_failure(self):
		class BrokenNormalizer:
			def normalize(self, *args, **kwargs):
				raise RuntimeError("test")

		errors = []

		def reporter():
			errors.append(True)
			raise RuntimeError("reporting also failed")

		filter_callable = pipeline.FailOpenSpeechFilter(
			normalizer=BrokenNormalizer(),
			options_provider=lambda: self.options,
			error_reporter=reporter,
		)
		sequence = ["private spoken content"]
		self.assertIs(sequence, filter_callable(sequence))
		self.assertEqual(sequence, filter_callable(iter(sequence)))
		self.assertEqual([True, True], errors)

	def test_generator_is_consumed_once(self):
		count = []

		def upstream():
			count.append(True)
			yield "盛汤"

		self.assertEqual(["呈汤"], self.normalize(upstream()))
		self.assertEqual([True], count)


if __name__ == "__main__":
	unittest.main()
