"""Run the complete upstream suite, restoring its screen-test color effect.

Uses the same discovery roots, native bootstrap and XML runner as upstream's
rununittests.bat. No upstream files/assertions/skips are modified. An instance
wrapper only restores the screen test's entry matrix before its tearDown.
"""

from __future__ import annotations

import importlib
import json
import sys
import unittest
from datetime import UTC, datetime
from pathlib import Path


def protect_test_body(case, *, read_state, restore_state, encode_state, observations):
	"""Add restoration only; keep the original test ID, assertions and outcome."""
	method = case._testMethodName
	original = getattr(case, method)

	def body():
		before = read_state()
		record = {"testId": case.id(), "before": encode_state(before), "restored": False}
		observations.append(record)
		try:
			return original()
		finally:
			# No waiting, logging or filesystem access while a black effect is set.
			restore_state(before)
			record["after"] = encode_state(read_state())
			record["restored"] = record["after"] == record["before"]
			case.assertTrue(record["restored"], "Screen-test color state must be restored")

	setattr(case, method, body)


def iter_cases(suite):
	for item in suite:
		if isinstance(item, unittest.TestSuite):
			yield from iter_cases(item)
		else:
			yield item


def main() -> int:
	from evidence import SCREEN_EFFECT_TEST
	from prepare_nvda import NVDA

	root = Path(__file__).resolve().parents[1]
	sys.path.insert(0, str(NVDA))
	sys.path.insert(0, str(NVDA / "source"))
	importlib.import_module("tests.unit")
	mag = importlib.import_module("winBindings.magnification")
	import xmlrunner

	suite = unittest.defaultTestLoader.discover(str(NVDA / "tests/unit"), top_level_dir=str(NVDA))
	observations = []
	guarded = []
	for case in iter_cases(suite):
		if case.id() == SCREEN_EFFECT_TEST:
			guarded.append(case.id())
			protect_test_body(
				case,
				read_state=mag.MagGetFullscreenColorEffect,
				restore_state=mag.MagSetFullscreenColorEffect,
				encode_state=lambda effect: [[float(effect.transform[i][j]) for j in range(5)] for i in range(5)],
				observations=observations,
			)
	if guarded != [SCREEN_EFFECT_TEST]:
		raise RuntimeError("Expected exactly one upstream screen-color test to protect")
	output = NVDA / "testOutput/unit/unitTests.xml"
	output.parent.mkdir(parents=True, exist_ok=True)
	try:
		with output.open("wb") as stream:
			result = xmlrunner.XMLTestRunner(output=stream, buffer=True, verbosity=1).run(suite)
	finally:
		(root / "artifacts/nvda-display-guard.json").write_text(
			json.dumps(
				{
					"testedAtUtc": datetime.now(UTC).isoformat(),
					"guardedTests": guarded,
					"executedGuards": observations,
					"allExecutedGuardsRestored": all(record["restored"] for record in observations),
					"note": "Keep upstream external-effect skips; never force-reset the display to run a test.",
				},
				indent=2,
			)
			+ "\n",
			"utf-8",
		)
	return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
	raise SystemExit(main())
