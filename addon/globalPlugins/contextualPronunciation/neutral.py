"""Bounded lexical neutral-tone selection; no prosodic guesses from suffixes.

Citation/full-tone words remain intact. Productive 个 is selected by a local
quantity or verb/classifier construction, never by a sentence-wide trigger.
"""

from __future__ import annotations

from . import syntax as g
from .argument_roles import stature_boundary
from .verb_forms import predicate_form, predicate_tail

_QUANTITIES = frozenset("零〇一二两兩三四五六七八九十百千万萬亿億几幾半俩倆")
_DETERMINERS = frozenset("这這那哪每各")
_PARTICLES = frozenset("了吧呢啊呀吗嗎么麼")
MAX_LEFT = 16


def clipped_stature_reading(text, index, parser, context=None):
	"""ge4 for the nominal stature in V个, never for an overt classifier NP."""
	if index == 0 or parser is None:
		return None
	if index + 1 < len(text) and text[index + 1] not in _PARTICLES and g._is_han(text[index + 1]):
		return None
	if context is not None:
		if (reading := context.nominal_readings.get(index)) is not None:
			return reading
	if not stature_boundary(text, index + 1, g):
		return None
	argument = index
	if text[index - 1] in "点點儿兒":
		for word in ("一点儿", "一點兒", "一点", "一點", "点", "點"):
			if text[max(0, index - len(word)) : index] == word:
				argument -= len(word)
				break
	for pos in range(max(0, argument - 5), argument):
		if text[pos] not in "长長":
			continue
		start, end, stems = predicate_form(text, pos, interrogative=True)
		if not stems or predicate_tail(text, end)[0] != argument:
			continue
		# A stem hidden in a completed noun (校长/隊長) is not this verb.
		begin = start
		while begin > max(0, start + 1 - MAX_LEFT) and g._is_han(text[begin - 1]):
			begin -= 1
		for left in range(begin, start + 1):
			features = parser.lexicon.words.get(text[left : start + 1], 0)
			if features:
				return "ge4" if features & g.VERB else None
	return None


def classifier_reading(text, index, parser, context=None):
	"""ge4 for clipped stature; ge5 for a quantity or omitted numeral.

	An overt 个子/个头/个性 is a lexical word. A quantity preceding an
	otherwise overlapping 个人 instead establishes the classifier (一个人).
	No numeral tail, punctuation or speech-item boundary can supply evidence.
	"""
	if index == 0 or parser is None:
		return None
	if (reading := clipped_stature_reading(text, index, parser, context)) is not None:
		return reading
	word, _ = parser.lexicon.longest(text, index, min(len(text), index + 16))
	if len(word) > 1 and word.startswith(text[index]) and word not in {"个人", "個人"}:
		following, features = parser.lexicon.longest(text, index + 1, min(len(text), index + 16))
		if len(following) < len(word) or not features & (g.NOUN | g.PRON):
			return None  # 个性 remains a noun; 一个性格 has the head 性格.
	left = index - 1
	if text[left] in _QUANTITIES or text[left].isdecimal():
		count = 0
		while left >= 0 and (text[left] in _QUANTITIES or text[left].isdecimal()):
			count += 1
			if count > 8:
				return None
			left -= 1
		return "ge5"
	if text[left] in _DETERMINERS:
		return "ge5"
	if len(word) > 1 and word.startswith(text[index]):
		return None  # Lexical 個性/個人/個子/個頭, not a classifier prefix.
	end = index
	# Shared morphology recognizes the complement independently of meaning.
	for start in range(max(0, index - 5), index):
		if not parser.lexicon.words.get(text[start], 0) & g.VERB:
			continue
		_, stem_end, _ = predicate_form(text, start, interrogative=True)
		tail, _ = predicate_tail(text, stem_end)
		if tail == index:
			end = start + 1
			break
	else:
		end -= int(text[index - 1] in {"了", "着", "著", "过", "過"})
	begin = end
	while begin > max(0, end - MAX_LEFT) and g._is_han(text[begin - 1]):
		begin -= 1
	for start in range(begin, end):
		features = parser.lexicon.words.get(text[start:end], 0)
		if features:
			break  # Longest ending word, not a verb hidden inside a noun.
	else:
		return None
	if not features & g.VERB:
		return None
	stature_verb = text[start:end] in {"长", "長"}
	# Verb + 个 licenses an omitted numeral. Unknown material still fails;
	# no unknown word is used as the head or as a neutral-tone suffix rule.
	end = index + 1
	if end == len(text) or text[end] in _PARTICLES or not g._is_han(text[end]):
		return None if stature_verb else "ge5"
	_, following = parser.lexicon.longest(text, end, min(len(text), end + 16))
	return "ge5" if following & (g.NOUN | g.PRON | g.ADJ) else None
