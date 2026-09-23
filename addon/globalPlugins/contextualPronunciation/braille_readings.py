"""Read-only phonetic annotations for braille consumers, never homophone text.

Cells use the initials, finals and tones in GF 0019-2018 sections 7-9, with ALL
citation tones retained. This is a phonetic annotation, NOT a complete Chinese
Common Braille translator: no tone abbreviation, contractions, word spacing or
punctuation translation. Existing NVDA braille tables/cursor routing are untouched.
Unknown readings remain absent. Offsets in both Unicode code points and UTF-16
refer to the original text, not to a rewritten speech string.
"""

from __future__ import annotations

from dataclasses import dataclass

from .pinyin import numbered

_INITIALS = dict(
	zip(
		"b p m f d t n l g k h j q x zh ch sh r z c s".split(),
		"12 1234 134 124 145 2345 1345 123 1245 13 125 1245 13 125 34 12345 156 245 1356 14 234".split(),
		strict=True,
	)
)
_FINALS = dict(
	zip(
		(
			"a o e i u v er ai ao ei ou ia iao ie iou ua uai uei uo ve an ang en eng "
			"ian iang in ing uan ueng ong uang uen van vn iong"
		).split(),
		(
			"35 26 26 24 136 346 1235 246 235 2346 12356 1246 345 15 1256 123456 13456 2456 135 23456 "
			"1236 236 356 3456 146 1346 126 16 12456 256 256 2356 25 12346 456 1456"
		).split(),
		strict=True,
	)
)
_ZERO = dict(
	zip(
		"yi ya yao ye you yan yang yin ying yong yu yue yuan yun wu wa wai wei wo wan wang wen weng".split(),
		"i ia iao ie iou ian iang in ing iong v ve van vn u ua uai uei uo uan uang uen ueng".split(),
		strict=True,
	)
)
_TONES = {"1": "1", "2": "2", "3": "3", "4": "23", "5": ""}


def full_tone_dots(reading: str) -> tuple[str, ...] | None:
	"""Return full-tone phonetic cells, or abstain for unsupported syllables."""
	canonical = numbered(reading)
	if canonical is None:
		return None
	base, tone = canonical[:-1], canonical[-1]
	initial = ""
	if base in _ZERO:
		final = _ZERO[base]
	else:
		initial = next((item for item in ("zh", "ch", "sh", *_INITIALS) if base.startswith(item)), "")
		final = base[len(initial) :]
		if initial in {"j", "q", "x"} and final.startswith("u"):
			final = "v" + final[1:]
		final = {"iu": "iou", "ui": "uei", "un": "uen"}.get(final, final)
	if final == "i" and initial in {"zh", "ch", "sh", "r", "z", "c", "s"}:
		final = ""
	elif final not in _FINALS:
		return None
	return tuple(value for value in (_INITIALS.get(initial, ""), _FINALS.get(final, ""), _TONES[tone]) if value)


def unicode_cells(dots: tuple[str, ...]) -> str:
	return "".join(chr(0x2800 + sum(1 << (int(dot) - 1) for dot in cell)) for cell in dots)


@dataclass(frozen=True, slots=True)
class BrailleReading:
	start: int
	end: int
	utf16_start: int
	utf16_end: int
	character: str
	reading: str
	dots: tuple[str, ...] | None
	cells: str | None
	source: str


def annotate(text: str, rules, *, strict: bool = True) -> tuple[BrailleReading, ...]:
	"""Read the SAME rule decisions used by speech; never invent missing ones.

	Consumers must keep absent/unencodable spans as unknown, not shift subsequent
	indices or assume a default pronunciation. This function does not call NVDA.
	"""
	readings = {}
	if rules.lexicon is not None:
		for span in rules.lexicon.annotate(text):
			for offset, reading in enumerate(span.readings, span.start):
				if reading is not None and text[offset] not in rules.lexicon.reserved_targets:
					readings[offset] = (reading, span.source)
	for index, decision in rules.resolve(text, strict=strict).items():
		if decision.protect or decision.reading_id is None:
			readings.pop(index, None)
		else:
			readings[index] = (decision.reading_id, decision.rule_id)
	result, utf16_offset = [], 0
	for index, character in enumerate(text):
		length = 2 if ord(character) > 0xFFFF else 1
		if index in readings:
			reading, source = readings[index]
			dots = full_tone_dots(reading)
			result.append(
				BrailleReading(
					index,
					index + 1,
					utf16_offset,
					utf16_offset + length,
					character,
					reading,
					dots,
					unicode_cells(dots) if dots else None,
					source,
				)
			)
		utf16_offset += length
	return tuple(result)
