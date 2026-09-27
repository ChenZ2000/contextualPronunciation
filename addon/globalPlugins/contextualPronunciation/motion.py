"""Argument attachment and predicate morphology for rotational/walking senses.

The noun chart determines heads of places and rotating objects. A location
inside a modifier does not establish the sense of a later unrelated verb.
All evidence is per-item, bounded, and expressed at original text offsets.
"""

from __future__ import annotations

from .argument_roles import RECIPIENT_MARKERS, quantity_ellipsis, recipient
from .constituents import ConstituentParser
from .predicates import _MODALS
from .verb_forms import predicate_form, predicate_tail

_LOCATIVE = frozenset(("去", "到", "在", "往"))
_CAUSATIVE = frozenset(("让", "讓", "使", "令"))
_DISPOSAL = frozenset(("把", "将", "將"))
_AUXILIARIES = (
	_MODALS
	| frozenset(neg + modal for neg in ("不", "没", "沒") for modal in _MODALS)
	| frozenset(("不", "没", "沒", "没有", "沒有", "未", "不能", "无法", "無法", "没法", "沒法", "想", "想要"))
)
_BLOCKED = frozenset(("卡住", "卡死", "锈住", "銹住", "锈死", "銹死"))
_DIRECTIVES = frozenset(("请", "請", "先", "再", "就", "都", "也", "还", "還"))
_MODIFIER_WORDS = _AUXILIARIES | _DIRECTIVES
_OBJECT_MARKERS = _DISPOSAL | _CAUSATIVE
_SPLIT_INITIALS = frozenset(word[0] for word in _MODIFIER_WORDS | _LOCATIVE)
_CLAUSE_LINKS = frozenset(("但", "但是", "然后", "然後", "而", "并", "並", "而且", "并且", "並且"))
_DIRECTIONS = frozenset(("向左", "向右", "向后", "向後", "向前", "往左", "往右", "往后", "往後", "往前"))
_TEMPORAL_BOUNDARIES = frozenset(("后", "後", "之后", "之後", "以后", "以後", "时", "時", "的时候", "的時候"))
_SUFFIXES = {
	"一": ("一下", "一会儿", "一會兒", "一会", "一會"),
	**{ch: (ch,) for ch in "了过過着著"},
}


def contextual_form(word):
	"""An AA dictionary entry cannot determine the sense of a full clause."""
	return len(word) == 2 and word[0] in "转轉" and word[1] == word[0]


def _tokens(lexicon, text, start, g, depth=0, stop=None):
	"""Expose productive modal + motion / locative + noun boundaries.

	Greedy segmentation merges 想出 in 想出去, or 在家 into a verb.
	Only an attested motion/location constituent licenses this split.
	"""
	if depth > 16:
		return ()
	stop = len(text) if stop is None else stop
	tokens = lexicon.tokenize(text, start, stop)
	if not any(len(t.text) > 1 and t.text[0] in _SPLIT_INITIALS for t in tokens):
		return tokens
	result = []
	for token in tokens:
		word = token.text
		for size in range(1, min(4, len(word))):
			prefix = word[:size]
			if prefix not in _AUXILIARIES and prefix not in _DIRECTIVES and prefix not in _LOCATIVE:
				continue
			following, flags = lexicon.longest(text, token.start + size, stop)
			if prefix in _MODIFIER_WORDS and (following in _LOCATIVE or flags & g.PATH_MOTION):
				return (
					tuple(result)
					+ (g.Token(token.start, token.start + size, prefix, g.VERB),)
					+ _tokens(lexicon, text, token.start + size, g, depth + 1, stop)
				)
			if prefix in _LOCATIVE and flags & g.PLACE and following == word[size:]:
				result.extend(
					(
						g.Token(token.start, token.start + size, prefix, g.PREP),
						g.Token(token.start + size, token.end, following, flags),
					)
				)
				break
		else:
			result.append(token)
	return tuple(result)


