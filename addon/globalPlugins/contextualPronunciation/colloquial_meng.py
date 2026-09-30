"""Positive, bounded evidence for the colloquial confusion sense of 懵.

This is a compatibility policy, NOT a default reading for the character. A bare
character, a lexical mention, and an unsupported context abstain. Reviewed
literary phrases and user decisions are resolved before this handler is called.
See docs/COLLOQUIAL_MENG.md for source evidence, constructed examples and limits.

Only fixed-size slices and fixed inventories are inspected. No sentence scan,
regular-expression backtracking, dictionary lookup, I/O or cross-item cache is
used. Reiteration examines at most one peer, never recursively propagating a hit.
"""

from __future__ import annotations

from typing import Final

WINDOW: Final = 24
# These are morphemes/grammatical cues, not a finite list of complete sentences.
_STATE_SUFFIXES: Final = (
	"了",
	"住",
	"掉",
	"着",
	"著",
	"过",
	"過",
	"起来",
	"起來",
	"下去",
	"下来",
	"下來",
	"过去",
	"過去",
	"极了",
	"極了",
	"坏了",
	"壞了",
	"死了",
	"翻了",
	"炸了",
	"一下",
	"一阵",
	"一陣",
	"一会",
	"一會",
	"半天",
	"半晌",
)
_STATE_NOMINALS: Final = (
	"的样子",
	"的樣子",
	"的表情",
	"的状态",
	"的狀態",
	"的感觉",
	"的感覺",
	"的时候",
	"的時候",
)
_DEGREE_LEFT: Final = (
	"有点",
	"有點",
	"有些",
	"有一点",
	"有一點",
	"有一些",
	"有那么点",
	"有那麼點",
	"有那么一点",
	"有那麼一點",
	"有一丢丢",
	"有一丟丟",
	"有点儿",
	"有點兒",
	"特别",
	"特別",
	"非常",
	"相当",
	"相當",
	"十分",
	"超级",
	"超級",
	"极其",
	"極其",
	"彻底",
	"徹底",
	"完全",
	"瞬间",
	"瞬間",
	"当场",
	"當場",
	"顿时",
	"頓時",
	"直接",
	"立刻",
	"突然",
	"一下子",
	"一时",
	"一時",
	"一直",
	"全程",
	"集体",
	"集體",
	"整个人",
	"整個人",
	"大写的",
	"大寫的",
	"满脑子",
	"滿腦子",
	"更加",
	"这么",
	"這麼",
	"那么",
	"那麼",
	"多么",
	"多麼",
	"不怎么",
	"不怎麼",
	"一点也不",
	"一點也不",
	"一点都不",
	"一點都不",
	"很",
	"挺",
	"太",
	"真",
	"更",
	"最",
	"好",
	"超",
	"巨",
)
_SUBJECTS: Final = (
	"我",
	"你",
	"他",
	"她",
	"咱",
	"俺",
	"您",
	"我们",
	"我們",
	"你们",
	"你們",
	"他们",
	"他們",
	"她们",
	"她們",
	"咱们",
	"咱們",
	"大家",
	"所有人",
	"全场",
	"全場",
	"整个人",
	"整個人",
	"人",
	"全员",
	"全員",
	"观众",
	"觀眾",
	"同学",
	"同學",
	"学生",
	"學生",
	"老师",
	"老師",
	"孩子",
	"小孩",
	"大伙",
	"大夥",
	"宝宝",
	"寶寶",
	"谁",
	"誰",
)
# At most three adjacent modifiers are peeled, and only a grounded subject or
# degree expression licenses the remaining bare predicate. 不/就/还 alone do not.
_PREDICATE_MODIFIERS: Final = frozenset("都也还還又就不没沒别別全已才更真")
_RESULT_VERBS: Final = (
	"看",
	"听",
	"聽",
	"问",
	"問",
	"说",
	"說",
	"讲",
	"講",
	"搞",
	"整",
	"弄",
	"吓",
	"嚇",
	"笑",
	"气",
	"氣",
	"惊",
	"驚",
	"愁",
	"急",
	"疼",
	"打",
	"揍",
	"砸",
	"撞",
	"震",
	"雷",
	"炸",
	"绕",
	"繞",
	"转",
	"轉",
	"晃",
	"摇",
	"搖",
	"闹",
	"鬧",
	"吵",
	"怼",
	"懟",
	"算",
	"考",
	"学",
	"學",
	"背",
	"练",
	"練",
	"刷",
	"玩",
	"忙",
	"累",
	"困",
	"睡",
	"喝",
	"跑",
	"赶",
	"趕",
	"等",
	"熬",
	"忽悠",
	"折腾",
	"折騰",
	"折磨",
	"转悠",
	"轉悠",
	"纠结",
	"糾結",
)
# 读/写/念 + 懵 can instead mean reading/writing the CHARACTER. They need an
# overt result/state suffix, or 得/到, not a bare verb-object substring.
_MENTION_LEFT: Final = (
	"读作",
	"讀作",
	"念作",
	"写作",
	"寫作",
	"写成",
	"寫成",
	"输入",
	"輸入",
	"键入",
	"鍵入",
	"敲入",
	"输出",
	"輸出",
	"字符",
	"汉字",
	"漢字",
	"单字",
	"單字",
	"字头",
	"字頭",
	"名为",
	"名為",
	"名叫",
	"姓",
)
_MENTION_RIGHT: Final = (
	"字",
	"这个字",
	"這個字",
	"这字",
	"這字",
	"此字",
	"的读音",
	"的讀音",
	"的拼音",
	"的声调",
	"的聲調",
	"的发音",
	"的發音",
	"的笔画",
	"的筆畫",
	"的部首",
	"的写法",
	"的寫法",
	"的意思",
	"的含义",
	"的含義",
	"的字形",
	"的字义",
	"的字義",
	"的解释",
	"的解釋",
	"的释义",
	"的釋義",
	"的规范读音",
	"的規範讀音",
	"的笔顺",
	"的筆順",
	"的词性",
	"的詞性",
	"的注音",
	"的声母",
	"的聲母",
	"的韵母",
	"的韻母",
	"的音节",
	"的音節",
	"读几声",
	"讀幾聲",
	"先生",
	"女士",
	"氏",
	"姓",
	"怎么读",
	"怎麼讀",
	"怎么念",
	"怎麼念",
	"如何读",
	"如何讀",
	"读什么",
	"讀什麼",
	"念什么",
	"念什麼",
	"是什么意思",
	"是什麼意思",
	"意为",
	"意為",
	"读作",
	"讀作",
	"念作",
	"读音",
	"讀音",
	"拼音",
	"笔画",
	"筆畫",
	"部首",
	"码位",
	"碼位",
	"在字典",
	"在词典",
	"在詞典",
	"在文言",
	"在古汉语",
	"在古漢語",
	"在甲骨文",
	"在金文",
)
_LITERARY_RIGHT: Final = (
	"之",
	"者",
	"乎",
	"兮",
	"懂",
	"董",
	"憧",
	"昧",
	"钝",
	"鈍",
	"然",
	"愦",
	"憒",
	"瞢",
	"于",
	"於",
	"无知",
	"無知",
	"无识",
	"無識",
	"不知",
	"不晓",
	"不曉",
)
_NUMERALS: Final = frozenset("0123456789０１２３４５６７８９〇零一二三四五六七八九十百千万亿兩两幾几半數数")
_TIME_UNITS: Final = ("秒", "分钟", "分鐘", "小时", "小時", "天", "会儿", "會兒", "阵子", "陣子")


