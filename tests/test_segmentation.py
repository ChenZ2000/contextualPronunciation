"""Independent lattice arithmetic and linguistic counterexamples; no CPP labels."""

from __future__ import annotations

import itertools
import math
import random
import unittest
from unittest import mock

from tests.core_loader import PLUGIN_PATH, load
from tools import build_segmentation_data
from tools.import_cedict import parse_cedict

lexicon = load("lexicon")
segmentation = load("segmentation")


def small_lexicon(words, counts):
	data = {
		"schemaVersion": 2,
		"maxWordLength": 32,
		"defaults": {},
		"renderings": {},
		"speechTargets": [],
		"reservedTargets": "",
		"allowedReadings": [],
		"words": words,
	}
	return lexicon.PhraseLexicon(
		data, segmentation={"schemaVersion": 1, "frequencies": counts, "totalFrequency": 1000000}
	)


class SegmentationTests(unittest.TestCase):
	def test_pinned_frequency_compiler_reproduces_offline(self):
		self.assertEqual(
			build_segmentation_data.generate(), (PLUGIN_PATH / "data/segmentation_zh_CN.json").read_bytes()
		)

	def test_confident_disagreement_can_add_a_whole_word_not_a_single_guess(self):
		words = {"甲乙": "jia3 yi3", "乙丙": "yi3 bing3"}
		for order in (list(words), list(reversed(words))):
			model = small_lexicon(dict((w, words[w]) for w in order), {"甲乙": 10000, "乙丙": 2})
			spans = model.annotate("😀甲乙丙！")
			self.assertEqual([(1, 3, "甲乙")], [(s.start, s.end, s.text) for s in spans])
			self.assertIn("unigram-margin", spans[0].source)

	def test_tied_small_margin_unknown_and_blocked_candidates_abstain(self):
		for words, counts in (
			({"甲乙": "jia3 yi3", "乙丙": "yi3 bing3"}, {"甲乙": 100, "乙丙": 100}),
			({"甲乙": "jia3 yi3", "乙丙": "yi3 bing3"}, {"甲乙": 100, "乙丙": 10}),
			({"甲乙": "jia3 yi3", "乙丙": "yi3 bing3"}, {}),
			({"甲乙": "jia3 yi3", "乙丙": ""}, {"甲乙": 100000, "乙丙": 1}),
		):
			self.assertEqual((), small_lexicon(words, counts).annotate("甲乙丙"))

	def test_agreed_words_are_not_resegmented_even_if_a_split_has_higher_frequency(self):
		model = small_lexicon({"甲乙": "jia3 yi3", "甲乙丙": ""}, {"甲乙": 99999, "甲乙丙": 1})
		self.assertEqual((), model.annotate("甲乙丙"))

	def test_long_disagreement_is_not_truncated_or_guessed(self):
		model = small_lexicon({"甲乙": "jia3 yi3", "乙甲": "yi3 jia3"}, {"甲乙": 10000, "乙甲": 1})
		with mock.patch.object(model._adjudicator, "_island", side_effect=AssertionError("over-budget island")):
			self.assertEqual((), model.annotate("甲乙" * 100 + "甲"))

	def test_max_marginal_matches_exhaustive_enumeration_not_only_runner_up(self):
		text = "甲乙丙丁戊"
		words = {text[start:end]: "p " * (end - start) for start in range(5) for end in range(start + 2, 6)}
		for seed in range(25):
			rng = random.Random(seed)
			counts = {word: rng.randint(1, 500000) for word in (*words, *text)}
			model = small_lexicon(words, counts)
			candidates = [(start, end) for start in range(5) for end in range(start + 2, 6)]
			paths = []
			for cuts in itertools.product((False, True), repeat=4):
				boundaries = [0, *(i + 1 for i, cut in enumerate(cuts) if cut), 5]
				edges = set(zip(boundaries, boundaries[1:], strict=False))
				score = sum(math.log(counts[text[a:b]] / 1000000) for a, b in edges)
				paths.append((edges, score))
			expected = {
				edge
				for edge in candidates
				if max(s for e, s in paths if edge in e) - max(s for e, s in paths if edge not in e)
				>= segmentation.MIN_MARGIN
			}
			self.assertEqual(expected, model._adjudicator.choose(text, candidates, model._words, model._forward), seed)

	def test_source_authored_traditional_forms_and_collisions_are_not_simplification(self):
		rows = ["後發 后发 [hou4 fa1] /later/", "后髮 后发 [hou4 fa4] /hair/", "樂觀 乐观 [le4 guan1] /optimistic/"]
		words, _, _ = parse_cedict(rows)
		self.assertEqual({("hou4", "fa1")}, words["後發"])
		self.assertEqual({("hou4", "fa4")}, words["后髮"])
		self.assertEqual(2, len(words["后发"]))
		self.assertEqual(words, parse_cedict(reversed(rows))[0])

	def test_traditional_independent_readings_and_original_offsets(self):
		rules = load("rules").load_default_rules()
		for text, position, reading in (("單于", 0, "chan2"), ("龜裂", 0, "jun1"), ("軀殼", 1, "qiao4")):
			decision = rules.resolve("😀" + text)[position + 1]
			self.assertEqual(reading, decision.reading_id)
			self.assertEqual(rules.renderings[reading], rules.transform(text)[position])
		self.assertIsNone(rules.resolve("朝陽").get(0))

	def test_model_data_validation_rejects_nonfinite_or_malformed_weights(self):
		for counts in ({"甲乙": -1}, {"甲乙": float("nan")}, {"甲乙": True}, {"": 1}, {"甲": 1000001}):
			with self.assertRaises(ValueError):
				small_lexicon({}, counts)

	def test_speech_projection_keeps_weighted_decisions(self):
		rules = load("rules").load_default_rules()
		for text in ("測量尺寸後重新開始", "这个音乐观众很好", "😀甲乙丙", "银行行长", "海水淹没了小桥"):
			full = rules.resolve(text)
			self.assertEqual({i: d for i, d in full.items() if d.speech}, rules.resolve(text, speech_only=True))
