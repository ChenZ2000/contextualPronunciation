"""Readable bounded context templates: 仙[乐:yuè], [盛:chéng]{number}{container}.

All literal text is escaped; contributors cannot insert regex or Python. There
is one target, at most four placeholders, and at most 64 characters of context
per side. Equal-priority conflicting readings abstain instead of using order.
"""

from __future__ import annotations

import re
import tomllib
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

from .pinyin import numbered

_TARGET = re.compile(r"\[([^\[\]:]):([^\[\]:]+)\]")
_PLACEHOLDER = re.compile(r"\{([a-zA-Z][a-zA-Z0-9_]*)\}")
_NUMBERS = "0-9０-９〇零一二两三四五六七八九十百千万亿"
MAX_CLASS_VALUES = 64


@dataclass(frozen=True, slots=True)
class ContextTemplate:
	id: str
	pattern: str
	target: str
	reading: str | None
	left: re.Pattern
	right: re.Pattern
	priority: int
	user: bool
	positive: tuple[str, ...] = ()
	negative: tuple[str, ...] = ()
	source: str = ""
	left_hint: frozenset[str] | None = None
	right_hint: frozenset[str] | None = None

	def matches(self, text: str, index: int) -> bool:
		if self.left_hint is not None and (index == 0 or text[index - 1] not in self.left_hint):
			return False
		if self.right_hint is not None and (index + 1 == len(text) or text[index + 1] not in self.right_hint):
			return False
		return bool(
			text[index] == self.target
			and self.left.search(text[max(0, index - 65) : index])
			and self.right.match(text[index + 1 : index + 66])
		)


def _edge_hint(context, classes, *, left=False):
	"""Exact FIRST/LAST-character filter with epsilon handling, not a heuristic.

	Regex remains authoritative. A fully nullable side has no hint; optional
	spaces must also include the following/preceding required token's edge.
	"""
	parts, last = [], 0
	for match in _PLACEHOLDER.finditer(context):
		if literal := context[last : match.start()]:
			parts.append((literal, False))
		parts.append((match[1], True))
		last = match.end()
	if last < len(context):
		parts.append((context[last:], False))
	result = set()
	for value, placeholder in reversed(parts) if left else parts:
		if not placeholder:
			result.add(value[-1 if left else 0])
		elif value == "space":
			result.update(" \t\u00a0\u3000")
			continue
		elif value == "number":
			result.update("0123456789０１２３４５６７８９〇零一二两三四五六七八九十百千万亿")
		else:
			result.update(word[-1 if left else 0] for word in classes[value])
		return frozenset(result)
	return None


def _context(text: str, classes: dict) -> str:
	parts, last, maximum = [], 0, 0
	matches = tuple(_PLACEHOLDER.finditer(text))
	if len(matches) > 4:
		raise ValueError("At most four placeholders per side")
	for match in matches:
		literal = text[last : match.start()]
		if any(ch in literal for ch in "{}[]"):
			raise ValueError("Invalid template bracket")
		parts.append(re.escape(literal))
		maximum += len(literal)
		name = match[1]
		if name == "number":
			parts.append(f"(?<![{_NUMBERS}])[{_NUMBERS}]{{1,12}}(?![{_NUMBERS}])")
			maximum += 12
		elif name == "space":
			parts.append(r"[ \t\u00a0\u3000]{0,4}")
			maximum += 4
		else:
			values = classes.get(name)
			if not isinstance(values, list) or not 1 <= len(values) <= MAX_CLASS_VALUES:
				raise ValueError(f"Unknown or over-limit class: {name}")
			if not all(isinstance(v, str) and 1 <= len(v) <= 8 for v in values):
				raise ValueError(f"Invalid class values: {name}")
			parts.append("(?:" + "|".join(re.escape(v) for v in sorted(set(values), key=lambda v: (-len(v), v))) + ")")
			maximum += max(map(len, values))
		last = match.end()
	literal = text[last:]
	if any(ch in literal for ch in "{}[]"):
		raise ValueError("Invalid template bracket")
	parts.append(re.escape(literal))
	if maximum + len(literal) > 64:
		raise ValueError("Template context exceeds 64 code points")
	return "".join(parts)


