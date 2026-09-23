from __future__ import annotations

import builtins
import importlib.util
import inspect
import sys
import types
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
PLUGIN_PATH = ROOT / "addon" / "globalPlugins" / "contextualPronunciation"
PACKAGE_NAME = "_contextualPronunciationGlobalPluginUnderTest"


class FakeExtensionPoint:
	"""Small NVDA 2026.2 Action/Filter-compatible registrar."""

	def __init__(self):
		self.handlers = []

	def register(self, handler):
		if handler not in self.handlers:
			self.handlers.append(handler)

	def moveToEnd(self, handler, last=True):
		if handler not in self.handlers:
			return False
		self.handlers.remove(handler)
		self.handlers.insert(len(self.handlers) if last else 0, handler)
		return True

	def unregister(self, handler):
		try:
			self.handlers.remove(handler)
		except ValueError:
			return False
		return True

	def notify(self, **kwargs):
		for handler in tuple(self.handlers):
			signature = inspect.signature(handler)
			if any(parameter.kind is inspect.Parameter.VAR_KEYWORD for parameter in signature.parameters.values()):
				supported = kwargs
			else:
				supported = {name: value for name, value in kwargs.items() if name in signature.parameters}
			handler(**supported)

	def apply(self, value):
		for handler in tuple(self.handlers):
			value = handler(value)
		return value


class FakeConfig(dict):
	def __init__(self):
		super().__init__(
			{
				"speech": {
					"autoLanguageSwitching": True,
					"autoDialectSwitching": False,
					"reportLanguage": False,
				},
				"contextualPronunciation": {
					"enabled": True,
					"chinesePolyphonesEnabled": True,
					"extendedLexiconEnabled": True,
					"normalizeApostrophes": True,
					"strictMode": True,
					"rendererMode": "auto",
					"customEntries": "",
					"customTemplates": "",
					"disabledRules": "",
				},
			}
		)
		self.spec = {}


class FakeCheckBox:
	def __init__(self, value):
		self._value = value

	def GetValue(self):  # noqa: N802 - mirrors wx API
		return self._value


def _load_plugin(*, legacy_mode="auto"):
	filter_point = FakeExtensionPoint()
	queue_point = FakeExtensionPoint()
	profile_point = FakeExtensionPoint()
	config_conf = FakeConfig()
	config_conf["contextualPronunciation"]["rendererMode"] = legacy_mode
	settings_categories = []

	addon_handler = types.ModuleType("addonHandler")
	addon_handler.initTranslation = lambda: None

	config = types.ModuleType("config")
	config.conf = config_conf
	config.post_configProfileSwitch = profile_point

	extension_points = types.ModuleType("extensionPoints")
	extension_points.Action = FakeExtensionPoint

	class BaseGlobalPlugin:
		def __init__(self):
			self.base_terminated = False

		def terminate(self):
			self.base_terminated = True

	global_plugin_handler = types.ModuleType("globalPluginHandler")
	global_plugin_handler.GlobalPlugin = BaseGlobalPlugin

	class SilentLogger:
		def exception(self, *args, **kwargs):
			pass

		def error(self, *args, **kwargs):
			pass

	log_handler = types.ModuleType("logHandler")
	log_handler.log = SilentLogger()

	class CharacterModeCommand:
		def __init__(self, state):
			self.state = state

	class LangChangeCommand:
		def __init__(self, lang):
			self.lang = lang

	speech = types.ModuleType("speech")
	speech.__path__ = []
	speech.getCurrentLanguage = lambda: "zh_CN"
	speech_commands = types.ModuleType("speech.commands")
	speech_commands.CharacterModeCommand = CharacterModeCommand
	speech_commands.LangChangeCommand = LangChangeCommand
	speech_extensions = types.ModuleType("speech.extensions")
	speech_extensions.filter_speechSequence = filter_point
	speech_extensions.pre_speechQueued = queue_point
	synth_handler = types.ModuleType("synthDriverHandler")
	synth_handler.synthChanged = FakeExtensionPoint()
	synth = types.SimpleNamespace(name="vocalizer_expressive2", voice="Ting-Ting", language="zh_CN")
	synth_handler.getSynth = lambda: synth

	class SettingsPanel:
		pass

	class NVDASettingsDialog:
		categoryClasses = settings_categories

	settings_dialogs = types.ModuleType("gui.settingsDialogs")
	settings_dialogs.NVDASettingsDialog = NVDASettingsDialog
	settings_dialogs.SettingsPanel = SettingsPanel
	gui_helper = types.ModuleType("gui.guiHelper")
	gui_helper.BoxSizerHelper = object
	gui = types.ModuleType("gui")
	gui.__path__ = []
	gui.guiHelper = gui_helper
	wx = types.ModuleType("wx")
	wx.Sizer = object
	wx.CheckBox = object

	stubs = {
		"addonHandler": addon_handler,
		"config": config,
		"extensionPoints": extension_points,
		"globalPluginHandler": global_plugin_handler,
		"logHandler": log_handler,
		"speech": speech,
		"speech.commands": speech_commands,
		"speech.extensions": speech_extensions,
		"synthDriverHandler": synth_handler,
		"gui": gui,
		"gui.guiHelper": gui_helper,
		"gui.settingsDialogs": settings_dialogs,
		"wx": wx,
	}

	spec = importlib.util.spec_from_file_location(
		PACKAGE_NAME,
		PLUGIN_PATH / "__init__.py",
		submodule_search_locations=[str(PLUGIN_PATH)],
	)
	assert spec is not None and spec.loader is not None
	module = importlib.util.module_from_spec(spec)
	with (
		mock.patch.dict(sys.modules, stubs),
		mock.patch.object(builtins, "_", lambda text: text, create=True),
	):
		sys.modules[PACKAGE_NAME] = module
		spec.loader.exec_module(module)
		plugin = module.GlobalPlugin()
		settings_module = sys.modules[f"{PACKAGE_NAME}.settings"]
		return types.SimpleNamespace(
			module=module,
			plugin=plugin,
			settings=settings_module,
			config=config,
			filter_point=filter_point,
			queue_point=queue_point,
			profile_point=profile_point,
			settings_categories=settings_categories,
			synth=synth,
		)


