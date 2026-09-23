"""Summarize complete-stream P1 Vocalizer comparisons as JSON and Markdown."""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REPORT = ROOT / "artifacts" / "vocalizer-p1-ting-ting" / "report.json"
DEFAULT_JSON = ROOT / "artifacts" / "vocalizer-p1-ting-ting" / "summary.json"
DEFAULT_MARKDOWN = ROOT / "docs" / "Ting-Ting-P1多音字实机探测报告.md"
DEFAULT_CONCISE = ROOT / "data" / "ting_ting_p1_probe_findings.json"


def _index_matrix(matrix: dict[str, Any]) -> tuple[dict[str, dict[str, Any]], dict[tuple[str, str], dict[str, Any]]]:
	entries = {entry["id"]: entry for entry in matrix["entries"]}
	readings = {(entry["id"], reading["id"]): reading for entry in matrix["entries"] for reading in entry["readings"]}
	return entries, readings


def summarize(matrix: dict[str, Any], report: dict[str, Any]) -> dict[str, Any]:
	entries, readings = _index_matrix(matrix)
	groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
	for case in report["cases"]:
		if isinstance(case.get("compareGroup"), str) and case["compareGroup"].startswith("p1_"):
			groups[case["compareGroup"]].append(case)

	results: list[dict[str, Any]] = []
	for _group, members in sorted(groups.items()):
		source = next(member for member in members if member.get("role") == "source")
		anchors = [member for member in members if member.get("role") == "anchor"]
		source_stream = source["allPhonemes"]
		matching = [anchor for anchor in anchors if source_stream and source_stream == anchor["allPhonemes"]]
		matched_ids = sorted({anchor["anchorReadingId"] for anchor in matching})
		expected_id = source["expectedReadingId"]
		entry = entries[source["entryId"]]
		gold_reading = next(
			reading["id"]
			for reading in entry["readings"]
			if any(phrase["id"] == source["phraseId"] for phrase in reading["phrases"])
		)
		if expected_id != gold_reading:
			raise ValueError(f"Stale probe gold label for {source['id']}: regenerate and rerun the fixture")
		expected_anchor = next(anchor for anchor in anchors if anchor["anchorReadingId"] == expected_id)
		expected_meta = readings[(source["entryId"], expected_id)]
		if expected_id in matched_ids and len(matched_ids) > 1:
			# Vocalizer's ``usPhoneme`` stream describes segmental phones but does
			# not encode Mandarin lexical tone.  Anchors such as 钟/众 therefore
			# have the same stream even though their tones differ.  Never turn
			# that collision into a false positive.
			status = "tone_ambiguous"
		elif expected_id in matched_ids:
			status = (
				"correct" if expected_meta["anchorConfidence"] == "common" else "expected_match_experimental_anchor"
			)
		elif matched_ids:
			status = "reading_preference" if entry.get("readingPolicy") == "literary_preference" else "misread"
		else:
			status = "inconclusive"
		results.append(
			{
				"character": source["character"],
				"entryId": source["entryId"],
				"phraseId": source["phraseId"],
				"word": source["text"],
				"expectedReadingId": expected_id,
				"expectedReading": source["expectedReading"],
				"sourceMatchesExpectedAnchor": expected_id in matched_ids,
				"matchedReadingIds": matched_ids,
				"matchedReadings": [readings[(source["entryId"], item)]["display"] for item in matched_ids],
				"status": status,
				"candidateReplacement": expected_anchor["rendererCandidate"],
				"candidateRenderedText": expected_anchor["text"],
				"candidateUsesPhraseOverride": expected_anchor.get("anchorTextOverride", False),
				"candidateAnchorConfidence": expected_anchor["anchorConfidence"],
				"completePhonemeCount": len(source_stream),
			}
		)

	by_character = []
	for entry_id, entry in entries.items():
		members = [item for item in results if item["entryId"] == entry_id]
		counts = Counter(item["status"] for item in members)
		by_character.append(
			{
				"character": entry["character"],
				"entryId": entry_id,
				"total": len(members),
				"correct": counts["correct"],
				"expectedMatchExperimentalAnchor": counts["expected_match_experimental_anchor"],
				"misread": counts["misread"],
				"inconclusive": counts["inconclusive"],
				"toneAmbiguous": counts["tone_ambiguous"],
				"readingPreference": counts["reading_preference"],
				"misreadWords": [item["word"] for item in members if item["status"] == "misread"],
				"inconclusiveWords": [item["word"] for item in members if item["status"] == "inconclusive"],
			}
		)

	counts = Counter(item["status"] for item in results)
	return {
		"schemaVersion": 1,
		"probe": {
			"voice": report["voice"],
			"driverVersion": report["manifest"].get("version"),
			"engineProductVersion": report.get("engineProductVersion"),
			"engineBuild": report.get("engineBuild"),
			"generatedFrom": str(DEFAULT_REPORT.relative_to(ROOT)),
		},
		"decisionRule": (
			"source 与正确同音锚的 complete phoneme stream 完全相等为 correct；"
			"只与其他读音锚相等为 misread；文白读音偏好另标 reading_preference；"
			"多个声调同流为 tone_ambiguous；无匹配为 inconclusive。此判据不独立验证声调。"
		),
		"counts": {
			"characters": len(by_character),
			"phrases": len(results),
			"correct": counts["correct"],
			"expectedMatchExperimentalAnchor": counts["expected_match_experimental_anchor"],
			"misread": counts["misread"],
			"inconclusive": counts["inconclusive"],
			"toneAmbiguous": counts["tone_ambiguous"],
			"readingPreference": counts["reading_preference"],
		},
		"characters": by_character,
		"results": results,
	}


