"""Declarative, bounded-context Chinese polyphone rule engine.

The module has no NVDA dependencies. JSON is parsed and compiled once at add-on
startup; the synchronous speech path performs no file access or unbounded regex work.
Ordinary Chinese lexemes match inside sentences, not just delimiter-separated
tokens. Explicit left/rightBoundary flags are only for genuinely delimited
patterns. Resolve every target against the original text before rendering;
protective lexical overlaps take precedence without blocking other occurrences.
"""

from __future__ import annotations

import json
import unicodedata
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any, Final

from .lexicon import PhraseLexicon, load_default_lexicon, load_reading_metadata
from .syntax import ArgumentParser, load_argument_parser
from .templates import CompiledTemplates, load_templates

SCHEMA_VERSION: Final = 1
_CONFIDENCE_LEVELS: Final = frozenset({"high", "medium"})
_CHINESE_NUMERALS: Final = frozenset("〇零一二两三四五六七八九十百千万亿两俩")
_MEASURE_WORDS: Final = frozenset("碗杯勺盆锅盘瓶壶桶盒袋份盅罐匙")
_ROW_FOLLOWING_WORDS: Final = (
	"内容",
	"文字",
	"文本",
	"代码",
	"数据",
	"单元格",
	"开头",
	"末尾",
	"开始",
	"结束",
	"标题",
	"记录",
	"结果",
	"输入",
	"輸入",
	"编辑",
	"編輯",
	"显示",
	"顯示",
	"选择",
	"選擇",
	"选中",
	"選中",
	"格式",
	"注释",
	"註釋",
	"字符串",
	"模式",
	"排列",
	"表格",
	"列表",
)
_RANK_PREFIXES: Final = ("家中", "兄弟中", "姐妹中", "同辈中", "排行", "排行中")
_INDEFINITE_ROW_QUANTITIES: Final = ("若干", "多少", "几", "幾")
_FURNITURE_JI: Final = ("茶几", "条几", "條几", "案几", "炕几", "窗几")
_ROW_QUANTITY_PREFIXES: Final = (
	"写了",
	"寫了",
	"写下",
	"寫下",
	"读了",
	"讀了",
	"删除",
	"刪除",
	"删去",
	"刪去",
	"插入",
	"包含",
	"共有",
	"剩下",
	"还剩",
	"還剩",
	"这",
	"這",
	"那",
	"前",
	"后",
	"後",
	"共",
)
_INLINE_SPACES: Final = frozenset(" \t\u00a0\u3000")
_MAX_PHRASE_LENGTH: Final = 64


class RuleDataError(ValueError):
	"""The declarative rule data is invalid."""


@dataclass(frozen=True, slots=True)
class PhraseRule:
	id: str
	target: str
	phrase: str
	pivot: int
	reading_id: str | None
	protect: bool
	confidence: str
	priority: int
	order: int
	left_boundary: bool
	right_boundary: bool
	layer: int
	contextual: bool = False

	@property
	def sort_key(self) -> tuple[int, int, int, int, int]:
		# A matching negative/protection rule always wins. Within the same
		# decision class, prefer the longest and then highest-priority phrase.
		return (-self.layer, -int(self.protect), -len(self.phrase), -self.priority, self.order)


@dataclass(frozen=True, slots=True)
class ReadingDecision:
	reading_id: str | None
	protect: bool = False
	speech: bool = True
	rule_id: str = ""
	user: bool = False
	contextual: bool = False


