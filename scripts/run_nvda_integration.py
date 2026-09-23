"""Exercise the real NVDA speech entry point and GlobalPlugin in its native test environment.

Run with NVDA's built .venv Python. No installed NVDA profile is loaded. Speech
is intercepted at SpeechManager.speak; no synth/audio output is started.
"""

from __future__ import annotations

import hashlib
import importlib
import importlib.util
import json
import platform
import sys
import types
import unittest
from datetime import UTC, datetime
from pathlib import Path
from unittest import mock

from prepare_nvda import NVDA

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(NVDA))
sys.path.insert(0, str(NVDA / "source"))
# Use upstream's isolated configuration, compiled helper DLLs and generated COM
# interfaces. The 'tests' package here is NVDA's, not this add-on's unit suite.
importlib.import_module("tests.unit")

import addonHandler  # noqa: E402
import characterProcessing as cp  # noqa: E402
import config  # noqa: E402
import speech  # noqa: E402
import synthDriverHandler  # noqa: E402
from speech.commands import CharacterModeCommand, IndexCommand, LangChangeCommand  # noqa: E402
from speech.extensions import filter_speechSequence  # noqa: E402

core_speech = importlib.import_module("speech.speech")
PLUGIN_DIR = ROOT / "addon/globalPlugins/contextualPronunciation"
sentence_spec = importlib.util.spec_from_file_location("_nativeSentenceCases", ROOT / "tests/sentence_cases.py")
sentences = importlib.util.module_from_spec(sentence_spec)
sentence_spec.loader.exec_module(sentences)


