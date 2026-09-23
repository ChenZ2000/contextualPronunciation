"""Measure the pure-Python speech-filter hot path without loading NVDA."""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import statistics
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tests.core_loader import load  # noqa: E402

pipeline = load("pipeline")
rules_module = load("rules")


class LangChangeCommand:
	def __init__(self, lang: str):
		self.lang = lang


class CharacterModeCommand:
	def __init__(self, state: bool):
		self.state = state


def _measure(callable_, *, iterations: int, rounds: int) -> dict[str, float | int]:
	for _ in range(max(20, iterations // 100)):
		callable_()
	samples: list[float] = []
	for _ in range(rounds):
		start = time.perf_counter_ns()
		for _ in range(iterations):
			callable_()
		elapsed = time.perf_counter_ns() - start
		samples.append(elapsed / iterations / 1_000)
	return {
		"iterationsPerRound": iterations,
		"rounds": rounds,
		"medianMicrosecondsPerCall": round(statistics.median(samples), 4),
		"minimumMicrosecondsPerCall": round(min(samples), 4),
		"maximumMicrosecondsPerCall": round(max(samples), 4),
	}


def run(*, short_iterations: int, long_iterations: int, rounds: int) -> dict[str, object]:
	normalizer = pipeline.SpeechSequenceNormalizer(
		rules=rules_module.load_default_rules(),
		character_mode_command_type=CharacterModeCommand,
	)
	options = pipeline.RuntimeOptions()

	def normalize(sequence: list[object]):
		return normalizer.normalize(sequence, options=options)

	scenarios = {
		"shortNoCandidate": (["普通桌面文本，没有候选。"], short_iterations),
		"shortP0Hit": (["当前行是第12行，下一行盛两碗汤，然后重新加载。"], short_iterations),
		"shortP1Hit": (["打开调试器，弹出窗口，输入私钥并屏住呼吸。"], short_iterations),
		"shortBoundarySoup": (["盛汤$"], short_iterations),
		"shortBoundaryRow": (["$行 12|"], short_iterations),
		"shortIndefiniteRows": (["这几行很好，文字排成竖行。"], short_iterations),
		"shortFastenMeasure": (["请系好安全带之后量一下体温。"], short_iterations),
		"shortToolMeasure": (["系领结并用卷尺重新量一量。"], short_iterations),
		"shortWeightedOverlap": (["我用大调和小调创作。"], short_iterations),
		"shortSyntaxFood": (["盛刚煮好的红豆粥"], short_iterations),
		"shortSyntaxOwner": (["量住在隔壁的小名的身高"], short_iterations),
		"shortSyntaxLiquid": (["盛装液体的容器"], short_iterations),
		"shortSyntaxQuantity": (["盛了半瓶透明液体"], short_iterations),
		"shortCrossingDefault": (["降调音频发给调音师"], short_iterations),
		"shortSentencePair": (["我给孩子盛汤之后盛饭"], short_iterations),
		"shortSentenceRepeated": (["盛饭盛汤很好"], short_iterations),
		"shortLexiconMusic": (["仙乐飘飘，音乐观众很快乐。"], short_iterations),
		"shortLexiconAmbiguous": (["便宜、同行、朝阳；盛面的时候。"], short_iterations),
		"lexicalApostrophes": (["Doesn’t; Mike's; we’ll"], short_iterations),
		"quotesAndPossessive": (["He said ‘hello’; students’ books"], short_iterations),
		"longNoCandidate8k": (["普通桌面文字与数字123。" * 625], long_iterations),
		"longSparseHits8k": ([(("普通桌面文字与数字123。" * 125) + "第12行，盛两碗汤。") * 5], long_iterations),
		"longDenseHits8k": (["行首、重新、盛汤。" * 900], min(long_iterations, 50)),
		"longDenseServing8k": (["盛饭盛汤很好" * 1365], min(long_iterations, 50)),
		"longCandidateOnly8k": (["重" * 8192], min(long_iterations, 50)),
		"longIndefiniteRows8k": (["这几行很好，若干行，竖行。" * 630], min(long_iterations, 50)),
		"longLexiconDense8k": (["仙乐飘飘，音乐观众很快乐。" * 580], min(long_iterations, 50)),
		"longWeightedOverlap8k": (["我用大调和小调创作。" * 800], min(long_iterations, 50)),
		"longFastenMeasure8k": (["系好安全带之后量体温。" * 740], min(long_iterations, 50)),
		"longToolMeasure8k": (["系领结并用卷尺重新量一量。" * 625], min(long_iterations, 50)),
		"longSyntaxObjects8k": (["盛豆角，量小名的身高，" * 740], min(long_iterations, 50)),
		"longSyntaxLiquid8k": (["盛装液体的容器，" * 1024], min(long_iterations, 50)),
		"longCrossingDefault8k": (["降调音频，调音师，" * 910], min(long_iterations, 50)),
		"longMeasureCandidates8k": (["量" * 8192], min(long_iterations, 50)),
		"longServingCandidates8k": (["盛" * 8192], min(long_iterations, 50)),
		"longFastenCandidates8k": (["系" * 8192], min(long_iterations, 50)),
	}
	measurements = {
		name: {
			"inputCodePoints": len(sequence[0]),
			**_measure(lambda sequence=sequence: normalize(sequence), iterations=iterations, rounds=rounds),
		}
		for name, (sequence, iterations) in scenarios.items()
	}
	# Exercise the actual GlobalPlugin and all provider callbacks, with only
	# NVDA/wx replaced by in-memory stubs. Never attach to a running NVDA.
	from tests.test_global_plugin_integration import _load_plugin

	environment = _load_plugin()
	try:
		for name in (
			"shortNoCandidate",
			"shortP0Hit",
			"shortP1Hit",
			"shortBoundarySoup",
			"shortBoundaryRow",
			"shortIndefiniteRows",
			"shortFastenMeasure",
			"shortToolMeasure",
			"shortWeightedOverlap",
			"shortSyntaxFood",
			"shortSyntaxOwner",
			"shortSyntaxLiquid",
			"shortSyntaxQuantity",
			"shortCrossingDefault",
			"shortSentencePair",
			"shortSentenceRepeated",
			"shortLexiconMusic",
			"shortLexiconAmbiguous",
		):
			sequence, iterations = scenarios[name]
			measurements[f"pluginFilterWithStubs_{name}"] = {
				"extendedLexiconEnabled": True,
				"inputCodePoints": len(sequence[0]),
				**_measure(
					lambda sequence=sequence: environment.plugin._speech_filter(sequence),
					iterations=iterations,
					rounds=rounds,
				),
			}
		environment.config.conf["contextualPronunciation"]["extendedLexiconEnabled"] = False
		environment.plugin._reload_configuration()
		for name in (
			"shortNoCandidate",
			"shortSentencePair",
			"shortLexiconMusic",
			"shortIndefiniteRows",
			"shortFastenMeasure",
			"shortToolMeasure",
		):
			sequence, iterations = scenarios[name]
			measurements[f"defaultPlugin_{name}"] = {
				"extendedLexiconEnabled": False,
				"inputCodePoints": len(sequence[0]),
				**_measure(
					lambda sequence=sequence: environment.plugin._speech_filter(sequence),
					iterations=iterations,
					rounds=rounds,
				),
			}
		for name in ("shortSyntaxFood", "shortSyntaxOwner", "shortSyntaxLiquid", "shortSyntaxQuantity"):
			sequence, iterations = scenarios[name]
			measurements[f"defaultPlugin_{name}"] = {
				"extendedLexiconEnabled": False,
				"inputCodePoints": len(sequence[0]),
				**_measure(
					lambda sequence=sequence: environment.plugin._speech_filter(sequence),
					iterations=iterations,
					rounds=rounds,
				),
			}
	finally:
		environment.plugin.terminate()
	return {
		"schemaVersion": 1,
		"measuredAtUtc": datetime.now(UTC).isoformat(),
		"sourceSha256": {
			str(path.relative_to(ROOT)).replace("\\", "/"): hashlib.sha256(path.read_bytes()).hexdigest()
			for path in sorted(
				[
					*((ROOT / "addon/globalPlugins/contextualPronunciation").glob("*.py")),
					*((ROOT / "addon/globalPlugins/contextualPronunciation/data").glob("*.json")),
					*((ROOT / "addon/globalPlugins/contextualPronunciation/data").glob("*.toml")),
				]
			)
		},
		"benchmarkSha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
		"runtime": {
			"python": platform.python_version(),
			"implementation": platform.python_implementation(),
			"platform": platform.platform(),
			"processor": platform.processor(),
		},
		"method": (
			"Broad lexicon enabled except explicitly marked defaultPlugin cases. Legacy NoCandidate names "
			"refer to the old six-character inventory, not an empty candidate set in the broad lexicon. "
			"Median of per-round average wall times, not per-call p99. Normalizer and real plugin filter "
			"with NVDA property stubs. Excludes real NVDA dispatch, COM, IPC, synthesis, audio "
			"and interruption latency."
		),
		"measurements": measurements,
	}


def main() -> int:
	parser = argparse.ArgumentParser()
	parser.add_argument("--short-iterations", type=int, default=10_000)
	parser.add_argument("--long-iterations", type=int, default=200)
	parser.add_argument("--rounds", type=int, default=7)
	parser.add_argument("--output", type=Path)
	args = parser.parse_args()
	if min(args.short_iterations, args.long_iterations, args.rounds) <= 0:
		parser.error("iteration and round counts must be positive")
	report = run(
		short_iterations=args.short_iterations,
		long_iterations=args.long_iterations,
		rounds=args.rounds,
	)
	serialized = json.dumps(report, ensure_ascii=False, indent=2)
	if args.output:
		args.output.parent.mkdir(parents=True, exist_ok=True)
		args.output.write_text(serialized + "\n", encoding="utf-8")
	print(serialized)
	return 0


if __name__ == "__main__":
	raise SystemExit(main())
