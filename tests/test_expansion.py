"""Independent positive/negative oracles for the 0.4 coverage expansion."""

from __future__ import annotations

import gzip
import json
import unittest

from tests.core_loader import load
from tools import audit_polyphone_reference as reference
from tools import build_polyphone_coverage as coverage
from tools.import_cedict import UNIHAN, read_unihan

ROW_POSITIVES = (
	"几行",
	"这几行很好",
	"请删除那几行之后重试",
	"数行",
	"若干行",
	"多少行",
	"十几行",
	"二十多行",
	"百余行",
	"幾行",
	"數行",
	"百餘行",
	"几 行",
	"几\t行",
	"几　行",
	"几行几列",
	"表格有多少行多少列",
	"竖行",
	"豎行",
	"竪行",
	"这几行和竖行很好",
	"几行代码写在句子中间",
	"写了数行之后",
	"删去数行",
	"共有數行",
	"前数行很好",
	"这段文本有数行内容",
)
ROW_NEGATIVES = (
	"这张茶几行吗",
	"茶几行不行",
	"条几行吗",
	"炕几 行吗",
	"几\n行",
	"几     行",
	"几行星",
	"数行程",
	"几行礼",
	"数行善事",
	"多行不义必自毙",
	"横行霸道",
	"直行车辆",
	"一行人",
	"日行二百里",
	"几何",
	"几乎",
	"1" * 13 + "几行",
	"1" * 13 + "多行",
	"这个参数行吗",
	"这个读数行不行",
	"约数行吗",
	"岁数行吗",
	"次數行嗎",
	"这个字数行吗",
	"心里有数行不行",
	"参数行不行",
	"這個函數行嗎",
)


class ExpansionTests(unittest.TestCase):
	def test_quantity_followed_by_feasibility_predicate(self):
		rules = load("rules").load_default_rules(extended=False)
		for source, expected in (
			("这几行不行", "这几航不行"),
			("这几行行不行", "这几航行不行"),
			("数行不行，十几行才够", "数航不行，十几航才够"),
			("茶几行不行，这几行不行", "茶几行不行，这几航不行"),
		):
			self.assertEqual(expected, rules.transform(source), source)

	def test_quantities_and_vertical_rows_in_both_modes(self):
		for extended in (False, True):
			rules = load("rules").load_default_rules(extended=extended)
			for text in ROW_POSITIVES:
				for index, character in enumerate(text):
					if character == "行":
						self.assertEqual("hang2", rules.resolve(text)[index].reading_id, (extended, text))
			for text in ROW_NEGATIVES:
				self.assertFalse(
					any(d.reading_id == "hang2" and not d.protect for d in rules.resolve(text).values()), text
				)

	def test_original_offsets_and_local_disabling(self):
		text = "😀茶几行不行，这几行很好，竖行"
		rules = load("rules").load_default_rules(extended=False)
		annotations = load("braille_readings").annotate(text, rules)
		rows = [v for v in annotations if v.reading == "hang2"]
		self.assertEqual(2, len(rows))
		for item in rows:
			self.assertEqual("行", text[item.start : item.end])
			self.assertEqual(item.start + 1, item.utf16_start)
		self.assertEqual(
			"几行，竖航",
			load("rules")
			.load_default_rules(extended=False, disabled_rules="rowIndefiniteQuantity")
			.transform("几行，竖行"),
		)

	def test_every_unicode_delimiter_retains_row_quantity(self):
		from tests.test_boundaries import boundary_characters

		rules = load("rules").load_default_rules(extended=False)
		for boundary in boundary_characters():
			self.assertEqual("几航" + boundary + "竖航", rules.transform("几行" + boundary + "竖行"), repr(boundary))

	def test_music_elasticity_breathing_and_projectile_counterexamples(self):
		rules = load("rules").load_default_rules(extended=False)
		for source, expected in (
			("他屏息听她弹琴", "他丙息听她谈琴"),
			("弹簧的弹性和弹力", "谈簧的谈性和谈力"),
			("她屏气凝神地弹奏", "她丙气凝神地谈奏"),
			("子弹性能很好", "子弹性能很好"),
			("炮弹力量很大", "炮弹力量很大"),
			("屏幕和屏风", "屏幕和屏风"),
		):
			self.assertEqual(expected, rules.transform(source), source)

	def test_grammatical_homographs_remain_whole_word_blockers(self):
		rules = load("rules").load_default_rules()
		for text in ("文中的词语", "手中的书", "字面上的意思", "正中的位置"):
			self.assertEqual(text, rules.transform(text), text)

	def test_coverage_exhausts_pinned_multireading_inventory_and_is_reproducible(self):
		content = coverage.generate()
		self.assertEqual(content, coverage.OUTPUT.read_bytes())
		report = json.loads(content)
		with gzip.open(UNIHAN, "rt", encoding="utf-8") as stream:
			_, attested, _ = read_unihan(stream)
		self.assertEqual({ch for ch, values in attested.items() if len(values) > 1}, set(report["characters"]))
		for ch, item in report["characters"].items():
			self.assertEqual(attested[ch], set(item["readings"]))
			for reading, state in item["readings"].items():
				self.assertLessEqual(len(state["examples"]), state["headwords"])
				if state["automaticLexiconSpeechEligible"]:
					self.assertTrue(state["headwords"] and state["homophoneCandidate"])
					self.assertNotEqual(item["unihanCNDefault"], reading)

	def test_reference_parser_marks_damaged_and_misaligned_claims(self):
		text = "# test\n1. 伺 ①cì 伺候\n②chuo 伺机\n2.辟 ①biàn 方便 便利\n3. 差 ①chà 差点 ②shā 刹车\n## next\n答应"
		claims, unparsed = reference.extract(text)
		self.assertEqual(4, len(claims))
		self.assertEqual([7], unparsed)
		self.assertEqual(
			"reading_not_attested_in_pinned_unihan", reference.classify(claims[1], "伺机", {"伺": {"si4", "ci4"}}, {})
		)
		self.assertEqual("target_alignment_manual_review", reference.classify(claims[2], "方便", {}, {}))
		self.assertEqual("damaged_line_manual_review", reference.classify(claims[3], "差点", {}, {}))
		self.assertEqual(
			"corroborated_candidate_only",
			reference.classify(claims[0], "伺候", {"伺": {"ci4"}}, {"伺候": {("ci4", "hou5")}}),
		)
		self.assertEqual(
			"cedict_opaque_or_ambiguous",
			reference.classify(claims[0], "伺候", {"伺": {"ci4"}}, {"伺候": {None, ("ci4", "hou5")}}),
		)
