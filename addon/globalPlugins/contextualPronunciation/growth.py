"""Local argument and complement selection for 长 / 長.

Nominal senses are candidates. A body location, a growing subject or an actual
growth-product head must attach to THIS predicate. Degree and measurement
constructions instead select length. Unknown bare uses remain undecided.
"""

from __future__ import annotations

from .argument_roles import classified_object, quantity_ellipsis
from .constituents import ConstituentParser
from .verb_forms import predicate_form, predicate_tail

MAX_WINDOW = 96
_STATURE_FORMS = frozenset(("个子", "個子", "个儿", "個兒", "个头", "個頭"))
_DISTRIBUTIVE = frozenset(("各自", "分别", "分別"))
_LOCALIZERS = (
	"里面",
	"裡面",
	"上面",
	"下面",
	"前面",
	"后面",
	"後面",
	"表面",
	"上",
	"下",
	"前",
	"后",
	"後",
	"里",
	"裡",
	"内",
	"內",
	"中",
)
_DEGREES = (
	"非常",
	"十分",
	"比较",
	"比較",
	"不太",
	"有点",
	"有點",
	"那么",
	"那麼",
	"这么",
	"這麼",
	"很",
	"太",
	"更",
	"最",
	"真",
	"好",
	"较",
	"較",
)
_AUX = tuple(
	sorted(
		(
			"已经",
			"已經",
			"没有",
			"沒有",
			"不会",
			"不會",
			"不能",
			"可以",
			"正在",
			"总是",
			"總是",
			"一直",
			"不再",
			"各自",
			"分别",
			"分別",
			"开始",
			"開始",
			"重新",
			"慢慢",
			"渐渐",
			"漸漸",
			"逐渐",
			"逐漸",
			"继续",
			"繼續",
			"不",
			"没",
			"沒",
			"未",
			"又",
			"再",
			"也",
			"都",
			"还",
			"還",
			"会",
			"會",
			"能",
			"要",
			"才",
			"就",
		),
		key=lambda s: -len(s),
	)
)
_GOVERNORS = frozenset(("发现", "發現", "看到", "看见", "看見", "听说", "聽說", "觉得", "覺得"))
_LINKS = frozenset(("但", "但是", "而", "然后", "然後", "并且", "並且"))
_RESULTS = (
	"出来",
	"出來",
	"起来",
	"起來",
	"出去",
	"下去",
	"大",
	"高",
	"胖",
	"壮",
	"壯",
	"出",
	"成",
	"满",
	"滿",
	"好",
	"齐",
	"齊",
	"到",
)
_UNITS = frozenset(("米", "厘米", "毫米", "公分", "寸", "尺", "丈", "公里", "千米"))
_FORMS = frozenset(("长大", "長大", "长高", "長高", "长出", "長出", "长成", "長成", "长得", "長得", "长长", "長長"))
_MODIFIER_ENDS = {ch: tuple(w for w in (*_DEGREES, *_AUX) if w[-1] == ch) for ch in {w[-1] for w in (*_DEGREES, *_AUX)}}
_LOCALIZER_ENDS = {ch: tuple(w for w in _LOCALIZERS if w[-1] == ch) for ch in {w[-1] for w in _LOCALIZERS}}
_CLAUSE_TAILS = frozenset(w[-1] for w in _GOVERNORS | _LINKS)
_RESULT_TAILS = {ch: tuple((w, "compound:result") for w in _RESULTS if w[0] == ch) for ch in {w[0] for w in _RESULTS}}


def contextual_lexeme(word, offset=0):
	return (
		offset == 0
		and len(word) > 1
		and word[0] in "长長"
		and (
			word in _FORMS
			or word[1:] in _RESULTS
			or word[1:] in _STATURE_FORMS | {"脸", "臉", "脸型", "臉型", "个", "個"}
		)
	)


def _frame(frames, reading):
	for frame in frames:
		if frame.reading == reading:
			return frame
	return None


