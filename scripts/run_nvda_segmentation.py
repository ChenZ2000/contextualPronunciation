"""Native beta CWS/Liblouis tests in an isolated NVDA bootstrap, never live NVDA.

Private upstream interfaces are used ONLY here to test the pinned implementation;
none are imported, initialized or patched by the shipped plugin.
"""

from __future__ import annotations

import importlib
import json
import re
import statistics
import subprocess
import sys
import tempfile
import timeit
import types
import unittest
from pathlib import Path
from unittest import mock

from prepare_nvda import NVDA, NVDA_COMMIT, NVDA_VERSION

if NVDA_VERSION != "2026.3beta2":
	raise RuntimeError("This native CWS test requires the pinned beta target")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(NVDA))
sys.path.insert(0, str(NVDA / "source"))
importlib.import_module("tests.unit")
from textUtils._wordSeg.wordSegStrategy import ChineseWordSegmentationStrategy  # noqa: E402
from textUtils._wordSeg.wordSegUtils import WordSegWithSeparatorOffsetConverter  # noqa: E402

ChineseWordSegmentationStrategy._initCppJieba(forceInit=True)
if ChineseWordSegmentationStrategy._lib is None:
	raise RuntimeError("Native cppjieba DLL must really initialize; no fallback/stub allowed")
package = types.ModuleType("_nativeCwsPronunciation")
package.__path__ = [str(ROOT / "addon/globalPlugins/contextualPronunciation")]
sys.modules[package.__name__] = package
rules_module = importlib.import_module(package.__name__ + ".rules")
annotations = importlib.import_module(package.__name__ + ".braille_readings")


