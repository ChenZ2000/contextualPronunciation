"""Typed constituent grammar and productive predicate morphology.

Multi-source lexical alternatives constrain a memoized constituent chart. It
composes modifiers, coordination, relatives and preposed arguments without
enumerating sentences. This is a bounded symbolic grammar, not an open-domain
semantic oracle. Only dictionary evidence plus a reviewed frame emits a reading.
No I/O, timers, persistent document cache or speech buffering occurs here.
"""

from __future__ import annotations

import json
import sys
import tomllib
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from types import MappingProxyType

from .constituents import ConstituentParser
from .edges import DIRECTIONS, coordination_pair, edge_reading
from .nominals import general_role
from .predicates import _MODALS

_GRAMMAR = sys.modules[__name__]
NOUN, VERB, ADJ, ADV, PRON, PREP, CLASSIFIER, DET, NUMBER = (1 << n for n in range(9))
FOOD, POSSIBLE_FOOD, DIMENSION, FASTENER, STOP, DE, UNKNOWN = (1 << n for n in range(9, 16))
FOOD_COMPOUND = 1 << 16
CONTENTS, POSSIBLE_CONTENTS, CONTAINER = (1 << n for n in range(17, 20))
COORD, ADVERBIAL, COMPLEMENT = (1 << n for n in range(20, 23))
CONTAINER_MEASURE = 1 << 23
HUMAN, MILITARY, PERSON_MEASURE = (1 << n for n in range(28, 31))
EDGE_NOUN, SPEECH_VERB = 1 << 31, 1 << 32
MAX_CHARS = 512
MAX_TOKENS = 256
MAX_DEPTH = 16
MAX_CHART_STATES = 4096
MAX_CHART_WORK = 8192
MAX_ITEM_WORK = 65536
MAX_OWNER_CHARS = 8
MAX_MORPH = 8
_SPACES = frozenset(" \t\u00a0\u3000")
_NUMBERS = frozenset("0123456789０１２３４５６７８９〇零一二两兩三四五六七八九十百千万萬半几幾")
_NONREPEAT_PREDICATES = frozenset(
	(
		"是",
		"有",
		"存在",
		"属于",
		"屬於",
		"等于",
		"等於",
		"姓",
		"需要",
		"应该",
		"應該",
		"能够",
		"能夠",
		"可以",
		"必须",
		"必須",
		"可能",
	)
)
_LOCALIZERS = frozenset(("旁边", "旁邊", "里面", "裡面", "外面", "上面", "下面", "前面", "后面", "後面", "附近"))
# Reinstall versus heavy equipment: bare 装 cannot select the sense. Reviewed
# lexical rules already select 重装软件/系统 and protect 重装部队/重装甲.
_AMBIGUOUS_REPEAT_PREDICATES = frozenset(("装", "裝"))
_HEAD_CLASSES = {
	"food": FOOD,
	"contents": FOOD | CONTENTS,
	"container": CONTAINER,
	"dimension": DIMENSION,
	"fastener": FASTENER,
	"predicate": VERB,
	"nominalGeneral": NOUN,
	"edgeNoun": EDGE_NOUN,
	"coordinatingPredicate": VERB,
}
_FUNCTIONS = {
	"的": DE,
	"地": ADVERBIAL,
	"得": COMPLEMENT,
	**dict.fromkeys(("而且", "并且", "並且", "且", "而", "又", "和", "与", "與", "及"), COORD),
	**dict.fromkeys(("这", "那", "這", "每"), DET),
	**dict.fromkeys(("了", "过", "過", "着", "著"), ADV),
	**dict.fromkeys(("好", "新", "红", "紅", "热", "熱", "冷"), ADJ),
	**dict.fromkeys(("刚", "剛", "刚刚", "剛剛", "已经", "已經", "才", "很", "非常"), ADV),
	**dict.fromkeys(
		(
			"的时候",
			"的時候",
			"之后",
			"之後",
			"以后",
			"以後",
			"然后",
			"然後",
			"并",
			"並",
			"但",
			"但是",
			"以及",
			"或者",
			"或",
			"也",
			"再",
			"就",
			"吗",
			"嗎",
			"呢",
			"吧",
			"啊",
		),
		STOP,
	),
}
_FUNCTIONS.update(dict.fromkeys(("再", "也", "就", "都"), ADV))
# These lexical adverbs must retain their whole-word analysis. In particular,
# the classifier sense of 起 does not license segmenting the adverb 一起.
_FUNCTIONS.update(dict.fromkeys(("一起", "一同", "一齐", "一齊", "一直", "一并", "一併"), ADV))