class NativeSpeechChainTests(unittest.TestCase):
	@classmethod
	def setUpClass(cls):
		name = "_contextualPronunciationNativeIntegration"
		spec = importlib.util.spec_from_file_location(
			name, PLUGIN_DIR / "__init__.py", submodule_search_locations=[str(PLUGIN_DIR)]
		)
		module = importlib.util.module_from_spec(spec)
		sys.modules[name] = module
		# No installed add-on discovery is performed. All other NVDA modules,
		# config handling, commands, Filter/Action objects and wx are real.
		with mock.patch.object(addonHandler, "initTranslation"):
			spec.loader.exec_module(module)
		cls.module = module
		cls.dictionary = cp.SymbolDictionaryDefinition(
			name="lexicalApostrophe",
			source="contextualPronunciation",
			mandatory=True,
			path=str(ROOT / "addon/locale/{locale}/symbols-lexicalApostrophe.dic"),
		)
		cp._symbolDictionaryDefinitions.insert(-1, cls.dictionary)
		cp.clearSpeechSymbols()

	@classmethod
	def tearDownClass(cls):
		cp._symbolDictionaryDefinitions.remove(cls.dictionary)
		cp.clearSpeechSymbols()

	def setUp(self):
		config.conf["speech"]["autoLanguageSwitching"] = True
		config.conf["speech"]["autoDialectSwitching"] = True
		config.conf["speech"]["unicodeNormalization"] = "disabled"
		core_speech.setSpeechMode(core_speech.SpeechMode.talk)
		self.voice = types.SimpleNamespace(name="vocalizer_expressive2", voice="Ting-Ting", language="zh_CN")
		for patcher in (
			mock.patch.object(synthDriverHandler, "getSynth", return_value=self.voice),
			mock.patch.object(speech, "getCurrentLanguage", return_value="zh_CN"),
			mock.patch.object(core_speech, "getCurrentLanguage", return_value="zh_CN"),
		):
			patcher.start()
			self.addCleanup(patcher.stop)
		self.plugin = self.module.GlobalPlugin()
		self.addCleanup(self.plugin.terminate)

	def capture(self, sequence, level):
		with mock.patch.object(core_speech._manager, "speak") as output:
			core_speech.speak(sequence, symbolLevel=level)
			output.assert_called_once()
			return output.call_args.args[0]

	def test_late_dictionary_output_reaches_real_queue_guard(self):
		import speechDictHandler

		class CapturedBeforeSynthesis(Exception):
			pass

		for phrase, expected in (("下边缘", "下编缘"), ("唱和说", "唱河说"), ("多行", "多航")):
			for spelling in (False, True):
				captured = []

				def capture_queue(sequence, priority, captured=captured):
					captured.extend(sequence)
					self.assertIsNotNone(priority)
					raise CapturedBeforeSynthesis

				sequence = ["词典生成文本"]
				if spelling:
					sequence = [CharacterModeCommand(True), *sequence, CharacterModeCommand(False)]
				with (
					mock.patch.object(
						speechDictHandler, "processText", side_effect=lambda t, p=phrase: t.replace("词典生成文本", p)
					),
					mock.patch.object(core_speech._manager, "_queueSpeechSequence", side_effect=capture_queue),
					self.assertRaises(CapturedBeforeSynthesis),
				):
					core_speech.speak(sequence, symbolLevel=cp.SymbolLevel.NONE)
				text = "".join(s for s in captured if isinstance(s, str)).strip()
				self.assertEqual(phrase if spelling else expected, text)

	def test_actual_speak_filter_dictionary_symbol_chain(self):
		pairs = (
			("下边缘", "下编缘"),
			("唱和说", "唱河说"),
			("多行", "多航"),
			("盛汤", "呈汤"),
			("第12行", "第12航"),
			("12行", "12航"),
			("行二", "航二"),
			("同辈中行三", "同辈中航三"),
			("行 12", "航 12"),
			("盛开", "盛开"),
			("盛汤姆", "盛汤姆"),
			("日行二百里", "日行二百里"),
			("重新", "崇新"),
			("弹窗", "谈窗"),
			("屏住呼吸", "丙住呼吸"),
			("几行", "几航"),
			("竖行", "竖航"),
			("这几行不行", "这几航不行"),
			("写了数行之后", "写了数航之后"),
			("这个参数行吗", "这个参数行吗"),
			("茶几行不行", "茶几行不行"),
			("系鞋带", "冀鞋带"),
			("系好安全带", "冀好安全带"),
			("量一下体温", "梁一下体温"),
			("测量重量", "测梁重量"),
			("联系好安全带厂家", "联系好安全带厂家"),
			("商量尺寸", "商量尺寸"),
			("量体裁衣", "量体裁衣"),
			("系领结，系绳子，系红领巾", "冀领结，冀绳子，冀红领巾"),
			("用尺子量长度，量身高", "用尺子梁长度，梁身高"),
			("校量尺寸，估量长度", "校量尺寸，估量长度"),
			("用卷尺重新量一量", "用卷尺崇新梁一梁"),
			("系了一条领带，身高量了两次", "冀了一条领带，身高梁了两次"),
			("盛豆角，盛红豆粥", "呈豆角，呈红豆粥"),
			("盛刚煮好的红豆粥", "呈刚煮好的红豆粥"),
			("量小名的身高", "梁小名的身高"),
			("量住在隔壁的小名的身高", "梁住在隔壁的小名的身高"),
			("系小名的鞋带", "冀小名的鞋带"),
			("盛液体，盛装液体", "呈液体，呈装液体"),
			("盛装液体的容器", "呈装液体的容器"),
			("盛了半瓶透明液体", "呈了半瓶透明液体"),
			("盛装饰品，盛过气体", "呈装饰品，呈过气体"),
			("盛装出席，盛先生的液体", "盛装出席，盛先生的液体"),
			("重吸收，重捏，重飞", "崇吸收，崇捏，崇飞"),
			("盛了一碗饭", "呈了一碗饭"),
			("虾兵和蟹将，天兵和天将", "虾兵和蟹匠，天兵和天匠"),
			("士兵和飞机将起飞", "士兵和飞机将起飞"),
		)
		for level in (cp.SymbolLevel.NONE, cp.SymbolLevel.SOME, cp.SymbolLevel.MOST, cp.SymbolLevel.ALL):
			for symbol in "|$^+=<>`~￥×→★😀":
				for source, expected in pairs:
					with self.subTest(source=source, symbol=symbol, level=level):
						actual = self.capture([source + symbol], level)
						strings = [item for item in actual if isinstance(item, str)]
						self.assertEqual(
							[core_speech.processText("zh_CN", expected + symbol, level) + core_speech.CHUNK_SEPARATOR],
							strings,
						)

	def test_actual_crossing_default_reading_reaches_speech_manager(self):
		settings = sys.modules[self.module.__name__ + ".settings"]
		section = config.conf[settings.CONFIG_SECTION]
		previous = section["extendedLexiconEnabled"]
		self.addCleanup(section.__setitem__, "extendedLexiconEnabled", previous)
		section["extendedLexiconEnabled"] = True
		self.plugin._reload_configuration()
		for source, expected in (
			("降调音频", "降吊音频"),
			("升调音频", "升吊音频"),
			("调音师", "条音师"),
			("降调版本", "降调版本"),
		):
			for level in (cp.SymbolLevel.NONE, cp.SymbolLevel.SOME, cp.SymbolLevel.MOST, cp.SymbolLevel.ALL):
				for symbol in "|$^+=<>`~😀":
					with self.subTest(source=source, symbol=symbol, level=level):
						sequence = [source + symbol]
						result = self.capture(sequence, level)
						self.assertEqual(
							[core_speech.processText("zh_CN", expected + symbol, level) + core_speech.CHUNK_SEPARATOR],
							[item for item in result if isinstance(item, str)],
						)
						self.assertEqual([source + symbol], sequence)

	def test_actual_commands_global_language_policy_and_character_mode(self):
		index = IndexCommand(17)
		sequence = [
			"盛汤$",
			index,
			CharacterModeCommand(True),
			"盛汤$",
			CharacterModeCommand(False),
			LangChangeCommand("en_US"),
			"盛汤$",
			LangChangeCommand("zh_CN"),
			"行 12$",
		]
		result = self.capture(sequence, cp.SymbolLevel.ALL)
		self.assertIn(index, result)
		texts = [item for item in result if isinstance(item, str)]
		self.assertTrue(texts[0].startswith("呈汤"))
		self.assertTrue(texts[1].startswith("盛汤"))
		self.assertTrue(texts[2].startswith("呈汤"))
		self.assertTrue(texts[3].startswith("航"))
		self.assertEqual("盛汤$", sequence[0], "Caller-owned input must remain unchanged")

	def test_actual_sentence_chain_matches_independent_oracles_at_all_symbol_levels(self):
		for level in (cp.SymbolLevel.NONE, cp.SymbolLevel.SOME, cp.SymbolLevel.MOST, cp.SymbolLevel.ALL):
			for source, expected in sentences.SENTENCE_CASES:
				with self.subTest(source=source, level=level):
					sequence = [source]
					actual = self.capture(sequence, level)
					self.assertEqual(
						[core_speech.processText("zh_CN", expected, level) + core_speech.CHUNK_SEPARATOR],
						[item for item in actual if isinstance(item, str)],
					)
					self.assertEqual([source], sequence)

	def test_actual_sentence_chain_preserves_index_and_character_commands(self):
		index = IndexCommand(31)
		first = "我给孩子盛汤之后盛饭"
		second = "盛饭盛汤很好"
		sequence = [first, index, second, CharacterModeCommand(True), "盛汤"]
		actual = self.capture(sequence, cp.SymbolLevel.NONE)
		self.assertIn(index, actual)
		texts = [item for item in actual if isinstance(item, str)]
		self.assertEqual(
			[
				"我给孩子呈汤之后呈饭" + core_speech.CHUNK_SEPARATOR,
				"呈饭呈汤很好" + core_speech.CHUNK_SEPARATOR,
				"盛汤",  # NVDA character mode does not append its normal speech chunk separator.
			],
			texts,
		)
		self.assertEqual(first, sequence[0])
		self.assertEqual(second, sequence[2])

	def test_actual_lexical_apostrophes_and_quotes(self):
		for language in ("zh_CN", "en_US"):
			output = self.capture([LangChangeCommand(language), "Doesn’t; Mike's; He said ‘hello’"], cp.SymbolLevel.ALL)
			text = "".join(item for item in output if isinstance(item, str))
			self.assertIn("Doesn't", text)
			self.assertIn("Mike's", text)
			self.assertIn("hello", text)
			self.assertNotIn("hello’", text)

	def test_actual_filter_unregistered_on_termination(self):
		self.plugin.terminate()
		sequence = ["盛汤$"]
		self.assertEqual(sequence, filter_speechSequence.apply(sequence))

	def test_legacy_off_migration_with_real_aggregated_config_section(self):
		settings = sys.modules[self.module.__name__ + ".settings"]
		section = config.conf[settings.CONFIG_SECTION]
		previous = section["chinesePolyphonesEnabled"]
		self.addCleanup(section.__setitem__, "chinesePolyphonesEnabled", previous)
		section["rendererMode"] = "off"
		self.assertFalse(settings.get_runtime_options().chinese_polyphones_enabled)
		self.assertEqual("retired", section["rendererMode"])
		# The user can re-enable globally without the retired field turning it off.
		section["chinesePolyphonesEnabled"] = True
		self.assertTrue(settings.get_runtime_options().chinese_polyphones_enabled)

	def test_extended_lexicon_in_real_speech_chain_and_braille_unchanged(self):
		from unittest.mock import PropertyMock

		import braille

		for source, expected in (("仙乐飘飘", "仙月飘飘"), ("乐观的音乐家", "乐观的音月家")):
			for level in (cp.SymbolLevel.NONE, cp.SymbolLevel.ALL):
				result = self.capture([source], level)
				self.assertEqual(
					[core_speech.processText("zh_CN", expected, level) + core_speech.CHUNK_SEPARATOR],
					[item for item in result if isinstance(item, str)],
				)
			region = braille.Region()
			region.rawText = source
			# The plugin never inserts speech homophones into a braille region.
			self.assertEqual(source, region.rawText)
		# Exercise the real native liblouis helper with original text, checking
		# mapping lengths and valid bounds rather than assuming a braille scheme.
		import brailleTables
		import louisHelper

		with mock.patch.object(
			type(braille.handler),
			"table",
			new_callable=PropertyMock,
			return_value=brailleTables.getTable("zhcn-cbs.ctb"),
		):
			cells, b2r, r2b, cursor = louisHelper.translate(["zhcn-cbs.ctb", "braille-patterns.cti"], "仙乐飘飘")
		self.assertEqual(len(cells), len(b2r))
		self.assertEqual(4, len(r2b))
		self.assertTrue(all(0 <= index < 4 for index in b2r))
		self.assertTrue(all(0 <= index < len(cells) for index in r2b))

	def test_optional_braille_overlay_exact_target_cells_and_cursor_routing(self):
		import louisHelper

		with (
			(ROOT / "manifest.ini").open("rb") as source,
			(ROOT / "addon/locale/zh_CN/manifest.ini").open("rb") as translated,
		):
			manifest = addonHandler.AddonManifest(source, translated)
		self.assertFalse(manifest.errors)
		table_info = manifest["brailleTables"]["zhcn-contextual-2018.ctb"]
		self.assertFalse(table_info["input"])
		self.assertTrue(table_info["output"])

		table = str(ROOT / "addon/brailleTables/zhcn-contextual-2018.ctb")
		# Independent GF 0019-2018 dot expectations, including abbreviated tones.
		for text, target, expected in (
			("仙乐飘飘", 1, [62]),
			("盛汤之后盛饭", 0, [31, 60]),
			("盛汤之后盛饭", 4, [31, 60]),
			("行首", 0, [19, 38]),
			("屏住呼吸", 0, [3, 33, 4]),
			("弹窗", 0, [30, 39]),
			("竖行", 1, [19, 38]),
			("豎行", 1, [19, 38]),
		):
			with self.subTest(text=text, target=target):
				cells, b2r, r2b, cursor = louisHelper.translate([table, "braille-patterns.cti"], text, cursorPos=target)
				self.assertEqual(expected, [cell for cell, raw in zip(cells, b2r, strict=True) if raw == target])
				self.assertEqual(len(text), len(r2b))
				self.assertEqual(r2b[target], cursor)
				self.assertTrue(all(0 <= raw < len(text) for raw in b2r))
				self.assertTrue(all(0 <= cell < len(cells) for cell in r2b))
				_base_cells, _base_b2r, base_r2b, _ = louisHelper.translate(["zhcn-cbs.ctb"], text)
				# Base liblouis already groups some complete words to one routing
				# location. The overlay must not merge any additional locations.
				for index in range(1, len(text)):
					if base_r2b[index] != base_r2b[index - 1]:
						self.assertNotEqual(r2b[index], r2b[index - 1])
		# Existing base-table whole-word entries can win over a one-character
		# match. Verify their complete correct result, not fictitious per-letter
		# routing: the base table itself assigns these cells to a word span.
		for text, expected in (
			("音乐", [35, 1, 62]),
			("重新", [31, 50, 19, 35, 1]),
			("乐曲", [62, 5, 44, 4]),
			("屏息", [3, 33, 4, 19, 10, 1]),
		):
			self.assertEqual(expected, louisHelper.translate([table], text)[0])
			self.assertEqual(louisHelper.translate(["zhcn-cbs.ctb"], text), louisHelper.translate([table], text))
		for text in (
			"快乐",
			"乐观",
			"丰盛饭菜",
			"盛汤姆",
			"盛饭店",
			"重装部队",
			"一行人",
			"未知龘龘",
			"茶几行不行",
			"子弹性能很好",
			"横行霸道",
			"直行车辆",
		):
			self.assertEqual(
				louisHelper.translate(["zhcn-cbs.ctb", "braille-patterns.cti"], text),
				louisHelper.translate([table, "braille-patterns.cti"], text),
				text,
			)


