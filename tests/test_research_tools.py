from __future__ import annotations

import json
import unittest
from pathlib import Path

from tools.generate_unihan_inventory import extract

ROOT = Path(__file__).resolve().parents[1]


class ResearchToolTests(unittest.TestCase):
	def test_unihan_union_and_source_traceability(self):
		items = extract(
			[
				"# header\n",
				"U+884C\tkMandarin\txíng\n",
				"U+884C\tkHanyuPinyin\t00000.000:háng,xíng 00001.000:xíng\n",
				"U+4E00\tkMandarin\tyī\n",
				"U+884C\tkCantonese\thang4\n",
			]
		)
		self.assertEqual(1, len(items))
		self.assertEqual(["háng", "xíng"], items[0]["candidateReadings"])
		self.assertFalse(items[0]["defaultEnabled"])

	def test_final_fixture_is_generated_from_current_rules(self):
		from tools.generate_final_renderer_fixture import build_fixture

		fixture = json.loads(
			(ROOT / "tests/fixtures/vocalizer_expressive2/final_renderer_regression.json").read_text("utf-8")
		)
		self.assertEqual(build_fixture(), fixture)

	def test_cross_engine_probe_uses_both_default_and_extended_modes(self):
		from tools.generate_final_renderer_fixture import SCENARIOS
		from tools.probe_global_voices import cases

		items = {item["id"]: item for item in cases()}
		self.assertEqual({scenario.id for scenario in SCENARIOS}, set(items))
		for name, expected, extended in (
			("cheng2_compound_food", "呈红豆粥", False),
			("liang2_unknown_owner", "梁小名的身高", False),
			("diao4_lowered_audio", "降吊音频", True),
			("tiao2_audio_engineer", "条音师", True),
		):
			self.assertEqual(expected, items[name]["normalized"])
			self.assertIs(items[name]["extended"], extended)
			self.assertNotEqual(items[name]["normalized"], items[name]["anchor"])

	def test_renderer_candidates_and_runtime_profiles_are_consistent(self):
		from tests.core_loader import load

		data = json.loads(
			(ROOT / "addon/globalPlugins/contextualPronunciation/data/rules_zh_CN.json").read_text("utf-8")
		)
		self.assertEqual(
			{
				**load("lexicon").load_default_lexicon().renderings,
				**{key: value["replacement"] for key, value in data["readings"].items()},
			},
			dict(load("rules").load_default_rules(extended=False).renderings),
		)
