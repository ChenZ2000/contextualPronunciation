from __future__ import annotations

import builtins
import importlib.util
import sys
import types
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
CHARACTER_PROCESSING = ROOT / "vendor" / "nvda-2026.2" / "source" / "characterProcessing.py"

# Import the production speech-only guard without importing NVDA itself.
sys.path.insert(0, str(ROOT))
from tests.core_loader import load  # noqa: E402

apostrophe = load("apostrophe")
pipeline = load("pipeline")
rules_module = load("rules")


def _silent_logger() -> object:
	class SilentLogger:
		def __getattr__(self, _name: str):
			return lambda *args, **kwargs: None

	return SilentLogger()


def _load_character_processing():
	nvda_state = types.ModuleType("NVDAState")
	nvda_state.shouldWriteToDisk = lambda: False
	nvda_state.WritePaths = type("WritePaths", (), {"speechDictsDir": ""})
	log_handler = types.ModuleType("logHandler")
	log_handler.log = _silent_logger()
	global_vars = types.ModuleType("globalVars")
	global_vars.appDir = ""
	config = types.ModuleType("config")
	config.conf = {"speech": {"symbolDictionaries": []}}
	stubs = {
		"NVDAState": nvda_state,
		"logHandler": log_handler,
		"globalVars": global_vars,
		"config": config,
	}
	spec = importlib.util.spec_from_file_location("_nvda2026CharacterProcessingUnderTest", CHARACTER_PROCESSING)
	assert spec is not None and spec.loader is not None
	module = importlib.util.module_from_spec(spec)
	with (
		mock.patch.dict(sys.modules, stubs),
		mock.patch.object(builtins, "_", lambda text: text, create=True),
		mock.patch.object(builtins, "pgettext", lambda _context, text: text, create=True),
	):
		sys.modules[spec.name] = module
		spec.loader.exec_module(module)
	return module