def _face_reading(parser, text, start, index, frames, left, context, g, *, face_start=None, spans=()):
	ltokens, subject, _, degree, modifiers = left
	face_start = start + 1 if face_start is None else face_start
	end = face_start + 1
	before, after = text[max(0, start - 12) : start], text[end : end + 12]
	shape = after.startswith("型") or before.endswith(
		("张", "張", "拉", "拉着", "拉著", "板着", "板著", "绷着", "繃著", "是")
	)
	beneficiary = None
	for pos, token in enumerate(ltokens):
		if token.text in {"给", "給", "替", "为", "為"}:
			np = _noun(ltokens[pos + 1 :], context, g, complete=True)
			if np is not None:
				beneficiary = (token.start, ltokens[-1].end)
	honor = (
		beneficiary is not None
		or any(relation == "aspect" for relation, _, _ in spans)
		or after.startswith(("了", "过", "過", "吧", "啊", "呀"))
		or (not before and (not after or not g._is_han(after[0])))
	)
	if shape:
		reading, construction = "chang2", "face-shape"
	elif honor:
		reading, construction = "zhang3", "honor-idiom"
	else:
		return None
	frame = _frame(frames, reading)
	if frame is None:
		return None
	deps = []
	if context is None or context.details:
		deps.append(g.Dependency("compound:idiom" if honor and not shape else "amod", start, face_start, end))
		deps.extend(g.Dependency(relation, start, a, b) for relation, a, b in spans)
		if beneficiary is not None:
			deps.append(g.Dependency("obl:beneficiary", start, *beneficiary))
		if after.startswith("了"):
			deps.append(g.Dependency("aspect", start, end, end + 1))
		deps.extend(g.Dependency("advmod", start, a, b) for a, b in modifiers)
		if subject is not None:
			deps.extend(subject.dependencies)
	return g.SyntaxReading(
		reading,
		frame.id,
		frame.object_class,
		index,
		face_start,
		end,
		face_start,
		end,
		(g.Token(face_start, end, text[face_start:end], g.NOUN | g.BODY_SITE),),
		tuple(deps),
		construction,
	)


def _noun(tokens, context, g, *, complete=False):
	if not tokens:
		return None
	# A two-token preposition/predicate + NP cannot form a nominal without
	# a relative marker. Do not allocate a failing chart for 给我 / 替大家.
	if len(tokens) == 2 and not tokens[0].features & (
		g.NOUN | g.PRON | g.ADJ | g.ADV | g.DET | g.NUMBER | g.CLASSIFIER
	):
		if context is not None:
			context.consume(1)
		return None
	if len(tokens) == 1 and tokens[0].features & (g.NOUN | g.PRON):
		if context is not None and not context.consume(1):
			return None
		return g.NounPhrase(1, 0, tokens[0].features, 0)
	np = ConstituentParser(tokens, g, context).parse()
	return np if np is not None and (not complete or np.end == len(tokens)) else None


