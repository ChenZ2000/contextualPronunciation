"""Global text normalization, independent of engines, voices and language tags.

Only explicit character/spelling commands suppress contextual rewriting. Other
commands are preserved by identity; context never crosses a command boundary.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import Any

from .apostrophe import APOSTROPHES, prepare_apostrophes_for_nvda
from .rules import CompiledRules


@dataclass(frozen=True, slots=True)
class RuntimeOptions:
	enabled: bool = True
	chinese_polyphones_enabled: bool = True
	extended_lexicon_enabled: bool = False
	normalize_apostrophes: bool = True
	strict_mode: bool = True
	custom_entries: str = ""
	custom_templates: str = ""
	disabled_rules: str = ""


class SpeechSequenceNormalizer:
	def __init__(self, *, rules: CompiledRules, character_mode_command_type: type):
		self._rules = rules
		self._character_mode_command_type = character_mode_command_type
		self._fast_gate = frozenset((*rules.triggers, *APOSTROPHES))

	def normalize(
		self,
		sequence: Iterable[Any],
		*,
		options: RuntimeOptions,
		reading_targets: frozenset[str] | None = None,
	) -> list[Any]:
		# Some public filters return generators. Consume once so downstream
		# consumers and our own fail-open handler receive a reusable sequence.
		if not isinstance(sequence, list):
			sequence = list(sequence)
		character_mode = False
		gate = self._fast_gate if reading_targets is None else reading_targets
		result: list[Any] | None = None
		for index, item in enumerate(sequence):
			new_item = item
			if isinstance(item, self._character_mode_command_type):
				character_mode = bool(item.state)
			elif isinstance(item, str) and not character_mode and not gate.isdisjoint(item):
				# Closing-quote protection belongs to the mandatory symbol metadata,
				# so it still applies when optional contextual rewriting is disabled.
				if reading_targets is None:
					new_item = prepare_apostrophes_for_nvda(
						item, normalize_curly=options.enabled and options.normalize_apostrophes
					)
				if options.enabled and options.chinese_polyphones_enabled:
					kwargs = {} if reading_targets is None else {"targets": reading_targets}
					new_item = self._rules.transform(new_item, strict=options.strict_mode, **kwargs)
			if result is None:
				if new_item is item or new_item == item:
					continue
				result = list(sequence[:index])
			result.append(new_item)
		return sequence if result is None else result


class FailOpenSpeechFilter:
	"""Preserve the buffered original if our normalization fails.

	An upstream generator failure cannot be undone here; that is distinct from
	this plugin failing after the original sequence has been materialized.
	"""

	def __init__(
		self,
		*,
		normalizer: SpeechSequenceNormalizer,
		options_provider: Callable[[], RuntimeOptions],
		error_reporter: Callable[[], None] | None = None,
	):
		self._normalizer = normalizer
		self._options_provider = options_provider
		self._error_reporter = error_reporter

	def replace_normalizer(self, normalizer: SpeechSequenceNormalizer) -> None:
		self._normalizer = normalizer

	def guard_queued_readings(self, speechSequence, **_kwargs):  # noqa: N803 - NVDA event argument
		"""Last public queue boundary, after speech dictionaries and symbols.

		Only residual targets in the reviewed edge/row families are revisited.
		Already rendered anchors do not match these targets. Do not rewrite
		symbol output, add pauses, or assume adjacent strings are token barriers.
		"""
		if not isinstance(speechSequence, list):
			return
		try:
			result = self._normalizer.normalize(
				speechSequence,
				options=self._options_provider(),
				reading_targets=frozenset("和边邊行"),
			)
			if result is not speechSequence:
				speechSequence[:] = result
		except Exception:
			if self._error_reporter is not None:
				try:
					self._error_reporter()
				except Exception:
					pass

	def __call__(self, sequence: Iterable[Any]) -> list[Any]:
		if not isinstance(sequence, list):
			sequence = list(sequence)
		try:
			return self._normalizer.normalize(sequence, options=self._options_provider())
		except Exception:
			if self._error_reporter is not None:
				try:
					self._error_reporter()
				except Exception:
					pass
			return sequence
