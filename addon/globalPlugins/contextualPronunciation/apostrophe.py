"""Fast, conservative normalization for lexical apostrophes."""

from __future__ import annotations

import unicodedata

CURLY_APOSTROPHE = "\u2019"
ASCII_APOSTROPHE = "'"
APOSTROPHES = frozenset((ASCII_APOSTROPHE, CURLY_APOSTROPHE))
_MAX_COMBINING_MARKS = 4


def _is_latin_letter(character: str | None) -> bool:
	if not character or not character.isalpha():
		return False
	if character.isascii():
		return True
	return "LATIN" in unicodedata.name(character, "")


def _nearest_base_character(text: str, position: int, step: int) -> str | None:
	"""Return an adjacent base character, looking through a few combining marks."""
	seen_combining = 0
	while 0 <= position < len(text):
		character = text[position]
		if unicodedata.combining(character):
			seen_combining += 1
			if seen_combining > _MAX_COMBINING_MARKS:
				return None
			position += step
			continue
		return character
	return None


def normalize_lexical_apostrophes(text: str) -> str:
	"""Normalize U+2019 only when it joins two Latin letters.

	ASCII apostrophes are already the most broadly supported spelling accepted by
	speech engines. Quotation marks and word-final apostrophes are intentionally
	left untouched. If nothing changes, the original string object is returned.
	"""
	if CURLY_APOSTROPHE not in text:
		return text

	result: list[str] | None = None
	search_from = 0
	while True:
		position = text.find(CURLY_APOSTROPHE, search_from)
		if position < 0:
			break
		left = _nearest_base_character(text, position - 1, -1)
		right = _nearest_base_character(text, position + 1, 1)
		if _is_latin_letter(left) and _is_latin_letter(right):
			if result is None:
				result = list(text)
			result[position] = ASCII_APOSTROPHE
		search_from = position + 1
	return text if result is None else "".join(result)


def prepare_apostrophes_for_nvda(text: str, *, normalize_curly: bool = True) -> str:
	"""Prepare apostrophes for NVDA's built-in symbol processor.

	NVDA 2026.2's complex ``in-word '`` expression has only a left-hand
	assertion.  The add-on symbol dictionary must override that existing
	identifier to preserve true lexical joiners at the ``all`` symbol level, but
	that would also preserve a closing quote after a word.  A single ordinary
	space before a non-lexical match makes the complex expression fail so NVDA's
	ordinary symbol rule can continue to report the closing quote.

	The transformation is speech-only, linear, idempotent, and copy-on-write.
	"""
	if APOSTROPHES.isdisjoint(text):
		return text

	result: list[str] | None = None
	for position, character in enumerate(text):
		if character not in APOSTROPHES:
			continue
		left = _nearest_base_character(text, position - 1, -1)
		right = _nearest_base_character(text, position + 1, 1)
		is_lexical = _is_latin_letter(left) and _is_latin_letter(right)
		if is_lexical:
			if normalize_curly and character == CURLY_APOSTROPHE:
				if result is None:
					result = list(text)
				result[position] = ASCII_APOSTROPHE
			continue

		# This mirrors the useful part of NVDA's (?<=[^\W_]) lookbehind.
		# Combining marks do not satisfy that immediate lookbehind, so inspect the
		# actual preceding code point rather than the nearest base character.
		if position and text[position - 1].isalnum():
			if result is None:
				result = list(text)
			result[position] = f" {character}"

	return text if result is None else "".join(result)
