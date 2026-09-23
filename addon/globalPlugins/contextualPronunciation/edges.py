"""Source-backed alternatives at lexical edges, before acoustic rendering."""

from __future__ import annotations

DIRECTIONS = frozenset("上下左右前后後内內外")


def coordination_pair(lexicon, text, index, g):
	"""An independently attested speech action coordinated with a predicate.

	Only speech-action senses license splitting an overlapping lexical 和 word;
	附和/应和 retain their response senses. Aspect or a nominal right side is
	insufficient evidence. Unknown text is never skipped to find a predicate.
	"""
	if text[index : index + 1] != "和":
		return None
	left = None
	for start in range(max(0, index - 8), index):
		word = text[start:index]
		flags = lexicon.words.get(word, 0)
		if flags & g.SPEECH_VERB:
			left = g.Token(start, index, word, flags)
			break
	if left is None:
		return None
	start = index + 1
	while start < len(text) and text[start] in g._SPACES and start < index + 5:
		start += 1
	if start >= len(text) or not g._is_han(text[start]):
		return None
	word, flags = lexicon.longest(text, start, min(len(text), start + 16))
	if not flags & g.VERB or flags & (g.UNKNOWN | g.STOP | g.PREP):
		return None
	if flags & g.NOUN and not flags & g.SPEECH_VERB:
		return None
	return left, g.Token(start, start + len(word), word, flags)


def edge_reading(parser, text, index, frame, context, g):
	if context is not None and not context.consume(1):
		return None
	if frame.object_class == "coordinatingPredicate":
		pair = coordination_pair(parser.lexicon, text, index, g)
		if pair is None:
			return None
		left, right = pair
		return g.SyntaxReading(
			frame.reading,
			frame.id,
			frame.object_class,
			index,
			left.start,
			right.end,
			left.start,
			left.end,
			(left, g.Token(index, index + 1, text[index], g.COORD), right),
			(
				g.Dependency("cc", right.start, index, index + 1),
				g.Dependency("conj", left.start, right.start, right.end),
			),
			"coordinated-predicates",
		)
	if index == 0 or text[index - 1] not in DIRECTIONS:
		return None
	word, flags = parser.lexicon.longest(text, index, min(len(text), index + 16))
	if len(word) < 2 or not flags & g.EDGE_NOUN:
		return None
	return g.SyntaxReading(
		frame.reading,
		frame.id,
		frame.object_class,
		index,
		index - 1,
		index + len(word),
		index,
		index + len(word),
		(g.Token(index - 1, index, text[index - 1], g.ADJ), g.Token(index, index + len(word), word, flags)),
		(g.Dependency("amod", index, index - 1, index),),
		"spatial-head",
	)
