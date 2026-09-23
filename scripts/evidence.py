"""Small fail-closed validators shared by the workflow and release gate."""

from __future__ import annotations

import hashlib
import xml.etree.ElementTree as ET
from pathlib import Path


def sha256(path: Path) -> str:
	return hashlib.sha256(path.read_bytes()).hexdigest()


SCREEN_EFFECT_TEST = (
	"tests.unit.test_visionEnhancementProviders.test_magnificationAPI.Test_ScreenCurtain."
	"test_setAndConfirmBlackFullscreenColorEffect"
)
_BETA_BLE_REASON = "Requires BLE support from PR C (#19122)"
_BETA_BLE_TESTS = frozenset(
	"tests.unit.brailleDisplayDrivers.test_dotPad.TestDotPadBle." + name
	for name in (
		"test_addBleDevices_registration",
		"test_check_returnsTrue",
		"test_isBleDotPad_matching",
		"test_isBleDotPad_nonMatching",
		"test_tryConnect_bleDevice",
	)
)


def validate_xml(path: Path, *, allow_external_screen_effect: bool = False, nvda_version: str = "2026.2") -> dict:
	root = ET.parse(path).getroot()
	suites = [root] if root.tag == "testsuite" else list(root.iter("testsuite"))
	counts = {
		key: sum(int(suite.get(key, "0")) for suite in suites) for key in ("tests", "failures", "errors", "skipped")
	}
	if counts["tests"] <= 0 or any(counts[key] for key in ("failures", "errors")):
		raise ValueError(f"Official NVDA tests failed or empty: {counts}")
	if len(list(root.iter("testcase"))) != counts["tests"]:
		raise ValueError("XML test count does not match actual cases")
	if any(next(root.iter(tag), None) is not None for tag in ("failure", "error")):
		raise ValueError("XML includes an unsuccessful case despite suite counters")
	skips, upstream_skips = [], []
	for case in root.iter("testcase"):
		for skipped in case.findall("skipped"):
			identifier = f"{case.get('classname')}.{case.get('name')}"
			reason = skipped.get("message", "")
			if nvda_version == "2026.3beta2" and identifier in _BETA_BLE_TESTS and reason == _BETA_BLE_REASON:
				upstream_skips.append({"test": identifier, "reason": reason})
				continue
			if not (
				allow_external_screen_effect
				and identifier == SCREEN_EFFECT_TEST
				and "Full screen colour effect set external to tests." in reason
			):
				raise ValueError(f"Unapproved skipped NVDA test: {identifier}: {reason}")
			skips.append({"test": identifier, "reason": reason})
	if len(skips) + len(upstream_skips) != counts["skipped"] or len(skips) > 1:
		raise ValueError("XML skip counters or approved environment skip count do not match")
	if len(upstream_skips) != len({item["test"] for item in upstream_skips}):
		raise ValueError("Duplicate upstream skipped case")
	return {
		**counts,
		"passed": counts["tests"] - counts["skipped"],
		"environmentalSkips": skips,
		"upstreamUnimplementedSkips": upstream_skips,
	}


def validate_hashes(root: Path, hashes: dict[str, str]) -> None:
	if not hashes:
		raise ValueError("No source hashes in evidence")
	for relative, expected in hashes.items():
		path = (root / relative).resolve()
		if not path.is_relative_to(root.resolve()) or sha256(path) != expected:
			raise ValueError(f"Stale/out-of-scope evidence: {relative}")


def validate_performance(report: dict) -> None:
	# Loose batch-median guardrails detect order-of-magnitude regressions on CI;
	# these are NOT end-to-end latency promises or per-call percentiles.
	budgets_us = {
		"pluginFilterWithStubs_shortNoCandidate": 100,
		"pluginFilterWithStubs_shortP0Hit": 200,
		"pluginFilterWithStubs_shortP1Hit": 200,
		"pluginFilterWithStubs_shortBoundarySoup": 200,
		"pluginFilterWithStubs_shortBoundaryRow": 200,
		"pluginFilterWithStubs_shortIndefiniteRows": 200,
		"pluginFilterWithStubs_shortFastenMeasure": 200,
		"pluginFilterWithStubs_shortToolMeasure": 200,
		"pluginFilterWithStubs_shortWeightedOverlap": 200,
		"pluginFilterWithStubs_shortSyntaxFood": 200,
		"pluginFilterWithStubs_shortSyntaxOwner": 200,
		"pluginFilterWithStubs_shortSyntaxLiquid": 200,
		"pluginFilterWithStubs_shortSyntaxQuantity": 200,
		"pluginFilterWithStubs_shortCrossingDefault": 200,
		"pluginFilterWithStubs_shortSentencePair": 200,
		"pluginFilterWithStubs_shortSentenceRepeated": 200,
		"pluginFilterWithStubs_shortLexiconMusic": 200,
		"pluginFilterWithStubs_shortLexiconAmbiguous": 200,
		"longSparseHits8k": 10_000,
		"longDenseHits8k": 30_000,
		"longDenseServing8k": 30_000,
		"longCandidateOnly8k": 30_000,
		"longIndefiniteRows8k": 30_000,
		"longLexiconDense8k": 30_000,
		"longWeightedOverlap8k": 30_000,
		"longFastenMeasure8k": 30_000,
		"longToolMeasure8k": 30_000,
		"longSyntaxObjects8k": 30_000,
		"longSyntaxLiquid8k": 30_000,
		"longCrossingDefault8k": 30_000,
		"longMeasureCandidates8k": 30_000,
		"longServingCandidates8k": 30_000,
		"longFastenCandidates8k": 30_000,
		"defaultPlugin_shortNoCandidate": 100,
		"defaultPlugin_shortSentencePair": 200,
		"defaultPlugin_shortLexiconMusic": 200,
		"defaultPlugin_shortIndefiniteRows": 200,
		"defaultPlugin_shortFastenMeasure": 200,
		"defaultPlugin_shortToolMeasure": 200,
		"defaultPlugin_shortSyntaxFood": 200,
		"defaultPlugin_shortSyntaxOwner": 200,
		"defaultPlugin_shortSyntaxLiquid": 200,
		"defaultPlugin_shortSyntaxQuantity": 200,
	}
	for name, budget in budgets_us.items():
		value = report["measurements"][name]["medianMicrosecondsPerCall"]
		if not 0 < value <= budget:
			raise ValueError(f"Performance guardrail exceeded: {name}: {value} us, budget {budget} us")


def validate_grammar_performance(report: dict) -> None:
	for mode in ("default", "extended"):
		rows = report["modes"][mode]["measurements"]
		for name in (
			"repeat",
			"coordinatedModifier",
			"nestedLongModifier",
			"preposedObject",
			"denseRepeat8k",
			"denseObjects8k",
			"denseRelatives8k",
			"candidateOnly8k",
			"adversarialChart8k",
			"reabsorb",
			"spatialEdge",
			"boundaryPipeline",
			"coordinatingActions",
			"multirow",
			"denseSegmentation8k",
			"quantifiedObject",
			"nominalCoordination",
			"ellipticalObject",
			"coordinatedSubject",
			"longCoordinatedSubject",
			"denseContinuations8k",
			"denseNominals8k",
			"adversarialNominals8k",
		):
			row = rows[name]
			budget = 50000 if row["codepoints"] > 1000 else 500
			if row["samples"] < 100 or not 0 < row["medianUs"] <= budget:
				raise ValueError(f"Grammar performance guardrail exceeded: {mode}/{name}: {row}")