class CompiledRules:
	"""Immutable compiled rules suitable for NVDA's synchronous speech path."""

	def __init__(
		self,
		*,
		triggers: frozenset[str],
		buckets: dict[tuple[str, str | None, str | None], tuple[PhraseRule, ...]],
		structural_rules: dict[str, tuple[str, ...]],
		reading_replacements: dict[str, str],
		lexicon: PhraseLexicon | None = None,
		templates: CompiledTemplates | None = None,
		syntax: ArgumentParser | None = None,
		syntax_blockers: CompiledRules | None = None,
	):
		self._curated_triggers = triggers
		self._lexicon = lexicon
		self._templates = templates
		self.syntax = syntax
		self._syntax_blockers = syntax_blockers
		self.triggers = triggers | lexicon.triggers if lexicon is not None else triggers
		if templates is not None:
			self.triggers |= templates.triggers
		if syntax is not None:
			self.triggers |= syntax.triggers
		self._buckets = buckets
		self._structural_rules = structural_rules
		self._reading_replacements = MappingProxyType(dict(reading_replacements))

	@property
	def renderings(self):
		"""One immutable reading-to-text mapping, shared by all speech outputs."""
		return self._reading_replacements

	@property
	def lexicon(self):
		"""Engine-neutral immutable phrase readings, or None when disabled."""
		return self._lexicon

	@property
	def templates(self):
		"""Compiled context templates for contributor inspection."""
		return self._templates

	@classmethod
	def empty(cls) -> CompiledRules:
		return cls(triggers=frozenset(), buckets={}, structural_rules={}, reading_replacements={})

	@classmethod
	def from_json_file(cls, path: str | Path) -> CompiledRules:
		with Path(path).open("r", encoding="utf-8") as source:
			data = json.load(source)
		return cls.from_mapping(data)

	@classmethod
	def from_mapping(
		cls,
		data: Any,
		*,
		lexicon: PhraseLexicon | None = None,
		templates: CompiledTemplates | None = None,
		syntax: ArgumentParser | None = None,
		syntax_blockers: CompiledRules | None = None,
	) -> CompiledRules:
		if not isinstance(data, dict) or data.get("schemaVersion") != SCHEMA_VERSION:
			raise RuleDataError(f"Expected rule schema version {SCHEMA_VERSION}")

		readings = data.get("readings")
		characters = data.get("characters")
		if not isinstance(readings, dict) or not isinstance(characters, dict):
			raise RuleDataError("'readings' and 'characters' must be objects")

		replacements: dict[str, str] = {}
		for reading_id, definition in readings.items():
			if not isinstance(reading_id, str) or not isinstance(definition, dict):
				raise RuleDataError("Invalid reading definition")
			replacement = definition.get("replacement")
			if not isinstance(replacement, str) or len(replacement) != 1 or not replacement.isalpha():
				raise RuleDataError(f"Reading {reading_id!r} must have a single-letter/character replacement")
			replacements[reading_id] = replacement

		mutable_buckets: dict[tuple[str, str | None, str | None], list[PhraseRule]] = {}
		structural: dict[str, tuple[str, ...]] = {}
		seen_group_ids: set[str] = set()
		order = 0
		for target, definition in characters.items():
			if not isinstance(target, str) or len(target) != 1 or not isinstance(definition, dict):
				raise RuleDataError(f"Invalid target character {target!r}")
			structural_names = definition.get("structuralRules", [])
			if not isinstance(structural_names, list) or not all(isinstance(name, str) for name in structural_names):
				raise RuleDataError(f"Invalid structural rules for {target!r}")
			unknown = set(structural_names).difference(_STRUCTURAL_HANDLERS)
			if unknown:
				raise RuleDataError(f"Unknown structural rules for {target!r}: {sorted(unknown)!r}")
			for name in structural_names:
				expected_target, reading_id = _STRUCTURAL_REQUIREMENTS[name]
				if target != expected_target or reading_id not in replacements:
					raise RuleDataError(f"Structural rule {name!r} has an invalid target or missing reading")
			structural[target] = tuple(structural_names)

			groups = definition.get("phraseGroups", [])
			if not isinstance(groups, list):
				raise RuleDataError(f"Invalid phrase groups for {target!r}")
			for group in groups:
				if not isinstance(group, dict):
					raise RuleDataError(f"Invalid phrase group for {target!r}")
				group_id = group.get("id")
				if not isinstance(group_id, str) or not group_id or group_id in seen_group_ids:
					raise RuleDataError(f"Invalid or duplicate rule id {group_id!r}")
				seen_group_ids.add(group_id)
				protect = group.get("protect", False)
				reading_id = group.get("reading")
				if not isinstance(protect, bool) or (protect == (reading_id is not None)):
					raise RuleDataError(f"Rule {group_id!r} must specify exactly one of protect/readings")
				if reading_id is not None and reading_id not in replacements:
					raise RuleDataError(f"Unknown reading {reading_id!r} in {group_id!r}")
				confidence = group.get("confidence", "high")
				if confidence not in _CONFIDENCE_LEVELS:
					raise RuleDataError(f"Invalid confidence in {group_id!r}")
				priority = group.get("priority", 100)
				layer = group.get("layer", 0)
				left_boundary = group.get("leftBoundary", False)
				right_boundary = group.get("rightBoundary", False)
				phrases = group.get("phrases")
				contextual = group.get("contextualPhrases", [])
				if (
					not isinstance(priority, int)
					or not isinstance(left_boundary, bool)
					or layer not in (0, 1)
					or not isinstance(right_boundary, bool)
					or not isinstance(phrases, list)
					or not phrases
				):
					raise RuleDataError(f"Invalid phrases or priority in {group_id!r}")
				if (
					not isinstance(contextual, list)
					or any(p not in phrases for p in contextual)
					or (contextual and (not protect or layer))
				):
					raise RuleDataError(f"Invalid contextual protection in {group_id!r}")
				for phrase in phrases:
					if (
						not isinstance(phrase, str)
						or not 2 <= len(phrase) <= _MAX_PHRASE_LENGTH
						or target not in phrase
					):
						raise RuleDataError(f"Phrase {phrase!r} in {group_id!r} does not contain {target!r}")
					for pivot, character in enumerate(phrase):
						if character != target:
							continue
						left = phrase[pivot - 1] if pivot else None
						right = phrase[pivot + 1] if pivot + 1 < len(phrase) else None
						rule = PhraseRule(
							id=group_id,
							target=target,
							phrase=phrase,
							pivot=pivot,
							reading_id=reading_id,
							protect=protect,
							confidence=confidence,
							priority=priority,
							order=order,
							left_boundary=left_boundary,
							right_boundary=right_boundary,
							layer=layer,
							contextual=phrase in contextual,
						)
						order += 1
						mutable_buckets.setdefault((target, left, right), []).append(rule)

		buckets = {key: tuple(sorted(rules, key=lambda rule: rule.sort_key)) for key, rules in mutable_buckets.items()}
		return cls(
			triggers=frozenset(characters),
			buckets=buckets,
			structural_rules=structural,
			reading_replacements=replacements,
			lexicon=lexicon,
			templates=templates,
			syntax=syntax,
			syntax_blockers=syntax_blockers,
		)

	def transform(
		self,
		text: str,
		*,
		strict: bool = True,
		renderings: Mapping[str, str] | None = None,
		targets: frozenset[str] | None = None,
	) -> str:
		# Classify original text independently of output rendering. Explicit
		# mappings serve offline consumers; no runtime voice selection occurs.
		if renderings is None:
			renderings = self._reading_replacements
		if not renderings:
			return text
		if not text or self.triggers.isdisjoint(text):
			return text
		replacements = {}
		for index, decision in self.resolve(text, strict=strict, speech_only=True).items():
			if targets is not None and text[index] not in targets:
				continue
			if decision.speech and not decision.protect and decision.reading_id is not None:
				replacement = renderings.get(decision.reading_id)
				if replacement is not None and replacement != text[index]:
					replacements[index] = replacement
		if not replacements:
			return text
		result = list(text)
		for index, replacement in replacements.items():
			result[index] = replacement
		return "".join(result)

	def resolve(self, text: str, *, strict: bool = True, speech_only: bool = False) -> dict[int, ReadingDecision]:
		"""Shared speech/braille reading decisions, at ORIGINAL code-point offsets.

		Missing entries and protected decisions are abstentions. No homophone is
		used to infer a reading. Dictionary defaults may inform braille, while
		conservative speech replacement only forces supported alternatives.
		Speech-only projection omits non-speaking lexical annotations, but uses
		the identical full-dictionary segmentation and core/template decisions.
		"""
		decisions = {}
		syntax_context = None
		lexicon = self._lexicon
		if lexicon is not None and not lexicon.analysis_triggers.isdisjoint(text):
			for span in lexicon.annotate(text, speech_only=speech_only):
				for offset, (character, reading) in enumerate(zip(span.text, span.readings, strict=True)):
					if (
						reading is not None
						and character in lexicon.defaults
						and character not in lexicon.reserved_targets
					):
						speech = character in lexicon.triggers and (
							reading != lexicon.defaults[character] or offset in span.forced_offsets
						)
						if speech_only and not speech:
							continue
						decisions[span.start + offset] = ReadingDecision(
							reading,
							speech=speech,
							rule_id=span.source + ":" + span.text,
							contextual=bool(
								self.syntax is not None and self.syntax.contextual_lexeme(span.text, offset)
							),
						)
		for index, target in enumerate(text):
			core_decision = None
			if target in self._curated_triggers:
				core_decision = self._phrase_decision(text, index, target, strict=strict)
				if core_decision is None or core_decision.contextual and not core_decision.user:
					core_decision = self._structural_decision(text, index, target) or core_decision
			template = (
				self._templates.decision(text, index)
				if self._templates is not None and target in self._templates.triggers
				else None
			)
			if template is not None and (core_decision is None or template[2] and not core_decision.user):
				reading, rule_id, user = template
				decisions[index] = ReadingDecision(reading, protect=reading is None, rule_id=rule_id, user=user)
			elif core_decision is not None:
				decisions[index] = core_decision
			decision = decisions.get(index)
			if (
				(decision is None or decision.contextual and not decision.user)
				and self.syntax is not None
				and target in self.syntax.triggers
			):
				# A fallback must not re-enable a user's disabled lexical/structural
				# rule via a more general construction. Only explicitly conditional
				# BUILT-IN protections can yield to syntax; user keep never can.
				blockers = self._syntax_blockers
				if blockers is not None and (
					blockers._phrase_decision(text, index, target, strict=False) is not None
					or blockers._structural_decision(text, index, target) is not None
				):
					continue
				if syntax_context is None:
					syntax_context = self.syntax.context(text)
				if (parsed := self.syntax.analyze(text, index, syntax_context)) is not None:
					decisions[index] = ReadingDecision(parsed.reading, rule_id=parsed.rule_id)
		return decisions

	def _phrase_decision(self, text: str, index: int, target: str, *, strict: bool) -> ReadingDecision | None:
		left = text[index - 1] if index else None
		right = text[index + 1] if index + 1 < len(text) else None
		keys = (
			(target, left, right),
			(target, left, None),
			(target, None, right),
			(target, None, None),
		)
		best: PhraseRule | None = None
		for key in keys:
			for rule in self._buckets.get(key, ()):
				if strict and not rule.protect and rule.confidence != "high":
					continue
				start = index - rule.pivot
				if start < 0 or not text.startswith(rule.phrase, start):
					continue
				if rule.left_boundary and not _is_left_boundary(text, start):
					continue
				# Delimiters are opt-in constraints, not Chinese word segmentation.
				# A known lexeme such as 盛汤 remains valid in 盛汤之后盛饭.
				if rule.right_boundary and not _is_boundary(text, start + len(rule.phrase)):
					continue
				if best is None or rule.sort_key < best.sort_key:
					best = rule
		if best is None:
			return None
		return ReadingDecision(
			reading_id=best.reading_id,
			protect=best.protect,
			rule_id=best.id,
			user=bool(best.layer),
			contextual=best.contextual,
		)

	def _structural_decision(self, text: str, index: int, target: str) -> ReadingDecision | None:
		for name in self._structural_rules.get(target, ()):
			reading_id = _STRUCTURAL_HANDLERS[name](text, index)
			if reading_id is not None:
				return ReadingDecision(reading_id=reading_id, rule_id=name)
		return None


