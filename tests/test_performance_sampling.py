"""Distributed hosted samples retain workloads, provenance and strict gates."""

import copy
import unittest

from scripts.compare_hosted_performance import compare
from scripts.sample_hosted_performance import PROCESS_ROUNDS, aggregate
from tools.benchmark_growth import SCENARIOS, validate


class PerformanceSamplingTests(unittest.TestCase):
	def reports(self, values=(100, 101, 102, 103, 1000), *, kind="hot_path"):
		rows = []
		for value in values:
			report = {"sourceSha256": {"runtime.py": "fixed"}}
			if kind == "hot_path":
				report["measurements"] = {
					"text": {
						"inputCodePoints": 5,
						"iterationsPerRound": 2000,
						"rounds": 7,
						"medianMicrosecondsPerCall": value,
					}
				}
			else:
				report["modes"] = {
					mode: {
						"measurements": {
							"text": {"codepoints": 5, "samples": 200, "medianUs": value, "p95Us": value * 2}
						}
					}
					for mode in ("default", "extended")
				}
			rows.append(report)
		return rows

	def test_every_round_is_retained_and_original_timed_call_totals_are_preserved(self):
		for kind, metric, total in (("hot_path", "medianMicrosecondsPerCall", 70_000), ("grammar", "medianUs", 1000)):
			with self.subTest(kind=kind):
				reports = self.reports(kind=kind)
				before = copy.deepcopy(reports)
				result = aggregate(reports, kind)
				row = (result if kind == "hot_path" else result["modes"]["default"])["measurements"]["text"]
				self.assertEqual(102, row[metric])
				self.assertEqual([100, 101, 102, 103, 1000], row["processMediansUs"])
				self.assertEqual(total, row["totalTimedCalls"])
				self.assertEqual(PROCESS_ROUNDS, row["processRounds"])
				self.assertNotIn("p95Us", row)
				self.assertEqual(before, reports)

	def test_missing_round_or_changed_source_cannot_be_accepted(self):
		with self.assertRaises(ValueError):
			aggregate(self.reports()[:-1], "hot_path")
		reports = self.reports()
		reports[-1]["sourceSha256"]["runtime.py"] = "changed"
		with self.assertRaises(ValueError):
			aggregate(reports, "hot_path")
		for field in ("benchmarkSha256", "measurementEnvironment"):
			reports = self.reports()
			reports[-1][field] = "changed"
			with self.subTest(field=field), self.assertRaises(ValueError):
				aggregate(reports, "hot_path")

	def test_invalid_timing_cannot_be_hidden_by_a_valid_median(self):
		for invalid in (0, -1, float("nan"), float("inf")):
			with self.subTest(invalid=invalid), self.assertRaises(ValueError):
				aggregate(self.reports((100, 100, 100, 100, invalid)), "hot_path")

	def test_changed_workload_and_sampling_are_rejected(self):
		for field in ("inputCodePoints", "iterationsPerRound", "rounds"):
			reports = self.reports()
			reports[-1]["measurements"]["text"][field] += 1
			with self.subTest(field=field), self.assertRaises(ValueError):
				aggregate(reports, "hot_path")
		reports = self.reports()
		reports[-1]["measurements"]["unexpected"] = {}
		with self.assertRaises(ValueError):
			aggregate(reports, "hot_path")

	def test_stable_regression_still_fails_the_unchanged_threshold(self):
		baseline = aggregate(self.reports((100,) * 5), "hot_path")["measurements"]
		current = aggregate(self.reports((140,) * 5), "hot_path")["measurements"]
		self.assertFalse(compare(current, baseline, "medianMicrosecondsPerCall")[0]["passed"])
		current["text"]["totalTimedCalls"] -= 1
		with self.assertRaises(ValueError):
			compare(current, baseline, "medianMicrosecondsPerCall")

	def test_growth_rounds_retain_call_totals_and_absolute_failure_is_an_observation(self):
		reports = []
		for value in (31000, 32000, 33000, 34000, 90000):
			reports.append(
				{
					"sourceSha256": {"runtime.py": "fixed"},
					"passed": True,
					"modes": {
						mode: {
							"measurements": {
								name: {
									"codepoints": len(text),
									"samples": (100 if len(text) > 1000 else 250) // PROCESS_ROUNDS,
									"medianUs": value if len(text) > 1000 else 50,
									"p95Us": value * 2,
								}
								for name, text in SCENARIOS.items()
							}
						}
						for mode in ("default", "extended")
					},
				}
			)
		result = aggregate(reports, "growth")
		self.assertFalse(result["passed"])
		rows = result["modes"]["default"]["measurements"]
		self.assertEqual(33000, rows["generic8k"]["medianUs"])
		self.assertEqual(100, rows["generic8k"]["totalTimedCalls"])
		self.assertEqual(250, rows["classifiedGeneric"]["totalTimedCalls"])
		self.assertEqual([31000, 32000, 33000, 34000, 90000], rows["generic8k"]["processMediansUs"])
		self.assertNotIn("p95Us", rows["generic8k"])
		report = {"modes": {mode: data["measurements"] for mode, data in result["modes"].items()}}
		validate(report, check_latency=False, minimum_samples=20)
		with self.assertRaises(ValueError):
			validate(report, minimum_samples=20)
		rows["generic8k"]["medianUs"] = float("nan")
		with self.assertRaises(ValueError):
			validate(report, check_latency=False, minimum_samples=20)
