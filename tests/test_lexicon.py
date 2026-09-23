from __future__ import annotations

import json
import random
import unittest
from pathlib import Path
from unittest import mock

from tests.core_loader import PLUGIN_PATH, load
from tests.lexicon_cases import LEXICON_CASES, UNCHANGED_CASES, expected_text
from tools.import_cedict import compile_lexicon, generate, numbered, parse_cedict

lexicon_module = load("lexicon")
rules_module = load("rules")
renderings = load("rules").load_default_rules(extended=False).renderings


class ImporterTests(unittest.TestCase):
	def test_numbered_pinyin_and_umlaut_are_not_conflated(self):
		for raw, expected in (
			("lǜ", "lv4"),
			("lu:4", "lv4"),
			("lü4", "lv4"),
			("lù", "lu4"),
			("nǚ", "nv3"),
			("chóng", "chong2"),
			("shèng", "sheng4"),
			("de", "de5"),
			("de5", "de5"),
			("r5", None),
			("xx5", None),
			("huar1", "huar1"),
			("hua1 r5", None),
			("abc0", None),
		):
			self.assertEqual(expected, numbered(raw), raw)

	def test_conflicting_readings_never_depend_on_source_order(self):
		lines = [
			"便宜 便宜 [bian4 yi2] /convenient/\n",
			"便宜 便宜 [pian2 yi5] /cheap/\n",
			"樂觀 乐观 [le4 guan1] /optimistic/\n",
		]
		expected = parse_cedict(lines)
		for seed in range(10):
			shuffled = lines.copy()
			random.Random(seed).shuffle(shuffled)
			self.assertEqual(expected, parse_cedict(shuffled))
		self.assertEqual(2, len(expected[0]["便宜"]))

	def test_proper_names_and_unaligned_erhua_remain_blockers(self):
		words, _, counts = parse_cedict(
			[
				"朝陽 朝阳 [zhao1 yang2] /morning sun/\n",
				"朝陽 朝阳 [Chao2 yang2] /place/\n",
				"花兒 花儿 [huar1] /flower/\n",
				"不明 不明 [bu4 xx5] /unknown/\n",
			]
		)
		self.assertIn(None, words["朝阳"])
		self.assertEqual({None}, words["花儿"])
		self.assertEqual({None}, words["不明"])
		self.assertEqual(2, counts["unalignedEntriesBlocked"])
		with self.assertRaises(ValueError):
			parse_cedict(["invalid entry"])

	def test_pinned_sources_reproduce_every_generated_byte_offline(self):
		for path, content in generate().items():
			self.assertEqual(content, path.read_bytes(), str(path))

	def test_unverified_positions_do_not_discard_other_attested_positions(self):
		unihan = [
			"U+7532\tkMandarin\tjiǎ\n",
			"U+7532\tkHanyuPinyin\t1:jiǎ,jiá\n",
			"U+4E59\tkMandarin\tyǐ\n",
			"U+4E19\tkMandarin\tde\n",
		]
		cedict = ["甲乙 甲乙 [jia2 yi4] /test/", "甲丙 甲丙 [jia2 de2] /test/"]
		for lines in (cedict, list(reversed(cedict))):
			runtime, coverage = compile_lexicon(lines, unihan)
			self.assertEqual("jia2 ?", runtime["words"]["甲乙"])
			self.assertEqual("", runtime["words"]["甲丙"])
			self.assertEqual(1, coverage["counts"]["crossCheckAbstainedPositions"])
			self.assertNotIn("甲乙", coverage["blockedHeadwords"])
		# A proper-name entry still blocks the WHOLE word despite the above.
		runtime, _ = compile_lexicon([*cedict, "甲乙 甲乙 [Jia3 yi3] /name/"], unihan)
		self.assertEqual("", runtime["words"]["甲乙"])


