"""Development-only comparison; never imports a model into NVDA or user documents."""

from __future__ import annotations

import hashlib
import json
import os
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODEL = ROOT / "vendor/g2pM-model-review"


def main():
	# Pin verified source and weights before the upstream pickle loader executes.
	import subprocess

	commit = subprocess.check_output(["git", "-C", str(MODEL), "rev-parse", "HEAD"], text=True).strip()
	if commit != "170526efad0a3ef9b55a9ad4579f73218f9be06c":
		raise ValueError("Unreviewed model revision")
	if subprocess.check_output(["git", "-C", str(MODEL), "status", "--porcelain", "--untracked-files=no"]):
		raise ValueError("Modified upstream model")
	os.environ["OPENBLAS_NUM_THREADS"] = "1"
	sys.path.insert(0, str(MODEL))
	started = time.perf_counter()
	from g2pM import G2pM

	model = G2pM()
	cold_ms = (time.perf_counter() - started) * 1000
	sentences = (
		"盛豆角",
		"盛红豆粥",
		"量小名的身高",
		"给孩子盛刚煮好的红豆粥",
		"请量住在隔壁的小名的身高",
		"我给孩子盛汤之后盛饭",
		"请商量小名的身高问题",
		"盛先生量了小名的身高",
	)
	results = []
	for text in sentences:
		model(text, char_split=True)
		samples = []
		for _ in range(50):
			started = time.perf_counter_ns()
			readings = model(text, char_split=True)
			samples.append((time.perf_counter_ns() - started) / 1000)
		results.append(
			{"text": text, "readings": readings, "medianUs": statistics.median(samples), "maxUs": max(samples)}
		)
	report = {
		"source": "https://github.com/kakaobrain/g2pM",
		"commit": commit,
		"numpy": __import__("numpy").__version__,
		"coldImportAndLoadMs": cold_ms,
		"method": "50 individual warm calls; fixed development probes, not an accuracy benchmark; one BLAS thread",
		"results": results,
		"weightsSha256": {
			p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((MODEL / "g2pM").glob("*.pkl"))
		},
	}
	path = ROOT / "artifacts/g2pm-design-review.json"
	path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", "utf-8")
	print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
	main()
