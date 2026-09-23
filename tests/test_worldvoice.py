"""Real upstream pipeline/detector/speak body with in-memory engines and config.

No WorldVoice driver constructor, DLL, voice installation, audio device or
logging backend is used. Tests deliberately include generators and WV commands.
"""

from __future__ import annotations

import ast
import importlib
import os
import sys
import types
import unittest
from contextlib import contextmanager
from pathlib import Path
from unittest import mock

from scripts.prepare_worldvoice import WORLDVOICE
from tests.core_loader import load
from tests.test_global_plugin_integration import FakeExtensionPoint
from tests.test_pipeline import CharacterModeCommand, LangChangeCommand


@contextmanager
def upstream_worldvoice():
	path = Path(os.environ.get("CONTEXTUAL_WORLDVOICE_SOURCE", str(WORLDVOICE / "addon/synthDrivers/WorldVoice")))
	if not (path / "pipeline/__init__.py").exists():
		raise RuntimeError("Run scripts/prepare_worldvoice.py; WorldVoice tests may not be skipped")
	name = "_worldVoiceCompatibilityUnderTest"
	module = types.ModuleType(name)
	module.__path__ = [str(path)]
	configuration = types.ModuleType("config")
	configuration.conf = {
		"general": {"loggingLevel": "INFO"},
		"WorldVoice": {
			"log": {"enable": False},
			"pipeline": {},
			"autoLanguageSwitching": {
				"DetectLanguageTiming": "after",
				"CJKCharactersLanguage": "zh_CN",
				"latinCharactersLanguage": "en_US",
				"arabicCharactersLanguage": "ar",
				"ignoreNumbersInLanguageDetection": True,
			},
		},
	}
	commands = types.ModuleType("speech.commands")
	commands.LangChangeCommand = LangChangeCommand
	commands.SynthCommand = commands.SynthParamCommand = object
	commands.BreakCommand = type("BreakCommand", (), {"__init__": lambda self, time: setattr(self, "time", time)})
	extensions = types.ModuleType("speech.extensions")
	extensions.filter_speechSequence = FakeExtensionPoint()
	speech = types.ModuleType("speech")
	speech.__path__ = []
	speech.speech = types.SimpleNamespace(processText=lambda text: text)
	synth_handler = types.ModuleType("synthDriverHandler")
	synth_handler.getSynth = lambda: module.synth
	dictionaries = types.ModuleType("speechDictHandler")
	dictionaries.processText = lambda text: text
	log_handler = types.ModuleType("logHandler")
	log_handler.log = types.SimpleNamespace(debug=lambda *args: None)
	logger = types.ModuleType(name + ".log")
	logger.PipelineLog = lambda _: None
	global_vars = types.ModuleType("globalVars")
	global_vars.speechDictionaryProcessing = True
	patches = {
		name: module,
		"synthDrivers.WorldVoice": module,
		name + ".log": logger,
		"config": configuration,
		"speech": speech,
		"speech.commands": commands,
		"speech.extensions": extensions,
		"speechDictHandler": dictionaries,
		"synthDriverHandler": synth_handler,
		"logHandler": log_handler,
		"globalVars": global_vars,
	}
	with mock.patch.dict(sys.modules, patches):
		for existing in tuple(sys.modules):
			if existing.startswith(name + ".") and existing != name + ".log":
				del sys.modules[existing]
		pipeline = importlib.import_module(name + ".pipeline")
		detection = importlib.import_module(name + ".languageDetection")
		wv_commands = importlib.import_module(name + "._speechcommand")

		class Voice:
			def __init__(self, language, engine, identifier):
				self.language, self.engine, self.id = language, engine, identifier
				self.output = []

			def speak(self, chunks):
				self.output.append(chunks)

			def breaks(self, seconds):
				pass

		voices = {
			"en_US": Voice("en_US", "OneCore", "English"),
			"zh_CN": Voice("zh_CN", "VE", "Ting-Ting"),
			"zh_HK": Voice("zh_HK", "VE", "Sin-Ji"),
		}
		manager = types.SimpleNamespace(defaultVoiceInstance=voices["en_US"], getVoiceInstanceForLanguage=voices.get)
		module.synth = types.SimpleNamespace(name="WorldVoice", language="en_US", _voiceManager=manager, uwv=True)
		detector = detection.LanguageDetector(voices, types.SimpleNamespace(symbols={}))
		module.synth.add_detected_language_commands = detector.add_detected_language_commands
		module.config, module.Voice = configuration, Voice
		module.READY_ENGINE_CLASS = {"VE": None, "OneCore": None}
		module.BreakCommand = commands.BreakCommand
		for function in ("inject_langchange_reorder", "deduplicate_language_command", "lang_cmd_to_voice"):
			setattr(module, function, getattr(pipeline, function))
		# Execute the upstream method unchanged, without importing or running
		# its engine-discovery constructor. Filename stays attributable upstream.
		tree = ast.parse((path / "__init__.py").read_text("utf-8"))
		klass = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "SynthDriver")
		method = next(node for node in klass.body if isinstance(node, ast.FunctionDef) and node.name == "speak")
		exec(compile(ast.Module(body=[method], type_ignores=[]), str(path / "__init__.py"), "exec"), module.__dict__)
		module.pipeline, module.detector, module.voices = pipeline, detector, voices
		module.filter_point = extensions.filter_speechSequence
		module.dictionaries, module.WVLangChangeCommand = dictionaries, wv_commands.WVLangChangeCommand
		yield module