def _noun(tokens, g, context):
	if not tokens:
		return None
	if len(tokens) == 1 and tokens[0].features & (g.NOUN | g.PRON):
		if context is not None and not context.consume(1):
			return None
		return g.NounPhrase(1, 0, tokens[0].features, 0)
	np = ConstituentParser(tokens, g, context).parse()
	if np is not None and np.end == len(tokens):
		return np
	# A coordinated argument must validate ALL conjuncts; only their shared
	# semantic features can select a meaning. Never borrow one conjunct's type.
	links = [i for i, token in enumerate(tokens) if token.text in {"和", "与", "與", "及"}]
	if not links or len(links) > 16:
		return None
	deps, features, head = [], None, None
	for begin, end in zip((0, *(i + 1 for i in links)), (*links, len(tokens)), strict=True):
		part = tokens[begin:end]
		if not part:
			return None
		p = ConstituentParser(part, g, context).parse()
		if p is None or p.end != len(part):
			return None
		features = p.features if features is None else features & p.features
		if head is None:
			head = begin + p.head
		else:
			deps.append(g.Dependency("conj", tokens[head].start, part[0].start, part[-1].end))
		deps.extend(p.dependencies)
	return g.NounPhrase(len(tokens), head, features | g.NOUN, head, tuple(deps))


def _modifiers(tokens, g):
	"""Split preverbal adverbs, modals and Adj 地 from their argument."""
	end = len(tokens)
	while end:
		token = tokens[end - 1]
		if token.features == g.ADVERBIAL and end > 1 and tokens[end - 2].features & (g.ADJ | g.ADV):
			end -= 2
		elif (
			token.text in _MODIFIER_WORDS
			or token.features & g.ADV
			and not token.features & (g.NOUN | g.PRON)
			or token.features & g.ADJ
			and len(token.text) == 2
			and token.text[0] == token.text[1]
		):
			end -= 1
		else:
			break
	return tokens[:end], tokens[end:]


def _prefix(parser, text, end, context, g):
	start = end
	while start and end - start < g.MAX_CHARS:
		ch = text[start - 1]
		if not (g._is_han(ch) or ch in g._NUMBERS or ch in g._SPACES):
			break
		start -= 1
	if context is not None and not context.consume(end - start + 1):
		return ()
	# Only grammatical clause links can start a new local clause. Unknown
	# text, punctuation and exhausted token budgets never disappear.
	for _ in range(16):
		tokens = _tokens(parser.lexicon, text, start, g, stop=end)
		if not tokens:
			return ()
		if tokens[-1].end == end:
			last_link = next(
				(
					i
					for i in range(len(tokens) - 1, -1, -1)
					if tokens[i].text in _CLAUSE_LINKS and not any(t.features == g.DE for t in tokens[i + 1 :])
				),
				-1,
			)
			return tokens[last_link + 1 :]
		if tokens[-1].text not in _CLAUSE_LINKS or tokens[-1].end <= start:
			return ()
		start = tokens[-1].end
	return ()


def motion_reading(parser, text, index, frames, context, g):
	"""One role analysis selects between rotation/roaming and transfer frames."""
	if (
		index + 3 == len(text)
		and text[index + 1] in g._NUMBERS
		and not text.startswith(_SUFFIXES.get(text[index + 1], ()), index + 1)
	):
		unit_flags = parser.lexicon.words.get(text[index + 2], 0)
		if unit_flags & g.ACTION_MEASURE and not unit_flags & (g.ROTOR | g.TRANSFER_THEME | g.DURATION):
			return None
	if context is None:
		return _motion_reading(parser, text, index, frames, context, g)
	if index not in context.motion_readings:
		if len(context.motion_readings) >= g.MAX_CHART_STATES:
			return None
		form = predicate_form(text, index)
		if not form[2]:
			context.motion_readings[index] = None
			return None
		if len(context.motion_readings) + len(form[2]) > g.MAX_CHART_STATES:
			return None
		parsed = _motion_reading(parser, text, index, frames, context, g, form)
		for stem in form[2]:
			context.motion_readings[stem] = parsed
	parsed = context.motion_readings[index]
	if parsed is None or parsed.target == index:
		return parsed
	return g.SyntaxReading(
		parsed.reading,
		parsed.rule_id,
		parsed.object_class,
		index,
		parsed.object_start,
		parsed.object_end,
		parsed.head_start,
		parsed.head_end,
		parsed.tokens,
		parsed.dependencies,
		parsed.construction,
		parsed.preserve,
	)