def _index_cues(cues: tuple[str, ...], *, suffix: bool = False) -> dict[str, tuple[str, ...]]:
	"""First/last-character dispatch avoids scanning unrelated fixed cues."""
	buckets: dict[str, list[str]] = {}
	for cue in cues:
		buckets.setdefault(cue[-1] if suffix else cue[0], []).append(cue)
	return {key: tuple(value) for key, value in buckets.items()}


# Combine all protected right prefixes; the only exception is the temporal
# 之後/之后/之前 continuation to the literary 之 marker.
_BLOCKED_PREFIXES: Final = _index_cues(
	(*_MENTION_RIGHT, *_LITERARY_RIGHT, "了解", "了然", "了悟", "过敏", "過敏", "过失", "過失", "着作", "著作")
)
_MENTION_SUFFIXES: Final = _index_cues(_MENTION_LEFT, suffix=True)
_DEGREE_SUFFIXES: Final = _index_cues(_DEGREE_LEFT, suffix=True)
_SUBJECT_SUFFIXES: Final = _index_cues(_SUBJECTS, suffix=True)
_RESULT_SUFFIXES: Final = _index_cues(_RESULT_VERBS, suffix=True)


def _index_reiterations() -> tuple[dict[str, tuple[tuple[str, int], ...]], dict[str, tuple[tuple[str, int], ...]]]:
	"""Compile immutable candidate tuples once, not in the speech hot path."""
	starts: dict[str, list[tuple[str, int]]] = {}
	ends: dict[str, list[tuple[str, int]]] = {}
	for pattern in (
		"懵不懵",
		"懵没懵",
		"懵沒懵",
		"懵归懵",
		"懵歸懵",
		"懵是懵",
		"懵来懵去",
		"懵來懵去",
		"懵上加懵",
		"懵了又懵",
	):
		pivot = pattern.rfind("懵")
		starts.setdefault(pattern[1], []).append((pattern, 0))
		ends.setdefault(pattern[pivot - 1], []).append((pattern, pivot))
	return (
		{key: tuple(value) for key, value in starts.items()},
		{key: tuple(value) for key, value in ends.items()},
	)