class NativeSegmentationTests(unittest.TestCase):
	observations = {}

	def test_native_tone_audio_boundaries_and_addon_reading_lock(self):
		rules = rules_module.load_default_rules()
		boundaries = {}
		for text in ("降调音频", "降调版本", "升调音频", "调音师"):
			converter = WordSegWithSeparatorOffsetConverter(text)
			boundaries[text] = converter.encoded
			self.assertEqual(
				text, "".join(ch for i, ch in enumerate(converter.encoded) if i not in converter.newSepIndex)
			)
			for position in range(len(text) + 1):
				self.assertEqual(position, converter.encodedToStrOffsets(converter.strToEncodedOffsets(position)))
		self.assertEqual("降调 音频", boundaries["降调音频"])
		self.assertEqual("降吊音频", rules.transform("降调音频"))
		self.assertEqual("条音师", rules.transform("调音师"))
		self.observations["toneAudioSegmentation"] = boundaries

	def test_compact_table_matches_every_expanded_context_and_routing(self):
		import louisHelper

		installed = str(ROOT / "addon/brailleTables/zhcn-contextual-2018.ctb")
		with tempfile.TemporaryDirectory(prefix="pronunciation-braille-") as directory:
			reference = Path(directory) / "reference.ctb"
			subprocess.run(
				[sys.executable, str(ROOT / "tools/build_braille_table.py"), "--reference-output", str(reference)],
				cwd=ROOT,
				check=True,
				capture_output=True,
			)
			phrases = sorted(
				set(re.findall(r"^# \S+: (\S+) \((?:keep|[a-z]+[1-5])\)$", reference.read_text("utf-8"), re.M))
			)
			self.assertGreater(len(phrases), 10_000)
			comparisons = 0
			for i, phrase in enumerate(phrases):
				variants = [phrase, " ".join(phrase)]
				if i % 23 == 0:
					variants.extend((phrase[:1] + "\n" + phrase[1:], "😀" + phrase + "|$^+=<>`~"))
				for text in variants:
					cursor = len(text) // 2
					self.assertEqual(
						louisHelper.translate([str(reference)], text, cursorPos=cursor),
						louisHelper.translate([installed], text, cursorPos=cursor),
						text,
					)
					comparisons += 1
			self.observations["factoringDifferential"] = {"uniquePhrases": len(phrases), "comparisons": comparisons}

	def test_compact_table_has_a_bounded_warm_translation_cost(self):
		import louisHelper

		text = "系领结并用卷尺量一下身高。" * 50
		timings = {}
		for name, table in (
			("base", "zhcn-cbs.ctb"),
			("contextual", str(ROOT / "addon/brailleTables/zhcn-contextual-2018.ctb")),
		):
			louisHelper.translate([table], text)
			timings[name] = (
				statistics.median(
					timeit.repeat(lambda table=table: louisHelper.translate([table], text), number=10, repeat=3)
				)
				/ 10
			)
		# Broad relative/absolute guard, not per-call p99 or physical-display latency.
		self.assertLess(timings["contextual"], max(0.030, timings["base"] * 10))
		self.observations["warmBrailleTranslation"] = {
			"codePoints": len(text),
			"rounds": 3,
			"callsPerRound": 10,
			"medianBatchAverageMilliseconds": {name: value * 1000 for name, value in timings.items()},
		}

	def test_actual_cppjieba_changes_boundaries_without_rewriting_original(self):
		text = "😀我给孩子盛汤之后盛饭"
		converter = WordSegWithSeparatorOffsetConverter(text)
		self.assertTrue(converter.newSepIndex, "Must exercise real segmentation")
		self.assertEqual(text, "".join(ch for i, ch in enumerate(converter.encoded) if i not in converter.newSepIndex))
		for position in range(len(text) + 1):
			encoded = converter.strToEncodedOffsets(position)
			self.assertEqual(position, converter.encodedToStrOffsets(encoded))

	def test_global_engine_is_independent_of_native_segmentation_and_reading_is_original(self):
		text = "😀系鞋带并量体温，仙乐飘飘"
		rules = rules_module.load_default_rules()
		expected = rules.transform(text)
		with mock.patch.object(
			ChineseWordSegmentationStrategy, "_callCppJieba", side_effect=AssertionError("coupling")
		):
			self.assertEqual(expected, rules.transform(text))
			readings = {a.start: a for a in annotations.annotate(text, rules)}
			self.assertEqual(("系", "ji4", 2), (readings[1].character, readings[1].reading, readings[1].utf16_start))

	def test_optional_overlay_handles_inserted_spaces_and_preserves_region_routing(self):
		import braille
		import config

		table = str(ROOT / "addon/brailleTables/zhcn-contextual-2018.ctb")
		config.conf["braille"]["translationTable"] = "zhcn-cbs.ctb"
		config.conf["braille"]["useChineseWordSegmentation"] = True
		# Normal literary output, not the user's intentional computer-braille
		# expansion at the cursor (which disables contextual table rules).
		config.conf["braille"]["expandAtCursor"] = False
		for text, target, expected in (
			("😀盛汤之后盛饭", 1, [31, 60]),
			("😀盛汤之后盛饭", 5, [31, 60]),
			("仙乐飘飘", 1, [62]),
			("系鞋带", 0, [27, 10]),
			("系领结", 0, [27, 10]),
			("量直径", 0, [7, 45, 2]),
			("用卷尺量一下", 3, [7, 45, 2]),
			("身高量一下", 2, [7, 45, 2]),
			# The base table groups 量体 at the first position. Keep that group,
			# correcting its first syllable without inventing per-char routing.
			("量体温", 0, [7, 45, 2, 30, 10, 4]),
		):
			with (
				self.subTest(text=text, target=target),
				mock.patch.object(
					type(braille.handler),
					"table",
					new_callable=mock.PropertyMock,
					return_value=types.SimpleNamespace(fileName=table),
				),
			):
				region = braille.Region()
				region.rawText, region.cursorPos = text, target
				region.update()
				self.assertEqual(text, region.rawText)
				self.assertEqual(len(text), len(region.rawToBraillePos))
				self.assertEqual(region.rawToBraillePos[target], region.brailleCursorPos)
				self.assertTrue(all(0 <= p < len(text) for p in region.brailleToRawPos))
				self.assertEqual(
					expected,
					[
						c
						for c, raw in zip(region.brailleCells, region.brailleToRawPos, strict=True)
						if raw == target and c
					],
				)

	def test_body_measurement_overrides_only_existing_base_word_group(self):
		import louisHelper

		table = str(ROOT / "addon/brailleTables/zhcn-contextual-2018.ctb")
		for text in ("量体温", "量体重", "量体积", "量体 温"):
			cells, b2r, r2b, cursor = louisHelper.translate([table], text, cursorPos=1)
			_base, _mapping, original_groups, _ = louisHelper.translate(["zhcn-cbs.ctb"], text)
			self.assertEqual([7, 45, 2, 30, 10, 4], [c for c, raw in zip(cells, b2r, strict=True) if raw == 0])
			self.assertEqual(r2b[1], cursor)
			for i in range(1, len(text)):
				self.assertEqual(original_groups[i] == original_groups[i - 1], r2b[i] == r2b[i - 1])
		for text in ("量体裁衣", "量体\n温", "校量尺寸", "估量长度", "商量身高", "心系红领巾"):
			self.assertEqual(louisHelper.translate(["zhcn-cbs.ctb"], text), louisHelper.translate([table], text))

	def test_optional_context_space_is_bounded_and_never_crosses_newlines(self):
		import louisHelper

		table = str(ROOT / "addon/brailleTables/zhcn-contextual-2018.ctb")
		for text in ("盛汤", "盛 汤"):
			cells, mapping, _, _ = louisHelper.translate([table], text)
			self.assertEqual([31, 60], [c for c, i in zip(cells, mapping, strict=True) if i == 0])
		for text in ("盛\n汤", "盛  汤", "丰 盛 饭 菜", "关 系 好 安 全 带"):
			self.assertEqual(louisHelper.translate(["zhcn-cbs.ctb"], text), louisHelper.translate([table], text), text)


if __name__ == "__main__":
	result = unittest.TextTestRunner(verbosity=2).run(
		unittest.defaultTestLoader.loadTestsFromTestCase(NativeSegmentationTests)
	)
	report = {
		"nvdaVersion": NVDA_VERSION,
		"nvdaCommit": NVDA_COMMIT,
		"testsRun": result.testsRun,
		"failures": len(result.failures),
		"errors": len(result.errors),
		"skipped": len(result.skipped),
		"passed": result.wasSuccessful() and not result.skipped,
		"nativeCppJieba": True,
		"liveConfigurationAccessed": False,
		"observations": NativeSegmentationTests.observations,
	}
	(ROOT / "artifacts/nvda-native-segmentation.json").write_text(json.dumps(report, indent=2) + "\n", "utf-8")
	raise SystemExit(0 if report["passed"] else 1)
