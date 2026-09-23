"""Audit the user-suggested cc-table reference; NEVER compile it into runtime data.

The upstream document has damaged formatting, typos and a separate attribution.
Extraction is deliberately diagnostic, not a claim to recover every intended
entry. Reproduce after cloning go-cc/cc-table at COMMIT into vendor/cc-table.
Only the local audit report contains extracted claims; vendor/artifacts are not
distributed in either the add-on or its source bundle.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.import_cedict import CEDICT, UNIHAN, numbered, parse_cedict, read_unihan  # noqa: E402

COMMIT = "4585fd963d27cb4311fff92ea6438bdae0089ce3"
RELATIVE = "text/info/duoyinzi/常用多音字表.md"
HEADING = re.compile(r"^\s*\d+\s*[.、]\s*([\u4e00-\u9fff])")
TOKEN = re.compile(r"[A-Za-züÜāáǎàēéěèīíǐìōóǒòūúǔùǖǘǚǜ:]+[1-5]?")
HAN = re.compile(r"[\u4e00-\u9fff]+")


def extract(text: str) -> tuple[list[dict], list[int]]:
	claims, unparsed, target = [], [], None
	for line_number, raw in enumerate(text.splitlines(), 1):
		line = raw.strip().strip("`").strip()
		if not line or line.startswith("http"):
			continue
		if line.startswith("#"):
			target = None
			continue
		if match := HEADING.match(line):
			target, line = match[1], line[match.end() :]
		if target is None or not (match := TOKEN.search(line)):
			unparsed.append(line_number)
			continue
		reading = numbered(match[0])
		# Explanation text is not an example phrase. Multiple reading markers on
		# a single damaged line need manual inspection; never silently merge them.
		rest = re.sub(r"\([^)]*\)|（[^）]*）", " ", line[match.end() :])
		damaged = bool(re.search(r"[①-⑳]", rest))
		examples = HAN.findall(rest)
		claims.append(
			{
				"line": line_number,
				"target": target,
				"rawReading": match[0],
				"reading": reading,
				"examples": examples,
				"damagedLine": damaged,
			}
		)
	return claims, unparsed


def classify(claim: dict, example: str, attested: dict, words: dict) -> str:
	target, reading = claim["target"], claim["reading"]
	if claim["damagedLine"]:
		return "damaged_line_manual_review"
	if example.count(target) != 1:
		return "target_alignment_manual_review"
	if reading is None or reading not in attested.get(target, ()):
		return "reading_not_attested_in_pinned_unihan"
	alternatives = words.get(example)
	if not alternatives:
		return "no_exact_cedict_headword"
	if None in alternatives or len(alternatives) != 1:
		return "cedict_opaque_or_ambiguous"
	values = next(iter(alternatives))
	return "corroborated_candidate_only" if values[example.index(target)] == reading else "cedict_disagreement"


def main() -> int:
	parser = argparse.ArgumentParser(description=__doc__)
	parser.add_argument("--repository", type=Path, default=ROOT / "vendor/cc-table")
	parser.add_argument("--output", type=Path, default=ROOT / "artifacts/cc-table-audit.json")
	args = parser.parse_args()
	commit = subprocess.check_output(["git", "-C", str(args.repository), "rev-parse", "HEAD"], text=True).strip()
	if commit != COMMIT:
		raise ValueError("Unreviewed cc-table revision")
	# Git object bytes avoid platform-dependent checkout CRLF changes.
	content = subprocess.check_output(["git", "-C", str(args.repository), "show", f"{COMMIT}:{RELATIVE}"])
	claims, unparsed = extract(content.decode("utf-8"))
	with gzip.open(UNIHAN, "rt", encoding="utf-8") as stream:
		_, attested, _ = read_unihan(stream)
	with gzip.open(CEDICT, "rt", encoding="utf-8") as stream:
		words, _, _ = parse_cedict(stream)
	counts = Counter()
	for claim in claims:
		claim["checks"] = [{"example": ex, "status": classify(claim, ex, attested, words)} for ex in claim["examples"]]
		counts.update(item["status"] for item in claim["checks"])
	report = {
		"schemaVersion": 1,
		"repository": "https://github.com/go-cc/cc-table",
		"commit": commit,
		"file": RELATIVE,
		"sha256": hashlib.sha256(content).hexdigest(),
		"declaredRepositoryLicense": "MIT",
		"documentAttribution": "http://xh.5156edu.com/page/18317.html",
		"policy": "reference_only_not_imported; upstream attribution unresolved; no automatic typo repair",
		"scope": "machine-extractable claims, not a reconstructed or linguistically verified complete table",
		"uniqueExtractedTargets": len({c["target"] for c in claims}),
		"extractedClaims": len(claims),
		"exampleChecks": dict(sorted(counts.items())),
		"unparsedLines": unparsed,
		"claims": claims,
	}
	args.output.parent.mkdir(parents=True, exist_ok=True)
	args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", "utf-8")
	print(
		json.dumps(
			{k: v for k, v in report.items() if k not in {"claims", "unparsedLines"}}, ensure_ascii=False, indent=2
		)
	)
	return 0


if __name__ == "__main__":
	raise SystemExit(main())
