"""Apply the measured bounded-dispatch optimization to the formatted 0.8.0 candidate."""
from pathlib import Path


def edit(path, old, new):
    p = Path(path)
    text = p.read_text('utf-8')
    assert text.count(old) == 1, (path, old[:80], text.count(old))
    p.write_text(text.replace(old, new), 'utf-8')

p = 'addon/globalPlugins/contextualPronunciation/colloquial_meng.py'
edit(p, '\t"的含義",\n', '\t"的含義",\n' + ''.join('\t' + repr(x).replace("'", '"') + ',\n' for x in ('的字形', '的字义', '的字義', '的解释', '的解釋', '的释义', '的釋義', '的规范读音', '的規範讀音', '的笔顺', '的筆順', '的词性', '的詞性', '的注音', '的声母', '的聲母', '的韵母', '的韻母', '的音节', '的音節', '读几声', '讀幾聲', '先生', '女士', '氏', '姓')))
edit(p, '\n\ndef _han(character: str) -> bool:', '''

def _index_cues(cues: tuple[str, ...], *, suffix: bool = False) -> dict[str, tuple[str, ...]]:
	"""First/last-character dispatch avoids scanning unrelated fixed cues."""
	buckets: dict[str, list[str]] = {}
	for cue in cues:
		buckets.setdefault(cue[-1] if suffix else cue[0], []).append(cue)
	return {key: tuple(value) for key, value in buckets.items()}


_MENTION_PREFIXES: Final = _index_cues(_MENTION_RIGHT)
_LITERARY_PREFIXES: Final = _index_cues(_LITERARY_RIGHT)
_MENTION_SUFFIXES: Final = _index_cues(_MENTION_LEFT, suffix=True)
_DEGREE_SUFFIXES: Final = _index_cues(_DEGREE_LEFT, suffix=True)
_SUBJECT_SUFFIXES: Final = _index_cues(_SUBJECTS, suffix=True)
_RESULT_SUFFIXES: Final = _index_cues(_RESULT_VERBS, suffix=True)


def _index_reiterations() -> tuple[dict[str, tuple[tuple[str, int], ...]], dict[str, tuple[tuple[str, int], ...]]]:
	"""Compile immutable candidate tuples once, not in the speech hot path."""
	starts: dict[str, list[tuple[str, int]]] = {}
	ends: dict[str, list[tuple[str, int]]] = {}
	for pattern in (
		"懵不懵", "懵没懵", "懵沒懵", "懵归懵", "懵歸懵", "懵是懵",
		"懵来懵去", "懵來懵去", "懵上加懵", "懵了又懵",
	):
		pivot = pattern.rfind("懵")
		starts.setdefault(pattern[1], []).append((pattern, 0))
		ends.setdefault(pattern[pivot - 1], []).append((pattern, pivot))
	return (
		{key: tuple(value) for key, value in starts.items()},
		{key: tuple(value) for key, value in ends.items()},
	)


_REITERATION_STARTS, _REITERATION_ENDS = _index_reiterations()


def _han(character: str) -> bool:''')
for old, new in (
    ('left.endswith(_MENTION_LEFT)', 'left.endswith(_MENTION_SUFFIXES.get(left[-1:], ()))'),
    ('right.startswith(_MENTION_RIGHT)', 'right.startswith(_MENTION_PREFIXES.get(right[:1], ()))'),
    ('right.startswith(_LITERARY_RIGHT)', 'right.startswith(_LITERARY_PREFIXES.get(right[:1], ()))'),
    ('left.endswith(_DEGREE_LEFT)', 'left.endswith(_DEGREE_SUFFIXES.get(left[-1:], ()))'),
    ('left.endswith(_RESULT_VERBS)', 'left.endswith(_RESULT_SUFFIXES.get(left[-1:], ()))'),
    ('left[:-1].endswith(_RESULT_VERBS)', 'left[:-1].endswith(_RESULT_SUFFIXES.get(left[-2:-1], ()))'),
    ('stem.endswith(_SUBJECTS)', 'stem.endswith(_SUBJECT_SUFFIXES.get(stem[-1:], ()))'),
):
    edit(p, old, new)
edit(p, 'def _base(left: str, right: str) -> str | None:\n\tif _blocked(left, right):\n\t\treturn None', 'def _base(left: str, right: str) -> str | None:\n\t"""Classify a window already checked by _blocked in classify."""')
edit(p, '''	for pattern in (
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
		for pivot in (0, pattern.rfind("懵")):''', '''	# Index the fixed constructions by the immediately adjacent morpheme.
	# Impossible candidates need no string match (or per-character rfind).
	blocked_reiteration = False
	for candidates in (
		_REITERATION_STARTS.get(right[:1], ()),
		_REITERATION_ENDS.get(left[-1:], ()),
	):
		for pattern, pivot in candidates:''')