def _left(parser, text, end, context, g):
	start = end
	while start and end - start < MAX_WINDOW:
		if not (g._is_han(text[start - 1]) or text[start - 1] in g._NUMBERS | g._SPACES):
			break
		start -= 1
	if start and end - start == MAX_WINDOW and g._is_han(text[start - 1]):
		return None  # A clipped tail cannot fabricate a complete argument.
	if context is not None and not context.consume(end - start + 1):
		return None
	# Only explicit complement governors / clause links establish a fresh NP.
	if not _CLAUSE_TAILS.isdisjoint(text[start:end]):
		initial = parser.lexicon.tokenize(text, start, end)
		for token in initial:
			if token.text in _GOVERNORS | _LINKS:
				start = token.end
	degree, modifiers = False, []
	for _ in range(8):
		fragment = text[start:end].rstrip(" \t\u3000")
		end = start + len(fragment)
		word = next((w for w in _MODIFIER_ENDS.get(fragment[-1:], ()) if fragment.endswith(w)), None)
		if word is None:
			break
		degree |= word in _DEGREES
		modifiers.append((end - len(word), end))
		end -= len(word)
	else:
		return None
	location = None
	for word in _LOCALIZER_ENDS.get(text[end - 1 : end], ()):
		if end > start + len(word) and text.startswith(word, end - len(word)):
			location = (end - len(word), end)
			end -= len(word)
			break
	if start < end and text[start] in "在从從":
		start += 1
	# An exact, complete nominal is already the longest token. Avoid running
	# the general lexer merely to reconstruct this same singleton NP.
	word = text[start:end]
	features = parser.lexicon.words.get(word, 0)
	tokens = (
		(g.Token(start, end, word, features),)
		if features & (g.NOUN | g.PRON)
		else parser.lexicon.tokenize(text, start, end)
	)
	if tokens and tokens[-1].text in {"个", "個"} and (len(tokens) == 1 or tokens[-2].features == g.DE):
		head = tokens[-1]
		tokens = (*tokens[:-1], g.Token(head.start, head.end, head.text, g.NOUN | g.STATURE | g.GROWTH_PRODUCT))
	np = _noun(tokens, context, g, complete=True)
	for i, token in enumerate(tokens):
		if token.text != "比":
			continue
		compared = _noun(tokens[:i], context, g, complete=True)
		other = tokens[i + 1 :]
		rival = _noun(other, context, g, complete=True)
		ellipsis = (
			len(other) == 1
			and len(other[0].text) == 2
			and other[0].text[0] in "这這那"
			and parser.lexicon.words.get(other[0].text[1:], 0) & g.CLASSIFIER
		)
		if compared is not None and compared.features & g.LENGTH_BEARER and (rival is not None or ellipsis):
			modifiers.append((token.start, end))
			tokens, np, degree = tokens[:i], compared, True
		break
	return tokens, np, location, degree, tuple(modifiers)


def _measurement(tokens, g):
	return len(tokens) >= 2 and tokens[0].features & g.NUMBER and tokens[1].text in _UNITS


def _stature_ellipsis(text, tokens, g):
	"""Clipped 个/個 denotes stature only at a complete nominal boundary.

	With an overt NP after it, 个 is a classifier and cannot supply stature.
	No absent 子 or 儿 and no fabricated source offsets are inserted.
	"""
	i = 0
	if tokens and tokens[0].text in {"点", "點", "一点", "一點", "一点儿", "一點兒"}:
		i += 1
	elif len(tokens) > 1 and tokens[0].text == "一" and tokens[1].text in {"点", "點"}:
		i += 2
	if i >= len(tokens) or tokens[i].text not in {"个", "個"}:
		return None
	head = tokens[i]
	end = head.end
	for _ in range(4):
		if text[end : end + 1] not in {"了", "吧", "呢", "啊", "呀", "吗", "嗎", "么", "麼"}:
			break
		end += 1
	else:
		return None
	if text[head.end : end].startswith("了"):
		for word in ("没有", "沒有", "没", "沒"):
			if text.startswith(word, end):
				end += len(word)
				break
	for _ in range(4):
		if end >= len(text) or text[end] not in g._SPACES:
			break
		end += 1
	else:
		return None
	if end < len(text) and (g._is_han(text[end]) or text[end] in g._NUMBERS):
		return None
	return g.NounPhrase(
		i + 1,
		i,
		g.NOUN | g.STATURE | g.GROWTH_PRODUCT,
		i,
		(g.Dependency("ellipsis:stature", head.start, head.start, head.end),),
	)


def _quantity_extent(tokens, g):
	items = []
	for token in tokens[:8]:
		if token.features & g.STOP:
			break
		items.append(token)
	return quantity_ellipsis(items, g)