@unittest.skipUnless(CHARACTER_PROCESSING.is_file(), "NVDA 2026.2 source checkout is unavailable")
class NVDASymbolDictionaryIntegrationTests(unittest.TestCase):
	@classmethod
	def setUpClass(cls):
		cls.character_processing = _load_character_processing()

	@classmethod
	def _load_symbols(cls, path: Path, *, complex_symbols: bool = True):
		symbols = cls.character_processing.SpeechSymbols()
		symbols.load(str(path), complex_symbols)
		return symbols

	def _processor(self, locale: str):
		cp = self.character_processing
		empty = cp.SpeechSymbols()
		user = cp.SpeechSymbols()
		locale_sources = {}
		for available_locale in ("en", "zh_CN", "zh_HK", "zh_TW"):
			builtin = self._load_symbols(
				ROOT / "vendor" / "nvda-2026.2" / "source" / "locale" / available_locale / "symbols.dic",
			)
			addon = self._load_symbols(
				ROOT / "addon" / "locale" / available_locale / "symbols-lexicalApostrophe.dic",
				complex_symbols=False,
			)
			locale_sources[available_locale] = (empty, builtin, addon, user)

		class LocaleSources:
			def fetchLocaleData(self, requested_locale: str, fallback: bool = True):  # noqa: N802, ARG002
				try:
					return locale_sources[requested_locale]
				except KeyError as error:
					raise LookupError(requested_locale) from error

		cp.SpeechSymbolProcessor.localeSymbols = LocaleSources()
		return cp.SpeechSymbolProcessor(locale)

	def test_words_keep_ascii_and_curly_apostrophes_at_all_symbols_in_chinese(self):
		processor = self._processor("zh_CN")
		self.assertEqual("Doesn't", processor.processText("Doesn't", self.character_processing.SymbolLevel.ALL))
		self.assertEqual("Doesn’t", processor.processText("Doesn’t", self.character_processing.SymbolLevel.ALL))

	def test_words_keep_apostrophes_at_all_symbols_in_english(self):
		processor = self._processor("en")
		self.assertEqual("Mike's", processor.processText("Mike's", self.character_processing.SymbolLevel.ALL))
		self.assertEqual("Mike’s", processor.processText("Mike’s", self.character_processing.SymbolLevel.ALL))

	def test_chinese_regional_locales_cannot_shadow_the_addon_override(self):
		for locale in ("zh_HK", "zh_TW"):
			with self.subTest(locale=locale):
				processor = self._processor(locale)
				self.assertEqual("Doesn't", processor.processText("Doesn't", self.character_processing.SymbolLevel.ALL))
				self.assertEqual("Mike’s", processor.processText("Mike’s", self.character_processing.SymbolLevel.ALL))

	def test_opening_quote_is_still_reported_at_all_symbols(self):
		processor = self._processor("zh_CN")
		processed = processor.processText("'Mike'", self.character_processing.SymbolLevel.ALL)
		self.assertIn("单引号", processed)
		self.assertTrue(processed.endswith("Mike'"))

	def test_full_guard_and_symbol_pipeline_preserves_words_and_reports_closing_marks(self):
		for locale, reported_name in (("en", "tick"), ("zh_CN", "单引号")):
			with self.subTest(locale=locale):
				processor = self._processor(locale)
				prepared = apostrophe.prepare_apostrophes_for_nvda(
					"Doesn’t; Mike's; He said ‘hello’; students’ books",
				)
				processed = processor.processText(prepared, self.character_processing.SymbolLevel.ALL)
				self.assertIn("Doesn't", processed)
				self.assertIn("Mike's", processed)
				self.assertNotIn("Doesn tick t", processed)
				self.assertNotIn("Doesn 撇 t", processed)
				self.assertGreaterEqual(processed.count(reported_name), 2)

	def test_polyphones_reach_real_symbol_processor_at_every_user_level(self):
		from tests.test_boundaries import REPORTED_SYMBOLS, SCENARIOS
		from tests.test_pipeline import CharacterModeCommand

		normalizer = pipeline.SpeechSequenceNormalizer(
			rules=rules_module.load_default_rules(),
			character_mode_command_type=CharacterModeCommand,
		)
		levels = ("NONE", "SOME", "MOST", "ALL", "CHAR")
		for locale in ("zh_CN", "en"):
			processor = self._processor(locale)
			for level_name in levels:
				level = getattr(self.character_processing.SymbolLevel, level_name)
				for symbol in REPORTED_SYMBOLS + "￥＋＜｜×→★😀。\u00a0\u2028":
					for source, expected in SCENARIOS:
						with self.subTest(locale=locale, level=level_name, source=source, symbol=symbol):
							actual = normalizer.normalize([source + symbol], options=pipeline.RuntimeOptions())[0]
							self.assertEqual(expected + symbol, actual)
							self.assertEqual(
								processor.processText(expected + symbol, level), processor.processText(actual, level)
							)

	def test_symbol_only_chunks_are_preserved_and_never_joined_across_commands(self):
		from tests.test_boundaries import REPORTED_SYMBOLS
		from tests.test_pipeline import CharacterModeCommand, IndexCommand, LangChangeCommand

		normalizer = pipeline.SpeechSequenceNormalizer(
			rules=rules_module.load_default_rules(),
			character_mode_command_type=CharacterModeCommand,
		)
		index = IndexCommand()
		for symbol in REPORTED_SYMBOLS:
			sequence = ["盛汤", index, symbol, CharacterModeCommand(True), "盛汤" + symbol]
			result = normalizer.normalize(sequence, options=pipeline.RuntimeOptions())
			self.assertEqual("呈汤", result[0])
			self.assertIs(index, result[1])
			self.assertEqual(symbol, result[2])
			self.assertIs(sequence[3], result[3])
			self.assertEqual(sequence[4], result[4])
		sequence = ["盛", index, "汤$", LangChangeCommand("en_US"), "盛汤$"]
		self.assertEqual(
			["盛", index, "汤$", sequence[3], "呈汤$"],
			normalizer.normalize(sequence, options=pipeline.RuntimeOptions()),
		)


if __name__ == "__main__":
	unittest.main()
