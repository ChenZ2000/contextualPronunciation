"""Per-call grammar latency distribution on fixed, public regression text.

No repeated-result cache is installed. Timings exclude startup, synthesis and
audio-device scheduling. Percentiles are empirical, not latency guarantees.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tests.core_loader import PLUGIN_PATH, load  # noqa: E402
from tests.grammar_cases import STRUCTURES  # noqa: E402


def measure(call, count):
	for _ in range(10):
		call()
	samples = []
	for _ in range(count):
		start = time.perf_counter_ns()
		call()
		samples.append((time.perf_counter_ns() - start) / 1000)
	samples.sort()
	return {
		"samples": count,
		"medianUs": round(statistics.median(samples), 3),
		"p95Us": round(samples[min(count - 1, int(count * 0.95))], 3),
		"p99Us": round(samples[min(count - 1, int(count * 0.99))], 3),
		"maxUs": round(samples[-1], 3),
	}


def run():
	report = {
		"python": platform.python_version(),
		"scope": "Pure reading engine, per-call samples; excludes startup and TTS",
		"modes": {},
	}
	scenarios = {
		"repeat": "请把文件重转一次",
		"reabsorb": "重吸收",
		"spatialEdge": "下边缘",
		"coordinatingActions": "唱和说",
		"multirow": "多行",
		"denseSegmentation8k": "下边缘，唱和说，多行。" * 745,
		"quantifiedObject": "盛了一大碗刚刚煮好而且非常香甜的饭",
		"nominalCoordination": "虾兵和蟹将，天兵和天将",
		"ellipticalObject": "也给我盛了一碗",
		"coordinatedSubject": "天兵和天将一起去吃饭",
		"longCoordinatedSubject": "那些训练有素的士兵和身经百战的将已经安静地吃饭",
		"denseContinuations8k": "也给我盛了一碗，天兵和天将一起去吃饭。" * 440,
		"coordinatedModifier": STRUCTURES[0][0],
		"nestedLongModifier": STRUCTURES[-1][0],
		"preposedObject": "把住在隔壁而且刚上小学的小名的身高再仔细地量一下",
		"denseRepeat8k": "请重转码，然后重编译。" * 750,
		"denseObjects8k": "盛豆角，量小名的身高，" * 740,
		"denseRelatives8k": "盛装液体的容器，" * 1024,
		"candidateOnly8k": "量" * 8192,
		"adversarialChart8k": ("量孩子的" * 128 + "身高") * 16,
		"denseNominals8k": "虾兵和蟹将，天兵和天将。" * 684,
		"adversarialNominals8k": ("一位孩子的" * 80 + "将。") * 21,
	}
	for extended in (False, True):
		start = time.perf_counter()
		rules = load("rules").load_default_rules(extended=extended)
		build_ms = (time.perf_counter() - start) * 1000
		pipeline = load("pipeline")
		options = pipeline.RuntimeOptions()
		normalizer = pipeline.SpeechSequenceNormalizer(
			rules=rules, character_mode_command_type=type("Spelling", (), {})
		)
		guard = pipeline.FailOpenSpeechFilter(normalizer=normalizer, options_provider=lambda options=options: options)

		def full_boundary_pipeline(normalizer=normalizer, guard=guard, options=options):
			sequence = normalizer.normalize(["下边缘，唱和说，多行"], options=options)
			guard.guard_queued_readings(sequence)
			return sequence

		report["modes"]["extended" if extended else "default"] = {
			"buildMsInThisProcess": round(build_ms, 3),
			"measurements": {
				"boundaryPipeline": {
					"codepoints": len("下边缘，唱和说，多行"),
					**measure(full_boundary_pipeline, 1000),
				},
				**{
					name: {
						"codepoints": len(text),
						**measure(
							lambda text=text, rules=rules: rules.transform(text), 100 if len(text) > 1000 else 1000
						),
					}
					for name, text in scenarios.items()
				},
			},
		}
	report["sourceSha256"] = {
		p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
		for p in sorted(PLUGIN_PATH.rglob("*"))
		if p.suffix in {".py", ".json", ".toml"}
	}
	return report


if __name__ == "__main__":
	parser = argparse.ArgumentParser(description=__doc__)
	parser.add_argument("--output", type=Path, default=ROOT / "artifacts/grammar-performance.json")
	args = parser.parse_args()
	report = run()
	args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", "utf-8")
	for mode, result in report["modes"].items():
		print(mode, result["measurements"])