def render_markdown(summary: dict[str, Any]) -> str:
	counts = summary["counts"]
	lines = [
		"# Ting-Ting P1 多音字实机探测报告",
		"",
		f"- Voice：`{summary['probe']['voice']}`",
		f"- Vocalizer Expressive 驱动：`{summary['probe']['driverVersion']}`",
		f"- 引擎：`{summary['probe']['engineProductVersion']}`",
		f"- 覆盖：{counts['characters']} 个多音字、{counts['phrases']} 条原词",
		f"- 判定：正确 {counts['correct']}；明确误读 {counts['misread']}；"
		f"仅声调不可判 {counts['toneAmbiguous']}；"
		f"实验锚命中 {counts['expectedMatchExperimentalAnchor']}；"
		f"文白读音偏好 {counts['readingPreference']}；"
		f"其他无法判定 {counts['inconclusive']}",
		"",
		"判定只使用同一次 Ting-Ting render 的完整 Vocalizer 私有音素流。"
		"`misread` 表示原词完整流与另一读音锚完全相等、且不等于正确锚；"
		"`tone_ambiguous` 表示几个读音只有声调不同，而 `usPhoneme` 不编码声调；"
		"`inconclusive` 不等于误读。最终 renderer 上线前仍应抽听 WAV。",
		"“调试”的金标已复核为 tiáo shì；不是 diào shì，当前引擎在该测试中无需修复。"
		"“密钥/公钥/私钥”的 yuè 列为可选文读音偏好，本报告不将 yào 输出认定为已证实错误。",
		"",
		"## 明确误读",
		"",
		"| 字 | 原词 | 应读 | 实际匹配锚读音 | renderer 候选 | 锚置信度 |",
		"|---|---|---|---|---|---|",
	]
	misreads = [item for item in summary["results"] if item["status"] == "misread"]
	for item in misreads:
		candidate = item["candidateReplacement"]
		if item["candidateAnchorConfidence"] != "common":
			candidate += "（未验证，不可上线）"
		lines.append(
			f"| {item['character']} | {item['word']} | {item['expectedReading']} | "
			f"{', '.join(item['matchedReadings'])} | {candidate} | {item['candidateAnchorConfidence']} |",
		)
	if not misreads:
		lines.append("| — | 本轮没有明确误读 | — | — | — | — |")

	lines.extend(
		[
			"",
			"## 无法自动判定",
			"",
			"| 字 | 原词 | 应读 | renderer 候选 | 原因 |",
			"|---|---|---|---|---|",
		],
	)
	uncertain = [
		item
		for item in summary["results"]
		if item["status"]
		in {
			"inconclusive",
			"expected_match_experimental_anchor",
			"tone_ambiguous",
			"reading_preference",
		}
	]
	for item in uncertain:
		if item["status"] == "tone_ambiguous":
			reason = "音素 ID 不编码声调，多个声调锚同流"
		elif item["status"] == "reading_preference":
			reason = "文白读音偏好，不作为明确误读；严格模式不改写"
		elif item["status"].startswith("expected_match"):
			reason = "实验锚命中，需人工确认锚字本身"
		else:
			reason = "未与任何读音锚完整匹配"
		lines.append(
			f"| {item['character']} | {item['word']} | {item['expectedReading']} | "
			f"{item['candidateReplacement']} | {reason} |",
		)
	if not uncertain:
		lines.append("| — | 无 | — | — | — |")

	lines.extend(
		[
			"",
			"## 按字符汇总",
			"",
			"| 字 | 测试数 | 正确 | 实验锚命中 | 明确误读 | 仅声调不可判 | 文白偏好 | 其他无法判定 | 误读词 |",
			"|---|---:|---:|---:|---:|---:|---:|---:|---|",
		],
	)
	for item in summary["characters"]:
		lines.append(
			f"| {item['character']} | {item['total']} | {item['correct']} | "
			f"{item['expectedMatchExperimentalAnchor']} | {item['misread']} | "
			f"{item['toneAmbiguous']} | {item['readingPreference']} | {item['inconclusive']} | "
			f"{'、'.join(item['misreadWords']) or '—'} |",
		)
	lines.extend(
		[
			"",
			"## 可复现命令",
			"",
			"```powershell",
			"python tools/generate_p1_probe_fixture.py",
			"python tools/probe_vocalizer_expressive2.py render --voice Ting-Ting "
			"--fixture artifacts/p1_polyphone_renderer_cases.generated.json "
			"--output-dir artifacts/vocalizer-p1-ting-ting "
			"--report artifacts/vocalizer-p1-ting-ting/report.json",
			"python tools/summarize_p1_probe.py",
			"```",
			"",
			"完整机器可读逐词结果见 `artifacts/vocalizer-p1-ting-ting/summary.json`；"
			"每个 probe case 的 WAV 和 marker 见同目录。",
			"",
		]
	)
	return "\n".join(lines)


