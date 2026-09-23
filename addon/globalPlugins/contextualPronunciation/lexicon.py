"""Engine-neutral, bounded phrase readings with conservative segmentation.

No NVDA, synthesizer, network, regex or file operations occur during matching.
Forward/reverse agreement is the fast path. Bounded unigram adjudication may
resolve disputed spans; homographs and named-word blockers remain opaque.
Empty dictionary values are real lexical blockers, not missing entries.
"""

from __future__ import annotations

import json
from bisect import bisect_left
from collections import defaultdict
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from types import MappingProxyType

from .segmentation import UnigramAdjudicator


@dataclass(frozen=True, slots=True)
class ReadingSpan:
	"""Offsets are Python Unicode code points in the ORIGINAL string, not UTF-16.

	Full citation readings are retained, including neutral tones. These are not
	braille cells, surface tone sandhi, or an assertion of sentence-level accuracy.
	"""

	start: int
	end: int
	text: str
	readings: tuple[str | None, ...]
	source: str = "CC-CEDICT + Unihan"
	# Relative character positions whose DEFAULT dictionary reading must also
	# reach the synthesizer: a conflicting word crosses this accepted edge.
	forced_offsets: tuple[int, ...] = ()


@dataclass(frozen=True, slots=True)
class ReadingMetadata:
	allowed_readings: frozenset[str]
	renderings: MappingProxyType


@lru_cache(maxsize=1)
def load_reading_metadata() -> ReadingMetadata:
	"""Small pronunciation alphabet; default mode never builds the large index."""
	with (Path(__file__).with_name("data") / "readings_zh_CN.json").open(encoding="utf-8") as stream:
		data = json.load(stream)
	allowed = frozenset(data["allowedReadings"])
	if data.get("schemaVersion") != 2 or any(
		len(ch) != 1 or not ch.isalpha() or reading not in allowed for reading, ch in data["renderings"].items()
	):
		raise ValueError("Invalid reading metadata")
	return ReadingMetadata(allowed, MappingProxyType(data["renderings"]))


