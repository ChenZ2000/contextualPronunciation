"""Compile pinned cppjieba unigram counts, not pronunciation or neural weights.

Keep only words in our pronunciation lattice plus single-character backoff.
POS tags are deliberately not treated as a context-sensitive POS prediction.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data/sources/cppjieba-b3602bef-dict.txt"
SHA256 = "2eed8a617b330a0d1117f78312f122d37373cd9db29b5515ca5098fcfa608de7"
COMMIT = "b3602bef7d1f67521a61788a74fb5801a0e62cd3"
DATA = ROOT / "addon/globalPlugins/contextualPronunciation/data"


def generate() -> bytes:
	content = SOURCE.read_bytes()
	if hashlib.sha256(content).hexdigest() != SHA256:
		raise ValueError("Unreviewed cppjieba frequency snapshot")
	words = json.loads((DATA / "lexicon_zh_CN.json").read_text("utf-8"))["words"]
	counts, total, rows = {}, 0, 0
	for line in content.decode("utf-8").splitlines():
		word, raw, _tag = line.split()
		frequency = int(raw)
		if frequency < 0:
			raise ValueError("Negative frequency")
		total += frequency
		rows += 1
		if frequency and (len(word) == 1 or word in words):
			# Dictionary duplicate handling is explicit and order-independent.
			counts[word] = max(frequency, counts.get(word, 0))
	return (
		json.dumps(
			{
				"schemaVersion": 1,
				"source": {
					"url": f"https://github.com/yanyiwu/cppjieba/tree/{COMMIT}",
					"commit": COMMIT,
					"sha256": SHA256,
					"license": "CPPJIEBA-LICENSE.txt",
					"rows": rows,
					"modification": "Dictionary-intersection counts plus single-character backoff; no POS tags",
				},
				"totalFrequency": total,
				"frequencies": dict(sorted(counts.items())),
			},
			ensure_ascii=False,
			separators=(",", ":"),
		)
		+ "\n"
	).encode()


if __name__ == "__main__":
	parser = argparse.ArgumentParser(description=__doc__)
	parser.add_argument("--check", action="store_true")
	args = parser.parse_args()
	content = generate()
	output = DATA / "segmentation_zh_CN.json"
	if args.check:
		if output.read_bytes() != content:
			raise ValueError("Stale segmentation data")
	else:
		output.write_bytes(content)
	print(f"Verified {len(json.loads(content)['frequencies'])} unigram counts")
