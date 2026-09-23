"""Reviewed fastening/measurement senses, composition, symbols and negative contexts."""

from __future__ import annotations

import unittest
from pathlib import Path
from unittest import mock

from tests.core_loader import load

CASES = (
	("系鞋带", "系", "ji4"),
	("系绳子", "系", "ji4"),
	("系领结", "系", "ji4"),
	("系红领巾", "系", "ji4"),
	("用尺子量长度", "量", "liang2"),
	("系好安全带", "系", "ji4"),
	("把鞋带系上", "系", "ji4"),
	("把安全带系紧", "系", "ji4"),
	("系紧红领巾", "系", "ji4"),
	("系上腰带", "系", "ji4"),
	("系牢绳子", "系", "ji4"),
	("量体温", "量", "liang2"),
	("量一下血压", "量", "liang2"),
	("量身高", "量", "liang2"),
	("量一量尺寸", "量", "liang2"),
	("测量", "量", "liang2"),
	("丈量土地", "量", "liang2"),
	("衡量标准", "量", "liang2"),
	("測量", "量", "liang2"),
	("系帽带", "系", "ji4"),
	("系了一条领带", "系", "ji4"),
	("系个活扣", "系", "ji4"),
	("系一个结", "系", "ji4"),
	("把绳子系在树上", "系", "ji4"),
	("把丝带系到盒子上", "系", "ji4"),
	("把鞋带儿系好", "系", "ji4"),
	("系好了领结", "系", "ji4"),
	("用卷尺量一下", "量", "liang2"),
	("用卷尺重新量一量", "量", "liang2"),
	("用量角器量一量", "量", "liang2"),
	("拿软尺再量一量这个盒子", "量", "liang2"),
	("身高量了两次", "量", "liang2"),
	("尺寸量不准", "量", "liang2"),
	("量孩子的身高", "量", "liang2"),
	("量我的腰围", "量", "liang2"),
	("量直径", "量", "liang2"),
	("量角度", "量", "liang2"),
	("量体积", "量", "liang2"),
	("量袖长", "量", "liang2"),
	("量出孔径", "量", "liang2"),
	("量不准水深", "量", "liang2"),
	("量三米布", "量", "liang2"),
	("量100毫升水", "量", "liang2"),
	("量３米绳子", "量", "liang2"),
	("称量样品", "量", "liang2"),
	("量杯", "量", "liang2"),
	("量具", "量", "liang2"),
	("量筒", "量", "liang2"),
	("量程", "量", "liang2"),
	("系領結", "系", "ji4"),
	("拿軟尺量一下", "量", "liang2"),
	("量直徑", "量", "liang2"),
)
NEGATIVES = (
	"系统",
	"系数",
	"系主任",
	"关系",
	"维系",
	"系泊",
	"系马",
	"舌系带",
	"系带手术",
	"联系好安全带厂家",
	"关系紧密",
	"维系了友谊",
	"把土筐系上来",
	"数量长度",
	"批量尺寸",
	"重量",
	"能量",
	"变量",
	"计量",
	"量力而行",
	"量体裁衣",
	"量入为出",
	"量子力学",
	"量化",
	"商量尺寸",
	"打量身高",
	"掂量",
	"思量",
	"系",
	"量",
	"校量",
	"校量尺寸",
	"估量长度",
	"考量身高",
	"计量尺寸",
	"裁量",
	"较量",
	"量刑",
	"量才录用",
	"量他不敢来",
	"心系红领巾",
	"此物确系领结",
	"解铃还须系铃人",
	"把桶系到井下",
	"用尺子量刑",
	"身高量化",
	"产量三米",
	"用力量身高",
	"量1234567890123米",
)