class PhraseLexicon:
	def __init__(self, data: dict, *, segmentation: dict | None = None):
		if data.get("schemaVersion") != 2 or data.get("maxWordLength") != 32:
			raise ValueError("Unsupported phrase lexicon schema or bound")
		words = data["words"]
		if not isinstance(words, dict):
			raise ValueError("Invalid phrase lexicon words")
		forward, reverse = defaultdict(set), defaultdict(set)
		for word, reading in words.items():
			if not isinstance(word, str) or not 2 <= len(word) <= 32 or not isinstance(reading, str):
				raise ValueError("Invalid phrase lexicon entry")
			if reading and len(reading.split()) != len(word):
				raise ValueError("Phrase reading alignment mismatch")
			forward[word[:2]].add(len(word))
			reverse[word[-2:]].add(len(word))
		self._words = MappingProxyType(words)
		self._adjudicator = UnigramAdjudicator(segmentation) if segmentation is not None else None
		self._sources = MappingProxyType({word: tuple(ids) for word, ids in data.get("wordSources", {}).items()})
		self._forward = {key: tuple(sorted(lengths, reverse=True)) for key, lengths in forward.items()}
		self._reverse = {key: tuple(sorted(lengths, reverse=True)) for key, lengths in reverse.items()}
		self.defaults = MappingProxyType(data["defaults"])
		self.analysis_triggers = frozenset(self.defaults)
		self.allowed_readings = frozenset(data["allowedReadings"])
		self.renderings = MappingProxyType(data["renderings"])
		if any(len(ch) != 1 or not ch.isalpha() for ch in self.renderings.values()):
			raise ValueError("Invalid homophone rendering")
		self.reserved_targets = frozenset(data["reservedTargets"])
		# Common neutral-tone characters (的/了/着 etc.) need grammatical
		# disambiguation. A lexical entry such as 面的 cannot establish whether
		# the same substring in 盛面的时候 is that noun or a particle boundary.
		self.triggers = frozenset(data["speechTargets"])
		if any(
			ch not in self.defaults or self.defaults[ch].endswith("5") or ch in self.reserved_targets
			for ch in self.triggers
		):
			raise ValueError("Invalid speech target policy")
		# Keep the COMPLETE dictionary for segmentation, including blockers.
		# Speech does not need to allocate annotations for words which cannot
		# change speech. This index contains no document text and is built once.
		self._speech_words = frozenset(
			word
			for word, reading in words.items()
			if reading
			and any(
				ch in self.triggers and p != "?" and p != self.defaults[ch]
				for ch, p in zip(word, reading.split(), strict=True)
			)
		)
		# A dictionary default is an inventory convention, NOT a prediction of
		# any particular synthesizer. Index alternative crossing lexemes once,
		# so an accepted 降调 / 音频 edge can lock diào against 调音 (tiáo).
		# No complete compound phrase is added and no word boundary is changed.
		crossing = defaultdict(list)
		default_words = set()
		for word, reading in words.items():
			if not reading:
				continue
			for pivot, (ch, pinyin) in enumerate(zip(word, reading.split(), strict=True)):
				if ch not in self.triggers or pinyin == "?":
					continue
				if pinyin == self.defaults[ch]:
					if pinyin in self.renderings:
						default_words.add(word)
				else:
					left = word[pivot - 1] if pivot else None
					right = word[pivot + 1] if pivot + 1 < len(word) else None
					crossing[ch, left, right].append((word, pivot))
		self._crossing = MappingProxyType({key: tuple(values) for key, values in crossing.items()})
		self._default_words = frozenset(default_words)

	def _crossing_default_offsets(self, text, start, end, readings):
		"""Lock only accepted, renderable defaults with an actual crossing rival.

		A rival contributes evidence of a possible engine resegmentation, never
		its pronunciation. Ambiguous/blocked winning spans never reach here.
		Contained subwords are not crossings. All comparisons use original text.
		"""
		result = []
		for offset, pinyin in enumerate(readings):
			index = start + offset
			ch = text[index]
			if ch not in self.triggers or pinyin != self.defaults[ch] or pinyin not in self.renderings:
				continue
			left = text[index - 1] if index else None
			right = text[index + 1] if index + 1 < len(text) else None
			for key in ((ch, left, right), (ch, left, None), (ch, None, right)):
				for word, pivot in self._crossing.get(key, ()):
					other_start = index - pivot
					other_end = other_start + len(word)
					if (
						other_start >= 0
						and (other_start < start or other_end > end)
						and text.startswith(word, other_start)
					):
						result.append(offset)
						break
				else:
					continue
				break
		return tuple(result)

	def _segments(self, text: str, *, reverse: bool = False) -> dict[tuple[int, int], str]:
		"""O(n * L), L <= 32, with a two-character index and bounded lookups.

		Include blocked headwords in BOTH segmentations. Dropping them would let
		an ambiguous or named longer word fall through to a misleading subword.
		"""
		result = {}
		text_length = len(text)
		position = text_length if reverse else 0
		index = self._reverse if reverse else self._forward
		while (position > 1) if reverse else (position + 1 < text_length):
			key = text[position - 2 : position] if reverse else text[position : position + 2]
			for length in index.get(key, ()):
				start = position - length if reverse else position
				end = position if reverse else position + length
				if start < 0 or end > text_length:
					continue
				reading = self._words.get(text[start:end])
				if reading is not None:
					result[start, end] = reading
					position = start if reverse else end
					break
			else:
				position += -1 if reverse else 1
		return result

	def annotate(self, text: str, *, speech_only: bool = False) -> tuple[ReadingSpan, ...]:
		"""Return agreed lexical readings without mutating speech or braille text.

		Agreement is a conservative heuristic, NOT proof of linguistic certainty.
		Unknown/ambiguous/cross-segmentation spans are omitted, never guessed.
		Speech-only projection changes allocation, NEVER the segmentation or
		blockers. Default callers retain complete/partial source annotations.
		"""
		forward = self._segments(text)
		if not forward:
			return ()
		reverse = self._segments(text, reverse=True)
		agreed = forward.keys() & reverse.keys()
		adjudicated = set()
		if self._adjudicator is not None:
			disputed = forward.keys() ^ reverse.keys()
			if disputed and any(
				self._words[text[start:end]]
				and (not speech_only or text[start:end] in self._speech_words or text[start:end] in self._default_words)
				for start, end in disputed
			):
				adjudicated = self._adjudicator.choose(text, disputed, self._words, self._forward)
				# Never displace agreed words (including agreed opaque blockers).
				ordered = sorted(agreed)
				starts = [span[0] for span in ordered]
				adjudicated = {
					(start, end)
					for start, end in adjudicated
					if not (before := bisect_left(starts, end)) or ordered[before - 1][1] <= start
				}
		result = []
		for start, end in sorted(agreed | adjudicated):
			word = text[start:end]
			reading = self._words[word]
			if not reading or (speech_only and word not in self._speech_words and word not in self._default_words):
				continue
			readings = tuple(None if p == "?" else p for p in reading.split())
			forced = self._crossing_default_offsets(text, start, end, readings) if word in self._default_words else ()
			if speech_only and word not in self._speech_words and not forced:
				continue
			source = ";".join(self._sources[word]) if word in self._sources else "CC-CEDICT + Unihan"
			source += " [unigram-margin]" if (start, end) in adjudicated else ""
			source += " [crossing-reading-lock]" if forced else ""
			result.append(ReadingSpan(start, end, word, readings, source, forced))
		return tuple(result)


@lru_cache(maxsize=1)
def load_default_lexicon() -> PhraseLexicon:
	# Only when broad matching is enabled, or requested by an offline tool.
	data_dir = Path(__file__).with_name("data")
	with (data_dir / "lexicon_zh_CN.json").open(encoding="utf-8") as stream:
		data = json.load(stream)
	with (data_dir / "segmentation_zh_CN.json").open(encoding="utf-8") as stream:
		return PhraseLexicon(data, segmentation=json.load(stream))