def _is_han(ch):
	# I Ching symbols U+4DC0..U+4DFF lie BETWEEN the two Han blocks.
	return "\u3400" <= ch <= "\u4dbf" or "\u4e00" <= ch <= "\u9fff"


@dataclass(frozen=True, slots=True)
class Token:
	start: int
	end: int
	text: str
	features: int


@dataclass(frozen=True, slots=True)
class Dependency:
	relation: str
	head: int
	start: int
	end: int


@dataclass(frozen=True, slots=True)
class NounPhrase:
	end: int  # token offset (exclusive)
	head: int  # token offset
	features: int
	front_head: int
	dependencies: tuple[Dependency, ...] = ()


@dataclass(frozen=True, slots=True)
class SyntaxReading:
	reading: str
	rule_id: str
	object_class: str
	target: int
	object_start: int
	object_end: int
	head_start: int
	head_end: int
	tokens: tuple[Token, ...]
	dependencies: tuple[Dependency, ...]
	construction: str = "transitive"


@dataclass(frozen=True, slots=True)
class ArgumentFrame:
	id: str
	target: str
	reading: str
	object_class: str
	prefixes: tuple[str, ...]
	source: str
	positive: tuple[str, ...]
	negative: tuple[str, ...]
	relative_heads: tuple[str, ...] = ()
	blocked_left: tuple[str, ...] = ()
	blocked_right: tuple[str, ...] = ()


class SyntaxContext:
	"""Ephemeral per-speech-item prefilter; never retained by the parser."""

	__slots__ = ("head_classes", "remaining_work")

	def __init__(self, text, lexicon):
		characters = frozenset(text)
		self.head_classes = frozenset(
			name for name, tails in lexicon.head_tails.items() if not tails.isdisjoint(characters)
		)
		self.remaining_work = MAX_ITEM_WORK

	def consume(self, amount):
		self.remaining_work -= amount
		return self.remaining_work >= 0