def _age_reading(parser, text, index, start, tail, left, obj, frames, context, g, *, closed=False):
	"""Age difference is an independent complement, not a nearby person hit."""
	ltokens, subject, _, _, modifiers = left
	if subject is not None and subject.features & g.LENGTH_BEARER:
		return None
	if obj is not None and not obj.features & (g.AGE_NOUN | g.AGE_MEASURE | g.HUMAN | g.PRON):
		return None  # An age modifier cannot donate its class to the actual head.
	for qstart in range(tail, min(len(text), tail + 64)):
		if context is not None and not context.consume(1):
			return None
		if text[qstart] in g._NUMBERS:
			break
		if not g._is_han(text[qstart]):
			return None
	else:
		return None
	qend = qstart
	while qend < len(text) and qend - qstart < 8 and text[qend] in g._NUMBERS:
		qend += 1
	if context is not None and not context.consume(qend - qstart + 1):
		return None
	if qend == len(text) or text[qend] in g._NUMBERS:
		return None
	unit, flags = parser.lexicon.longest(text, qend, min(len(text), qend + 16))
	if not flags & g.AGE_MEASURE:
		return None
	unit_end = qend + len(unit)
	if closed and unit_end < len(text) and (g._is_han(text[unit_end]) or text[unit_end] in g._NUMBERS | g._SPACES):
		return None  # A following modifier/name requires the full head chart.
	rival_tokens = parser.lexicon.tokenize(text, tail, qstart)
	rival = _noun(rival_tokens, context, g, complete=True) if rival_tokens else None
	if rival_tokens and (rival is None or not rival.features & (g.HUMAN | g.PRON)):
		return None
	comparison = None
	for i, token in enumerate(ltokens):
		if token.text == "比":
			compared = _noun(ltokens[:i], context, g, complete=True)
			other = _noun(ltokens[i + 1 :], context, g, complete=True)
			if (
				(i and (compared is None or not compared.features & (g.HUMAN | g.PRON)))
				or other is None
				or not other.features & (g.HUMAN | g.PRON)
			):
				return None
			comparison = (token.start, ltokens[-1].end)
			subject = compared
			break
	else:
		if ltokens and subject is None:
			return None
	frame = _frame(frames, "zhang3")
	if frame is None:
		return None
	head = g.Token(qend, qend + len(unit), unit, flags)
	deps = []
	if context is None or context.details:
		deps.append(g.Dependency("extent:age", start, qstart, head.end))
		if rival is not None:
			deps.extend(rival.dependencies)
			deps.append(g.Dependency("obl:comparison", start, rival_tokens[0].start, rival_tokens[-1].end))
		if comparison is not None:
			deps.append(g.Dependency("obl:comparison", start, *comparison))
		if subject is not None:
			deps.extend(subject.dependencies)
			deps.append(g.Dependency("nsubj", start, ltokens[0].start, ltokens[subject.end - 1].end))
		deps.extend(g.Dependency("advmod", start, a, b) for a, b in modifiers)
	return g.SyntaxReading(
		"zhang3",
		frame.id,
		frame.object_class,
		index,
		qstart,
		head.end,
		head.start,
		head.end,
		(head,),
		tuple(deps),
		"age-comparison",
	)


