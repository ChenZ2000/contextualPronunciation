"""Independent regressions for colloquial 懵 and lexical neutral-tone 腾."""

from __future__ import annotations

import gzip
import hashlib
import json
import unittest
from pathlib import Path

from tests.core_loader import load

COLLOQUIAL_MENG = (
	"一脸懵逼",
	"一脸懵",
	"一臉懵",
	"一臉懵逼",
	"懵了",
	"懵圈",
	"我完全懵住了",
	"看懵了",
	"听懵了",
	"聽懵了",
	"发懵",
	"發懵",
	"被问懵了",
	"把我整懵了",
	"谁都被问懵过",
	"越想越懵",
	"从懵到清醒",
	"懵得答不上话",
	"懵得说不出话",
	"懵一会儿",
	"懵来懵去",
	"懵上加懵",
	"懵逼树上懵逼果",
	"懵懵的",
)
LITERARY_MENG = (
	"懵懂",
	"懵懵懂懂",
	"懵里懵懂",
	"懵裡懵懂",
	"懵然",
	"懵董",
	"懵憧",
	"懵昧",
	"懵钝",
	"懵鈍",
	"懵头懵脑",
	"懵頭懵腦",
	"愚懵",
	"宿懵",
)
NEUTRAL_TENG = (
	("折腾", "zhe1"),
	("折騰", "zhe1"),
	("倒腾", "dao3"),
	("倒騰", "dao3"),
	("捣腾", "dao3"),
	("搗騰", "dao3"),
	("闹腾", "nao4"),
	("鬧騰", "nao4"),
	("掀腾", "xian1"),
	("掀騰", "xian1"),
)
FULL_TONE_TENG = (
	"腾飞",
	"腾空",
	"腾云驾雾",
	"奔腾",
	"沸腾",
	"欢腾",
	"升腾",
	"飞腾",
	"騰飛",
	"騰空",
	"騰雲駕霧",
	"奔騰",
	"沸騰",
	"歡騰",
	"升騰",
	"飛騰",
)


