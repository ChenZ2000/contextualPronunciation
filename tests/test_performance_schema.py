"""Hosted timing comparisons must preserve workload meaning across upgrades."""

import unittest

from scripts.compare_hosted_performance import MOTION_ADDITIONS, compare_growth, compare_hot_path
from scripts.sample_hosted_performance import PROCESS_ROUNDS
from tools.benchmark_growth import SCENARIOS


class PerformanceSchemaTests(unittest.TestCase):
	def reports(self):
		baseline = {
			"pluginFilterWithStubs_shortNoCandidate": {"medianMicrosecondsPerCall": 10},
			"defaultPlugin_shortNoCandidate": {"medianMicrosecondsPerCall": 1},
			"longDenseHits8k": {"medianMicrosecondsPerCall": 1000},
		}
		current = {k: dict(v) for k, v in baseline.items()}
		current["defaultPlugin_shortNoCandidate"]["medianMicrosecondsPerCall"] = 10
		current.update({k: {"medianMicrosecondsPerCall": 15 if "short" in k else 1500} for k in MOTION_ADDITIONS})
		return current, baseline

	def test_retired_mode_uses_the_same_dictionary_workload(self):
		current, baseline = self.reports()
		rows, aliases = compare_hot_path(current, baseline)
		self.assertTrue(all(r["passed"] for r in rows))
		self.assertEqual("pluginFilterWithStubs_shortNoCandidate", aliases["defaultPlugin_shortNoCandidate"])
		self.assertEqual(1, baseline["defaultPlugin_shortNoCandidate"]["medianMicrosecondsPerCall"])

	def test_new_features_cannot_hide_regressions_or_missing_measurements(self):
		current, baseline = self.reports()
		current["longMotionSentences8k"]["medianMicrosecondsPerCall"] = 3000
		rows, _ = compare_hot_path(current, baseline)
		self.assertFalse(next(r for r in rows if r["scenario"] == "longMotionSentences8k")["passed"])
		for missing in ("longMotionSentences8k", "longDenseHits8k"):
			with self.assertRaises(ValueError):
				compare_hot_path({k: v for k, v in current.items() if k != missing}, baseline)
		with self.assertRaises(ValueError):
			compare_hot_path(current | {"unknown": {"medianMicrosecondsPerCall": 1}}, baseline)
		current["longMotionSentences8k"]["medianMicrosecondsPerCall"] = float("nan")
		with self.assertRaises(ValueError):
			compare_hot_path(current, baseline)

	def growth_reports(self, speed=1):
		current = {"modes": {}}
		baseline = {"modes": {}}
		for mode in ("default", "extended"):
			current["modes"][mode] = {
				"measurements": {
					name: {
						"codepoints": len(text),
						"samples": (100 if len(text) > 1000 else 250) // PROCESS_ROUNDS,
						"totalTimedCalls": 100 if len(text) > 1000 else 250,
						"processRounds": PROCESS_ROUNDS,
						"medianUs": (25000 if len(text) > 1000 else 100) * speed,
					}
					for name, text in SCENARIOS.items()
				}
			}
			baseline["modes"][mode] = {
				"measurements": {
					"short": {
						"codepoints": 10,
						"samples": 200,
						"totalTimedCalls": 1000,
						"processRounds": PROCESS_ROUNDS,
						"medianUs": 60 * speed,
					},
					"page": {
						"codepoints": 8192,
						"samples": 20,
						"totalTimedCalls": 100,
						"processRounds": PROCESS_ROUNDS,
						"medianUs": 15000 * speed,
					},
				}
			}
		return current, baseline

	def test_growth_envelope_accounts_for_host_speed_and_still_detects_excess_cost(self):
		for speed in (1, 2):
			current, baseline = self.growth_reports(speed)
			rows = compare_growth(current, baseline)
			self.assertEqual(2 * len(SCENARIOS), len(rows))
			self.assertTrue(all(row["passed"] for row in rows))
			self.assertTrue(all(row["comparisonType"] == "new-feature-envelope" for row in rows))
			current["modes"]["default"]["measurements"]["generic8k"]["medianUs"] = 31000 * speed
			rows = compare_growth(current, baseline)
			self.assertFalse(next(row for row in rows if row["scenario"] == "growth/default/generic8k")["passed"])

	def test_growth_unknown_missing_or_invalid_samples_cannot_pass(self):
		for field, value in (
			("samples", 1),
			("totalTimedCalls", 1),
			("processRounds", 1),
			("codepoints", 1),
			("medianUs", float("nan")),
			("medianUs", float("inf")),
			("medianUs", 0),
		):
			current, baseline = self.growth_reports()
			current["modes"]["default"]["measurements"]["generic8k"][field] = value
			with self.subTest(field=field, value=value), self.assertRaises(ValueError):
				compare_growth(current, baseline)
		for name in ("generic8k", "neutral8k"):
			current, baseline = self.growth_reports()
			del current["modes"]["default"]["measurements"][name]
			with self.subTest(missing=name), self.assertRaises(ValueError):
				compare_growth(current, baseline)
		current, baseline = self.growth_reports()
		current["modes"]["default"]["measurements"]["unexpected"] = {}
		with self.assertRaises(ValueError):
			compare_growth(current, baseline)

	def test_growth_reference_requires_both_sizes_modes_and_valid_sampling(self):
		for field, value in (("samples", 0), ("totalTimedCalls", 1), ("medianUs", float("nan"))):
			current, baseline = self.growth_reports()
			baseline["modes"]["default"]["measurements"]["page"][field] = value
			with self.subTest(field=field), self.assertRaises(ValueError):
				compare_growth(current, baseline)
		current, baseline = self.growth_reports()
		del baseline["modes"]["default"]["measurements"]["page"]
		with self.assertRaises(ValueError):
			compare_growth(current, baseline)
		current, baseline = self.growth_reports()
		del baseline["modes"]["extended"]
		with self.assertRaises(ValueError):
			compare_growth(current, baseline)
