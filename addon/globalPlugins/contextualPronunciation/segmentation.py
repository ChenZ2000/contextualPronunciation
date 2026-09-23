"""Bounded unigram lattice adjudication of disputed dictionary word spans.

Scores are log corpus-frequency priors, NOT pronunciation probabilities. Only
small disagreement islands are visited; agreed words and opaque blockers are
never overridden. No model inference, I/O, NVDA internals or document cache.
"""

from __future__ import annotations

import math
from types import MappingProxyType

MAX_ISLAND = 96
MIN_MARGIN = math.log(16)  # Explicit policy: likelihood ratio, not calibrated accuracy.


class UnigramAdjudicator:
	def __init__(self, data: dict):
		if data.get("schemaVersion") != 1:
			raise ValueError("Unsupported segmentation schema")
		total = data["totalFrequency"]
		counts = data["frequencies"]
		if type(total) is not int or total <= 0 or not isinstance(counts, dict):
			raise ValueError("Invalid unigram counts")
		if any(
			not isinstance(word, str) or not 1 <= len(word) <= 32 or type(count) is not int or not 0 < count <= total
			for word, count in counts.items()
		):
			raise ValueError("Invalid unigram entry")
		self._scores = MappingProxyType({word: math.log(count / total) for word, count in counts.items()})
		self._unknown = -math.log(total)

	def choose(self, text, candidates, words, index):
		"""Return original-offset spans whose complete word edge beats alternatives.

		Prefix/suffix Viterbi scores allow exact max-marginals: any path which
		omits an edge must use another edge covering its first character. Compare
		ALL such alternatives, not just the single runner-up path. A tied or
		low-margin path abstains; ordering never provides confidence.
		"""
		if not candidates:
			return set()
		islands = []
		for start, end in sorted(candidates):
			if islands and start < islands[-1][1]:
				islands[-1][1] = max(islands[-1][1], end)
				islands[-1][2].append((start, end))
			else:
				islands.append([start, end, [(start, end)]])
		selected = set()
		for start, end, spans in islands:
			if end - start > MAX_ISLAND:
				continue  # Do not truncate a word to fit the budget.
			selected.update(self._island(text[start:end], start, spans, words, index))
		return selected

	def _island(self, text, origin, candidates, words, index):
		n = len(text)
		edges = [[] for _ in range(n)]
		blocked = []
		for start in range(n):
			edges[start].append((start + 1, self._scores.get(text[start], self._unknown)))
			for length in index.get(text[start : start + 2], ()):
				end = start + length
				if end > n:
					continue
				word = text[start:end]
				reading = words.get(word)
				if reading is not None:
					edges[start].append((end, self._scores.get(word, self._unknown)))
					if not reading:
						blocked.append((start, end))
		prefix, suffix = [-math.inf] * (n + 1), [-math.inf] * (n + 1)
		prefix[0] = suffix[n] = 0.0
		for start in range(n):
			for end, weight in edges[start]:
				prefix[end] = max(prefix[end], prefix[start] + weight)
		for start in range(n - 1, -1, -1):
			suffix[start] = max(weight + suffix[end] for end, weight in edges[start])
		result = set()
		for absolute_start, absolute_end in candidates:
			start, end = absolute_start - origin, absolute_end - origin
			word = text[start:end]
			if not words.get(word) or word not in self._scores:
				continue
			if any(left < end and right > start for left, right in blocked):
				continue
			chosen = prefix[start] + self._scores[word] + suffix[end]
			alternative = max(
				prefix[left] + weight + suffix[right]
				for left in range(start + 1)
				for right, weight in edges[left]
				if right > start and (left, right) != (start, end)
			)
			if chosen - alternative >= MIN_MARGIN:
				result.add((absolute_start, absolute_end))
		return result
