"""Reported colloquial and happiness outputs at speech and command boundaries."""

from __future__ import annotations

import unittest

from tests.core_loader import load


class ReportedReadingTests(unittest.TestCase):
	@classmethod
	def setUpClass(cls):
		cls.modes = {extended: load("rules").load_default_rules(extended=extended) for extended in (False, True)}

	def test_happiness_with_and_without_punctuation_and_nearby_music(self):
		for rules in self.modes.values():
			for phrase in ("一点都不快乐", "一点都不快樂", "快樂", "快乐"):
				for suffix in ("", "。", ".", "！", "？", "……", "\n", "😀"):
					text = "😀" + phrase + suffix
					with self.subTest(text=text):
						i = next(i for i, ch in enumerate(text) if ch in "乐樂")
						self.assertEqual("le4", rules.resolve(text)[i].reading_id)
						self.assertEqual("泐", rules.transform(text)[i])
						self.assertEqual(
							{i: d for i, d in rules.resolve(text).items() if d.speech},
							rules.resolve(text, speech_only=True),
						)
			text = "音乐让人快乐，但我一点都不快乐。"
			self.assertEqual("音月让人快泐，但我一点都不快泐。", rules.transform(text))

	def test_colloquial_tone_and_isolated_literary_voice_preservation(self):
		positive = (
			"我整个人都懵逼了",
			"懵逼中",
			"懵逼ing",
			"懵逼得不行",
			"懵了个逼",
			"我现在有点懵",
			"当时都懵了",
			"懵懵地看着他",
			"懵懵哒",
			"懵懵噠",
		)
		for rules in self.modes.values():
			for text in positive:
				for suffix in ("", "。", "！", "？"):
					with self.subTest(text=text, suffix=suffix):
						self.assertEqual(
							text.replace("懵", "擝") + suffix, rules.transform(text + suffix, targets=frozenset("懵"))
						)
			for text in ("懵", "懵。", "懵！", "懵懂", "懵懵懂懂", "懵然", "懵懂的读音", "懵懵哒的读音"):
				self.assertEqual(text, rules.transform(text, targets=frozenset("懵")))

	def test_happiness_keep_disable_spelling_and_braille(self):
		for extended in (False, True):
			for kwargs in ({"custom_entries": "快乐|乐|keep"}, {"disabled_rules": "le-happiness"}):
				rules = load("rules").load_default_rules(extended=extended, **kwargs)
				self.assertEqual("一点都不快乐。", rules.transform("一点都不快乐。"))
			from tests.test_pipeline import CharacterModeCommand

			p = load("pipeline")
			n = p.SpeechSequenceNormalizer(rules=self.modes[extended], character_mode_command_type=CharacterModeCommand)
			marker = object()
			sequence = [
				"一点都不快乐。",
				marker,
				CharacterModeCommand(True),
				"快乐。",
				CharacterModeCommand(False),
				"快乐。",
			]
			actual = n.normalize(sequence, options=p.RuntimeOptions())
			self.assertEqual("一点都不快泐。", actual[0])
			self.assertEqual(sequence[1:5], actual[1:5])
			self.assertEqual("快泐。", actual[-1])
			annotation = next(
				a for a in load("braille_readings").annotate("😀快乐。", self.modes[extended]) if a.character == "乐"
			)
			self.assertEqual(
				(2, 3, "乐", "le4"),
				(annotation.start, annotation.utf16_start, annotation.character, annotation.reading),
			)
