"""A lexicon default is not an acoustic default: preserve resolved word edges."""

from __future__ import annotations

import unittest

from tests.core_loader import load


class CrossingReadingTests(unittest.TestCase):
	@classmethod
	def setUpClass(cls):
		cls.rules = load("rules").load_default_rules()

	def test_reported_compound_is_already_segmented_correctly_but_now_locked(self):
		rules = self.rules
		text = "降调音频"
		lexicon = rules.lexicon
		self.assertEqual("diao4", lexicon.defaults["调"])
		self.assertEqual({(0, 2), (2, 4)}, set(lexicon._segments(text)))
		self.assertEqual({(0, 2), (2, 4)}, set(lexicon._segments(text, reverse=True)))
		self.assertEqual("降吊音频", rules.transform(text))
		decision = rules.resolve(text)[1]
		self.assertEqual("diao4", decision.reading_id)
		self.assertTrue(decision.speech)
		self.assertIn("crossing-reading-lock", decision.rule_id)

	def test_systemic_lock_with_multiple_tone_nouns_and_traditional_forms(self):
		for prefix in ("降调", "升调", "变调", "大调", "小调", "音调", "降調", "升調"):
			for suffix in ("音频", "音頻"):
				text = prefix + suffix
				index = len(prefix) - 1
				decision = self.rules.resolve(text).get(index)
				self.assertIsNotNone(decision, text)
				self.assertEqual("diao4", decision.reading_id, text)
				self.assertEqual("吊", self.rules.transform(text)[index], text)

	def test_a_real_tuning_word_keeps_tiao_and_no_collision_does_not_force_default(self):
		for text in ("调音", "调音师", "负责调音的师傅", "调音设备", "調音", "空调音频"):
			target = "調" if "調" in text else "调"
			index = text.index(target)
			self.assertEqual("tiao2", self.rules.resolve(text)[index].reading_id, text)
			self.assertEqual("条", self.rules.transform(text)[index], text)
		for text in ("降调", "降调版本", "升调版本"):
			self.assertFalse(self.rules.resolve(text)[1].speech)
			self.assertEqual(text, self.rules.transform(text))

	def test_sentence_commands_spelling_user_keep_and_braille_offsets(self):
		text = "😀把降调音频发给调音师"
		rules = self.rules
		self.assertEqual("😀把降吊音频发给条音师", rules.transform(text))
		annotations = {a.start: a for a in load("braille_readings").annotate(text, rules)}
		self.assertEqual(
			("调", "diao4", 4), (annotations[3].character, annotations[3].reading, annotations[3].utf16_start)
		)
		self.assertEqual("tiao2", annotations[8].reading)
		rules = load("rules").load_default_rules(custom_entries="降调|调|keep")
		self.assertEqual("降调音频", rules.transform("降调音频"))
		pipeline = load("pipeline")

		class CharacterMode:
			def __init__(self, state):
				self.state = state

		normalizer = pipeline.SpeechSequenceNormalizer(rules=self.rules, character_mode_command_type=CharacterMode)
		marker = object()
		sequence = ["降调", marker, "音频"]
		self.assertEqual(sequence, normalizer.normalize(iter(sequence), options=pipeline.RuntimeOptions()))
		sequence = [CharacterMode(True), "降调音频", CharacterMode(False), "降调音频"]
		result = normalizer.normalize(sequence, options=pipeline.RuntimeOptions())
		self.assertEqual("降调音频", result[1])
		self.assertEqual("降吊音频", result[3])

	def test_synthetic_other_character_proves_no_tone_specific_exception(self):
		module = load("lexicon")
		data = {
			"schemaVersion": 2,
			"maxWordLength": 32,
			"defaults": {"甲": "jia3"},
			"renderings": {"jia3": "假", "jia4": "架"},
			"speechTargets": ["甲"],
			"reservedTargets": "",
			"allowedReadings": ["jia3", "jia4"],
			"words": {"乙甲": "yi3 jia3", "甲丙": "jia4 bing3", "丙丁": "bing3 ding1"},
		}
		for words in (data["words"], dict(reversed(list(data["words"].items())))):
			lexicon = module.PhraseLexicon(dict(data, words=words))
			self.assertEqual((), lexicon.annotate("乙甲")[0].forced_offsets)
			spans = lexicon.annotate("乙甲丙丁", speech_only=True)
			self.assertEqual(1, len(spans))
			self.assertEqual("乙甲", spans[0].text)
			self.assertEqual((1,), spans[0].forced_offsets)
			# A blocked longer word must remain opaque, not be rescued by a rival.
			blocked = module.PhraseLexicon(dict(data, words={**words, "乙甲丙丁": ""}))
			self.assertEqual((), blocked.annotate("乙甲丙丁", speech_only=True))

	def test_full_and_speech_projections_are_identical_at_forced_default_positions(self):
		for text in ("降调音频", "降调音乐", "😀升调音频$", "大调和小调音频", "调音师", "降调"):
			full = self.rules.resolve(text)
			self.assertEqual(
				{i: d for i, d in full.items() if d.speech}, self.rules.resolve(text, speech_only=True), text
			)