def compile_template(entry: dict, classes: dict, allowed: frozenset[str], *, user: bool = False) -> ContextTemplate:
	pattern = entry["pattern"]
	if not isinstance(pattern, str) or len(pattern) > 160:
		raise ValueError("Template exceeds 160 characters")
	matches = tuple(_TARGET.finditer(pattern))
	if len(matches) != 1:
		raise ValueError("Use exactly one target, such as 仙[乐:yuè]")
	match = matches[0]
	reading = None if match[2] == "keep" else numbered(match[2])
	if match[2] != "keep" and reading not in allowed:
		raise ValueError(f"Unknown pinyin reading: {match[2]}")
	if not pattern[: match.start()] and not pattern[match.end() :]:
		raise ValueError("A single character without context is not a pronunciation rule")
	priority = entry.get("priority", 100)
	if type(priority) is not int or not 0 <= priority <= 1000:
		raise ValueError("Priority must be between 0 and 1000")
	return ContextTemplate(
		id=entry["id"],
		pattern=pattern,
		target=match[1],
		reading=reading,
		left=re.compile(_context(pattern[: match.start()], classes) + r"\Z"),
		right=re.compile(_context(pattern[match.end() :], classes)),
		priority=priority,
		user=user,
		positive=tuple(entry.get("positive", ())),
		negative=tuple(entry.get("negative", ())),
		source=entry.get("source", ""),
		left_hint=_edge_hint(pattern[: match.start()], classes, left=True),
		right_hint=_edge_hint(pattern[match.end() :], classes),
	)


class CompiledTemplates:
	def __init__(self, entries):
		buckets = defaultdict(list)
		seen = set()
		for entry in entries:
			if entry.id in seen:
				raise ValueError(f"Duplicate template ID: {entry.id}")
			seen.add(entry.id)
			buckets[entry.target].append(entry)
		self.buckets = {ch: tuple(items) for ch, items in buckets.items()}
		self.triggers = frozenset(buckets)
		right_buckets = defaultdict(list)
		for ch, items in self.buckets.items():
			for entry in items:
				for right in entry.right_hint if entry.right_hint is not None else (None,):
					right_buckets[ch, right].append(entry)
		self._right_buckets = {key: tuple(items) for key, items in right_buckets.items()}

	def decision(self, text: str, index: int) -> tuple[str | None, str, bool] | None:
		right = text[index + 1] if index + 1 < len(text) else ""
		candidates = self._right_buckets.get((text[index], right), ()) + self._right_buckets.get(
			(text[index], None), ()
		)
		matches = [entry for entry in candidates if entry.matches(text, index)]
		if not matches:
			return None
		priority = max((entry.user, entry.priority) for entry in matches)
		best = [entry for entry in matches if (entry.user, entry.priority) == priority]
		readings = {entry.reading for entry in best}
		if len(readings) != 1:
			return None, "template_conflict", priority[0]
		return best[0].reading, best[0].id, best[0].user


def load_templates(allowed: frozenset[str], custom: str = "") -> CompiledTemplates:
	with (Path(__file__).with_name("data") / "contributions.toml").open("rb") as stream:
		data = tomllib.load(stream)
	if data.get("schemaVersion") != 1 or len(custom) > 32768:
		raise ValueError("Invalid template schema or oversized custom configuration")
	classes = data.get("classes", {})
	entries = [compile_template(entry, classes, allowed) for entry in data["rules"]]
	user_count = 0
	for number, line in enumerate(custom.splitlines(), 1):
		line = line.strip()
		if not line or line.startswith("#"):
			continue
		user_count += 1
		if user_count > 256:
			raise ValueError("At most 256 user templates")
		try:
			entries.append(
				compile_template({"id": f"user-template-{number}", "pattern": line}, classes, allowed, user=True)
			)
		except ValueError as error:
			raise ValueError(f"Line {number}: {error}") from error
	return CompiledTemplates(entries)
