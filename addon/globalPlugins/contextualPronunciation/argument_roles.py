"""Shared bounded recipient and overt-quantity analyses at original offsets."""

from __future__ import annotations

from .constituents import ConstituentParser

RECIPIENT_MARKERS = frozenset(("给", "給"))


def stature_boundary(text, end, grammar):
	"""Bounded closure after clipped stature 个, shared by sense and tone.

	An overt noun, numeral or unknown Han material defeats this ellipsis.
	Particles and the closed 了没/了没有 question may precede a boundary.
	"""
	g = grammar
	begin = end
	for _ in range(4):
		if text[end : end + 1] not in {"了", "吧", "呢", "啊", "呀", "吗", "嗎", "么", "麼"}:
			break
		end += 1
	else:
		return False
	if text[begin:end].startswith("了"):
		for word in ("没有", "沒有", "没", "沒"):
			if text.startswith(word, end):
				end += len(word)
				break
	for _ in range(4):
		if end >= len(text) or text[end] not in g._SPACES:
			break
		end += 1
	else:
		return False
	return end == len(text) or not (g._is_han(text[end]) or text[end] in g._NUMBERS)


def recipient(tokens, grammar, context):
	"""A human/pronominal NP; never a human mentioned inside another NP."""
	if not tokens:
		return None
	g = grammar
	if len(tokens) == 1 or (
		len(tokens) == 2
		# Only an unambiguous verb can close this simple recipient NP;
		# speech/path sense tags do not change its part of speech.
		and tokens[1].features & ~(g.SPEECH_VERB | g.PATH_MOTION) == g.VERB
	):
		flags = tokens[0].features
		if (
			flags & (g.NOUN | g.PRON)
			and flags & (g.HUMAN | g.PRON)
			and not flags & (g.STOP | g.DE | g.UNKNOWN | g.COORD | g.ADVERBIAL | g.COMPLEMENT)
		):
			if context is not None and not context.consume(len(tokens)):
				return None
			return g.NounPhrase(1, 0, flags, 0)
	np = ConstituentParser(tokens, g, context).parse()
	if np is None or not np.features & (g.HUMAN | g.PRON):
		return None
	return np


def quantity_ellipsis(tokens, grammar):
	"""A surface quantity can fill an omitted theme ONLY in a licensed frame.

	Does not manufacture a missing noun, its meaning, or its source position.
	An ordinary adjective/adverb (e.g. 好, 快) is not a quantity.
	"""
	g = grammar
	if not tokens:
		return False
	if any(t.features & (g.ACTION_MEASURE | g.DURATION) for t in tokens):
		return False
	if len(tokens) == 1 and tokens[0].features & g.INDEFINITE_QUANTITY:
		return True
	return bool(
		tokens[0].features & (g.NUMBER | g.DET) and all(t.features & (g.NUMBER | g.DET | g.CLASSIFIER) for t in tokens)
	)


def classified_object(tokens, grammar, context):
	"""Bare Clf NP after a verb, with an omitted numeral (长个新的痘).

	The overt noun remains the head. This does not license classifier-only
	ellipsis or skip a conflicting noun, unknown token or clause boundary.
	"""
	g = grammar
	if len(tokens) < 2 or not tokens[0].features & g.CLASSIFIER or tokens[1].text in {"了", "过", "過", "着", "著"}:
		return None
	if (
		len(tokens) == 2
		and tokens[1].features & (g.NOUN | g.PRON)
		and not tokens[1].features & (g.STOP | g.DE | g.UNKNOWN | g.COORD | g.ADVERBIAL | g.COMPLEMENT)
	):
		if context is not None and not context.consume(2):
			return None
		head = tokens[1]
		return g.NounPhrase(2, 1, head.features, 1, (g.Dependency("clf", head.start, tokens[0].start, tokens[0].end),))
	else:
		np = ConstituentParser(tokens, g, context).parse(start=1)
	if np is None:
		return None
	head = tokens[np.head]
	return g.NounPhrase(
		np.end,
		np.head,
		np.features,
		np.front_head,
		(g.Dependency("clf", head.start, tokens[0].start, tokens[0].end), *np.dependencies),
	)


def closed_classified_object(text, start, lexicon, grammar, context, *, excluded_heads=frozenset()):
	"""Clf + one lexical NP at a closed boundary; same head as the chart.

	Modifiers, compounds with multiple tokens and unknown suffixes must use
	the general chart. Lexical 个子/个头 are not classifier prefixes.
	"""
	g = grammar
	if text[start : start + 1] not in {"个", "個"}:
		return None
	word, _ = lexicon.longest(text, start, min(len(text), start + 16))
	if len(word) != 1:
		return None
	noun, features = lexicon.longest(text, start + 1, min(len(text), start + 17))
	if (
		noun in excluded_heads
		or not features & (g.NOUN | g.PRON)
		or features & (g.DURATION | g.AGE_MEASURE | g.STOP | g.DE | g.UNKNOWN | g.COORD | g.ADVERBIAL | g.COMPLEMENT)
	):
		return None
	end = start + 1 + len(noun)
	if not stature_boundary(text, end, g):
		return None
	if context is not None and not context.consume(2):
		return None
	# The same two-token nominal production, without allocating an
	# intermediate phrase or dependencies which speech would discard.
	return (g.Token(start, start + 1, text[start], g.CLASSIFIER), g.Token(start + 1, end, noun, features))
