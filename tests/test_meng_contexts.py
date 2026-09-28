"""Positive grammatical evidence, counterexamples, and boundedness regressions."""

from __future__ import annotations

import unittest

from tests.core_loader import load
from tests.meng_cases import MIXED, NEGATIVE, POSITIVE, generated_mentions, generated_negatives, generated_positives


class MengContextTests(unittest.TestCase):
	@classmethod
	def setUpClass(cls):
		cls.modes = {extended: load("rules").load_default_rules(extended=extended) for extended in (False, True)}

	def test_confirmed_and_productive_contexts_in_all_modes(self):
		texts = [text for group in POSITIVE.values() for text in group] + list(generated_positives())
		for extended, rules in self.modes.items():
			for strict in (False, True):
				for text in texts:
					with self.subTest(extended=extended, strict=strict, text=text):
						self.assertEqual(
							text.replace("懵", "擝"), rules.transform(text, strict=strict, targets=frozenset("懵"))
						)
						decisions = rules.resolve(text, strict=strict)
						for index, character in enumerate(text):
							if character == "懵":
								self.assertEqual("meng1", decisions[index].reading_id)

	def test_isolated_non_colloquial_and_ambiguous_contexts_are_preserved(self):
		texts = (
			[text for group in NEGATIVE.values() for text in group]
			+ list(generated_negatives())
			+ list(generated_mentions())
		)
		for extended, rules in self.modes.items():
			for strict in (False, True):
				for text in texts:
					with self.subTest(extended=extended, strict=strict, text=text):
						self.assertEqual(text, rules.transform(text, strict=strict, targets=frozenset("懵")))
						for index, item in rules.resolve(text, strict=strict).items():
							if text[index] == "懵":
								self.assertNotEqual("meng1", item.reading_id)

	def test_mixed_text_keeps_each_decision_local(self):
		for rules in self.modes.values():
			for strict in (False, True):
				for source, expected in MIXED:
					with self.subTest(source=source, strict=strict):
						self.assertEqual(expected, rules.transform(source, strict=strict, targets=frozenset("懵")))
						full = rules.resolve(source, strict=strict)
						self.assertEqual(
							{i: d for i, d in full.items() if d.speech},
							rules.resolve(source, strict=strict, speech_only=True),
						)

	def test_user_overrides_and_disable_preserve_precedence(self):
		for extended in (False, True):
			for entries, templates, source, expected in (
				("一脸懵|懵|keep", "", "一脸懵，懵了", "一脸懵，擝了"),
				("懵的|懵|meng1", "", "懵的", "擝的"),
				("", "甲[懵:meng1]", "甲懵", "甲擝"),
				("", "一脸[懵:keep]", "一脸懵", "一脸懵"),
				("懵的|懵|keep", "[懵:meng1]的", "懵的", "懵的"),
			):
				rules = load("rules").load_default_rules(
					extended=extended, custom_entries=entries, custom_templates=templates
				)
				self.assertEqual(expected, rules.transform(source), (entries, templates))
			rules = load("rules").load_default_rules(extended=extended, disabled_rules="colloquialMeng")
			for source in ("懵", "一脸懵，懵了", "看懵了，懵懂", "懵懵的", "懵不懵"):
				self.assertEqual(source, rules.transform(source, targets=frozenset("懵")))

	def test_spelling_and_speech_items_do_not_borrow_context(self):
		from tests.test_pipeline import CharacterModeCommand

		pipeline = load("pipeline")
		for rules in self.modes.values():
			normalizer = pipeline.SpeechSequenceNormalizer(
				rules=rules, character_mode_command_type=CharacterModeCommand
			)
			marker, on, off = object(), CharacterModeCommand(True), CharacterModeCommand(False)
			for sequence in (["懵"], ["一脸", "懵"], ["懵", "了"], ["我", marker, "懵"], ["懵", "懂"]):
				self.assertEqual(sequence, normalizer.normalize(sequence, options=pipeline.RuntimeOptions()))
			self.assertEqual(
				["一脸擝", marker, on, "懵了", off, "懵", "擝了"],
				normalizer.normalize(
					["一脸懵", marker, on, "懵了", off, "懵", "懵了"], options=pipeline.RuntimeOptions()
				),
			)

	def test_indexed_cues_preserve_linear_prefix_and_suffix_matching(self):
		matcher = load("colloquial_meng")
		for cues, suffix in (
			(matcher._MENTION_RIGHT, False),
			(matcher._LITERARY_RIGHT, False),
			(matcher._MENTION_LEFT, True),
			(matcher._DEGREE_LEFT, True),
			(matcher._SUBJECTS, True),
			(matcher._RESULT_VERBS, True),
		):
			buckets = matcher._index_cues(cues, suffix=suffix)
			for cue in (*cues, "", "😀", "\n", "非线索"):
				for outside in ("", "甲", "\n", "😀"):
					text = outside + cue if suffix else cue + outside
					with self.subTest(cue=cue, suffix=suffix, text=text):
						if suffix:
							self.assertEqual(text.endswith(cues), text.endswith(buckets.get(text[-1:], ())))
						else:
							self.assertEqual(text.startswith(cues), text.startswith(buckets.get(text[:1], ())))

	def test_combined_protection_index_matches_independent_linear_reference(self):
		matcher = load("colloquial_meng")
		false_aspect = ("了解", "了然", "了悟", "过敏", "過敏", "过失", "過失", "着作", "著作")
		for left in ("", *matcher._MENTION_LEFT, "A", "_", "，", "你好"):
			for right in (
				"",
				*matcher._MENTION_RIGHT,
				*matcher._LITERARY_RIGHT,
				*false_aspect,
				"之后",
				"之後",
				"之前",
				"😀",
				"懵",
			):
				for padding in ("", "甲", "甲乙"):
					before, after = padding + left, right + padding
					expected = bool(
						before
						and before[-1].isascii()
						and (before[-1].isalnum() or before[-1] == "_")
						or before.endswith(matcher._MENTION_LEFT)
						or after.startswith(matcher._MENTION_RIGHT)
						or after.startswith(matcher._LITERARY_RIGHT)
						and not after.startswith(("之后", "之後", "之前"))
						or after.startswith(false_aspect)
					)
					with self.subTest(left=before, right=after):
						self.assertEqual(expected, matcher._blocked(before, after))

	def test_comparative_fast_path_does_not_shadow_other_grammatical_evidence(self):
		matcher = load("colloquial_meng")
		for suffix, expected in (
			("", "comparative-state"),
			("，", "comparative-state"),
			("😀", "comparative-state"),
			("B", "colloquial-lexeme"),
			("b", "colloquial-lexeme"),
			("Ｂ", "colloquial-lexeme"),
			("ing", "colloquial-progressive"),
			("1天", "state-duration"),
			("了", "state-predicate"),
			("得说不出话", "state-complement"),
		):
			with self.subTest(suffix=suffix):
				self.assertEqual(expected, matcher.classify("越想越懵" + suffix, 3))

	def test_original_offsets_and_abstention_in_annotation_api(self):
		source = "😀懵，一脸懵，懵懂，懵了"
		for rules in self.modes.values():
			annotations = {a.start: a for a in load("braille_readings").annotate(source, rules)}
			for i, character in enumerate(source):
				if character != "懵":
					continue
				if i in (5, 10):
					self.assertEqual(
						("懵", "meng1", i + 1, i + 2),
						(
							annotations[i].character,
							annotations[i].reading,
							annotations[i].utf16_start,
							annotations[i].utf16_end,
						),
					)
				else:
					self.assertNotIn(i, annotations)
			self.assertEqual("😀懵，一脸懵，懵懂，懵了", source)

	def test_matcher_never_slices_unbounded_context_or_propagates_a_run(self):
		matcher = load("colloquial_meng")

		class BoundedText(str):
			def __getitem__(self, key):
				if isinstance(key, slice):
					start, stop, step = key.indices(len(self))
					if step != 1 or stop - start > matcher.WINDOW:
						raise AssertionError(f"Unbounded slice: {key}")
				return super().__getitem__(key)

		for middle, positive in (("一脸懵", True), ("懵得想不起问题", True), ("懵归懵", True), ("\n懵\n", False)):
			text = BoundedText("甲" * 100_000 + middle + "乙" * 100_000)
			for i in range(100_000, 100_000 + len(middle)):
				if text[i] == "懵":
					self.assertEqual(positive, matcher.classify(text, i) is not None)
		for rules in self.modes.values():
			text = "懵" * 8192
			self.assertEqual(text, rules.transform(text))
		self.assertIsNone(matcher.classify("越" + "想" * 32 + "越懵", 34))


class MengPerformanceReportTests(unittest.TestCase):
	def test_latency_report_cannot_silently_omit_cases_or_exceed_budgets(self):
		import copy

		from tools.benchmark_colloquial_meng import SCENARIOS, validate

		report = {
			"modes": {
				mode: {
					name: {"medianUs": 1.0, "samples": 100, "codepoints": len(text)} for name, text in SCENARIOS.items()
				}
				for mode in ("default", "extended")
			}
		}
		validate(report)
		for name, value in (
			("bare", 201),
			("bare8k", 30001),
			("bare", float("nan")),
			("bare", float("inf")),
			("bare", 0),
		):
			invalid = copy.deepcopy(report)
			invalid["modes"]["extended"][name]["medianUs"] = value
			with self.subTest(name=name, value=value), self.assertRaises(ValueError):
				validate(invalid)
		invalid = copy.deepcopy(report)
		del invalid["modes"]["default"]["facial"]
		with self.assertRaises(ValueError):
			validate(invalid)
