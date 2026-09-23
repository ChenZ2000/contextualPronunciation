"""Independent sentence oracles -> actual normalizer/NVDA symbols -> offline VE.

Includes the old delimiter policy as a control, never as the expected result.
This program does not play audio or read an installed NVDA user profile.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.evidence import sha256  # noqa: E402
from tests.sentence_cases import SENTENCE_CASES, SERVING_PHRASES  # noqa: E402

FIXTURE = ROOT / "tests/fixtures/vocalizer_expressive2/sentence_regression.json"
REPORT = ROOT / "artifacts/sentence-ting-ting/report.json"


def build_fixture() -> dict:
	from tests.core_loader import PLUGIN_PATH, load
	from tests.test_nvda_symbol_integration import NVDASymbolDictionaryIntegrationTests
	from tests.test_pipeline import CharacterModeCommand

	NVDASymbolDictionaryIntegrationTests.setUpClass()
	harness = NVDASymbolDictionaryIntegrationTests()
	processor = harness._processor("zh_CN")
	rules = load("rules")
	pipeline = load("pipeline")
	normalizer = pipeline.SpeechSequenceNormalizer(
		rules=rules.load_default_rules(),
		character_mode_command_type=CharacterModeCommand,
	)
	data = json.loads((PLUGIN_PATH / "data/rules_zh_CN.json").read_text("utf-8"))
	next(g for g in data["characters"]["盛"]["phraseGroups"] if g["id"] == "cheng-serving-object-bounded")[
		"rightBoundary"
	] = True
	old_policy = rules.CompiledRules.from_mapping(data)
	inputs = (
		*SENTENCE_CASES,
		*(("我来" + phrase + "之后就离开", "我来呈" + phrase[1:] + "之后就离开") for phrase in SERVING_PHRASES),
	)
	cases, groups = [], []
	for index, (source, expected) in enumerate(inputs):
		actual = normalizer.normalize(
			[source],
			options=pipeline.RuntimeOptions(),
		)[0]
		if actual != expected or actual == source or len(actual) != len(source):
			raise ValueError(f"Sentence oracle mismatch: {source!r}: {actual!r} != {expected!r}")
		changed = [i for i, (before, after) in enumerate(zip(source, expected, strict=True)) if before != after]
		if any(source[i] != "盛" or expected[i] != "呈" for i in changed):
			raise ValueError("This acoustic fixture must change only explicit cheng2 targets")
		anchor_chars = list(expected)
		for i in changed:
			anchor_chars[i] = "乘"
		anchor = "".join(anchor_chars)
		legacy = old_policy.transform(source)
		for level_name in ("RAW", "NONE", "SOME", "MOST", "ALL"):
			group_id = f"sentence_{index:02d}_{level_name.lower()}"
			texts = (source, legacy, actual, anchor)
			if level_name != "RAW":
				level = getattr(harness.character_processing.SymbolLevel, level_name)
				texts = tuple(processor.processText(text, level).strip() for text in texts)
			for role, text in zip(("source", "old_policy", "transformed", "anchor"), texts, strict=True):
				cases.append(
					{
						"id": f"{group_id}_{role}",
						"text": text,
						"role": role,
						"compareGroup": group_id,
						"anchorConfidence": "common",
					}
				)
			groups.append(
				{
					"id": group_id,
					"source": source,
					"expectedBeforeSymbols": expected,
					"oldPolicyBeforeSymbols": legacy,
					"targetIndices": changed,
					"expectedReading": "chéng",
					"symbolLevel": level_name,
				}
			)
	paths = [
		*PLUGIN_PATH.glob("*.py"),
		*(PLUGIN_PATH / "data").glob("*.json"),
		*(PLUGIN_PATH / "data").glob("*.toml"),
		ROOT / "tests/sentence_cases.py",
		ROOT / "tests/test_nvda_symbol_integration.py",
		ROOT / "vendor/nvda-2026.2/source/characterProcessing.py",
		ROOT / "vendor/nvda-2026.2/source/locale/zh_CN/symbols.dic",
		ROOT / "vendor/nvda-2026.2/source/locale/en/symbols.dic",
		ROOT / "addon/locale/zh_CN/symbols-lexicalApostrophe.dic",
		ROOT / "addon/locale/en/symbols-lexicalApostrophe.dic",
		Path(__file__).resolve(),
	]
	return {
		"schemaVersion": 1,
		"purpose": "0.1.2 sentence-position regression with independent text oracles and an old-policy control",
		"sourceSha256": {p.relative_to(ROOT).as_posix(): sha256(p) for p in sorted(paths)},
		"groups": groups,
		"cases": cases,
	}


def summarize(fixture: dict, report: dict) -> dict:
	if fixture != build_fixture():
		raise ValueError("Sentence fixture is stale; regenerate it")
	if report["fixtureMetadata"]["sourceSha256"] != fixture["sourceSha256"]:
		raise ValueError("Sentence audio report is stale; rerun offline VE")
	cases = {item["id"]: item for item in report["cases"]}
	if len(cases) != len(fixture["cases"]) or len(cases) != len(report["cases"]):
		raise ValueError("Missing or duplicate rendered sentence cases")
	for expected in fixture["cases"]:
		actual = cases[expected["id"]]
		if actual["text"] != expected["text"] or actual["pcmBytes"] <= 0 or not actual["allPhonemes"]:
			raise ValueError(f"Empty/mismatched sentence render: {expected['id']}")
	results = []
	for group in fixture["groups"]:
		actual = cases[group["id"] + "_transformed"]
		anchor = cases[group["id"] + "_anchor"]
		old = cases[group["id"] + "_old_policy"]
		results.append(
			{
				**group,
				"phonemesEqual": actual["allPhonemes"] == anchor["allPhonemes"],
				"pcmEqual": actual["pcmSha256"] == anchor["pcmSha256"],
				"oldPolicyPhonemesEqual": old["allPhonemes"] == anchor["allPhonemes"],
				"oldPolicyPcmEqual": old["pcmSha256"] == anchor["pcmSha256"],
			}
		)
	return {
		"passed": all(item["phonemesEqual"] and item["pcmEqual"] for item in results),
		"groups": len(results),
		"cases": len(cases),
		"phonemeMatches": sum(item["phonemesEqual"] for item in results),
		"pcmMatches": sum(item["pcmEqual"] for item in results),
		"oldPolicyPhonemeMatches": sum(item["oldPolicyPhonemesEqual"] for item in results),
		"oldPolicyPcmMatches": sum(item["oldPolicyPcmEqual"] for item in results),
		"voice": report["voice"],
		"engineVersion": report["engineProductVersion"],
		"sourceSha256": fixture["sourceSha256"],
		"reportSha256": sha256(REPORT),
		"humanListeningCompleted": False,
		"limitations": (
			"Same-run full phoneme/PCM homophone-anchor equality; not all voices/contexts/Word UI certification."
		),
		"results": results,
	}


def main() -> int:
	parser = argparse.ArgumentParser(description=__doc__)
	parser.add_argument("action", choices=("generate", "summarize"))
	args = parser.parse_args()
	if args.action == "generate":
		fixture = build_fixture()
		FIXTURE.write_text(json.dumps(fixture, ensure_ascii=False, indent=2) + "\n", "utf-8")
		print(f"{len(fixture['groups'])} groups / {len(fixture['cases'])} cases: {FIXTURE}")
		return 0
	summary = summarize(json.loads(FIXTURE.read_text("utf-8")), json.loads(REPORT.read_text("utf-8")))
	(REPORT.parent / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", "utf-8")
	print(
		json.dumps(
			{key: value for key, value in summary.items() if key not in {"results", "sourceSha256"}}, ensure_ascii=False
		)
	)
	return 0 if summary["passed"] else 1


if __name__ == "__main__":
	raise SystemExit(main())