class WorldVoiceTests(unittest.TestCase):
	def test_syntax_and_crossing_default_readings_after_real_dictionary_pipeline(self):
		for timing in ("before", "after"):
			with self.subTest(timing=timing), upstream_worldvoice() as wv:
				self.register(wv, extended=True)
				wv.config.conf["WorldVoice"]["autoLanguageSwitching"]["DetectLanguageTiming"] = timing
				wv.dictionaries.processText = lambda text: text.replace(
					"测试词", "盛红豆粥，量小名的身高，降调音频，盛液体，盛装液体的容器，盛装出席"
				)

				if timing == "before":
					wv.filter_point.register(wv.detector.add_detected_language_commands)
					wv.filter_point.moveToEnd(wv.detector.add_detected_language_commands, False)
					wv.pipeline.order_move_to_start_register()
				wv.speak(wv.synth, wv.filter_point.apply(iter(["测试词"])))
				self.assertEqual(
					[["呈红豆粥，梁小名的身高，降吊音频，呈液体，呈装液体的容器，盛装出席"]],
					wv.voices["zh_CN"].output,
				)

	def test_productive_predicates_and_nested_grammar_follow_real_dictionary(self):
		for timing in ("before", "after"):
			with self.subTest(timing=timing), upstream_worldvoice() as wv:
				self.register(wv)
				wv.config.conf["WorldVoice"]["autoLanguageSwitching"]["DetectLanguageTiming"] = timing
				wv.dictionaries.processText = lambda text: text.replace(
					"新语法",
					"重转，盛那碗刚刚煮好而且非常香甜的红豆粥，量住在隔壁而且刚上小学的小名的身高，重吸收，盛了一碗饭，虾兵和蟹将，也给我盛了一碗，天兵和天将一起去吃饭，下边缘，唱和说，多行",
				)
				if timing == "before":
					wv.filter_point.register(wv.detector.add_detected_language_commands)
					wv.filter_point.moveToEnd(wv.detector.add_detected_language_commands, False)
					wv.pipeline.order_move_to_start_register()
				wv.speak(wv.synth, wv.filter_point.apply(["新语法"]))
				self.assertEqual(
					[
						[
							"崇转，呈那碗刚刚煮好而且非常香甜的红豆粥，梁住在隔壁而且刚上小学的小名的身高，崇吸收，呈了一碗饭，虾兵和蟹匠，也给我呈了一碗，天兵和天匠一起去吃饭，下编缘，唱河说，多航"
						]
					],
					wv.voices["zh_CN"].output,
				)

	def test_new_fastening_measurement_rules_follow_dictionary_in_both_orders(self):
		for timing in ("before", "after"):
			with self.subTest(timing=timing), upstream_worldvoice() as wv:
				self.register(wv)
				wv.config.conf["WorldVoice"]["autoLanguageSwitching"]["DetectLanguageTiming"] = timing
				wv.dictionaries.processText = lambda text: text.replace("测试词", "系领结并用卷尺再量一量")
				if timing == "before":
					wv.filter_point.register(wv.detector.add_detected_language_commands)
					wv.filter_point.moveToEnd(wv.detector.add_detected_language_commands, False)
					wv.pipeline.order_move_to_start_register()
				wv.speak(wv.synth, wv.filter_point.apply(iter(["测试词，校量尺寸，商量尺寸，联系好安全带厂家"])))
				self.assertEqual(
					[["冀领结并用卷尺再梁一梁，校量尺寸，商量尺寸，联系好安全带厂家"]],
					wv.voices["zh_CN"].output,
				)

	def register(self, wv, *, extended=False):
		core = load("pipeline")
		normalizer = core.SpeechSequenceNormalizer(
			rules=load("rules").load_default_rules(extended=extended),
			character_mode_command_type=CharacterModeCommand,
		)
		filter_ = core.FailOpenSpeechFilter(normalizer=normalizer, options_provider=core.RuntimeOptions)
		wv.filter_point.register(filter_)
		wv.filter_point.register(wv.pipeline.apply_speech_dictionaries)
		wv.pipeline.order_move_to_start_register()
		return filter_

	def test_after_detection_routes_all_languages_without_voice_gate(self):
		with upstream_worldvoice() as wv:
			original = wv.lang_cmd_to_voice
			self.register(wv)
			stream = wv.filter_point.apply(
				iter(["Hello 仙乐飘飘，盛汤之后盛饭", wv.WVLangChangeCommand("zh_HK"), "盛汤"])
			)
			wv.speak(wv.synth, stream)
			self.assertEqual([["Hello "]], wv.voices["en_US"].output)
			self.assertEqual([["仙月飘飘，呈汤之后呈饭"]], wv.voices["zh_CN"].output)
			self.assertEqual([["呈汤"]], wv.voices["zh_HK"].output)
			self.assertIs(original, wv.lang_cmd_to_voice)

	def test_dictionary_and_normalization_each_run_once_in_both_detection_orders(self):
		for timing in ("before", "after"):
			with self.subTest(timing=timing), upstream_worldvoice() as wv:
				filter_ = self.register(wv)
				wv.config.conf["WorldVoice"]["autoLanguageSwitching"]["DetectLanguageTiming"] = timing
				calls = []

				def dictionary(text, calls=calls):
					calls.append(text)
					return text.replace("测试词", "仙乐飘飘")

				wv.dictionaries.processText = dictionary
				if timing == "before":
					wv.filter_point.register(wv.detector.add_detected_language_commands)
					wv.filter_point.moveToEnd(wv.detector.add_detected_language_commands, False)
					wv.pipeline.order_move_to_start_register()
				with mock.patch.object(
					filter_._normalizer._rules, "transform", wraps=filter_._normalizer._rules.transform
				) as transform:
					wv.speak(wv.synth, wv.filter_point.apply(iter(["测试词，盛汤"])))
					transform.assert_called_once()
				self.assertEqual(["测试词，盛汤"], calls)
				self.assertEqual([["仙月飘飘，呈汤"]], wv.voices["zh_CN"].output)

	def test_unicode_preferences_follow_their_configured_detection_stage(self):
		for timing in ("before", "after"):
			with self.subTest(timing=timing), upstream_worldvoice() as wv:
				self.register(wv)
				wv.config.conf["WorldVoice"]["autoLanguageSwitching"]["DetectLanguageTiming"] = timing
				wv.detector.speechSymbols.symbols["盛"] = types.SimpleNamespace(
					replacement="胜", language="zh_CN", mode=1
				)
				if timing == "before":
					wv.filter_point.register(wv.detector.add_detected_language_commands)
					wv.filter_point.moveToEnd(wv.detector.add_detected_language_commands, False)
					wv.pipeline.order_move_to_start_register()
				wv.speak(wv.synth, wv.filter_point.apply(["盛汤"]))
				# Deliberately document actual ordering instead of privately moving
				# WorldVoice's Unicode dictionary or pretending conflicts vanish.
				self.assertEqual([["胜汤" if timing == "before" else "呈汤"]], wv.voices["zh_CN"].output)

	def test_public_filter_character_commands_and_fail_open(self):
		with upstream_worldvoice() as wv:
			filter_ = self.register(wv)
			mode = CharacterModeCommand(True)
			sequence = [wv.WVLangChangeCommand("zh_CN"), mode, "仙乐盛汤"]
			self.assertEqual(sequence, wv.filter_point.apply(iter(sequence)))
			with mock.patch.object(filter_._normalizer, "normalize", side_effect=RuntimeError()):
				self.assertEqual(["盛汤"], wv.filter_point.apply(iter(["盛汤"])))

	def test_no_private_function_changes_when_public_filter_is_removed(self):
		with upstream_worldvoice() as wv:
			original = wv.lang_cmd_to_voice
			filter_ = self.register(wv)
			wv.filter_point.unregister(filter_)
			self.assertIs(original, wv.lang_cmd_to_voice)
			self.assertEqual(["盛汤"], list(wv.filter_point.apply(iter(["盛汤"]))))
