"""Normalize citation pinyin without conflating ü, tone, or surface sandhi."""

from __future__ import annotations

import re
import unicodedata

_NUMBERED = re.compile(r"[a-zv]+[1-5]\Z")


def numbered(text: str) -> str | None:
	text = text.lower().replace("u:", "v").replace("ü", "v")
	if _NUMBERED.fullmatch(text):
		return text if text not in {"r5", "xx5"} else None
	marks = {"\u0304": "1", "\u0301": "2", "\u030c": "3", "\u0300": "4"}
	tone, letters = "5", []
	for character in unicodedata.normalize("NFD", text):
		if character in marks:
			if tone != "5":
				return None
			tone = marks[character]
		elif character == "\u0308" and letters and letters[-1] == "u":
			letters[-1] = "v"
		else:
			letters.append(character)
	value = "".join(letters) + tone
	return value if _NUMBERED.fullmatch(value) else None
