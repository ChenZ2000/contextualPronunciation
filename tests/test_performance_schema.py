"""Hosted timing comparisons must preserve workload meaning across upgrades."""

import unittest

from scripts.compare_hosted_performance import MOTION_ADDITIONS, compare_hot_path


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
