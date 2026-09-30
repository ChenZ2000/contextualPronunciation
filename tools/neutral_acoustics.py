"""Source-bound Ting-Ting neutral/full and growth tones with SDK Pinyin controls.

Only the offline probe uses SDK markup. Runtime speech remains plain text.
Numeric phoneme markers alone cannot establish Mandarin tone; compare PCM too.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tests.core_loader import PLUGIN_PATH, load  # noqa: E402

FIXTURE = ROOT / "tests/fixtures/vocalizer_expressive2/neutral_regression.json"
REPORT = ROOT / "artifacts/neutral-ting-ting/report.json"

# Independent citation readings; the rival differs only in the target tone.
# Carrier syllables already have the intended zhǎng pronunciation.
CASES = (
	("clipped", "长个", "掌", "ge4", "ge5", ""),
	("clipped_aspect", "长个了", "掌", "ge4", "ge5", "了"),
	("clipped_question", "长个了没？", "掌", "ge4", "ge5", "了没？"),
	("potential", "长不了个", "掌不了", "ge4", "ge5", ""),
	("repeated", "长一长个", "掌一掌", "ge4", "ge5", ""),
	("traditional", "長個", "掌", "ge4", "ge5", ""),
	("classified", "长个东西", "掌", "ge5", "ge4", "东西"),
	("modified", "长个奇怪的东西", "掌", "ge5", "ge4", "奇怪的东西"),
	("growth_location", "树上长个奇怪的东西", "树上", "zhang3", "zhang4", "个奇怪的东西"),
)


def generate():
	rules = load("rules").load_default_rules()
	cases, groups = [], []
	for identifier, source, before, reading, rival, after in CASES:
		spoken = rules.transform(source)
		literal = before + {"ge4": "各", "ge5": "个", "zhang3": "掌"}[reading] + after
		if spoken != literal:
			raise ValueError(f"Rendered text differs from independent oracle: {identifier}: {spoken!r}")
		anchor = before + "\x1b\\toi=pyt\\" + reading + "\x1b\\toi=orth\\" + after
		contrast = before + "\x1b\\toi=pyt\\" + rival + "\x1b\\toi=orth\\" + after
		groups.append({"id": identifier, "source": source, "speechText": spoken, "reading": reading})
		for role, text in (("source", source), ("transformed", spoken), ("anchor", anchor), ("contrast", contrast)):
			cases.append({"id": identifier + "_" + role, "text": text})
	return {
		"schemaVersion": 1,
		"purpose": "Actual plain speech versus SDK tone controls; no all-driver or human-listening certification",
		"generatedFrom": {
			"runtimeSha256": {
				p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
				for p in sorted(PLUGIN_PATH.rglob("*"))
				if p.is_file() and p.suffix in {".py", ".json", ".toml"}
			}
		},
		"groups": groups,
		"cases": cases,
	}


def summarize():
	from scripts.evidence import validate_hashes

	fixture = json.loads(FIXTURE.read_text("utf-8"))
	if fixture != generate():
		raise ValueError("Tone fixture is stale")
	validate_hashes(ROOT, fixture["generatedFrom"]["runtimeSha256"])
	report = json.loads(REPORT.read_text("utf-8"))
	if report["fixtureMetadata"]["generatedFrom"] != fixture["generatedFrom"]:
		raise ValueError("Tone report is stale")
	rows = {row["id"]: row for row in report["cases"]}
	for case in fixture["cases"]:
		if rows[case["id"]]["text"] != case["text"]:
			raise ValueError("Rendered text differs from fixture")
	results = []
	for group in fixture["groups"]:
		prefix = group["id"] + "_"
		a, b, c = (rows[prefix + role] for role in ("transformed", "anchor", "contrast"))
		results.append(
			{
				**group,
				"phonemesEqual": bool(a["allPhonemes"]) and a["allPhonemes"] == b["allPhonemes"],
				"pcmEqual": a["pcmSha256"] == b["pcmSha256"],
				"differsFromCompetingTone": a["pcmSha256"] != c["pcmSha256"],
			}
		)
	summary = {
		"passed": all(r["phonemesEqual"] and r["pcmEqual"] and r["differsFromCompetingTone"] for r in results),
		"groups": len(results),
		"cases": len(rows),
		"humanListeningCompleted": False,
		"results": results,
	}
	(REPORT.parent / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", "utf-8")
	print(json.dumps({k: v for k, v in summary.items() if k != "results"}, ensure_ascii=False))
	return 0 if summary["passed"] else 1


def main():
	parser = argparse.ArgumentParser(description=__doc__)
	parser.add_argument("mode", choices=("generate", "summarize"))
	args = parser.parse_args()
	if args.mode == "summarize":
		return summarize()
	FIXTURE.write_text(json.dumps(generate(), ensure_ascii=False, indent=2) + "\n", "utf-8")
	print(FIXTURE)
	return 0


if __name__ == "__main__":
	raise SystemExit(main())
