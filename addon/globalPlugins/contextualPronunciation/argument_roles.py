"""Shared bounded recipient and overt-quantity analyses at original offsets."""

from __future__ import annotations

from .constituents import ConstituentParser

RECIPIENT_MARKERS = frozenset(("给", "給"))


def recipient(tokens, grammar, context):
	"""A human/pronominal NP; never a human mentioned inside another NP."""
	if not tokens:
		return None
	g = grammar
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
