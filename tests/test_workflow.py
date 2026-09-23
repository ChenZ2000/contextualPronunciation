from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unicodedata
import unittest
from pathlib import Path
from unittest import mock

from scripts import prepare_nvda
from scripts.evidence import SCREEN_EFFECT_TEST, validate_hashes, validate_performance, validate_xml

ROOT = Path(__file__).resolve().parents[1]


class WorkflowGuardTests(unittest.TestCase):
	def test_beta_ble_skips_cannot_mask_failures_or_apply_to_stable(self):
		from scripts.evidence import _BETA_BLE_REASON, _BETA_BLE_TESTS

		with tempfile.TemporaryDirectory() as directory:
			path = Path(directory) / "beta.xml"
			for identifier in sorted(_BETA_BLE_TESTS):
				classname, _, method = identifier.rpartition(".")
				xml = (
					f'<testsuite tests="1" skipped="1"><testcase classname="{classname}" name="{method}">'
					f'<skipped message="{_BETA_BLE_REASON}"/></testcase></testsuite>'
				)
				path.write_text(xml, "utf-8")
				result = validate_xml(path, nvda_version="2026.3beta2")
				self.assertEqual(0, result["passed"])
				self.assertEqual(1, len(result["upstreamUnimplementedSkips"]))
				with self.assertRaises(ValueError):
					validate_xml(path)
				path.write_text(xml.replace(_BETA_BLE_REASON, "Different reason"), "utf-8")
				with self.assertRaises(ValueError):
					validate_xml(path, nvda_version="2026.3beta2")

	def test_only_explicit_upstream_screen_effect_skip_can_be_recorded(self):
		classname, _, method = SCREEN_EFFECT_TEST.rpartition(".")
		xml = (
			f'<testsuite tests="1" skipped="1"><testcase classname="{classname}" name="{method}">'
			'<skipped message="Full screen colour effect set external to tests."/></testcase></testsuite>'
		)
		with tempfile.TemporaryDirectory() as directory:
			path = Path(directory) / "tests.xml"
			path.write_text(xml, "utf-8")
			with self.assertRaises(ValueError):
				validate_xml(path)
			result = validate_xml(path, allow_external_screen_effect=True)
			self.assertEqual(0, result["passed"], "A skipped test must never be counted as passed")
			self.assertEqual(1, result["skipped"])
			for mutated in (xml.replace(method, "test_speech"), xml.replace("external to tests", "unknown reason")):
				path.write_text(mutated, "utf-8")
				with self.assertRaises(ValueError):
					validate_xml(path, allow_external_screen_effect=True)

	def test_original_boundary_mutation_is_detected_for_all_reported_symbols(self):
		from tests.test_boundaries import BoundaryRegressionTests, rules_module

		def old_boundary(text, position):
			if position >= len(text):
				return True
			return text[position].isspace() or unicodedata.category(text[position])[0] in {"P", "Z"}

		BoundaryRegressionTests.setUpClass()
		with mock.patch.object(rules_module, "_is_boundary", old_boundary):
			result = unittest.TestResult()
			BoundaryRegressionTests("test_reported_nine_symbols_after_numeric_row").run(result)
		self.assertEqual(9, len(result.failures))
		self.assertFalse(result.errors, "Regression must fail assertions, not break its setup")

	def test_pinned_nvda_checkout_refuses_wrong_revision_or_tracked_changes(self):
		with tempfile.TemporaryDirectory() as directory:
			path = Path(directory)
			(path / ".git").mkdir()
			with mock.patch.object(prepare_nvda, "NVDA", path):
				with mock.patch.object(prepare_nvda, "git", return_value="wrong-revision"):
					with self.assertRaisesRegex(RuntimeError, "revision"):
						prepare_nvda.prepare()
				with mock.patch.object(prepare_nvda, "git", side_effect=[prepare_nvda.NVDA_COMMIT, " M file.py"]):
					with self.assertRaisesRegex(RuntimeError, "tracked changes"):
						prepare_nvda.prepare(submodules=True)

	def test_nvda_xml_gate_rejects_skips_errors_failures_and_empty_runs(self):
		with tempfile.TemporaryDirectory() as directory:
			path = Path(directory) / "results.xml"
			path.write_text(
				'<testsuites><testsuite tests="1"><testcase name="pass"/></testsuite></testsuites>', "utf-8"
			)
			self.assertEqual(1, validate_xml(path)["tests"])
			for xml in (
				"<testsuites/>",
				'<testsuite tests="2"><testcase/></testsuite>',
				'<testsuite tests="1" skipped="1"><testcase><skipped/></testcase></testsuite>',
				'<testsuite tests="1"><testcase><failure/></testcase></testsuite>',
				'<testsuite tests="1" errors="1"><testcase><error/></testcase></testsuite>',
			):
				path.write_text(xml, "utf-8")
				with self.subTest(xml=xml), self.assertRaises(ValueError):
					validate_xml(path)

	def test_evidence_rejects_stale_files_empty_hashes_and_escaping_paths(self):
		with tempfile.TemporaryDirectory() as directory:
			root = Path(directory)
			(root / "code.py").write_bytes(b"current")
			correct = hashlib.sha256(b"current").hexdigest()
			validate_hashes(root, {"code.py": correct})
			for hashes in ({}, {"code.py": "wrong"}, {"../code.py": correct}):
				with self.assertRaises(ValueError):
					validate_hashes(root, hashes)

	def test_performance_gate_rejects_missing_or_over_budget_scenarios(self):
		with self.assertRaises(KeyError):
			validate_performance({"measurements": {}})
		with self.assertRaises(ValueError):
			validate_performance(
				{"measurements": {"pluginFilterWithStubs_shortNoCandidate": {"medianMicrosecondsPerCall": 101}}}
			)

	def test_release_mode_cannot_silently_omit_native_or_licensed_ve(self):
		result = subprocess.run(
			[sys.executable, "scripts/run_regression.py", "--release"], cwd=ROOT, capture_output=True, text=True
		)
		self.assertEqual(2, result.returncode)
		self.assertIn("requires both --native and --vocalizer", result.stderr)

	def test_boundary_fixture_matches_current_pipeline_and_nvda_sources(self):
		from tools.boundary_acoustics import FIXTURE, build_fixture

		self.assertEqual(build_fixture(), json.loads(FIXTURE.read_text("utf-8")))

	def test_sentence_fixture_matches_independent_oracles_and_actual_profile(self):
		from tools.sentence_acoustics import FIXTURE, build_fixture

		fixture = build_fixture()
		self.assertEqual(fixture, json.loads(FIXTURE.read_text("utf-8")))
		self.assertEqual(130, len(fixture["groups"]))
		self.assertEqual(520, len(fixture["cases"]))

	def test_display_guard_restores_after_success_and_assertion_failure(self):
		from scripts.run_nvda_unit_tests import protect_test_body

		for fail in (False, True):
			state = ["original"]
			observations = []

			class Case(unittest.TestCase):
				def runTest(self):  # noqa: N802
					self.state[0] = "black"
					if self.should_fail:
						self.fail("original assertion")

			case = Case()
			case.state = state
			case.should_fail = fail
			protect_test_body(
				case,
				read_state=lambda state=state: state[0],
				restore_state=lambda before, state=state: state.__setitem__(0, before),
				encode_state=lambda value: value,
				observations=observations,
			)
			result = unittest.TestResult()
			case.run(result)
			self.assertEqual("original", state[0])
			self.assertTrue(observations[0]["restored"])
			self.assertEqual(int(fail), len(result.failures))
			self.assertFalse(result.errors)

	def test_display_guard_does_not_override_upstream_setup_skip(self):
		from scripts.run_nvda_unit_tests import protect_test_body

		class Case(unittest.TestCase):
			def setUp(self):
				self.skipTest("External display effect")

			def runTest(self):  # noqa: N802
				self.fail("Skipped body must not run")

		case = Case()
		unexpected = mock.Mock(side_effect=AssertionError("Skipped test must not touch display"))
		observations = []
		protect_test_body(
			case, read_state=unexpected, restore_state=unexpected, encode_state=unexpected, observations=observations
		)
		result = unittest.TestResult()
		case.run(result)
		self.assertEqual(1, len(result.skipped))
		self.assertFalse(result.errors)
		self.assertEqual([], observations)
		unexpected.assert_not_called()

	def test_no_hot_path_filesystem_or_network_access(self):
		from tests.core_loader import load
		from tests.test_pipeline import CharacterModeCommand

		pipeline = load("pipeline")
		normalizer = pipeline.SpeechSequenceNormalizer(
			rules=load("rules").load_default_rules(),
			character_mode_command_type=CharacterModeCommand,
		)
		with (
			mock.patch("builtins.open", side_effect=AssertionError("Hot-path I/O")),
			mock.patch("pathlib.Path.open", side_effect=AssertionError("Hot-path I/O")),
			mock.patch("socket.socket", side_effect=AssertionError("Hot-path network")),
		):
			self.assertEqual(
				["呈汤$；航 12|；Doesn't"],
				normalizer.normalize(["盛汤$；行 12|；Doesn’t"], options=pipeline.RuntimeOptions()),
			)
