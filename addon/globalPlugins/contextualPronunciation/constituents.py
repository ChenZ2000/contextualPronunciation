"""Per-analysis memoized constituent chart; all offsets refer to original text.

The grammar retains dictionary POS alternatives. It recognizes NP, adjective
modifiers and relative predicates; no punctuation/unknown token is skipped to
reach a desired head. Chart state and nesting budgets bound pathological input.
"""

from __future__ import annotations

from .predicates import _MODALS, predicate_spine


class ConstituentParser:
	def __init__(self, tokens, grammar, context=None):
		self.tokens = tokens
		self.g = grammar
		self.chart = {}
		self.modifiers = {}
		self.states = 0
		self.work = 0
		self.context = context
		self.exhausted = context is not None and not context.consume(len(tokens))

	def _budget(self, depth, cost):
		self.states += 1
		self.work += cost
		if (
			self.exhausted
			or depth > self.g.MAX_DEPTH
			or self.states > self.g.MAX_CHART_STATES
			or self.work > self.g.MAX_CHART_WORK
			or self.context is not None
			and not self.context.consume(cost)
		):
			self.exhausted = True
			return False
		return True

	def _plain(self, start, end, *, prefix=False):
		g, tokens = self.g, self.tokens
		quantity = self._quantity(start, end)
		if quantity is not None:
			qend, measure = quantity
			ellipsis = self._ellipsis(start, qend, measure, end, prefix)
			if ellipsis is not None:
				return ellipsis
			np = self._plain(qend, end, prefix=prefix)
			return self._quantified(start, measure, np) if np is not None else None
		head, deps = None, []
		for i in range(start, end):
			t = tokens[i]
			f = t.features
			if (
				prefix
				and head is not None
				and t.text in _MODALS
				and predicate_spine(
					tokens,
					i,
					tokens[start].start,
					t.start,
					self.context,
					g,
				)
				is not None
			):
				end = i
				break
			if f & (g.STOP | g.DE | g.UNKNOWN | g.COORD | g.ADVERBIAL | g.COMPLEMENT):
				if prefix and f & (g.STOP | g.COORD):
					end = i
					break
				return None
			if head is None and f & g.CLASSIFIER and i > start and tokens[i - 1].features & (g.NUMBER | g.DET):
				continue
			if f & (g.NOUN | g.PRON):
				if head is not None:
					deps.append(g.Dependency("compound", t.start, tokens[head].start, tokens[head].end))
				head = i
			elif head is None and f & (g.ADJ | g.ADV | g.DET | g.NUMBER | g.CLASSIFIER):
				continue
			else:
				if prefix and f & (g.VERB | g.ADJ | g.ADV | g.PREP):
					end = i
					break
				return None
		if head is None:
			return None
		features = tokens[head].features
		if deps and features & g.FOOD_COMPOUND:
			features |= g.FOOD
		front = head
		if tokens[head].text in g._LOCALIZERS:
			front = next((i for i in range(start, head) if tokens[i].features & g.NOUN), head)
		return g.NounPhrase(end, head, features, front, tuple(deps))

	def _quantity(self, start, end):
		"""Det? Num? Adj? Clf NP; a classifier must be selected by Det/Num."""
		g, tokens = self.g, self.tokens
		i = start
		while i < end and tokens[i].features & (g.DET | g.NUMBER):
			i += 1
		if i == start:
			return None
		while i < end and tokens[i].features & g.ADJ and not tokens[i].features & g.CLASSIFIER:
			i += 1
		if i < end and tokens[i].features & g.CLASSIFIER:
			return i + 1, i
		return None

	def _ellipsis(self, start, qend, measure, end, prefix=False):
		"""Num Clf [contents omitted], only at a complete NP boundary.

		The classifier is the surface head. No absent noun or source offset is
		invented; its container sense licenses contents, not necessarily food.
		"""
		g, tokens = self.g, self.tokens
		if not tokens[measure].features & g.CONTAINER_MEASURE:
			return None
		if qend != end:
			f = tokens[qend].features
			if not prefix or f & (g.NOUN | g.PRON | g.ADJ | g.DE | g.UNKNOWN | g.NUMBER | g.CLASSIFIER):
				return None
			if not f & (g.VERB | g.ADV | g.PREP | g.STOP | g.COORD):
				return None
		head = tokens[measure]
		np = g.NounPhrase(
			qend, measure, g.NOUN | g.CONTENTS, measure, (g.Dependency("ellipsis", head.start, head.start, head.end),)
		)
		return self._quantified(start, measure, np)

	def _quantified(self, start, measure, np):
		g, tokens = self.g, self.tokens
		features = np.features
		if tokens[measure].features & g.CONTAINER_MEASURE:
			if features & g.POSSIBLE_FOOD:
				features |= g.FOOD
			if features & g.POSSIBLE_CONTENTS:
				features |= g.CONTENTS
		head = tokens[np.head].start
		deps = (
			g.Dependency("nummod", head, tokens[start].start, tokens[measure].start),
			g.Dependency("clf", head, tokens[measure].start, tokens[measure].end),
			*np.dependencies,
		)
		return g.NounPhrase(np.end, np.head, features, np.front_head, deps)

	def _modifier(self, start, end, depth):
		key = start, end, depth
		if key in self.modifiers:
			return self.modifiers[key]
		self.modifiers[key] = None
		if start >= end or not self._budget(depth, end - start):
			return None
		g, tokens = self.g, self.tokens
		items = tokens[start:end]
		if any(t.features & g.STOP for t in items):
			return None
		# A conjunction is legal inside an explicit modifier, with a complete
		# constituent on each side. It cannot connect two unrelated objects.
		coord = [i for i in range(start, end) if tokens[i].features & g.COORD]
		if coord and not any(t.features & g.DE for t in items):
			bounds = [start, *(i + 1 for i in coord)]
			ends = [*coord, end]
			# 又细又长 and 又香又甜: the initial 又 is a correlative marker.
			if tokens[coord[0]].text == "又" and all(
				t.features & (g.DET | g.NUMBER | g.CLASSIFIER) for t in tokens[start : coord[0]]
			):
				bounds, ends = bounds[1:], ends[1:]
			parts = [self._modifier(a, b, depth + 1) for a, b in zip(bounds, ends, strict=True)]
			if not parts or any(p is None for p in parts):
				return None
			relation = "acl" if any(p[0] == "acl" for p in parts) else "amod"
			deps = tuple(d for p in parts for d in p[1])
			for a, b in zip(bounds[1:], ends[1:], strict=True):
				deps += (g.Dependency("conj", tokens[bounds[0]].start, tokens[a].start, tokens[b - 1].end),)
			result = relation, deps
		elif any(t.features & g.DE for t in items):
			# A relative predicate may contain its own fully parsed nominal
			# argument: 住在 [那条安静的街道] 的 ... . Prefer this attachment
			# over flattening every 的 into successive unrelated owners.
			owner = self._np(start, end, depth + 1)
			result = ("nmod", owner.dependencies) if owner is not None else None
			for v in range(start, end) if result is None else ():
				if tokens[v].features & g.VERB and not tokens[v].features & (g.NOUN | g.ADJ):
					if any(t.features & (g.DE | g.UNKNOWN) for t in tokens[start:v]):
						continue
					obj = self._np(v + 1, end, depth + 1)
					if obj is not None:
						result = (
							"acl",
							(
								*obj.dependencies,
								g.Dependency("obj", tokens[v].start, tokens[v + 1].start, tokens[end - 1].end),
							),
						)
						break
		else:
			# Degree and aspect alone are not a modifier. Unknown names are
			# allowed only as a bounded possessor/subject before an explicit 的.
			verbs = [
				i
				for i in range(start, end)
				if tokens[i].features & g.VERB and not tokens[i].features & (g.NOUN | g.ADJ)
			]
			unknown = sum(len(t.text) for t in items if t.features & g.UNKNOWN)
			if unknown > g.MAX_OWNER_CHARS:
				return None
			if verbs:
				if any(t.features & g.UNKNOWN for t in tokens[verbs[0] + 1 : end]):
					return None
				if (
					any(t.features & (g.DET | g.NUMBER) for t in tokens[verbs[-1] + 1 : end])
					and self._plain(verbs[-1] + 1, end) is None
				):
					return None  # unfinished nominal argument before an embedded 的
				result = "acl", ()
			elif all(
				t.features & (g.ADJ | g.ADV | g.COMPLEMENT | g.DET | g.NUMBER | g.CLASSIFIER) for t in items
			) and any(t.features & g.ADJ for t in items):
				result = "amod", ()
			elif all(
				t.features & (g.NOUN | g.PRON | g.UNKNOWN | g.ADJ | g.ADV | g.DET | g.NUMBER | g.CLASSIFIER)
				for t in items
			):
				if not any(t.features & (g.NOUN | g.PRON | g.UNKNOWN) for t in items):
					return None
				result = "nmod", ()
			else:
				result = None
		self.modifiers[key] = result
		return result

	def _np(self, start, end, depth):
		key = start, end, depth
		if key in self.chart:
			return self.chart[key]
		self.chart[key] = None
		if start >= end or not self._budget(depth, end - start):
			return None
		g, tokens = self.g, self.tokens
		quantity = self._quantity(start, end)
		if quantity is not None:
			qend, measure = quantity
			ellipsis = self._ellipsis(start, qend, measure, end)
			if ellipsis is not None:
				self.chart[key] = ellipsis
				return ellipsis
			right = self._np(qend, end, depth + 1)
			if right is not None:
				result = self._quantified(start, measure, right)
				self.chart[key] = result
				return result
		de_positions = [i for i in range(start + 1, end - 1) if tokens[i].features == g.DE]
		if not de_positions:
			result = self._plain(start, end)
		else:
			result = None
			# Prefer the widest *validated* modifier. A clause containing an
			# embedded NP is resolved before a shorter, incomplete clause.
			for de in reversed(de_positions):
				modifier = self._modifier(start, de, depth + 1)
				if modifier is None:
					continue
				right = self._np(de + 1, end, depth + 1)
				if right is None:
					continue
				relation, nested = modifier
				dep = g.Dependency(relation, tokens[right.front_head].start, tokens[start].start, tokens[de].end)
				front = right.front_head
				if relation == "nmod":
					front = next(
						(i for i in range(de - 1, start - 1, -1) if tokens[i].features & (g.NOUN | g.PRON | g.UNKNOWN)),
						front,
					)
				result = g.NounPhrase(right.end, right.head, right.features, front, (*nested, dep, *right.dependencies))
				break
		self.chart[key] = result
		return result

	def parse(self, start=0, depth=0):
		g, tokens = self.g, self.tokens
		if self.exhausted:
			return None
		if not any(t.features & g.DE for t in tokens[start:]):
			return self._plain(start, len(tokens), prefix=True)
		# Only complete constituent boundaries can end an argument. Never
		# truncate an unknown suffix or a nominal chain to recover a desired type.
		ends = []
		for end in range(start + 1, len(tokens) + 1):
			if not tokens[end - 1].features & (g.NOUN | g.PRON):
				continue
			if end == len(tokens):
				ends.append(end)
			else:
				f = tokens[end].features
				if (
					tokens[end].text in _MODALS
					or not f & (g.DE | g.UNKNOWN | g.NOUN | g.PRON)
					and f & (g.STOP | g.VERB | g.ADJ | g.ADV | g.PREP | g.COORD)
				):
					ends.append(end)
		for end in reversed(ends):
			result = self._np(start, end, depth)
			if self.exhausted:
				return None
			if result is not None:
				if (
					tokens[result.head].text in _MODALS
					and predicate_spine(
						tokens,
						result.head,
						tokens[start].start,
						tokens[result.head].start,
						self.context,
						g,
					)
					is not None
				):
					continue
				if any(d.relation == "ellipsis" for d in result.dependencies) and any(
					t.features == g.DE for t in tokens[end:]
				):
					continue  # Do not truncate an unparsed relative after Num Clf.
				return result
		return None
