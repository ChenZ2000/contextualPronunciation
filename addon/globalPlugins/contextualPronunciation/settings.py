"""NVDA configuration and settings panel."""

from __future__ import annotations

import addonHandler
import config
import extensionPoints
import gui
import wx
from gui import guiHelper
from gui.settingsDialogs import NVDASettingsDialog, SettingsPanel

from .pipeline import RuntimeOptions
from .rules import RuleDataError, load_default_rules

addonHandler.initTranslation()

CONFIG_SECTION = "contextualPronunciation"
CONFIG_SPEC = {
	"enabled": "boolean(default=True)",
	"chinesePolyphonesEnabled": "boolean(default=True)",
	"extendedLexiconEnabled": "boolean(default=False)",
	"normalizeApostrophes": "boolean(default=True)",
	"strictMode": "boolean(default=True)",
	"customEntries": "string(default='')",
	"customTemplates": "string(default='')",
	"disabledRules": "string(default='')",
}

# Notifies the running global plugin after the settings panel writes new values.
# Waiting for a configuration-profile switch would leave changes stale for the
# remainder of the current NVDA session.
options_changed = extensionPoints.Action()


def initialize_config() -> None:
	config.conf.spec[CONFIG_SECTION] = CONFIG_SPEC


def get_runtime_options() -> RuntimeOptions:
	section = config.conf[CONFIG_SECTION]
	# AggregatedSection exposes get/set but no pop/delete API. Retire an old
	# field in the active profile without flattening/replacing other profiles.
	# This is configuration migration, never a per-utterance selection gate.
	legacy = section.get("rendererMode")
	if legacy is not None and legacy != "retired":
		if legacy == "off":
			section["chinesePolyphonesEnabled"] = False
		section["rendererMode"] = "retired"
	return RuntimeOptions(
		enabled=bool(section["enabled"]),
		chinese_polyphones_enabled=bool(section["chinesePolyphonesEnabled"]),
		extended_lexicon_enabled=bool(section["extendedLexiconEnabled"]),
		normalize_apostrophes=bool(section["normalizeApostrophes"]),
		strict_mode=bool(section["strictMode"]),
		custom_entries=str(section["customEntries"]),
		custom_templates=str(section["customTemplates"]),
		disabled_rules=str(section["disabledRules"]),
	)


