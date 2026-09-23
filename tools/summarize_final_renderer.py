"""Audit the current rules' offline Vocalizer rendering and write concise evidence."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
FIXTURE = ROOT / "tests/fixtures/vocalizer_expressive2/final_renderer_regression.json"
REPORT = ROOT / "artifacts/final-renderer-ting-ting/report.json"


def summarize(fixture: dict, report: dict) -> dict:
	from scripts.evidence import validate_hashes
	from tools.generate_final_renderer_fixture import build_fixture

	if fixture != build_fixture():
		raise ValueError("Renderer fixture differs from current source")
	metadata = fixture["generatedFrom"]
	validate_hashes(ROOT, metadata["runtimeSha256"])
	if report["fixtureMetadata"]["generatedFrom"] != metadata:
		raise ValueError("Probe metadata is stale; regenerate the fixture and rerun render")
	for path_key, hash_key in (
		("ruleData", "ruleDataSha256"),
		("ruleEngine", "ruleEngineSha256"),
		("renderer", "rendererSha256"),
	):
		if hashlib.sha256((ROOT / metadata[path_key]).read_bytes()).hexdigest() != metadata[hash_key]:
			raise ValueError(f"Current {path_key} differs from the probed version")
	cases = {case["id"]: case for case in report["cases"]}
	for expected in fixture["cases"]:
		if cases[expected["id"]]["text"] != expected["text"]:
			raise ValueError("Rendered case does not match current fixture")
	results = []
	for item in fixture["transformations"]:
		prefix = item["id"]
		source = cases[f"{prefix}_source"]
		transformed = cases[f"{prefix}_transformed"]
		anchor = cases[f"{prefix}_common_anchor"]
		results.append(
			{
				**item,
				"completePhonemesEqual": bool(transformed["allPhonemes"])
				and transformed["allPhonemes"] == anchor["allPhonemes"],
				"pcmEqual": transformed["pcmSha256"] == anchor["pcmSha256"],
				"sourcePhonemesEqual": source["allPhonemes"] == anchor["allPhonemes"],
				"sourcePcmEqual": source["pcmSha256"] == anchor["pcmSha256"],
			}
		)
	return {
		"schemaVersion": 1,
		"voice": report["voice"],
		"driverVersion": report["manifest"]["version"],
		"engineVersion": report["engineProductVersion"],
		"generatedFrom": metadata,
		"reportSha256": hashlib.sha256(REPORT.read_bytes()).hexdigest(),
		"counts": {
			"groups": len(results),
			"cases": len(cases),
			"defaultGroups": sum(item["strict"] for item in results),
			"optionalGroups": sum(not item["strict"] for item in results),
			"extendedLexiconGroups": sum(item["extended"] for item in results),
			"phonemeMatches": sum(item["completePhonemesEqual"] for item in results),
			"pcmMatches": sum(item["pcmEqual"] for item in results),
		},
		"passed": all(item["completePhonemesEqual"] and item["pcmEqual"] for item in results),
		"humanListeningCompleted": False,
		"limitations": fixture["limitations"],
		"results": results,
	}


def render_markdown(summary: dict) -> str:
	c = summary["counts"]
	lines = [
		"# Ting-Ting 最终 renderer 声学回归",
		"",
		f"结果：{'通过' if summary['passed'] else '存在不一致，需复查'}。"
		f"{c['groups']} 组 / {c['cases']} 条渲染，其中严格模式 {c['defaultGroups']} 组，"
		f"可选读音偏好 {c['optionalGroups']} 组；其中启用扩展词库 {c['extendedLexiconGroups']} 组。",
		f"完整音素序列一致 {c['phonemeMatches']}/{c['groups']}；"
		f"整段 PCM SHA-256 一致 {c['pcmMatches']}/{c['groups']}。",
		"",
		"这些比较证明规则输出与另一枚常用同音同调锚字在本次环境中产生相同的输出；"
		"不等于对未知上下文、所有声库或所有声调的普遍保证。人工听辨尚未完成。"
		"原文音段相同也不独立证明声调正确；原文不相同也可能来自分词/韵律变化。",
		"",
		"| 范围 | 原文 | 插件实际输出 | 同音锚 | 读音 | 音段一致 | PCM 一致 | 原文音段已匹配 |",
		"|---|---|---|---|---|---|---|---|",
	]
	for item in summary["results"]:
		lines.append(
			f"| {'严格' if item['strict'] else '可选偏好'}{'＋扩展词库' if item['extended'] else ''} | "
			f"{item['source']} | {item['transformed']} | "
			f"{item['commonAnchor']} | {item['expectedReading']} | {item['completePhonemesEqual']} | "
			f"{item['pcmEqual']} | {item['sourcePhonemesEqual']} |",
		)
	lines.extend(
		[
			"",
			"## 可复现性与安全",
			"",
			f"驱动 {summary['driverVersion']}；引擎 {summary['engineVersion']}；voice {summary['voice']}。",
			f"规则数据 SHA-256：`{summary['generatedFrom']['ruleDataSha256']}`。",
			f"规则实现 SHA-256：`{summary['generatedFrom']['ruleEngineSha256']}`。",
			f"完整探针报告 SHA-256：`{summary['reportSha256']}`。",
			"",
			"```powershell",
			"python tools/generate_final_renderer_fixture.py",
			"python tools/probe_vocalizer_expressive2.py render --voice Ting-Ting "
			"--fixture tests/fixtures/vocalizer_expressive2/final_renderer_regression.json "
			"--output-dir artifacts/final-renderer-ting-ting --report artifacts/final-renderer-ting-ting/report.json",
			"python tools/summarize_final_renderer.py",
			"```",
			"",
			"探针只在独立进程中接收 PCM 并保存 WAV：不播放音频，不修改 NVDA 配置，不安装插件。"
			"完整报告/WAV 与精简 summary.json 位于 artifacts/final-renderer-ting-ting。",
			"",
		]
	)
	return "\n".join(lines)


def main() -> int:
	summary = summarize(json.loads(FIXTURE.read_text("utf-8")), json.loads(REPORT.read_text("utf-8")))
	(REPORT.parent / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", "utf-8")
	(ROOT / "artifacts/final-renderer-regression-summary.md").write_text(render_markdown(summary), "utf-8")
	print(json.dumps(summary["counts"], ensure_ascii=False))
	return 0 if summary["passed"] else 1


if __name__ == "__main__":
	raise SystemExit(main())
