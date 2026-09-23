"""Nominal-role evidence for 将/將, using NP heads and lexical selection.

A military conjunct selects a parallel nominal head; a human classifier also
selects a nominal head. An ordinary subject followed by 将 remains ambiguous.
These productions do not identify military roles by searching sentence keywords.
"""

from __future__ import annotations

from .predicates import predicate_spine


def general_role(parser, text, index, frame, context, g):
	lexicon = parser.lexicon
	predicate_continuation = False
	if context is not None and not context.consume(1):
		return None
	# Keep lexical words intact unless an attested nominal compound crosses
	# the boundary and the competing suffix can start a predicate (天将 / 要).
	word, word_flags = lexicon.longest(text, index, min(len(text), index + 16))
	if len(word) > 1 and (
		not word_flags & (g.VERB | g.ADV)
		or not (
			any(text[start : index + 1] in lexicon.general_nouns for start in range(max(0, index - 3), index))
			or text[index - 1 : index] == "的"
			and parser.contextual_lexeme(word)
		)
	):
		return None
	if index + 1 < len(text) and g._is_han(text[index + 1]):
		_, flags = lexicon.longest(text, index + 1, min(len(text), index + 17))
		if not flags & (g.DE | g.COORD | g.ADV | g.VERB | g.ADJ | g.STOP) or flags & g.UNKNOWN:
			return None
		predicate_continuation = bool(flags & (g.ADV | g.VERB | g.ADJ))
	left = index
	while left > max(0, index - g.MAX_CHARS):
		ch = text[left - 1]
		if not (g._is_han(ch) or ch in g._NUMBERS | g._SPACES):
			break
		left -= 1
	tokens = lexicon.tokenize(text[:index], left)
	if tokens and tokens[-1].end != index:
		return None
	if context is not None and not context.consume(len(tokens)):
		return None
	if tokens and tokens[-1].features & (g.HUMAN | g.PRON):
		return None  # 一位经验丰富的老师 将 离开 has a complete subject.
	target = g.Token(index, index + 1, text[index], g.NOUN | g.HUMAN | g.MILITARY)

	def nominal(items):
		np = g._NounParser(items, context).parse()
		return np if np is not None and np.end == len(items) and np.head == len(items) - 1 else None

	def established_head(items):
		# An explicit modifier selects the bound nominal head. Otherwise a
		# dictionary-attested compound must support it, including projections
		# of parallel military compounds. A vehicle/person noun + 将 cannot
		# borrow this evidence from a military noun elsewhere in the sentence.
		if len(items) > 1 and items[-2].features == g.DE:
			return True
		return any(text[t.start : index + 1] in lexicon.general_nouns for t in items[-4:-1])

	# A person measure must modify this very head, not a noun inside a
	# relative clause: 一位老人的将来 cannot donate its classifier to 将.
	for start, token in enumerate(tokens):
		if not token.features & (g.NUMBER | g.DET):
			continue
		items = (*tokens[start:], target)
		np = nominal(items)
		if np is not None and any(
			d.relation == "clf"
			and d.head == index
			and any(t.start == d.start and t.features & g.PERSON_MEASURE for t in items)
			for d in np.dependencies
		):
			return _reading(items, np, index, frame, "classified-nominal", (), g)

	# Coordination is symmetric: [蟹 将] 和 [虾 兵] supplies the same
	# nominal-role evidence as [虾 兵] 和 [蟹 将].
	if text[index + 1 : index + 2] in {"和", "与", "與", "及"}:
		right = lexicon.tokenize(text, index + 2)
		right_np = g._NounParser(right, context).parse()
		if right_np is not None and right_np.features & g.MILITARY:
			start = 0
			if nominal((*tokens, target)) is None:
				for i, t in enumerate(tokens):
					if t.features & (g.STOP | g.COORD | g.VERB | g.ADV | g.PREP) and not t.features & g.NOUN:
						start = i + 1
			items = (*tokens[start:], target)
			predicate = ()
			if right_np.end < len(right):
				if not established_head(items):
					return None
				predicate = predicate_spine(
					right,
					right_np.end,
					items[0].start,
					right[right_np.end - 1].end,
					context,
					g,
				)
				if predicate is None:
					return None
			np = nominal(items)
			if np is not None:
				deps = (g.Dependency("conj", index, right[0].start, right[right_np.end - 1].end),)
				return _reading(items, np, index, frame, "coordinated-nominal", (*deps, *predicate), g)

	# NP(military) + coordinator + NP(modifier, 将). Keep the complete
	# right conjunct; never drop an unknown name or pronoun to find a head.
	for boundary in range(len(tokens) - 1, -1, -1):
		if tokens[boundary].text not in {"和", "与", "與", "及"}:
			continue
		right = tokens[boundary + 1 :]
		if any(t.features & (g.PRON | g.UNKNOWN) for t in right):
			return None
		if not any(t.features & g.DE for t in right) and any(t.features & g.HUMAN for t in right):
			return None  # 士兵和老师将离开: 老师 is already a complete human subject.
		items = (*right, target)
		if predicate_continuation and not established_head(items):
			return None
		np = nominal(items)
		if np is None:
			return None
		preceding = tokens[:boundary]
		if not preceding:
			return None
		start = 0
		left_np = g._NounParser(preceding, context).parse()
		if left_np is None or left_np.end != len(preceding):
			for i, t in enumerate(preceding):
				if t.features & (g.STOP | g.COORD | g.VERB | g.ADV | g.PREP) and not t.features & g.NOUN:
					start = i + 1
			left_np = g._NounParser(preceding, context).parse(start)
		if left_np is None or left_np.end != len(preceding) or not left_np.features & g.MILITARY:
			return None
		head = preceding[left_np.head].start
		deps = (g.Dependency("conj", head, items[0].start, index + 1),)
		if predicate_continuation:
			predicate = predicate_spine(
				lexicon.tokenize(text, index + 1),
				0,
				preceding[start].start,
				index + 1,
				context,
				g,
			)
			if predicate is None:
				return None
			deps += predicate
		return _reading(items, np, index, frame, "coordinated-nominal", deps, g)
	return None


def _reading(tokens, np, index, frame, construction, dependencies, g):
	return g.SyntaxReading(
		frame.reading,
		frame.id,
		frame.object_class,
		index,
		tokens[0].start,
		index + 1,
		index,
		index + 1,
		tokens,
		(*np.dependencies, *dependencies),
		construction,
	)