class SyntaxLexicon:
	def __init__(
		self,
		words,
		head_classes=None,
		evidence=None,
		repeat_blockers=None,
		opaque_repeat_blockers=None,
		general_nouns=None,
	):
		self.words = MappingProxyType(dict(words))
		self.evidence = MappingProxyType(dict(evidence or {}))
		self.general_nouns = frozenset(general_nouns or ())
		blockers = {}
		for opaque, entries in ((False, repeat_blockers), (True, opaque_repeat_blockers)):
			for word, offsets in (entries or {}).items():
				for offset in offsets:
					key = (word[offset - 1] if offset else "", word[offset + 1 : offset + 2])
					blockers.setdefault(key, []).append((word, offset, opaque))
		self.repeat_blockers = MappingProxyType({k: tuple(v) for k, v in blockers.items()})
		self.head_classes = MappingProxyType(dict(_HEAD_CLASSES if head_classes is None else head_classes))
		lengths = {}
		for word in words:
			lengths.setdefault(word[0], set()).add(len(word))
		self.lengths = MappingProxyType({ch: tuple(sorted(values, reverse=True)) for ch, values in lengths.items()})
		self.head_tails = {
			name: frozenset(
				word[-1]
				for word, flags in words.items()
				if flags
				& (
					feature
					| (FOOD_COMPOUND if feature & FOOD else 0)
					| (CONTAINER_MEASURE if feature & CONTENTS else 0)
				)
			)
			for name, feature in self.head_classes.items()
		}

	def longest(self, text, start, end):
		for length in self.lengths.get(text[start], ()):
			if start + length <= end:
				word = text[start : start + length]
				if (features := self.words.get(word)) is not None:
					return word, features
		return text[start], UNKNOWN

	def blocks_repeat(self, text, index, predicate_end, compositional=False):
		left, right = text[index - 1 : index] if index else "", text[index + 1 : index + 2]
		for key in {(left, right), ("", right), (left, "")}:
			for word, pivot, opaque in self.repeat_blockers.get(key, ()):
				if opaque and compositional and pivot == 0 and index + len(word) == predicate_end:
					continue
				if pivot == 0 and index + len(word) < predicate_end:
					continue  # 重压 must not cut the independently attested verb 压缩.
				if index >= pivot and text.startswith(word, index - pivot):
					return True
		return False

	def tokenize(self, text, start):
		"""Bounded longest lexical segmentation; never skips unknown material."""
		end = min(len(text), start + MAX_CHARS)
		position, tokens, spaces = start, [], 0
		while position < end and len(tokens) < MAX_TOKENS:
			ch = text[position]
			if ch in _SPACES:
				spaces += 1
				if spaces > 4:
					return ()
				position += 1
				continue
			spaces = 0
			word, flags = ch, UNKNOWN
			if _is_han(ch):
				word, flags = self.longest(text, position, end)
				if ch in DIRECTIONS and len(word) > 1:
					next_word, next_flags = self.longest(text, position + 1, end)
					if next_flags & EDGE_NOUN and len(next_word) >= len(word):
						word, flags = ch, ADJ
				if (
					len(word) > 1
					and word.endswith("和")
					and coordination_pair(
						self,
						text,
						position + len(word) - 1,
						_GRAMMAR,
					)
					is not None
				):
					word = word[:-1]
					flags = self.words[word]
				# Competing segmentation: 训练有素 / 的 / 士兵 versus
				# 训练有素 / 的士 / 兵. Require a preceding modifier and a
				# complete multi-character noun across the lexical overlap.
				if ch == "的" and len(word) > 1 and flags & NOUN and tokens:
					next_word, next_flags = self.longest(text, position + 1, end)
					if len(next_word) >= len(word) and next_flags & NOUN:
						word, flags = ch, DE
			elif ch not in _NUMBERS:
				break  # Symbols, punctuation, controls and non-Han script are hard boundaries.
			# Lexicalized nouns such as 三明治 / 八宝粥 take precedence over
			# their initial numeral. Actual numeric sequences remain bounded.
			quantity_adjective = (
				flags & ADJ
				and self.words.get(word[-1], 0) & ADJ
				and self.words.get(text[position + len(word) : position + len(word) + 1], 0) & CLASSIFIER
			)
			if ch in _NUMBERS and (
				len(word) == 1
				or flags & (NUMBER | CLASSIFIER)
				or quantity_adjective
				or all(c in _NUMBERS for c in word)
			):
				stop = position + 1
				while stop < end and text[stop] in _NUMBERS:
					stop += 1
				if stop - position > 12:
					return ()
				word, flags = text[position:stop], NUMBER
			# A statistical dictionary may tag 大碗 / 小碗 as one numeral.
			# Expose adjective + attested classifier only in a quantity position.
			if len(word) > 1 and ch not in _NUMBERS and tokens and tokens[-1].features & (NUMBER | DET):
				if self.words.get(ch, 0) & ADJ and self.words.get(word[1:], 0) & CLASSIFIER:
					word, flags = ch, self.words[ch]
				elif self.words.get(ch, 0) & CONTAINER_MEASURE and self.words.get(word[1:], 0) & (
					FOOD | POSSIBLE_FOOD | CONTENTS | POSSIBLE_CONTENTS
				):
					word, flags = ch, self.words[ch]
			tokens.append(Token(position, position + len(word), word, flags))
			position += len(word)
			if flags == STOP:
				break
		# Mark an incomplete tail instead of dropping an already complete
		# object before a following predicate. A truncated NP itself fails at
		# UNKNOWN; a finished NP before an independent predicate stays valid.
		if position < len(text) and (position == end or len(tokens) == MAX_TOKENS):
			if _is_han(text[position]) or text[position] in _NUMBERS | _SPACES:
				tokens.append(Token(position, position, "", UNKNOWN))
		return tuple(tokens)


