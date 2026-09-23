"""Bounded predicate spines for attachment to an already established subject.

This recognizes the start of VP/AP, including preverbal adverbials. It does not
claim to validate every argument of an open-domain sentence. All dependencies
refer to the original speech item; an incomplete adverbial has no predicate.
"""

from __future__ import annotations

_MODALS = frozenset(("会", "會", "要", "能", "能够", "能夠", "可以", "应该", "應該", "必须", "必須", "愿意", "願意"))


def predicate_spine(tokens, start, subject_start, subject_end, context, g):
	modifiers, auxiliaries = [], []
	for i in range(start, min(len(tokens), start + 32)):
		t = tokens[i]
		if context is not None and not context.consume(1):
			return None
		f = t.features
		if f & (g.UNKNOWN | g.STOP | g.DE | g.COORD | g.NUMBER | g.CLASSIFIER):
			return None
		if t.text in _MODALS:
			auxiliaries.append((t.start, t.end))
			continue
		if f & g.ADV and not f & g.VERB:
			modifiers.append((t.start, t.end))
			continue
		if f & g.ADVERBIAL:
			if i > start and modifiers and modifiers[-1][1] == t.end:
				continue
			return None
		if f & g.ADJ and i + 1 < len(tokens) and tokens[i + 1].features == g.ADVERBIAL:
			modifiers.append((t.start, tokens[i + 1].end))
			continue
		if f & (g.VERB | g.ADJ) and not f & (g.NOUN | g.PRON):
			return (
				g.Dependency("nsubj", t.start, subject_start, subject_end),
				*(g.Dependency("aux", t.start, a, b) for a, b in auxiliaries),
				*(g.Dependency("advmod", t.start, a, b) for a, b in modifiers),
			)
		return None
	return None
