"""Expand the concise P1 polyphone matrix into probe_vocalizer_expressive2 cases."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MATRIX = ROOT / "tests" / "fixtures" / "vocalizer_expressive2" / "p1_polyphone_matrix.json"
DEFAULT_OUTPUT = ROOT / "artifacts" / "p1_polyphone_renderer_cases.generated.json"


def generate(matrix: dict) -> dict:
	cases: list[dict] = []
	for entry in matrix["entries"]:
		entry_id = entry["id"]
		character = entry["character"]
		readings = entry["readings"]
		if len(character) != 1:
			raise ValueError(f"{entry_id}: character must have length one")
		for expected in readings:
			for phrase in expected["phrases"]:
				text = phrase["text"]
				if text.count(character) != 1:
					raise ValueError(
						f"{entry_id}/{phrase['id']}: expected exactly one {character!r} in {text!r}",
					)
				index = text.index(character)
				group = f"p1_{entry_id}_{phrase['id']}"
				base = {
					"entryId": entry_id,
					"character": character,
					"phraseId": phrase["id"],
					"compareGroup": group,
					"targetCharIndex": index,
				}
				cases.append(
					{
						**base,
						"id": f"{group}_source",
						"text": text,
						"role": "source",
						"expectedReadingId": expected["id"],
						"expectedReading": expected["display"],
					},
				)
				for anchor_reading in readings:
					anchor = anchor_reading["anchor"]
					if len(anchor) != 1:
						raise ValueError(f"{entry_id}/{anchor_reading['id']}: anchor must have length one")
					anchor_overrides = phrase.get("anchorOverrides", {})
					anchor_text = anchor_overrides.get(
						anchor_reading["id"],
						text[:index] + anchor + text[index + 1 :],
					)
					if len(anchor_text) != len(text):
						raise ValueError(
							f"{entry_id}/{phrase['id']}: anchor override must preserve text length",
						)
					cases.append(
						{
							**base,
							"id": f"{group}_anchor_{anchor_reading['id']}",
							"text": anchor_text,
							"role": "anchor",
							"anchorReadingId": anchor_reading["id"],
							"expectedReading": anchor_reading["display"],
							"rendererCandidate": anchor,
							"anchorConfidence": anchor_reading["anchorConfidence"],
							"anchorTextOverride": anchor_reading["id"] in anchor_overrides,
						},
					)
	return {
		"schemaVersion": 1,
		"generatedFrom": "tests/fixtures/vocalizer_expressive2/p1_polyphone_matrix.json",
		"purpose": matrix["purpose"],
		"method": matrix["method"],
		"limitations": matrix["limitations"],
		"cases": cases,
	}


def main() -> int:
	parser = argparse.ArgumentParser(description=__doc__)
	parser.add_argument("--matrix", type=Path, default=DEFAULT_MATRIX)
	parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
	args = parser.parse_args()
	matrix = json.loads(args.matrix.read_text(encoding="utf-8"))
	fixture = generate(matrix)
	args.output.parent.mkdir(parents=True, exist_ok=True)
	args.output.write_text(json.dumps(fixture, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
	print(f"generated {len(fixture['cases'])} cases: {args.output}")
	return 0


if __name__ == "__main__":
	raise SystemExit(main())