def _closed_reading(text, index, start, end, stems, left, frames, context, g):
	"""Closed predicates need no right NP chart or complement search."""
	tokens, np, location, degree, modifiers = left
	flags = np.features if np is not None else 0
	stature = None
	if text[end : end + 1] in {"个", "個"}:
		object_head = g.Token(end, end + 1, text[end], g.CLASSIFIER)
		stature = _stature_ellipsis(text, (object_head,), g)
	aspect = text[end : end + 1] in {"了", "着", "著", "过", "過"}
	tail = end + int(aspect)
	if stature is None and tail < len(text) and (g._is_han(text[tail]) or text[tail] in g._NUMBERS | g._SPACES):
		return None
	distributed = any(text[a:b] in _DISTRIBUTIVE for a, b in modifiers)
	mixed = len(stems) == 2 and end - start == 2 and aspect and flags & (g.GROWER | g.GROWTH_PRODUCT)
	if stature is not None or aspect and flags & g.STATURE:
		reading, construction = "zhang3", "stature-growth"
	elif degree:
		reading, construction = "chang2", "degree-length"
	elif mixed:
		reading, construction = ("zhang3" if index == start else "chang2"), "growth-length-result"
	elif location is not None and flags & g.BODY_SITE:
		reading, construction = "zhang3", "locative-growth"
	elif aspect and flags & g.GROWTH_INCREMENT:
		reading, construction = "zhang3", "development-increment"
	elif flags & g.GROWER or aspect and flags & g.PRON:
		reading, construction = "zhang3", "growing-subject"
	elif aspect and distributed and (np is None or flags & (g.GROWTH_PRODUCT | g.PRON)):
		reading, construction = "zhang3", "distributed-growth"
	elif flags & g.LENGTH_BEARER and (not aspect or not flags & g.GROWTH_PRODUCT):
		reading, construction = "chang2", "length-predicate"
	else:
		return None
	frame = _frame(frames, reading)
	if frame is None:
		return None
	deps = []
	details = context is None or context.details
	if details:
		deps.extend(g.Dependency("advmod", start, a, b) for a, b in modifiers)
		if aspect:
			deps.append(g.Dependency("aspect", start, end, tail))
		deps.extend(g.Dependency("compound:result" if mixed else "redup", start, stem, stem + 1) for stem in stems[1:])
	if np is not None:
		head = tokens[np.head]
		begin, finish = tokens[0].start, tokens[-1].end
		if details:
			deps.extend(np.dependencies)
			deps.append(g.Dependency("obl:location" if location else "nsubj", start, begin, finish))
			if location:
				deps.append(g.Dependency("case:localizer", head.start, *location))
	else:
		head = g.Token(start, start + 1, text[start], g.VERB if reading == "zhang3" else g.ADJ)
		begin, finish, tokens = start, tail, (head,)
	if stature is not None:
		head = object_head
		begin, finish, tokens = head.start, head.end, (head,)
		if details:
			deps.extend(stature.dependencies)
			deps.append(g.Dependency("obj", start, begin, finish))
			if text[finish : finish + 1] == "了":
				deps.append(g.Dependency("aspect", start, finish, finish + 1))
	parsed = g.SyntaxReading(
		reading,
		frame.id,
		frame.object_class,
		index,
		begin,
		finish,
		head.start,
		head.end,
		tokens,
		tuple(deps),
		construction,
	)
	_cache(parsed, stems, start, frames, context, g, mixed=mixed and not degree)
	return parsed


def _cache(parsed, stems, start, frames, context, g, *, mixed=False):
	if context is None or len(context.motion_readings) + len(stems) > g.MAX_CHART_STATES:
		return
	for stem in stems:
		if mixed:
			reading = "zhang3" if stem == start else "chang2"
			frame = _frame(frames, reading)
			if frame is not None:
				context.motion_readings[stem] = (
					parsed
					if parsed.target == stem and parsed.reading == reading
					else g.SyntaxReading(
						reading,
						frame.id,
						frame.object_class,
						stem,
						parsed.object_start,
						parsed.object_end,
						parsed.head_start,
						parsed.head_end,
						parsed.tokens,
						parsed.dependencies,
						parsed.construction,
					)
				)
		else:
			context.motion_readings[stem] = parsed