class LexiconTests(unittest.TestCase):
	@classmethod
	def setUpClass(cls):
		cls.lexicon = lexicon_module.load_default_lexicon()
		cls.rules = rules_module.load_default_rules()
		cls.data = json.loads((PLUGIN_PATH / "data/lexicon_zh_CN.json").read_text("utf-8"))

	def test_all_headwords_round_trip_or_explicitly_abstain(self):
		# Exhaust the complete shipped dictionary, including every blocker, not
		# a sample of convenient positives. This checks conversion/matching, not
		# the independent linguistic truth of every source entry.
		for word, reading in self.data["words"].items():
			spans = self.lexicon.annotate(word)
			if not reading:
				self.assertEqual((), spans, word)
			else:
				self.assertEqual(1, len(spans), word)
				span = spans[0]
				self.assertEqual(
					(0, len(word), word, tuple(None if p == "?" else p for p in reading.split())),
					(span.start, span.end, span.text, span.readings),
					word,
				)

	def test_independent_reading_oracles_with_global_mapping(self):
		for source, positions in LEXICON_CASES:
			self.assertEqual(
				expected_text(source, positions, self.rules.renderings),
				self.rules.transform(source),
				source,
			)

	def test_speech_projection_matches_full_decisions_for_every_headword(self):
		for word in self.data["words"]:
			full = self.rules.resolve(word)
			self.assertEqual(
				{index: decision for index, decision in full.items() if decision.speech},
				self.rules.resolve(word, speech_only=True),
				word,
			)

	def test_speech_projection_keeps_segmentation_blockers_and_braille_annotations(self):
		for source in (*UNCHANGED_CASES, *(text for text, _ in LEXICON_CASES), "普通桌面文字与数字123。" * 5):
			full = self.rules.resolve(source)
			projected = self.rules.resolve(source, speech_only=True)
			self.assertEqual({i: d for i, d in full.items() if d.speech}, projected, source)
			# Projection must not cache, rewrite or delete the full source result.
			self.assertEqual(full, self.rules.resolve(source))
		self.assertTrue(self.lexicon.annotate("普通桌面文字"))
		self.assertEqual((), self.lexicon.annotate("普通桌面文字", speech_only=True))

	def test_all_unicode_boundaries_preserve_music_matches(self):
		from tests.test_boundaries import boundary_characters

		for symbol in boundary_characters():
			for prefix, suffix in ((symbol, ""), ("", symbol), (symbol, symbol)):
				source = prefix + "仙乐飘飘" + suffix
				self.assertEqual(prefix + "仙月飘飘" + suffix, self.rules.transform(source), repr(symbol))

	def test_repeated_music_lexemes_are_resolved_in_original_context(self):
		phrases = ("仙乐", "音乐", "礼乐", "管弦乐")
		for first in phrases:
			for second in phrases:
				for joiner in ("", "之后", "很好", "|$^+=<>`~"):
					for prefix, suffix in (("", ""), ("我听到", "飘飘"), ("😀", "🎵")):
						source = prefix + first + joiner + second + suffix
						self.assertEqual(source.replace("乐", "月"), self.rules.transform(source), source)

	def test_ambiguous_incomplete_neutral_and_unsupported_contexts(self):
		for source in UNCHANGED_CASES:
			self.assertIs(source, self.rules.transform(source), source)
		self.assertEqual("呈面的时候", self.rules.transform("盛面的时候", renderings=renderings))
		self.assertFalse(any(span.text == "面的" for span in self.lexicon.annotate("盛面的时候")))

	def test_reading_annotations_do_not_replace_original_braille_text(self):
		source = "😀仙乐飘飘，快乐"
		span = self.lexicon.annotate(source)[0]
		self.assertEqual((1, 3, "仙乐", ("xian1", "yue4")), (span.start, span.end, span.text, span.readings))
		self.assertEqual("😀仙乐飘飘，快乐", source)
		self.assertEqual(source[span.start : span.end], span.text)

	def test_bidirectional_disagreement_and_blocked_longer_words(self):
		data = {
			"schemaVersion": 2,
			"maxWordLength": 32,
			"defaults": {},
			"renderings": {},
			"speechTargets": [],
			"reservedTargets": "",
			"allowedReadings": [],
			"words": {"甲乙": "jia3 yi3", "乙丙": "yi3 bing3"},
		}
		lexicon = lexicon_module.PhraseLexicon(data)
		self.assertEqual((), lexicon.annotate("甲乙丙"))
		self.assertEqual(2, len(lexicon.annotate("甲乙，乙丙")))
		data["words"]["甲乙丙"] = ""
		self.assertEqual((), lexicon_module.PhraseLexicon(data).annotate("甲乙丙"))
		data["words"]["甲乙丙"] = "jia3 yi3 bing3"
		self.assertEqual(1, len(lexicon_module.PhraseLexicon(data).annotate("甲乙丙")))

	def test_custom_keep_is_local_and_does_not_disable_entire_new_character(self):
		rules = rules_module.load_default_rules(custom_entries="仙乐|乐|keep")
		self.assertEqual("仙乐飘飘，音月观众", rules.transform("仙乐飘飘，音乐观众"))
		rules = rules_module.load_default_rules(custom_entries="个人朝阳|朝|zhao1")
		self.assertEqual("个人钊阳", rules.transform("个人朝阳"))

	def test_original_rule_disabling_cannot_be_undone_by_the_lexicon(self):
		rules = rules_module.load_default_rules(disabled_rules="cheng-serving-object-bounded")
		self.assertEqual("盛饭盛汤，仙月飘飘", rules.transform("盛饭盛汤，仙乐飘飘"))

	def test_extended_mode_can_be_disabled_without_disabling_core_rules(self):
		with mock.patch.object(rules_module, "load_default_lexicon", side_effect=AssertionError("eager lexicon load")):
			rules = rules_module.load_default_rules(extended=False)
		self.assertEqual("仙月飘飘，呈汤", rules.transform("仙乐飘飘，盛汤"))
		self.assertEqual("龟裂", rules.transform("龟裂"))

	def test_no_file_access_during_repeated_normalization(self):
		with mock.patch.object(Path, "open", side_effect=AssertionError("I/O in speech path")):
			for _ in range(30):
				self.assertEqual("仙月飘飘", self.rules.transform("仙乐飘飘"))

	def test_loader_is_cached_and_renderer_maps_are_single_character(self):
		self.assertIs(self.lexicon, lexicon_module.load_default_lexicon())
		self.assertGreater(len(self.lexicon._words), 100_000)
		self.assertGreater(len(self.lexicon.triggers), 400)
		self.assertTrue(all(len(ch) == 1 for ch in renderings.values()))