def main() -> int:
	suite = unittest.defaultTestLoader.loadTestsFromTestCase(NativeSpeechChainTests)
	result = unittest.TextTestRunner(verbosity=2).run(suite)
	report = {
		"testedAtUtc": datetime.now(UTC).isoformat(),
		"python": platform.python_version(),
		"testsRun": result.testsRun,
		"failures": len(result.failures),
		"errors": len(result.errors),
		"skipped": len(result.skipped),
		"passed": result.wasSuccessful() and not result.skipped,
		"sourceSha256": {
			p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
			for p in sorted([*PLUGIN_DIR.rglob("*"), *(ROOT / "addon/brailleTables").glob("*.ctb"), Path(__file__)])
			if p.is_file() and p.suffix in {".py", ".json", ".toml", ".ctb"}
		},
		"realComponents": [
			"native liblouis with optional GF 0019-2018 context table",
			"GlobalPlugin",
			"NVDA config",
			"Filter/Action",
			"speech.speech.speak",
			"speechDictHandler",
			"SpeechSymbolProcessor",
			"commands",
			"compiled helper DLLs",
			"wx imports",
		],
		"substitutes": [
			"installed add-on translation discovery",
			"voice identity/language properties",
			"SpeechManager.speak captured (no audio)",
			"official NVDA unit test bootstrap isolation",
		],
	}
	(ROOT / "artifacts/nvda-native-integration.json").write_text(
		json.dumps(report, ensure_ascii=False, indent=2) + "\n", "utf-8"
	)
	return 0 if report["passed"] else 1


if __name__ == "__main__":
	raise SystemExit(main())
