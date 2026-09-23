"""Create a broad, offline-only multireading candidate index from Unicode 17.

This is NOT an error list or a normative modern-Mandarin dictionary. It includes
rare, historical, regional and variant readings; no generated entry is enabled.
"""

from __future__ import annotations

import hashlib
import json
import unicodedata
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "artifacts/Unihan/Unihan_Readings.txt"
OUTPUT = ROOT / "data/unihan_polyphone_candidates.json"


def extract(lines) -> list[dict]:
	readings = defaultdict(set)
	fields = defaultdict(dict)
	for line in lines:
		if line.startswith("#") or not line.strip():
			continue
		codepoint, field, value = line.rstrip("\r\n").split("\t", 2)
		if field == "kMandarin":
			values = value.split()
		elif field == "kHanyuPinyin":
			values = [pinyin for group in value.split() for pinyin in group.partition(":")[2].split(",")]
		else:
			continue
		readings[codepoint].update(unicodedata.normalize("NFC", text) for text in values if text)
		fields[codepoint][field] = value
	return [
		{
			"codepoint": codepoint,
			"character": chr(int(codepoint[2:], 16)),
			"candidateReadings": sorted(values),
			"sourceFields": fields[codepoint],
			"status": "unreviewed_not_an_engine_error",
			"defaultEnabled": False,
		}
		for codepoint, values in sorted(readings.items(), key=lambda item: int(item[0][2:], 16))
		if len(values) > 1
	]


def main() -> int:
	with SOURCE.open("r", encoding="utf-8") as stream:
		items = extract(stream)
	report = {
		"schemaVersion": 1,
		"unicodeVersion": "17.0.0",
		"source": "https://www.unicode.org/Public/17.0.0/ucd/Unihan.zip",
		"documentation": "https://www.unicode.org/reports/tr38/tr38-38.html",
		"license": "UNICODE-LICENSE.txt",
		"sourceSha256": hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
		"method": (
			"Union of kMandarin and kHanyuPinyin readings, NFC normalized; retain more than one distinct reading."
		),
		"warning": (
			"Not a list of modern Mandarin pronunciation errors. Includes historical/rare/regional variants; "
			"not all Chinese characters have these fields. Never imported by the runtime plugin."
		),
		"candidateCount": len(items),
		"items": items,
	}
	OUTPUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
	print(f"{len(items)} broad candidates (all disabled): {OUTPUT}")
	return 0


if __name__ == "__main__":
	raise SystemExit(main())