def concise_findings(summary: dict[str, Any]) -> dict[str, Any]:
	"""Keep the auditable findings small enough for renderer/profile review."""
	return {
		"schemaVersion": 1,
		"voice": summary["probe"]["voice"],
		"driverVersion": summary["probe"]["driverVersion"],
		"engineProductVersion": summary["probe"]["engineProductVersion"],
		"scope": {
			"characters": summary["counts"]["characters"],
			"phrases": summary["counts"]["phrases"],
		},
		"markerLimitation": (
			"VE 2.2 usPhoneme 不编码普通话声调；只有声调不同的读音标为 tone_ambiguous，不能据此认定正确或错误。"
		),
		"definiteMisreads": [
			{
				"character": item["character"],
				"word": item["word"],
				"expectedReading": item["expectedReading"],
				"sourceEqualsExpectedAnchor": item["sourceMatchesExpectedAnchor"],
				"sourceEqualsOtherReadingAnchor": True,
				"observedAnchorReadings": item["matchedReadings"],
				"candidateReplacement": item["candidateReplacement"],
				"candidateRenderedText": item["candidateRenderedText"],
				"candidateStatus": (
					"stream_verified_common_anchor"
					if item["candidateAnchorConfidence"] == "common"
					else "not_safe_without_listening"
				),
			}
			for item in summary["results"]
			if item["status"] == "misread"
		],
		"unresolvedCounts": {
			"readingPreference": summary["counts"]["readingPreference"],
			"toneAmbiguous": summary["counts"]["toneAmbiguous"],
			"experimentalAnchorMatches": summary["counts"]["expectedMatchExperimentalAnchor"],
			"otherInconclusive": summary["counts"]["inconclusive"],
		},
		"fullResults": "artifacts/vocalizer-p1-ting-ting/summary.json",
		"humanReport": "docs/Ting-Ting-P1多音字实机探测报告.md",
	}


def main() -> int:
	parser = argparse.ArgumentParser(description=__doc__)
	parser.add_argument(
		"--matrix",
		type=Path,
		default=ROOT / "tests" / "fixtures" / "vocalizer_expressive2" / "p1_polyphone_matrix.json",
	)
	parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
	parser.add_argument("--json", type=Path, default=DEFAULT_JSON)
	parser.add_argument("--markdown", type=Path, default=DEFAULT_MARKDOWN)
	parser.add_argument("--concise", type=Path, default=DEFAULT_CONCISE)
	args = parser.parse_args()
	matrix = json.loads(args.matrix.read_text(encoding="utf-8"))
	report = json.loads(args.report.read_text(encoding="utf-8"))
	summary = summarize(matrix, report)
	args.json.parent.mkdir(parents=True, exist_ok=True)
	args.json.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
	args.markdown.parent.mkdir(parents=True, exist_ok=True)
	args.markdown.write_text(render_markdown(summary), encoding="utf-8")
	args.concise.parent.mkdir(parents=True, exist_ok=True)
	args.concise.write_text(
		json.dumps(concise_findings(summary), ensure_ascii=False, indent=2) + "\n",
		encoding="utf-8",
	)
	print(json.dumps(summary["counts"], ensure_ascii=False))
	print(args.json)
	print(args.markdown)
	print(args.concise)
	return 0


if __name__ == "__main__":
	raise SystemExit(main())
