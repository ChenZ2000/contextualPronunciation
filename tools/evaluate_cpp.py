"""Honest coverage/conditional-accuracy audit on the public CPP test partition.

No training, model unpickling or target-specific adjustments. Dataset labels
are not linguistic truth; this is not comparable to a forced-choice neural
model's accuracy. Absent/protected decisions count as abstentions, NOT correct.
"""

from __future__ import annotations

import copy
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.prepare_cpp import COMMIT, CPP, HASHES, prepare  # noqa: E402
from scripts.run_tests import source_hashes  # noqa: E402
from tests.core_loader import load  # noqa: E402


def evaluate() -> dict:
	prepare(download=False)
	rules = load("rules").load_default_rules()
	# Fixed ablation on the same resource set. Never mutate the cached model
	# or use held-out differences to fit thresholds/rules.
	baseline = copy.copy(rules)
	baseline._lexicon = copy.copy(rules.lexicon)
	baseline.lexicon._adjudicator = None
	labels = (CPP / "data/test.lb").read_text("utf-8").splitlines()
	sentences = (CPP / "data/test.sent").read_text("utf-8").splitlines()
	counts, speech = Counter(), Counter()
	ablation, weighted, weighted_speech = Counter(), Counter(), Counter()
	by_reading, disagreements = defaultdict(Counter), []
	for number, (marked, expected) in enumerate(zip(sentences, labels, strict=True), 1):
		parts = marked.split("▁")
		if len(parts) != 3 or len(parts[1]) != 1:
			raise ValueError(f"Unexpected CPP annotation at line {number}")
		text, position = "".join(parts), len(parts[0])
		decision = rules.resolve(text).get(position)
		actual = decision.reading_id if decision and not decision.protect else None
		status = "abstained" if actual is None else "matchedLabel" if actual == expected else "disagreedWithLabel"
		counts[status] += 1
		base_decision = baseline.resolve(text).get(position)
		base_reading = base_decision.reading_id if base_decision and not base_decision.protect else None
		ablation[
			"abstained"
			if base_reading is None
			else "matchedLabel"
			if base_reading == expected
			else "disagreedWithLabel"
		] += 1
		if actual is not None and decision and "[unigram-margin]" in decision.rule_id:
			weighted[status] += 1
			if decision.speech and actual in rules.renderings:
				weighted_speech[status] += 1
		by_reading[f"{parts[1]}:{expected}"][status] += 1
		if actual and decision.speech and actual in rules.renderings:
			speech[status] += 1
		if status == "disagreedWithLabel":
			disagreements.append(
				{
					"line": number,
					"character": parts[1],
					"expected": expected,
					"actual": actual,
					"rule": decision.rule_id,
				}
			)
	decided = counts["matchedLabel"] + counts["disagreedWithLabel"]
	return {
		"dataset": "CPP test (g2pM, Park and Lee, Interspeech 2020)",
		"commit": COMMIT,
		"dataSha256": HASHES,
		"sourceSha256": source_hashes(),
		"samples": len(sentences),
		"counts": dict(counts),
		"decisionCoveragePercent": round(100 * decided / len(sentences), 3),
		"labelAgreementOnDecisionsPercent": round(100 * counts["matchedLabel"] / decided, 3) if decided else None,
		"speechSubstitutionCounts": dict(speech),
		"sameResourcesBidirectionalOnlyAblation": dict(ablation),
		"weightedAdjudicationDecisions": dict(weighted),
		"weightedSpeechDecisions": dict(weighted_speech),
		"byTargetReading": {key: dict(value) for key, value in sorted(by_reading.items())},
		"disagreements": disagreements,
		"limitations": [
			"No held-out labels used to train or customize rules",
			"No acoustic evaluation",
			"Abstentions are NOT counted as correct",
			"CPP label/region errors may exist",
			"Lexical resource overlap with benchmark vocabulary is possible",
			"This is not an all-context or forced-choice accuracy measure",
		],
	}


if __name__ == "__main__":
	report = evaluate()
	output = ROOT / "artifacts/cpp-evaluation.json"
	output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", "utf-8")
	print(
		json.dumps(
			{
				key: value
				for key, value in report.items()
				if key not in {"sourceSha256", "disagreements", "byTargetReading"}
			},
			ensure_ascii=False,
			indent=2,
		)
	)
