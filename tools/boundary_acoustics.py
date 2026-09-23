"""Generate and audit fixed boundary cases through rules + NVDA symbols + offline VE.

NVDA's actual SpeechSymbolProcessor is loaded by an isolated test adapter; these
tools never read the user's pronunciation dictionaries or play audio.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
FIXTURE = ROOT / "tests/fixtures/vocalizer_expressive2/boundary_regression.json"
REPORT = ROOT / "artifacts/boundary-ting-ting/report.json"


def sha256(path: Path) -> str:
	return hashlib.sha256(path.read_bytes()).hexdigest()


def build_fixture() -> dict:
	from tests.core_loader import PLUGIN_PATH, load
	from tests.test_nvda_symbol_integration import NVDASymbolDictionaryIntegrationTests
	from tests.test_pipeline import CharacterModeCommand

	NVDASymbolDictionaryIntegrationTests.setUpClass()
	harness = NVDASymbolDictionaryIntegrationTests()
	processor = harness._processor("zh_CN")
	pipeline = load("pipeline")
	normalizer = pipeline.SpeechSequenceNormalizer(
		rules=load("rules").load_default_rules(),
		character_mode_command_type=CharacterModeCommand,
	)
	options = pipeline.RuntimeOptions()
	cases, groups = [], []
	# Exhaustive Unicode coverage is in fast unit tests. Audio samples cover the
	# reported characters, each Symbol subcategory, fullwidths and other rules.
	inputs = [("soup", "盛汤" + symbol, "呈", "乘") for symbol in "|$^+=<>`~￥＋＜｜×→★😀"]
	inputs.extend(
		(name, text, rendering, anchor)
		for name, text, rendering, anchor in (
			("rowOrdinal", "第12行$", "航", "杭"),
			("rowCount", "12行|", "航", "杭"),
			("rank", "行二~", "航", "杭"),
			("rowLabel", "$行 12|", "航", "杭"),
			("repeat", "重复^", "崇", "虫"),
			("popup", "弹窗+", "谈", "坛"),
			("breath", "屏住呼吸=", "丙", "饼"),
		)
	)
	for i, (name, source, rendering, anchor) in enumerate(inputs):
		transformed = normalizer.normalize([source], options=options)[0]
		if transformed == source or transformed.count(rendering) != 1:
			raise ValueError(f"Missing/ambiguous expected rewrite in {source!r}")
		anchor_text = transformed.replace(rendering, anchor)
		for level_name in ("RAW", "NONE", "SOME", "MOST", "ALL"):
			group_id = f"boundary_{i:02d}_{name}_{level_name.lower()}"
			texts = (source, transformed, anchor_text)
			if level_name != "RAW":
				level = getattr(harness.character_processing.SymbolLevel, level_name)
				texts = tuple(processor.processText(text, level).strip() for text in texts)
			for role, text in zip(("source", "transformed", "anchor"), texts, strict=True):
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
					"sourceBeforeSymbols": source,
					"transformedBeforeSymbols": transformed,
					"symbolLevel": level_name,
				}
			)
	paths = [
		*PLUGIN_PATH.glob("*.py"),
		*(PLUGIN_PATH / "data").glob("*.json"),
		*(PLUGIN_PATH / "data").glob("*.toml"),
		ROOT / "vendor/nvda-2026.2/source/characterProcessing.py",
		ROOT / "vendor/nvda-2026.2/source/locale/zh_CN/symbols.dic",
		ROOT / "vendor/nvda-2026.2/source/locale/en/symbols.dic",
		ROOT / "addon/locale/zh_CN/symbols-lexicalApostrophe.dic",
		ROOT / "addon/locale/en/symbols-lexicalApostrophe.dic",
		Path(__file__).resolve(),
	]
	return {
		"schemaVersion": 1,
		"purpose": "0.1.1 Unicode boundary regression through NVDA symbols and VE",
		"sourceSha256": {p.relative_to(ROOT).as_posix(): sha256(p) for p in sorted(paths)},
		"groups": groups,
		"cases": cases,
	}


def summarize(fixture: dict, report: dict) -> dict:
	if fixture != build_fixture():
		raise ValueError("Boundary fixture is stale; regenerate it first")
	if report["fixtureMetadata"]["sourceSha256"] != fixture["sourceSha256"]:
		raise ValueError("Boundary acoustic report is stale; rerun offline VE rendering")
	cases = {item["id"]: item for item in report["cases"]}
	if len(cases) != len(fixture["cases"]) or len(cases) != len(report["cases"]):
		raise ValueError("Missing or duplicated rendered boundary cases")
	for expected in fixture["cases"]:
		actual = cases[expected["id"]]
		if actual["text"] != expected["text"] or actual["pcmBytes"] <= 0 or not actual["allPhonemes"]:
			raise ValueError(f"Empty or mismatched rendered case: {expected['id']}")
	results = []
	for group in fixture["groups"]:
		transformed = cases[group["id"] + "_transformed"]
		anchor = cases[group["id"] + "_anchor"]
		results.append(
			{
				**group,
				"phonemesEqual": transformed["allPhonemes"] == anchor["allPhonemes"],
				"pcmEqual": transformed["pcmSha256"] == anchor["pcmSha256"],
			}
		)
	return {
		"passed": all(item["phonemesEqual"] and item["pcmEqual"] for item in results),
		"groups": len(results),
		"cases": len(cases),
		"phonemeMatches": sum(item["phonemesEqual"] for item in results),
		"pcmMatches": sum(item["pcmEqual"] for item in results),
		"voice": report["voice"],
		"engineVersion": report["engineProductVersion"],
		"sourceSha256": fixture["sourceSha256"],
		"reportSha256": sha256(REPORT),
		"humanListeningCompleted": False,
		"limitations": (
			"Same-run full PCM/phoneme equality with common homophone anchors; "
			"not universal voice/Word UI certification."
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
