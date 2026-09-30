"""Independent classifier/stature contrasts and whole neutral-word preservation."""

from __future__ import annotations

import unittest

from tests.core_loader import load


class NeutralTests(unittest.TestCase):
	@classmethod
	def setUpClass(cls):
		cls.rules = load("rules").load_default_rules()

	def test_clipped_stature_has_full_tone_without_an_extra_syllable(self):
		for base in (
			"长个",
			"长个了",
			"长不了个",
			"长得了个",
			"长一长个",
			"长不长个",
			"长点个",
			"长一点个",
			"長個",
			"長不了個",
			"長個了沒",
		):
			for suffix in ("", "。", "？", "😀"):
				text = base + suffix
				with self.subTest(text=text):
					p = next(i for i, c in enumerate(text) if c in "个個")
					self.assertEqual("ge4", self.rules.resolve(text)[p].reading_id)
					spoken = self.rules.transform(text)
					self.assertEqual("各", spoken[p])
					self.assertEqual(len(text), len(spoken))
					self.assertNotIn("儿", spoken)

	def test_classifier_variations_remain_annotation_only_neutral(self):
		for text in (
			"长个东西",
			"长个奇怪的东西",
			"长了个东西",
			"一个人",
			"这三个人",
			"每个",
			"买了个东西",
			"说个不停",
			"哭个不停",
			"一个性格",
			"这个性格",
			"長個東西",
			"買了個東西",
			"這三個人",
		):
			with self.subTest(text=text):
				p = next(i for i, c in enumerate(text) if c in "个個")
				d = self.rules.resolve(text)[p]
				self.assertEqual("ge5", d.reading_id)
				self.assertFalse(d.speech)
				self.assertEqual(text[p], self.rules.transform(text)[p])

	def test_full_tone_words_unknowns_numeral_bounds_and_boundaries(self):
		for text in (
			"个",
			"個",
			"个人",
			"个性",
			"个中",
			"个别",
			"个体",
			"个子",
			"个头",
			"自个儿",
			"这个性鲜明",
			"这個性鮮明",
			"长，个",
			"长\n个",
			"长个未知东西",
			"长个了个包",
			"校长个",
			"队长个",
			"三" * 9 + "个",
			"长个" + "吧" * 4,
		):
			with self.subTest(text=text):
				for i, ch in enumerate(text):
					if ch in "个個":
						d = self.rules.resolve(text).get(i)
						self.assertNotIn(d.rule_id if d else None, ("neutralGe", "neutralGeTraditional"))

	def test_lexical_neutral_words_preserve_the_complete_word(self):
		for text in (
			"数落",
			"亲家",
			"朋友",
			"明白",
			"漂亮",
			"桌子",
			"妈妈",
			"爷爷",
			"麻烦",
			"看看",
			"说说",
			"折腾",
			"倒腾",
		):
			with self.subTest(text=text):
				self.assertEqual(text, self.rules.transform(text))
				self.assertTrue(
					any(d.reading_id and d.reading_id.endswith("5") for d in self.rules.resolve(text).values())
				)
		# Homographic full/neutral senses and a suffix alone supply no rule.
		for text in ("大意", "地方", "地道", "便宜", "原子", "分子"):
			self.assertNotIn(text, self.rules.lexicon.neutral_words)

	def test_disabled_rules_and_personal_overrides_preserve_authority(self):
		for options, expected in (
			({"disabled_rules": "neutralGe"}, "掌个"),
			({"custom_entries": "长个|个|keep"}, "掌个"),
			({"custom_entries": "长个|个|ge4"}, "掌各"),
			({"custom_templates": "长[个:keep]"}, "掌个"),
		):
			r = load("rules").load_default_rules(**options)
			self.assertEqual(expected, r.transform("长个"))

	def test_original_offsets_speech_projection_and_braille_agree(self):
		braille = load("braille_readings")
		for text in ("😀长个了没？", "😀长个东西", "长个奇怪的东西", "朋友数落妈妈", "長個了"):
			self.assertEqual(
				{i: d for i, d in self.rules.resolve(text).items() if d.speech},
				self.rules.resolve(text, speech_only=True),
			)
			annotations = {a.start: a for a in braille.annotate(text, self.rules)}
			for i, ch in enumerate(text):
				if ch not in "个個":
					continue
				a = annotations[i]
				self.assertEqual(ch, a.character)
				self.assertEqual(self.rules.resolve(text)[i].reading_id, a.reading)
				self.assertEqual(i + int(text.startswith("😀")), a.utf16_start)

	def test_speech_items_commands_and_spelling_do_not_supply_context(self):
		from tests.test_pipeline import CharacterModeCommand

		p = load("pipeline")
		n = p.SpeechSequenceNormalizer(rules=self.rules, character_mode_command_type=CharacterModeCommand)
		marker = object()
		sequence = ["长", marker, "个", CharacterModeCommand(True), "长个", CharacterModeCommand(False), "长个"]
		self.assertEqual(sequence[:-1] + ["掌各"], n.normalize(sequence, options=p.RuntimeOptions()))

	def test_stature_and_object_mixed_length_modifiers(self):
		text = "长个长长的东西"
		self.assertEqual("掌个偿偿的东西", self.rules.transform(text))
		parsed = self.rules.syntax.analyze(text, 0)
		self.assertEqual("东西", text[parsed.head_start : parsed.head_end])
		self.assertIn("clf", {d.relation for d in parsed.dependencies})


if __name__ == "__main__":
	unittest.main()