def _number_start_left(text: str, end: int, *, maximum: int = 12) -> int | None:
	position = end
	consumed = 0
	while position >= 0 and consumed < maximum:
		character = text[position]
		if not (character.isdigit() or character in _CHINESE_NUMERALS):
			break
		position -= 1
		consumed += 1
	if position >= 0 and _is_number(text[position]):
		return None  # Do not accept only the tail of an over-limit number.
	return position + 1 if consumed else None


def _number_end_right(text: str, start: int, *, maximum: int = 12) -> int | None:
	position = start
	consumed = 0
	while position < len(text) and consumed < maximum:
		character = text[position]
		if not (character.isdigit() or character in _CHINESE_NUMERALS):
			break
		position += 1
		consumed += 1
	if position < len(text) and _is_number(text[position]):
		return None
	return position if consumed else None


def _is_number(character: str) -> bool:
	return character.isdigit() or character in _CHINESE_NUMERALS


def _skip_spaces(text: str, position: int, step: int) -> int:
	for _ in range(4):
		if not 0 <= position < len(text) or text[position] not in _INLINE_SPACES:
			break
		position += step
	return position


def _is_boundary(text: str, position: int) -> bool:
	"""A local pronunciation-rule delimiter, not a general linguistic word boundary.

	Unicode separates punctuation (P) from symbols (S): $, +, |, ^ and emoji
	are symbols and must delimit bounded phrases/row labels too. Keep letters,
	numbers, combining marks and non-whitespace controls conservative. Do not
	strip punctuation, scan ahead, or change NVDA's symbol reporting policy.
	All left/right phrase and numeric-rule checks share this constant-time test.
	"""
	if position >= len(text):
		return True
	character = text[position]
	return character.isspace() or unicodedata.category(character)[0] in {"P", "S", "Z"}