class _NounParser(ConstituentParser):
	def __init__(self, tokens, context=None):
		super().__init__(tokens, _GRAMMAR, context)


class ArgumentParser:
	def __init__(self, lexicon, frames):
		self.lexicon = lexicon
		self.frames = tuple(frames)
		self.triggers = frozenset(frame.target for frame in self.frames)
		self.buckets = {ch: tuple(f for f in self.frames if f.target == ch) for ch in self.triggers}
		self.morphologies = {}
		for frame in self.frames:
			# Compile first-character alternatives once. Most objects do not
			# begin with morphology; they must not scan every verb/aspect form.
			bare = ("",) if "" in frame.prefixes else ()
			initials = {p[0] for p in frame.prefixes if p}
			self.morphologies[frame.id] = {
				"": bare,
				**{ch: tuple(p for p in frame.prefixes if p.startswith(ch)) + bare for ch in initials},
			}

	def context(self, text):
		return SyntaxContext(text, self.lexicon)

	def contextual_lexeme(self, word, offset=0):
		"""A bound nominal head may overlap a dictionary future auxiliary."""
		return (
			word[offset : offset + 1] in {"边", "邊"}
			and bool(self.lexicon.words.get(word, 0) & EDGE_NOUN)
			or offset == 0
			and len(word) > 1
			and word[0] in "将將"
			and word[1:] in _MODALS
			or offset == len(word) - 1
			and word.endswith("和")
			and bool(self.lexicon.words.get(word[:-1], 0) & SPEECH_VERB)
		)

	def _object(self, tokens, frame, target, context=None):
		feature = self.lexicon.head_classes[frame.object_class]
		if len(tokens) == 1 and tokens[0].features & feature:
			return NounPhrase(1, 0, tokens[0].features, 0), ()
		if len(tokens) == 3 and tokens[1].features == DE and tokens[2].features & feature:
			left = tokens[0].features
			if left & (NOUN | PRON | ADJ) and not left & (STOP | UNKNOWN):
				relation = "amod" if left & ADJ else "nmod"
				dep = Dependency(relation, tokens[2].start, tokens[0].start, tokens[1].end)
				return NounPhrase(3, 2, tokens[2].features, 0 if relation == "nmod" else 2, (dep,)), ()
		# Frequent unambiguous production V N 的 N: type the two heads
		# directly before allocating a chart (e.g. 盛装 液体 的 容器).
		if len(tokens) == 3 and tokens[1].features == DE and tokens[0].features & feature:
			if not tokens[2].features & feature and any(
				tokens[2].features & self.lexicon.head_classes[name] for name in frame.relative_heads
			):
				return NounPhrase(1, 0, tokens[0].features, 0), (
					Dependency("acl", tokens[2].start, target, tokens[1].end),
				)
		np = _NounParser(tokens, context).parse()
		if np is not None and np.features & feature:
			return np, ()
		if not frame.relative_heads:
			return None
		relative_feature = 0
		for name in frame.relative_heads:
			relative_feature |= self.lexicon.head_classes[name]
		# Keep both attachments available: V [owner 的 object] versus
		# [V object 的] container/tool. A typed external head is required;
		# do not truncate arbitrary 的 + noun until a desired object appears.
		for boundary, token in enumerate(tokens):
			if token.features != DE or not 0 < boundary < len(tokens) - 1:
				continue
			left = _NounParser(tokens[:boundary], context).parse()
			if left is None or left.end != boundary or not left.features & feature:
				continue
			right_tokens = tokens[boundary + 1 :]
			right = _NounParser(right_tokens, context).parse()
			if right is not None and right.features & relative_feature:
				head = right_tokens[right.head].start
				return left, (Dependency("acl", head, target, token.end),)
		return None

	def _repeat(self, text, index, frame):
		"""Productive re- + predicate; not an enumeration of 重-prefixed words."""
		start = index + 1
		if start == len(text) or text[start] == "重" or not _is_han(text[start]):
			return None
		# Degree-marked 重 is an adjective: 很重转不动. Word-internal 重
		# and dictionary homographs are blocked by their attested lexical senses.
		if text[max(0, index - 4) : index].endswith(
			("很", "太", "更", "最", "非常", "比较", "比較", "十分", "多么", "多麼")
		):
			return None
		word, flags = self.lexicon.longest(text, start, min(len(text), start + 16))
		if word in _NONREPEAT_PREDICATES | _AMBIGUOUS_REPEAT_PREDICATES or word.startswith(
			("不", "没", "沒", "未", "无", "無")
		):
			return None
		# An adjective/nominal reading competes with an alleged verb. Only
		# overt verbal syntax (aspect, object marking, repetition) selects it.
		if not flags & VERB or flags & (STOP | DE | UNKNOWN):
			return None
		end = start + len(word)
		compositional = (
			len(word) > 1
			and not flags & (NOUN | ADJ | PRON | PREP | CLASSIFIER)
			and (self.lexicon.evidence.get(word, 0) >> 12).bit_count() >= 2
		)
		if self.lexicon.blocks_repeat(text, index, end, compositional):
			return None
		if flags & (NOUN | ADJ | PRON | PREP | CLASSIFIER):
			evidence = self.lexicon.evidence.get(word, 0)
			if not evidence & (1 << 14) and not text.startswith(
				("了", "过", "過", "着", "著", "一次", "一遍", "一下"), end
			):
				return None
		# Do not split an incomplete unknown compound after a single verb.
		if end < len(text) and _is_han(text[end]):
			_next, following = self.lexicon.longest(text, end, min(len(text), end + 16))
			if following == UNKNOWN:
				return None
		token = Token(start, end, word, flags)
		return SyntaxReading(
			frame.reading,
			frame.id,
			"predicate",
			index,
			start,
			end,
			start,
			end,
			(token,),
			(Dependency("advmod", start, index, index + 1),),
			"repetitive-prefix",
		)

	def _preposed(self, text, index, frame, context=None):
		"""Find an explicit 把/将 NP V construction in this punctuation span."""
		left = max(0, index - MAX_CHARS)
		# A single bounded backward walk, never a search across speech items.
		for position in range(index - 1, left - 1, -1):
			ch = text[position]
			if not (_is_han(ch) or ch in _SPACES or ch in _NUMBERS):
				break
			if ch not in "把将將":
				continue
			tokens = self.lexicon.tokenize(text[:index], position + 1)
			np = _NounParser(tokens, context).parse()
			if np is None or not np.features & self.lexicon.head_classes[frame.object_class]:
				continue
			remaining = tokens[np.end :]
			# Object-to-verb material must be a grammatical adverbial, not
			# another predicate whose object happens to match our semantic type.
			if remaining:
				if any(not t.features & (ADV | ADJ | ADVERBIAL) for t in remaining):
					continue
				if (
					any(t.features & ADJ and not t.features & ADV for t in remaining)
					and remaining[-1].features != ADVERBIAL
				):
					continue
			head, last = tokens[np.head], tokens[np.end - 1]
			return SyntaxReading(
				frame.reading,
				frame.id,
				frame.object_class,
				index,
				tokens[0].start,
				last.end,
				head.start,
				head.end,
				tokens[: np.end],
				(Dependency("obj", index, tokens[0].start, last.end), *np.dependencies),
				"ba-preposed",
			)
		return None

	def analyze(self, text: str, index: int, context=None) -> SyntaxReading | None:
		if not 0 <= index < len(text):
			return None
		matches = []
		for frame in self.buckets.get(text[index], ()):
			if frame.object_class in {"edgeNoun", "coordinatingPredicate"}:
				if (parsed := edge_reading(self, text, index, frame, context, _GRAMMAR)) is not None:
					matches.append(parsed)
				continue
			if frame.object_class == "nominalGeneral":
				if (nominal := general_role(self, text, index, frame, context, _GRAMMAR)) is not None:
					matches.append(nominal)
				continue
			if frame.object_class == "predicate":
				if (repeat := self._repeat(text, index, frame)) is not None:
					matches.append(repeat)
				continue
			if context is not None and (context.remaining_work <= 0 or frame.object_class not in context.head_classes):
				continue
			# Necessary lexical condition only: an eventual semantic head must
			# end in one of these characters. Avoid allocating a token chart on
			# dense candidate-only input; a hit still needs the full grammar.
			if frame.blocked_left and text[max(0, index - 16) : index].endswith(frame.blocked_left):
				continue
			if frame.blocked_right and text.startswith(frame.blocked_right, index + 1):
				continue
			if self.lexicon.head_tails[frame.object_class].isdisjoint(
				text[index + 1 : index + MAX_CHARS + MAX_MORPH + 1]
			):
				if index and any(ch in text[max(0, index - MAX_CHARS) : index] for ch in "把将將"):
					if (preposed := self._preposed(text, index, frame, context)) is not None:
						matches.append(preposed)
				continue
			lexical = None
			bare_object = None
			# Try bounded morphological analyses, rather than irrevocably eating
			# 装 from 装饰品 or 好 from 好看的衣服. Longest valid morphology wins.
			forms = self.morphologies[frame.id]
			for prefix in forms.get(text[index + 1 : index + 2], forms[""]):
				if context is not None and context.remaining_work <= 0:
					break
				start = index + 1 + len(prefix)
				if start >= len(text) or not text.startswith(prefix, index + 1):
					continue
				if prefix:
					if lexical is None:
						lexical = self.lexicon.longest(text, index + 1, min(len(text), index + 17))
					word, flags = lexical
					if len(word) > len(prefix) and flags & (NOUN | ADJ) and not flags & VERB:
						# Prefer the intact noun only if it forms a valid argument.
						# A blind longest-word veto would also misread 盛过气体
						# as 盛 / 过气 / 体 instead of 盛过 / 气体.
						if bare_object is None:
							bare_object = (
								self._object(self.lexicon.tokenize(text, index + 1), frame, index, context) is not None
							)
						if bare_object:
							continue
				tokens = self.lexicon.tokenize(text, start)
				if not tokens:
					continue
				construction = "transitive"
				if tokens[0].features == DE:
					# [盛装 __ 的] 液体: the semantic argument is the external
					# head of an object-gap relative, not a fabricated object 装.
					de_end = tokens[0].end
					tokens = tokens[1:]
					np = _NounParser(tokens, context).parse()
					if np is None or not np.features & self.lexicon.head_classes[frame.object_class]:
						continue
					external = (Dependency("acl", tokens[np.head].start, index, de_end),)
					construction = "object-relative"
				else:
					parsed = self._object(tokens, frame, index, context)
					if parsed is None:
						continue
					np, external = parsed
				head, last = tokens[np.head], tokens[np.end - 1]
				object_deps = (
					(Dependency("obj", index, tokens[0].start, last.end),) if construction == "transitive" else ()
				)
				matches.append(
					SyntaxReading(
						frame.reading,
						frame.id,
						frame.object_class,
						index,
						tokens[0].start,
						last.end,
						head.start,
						head.end,
						tokens[: np.end],
						(*object_deps, *np.dependencies, *external),
						construction,
					)
				)
				break
			else:
				if index and any(ch in text[max(0, index - MAX_CHARS) : index] for ch in "把将將"):
					if (preposed := self._preposed(text, index, frame, context)) is not None:
						matches.append(preposed)
		if len({item.reading for item in matches}) != 1:
			return None
		return matches[0]


