"""Containment goal and action-nominal attachments at original offsets."""

from __future__ import annotations

from .constituents import ConstituentParser


def complement_reading(parser, text, index, frame, context, g):
	"""A filling event can omit its contents but retain a goal or event head.

	Do not classify 盛装赴会 from a following action verb. A nominalized
	动作 must be the parsed head; a container must be governed by 到/进/入/在
	or head an explicit relative clause. Attire governors block all paths.
	"""
	if context is not None and context.remaining_work <= 0:
		return None
	if frame.blocked_left and text[max(0, index - 16) : index].endswith(frame.blocked_left):
		return None
	for prefix in parser.morphologies[frame.id].get(text[index + 1], ()):
		if not prefix or not text.startswith(prefix, index + 1):
			continue
		start = index + 1 + len(prefix)
		if start >= len(text):
			continue
		marker = text[start]
		goal = marker in "到进進入在"
		relative = marker == "的"
		if (
			not goal
			and not relative
			and not any(0 <= text.find(word, start, start + g.MAX_CHARS) for word in ("动作", "動作"))
		):
			continue
		begin = start + int(goal or relative)
		tokens = parser.lexicon.tokenize(text, begin)
		# A locative suffix denotes the inside of the parsed container, not
		# another object. Keep every intervening noun/modifier in the chart.
		if goal:
			for i, token in enumerate(tokens):
				if token.text in {"里", "裡", "内", "內", "中", "里面", "裡面"}:
					tokens = tokens[:i]
					break
		if not tokens:
			continue
		np = ConstituentParser(tokens, g, context).parse()
		if np is None:
			continue
		feature = g.CONTAINER if goal else g.ACTION_NOMINAL | (g.CONTAINER if relative else 0)
		if not np.features & feature:
			continue
		head, last = tokens[np.head], tokens[np.end - 1]
		dep = (
			g.Dependency("obl:goal", index, begin, last.end) if goal else g.Dependency("acl", head.start, index, begin)
		)
		return g.SyntaxReading(
			frame.reading,
			frame.id,
			frame.object_class,
			index,
			begin,
			last.end,
			head.start,
			head.end,
			tokens[: np.end],
			(dep, *np.dependencies),
			"container-goal" if goal else "containment-nominal",
		)
	return None