def _is_left_boundary(text: str, position: int) -> bool:
	return position <= 0 or _is_boundary(text, position - 1)


def _row_ordinal(text: str, index: int) -> str | None:
	number_start = _number_start_left(text, _skip_spaces(text, index - 1, -1))
	if number_start is None:
		return None
	ordinal_position = _skip_spaces(text, number_start - 1, -1)
	if ordinal_position < 0 or text[ordinal_position] != "第":
		return None
	if _is_boundary(text, index + 1) or text.startswith(_ROW_FOLLOWING_WORDS, index + 1):
		return "hang2"
	return None


def _row_column_count(text: str, index: int) -> str | None:
	number_start = _number_start_left(text, _skip_spaces(text, index - 1, -1))
	if number_start is None:
		return None
	right_end = _number_end_right(text, _skip_spaces(text, index + 1, 1))
	if right_end is None:
		return None
	column_position = _skip_spaces(text, right_end, 1)
	if column_position < len(text) and text[column_position] == "列":
		return "hang2"
	return None


def _row_count(text: str, index: int) -> str | None:
	"""Recognize a bounded quantity of text/table rows.

	Requiring a number before ``行`` (with bounded optional spaces) and either a boundary or a
	known row-content noun afterwards avoids false positives such as ``第十二行星``.
	The motion construction ``日行二百里`` has its number after ``行`` and is
	therefore outside this rule by construction.
	"""
	if _number_start_left(text, _skip_spaces(text, index - 1, -1)) is None:
		return None
	if _is_boundary(text, index + 1) or text.startswith(_ROW_FOLLOWING_WORDS, index + 1):
		return "hang2"
	return None


