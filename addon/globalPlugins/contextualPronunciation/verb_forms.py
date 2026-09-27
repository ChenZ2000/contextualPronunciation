"""Bounded productive verb morphology, independent of a verb's selected sense.

The same phase/potential complement occurs with rotation and transfer. Recognize
its structure before lexical segmentation, then let argument roles select sense.
UD Chinese compound:dir and potential 得/不 motivate these productions; phase
and result subtypes are project annotations, not a complete UD treebank parser.
"""

from __future__ import annotations

_COMPLEMENTS = {
	"起": (("起来", "compound:phase"), ("起來", "compound:phase")),
	"下": (("下去", "compound:phase"), ("下来", "compound:dir"), ("下來", "compound:dir")),
	"出": (("出去", "compound:dir"), ("出来", "compound:dir"), ("出來", "compound:dir")),
	"进": (("进去", "compound:dir"), ("进来", "compound:dir")),
	"進": (("進去", "compound:dir"), ("進來", "compound:dir")),
	"回": (("回去", "compound:dir"), ("回来", "compound:dir"), ("回來", "compound:dir")),
	**{ch: ((ch, "compound:result"),) for ch in "动動"},
}
_ASPECT = frozenset("了过過着著")
_REITERATION = ("了又", "了再", "呀", "啊", "着", "著")
MAX_STEMS = 8


def reiterated_form(text, index):
	"""V 呀/啊 V, V 着 V 着, V 了又/了再 V share arguments.

	No punctuation crossing or arbitrary conjunction skipping. Empty stems mark
	an over-budget group, which callers must not reinterpret as a bare verb.
	"""
	if not (index + 1 < len(text) and text[index + 1] in "呀啊着著了" or index and text[index - 1] in "呀啊着著又再"):
		return None
	stem = text[index]
	for link in _REITERATION:
		step = len(link) + 1
		start = index
		count = 1
		while start >= step and text.startswith(stem + link, start - step):
			start -= step
			count += 1
			if count > MAX_STEMS:
				return index, index + 1, ()
		stems = [start]
		end = start + 1
		while text.startswith(link + stem, end):
			stems.append(end + len(link))
			end += step
			if len(stems) > MAX_STEMS:
				return index, index + 1, ()
		if len(stems) > 1:
			if link in "呀啊着著" and text.startswith(link, end):
				end += 1
			return start, end, tuple(stems)
	return None


def predicate_form(text, index):
	"""Return one verb group and its stem offsets: V / VV / V一V / V了V."""
	stem = text[index]
	start = index
	if index and text[index - 1] == stem:
		start -= 1
	elif index > 1 and text[index - 1] in "一了" and text[index - 2] == stem:
		start -= 2
	if text.startswith(stem * 2, start):
		return start, start + 2, (start, start + 1)
	if start + 2 < len(text) and text[start + 1] in "一了" and text[start + 2] == stem:
		return start, start + 3, (start, start + 2)
	if (group := reiterated_form(text, index)) is not None:
		return group
	return start, start + 1, (start,)


def predicate_tail(text, end):
	"""Return tail end and (relation, start, end) spans; never infer pronunciation."""
	start = end
	potential = end < len(text) and text[end] in "得不"
	if potential:
		end += 1
	for word, relation in _COMPLEMENTS.get(text[end : end + 1], ()):
		if text.startswith(word, end):
			spans = ((relation, end, end + len(word)),)
			if potential:
				spans += (("aux:potential", start, end),)
			end += len(word)
			break
	else:
		end, spans = start, ()
	if end < len(text) and text[end] in _ASPECT:
		spans += (("aspect", end, end + 1),)
		end += 1
	return end, spans
