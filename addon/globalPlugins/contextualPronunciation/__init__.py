"""NVDA global plugin entry point for contextual pronunciation normalization."""

from __future__ import annotations

import time

import addonHandler
import config
import globalPluginHandler
from logHandler import log
from speech.commands import CharacterModeCommand
from speech.extensions import filter_speechSequence, pre_speechQueued

from . import settings
from .lifecycle import ExtensionRegistration
from .pipeline import FailOpenSpeechFilter, RuntimeOptions, SpeechSequenceNormalizer
from .rules import CompiledRules, load_default_rules

addonHandler.initTranslation()

_ERROR_LOG_INTERVAL_SECONDS = 60.0


class GlobalPlugin(globalPluginHandler.GlobalPlugin):
	"""Register a public NVDA speech-sequence filter and cleanly remove it."""

	def __init__(self):
		super().__init__()
		settings.initialize_config()
		settings.register_settings_panel()
		self._options: RuntimeOptions = settings.get_runtime_options()
		self._last_error_log_time = float("-inf")
		try:
			rules = load_default_rules(
				custom_entries=self._options.custom_entries,
				disabled_rules=self._options.disabled_rules,
				extended=self._options.extended_lexicon_enabled,
				custom_templates=self._options.custom_templates,
			)
		except Exception:
			log.error("Contextual pronunciation rule data could not be loaded; Chinese rules are disabled")
			rules = CompiledRules.empty()

		self._rules = rules
		normalizer = SpeechSequenceNormalizer(
			rules=rules,
			character_mode_command_type=CharacterModeCommand,
		)
		self._speech_filter = FailOpenSpeechFilter(
			normalizer=normalizer,
			options_provider=lambda: self._options,
			error_reporter=self._report_filter_error,
		)
		self._filter_registration = ExtensionRegistration(filter_speechSequence, self._speech_filter)
		self._queue_registration = ExtensionRegistration(pre_speechQueued, self._speech_filter.guard_queued_readings)
		self._profile_registration = ExtensionRegistration(config.post_configProfileSwitch, self._on_profile_switch)
		self._settings_registration = ExtensionRegistration(settings.options_changed, self._on_settings_changed)
		self._profile_registration.start()
		self._settings_registration.start()
		self._filter_registration.start()
		self._queue_registration.start()

	def terminate(self):
		self._filter_registration.stop()
		self._queue_registration.stop()
		self._settings_registration.stop()
		self._profile_registration.stop()
		settings.unregister_settings_panel()
		super().terminate()

	def _on_profile_switch(self, **_kwargs) -> None:
		self._reload_configuration()

	def _on_settings_changed(self) -> None:
		self._reload_configuration()

	def _reload_configuration(self) -> None:
		options = settings.get_runtime_options()
		try:
			rules = load_default_rules(
				custom_entries=options.custom_entries,
				disabled_rules=options.disabled_rules,
				extended=options.extended_lexicon_enabled,
				custom_templates=options.custom_templates,
			)
		except Exception:
			# Do not log exception values: user phrases may contain private text.
			log.error("Contextual pronunciation: invalid rule configuration; Chinese rewriting disabled")
			rules = CompiledRules.empty()
		normalizer = SpeechSequenceNormalizer(
			rules=rules,
			character_mode_command_type=CharacterModeCommand,
		)
		self._options = options
		self._rules = rules
		self._speech_filter.replace_normalizer(normalizer)

	def getReadingAnnotations(self, text: str):  # noqa: N802 - public NVDA-facing API
		"""Original-offset phonetic annotations for braille add-on consumers.

		Does not replace NVDA's braille translation table. Missing spans remain
		unknown; consumers must implement their own scheme's spacing/abbreviation.
		"""
		if not self._options.enabled or not self._options.chinese_polyphones_enabled:
			return ()
		from .braille_readings import annotate

		return annotate(text, self._rules, strict=self._options.strict_mode)

	def _report_filter_error(self) -> None:
		now = time.monotonic()
		if now - self._last_error_log_time < _ERROR_LOG_INTERVAL_SECONDS:
			return
		self._last_error_log_time = now
		# Do not include spoken text in logs; it may contain sensitive content.
		# Exception messages from third-party command/property providers can also
		# contain spoken text. Do not log their values or traceback locals.
		log.error("Contextual pronunciation failed; the original speech sequence was preserved")