def _row_indefinite_quantity(text: str, index: int) -> str | None:
	"""Productive row quantities, not an unrestricted ``.几行.`` replacement.

	Lexical protections are resolved before this handler. Furniture 几 is
	blocked locally; bounded spaces never cross newlines or speech commands.
	A numeral suffix (十几/二十多/百余) must have a complete bounded number.
	Unlike bare numeric UI labels, these quantifiers can precede a predicate:
	``这几行很好`` does not require punctuation after 行.
	"""
	end = _skip_spaces(text, index - 1, -1) + 1
	if end <= 0:
		return None
	window = text[max(0, end - 15) : end]
	if window.endswith(_FURNITURE_JI):
		return None
	if window[-1] in "数數":
		# 数 is also the noun suffix in 参数/读数/约数/岁数. Require a
		# delimited quantity, a counting construction, or explicit row content.
		# Do not let the following predicate 行吗 turn a noun into a quantifier.
		if (
			_is_left_boundary(text, end - 1)
			or window[:-1].endswith(_ROW_QUANTITY_PREFIXES)
			or text.startswith(_ROW_FOLLOWING_WORDS, index + 1)
		):
			return "hang2"
		return None
	if window[-1] in "几幾多余餘":
		start = _number_start_left(text, end - 2)
		if start is not None:
			return "hang2"
		if end >= 2 and _is_number(text[end - 2]):
			return None  # Never accept the tail of an over-limit quantity.
	if window.endswith("多") and not text.startswith(("不义", "不義"), index + 1):
		if window[:-1].endswith("至"):
			return None  # 至多 needs its own explicit number.
		if _is_boundary(text, index + 1) or text.startswith(_ROW_FOLLOWING_WORDS, index + 1):
			return "hang2"
	if window.endswith(_INDEFINITE_ROW_QUANTITIES):
		return "hang2"
	return None