_REITERATION_STARTS, _REITERATION_ENDS = _index_reiterations()


def _han(character: str) -> bool:
	return "\u3400" <= character <= "\u9fff"


def _predicate_end(right: str) -> bool:
	# Only a genuine local end/particle licenses weak left-only evidence. This
	# prevents 看懵字 / 我懵氏 from being interpreted as a result/state predicate.
	return (
		not right
		or not _han(right[0])
		or right.startswith(
			(
				"吗",
				"嗎",
				"呢",
				"吧",
				"啊",
				"呀",
				"哦",
				"喔",
				"嘛",
				"啦",
				"的",
				"得",
				"到",
				"成",
				"而",
				"但",
				"也",
				"还",
				"還",
				"就",
				"却",
				"卻",
				"才",
				"所以",
				"然后",
				"然後",
				"之后",
				"之後",
				"之前",
				"以后",
				"以後",
				"以前",
				"不过",
				"不過",
				"仍",
				"并",
				"並",
				"又",
				"不",
				"没",
				"沒",
			)
		)
	)


def _blocked(left: str, right: str) -> bool:
	if left:
		last = left[-1]
		if last.isascii() and (last.isalnum() or last == "_"):
			return True
		endings = _MENTION_SUFFIXES.get(last)
		if endings is not None and left.endswith(endings):
			return True
	if right:
		first = right[0]
		beginnings = _BLOCKED_PREFIXES.get(first)
		if beginnings is not None and right.startswith(beginnings):
			return not (first == "之" and right.startswith(("之后", "之後", "之前")))
	return False


