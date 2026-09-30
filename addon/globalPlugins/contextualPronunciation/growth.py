"""Local argument and complement selection for 长 / 長.

Nominal senses are candidates. A body location, a growing subject or an actual
growth-product head must attach to THIS predicate. Degree and measurement
constructions instead select length. Unknown bare uses remain undecided.
"""

from __future__ import annotations

from .constituents import ConstituentParser
from .verb_forms import predicate_form, predicate_tail

MAX_WINDOW = 96
_HEIGHT_HEADS = frozenset(("个子", "個子", "个儿", "個兒"))
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
			or word[1:] in _HEIGHT_HEADS | {"脸", "臉", "脸型", "臉型", "个", "個"}
		)
	)


def _frame(frames, reading):
	for frame in frames:
		if frame.reading == reading:
			return frame
	return None


def _face_reading(parser, text, start, index, frames, left, context, g):
	ltokens, subject, _, degree, modifiers = left
	end = start + 2
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
		deps.append(g.Dependency("compound:idiom" if honor and not shape else "amod", start, start + 1, end))
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
		start + 1,
		end,
		start + 1,
		end,
		(g.Token(start + 1, end, text[start + 1 : end], g.NOUN | g.BODY_SITE),),
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


def _closed_reading(text, index, start, end, stems, left, frames, context, g):
	"""Closed predicates need no right NP chart or complement search."""
	tokens, np, location, degree, modifiers = left
	flags = np.features if np is not None else 0
	aspect = text[end : end + 1] in {"了", "着", "著", "过", "過"}
	tail = end + int(aspect)
	if tail < len(text) and (g._is_han(text[tail]) or text[tail] in g._NUMBERS | g._SPACES):
		return None
	distributed = any(text[a:b] in _DISTRIBUTIVE for a, b in modifiers)
	mixed = len(stems) == 2 and end - start == 2 and aspect and flags & (g.GROWER | g.GROWTH_PRODUCT)
	if degree:
		reading, construction = "chang2", "degree-length"
	elif mixed:
		reading, construction = ("zhang3" if index == start else "chang2"), "growth-length-result"
	elif location is not None and flags & g.BODY_SITE:
		reading, construction = "zhang3", "locative-growth"
	elif aspect and np is not None and tokens[np.head].text in _HEIGHT_HEADS:
		reading, construction = "zhang3", "stature-growth"
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
		and not contextual_lexeme(word)
		and not _measurement(parser.lexicon.tokenize(text, start + 1, start + 17), g)
	):
		return None  # Preserve intact compounds and names (长江 / 长裙 / 长子).
	left = _left(parser, text, start, context, g)
	if left is None:
		return None
	ltokens, subject, location, degree, modifiers = left
	if text.startswith(("长脸", "長臉"), start):
		return _face_reading(parser, text, start, index, frames, left, context, g)
	if (closed := _closed_reading(text, index, start, end, stems, left, frames, context, g)) is not None:
		return closed
	flags = subject.features if subject is not None else 0
	tail, spans = predicate_tail(text, end, results=_RESULT_TAILS)
	right = parser.lexicon.tokenize(text, tail, min(len(text), tail + MAX_WINDOW))
	obj = _noun(right, context, g)
	product = obj is not None and bool(obj.features & g.GROWTH_PRODUCT)
	height = obj is not None and right[obj.head].text in _HEIGHT_HEADS
	distributive = any(text[a:b] in _DISTRIBUTIVE for a, b in modifiers)
	measurement = _measurement(right, g)
	result = any(relation.startswith("compound:") for relation, _, _ in spans)
	if result and obj is not None and not obj.features & (g.GROWTH_PRODUCT | g.GROWER | g.HUMAN):
		return None
	aspect = any(relation == "aspect" for relation, _, _ in spans)
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
	# Degree + 长 is adjectival even if its subject is a body part or person.
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
		if obj is not None and not obj.features & (g.GROWTH_PRODUCT | g.GROWER | g.HUMAN):
			return None
		if not flags & g.LENGTH_BEARER or flags & (g.GROWER | g.GROWTH_PRODUCT):
			reading, construction = "zhang3", "growth-result"
	elif appearance and (not flags or flags & (g.GROWER | g.GROWTH_PRODUCT | g.PRON)):
		reading, construction = "zhang3", "growth-description"
	elif height or aspect and subject is not None and ltokens[subject.head].text in _HEIGHT_HEADS:
		reading, construction = "zhang3", "stature-growth"
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
	if product and reading == "zhang3":
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