def _motion_reading(parser, text, index, frames, context, g, form=None):
	if context is not None and context.remaining_work <= 0:
		return None
	start, end, stems = form if form is not None else predicate_form(text, index)
	if not stems:
		return None
	if end < len(text) and text[end] in "起下出进進回动動得不了过過着著":
		tail_end, tail = predicate_tail(text, end)
	else:
		tail_end, tail = end, ()
	# A closed numeral + action-unit complement cannot supply the theme
	# required by either current frame. Reject this common, unambiguous
	# shape before constructing a prefix chart (e.g. 重转一次). Keep open
	# continuations, lexical noun heads and durations on the full path.
	if (
		tail_end + 2 == len(text)
		and text[tail_end] in g._NUMBERS
		and not text.startswith(_SUFFIXES.get(text[tail_end], ()), tail_end)
	):
		unit_flags = parser.lexicon.words.get(text[tail_end + 1], 0)
		if unit_flags & g.ACTION_MEASURE and not unit_flags & (g.ROTOR | g.TRANSFER_THEME | g.DURATION):
			return None
	# A lexical compound such as 转发/转身 cannot be split into a bare V.
	# Productive phase/potential morphology and recipient 给 are analyzed
	# before greedy lexical entries such as 转起 can block the verb boundary.
	word, _flags = parser.lexicon.longest(text, start, min(len(text), start + 16))
	if (
		len(word) > 1
		and not text[start:tail_end].startswith(word)
		and word != text[start] + "给"
		and word != text[start] + "給"
	):
		return None
	if end < len(text) and text[end] == text[start]:
		return None  # Overlapping runs are not an unlimited VV construction.
	if len(stems) > 1 and text[stems[0] + 1 : stems[1]] not in {"", "一", "了"}:
		last_word, _flags = parser.lexicon.longest(text, stems[-1], min(len(text), stems[-1] + 16))
		if stems[-1] + len(last_word) > tail_end and last_word not in {text[start] + "给", text[start] + "給"}:
			obj, flags = parser.lexicon.longest(text, tail_end, min(len(text), tail_end + 16))
			if not flags & g.NOUN or tail_end + len(obj) <= stems[-1] + len(last_word):
				return None  # 转呀转账 is not two bare verbs; 转呀转车轮 has an intact object.
	left = _prefix(parser, text, start, context, g)
	if left:
		# Prefix tokenization must not manufacture a boundary inside 掉转,
		# 好转, etc. Check the original text, before truncation at the verb.
		previous = left[-1]
		compound, _flags = parser.lexicon.longest(text, previous.start, min(len(text), previous.start + 16))
		if previous.start + len(compound) > start:
			return None
	arguments, modifiers = _modifiers(left, g)
	if any(t.text in _DIRECTIONS for t in modifiers):
		return None
	deps = tuple(g.Dependency("aux" if t.text in _AUXILIARIES else "advmod", start, t.start, t.end) for t in modifiers)
	deps += tuple(g.Dependency("redup", start, p, p + 1) for p in stems[1:])
	if tail:
		deps += tuple(g.Dependency(relation, start, a, b) for relation, a, b in tail)

	def result(kind, evidence, np=None, relation="obl:loc", *, transfer=False):
		selected = "transferPredicate" if transfer else "motionPredicate"
		for frame in frames:
			if frame.object_class == selected:
				break
		else:
			return None
		head = evidence[np.head] if np is not None else evidence[-1]
		relations = deps + (g.Dependency(relation, start, evidence[0].start, evidence[-1].end),)
		if transfer and pre_recipient is not None:
			relations = tuple(
				g.Dependency("obl:recipient", d.head, d.start, d.end) if d.relation == "obl:beneficiary" else d
				for d in relations
			)
		if np is not None:
			relations += np.dependencies
		return g.SyntaxReading(
			frame.reading,
			frame.id,
			frame.object_class,
			index,
			evidence[0].start,
			evidence[-1].end,
			head.start,
			head.end,
			left,
			relations,
			kind,
			frame.preserve,
		)

	# An overt direct object takes precedence over a preceding location:
	# 去公园转转文件 is a transfer, regardless of the park in the same clause.
	right_start = tail_end
	for marker in _SUFFIXES.get(text[right_start : right_start + 1], ()):
		if text.startswith(marker, right_start):
			right_start += len(marker)
			break
	right = (
		parser.lexicon.tokenize(text, right_start)
		if right_start < len(text)
		and (g._is_han(text[right_start]) or text[right_start] in g._NUMBERS or text[right_start] in g._SPACES)
		else ()
	)
	if tail and right and right[0].text in _TEMPORAL_BOUNDARIES:
		deps += (g.Dependency("mark:temporal", start, right[0].start, right[0].end),)
		right = ()
	pre_recipient = None
	# Postverbal 给 selects a recipient. The theme may precede 给 or be
	# omitted with an overt quantity. A phase/result plus 给 NP VP is a
	# purpose clause (转起来给大家看), not the verb's transfer recipient.
	for marker, token in enumerate(right[:32]):
		if token.text not in RECIPIENT_MARKERS:
			continue
		before, after = right[:marker], right[marker + 1 :]
		rnp = recipient(after, g, context)
		if rnp is None:
			if not before or quantity_ellipsis(before, g):
				return None  # Unresolved recipient versus 给-relative attachment.
			break
		theme = _noun(before, g, context) if before else None
		quantity = quantity_ellipsis(before, g)
		if (
			before
			and before[0].features & (g.NUMBER | g.DET)
			and (
				any(t.features & (g.ACTION_MEASURE | g.DURATION) for t in before)
				and (theme is None or theme.features & (g.ACTION_MEASURE | g.DURATION))
			)
		):
			return None  # An extent/duration is not an omitted transfer theme.
		if before and theme is None and not quantity:
			break
		purpose = rnp.end < len(after) and after[rnp.end].features & g.VERB
		durative_subject = None
		if purpose and len(stems) > 1 and text[stems[0] + 1 : stems[1]] in {"呀", "啊", "着", "著"}:
			durative_subject = _noun(arguments, g, context)
		if purpose and (
			any(rel.startswith("compound:") for rel, _a, _b in tail)
			or theme is not None
			and theme.features & g.ROTOR
			or durative_subject is not None
			and durative_subject.features & g.ROTOR
		):
			deps += (g.Dependency("advcl:purpose", start, token.start, after[-1].end),)
			right = before
			break
		if before:
			deps += (g.Dependency("obj:ellipsis" if quantity else "obj", start, before[0].start, before[-1].end),)
		return result("transfer-recipient", after[: rnp.end], rnp, "obl:recipient", transfer=True)

	# Preverbal 给 NP may be a recipient OR a beneficiary. Remove exactly
	# the validated PP, then use the theme head / direct object to select.
	for marker in range(len(arguments) - 1, -1, -1):
		if arguments[marker].text not in RECIPIENT_MARKERS:
			continue
		after = arguments[marker + 1 :]
		rnp = recipient(after, g, context)
		if rnp is not None and rnp.end == len(after):
			pre_recipient = after, rnp
			arguments, more_modifiers = _modifiers(arguments[:marker], g)
			deps += tuple(
				g.Dependency("aux" if t.text in _AUXILIARIES else "advmod", start, t.start, t.end)
				for t in more_modifiers
			)
			deps += (g.Dependency("obl:beneficiary", start, after[0].start, after[-1].end), *rnp.dependencies)
		break

	if pre_recipient is not None:
		quantity_tokens = right[:-1] if right and right[-1].features == g.STOP else right
		if quantity_ellipsis(quantity_tokens, g):
			return result("transfer-quantity", quantity_tokens, relation="obj:ellipsis", transfer=True)

	if right and (
		right[0].features & (g.NOUN | g.PRON | g.DET | g.NUMBER | g.ADJ | g.UNKNOWN)
		or right[0].features & (g.ADV | g.VERB)
		and any(t.features == g.DE for t in right)
	):
		np = ConstituentParser(right, g, context).parse()
		if np is None:
			return None
		if np.features & g.TRANSFER_THEME:
			return result("transfer-object", right[: np.end], np, "obj", transfer=True)
		if np.features & g.ROTOR:
			return result("rotating-object", right[: np.end], np, "obj")
		if not np.features & g.DURATION or not right[0].features & (g.NUMBER | g.DET):
			return None
		deps += (g.Dependency("obl:duration", start, right[0].start, right[np.end - 1].end),)
	if not arguments:
		# A closed, standalone durative depiction has the conventional motion
		# reading. Overt transfer objects/recipients were resolved above.
		# This is a scoped default, not a claim that repetition implies rotation.
		if (
			not left
			and len(stems) > 1
			and text[stems[0] + 1 : stems[1]] in {"呀", "啊"}
			and (not right or right[0].features == g.STOP)
		):
			return result("durative-motion-default", (g.Token(start, end, text[start:end], g.VERB),), relation="root")
		return None

	# The final verb of a serial movement selects its own subject.
	if arguments[-1].features & g.PATH_MOTION or arguments[-1].text in {"去", "来", "來"}:
		return result("serial-motion", arguments[-1:], relation="xcomp")

	# The nearest complete argument frame wins: 让他到公园 V versus
	# 到公园把文件 V. An older place/cause cannot override a newer object.
	for marker in range(len(arguments) - 1, -1, -1):
		if arguments[marker].text in _LOCATIVE:
			place = arguments[marker + 1 :]
			np = _noun(place, g, context)
			if np is not None and np.features & g.PLACE:
				return result("locative-motion", place, np)
			return None
		if arguments[marker].text in _OBJECT_MARKERS:
			obj = arguments[marker + 1 :]
			np = _noun(obj, g, context)
			if np is not None and np.features & g.TRANSFER_THEME:
				return result("transfer-preposed", obj, np, "obj", transfer=True)
			if np is None or not np.features & g.ROTOR:
				return None
			return result("caused-rotation", obj, np, "obj")

	# A stuck predicate can introduce an omitted rotating subject, but an
	# explicit nonrotating noun cannot borrow this ellipsis interpretation.
	if arguments[-1].text in _BLOCKED:
		before = arguments[:-1]
		if not before:
			return result("blocked-motion", arguments[-1:], relation="advcl")
		arguments, _ = _modifiers(before, g)
	# Topic + overt human subject: 钱我给他转了 / 车轮我转了转.
	# Keep both roles instead of treating the final pronoun as a compound head.
	if len(arguments) > 1 and arguments[-1].features & (g.PRON | g.HUMAN):
		topic = arguments[:-1]
		np = _noun(topic, g, context)
		if np is not None and np.features & (g.TRANSFER_THEME | g.ROTOR):
			agent = arguments[-1]
			deps += (g.Dependency("nsubj", start, agent.start, agent.end),)
			return result("topicalized-object", topic, np, "obj:topic", transfer=bool(np.features & g.TRANSFER_THEME))
	for begin in range(min(len(arguments), 32)):
		if begin and arguments[begin - 1].text not in _DIRECTIVES and not arguments[begin - 1].features & g.VERB:
			continue
		subject = arguments[begin:]
		np = _noun(subject, g, context)
		if np is not None and np.features & g.TRANSFER_THEME:
			return result("transfer-topic", subject, np, "obj:topic", transfer=True)
		if np is not None and np.features & g.ROTOR:
			return result("rotating-subject", subject, np, "nsubj")
	return None