class GlobalPluginIntegrationTests(unittest.TestCase):
	def test_worldvoice_uses_the_same_public_filter_without_private_patching(self):
		from tests.test_worldvoice import upstream_worldvoice

		with upstream_worldvoice() as wv:
			original = wv.lang_cmd_to_voice
			environment = _load_plugin()
			plugin = environment.plugin
			self.addCleanup(plugin.terminate)
			sequence = wv.pipeline.apply_speech_dictionaries(iter(["仙乐飘飘，盛汤之后盛饭"]))
			with mock.patch.object(plugin._rules, "transform", wraps=plugin._rules.transform) as transform:
				sequence = plugin._speech_filter(sequence)
				self.assertEqual(["仙月飘飘，呈汤之后呈饭"], sequence)
				wv.speak(wv.synth, sequence)
				transform.assert_called_once()
			self.assertEqual([["仙月飘飘，呈汤之后呈饭"]], wv.voices["zh_CN"].output)
			self.assertIs(original, wv.lang_cmd_to_voice)
			self.assertFalse(hasattr(plugin, "_worldvoice"))

	def tearDown(self):
		for module_name in tuple(sys.modules):
			if module_name == PACKAGE_NAME or module_name.startswith(f"{PACKAGE_NAME}."):
				sys.modules.pop(module_name, None)

	def test_lifecycle_profile_switch_and_immediate_settings_refresh(self):
		environment = _load_plugin()
		plugin = environment.plugin
		settings = environment.settings

		self.assertIn(settings.CONFIG_SECTION, environment.config.conf.spec)
		self.assertEqual([plugin._speech_filter], environment.filter_point.handlers)
		self.assertEqual([plugin._speech_filter.guard_queued_readings], environment.queue_point.handlers)
		self.assertEqual([plugin._on_profile_switch], environment.profile_point.handlers)
		self.assertEqual([plugin._on_settings_changed], settings.options_changed.handlers)
		self.assertEqual([settings.ContextualPronunciationSettingsPanel], environment.settings_categories)
		self.assertEqual(["航首"], environment.filter_point.apply(["行首"]))

		section = environment.config.conf[settings.CONFIG_SECTION]
		section["chinesePolyphonesEnabled"] = False
		environment.profile_point.notify(prevConf={"profile": "previous"})
		self.assertFalse(plugin._options.chinese_polyphones_enabled)
		self.assertEqual(["行首"], environment.filter_point.apply(["行首"]))

		panel = object.__new__(settings.ContextualPronunciationSettingsPanel)
		panel.enable_checkbox = FakeCheckBox(True)
		panel.chinese_checkbox = FakeCheckBox(True)
		panel.lexicon_checkbox = FakeCheckBox(True)
		panel.apostrophe_checkbox = FakeCheckBox(False)
		panel.strict_checkbox = FakeCheckBox(False)
		panel.custom_entries_edit = FakeCheckBox("")
		panel.custom_templates_edit = FakeCheckBox("")
		panel.disabled_rules_edit = FakeCheckBox("")
		panel.onSave()
		self.assertTrue(plugin._options.chinese_polyphones_enabled)
		self.assertFalse(plugin._options.normalize_apostrophes)
		self.assertFalse(plugin._options.strict_mode)
		self.assertEqual(["航首"], environment.filter_point.apply(["行首"]))

		plugin.terminate()
		self.assertEqual([], environment.filter_point.handlers)
		self.assertEqual([], environment.queue_point.handlers)
		self.assertEqual([], environment.profile_point.handlers)
		self.assertEqual([], settings.options_changed.handlers)
		self.assertEqual([], environment.settings_categories)
		self.assertTrue(plugin.base_terminated)

	def test_no_synth_or_language_queries_are_needed_for_global_rewriting(self):
		environment = _load_plugin()
		self.addCleanup(environment.plugin.terminate)
		for synth, voice, language in (
			("WorldVoice", "English", "en_US"),
			("sapi5", "Huihui", "zh_CN"),
			("oneCore", "Meijia", "zh_TW"),
			("unknown", None, None),
			("VE", "Sin-Ji", "yue"),
		):
			environment.synth.name, environment.synth.voice, environment.synth.language = synth, voice, language
			self.assertEqual(["航首、呈汤、仙月"], environment.filter_point.apply(["行首、盛汤、仙乐"]))
		self.assertNotIn("synthDriverHandler", environment.module.__dict__)
		self.assertNotIn("speech", environment.module.__dict__)

	def test_legacy_profile_is_removed_and_explicit_off_is_preserved(self):
		for mode in ("auto", "generic", "off"):
			environment = _load_plugin(legacy_mode=mode)
			try:
				section = environment.config.conf[environment.settings.CONFIG_SECTION]
				self.assertEqual("retired", section["rendererMode"])
				self.assertNotIn("rendererMode", environment.settings.CONFIG_SPEC)
				expected = "盛汤" if mode == "off" else "呈汤"
				self.assertEqual([expected], environment.filter_point.apply(["盛汤"]))
			finally:
				environment.plugin.terminate()

	def test_compositional_grammar_is_embedded_in_the_public_default_filter(self):
		environment = _load_plugin()
		self.addCleanup(environment.plugin.terminate)
		section = environment.config.conf[environment.settings.CONFIG_SECTION]
		section["extendedLexiconEnabled"] = False
		environment.settings.options_changed.notify()
		self.assertEqual(
			["崇转，呈那碗刚刚煮好而且非常香甜的红豆粥"],
			environment.filter_point.apply(["重转，盛那碗刚刚煮好而且非常香甜的红豆粥"]),
		)
		section["disabledRules"] = "syntax-repeat-predicate"
		environment.settings.options_changed.notify()
		self.assertEqual(["重转"], environment.filter_point.apply(["重转"]))

	def test_feedback_grammar_reaches_the_public_speech_filter(self):
		environment = _load_plugin()
		self.addCleanup(environment.plugin.terminate)
		self.assertEqual(
			["崇吸收，呈了一碗饭，崇捏，崇飞，虾兵和蟹匠，天兵和天匠"],
			environment.filter_point.apply(["重吸收，盛了一碗饭，重捏，重飞，虾兵和蟹将，天兵和天将"]),
		)
		self.assertEqual(
			["也给我呈了一碗，天兵和天匠一起去吃饭"],
			environment.filter_point.apply(["也给我盛了一碗，天兵和天将一起去吃饭"]),
		)

	def test_custom_entries_are_recompiled_after_settings_and_profile_switch(self):
		environment = _load_plugin()
		apply = environment.filter_point.apply
		section = environment.config.conf[environment.settings.CONFIG_SECTION]
		section["customEntries"] = "行首|行|keep\n同行评审|行|hang2"
		environment.settings.options_changed.notify()
		self.assertEqual(["行首，同航评审"], apply(["行首，同行评审"]))
		section["customEntries"] = "invalid"
		environment.profile_point.notify()
		self.assertEqual(["行尾 Doesn't"], apply(["行尾 Doesn’t"]))
		section["customEntries"] = ""
		environment.settings.options_changed.notify()
		self.assertEqual(["航尾"], apply(["行尾"]))
		environment.plugin.terminate()


if __name__ == "__main__":
	unittest.main()