edit(p, '\t\t\t\t\treturn "reiteration"\n\tif right.startswith("懵")', '''					return "reiteration"
				blocked_reiteration = True
	if blocked_reiteration:
		# A complete construction named as text must not fall through to a
		# weaker 看/问/我 cue and correct only its first occurrence.
		return None
	if right.startswith("懵")''')

p = Path('tests/meng_cases.py')
p.write_text(p.read_text('utf-8') + '''

def generated_mentions():
	"""Character/phrase descriptions that otherwise resemble weak predicates."""
	for prefix in ("请问", "请看", "这是我输入", "老师提问"):
		for phrase in ("懵", "懵不懵", "懵归懵", "懵懵"):
			for tail in ("的字形", "的解释", "的规范读音", "的笔顺", "的词性", "的注音"):
				yield prefix + phrase + tail
	for prefix in ("请问", "请看", "大家都问"):
		for title in ("先生", "女士", "氏"):
			yield prefix + "懵" + title
''', 'utf-8')
for p in ('tests/test_meng_contexts.py', 'tools/evaluate_colloquial_meng.py'):
    edit(p, 'MIXED, NEGATIVE, POSITIVE, generated_negatives, generated_positives', 'MIXED, NEGATIVE, POSITIVE, generated_mentions, generated_negatives, generated_positives')
edit('tests/test_meng_contexts.py', ' + list(generated_negatives())', ' + list(generated_negatives()) + list(generated_mentions())')
edit('tools/evaluate_colloquial_meng.py', '\t\t*[(s, s) for s in generated_negatives()],', '\t\t*[(s, s) for s in generated_negatives()],\n\t\t*[(s, s) for s in generated_mentions()],')
edit('tests/test_meng_contexts.py', '\n\tdef test_original_offsets_and_abstention_in_annotation_api(self):', '''
	def test_indexed_cues_preserve_linear_prefix_and_suffix_matching(self):
		matcher = load("colloquial_meng")
		for cues, suffix in (
			(matcher._MENTION_RIGHT, False), (matcher._LITERARY_RIGHT, False),
			(matcher._MENTION_LEFT, True), (matcher._DEGREE_LEFT, True),
			(matcher._SUBJECTS, True), (matcher._RESULT_VERBS, True),
		):
			buckets = matcher._index_cues(cues, suffix=suffix)
			for cue in (*cues, "", "😀", "\\n", "非线索"):
				for outside in ("", "甲", "\\n", "😀"):
					text = outside + cue if suffix else cue + outside
					with self.subTest(cue=cue, suffix=suffix, text=text):
						if suffix:
							self.assertEqual(text.endswith(cues), text.endswith(buckets.get(text[-1:], ())))
						else:
							self.assertEqual(text.startswith(cues), text.startswith(buckets.get(text[:1], ())))

	def test_original_offsets_and_abstention_in_annotation_api(self):''')
p = 'docs/COLLOQUIAL_MENG.md'
edit(p, '| [AllSet Learning: result complements]', '| [Universal Dependencies: Chinese resultative compounds](https://universaldependencies.org/zh/dep/compound-vv.html) | Resulting states can be adjective complements; potential 得/不 can intervene. / 动结式的结果成分可以是形容词，得／不用于可能式。 | Structural support only; it does not assign the tone of 懵. |\n| [AllSet Learning: result complements]')
edit(p, 'examines at most 24 code points on either side.', 'uses windows of at most 24 code points on either side of an occurrence or a matched reiterative span (at most five code points).')
edit(p, 'It uses fixed string inventories, bounded numeral/modifier loops and one-peer checks.', 'It uses fixed string inventories, bounded numeral/modifier loops and one-peer checks. Fixed cues and reiterations are indexed by their first/last adjacent character at import time; unrelated candidates are not scanned at every target. Protection checks are reused only within the same classification, with no retained utterance cache.')
p = Path(p)
p.write_text(p.read_text('utf-8') + '\nPerformance recovery does not relax either budget: adjacent-character indexes replace repeated full-inventory scans. Character-description tails such as “请问懵的字形” and complete reiterations named as text (“请问懵不懵的读音”) are preservation cases, not weak resultative predicates.\n', 'utf-8')