def _base(left: str, right: str) -> str | None:
	"""Classify a window already checked by _blocked in classify."""
	# End-delimited 越V越懵 cannot match any of the lexical/complement cases
	# below. Dispatch this productive comparative without scanning their cues.
	if left.endswith("越") and (not right or not right[0].isalnum()):
		previous = left.rfind("越", 0, len(left) - 1)
		between = left[previous + 1 : -1] if previous >= 0 else ""
		if between and all(_han(ch) for ch in between):
			return "comparative-state"
	if (
		right.startswith(("逼", "圈"))
		or right.startswith("比")
		and not right.startswith(("比较", "比較", "比赛", "比賽", "比例", "比率"))
	):
		return "colloquial-lexeme"
	if right[:1] in ("B", "b", "Ｂ", "ｂ") and (
		len(right) == 1 or not right[1].isascii() or not (right[1].isalnum() or right[1] == "_")
	):
		return "colloquial-lexeme"
	if left.endswith(("发", "發", "犯")):
		return "confusion-inchoative"
	if left.endswith(("满脸", "滿臉")):
		return "facial-state"
	if left.endswith(("脸", "臉")):
		# Productive numeral + 脸 (一脸/万脸/两脸…), bounded to six digits.
		position = len(left) - 2
		for _ in range(6):
			if position < 0 or left[position] not in _NUMERALS:
				break
			position -= 1
		if position < len(left) - 2 and (position < 0 or left[position] not in _NUMERALS):
			return "facial-state"
	if right.startswith(_STATE_SUFFIXES) or right.startswith(_STATE_NOMINALS):
		return "state-predicate"
	# Open complement slot: do not enumerate 说不出话/忘了回复/怀疑人生/etc.
	if right[:1] in ("得", "到", "成", "在") and len(right) > 1 and _han(right[1]):
		return "state-complement"
	if right and right[0] in _NUMERALS:
		position = 0
		for _ in range(6):
			if position == len(right) or right[position] not in _NUMERALS:
				break
			position += 1
		if right.startswith(_TIME_UNITS, position):
			return "state-duration"
	if right.startswith(("吗", "嗎", "呢", "吧", "啊", "呀", "嘛", "啦")) and (len(right) == 1 or not _han(right[1])):
		return "state-question"
	if right.startswith(("ing", "ING")) and (
		len(right) == 3 or not right[3].isascii() or not (right[3].isalnum() or right[3] == "_")
	):
		return "colloquial-progressive"
	if left.endswith(("又", "既")) and right.startswith(("又", "且")) and len(right) > 1 and _han(right[1]):
		return "coordinated-state"
	if left.endswith("越") and right.startswith("越") and len(right) > 1 and _han(right[1]):
		return "comparative-state"
	if left.endswith(
		(
			"怎么会",
			"怎麼會",
			"怎么就",
			"怎麼就",
			"咋就",
			"咋会",
			"咋會",
			"怎么还",
			"怎麼還",
			"为什么会",
			"為什麼會",
			"怎么不",
			"怎麼不",
			"怎么能",
			"怎麼能",
		)
	) and _predicate_end(right):
		return "state-question"
	if left.endswith(_DEGREE_SUFFIXES.get(left[-1:], ())):
		return "degree-state"
	if left.endswith(("别", "別")) and _predicate_end(right):
		return "state-imperative"
	if left.endswith(_RESULT_SUFFIXES.get(left[-1:], ())) and _predicate_end(right):
		return "resultative"
	if (
		left.endswith(("得", "到", "不"))
		and left[:-1].endswith(_RESULT_SUFFIXES.get(left[-2:-1], ()))
		and _predicate_end(right)
	):
		return "resultative-complement"
	if (
		left.endswith(("得", "到"))
		and left[:-1].endswith(("读", "讀", "写", "寫", "念", "认", "認"))
		and _predicate_end(right)
	):
		return "resultative-complement"
	stem = left
	for _ in range(4):
		if stem.endswith(_SUBJECT_SUFFIXES.get(stem[-1:], ())) and _predicate_end(right):
			return "subject-state"
		if not stem or stem[-1] not in _PREDICATE_MODIFIERS:
			break
		stem = stem[:-1]
	# 越V越懵 needs a paired 越 and a short all-Han intervening constituent.
	if left.endswith("越"):
		previous = left.rfind("越", 0, len(left) - 1)
		between = left[previous + 1 : -1] if previous >= 0 else ""
		if between and all(_han(ch) for ch in between) and _predicate_end(right):
			return "comparative-state"
	return None


def classify(text: str, index: int) -> str | None:
	"""Return positive grammatical evidence, or None; never infer a default tone."""
	# A long bare character run cannot acquire a predicate from a distant cue.
	if (
		text.startswith("懵懵", index + 1)
		or text[max(0, index - 2) : index] == "懵懵"
		or (index > 0 and text[index - 1] == "懵" and text[index + 1 : index + 2] == "懵")
	):
		return None
	left = text[max(0, index - WINDOW) : index]
	right = text[index + 1 : index + 1 + WINDOW]
	if _blocked(left, right):
		return None
	# Both occurrences in bounded reiterative constructions, independently of
	# adjacent text. Literary/mixed runs do not inherit a neighbour's decision.
	# Index the fixed constructions by the immediately adjacent morpheme.
	# Impossible candidates need no string match (or per-character rfind).
	blocked_reiteration = False
	for candidates in (
		_REITERATION_STARTS.get(right[:1], ()),
		_REITERATION_ENDS.get(left[-1:], ()),
	):
		for pattern, pivot in candidates:
			start = index - pivot
			if start >= 0 and text.startswith(pattern, start):
				end = start + len(pattern)
				if not _blocked(text[max(0, start - WINDOW) : start], text[end : end + WINDOW]):
					return "reiteration"
				blocked_reiteration = True
	if blocked_reiteration:
		# A complete construction named as text must not fall through to a
		# weaker 看/问/我 cue and correct only its first occurrence.
		return None
	if right.startswith("懵") or left.endswith("懵"):
		start = index - 1 if left.endswith("懵") else index
		end = start + 2
		if (start and text[start - 1] == "懵") or text[end : end + 1] == "懵":
			return None  # Unbounded repeated characters are not grammatical evidence.
		before, after = text[max(0, start - WINDOW) : start], text[end : end + WINDOW]
		if _blocked(before, after):
			return None
		if after[:1] in {"哒", "噠"} and _blocked(before, after[1:]):
			return None
		if (
			after.startswith(("的", "哒", "噠")) or after.startswith("地") and len(after) > 1 and _han(after[1])
		) and not after.startswith(_MENTION_RIGHT):
			return "reduplicated-state"
		return _base(before, after)
	return _base(left, right)