def _rank_order(text: str, index: int) -> str | None:
	right_end = _number_end_right(text, index + 1, maximum=4)
	if right_end is None or not _is_boundary(text, right_end):
		return None
	if index == 0:
		return "hang2"
	left_window = text[max(0, index - 4) : index]
	if left_window.endswith(_RANK_PREFIXES):
		return "hang2"
	return None


def _row_label(text: str, index: int) -> str | None:
	"""Recognize standalone UI labels: 行 12, 行：12, 行12列3.

	A lexical/motion prefix is deliberately disallowed. No newline or command
	boundary is traversed and no number is converted to an integer.
	"""
	if not _is_left_boundary(text, index):
		return None
	start = _skip_spaces(text, index + 1, 1)
	if start < len(text) and text[start] in ":：":
		start = _skip_spaces(text, start + 1, 1)
	end = _number_end_right(text, start)
	if end is not None and (_is_boundary(text, end) or text.startswith("列", end)):
		return "hang2"
	return None


def _serving_quantity(text: str, index: int) -> str | None:
	start = _skip_spaces(text, index + 1, 1)
	right_end = start + 1 if text.startswith("半", start) else _number_end_right(text, start, maximum=8)
	if right_end is None or right_end >= len(text):
		return None
	right_end = _skip_spaces(text, right_end, 1)
	if right_end >= len(text):
		return None
	if text[right_end] in _MEASURE_WORDS:
		return "cheng2"
	return None


_STRUCTURAL_HANDLERS: Final = {
	"rowOrdinal": _row_ordinal,
	"rowColumnCount": _row_column_count,
	"rowCount": _row_count,
	"rowIndefiniteQuantity": _row_indefinite_quantity,
	"rankOrder": _rank_order,
	"rowLabel": _row_label,
	"servingQuantity": _serving_quantity,
}
_STRUCTURAL_REQUIREMENTS: Final = {
	"rowOrdinal": ("行", "hang2"),
	"rowColumnCount": ("行", "hang2"),
	"rowCount": ("行", "hang2"),
	"rowIndefiniteQuantity": ("行", "hang2"),
	"rankOrder": ("行", "hang2"),
	"rowLabel": ("行", "hang2"),
	"servingQuantity": ("盛", "cheng2"),
}