@lru_cache(maxsize=1)
def _load_data():
	data_dir = Path(__file__).with_name("data")
	with (data_dir / "syntax_lexicon.json").open("r", encoding="utf-8") as stream:
		data = json.load(stream)
	with (data_dir / "syntax_frames.toml").open("rb") as stream:
		grammar = tomllib.load(stream)
	with (data_dir / "grammar_lexicon.json").open("r", encoding="utf-8") as stream:
		evidence = json.load(stream)
	with (data_dir / "contributions.toml").open("rb") as stream:
		classes = tomllib.load(stream)["classes"]
	if data.get("schemaVersion") != 2 or grammar.get("schemaVersion") != 1:
		raise ValueError("Invalid syntax schema")
	words = data["words"]
	for word, features in words.items():
		if (
			not isinstance(word, str)
			or not 1 <= len(word) <= 16
			or type(features) is not int
			or features <= 0
			or features & ~(2047 | CONTENTS | POSSIBLE_CONTENTS | CONTAINER)
		):
			raise ValueError("Invalid syntax lexicon entry")
	if evidence.get("schemaVersion") != 1:
		raise ValueError("Invalid grammar evidence schema")
	if any(
		not 2 <= len(word) <= 4 or not all(_is_han(c) for c in word) or not word.endswith(("将", "將")) or not ids
		for word, ids in evidence["generalNouns"].items()
	):
		raise ValueError("Invalid nominal compound evidence")
	semantic_words = dict(words)
	for word, value in evidence["words"].items():
		if (
			not isinstance(word, str)
			or not 1 <= len(word) <= 16
			or not all(_is_han(c) for c in word)
			or type(value) is not int
			or not value & 511
			or value & ~(511 | (7 << 12))
		):
			raise ValueError("Invalid grammar evidence entry")
		# Keep established semantic/POS reviews; additional sources fill gaps.
		# Do not hide typed compounds such as 红豆+汤 / 液体+燃料 behind
		# a longer POS-only noun lacking any semantic evidence of its own.
		if value & NOUN and any(
			semantic_words.get(word[:split], 0) & NOUN and semantic_words.get(word[split:], 0) & NOUN
			for split in range(1, len(word))
		):
			continue
		words.setdefault(word, value & 511)
	for word, offsets in (evidence["repeatBlockers"] | evidence["opaqueRepeatBlockers"]).items():
		if (
			not isinstance(word, str)
			or not 2 <= len(word) <= 16
			or not isinstance(offsets, list)
			or not offsets
			or any(type(i) is not int or not 0 <= i < len(word) or word[i] != "重" for i in offsets)
		):
			raise ValueError("Invalid repeat lexical blocker")
	selection_flags = {
		"containerMeasure": CLASSIFIER | CONTAINER_MEASURE,
		"personMeasure": CLASSIFIER | PERSON_MEASURE,
		"humanNoun": NOUN | HUMAN,
		"militaryNoun": NOUN | MILITARY,
		"edgeNoun": NOUN | EDGE_NOUN,
		"speechVerb": VERB | SPEECH_VERB,
	}
	for name, entries in evidence["selection"].items():
		if name not in selection_flags:
			raise ValueError("Invalid lexical selection class")
		for word in entries:
			if word not in evidence["words"]:
				raise ValueError("Selection class lacks source headword")
			words[word] = words.get(word, 0) | selection_flags[name]
	# Only source-authored, unambiguous form pairs carry semantic features.
	# This is not character-by-character traditional conversion.
	semantic_mask = FOOD | POSSIBLE_FOOD | CONTENTS | POSSIBLE_CONTENTS | CONTAINER | HUMAN | MILITARY
	semantic_mask |= CLASSIFIER | CONTAINER_MEASURE | PERSON_MEASURE
	semantic_mask |= EDGE_NOUN | SPEECH_VERB
	for traditional, simplified in evidence["formAliases"].items():
		if not all(_is_han(c) for c in traditional + simplified):
			raise ValueError("Invalid dictionary form pair")
		features = words.get(simplified, 0)
		if features & (semantic_mask | NOUN):
			words[traditional] = words.get(traditional, 0) | features
	head_classes = dict(_HEAD_CLASSES)
	if len(grammar["classes"]) > 32 or len(grammar["frames"]) > 64:
		raise ValueError("Over-limit argument grammar")
	for number, (name, source_class) in enumerate(sorted(grammar["classes"].items()), 24):
		if not name.isascii() or not name.isidentifier() or name == "food" or source_class not in classes:
			raise ValueError("Invalid semantic class binding")
		head_classes.setdefault(name, 1 << number)
		if not 1 <= len(classes[source_class]) <= 1024:
			raise ValueError("Over-limit semantic class")
		for word in classes[source_class]:
			if not isinstance(word, str) or not 1 <= len(word) <= 16 or not all(_is_han(ch) for ch in word):
				raise ValueError("Invalid semantic noun")
			words[word] = words.get(word, 0) | NOUN | head_classes[name]
	words.update(_FUNCTIONS)
	# Small, sourced lexical sense reviews supplement incomplete source types
	# (e.g. 粉末 classified only as shape). These are noun heads, not sentences.
	for name, row in grammar.get("nounHeads", {}).items():
		feature = {"contents": CONTENTS, "container": CONTAINER}.get(name)
		if feature is None or not row.get("source") or not 1 <= len(row["words"]) <= 128:
			raise ValueError("Invalid reviewed noun class")
		for word in row["words"]:
			if not isinstance(word, str) or not 1 <= len(word) <= 16 or not all(_is_han(ch) for ch in word):
				raise ValueError("Invalid reviewed noun")
			words[word] = words.get(word, 0) | NOUN | feature
	if set(grammar.get("compoundHeads", {})) - {"food"}:
		raise ValueError("Unknown compound-head class")
	for word in grammar.get("compoundHeads", {}).get("food", ()):
		if not isinstance(word, str) or not 1 <= len(word) <= 8 or not words.get(word, 0) & NOUN:
			raise ValueError("Compound head needs an attested noun")
		words[word] |= FOOD_COMPOUND
	frames, seen = [], set()
	for row in grammar["frames"]:
		extensions = row.get("extensions", [""])
		results = row.get("results", [])
		relative_heads = row.get("relativeHeads", [])
		blocked_left = row.get("blockedLeft", [])
		blocked_right = row.get("blockedRight", [])
		if (
			not isinstance(row["id"], str)
			or row["id"] in seen
			or len(row["target"]) != 1
			or row["object"] not in head_classes
			or not row["source"]
			or not row["positive"]
			or not row["negative"]
			or not isinstance(row["prefixes"], list)
			or not 1 <= len(row["prefixes"]) <= 32
			or not all(isinstance(p, str) and len(p) <= 4 for p in row["prefixes"])
			or not isinstance(extensions, list)
			or not 1 <= len(extensions) <= 4
			or not all(isinstance(p, str) and len(p) <= 4 for p in extensions)
			or not isinstance(results, list)
			or len(results) > 16
			or not all(isinstance(p, str) and 1 <= len(p) <= 3 for p in results)
			or not isinstance(relative_heads, list)
			or len(relative_heads) > 4
			or any(name not in head_classes for name in relative_heads)
			or not isinstance(blocked_left, list)
			or len(blocked_left) > 32
			or not all(isinstance(p, str) and 1 <= len(p) <= 16 for p in blocked_left)
			or not isinstance(blocked_right, list)
			or len(blocked_right) > 32
			or not all(isinstance(p, str) and 1 <= len(p) <= 16 for p in blocked_right)
		):
			raise ValueError("Invalid argument frame")
		seen.add(row["id"])
		prefixes = set(row["prefixes"]) | {
			result + aspect for result in results for aspect in ("了", "过", "過", "着", "著")
		}
		frames.append(
			ArgumentFrame(
				row["id"],
				row["target"],
				row["reading"],
				row["object"],
				tuple(
					sorted({extension + p for extension in extensions for p in prefixes}, key=lambda p: (-len(p), p))
				),
				row["source"],
				tuple(row["positive"]),
				tuple(row["negative"]),
				tuple(relative_heads),
				tuple(blocked_left),
				tuple(blocked_right),
			)
		)
	return SyntaxLexicon(
		words,
		head_classes,
		evidence["words"],
		evidence["repeatBlockers"],
		evidence["opaqueRepeatBlockers"],
		evidence["generalNouns"],
	), tuple(frames)


def load_argument_parser(allowed, disabled=frozenset()):
	lexicon, frames = _load_data()
	if any(frame.reading not in allowed for frame in frames):
		raise ValueError("Unknown frame pronunciation")
	return ArgumentParser(lexicon, (frame for frame in frames if frame.id not in disabled))