class ContextualPronunciationSettingsPanel(SettingsPanel):
	# Translators: Title of the settings panel for this add-on.
	title = _("Context-aware pronunciation")

	def makeSettings(self, settingsSizer: wx.Sizer) -> None:  # noqa: N802 - NVDA API naming
		helper = guiHelper.BoxSizerHelper(self, sizer=settingsSizer)
		section = config.conf[CONFIG_SECTION]

		# Translators: Enables context-sensitive text rewriting. The mandatory
		# symbol metadata remains active so English apostrophes can reach a synth.
		self.enable_checkbox = helper.addItem(
			wx.CheckBox(self, label=_("Enable contextual pronunciation rewriting")),
		)
		self.enable_checkbox.SetValue(section["enabled"])

		# Translators: Enables context-aware Chinese polyphone rules.
		self.chinese_checkbox = helper.addItem(wx.CheckBox(self, label=_("Correct supported Chinese polyphones")))
		self.chinese_checkbox.SetValue(section["chinesePolyphonesEnabled"])
		self.lexicon_checkbox = helper.addItem(
			wx.CheckBox(self, label=_("Use extended phrase lexicon (experimental; may introduce wrong readings)")),
		)
		self.lexicon_checkbox.SetValue(section["extendedLexiconEnabled"])

		# Translators: No engine, voice or language-tag whitelist is consulted.
		helper.addItem(
			wx.StaticText(
				self,
				label=_(
					"Chinese rules apply globally to every voice, regardless of language tags. "
					"They specify Mandarin readings; other languages and dialects may sound incorrect."
				),
			)
		)

		# Translators: Converts a curly apostrophe to ASCII only inside a Latin word.
		self.apostrophe_checkbox = helper.addItem(
			wx.CheckBox(self, label=_("Normalize curly apostrophes inside Latin words")),
		)
		self.apostrophe_checkbox.SetValue(section["normalizeApostrophes"])

		# Translators: Prefer leaving ambiguous text unchanged over guessing a pronunciation.
		self.strict_checkbox = helper.addItem(
			wx.CheckBox(self, label=_("Strict mode (leave ambiguous text unchanged)")),
		)
		self.strict_checkbox.SetValue(section["strictMode"])
		# Translators: In this release, disabling strict mode enables only a
		# literary yuè preference in the technical words for cryptographic keys.
		helper.addItem(
			wx.StaticText(
				self,
				label=_(
					"Turning off strict mode also prefers yuè in 密钥、公钥、私钥. "
					"This is a reading preference, not a proven error.",
				),
			)
		)
		# Translators: Literal custom rules. keep preserves the original text so
		# that a user's existing NVDA speech dictionary can process it later.
		self.custom_templates_edit = helper.addLabeledControl(
			_("Context templates (one per line, e.g. 仙[乐:yuè]; [盛:chéng]{number}{container})"),
			wx.TextCtrl,
			value=section["customTemplates"],
			style=wx.TE_MULTILINE,
		)
		self.custom_entries_edit = helper.addLabeledControl(
			_("Custom literal rules (phrase|target|reading ID or keep; one per line)"),
			wx.TextCtrl,
			value=section["customEntries"],
			style=wx.TE_MULTILINE,
		)
		helper.addItem(
			wx.StaticText(
				self,
				label=_(
					"Reading IDs use numbered pinyin, such as yue4, chang2, lv4; "
					"only available homophones are accepted. "
					"Example: 仙乐|乐|yue4. To preserve: 盛汤|盛|keep.",
				),
			)
		)
		self.disabled_rules_edit = helper.addLabeledControl(
			_("Disabled rule IDs (comma or newline separated)"),
			wx.TextCtrl,
			value=section["disabledRules"],
			style=wx.TE_MULTILINE,
		)

	def isValid(self) -> bool:  # noqa: N802 - NVDA API naming
		try:
			load_default_rules(
				custom_entries=self.custom_entries_edit.GetValue(),
				disabled_rules=self.disabled_rules_edit.GetValue(),
				extended=self.lexicon_checkbox.GetValue(),
				custom_templates=self.custom_templates_edit.GetValue(),
			)
		except (RuleDataError, ValueError) as error:
			gui.messageBox(str(error), _("Invalid pronunciation rules"), wx.OK | wx.ICON_ERROR)
			return False
		return True

	def onSave(self) -> None:  # noqa: N802 - NVDA API naming
		section = config.conf[CONFIG_SECTION]
		section["enabled"] = self.enable_checkbox.GetValue()
		section["chinesePolyphonesEnabled"] = self.chinese_checkbox.GetValue()
		section["extendedLexiconEnabled"] = self.lexicon_checkbox.GetValue()
		section["normalizeApostrophes"] = self.apostrophe_checkbox.GetValue()
		section["strictMode"] = self.strict_checkbox.GetValue()
		section["customEntries"] = self.custom_entries_edit.GetValue()
		section["customTemplates"] = self.custom_templates_edit.GetValue()
		section["disabledRules"] = self.disabled_rules_edit.GetValue()
		options_changed.notify()


def register_settings_panel() -> None:
	if ContextualPronunciationSettingsPanel not in NVDASettingsDialog.categoryClasses:
		NVDASettingsDialog.categoryClasses.append(ContextualPronunciationSettingsPanel)


def unregister_settings_panel() -> None:
	try:
		NVDASettingsDialog.categoryClasses.remove(ContextualPronunciationSettingsPanel)
	except ValueError:
		pass