class FastenMeasureTests(unittest.TestCase):
	def test_default_and_extended_senses_are_identical_inside_sentences(self):
		for extended in (False, True):
			rules = load("rules").load_default_rules(extended=extended)
			for first, target, reading in CASES:
				for prefix, suffix in (("", ""), ("我给孩子", "之后继续"), ("😀", "|$^+=<>`~")):
					text = prefix + first + suffix
					positions = [i for i, ch in enumerate(text) if ch == target]
					for i in positions:
						self.assertEqual(reading, rules.resolve(text)[i].reading_id, text)
						self.assertEqual(rules.renderings[reading], rules.transform(text)[i], text)

	def test_every_unicode_symbol_boundary_keeps_the_new_default_readings(self):
		from tests.test_boundaries import boundary_characters

		rules = load("rules").load_default_rules(extended=False)
		for symbol in boundary_characters():
			text = symbol + "系鞋带" + symbol + "量体温" + symbol
			self.assertEqual(symbol + "冀鞋带" + symbol + "梁体温" + symbol, rules.transform(text), repr(symbol))
			text = symbol + "系领结" + symbol + "用尺子量一下" + symbol + "校量尺寸"
			self.assertEqual(
				symbol + "冀领结" + symbol + "用尺子梁一下" + symbol + "校量尺寸", rules.transform(text), repr(symbol)
			)

	def test_negative_meanings_and_cross_word_suffixes_do_not_force_alternatives(self):
		for extended in (False, True):
			rules = load("rules").load_default_rules(extended=extended)
			for text in NEGATIVES:
				for i, character in enumerate(text):
					if character in "系量":
						self.assertEqual(character, rules.transform(text)[i], (extended, text))

	def test_repetition_and_original_context_avoid_cascaded_replacement(self):
		rules = load("rules").load_default_rules(extended=False)
		for a in ("系鞋带", "系好安全带", "量体温", "测量尺寸"):
			for b in ("系鞋带", "系好安全带", "量体温", "测量尺寸"):
				for middle in ("", "之后", "很好", "|$^+=<>`~"):
					text = "请" + a + middle + b + "然后继续"
					self.assertEqual(text.replace("系", "冀").replace("量", "梁"), rules.transform(text), text)

	def test_semantic_opposites_stay_separate_in_the_same_sentence(self):
		for extended in (False, True):
			rules = load("rules").load_default_rules(extended=extended)
			for source, expected in (
				("校量尺寸之后用尺子量长度", "校量尺寸之后用尺子梁长度"),
				("商量孩子的身高，然后量孩子的身高", "商量孩子的身高，然后梁孩子的身高"),
				("心系红领巾的孩子正在系红领巾", "心系红领巾的孩子正在冀红领巾"),
				("用卷尺重新量一量，然后量力而行", "用卷尺重新梁一梁，然后量力而行"),
				("用量角器量角度，记录数量", "用梁角器梁角度，记录数量"),
			):
				# Inspect only requested targets: extended data may annotate other polyphones.
				actual = rules.transform(source)
				self.assertEqual(
					[expected[i] for i, c in enumerate(source) if c in "系量"],
					[actual[i] for i, c in enumerate(source) if c in "系量"],
					source,
				)

	def test_semantic_classes_compose_and_lexical_collisions_abstain(self):
		import tomllib

		from tests.core_loader import PLUGIN_PATH

		with (PLUGIN_PATH / "data/contributions.toml").open("rb") as stream:
			classes = tomllib.load(stream)["classes"]
		rules = load("rules").load_default_rules(extended=False)
		for noun in classes["fastener"]:
			for text in (f"系{noun}", f"系好{noun}", f"{noun}系上", f"系了一条{noun}"):
				self.assertEqual("ji4", rules.resolve(text)[text.index("系")].reading_id, text)
		for noun in classes["measurement"]:
			for text in (f"量{noun}", f"量出{noun}", f"{noun}量一下", f"量我的{noun}"):
				# These surface strings can also contain the nouns 重量/流量.
				# Do not make a topic-first construction override that ambiguity.
				expected = None if text in ("体重量一下", "體重量一下", "电流量一下", "電流量一下") else "liang2"
				self.assertEqual(expected, rules.resolve(text)[text.index("量")].reading_id, text)
		for prefix in (*classes["liangNounPrefix"], *classes["liangEvaluativePrefix"], *classes["liangNeutralPrefix"]):
			for noun in ("尺寸", "身高", "直径", "杯", "三米"):
				text = prefix + "量" + noun
				self.assertEqual("量", rules.transform(text)[len(prefix)], text)

	def test_tool_context_is_bounded_and_does_not_leak_to_later_text(self):
		rules = load("rules").load_default_rules(extended=False)
		for text in ("量", "量一量", "用尺子\n量", "用尺子，量", "用尺子" + "再" * 1000 + "量"):
			self.assertEqual(text, rules.transform(text))
		for text in ("用尺子量", "量", "用尺子量", "量"):
			self.assertEqual("用尺子梁" if text.startswith("用尺子") else text, rules.transform(text))

	def test_tool_context_does_not_cross_a_speech_item_or_command(self):
		pipeline = load("pipeline")

		class CharacterMode:
			def __init__(self, state):
				self.state = state

		normalizer = pipeline.SpeechSequenceNormalizer(
			rules=load("rules").load_default_rules(extended=False), character_mode_command_type=CharacterMode
		)
		marker = object()
		for sequence in (["用尺子", "量"], ["用尺子", marker, "量"], [CharacterMode(True), "用尺子量"]):
			self.assertIs(sequence, normalizer.normalize(sequence, options=pipeline.RuntimeOptions()))
		sequence = ["系领结", marker, "用卷尺量"]
		self.assertEqual(
			["冀领结", marker, "用卷尺梁"], normalizer.normalize(sequence, options=pipeline.RuntimeOptions())
		)

	def test_no_runtime_io_or_pronunciation_driven_braille_rewriting(self):
		rules = load("rules").load_default_rules()
		text = "😀系鞋带并量体温"
		with mock.patch.object(Path, "open", side_effect=AssertionError("speech-path I/O")):
			annotations = load("braille_readings").annotate(text, rules)
			self.assertEqual("😀冀鞋带并梁体温", rules.transform(text))
		by_offset = {a.start: a for a in annotations}
		self.assertEqual(("系", "ji4", 2), (by_offset[1].character, by_offset[1].reading, by_offset[1].utf16_start))
		self.assertEqual(("量", "liang2", 6), (by_offset[5].character, by_offset[5].reading, by_offset[5].utf16_start))