class ColloquialToneTests(unittest.TestCase):
	@classmethod
	def setUpClass(cls):
		cls.defaults = {extended: load("rules").load_default_rules(extended=extended) for extended in (False, True)}

	def test_meng_renderer_has_first_tone_in_independent_pinned_source(self):
		# Checking only the selected reading or replacement text missed the
		# 0.7.9 bug: 蒙 (also 矇) defaults to meng2 in this independent source.
		# Lexical evidence is not an acoustic guarantee for every synthesizer.
		from tools.import_cedict import PINS, UNIHAN, read_unihan

		source = gzip.decompress(UNIHAN.read_bytes())
		self.assertEqual(PINS["unihan"], hashlib.sha256(source).hexdigest())
		defaults, readings, _common = read_unihan(source.decode("utf-8").splitlines())
		for ambiguous in ("蒙", "矇"):
			self.assertEqual("meng2", defaults[ambiguous])
		for extended, rules in self.defaults.items():
			with self.subTest(extended=extended):
				renderer = rules.renderings["meng1"]
				self.assertEqual("meng1", defaults[renderer])
				self.assertEqual({"meng1"}, readings[renderer])
				self.assertEqual(1, len(renderer))
				self.assertEqual(2, len(renderer.encode("utf-16-le")))

	def test_meng_listening_probe_uses_current_output_without_claiming_certified_anchors(self):
		fixture = Path(__file__).parent / "fixtures/vocalizer_expressive2/renderer_cases.json"
		cases = json.loads(fixture.read_text("utf-8"))["cases"]
		groups = {}
		for case in cases:
			if case["id"].startswith("meng1_colloquial_"):
				groups.setdefault(case["compareGroup"], {})[case["role"]] = case
		self.assertEqual(
			{"一脸懵逼", "一脸懵", "懵了", "懵圈", "看懵了", "懵得说不出话", "被新通知整懵了"},
			{group["source"]["text"] for group in groups.values()},
		)
		for group in groups.values():
			self.assertEqual({"source", "candidate", "previous_renderer"}, set(group))
			source = group["source"]["text"]
			self.assertEqual(source.replace("懵", "蒙"), group["previous_renderer"]["text"])
			for rules in self.defaults.values():
				self.assertEqual(rules.transform(source), group["candidate"]["text"])
				self.assertEqual("meng1", group["candidate"]["expectedReading"])
			for case in group.values():
				self.assertEqual(source.index("懵"), case["targetCharIndex"])

	def test_colloquial_meng_is_productive_in_every_default_mode(self):
		for extended, rules in self.defaults.items():
			for phrase in COLLOQUIAL_MENG:
				for prefix, suffix in (("", ""), ("他说", "之后才回过神"), ("😀|", "\n")):
					text = prefix + phrase + suffix
					with self.subTest(extended=extended, text=text):
						decisions = rules.resolve(text)
						spoken = rules.transform(text)
						for index, character in enumerate(text):
							if character == "懵":
								self.assertEqual("meng1", decisions[index].reading_id)
								self.assertEqual("colloquialMeng", decisions[index].rule_id)
								self.assertEqual("擝", spoken[index])

	def test_unlisted_contexts_do_not_require_a_finite_phrase_inventory(self):
		for rules in self.defaults.values():
			for prefix in ("我", "全场观众", "阿明一下子", "看完第九版报告大家", "😀"):
				for suffix in ("了一秒", "到忘记回复", "得睁大眼睛", "归懵还得继续", "得说不出话"):
					text = prefix + "懵" + suffix
					with self.subTest(text=text):
						self.assertEqual(text.replace("懵", "擝"), rules.transform(text, targets=frozenset("懵")))

	def test_every_occurrence_in_literary_words_is_protected(self):
		for extended, rules in self.defaults.items():
			for phrase in LITERARY_MENG:
				text = "😀他说" + phrase + "，仍然" + phrase
				with self.subTest(extended=extended, text=text):
					decisions = rules.resolve(text)
					spoken = rules.transform(text)
					for index, character in enumerate(text):
						if character == "懵":
							self.assertTrue(decisions[index].protect)
							self.assertEqual("meng-literary-protection", decisions[index].rule_id)
							self.assertNotEqual("meng1", decisions[index].reading_id)
							self.assertEqual("懵", spoken[index])

	def test_protection_is_local_even_when_words_touch(self):
		for rules in self.defaults.values():
			for phrase in LITERARY_MENG:
				for separator in ("", "、", "😀", "\n"):
					text = "懵了" + separator + phrase + separator + "懵逼"
					expected = "擝了" + separator + phrase + separator + "擝逼"
					with self.subTest(text=text):
						self.assertEqual(expected, rules.transform(text, targets=frozenset("懵")))
			for text in ("一脸懵懂", "一脸懵然无知", "一臉懵懂", "一臉懵然無知"):
				self.assertEqual(text, rules.transform(text, targets=frozenset("懵")))
				self.assertTrue(rules.resolve(text)[text.index("懵")].protect)

	def test_neutral_teng_preserves_complete_words_and_explicit_readings(self):
		for extended, rules in self.defaults.items():
			self.assertNotIn("teng5", rules.renderings)
			for phrase, first_reading in NEUTRAL_TENG:
				for prefix, suffix in (("", ""), ("别再", "了"), ("😀", "了一整天")):
					text = prefix + phrase + suffix
					start = len(prefix)
					with self.subTest(extended=extended, text=text):
						decisions = rules.resolve(text)
						self.assertEqual(first_reading, decisions[start].reading_id)
						self.assertEqual("teng5", decisions[start + 1].reading_id)
						self.assertFalse(decisions[start].speech)
						self.assertFalse(decisions[start + 1].speech)
						self.assertEqual(phrase, rules.transform(text)[start : start + 2])

	def test_repeated_neutral_teng_words_resolve_each_original_character(self):
		for rules in self.defaults.values():
			for phrase, first_reading in NEUTRAL_TENG:
				text = phrase + phrase + "着" + phrase + "，又" + phrase
				decisions = rules.resolve(text)
				with self.subTest(text=text):
					self.assertEqual(text, rules.transform(text))
					for index, character in enumerate(text):
						if character == phrase[0]:
							self.assertEqual(first_reading, decisions[index].reading_id)
						elif character == phrase[1]:
							self.assertEqual("teng5", decisions[index].reading_id)
			for text in ("倒腾来倒腾去", "倒騰來倒騰去"):
				decisions = rules.resolve(text)
				self.assertEqual(text, rules.transform(text))
				for index, reading in ((0, "dao3"), (1, "teng5"), (3, "dao3"), (4, "teng5")):
					self.assertEqual(reading, decisions[index].reading_id, text)

	def test_full_tone_teng_and_unrelated_characters_do_not_gain_neutral_tone(self):
		for rules in self.defaults.values():
			for phrase in FULL_TONE_TENG:
				text = "折腾，" + phrase + "，倒腾"
				decisions = rules.resolve(text)
				with self.subTest(text=text):
					for index, character in enumerate(phrase, 3):
						if character in "腾騰":
							decision = decisions.get(index)
							self.assertNotEqual("teng5", decision.reading_id if decision else None)
			for text in (
				"蒙",
				"矇",
				"擝",
				"蒙古",
				"蒙面",
				"启蒙",
				"檬",
				"夢",
				"梦",
				"濛",
				"腾",
				"騰",
				"折，腾",
				"倒\n腾",
			):
				self.assertEqual(text, rules.transform(text), text)
			# Dictionaries disagree on these words; the new reviewed groups must abstain.
			for text in ("翻腾", "扑腾", "翻騰", "撲騰"):
				decision = rules.resolve(text).get(1)
				self.assertNotIn(
					decision.rule_id if decision else None,
					("teng-neutral-word", "teng-neutral-word-traditional"),
					text,
				)

	def test_speech_projection_suppresses_dictionary_rewrites_consistently(self):
		for rules in self.defaults.values():
			for text in (
				"😀懵了，懵懵懂懂，折腾倒腾捣腾闹腾掀腾",
				"一臉懵逼，懵裡懵懂，折騰倒騰搗騰鬧騰掀騰",
				"反复折腾之后懵了，懵懂的人又开始倒腾",
			):
				with self.subTest(text=text):
					full = rules.resolve(text)
					self.assertEqual(
						{index: decision for index, decision in full.items() if decision.speech},
						rules.resolve(text, speech_only=True),
					)
					self.assertNotIn("遮腾", rules.transform(text))
					self.assertNotIn("导腾", rules.transform(text))

	def test_neutral_teng_does_not_cross_completed_left_words(self):
		left_words = (
			("曲折", "曲折"),
			("波折", "波折"),
			("转折", "轉折"),
			("挫折", "挫折"),
			("骨折", "骨折"),
			("打折", "打折"),
			("打倒", "打倒"),
			("摔倒", "摔倒"),
			("跌倒", "跌倒"),
			("绊倒", "絆倒"),
			("推倒", "推倒"),
			("压倒", "壓倒"),
			("倾倒", "傾倒"),
		)
		texts = [left + teng + "空" for pair in left_words for left, teng in zip(pair, "腾騰", strict=True)]
		texts.extend(
			(
				"小说情节曲折腾挪，极尽变化",
				"小說情節曲折騰挪，極盡變化",
				"被一拳打倒腾空跃起的对手",
				"被一拳打倒騰空躍起的對手",
			)
		)
		for extended, rules in self.defaults.items():
			for text in texts:
				with self.subTest(extended=extended, text=text):
					full = rules.resolve(text)
					speech = rules.resolve(text, speech_only=True)
					self.assertEqual({index: decision for index, decision in full.items() if decision.speech}, speech)
					spoken = rules.transform(text)
					for index, character in enumerate(text):
						if character not in "折倒腾騰":
							continue
						for decisions in (full, speech):
							self.assertTrue(decisions[index].protect)
							self.assertIsNone(decisions[index].reading_id)
						self.assertEqual(character, spoken[index])
					annotations = load("braille_readings").annotate(text, rules)
					self.assertTrue(all(item.character not in "折倒腾騰" for item in annotations))

	def test_neutral_teng_before_full_tone_word_prefixes_remains_valid(self):
		for extended, rules in self.defaults.items():
			for phrase, first_reading in NEUTRAL_TENG:
				for suffix in ("空调", "空间", "飞机", "空調", "空間", "飛機"):
					text = "别再" + phrase + suffix + "了"
					with self.subTest(extended=extended, text=text):
						full = rules.resolve(text)
						speech = rules.resolve(text, speech_only=True)
						self.assertEqual(first_reading, full[2].reading_id)
						self.assertEqual("teng5", full[3].reading_id)
						self.assertFalse(full[2].protect or full[3].protect)
						self.assertNotIn(2, speech)
						self.assertNotIn(3, speech)
						self.assertEqual(phrase, rules.transform(text)[2:4])

	def test_user_keep_and_explicit_readings_take_priority(self):
		for extended in (False, True):
			for entry, text, expected, index, reading in (
				("懵了|懵|keep", "懵了，懵逼", "懵了，擝逼", 0, None),
				("懵了|懵|meng3", "懵了", "猛了", 0, "meng3"),
				("懵懂|懵|meng1", "懵懂", "擝懂", 0, "meng1"),
				("折腾|折|keep", "折腾", "折腾", 0, None),
				("折腾|折|zhe2", "折腾", "哲腾", 0, "zhe2"),
				("倒腾|倒|dao4", "倒腾", "到腾", 0, "dao4"),
				("折腾|腾|keep", "折腾", "折腾", 1, None),
				("折腾|腾|teng2", "折腾", "折疼", 1, "teng2"),
			):
				rules = load("rules").load_default_rules(extended=extended, custom_entries=entry)
				with self.subTest(extended=extended, entry=entry):
					self.assertEqual(reading, rules.resolve(text)[index].reading_id)
					self.assertTrue(rules.resolve(text)[index].user)
					self.assertEqual(expected, rules.transform(text))

	def test_user_templates_override_keep_and_annotate_without_a_neutral_anchor(self):
		for extended in (False, True):
			for pattern, text, expected, index, reading in (
				("[懵:keep]了", "懵了，懵逼", "懵了，擝逼", 0, None),
				("[懵:meng1]懂", "懵懂", "擝懂", 0, "meng1"),
				("折[腾:keep]", "折腾", "折腾", 1, None),
				("倒[騰:teng5]", "倒騰", "倒騰", 1, "teng5"),
				("翻[腾:teng5]", "翻腾", "翻腾", 1, "teng5"),
			):
				rules = load("rules").load_default_rules(extended=extended, custom_templates=pattern)
				with self.subTest(extended=extended, pattern=pattern):
					self.assertNotIn("teng5", rules.renderings)
					self.assertEqual(expected, rules.transform(text))
					decision = rules.resolve(text)[index]
					self.assertTrue(decision.user)
					self.assertEqual(reading, decision.reading_id)
					annotations = {item.start: item for item in load("braille_readings").annotate(text, rules)}
					if reading is None:
						self.assertNotIn(index, annotations)
					else:
						self.assertEqual(reading, annotations[index].reading)

	def test_first_syllable_groups_can_be_disabled_independently(self):
		for extended in (False, True):
			for group, first, original, fallback in (
				("zhe-neutral-word", "折", "折腾，倒腾", "折腾，倒腾"),
				("dao-neutral-word", "倒", "倒腾，折腾", "倒腾，折腾"),
			):
				rules = load("rules").load_default_rules(extended=extended, disabled_rules=group)
				with self.subTest(extended=extended, group=group):
					self.assertEqual(fallback if extended else original, rules.transform(original))
					decisions = rules.resolve(original)
					decision = decisions.get(original.index(first))
					self.assertNotEqual(group, decision.rule_id if decision else None)
					for index in (1, 4):
						self.assertEqual("teng5", decisions[index].reading_id)
						self.assertFalse(decisions[index].speech)

	def test_disabling_colloquial_default_keeps_protections_and_teng_rules(self):
		for extended in (False, True):
			rules = load("rules").load_default_rules(extended=extended, disabled_rules="colloquialMeng")
			text = "一脸懵逼，懵了，懵懵懂懂，折腾倒腾"
			self.assertEqual(text, rules.transform(text))
			self.assertEqual("teng5", rules.resolve(text)[text.index("腾")].reading_id)

	def test_annotations_keep_original_characters_and_utf16_offsets(self):
		text = "😀懵了，折腾；懵懂，倒騰"
		for rules in self.defaults.values():
			annotations = {item.start: item for item in load("braille_readings").annotate(text, rules)}
			for index, character, reading in (
				(1, "懵", "meng1"),
				(4, "折", "zhe1"),
				(5, "腾", "teng5"),
				(10, "倒", "dao3"),
				(11, "騰", "teng5"),
			):
				item = annotations[index]
				self.assertEqual((character, reading), (item.character, item.reading))
				self.assertEqual((index, index + 1), (item.start, item.end))
				self.assertEqual((index + 1, index + 2), (item.utf16_start, item.utf16_end))
			self.assertNotIn(7, annotations)
			self.assertEqual(("2345", "3456"), annotations[5].dots)
			self.assertEqual("😀懵了，折腾；懵懂，倒騰", text)

	def test_pipeline_preserves_spelling_mode_and_command_boundaries(self):
		pipeline = load("pipeline")

		class CharacterMode:
			def __init__(self, state):
				self.state = state

		for rules in self.defaults.values():
			normalizer = pipeline.SpeechSequenceNormalizer(rules=rules, character_mode_command_type=CharacterMode)
			marker = object()
			on, off = CharacterMode(True), CharacterMode(False)
			sequence = ["一脸懵逼，折腾", marker, on, "懵了倒腾", off, "懵懂，懵了倒腾"]
			self.assertEqual(
				["一脸擝逼，折腾", marker, on, "懵了倒腾", off, "懵懂，擝了倒腾"],
				normalizer.normalize(sequence, options=pipeline.RuntimeOptions()),
			)
			# A word's protection cannot be reconstructed across speech items or commands.
			for split in (["懵", "懂"], ["懵", marker, "懂"]):
				self.assertEqual(split, normalizer.normalize(split, options=pipeline.RuntimeOptions()))
			sequence = ["懵了折腾", marker]
			self.assertIs(sequence, normalizer.normalize(sequence, options=pipeline.RuntimeOptions(enabled=False)))