def growth_reading(parser, text, index, frames, context, g):
	if context is not None and context.remaining_work <= 0:
		return None
	start, end, stems = predicate_form(text, index, interrogative=True)
	if not stems or end - start > 32:
		return None
	if text[max(0, start - 1) : start] == text[index] or text[end : end + 1] == text[index]:
		return None  # Dense AA runs are neither length nor growth evidence.
	word, _ = parser.lexicon.longest(text, start, min(len(text), start + 16))
	if (
		len(word) > 1
		and not parser._growth_lexeme(word)
		and not _measurement(parser.lexicon.tokenize(text, start + 1, start + 17), g)
	):
		return None  # Preserve intact compounds and names (长江 / 长裙 / 长子).
	left = _left(parser, text, start, context, g)
	if left is None:
		return None
	ltokens, subject, location, degree, modifiers = left
	if text.startswith(("长脸", "長臉"), start):
		return _face_reading(parser, text, start, index, frames, left, context, g)
	if text[end : end + 1] in g._NUMBERS or parser.lexicon.words.get(text[end : end + 1], 0) & g.PRON:
		age = _age_reading(parser, text, index, start, end, left, None, frames, context, g, closed=True)
		if age is not None:
			_cache(age, stems, start, frames, context, g)
			return age
	if (closed := _closed_reading(text, index, start, end, stems, left, frames, context, g)) is not None:
		return closed
	flags = subject.features if subject is not None else 0
	tail, spans = predicate_tail(text, end, results=_RESULT_TAILS)
	right = parser.lexicon.tokenize(text, tail, min(len(text), tail + MAX_WINDOW))
	obj = (
		classified_object(right, g, context)
		if right and right[0].features & g.CLASSIFIER and not right[0].features & g.NOUN
		else _noun(right, context, g)
	)
	if obj is None:
		obj = _stature_ellipsis(text, right, g)
	if (age := _age_reading(parser, text, index, start, tail, left, obj, frames, context, g)) is not None:
		_cache(age, stems, start, frames, context, g)
		return age
	if obj is not None and obj.features & g.AGE_MEASURE:
		return None  # A rejected age complement cannot fall back to growth.
	if obj is not None and obj.head == 0 and right[0].text in {"脸", "臉"}:
		face = _face_reading(
			parser, text, start, index, frames, left, context, g, face_start=right[0].start, spans=spans
		)
		if face is not None:
			_cache(face, stems, start, frames, context, g)
			return face
	product = obj is not None and bool(obj.features & g.GROWTH_PRODUCT)
	height = obj is not None and bool(obj.features & g.STATURE)
	increment = obj is not None and bool(obj.features & g.GROWTH_INCREMENT)
	quantity = _quantity_extent(right, g) if right and right[0].features & (g.NUMBER | g.DET) else False
	distributive = any(text[a:b] in _DISTRIBUTIVE for a, b in modifiers)
	measurement = _measurement(right, g)
	result = any(relation.startswith("compound:") for relation, _, _ in spans)
	if result and obj is not None and not quantity and not obj.features & (g.GROWTH_PRODUCT | g.GROWER | g.HUMAN):
		return None
	aspect = any(relation == "aspect" for relation, _, _ in spans)
	object_aspect = obj is not None and text[right[obj.end - 1].end : right[obj.end - 1].end + 1] == "了"
	if object_aspect:
		pos = right[obj.end - 1].end
		spans += (("aspect", pos, pos + 1),)
	appearance = text[end : end + 1] == "得" and not result
	relative = text[end : end + 1] == "的"
	external = _noun(parser.lexicon.tokenize(text, end + 1, end + 1 + MAX_WINDOW), context, g) if relative else None
	length_relative = (
		external is not None and external.features & g.LENGTH_BEARER and not external.features & g.GROWTH_PRODUCT
	)
	mixed_result = len(stems) == 2 and end - start == 2 and aspect and flags & (g.GROWER | g.GROWTH_PRODUCT)
	adjective = len(stems) == 2 and end - start == 2 and text[end : end + 1] in "的地"
	comparison = text.startswith(("还是短", "還是短", "还是短的", "還是短的"), end)
	coordinated_attribute = False
	if len(right) >= 4 and right[0].features & g.COORD and right[1].features & g.ADJ and right[2].features == g.DE:
		head = _noun(right[3:], context, g)
		coordinated_attribute = head is not None and bool(head.features & g.LENGTH_BEARER)
	# A degree/confirmation adverb can modify a verb too (真长个了 /
	# 真长得好看). Independent verb arguments and complements outrank its
	# adjectival alternative; plain 很长头发 still retains the length analysis.
	verbal_evidence = (
		height
		or aspect
		and flags & g.STATURE
		or result
		and (not flags & g.LENGTH_BEARER or flags & (g.GROWER | g.GROWTH_PRODUCT))
		or appearance
		and (not flags or flags & (g.GROWER | g.GROWTH_PRODUCT | g.PRON))
		or measurement
		and aspect
		and flags & g.GROWTH_PRODUCT
		or product
		and obj is not None
		and any(d.relation == "clf" for d in obj.dependencies)
	)
	degree = degree and not verbal_evidence
	# Remaining degree evidence is adjectival, after independent verb cues.
	# A repeated stem needs the independent 的/地 production or an argument.
	reading, construction = None, None
	if mixed_result:
		reading, construction = ("zhang3" if index == start else "chang2"), "growth-length-result"
	elif degree or adjective or comparison or length_relative or coordinated_attribute:
		reading, construction = "chang2", "degree-length" if degree else "adjectival-length"
	elif location is not None and subject is not None and flags & g.NOUN:
		if flags & g.BODY_SITE or product or result:
			reading, construction = "zhang3", "locative-growth"
	elif result:
		# A length-bearing artifact does not grow merely because 大 follows.
		if obj is not None and not quantity and not obj.features & (g.GROWTH_PRODUCT | g.GROWER | g.HUMAN):
			return None
		if not flags & g.LENGTH_BEARER or flags & (g.GROWER | g.GROWTH_PRODUCT):
			reading, construction = "zhang3", "growth-result"
	elif appearance and (not flags or flags & (g.GROWER | g.GROWTH_PRODUCT | g.PRON)):
		reading, construction = "zhang3", "growth-description"
	elif height or aspect and flags & g.STATURE:
		reading, construction = "zhang3", "stature-growth"
	elif increment and not degree:
		reading, construction = "zhang3", "development-increment"
	elif (
		product and obj is not None and (aspect or object_aspect or any(d.relation == "clf" for d in obj.dependencies))
	):
		reading, construction = "zhang3", "classified-growth-object"
	elif product and subject is not None and flags & (g.GROWER | g.BODY_SITE | g.GROWTH_PRODUCT | g.PRON):
		reading, construction = "zhang3", "growth-object"
	elif subject is not None and flags & g.GROWER:
		reading, construction = "zhang3", "growing-subject"
	elif subject is not None and flags & g.PRON and aspect:
		reading, construction = "zhang3", "growing-subject"
	elif distributive and (aspect or product) and (subject is None or flags & (g.GROWER | g.GROWTH_PRODUCT | g.PRON)):
		reading, construction = "zhang3", "distributed-growth"
	elif measurement and aspect and flags & g.GROWTH_PRODUCT:
		reading, construction = "zhang3", "growth-increment"
	elif subject is not None and flags & g.LENGTH_BEARER and (not aspect or not flags & g.GROWTH_PRODUCT):
		reading, construction = "chang2", "length-predicate"
	elif measurement and not aspect and not flags:
		reading, construction = "chang2", "measured-length"
	if reading is None:
		return None
	frame = _frame(frames, reading)
	if frame is None:
		return None  # Disabling one sense never selects its competitor.
	deps = [g.Dependency(relation, start, a, b) for relation, a, b in spans]
	deps.extend(
		g.Dependency("compound:result" if mixed_result else "redup", start, stem, stem + 1) for stem in stems[1:]
	)
	deps.extend(g.Dependency("advmod", start, a, b) for a, b in modifiers)
	argument, np = (), None
	if subject is not None:
		argument, np = ltokens, subject
		deps.append(
			g.Dependency("obl:location" if location else "nsubj", start, ltokens[0].start, ltokens[subject.end - 1].end)
		)
		deps.extend(subject.dependencies)
		if location:
			deps.append(g.Dependency("case:localizer", ltokens[subject.head].start, *location))
	if (product or increment) and reading == "zhang3":
		deps.append(g.Dependency("obj", start, right[0].start, right[obj.end - 1].end))
		deps.extend(obj.dependencies)
		argument, np = right, obj
	if measurement:
		deps.append(g.Dependency("extent", start, right[0].start, right[1].end))
	begin = argument[0].start if np is not None else start
	finish = argument[np.end - 1].end if np is not None else tail
	head = (
		argument[np.head]
		if np is not None
		else g.Token(start, start + 1, text[start], g.VERB if reading == "zhang3" else g.ADJ)
	)
	parsed = g.SyntaxReading(
		reading,
		frame.id,
		frame.object_class,
		index,
		begin,
		finish,
		head.start,
		head.end,
		tuple(argument[: np.end]) if np is not None else (head,),
		tuple(deps),
		construction,
	)
	_cache(parsed, stems, start, frames, context, g, mixed=mixed_result)
	return parsed
