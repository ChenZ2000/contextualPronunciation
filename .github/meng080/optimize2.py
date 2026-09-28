from pathlib import Path
p=Path('addon/globalPlugins/contextualPronunciation/colloquial_meng.py')
s=p.read_text('utf-8')
old='_MENTION_PREFIXES: Final = _index_cues(_MENTION_RIGHT)\n_LITERARY_PREFIXES: Final = _index_cues(_LITERARY_RIGHT)'
new='''# Combine all protected right prefixes; the only exception is the temporal
# 之後/之后/之前 continuation to the literary 之 marker.
_BLOCKED_PREFIXES: Final = _index_cues(
	(*_MENTION_RIGHT, *_LITERARY_RIGHT, "了解", "了然", "了悟", "过敏", "過敏", "过失", "過失", "着作", "著作")
)'''
assert old in s
s=s.replace(old,new)
a=s.index('def _blocked(left: str, right: str) -> bool:')
b=s.index('\n\ndef _base',a)
s=s[:a]+'''def _blocked(left: str, right: str) -> bool:
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
'''+s[b:]
a='\t"""Classify a window already checked by _blocked in classify."""\n'
b='''	# End-delimited 越V越懵 cannot match any of the lexical/complement cases
	# below. Dispatch this productive comparative without scanning their cues.
	if left.endswith("越") and (not right or not right[0].isalnum()):
		previous = left.rfind("越", 0, len(left) - 1)
		between = left[previous + 1 : -1] if previous >= 0 else ""
		if between and all(_han(ch) for ch in between):
			return "comparative-state"
'''
assert a in s
s=s.replace(a,a+b)
p.write_text(s,'utf-8')
p=Path('tests/test_meng_contexts.py')
s=p.read_text('utf-8')
anchor='\n\tdef test_original_offsets_and_abstention_in_annotation_api(self):'
addition='''
	def test_combined_protection_index_matches_independent_linear_reference(self):
		matcher = load("colloquial_meng")
		false_aspect = ("了解", "了然", "了悟", "过敏", "過敏", "过失", "過失", "着作", "著作")
		for left in ("", *matcher._MENTION_LEFT, "A", "_", "，", "你好"):
			for right in ("", *matcher._MENTION_RIGHT, *matcher._LITERARY_RIGHT, *false_aspect, "之后", "之後", "之前", "😀", "懵"):
				for padding in ("", "甲", "甲乙"):
					before, after = padding + left, right + padding
					expected = bool(
						before and before[-1].isascii() and (before[-1].isalnum() or before[-1] == "_")
						or before.endswith(matcher._MENTION_LEFT)
						or after.startswith(matcher._MENTION_RIGHT)
						or after.startswith(matcher._LITERARY_RIGHT) and not after.startswith(("之后", "之後", "之前"))
						or after.startswith(false_aspect)
					)
					with self.subTest(left=before, right=after):
						self.assertEqual(expected, matcher._blocked(before, after))

	def test_comparative_fast_path_does_not_shadow_other_grammatical_evidence(self):
		matcher = load("colloquial_meng")
		for suffix, expected in (
			("", "comparative-state"), ("，", "comparative-state"), ("😀", "comparative-state"),
			("B", "colloquial-lexeme"), ("b", "colloquial-lexeme"), ("Ｂ", "colloquial-lexeme"),
			("ing", "colloquial-progressive"), ("1天", "state-duration"),
			("了", "state-predicate"), ("得说不出话", "state-complement"),
		):
			with self.subTest(suffix=suffix):
				self.assertEqual(expected, matcher.classify("越想越懵" + suffix, 3))
'''
assert anchor in s
p.write_text(s.replace(anchor,'\n'+addition+anchor),'utf-8')
p=Path('docs/COLLOQUIAL_MENG.md')
s=p.read_text('utf-8')
s+='\nThe hot path also combines compatible preservation-prefix checks and dispatches end-delimited 越V越懵 directly. Independent linear-reference tests protect the temporal 之后/之後/之前 exception, and precedence tests keep B/ing/duration/complement evidence intact. No benchmark case, sample count or threshold is reduced.\n'
p.write_text(s,'utf-8')