def load_default_rules(
	*, custom_entries: str = "", disabled_rules: str = "", extended: bool = True, custom_templates: str = ""
) -> CompiledRules:
	with (Path(__file__).with_name("data") / "rules_zh_CN.json").open("r", encoding="utf-8") as source:
		data = json.load(source)
	database = load_reading_metadata()
	lexicon = load_default_lexicon() if extended else None
	templates = load_templates(database.allowed_readings, custom_templates)
	disabled = frozenset(value.strip() for value in disabled_rules.replace(",", "\n").splitlines() if value.strip())
	syntax = load_argument_parser(database.allowed_readings, disabled)
	all_syntax = load_argument_parser(database.allowed_readings)
	# Turning off broad matching must not disable reviewed/custom templates.
	data["readings"] = {
		**{reading: {"replacement": ch} for reading, ch in database.renderings.items()},
		**data["readings"],
	}
	syntax_blockers = None
	if disabled:
		syntax_blockers = CompiledRules.from_mapping(
			{
				"schemaVersion": SCHEMA_VERSION,
				"readings": data["readings"],
				"characters": {
					target: {
						"phraseGroups": [g for g in definition["phraseGroups"] if g["id"] in disabled],
						"structuralRules": [name for name in definition["structuralRules"] if name in disabled],
					}
					for target, definition in data["characters"].items()
				},
			}
		)
	if custom_entries or disabled_rules:
		apply_user_overrides(data, custom_entries, disabled_rules, extra_disabled_ids={f.id for f in all_syntax.frames})
	return CompiledRules.from_mapping(
		data, lexicon=lexicon, templates=templates, syntax=syntax, syntax_blockers=syntax_blockers
	)


def apply_user_overrides(
	data: dict, custom_entries: str, disabled_rules: str, *, extra_disabled_ids=frozenset()
) -> None:
	"""Validate and merge bounded literal rules, outside the speech hot path.

	Lines have the form phrase|target|readingId (or keep). They are never regular
	expressions or executable code. Explicit user rules outrank built-in rules.
	"""
	if len(custom_entries) > 32_768 or len(disabled_rules) > 16_384:
		raise RuleDataError("Custom configuration exceeds the safe size limit")
	characters = data["characters"]
	known_ids = {group["id"] for definition in characters.values() for group in definition["phraseGroups"]}
	# Structural IDs are individually disableable as well.
	known_ids.update(_STRUCTURAL_HANDLERS)
	known_ids.update(extra_disabled_ids)
	disabled = {value.strip() for value in disabled_rules.replace(",", "\n").splitlines() if value.strip()}
	unknown = disabled.difference(known_ids)
	if unknown:
		raise RuleDataError(f"Unknown disabled rule IDs: {', '.join(sorted(unknown))}")
	for definition in characters.values():
		definition["phraseGroups"] = [g for g in definition["phraseGroups"] if g["id"] not in disabled]
		definition["structuralRules"] = [name for name in definition["structuralRules"] if name not in disabled]
	seen = set()
	entry_count = 0
	for line_number, line in enumerate(custom_entries.splitlines(), 1):
		if not line.strip() or line.lstrip().startswith("#"):
			continue
		entry_count += 1
		parts = [part.strip() for part in line.split("|")]
		if entry_count > 256 or len(parts) != 3:
			raise RuleDataError(f"Line {line_number}: use phrase|target|readingId; maximum 256 entries")
		phrase, target, reading_id = parts
		if (
			len(target) != 1
			or not 2 <= len(phrase) <= _MAX_PHRASE_LENGTH
			or phrase.count(target) != 1
			or any(unicodedata.category(char).startswith("C") for char in phrase)
			or (phrase, target) in seen
		):
			raise RuleDataError(f"Line {line_number}: use a unique 2–64 character phrase with one target character")
		if reading_id != "keep" and reading_id not in data["readings"]:
			raise RuleDataError(f"Line {line_number}: unknown reading ID {reading_id!r}")
		seen.add((phrase, target))
		group = {
			"id": f"user-{line_number}",
			"phrases": [phrase],
			"confidence": "high",
			"layer": 1,
		}
		if reading_id == "keep":
			group["protect"] = True
		else:
			group["reading"] = reading_id
		definition = characters.setdefault(target, {"structuralRules": [], "phraseGroups": []})
		definition["phraseGroups"].append(group)
