"""Compile reproducible multi-source lexical evidence for compositional grammar.

POS alternatives are evidence, never sentence labels. English gloss recognition
only adds a verb candidate when a definition explicitly starts with ``to``.
No definition text, neural model or executable source is shipped at runtime.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import re
import tomllib
from collections import defaultdict
from pathlib import Path

if __package__:
	from .build_syntax_data import TAXONOMY, TAXONOMY_SHA256, descendants
else:
	from build_syntax_data import TAXONOMY, TAXONOMY_SHA256, descendants

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "addon/globalPlugins/contextualPronunciation/data"
OUTPUT = DATA / "grammar_lexicon.json"
RECORDS_SHA256 = "42fa9059afa823def37d461d585ad3f35573712a83212e393bf1c0bd19cfd3a8"
HOW_SHA256 = "ef9ccab1ff9c87b31e3dc9b765071b5ecefe9568367eabc5c211e57da1a76ced"
JIEBA_SHA256 = "2eed8a617b330a0d1117f78312f122d37373cd9db29b5515ca5098fcfa608de7"
HAN = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff]{1,16}\Z")
VERB_GLOSS = re.compile(r"^(?:\([^()]*\)\s*)*to [a-z]")
# Definition HEADS, not substring hits ("wheel factory" is not a wheel).
# A rotating sense remains a candidate until the sentence supplies its role.
GLOSS_LABEL = re.compile(r"^(?:\([^()]*\)\s*)*")
PROJECTION_PATH = ROOT / "data/semantic_projection.toml"
TRANSFER_ROOTS = ("fund", "money", "wealth", "letter", "document", "InfoElement", "information", "software")


def projection_rules():
	data = tomllib.loads(PROJECTION_PATH.read_text("utf-8"))
	excluded = re.compile("|".join(data["excludedLabels"]), re.I)
	rules = []
	for family in data["families"]:
		modifiers = "|".join(re.escape(m) for m in family["modifiers"])
		for head in family["heads"]:
			pattern = re.compile(r"^(?:(?:" + modifiers + r") )*" + re.escape(head) + r"(?=$|\s*[;,(])", re.I)
			rules.append((family["id"], pattern, family.get("requires", {}).get(head)))
	return excluded, tuple(rules)


def projection_classes():
	data = tomllib.loads(PROJECTION_PATH.read_text("utf-8"))
	return {family["id"]: family.get("selection", "rotorNoun") for family in data["families"]}


def projected_families(glosses, rules):
	excluded, families = rules
	result = set()
	for gloss in glosses:
		labels = " ".join(re.findall(r"\([^()]*\)", gloss))
		if excluded.search(labels):
			continue
		definition = GLOSS_LABEL.sub("", gloss)
		for name, pattern, required in families:
			if pattern.match(definition) and (required is None or required in gloss):
				result.add(name)
	return result


def argument_classes(pos, kdml):
	"""Project typed senses/roles; a mention inside another sense is insufficient."""
	if pos == "noun":
		if "{rotate|转动:agent={~}" in kdml:
			yield "rotorNoun"
		if any(kdml.startswith("{" + root + "|") for root in TRANSFER_ROOTS) or (
			kdml.startswith("{part|部件")
			and any("whole={" + root + "|" in kdml for root in ("text", "publications", "document"))
		):
			yield "transferTheme"
	if pos == "num" and kdml.startswith(("{many|多", "{few|少", "{some|若干")):
		yield "indefiniteQuantity"
	if pos == "classifier" and kdml.startswith("{ActUnit|动量"):
		yield "actionMeasure"


POS = {"noun": 1, "verb": 2, "adj": 4, "adv": 8, "pron": 16, "prep": 32, "classifier": 64, "det": 128, "num": 256}
# Bits 0..8 = POS alternatives; bits 12..14 = source membership.
HOW, JIEBA, CEDICT = 1 << 12, 1 << 13, 1 << 14


def checked(path, digest):
	content = path.read_bytes()
	if hashlib.sha256(content).hexdigest() != digest:
		raise ValueError(f"Unreviewed grammar source: {path.name}")
	return content


def jieba_pos(tag):
	if tag in {"vn", "an"}:
		return 1 | (2 if tag == "vn" else 4)
	if tag in {"vd", "ad"}:
		return 8 | (2 if tag == "vd" else 4)
	return {"n": 1, "v": 2, "a": 4, "d": 8, "r": 16, "p": 32, "q": 64, "m": 256}.get(tag[0], 0)


def generate():
	projection = projection_rules()
	family_classes = projection_classes()
	taxonomy = checked(TAXONOMY, TAXONOMY_SHA256).decode("utf-8")
	living_roots = descendants(taxonomy, ("plant|植物", "AnimalHuman|动物", "bacteria|微生物")) - {
		"human|人",
		"humanized|拟人",
		"fruit|水果",
		"vegetable|蔬菜",
	}
	derivations = defaultdict(lambda: defaultdict(set))
	words = defaultdict(int)
	selection = defaultdict(set)
	motion_evidence = defaultdict(lambda: defaultdict(list))
	rows = json.loads(gzip.decompress(checked(ROOT / "data/sources/openhownet-core-20210920.json.gz", HOW_SHA256)))[
		"rows"
	]
	for sense_id, word, pos, kdml in rows:
		words[word] |= POS[pos] | HOW
		for name in argument_classes(pos, kdml):
			selection[name].add(word)
			motion_evidence[name][word].append("openhownet:" + str(sense_id))
		if pos == "noun":
			root = kdml[1:].split(":", 1)[0].split("}", 1)[0]
			growth_classes = []
			if root in living_roots or kdml.startswith("{human|人:modifier={child|少儿}"):
				growth_classes.append("grower")
			if root == "part|部件" and "domain={physiology|生理学}" in kdml:
				if "whole={AnimalHuman|动物}" in kdml or "whole={human|人}" in kdml:
					growth_classes.extend(("bodySite", "growthProduct"))
				elif "whole={plant|植物}" in kdml or "whole={vegetable|蔬菜}" in kdml:
					growth_classes.append("growthProduct")
			if root == "Stature|高矮" and "host={human|人}" in kdml:
				growth_classes.append("stature")
			if root == "Age|年龄" and "host={animate|生物}" in kdml:
				growth_classes.append("ageNoun")
			if root == "Unit|单位" and "restrictive={Age|年龄:" in kdml:
				growth_classes.append("ageMeasure")
			for name in growth_classes:
				selection[name].add(word)
				motion_evidence[name][word].append("openhownet:" + str(sense_id))
		# These are argument-type candidates, not a sentence pronunciation.
		# Select the root sense or an explicit location role of this noun;
		# an incidental place mentioned elsewhere in a gloss is insufficient.
		if pos == "noun" and (
			kdml.startswith(("{place|地方", "{InstitutePlace|场所", "{location|位置", "{route|道路", "{house|房屋"))
			or kdml.startswith("{facilities|设施")
			and "location={~}" in kdml
		):
			selection["placeNoun"].add(word)
			motion_evidence["placeNoun"][word].append(sense_id)
		if pos == "verb" and (
			kdml.startswith(
				(
					"{GoOut|出去",
					"{GoIn|进入",
					"{ComeOut|出来",
					"{ComeIn|进来",
					"{GoDown|下去",
					"{GoUp|上去",
					"{ComeDown|下来",
					"{ComeUp|上来",
				)
			)
			or kdml.startswith(("{leave|离开", "{LeaveFor|前往"))
			and any(
				f"{role}={{{kind}|" in kdml
				for role in ("LocationIni", "LocationFin")
				for kind in ("family", "house", "place", "route", "InstitutePlace", "building")
			)
		):
			selection["pathMotion"].add(word)
			motion_evidence["pathMotion"][word].append(sense_id)
		if pos == "verb" and kdml.startswith(("{sing|唱", "{speak|说", "{recite|诵读", "{read|读")):
			selection["speechVerb"].add(word)
		if pos == "classifier":
			if "{put|放置:LocationFin={~}}" in kdml:
				selection["containerMeasure"].add(word)
			if "host={human|人}" in kdml:
				selection["personMeasure"].add(word)
		if pos == "noun":
			if kdml.startswith("{part|部件:PartPosition={edge|边}"):
				selection["edgeNoun"].add(word)
			if kdml.startswith("{human|人:"):
				selection["humanNoun"].add(word)
			if kdml.startswith("{army|军队:") or (kdml.startswith("{human|人:") and "belong={army|军队}" in kdml):
				selection["militaryNoun"].add(word)
	jieba = checked(ROOT / "data/sources/cppjieba-b3602bef-dict.txt", JIEBA_SHA256).decode("utf-8")
	for line in jieba.splitlines():
		word, _count, tag = line.split()
		flags = jieba_pos(tag)
		if flags and HAN.fullmatch(word):
			words[word] |= flags | JIEBA
	readings = defaultdict(lambda: defaultdict(set))
	aliases = defaultdict(set)
	general_nouns = defaultdict(set)
	records = gzip.decompress(checked(ROOT / "data/dictionary-records.jsonl.gz", RECORDS_SHA256))
	for line in records.splitlines():
		row = json.loads(line)
		forms = set(row["forms"].values())
		simplified, traditional = row["forms"].get("simplified"), row["forms"].get("traditional")
		if (
			simplified
			and traditional
			and simplified != traditional
			and HAN.fullmatch(traditional)
			and HAN.fullmatch(simplified)
		):
			aliases[traditional].add(simplified)
		if row["kind"] == "word":
			families = projected_families(row["glosses"], projection) if not row["properName"] else ()
			for word in forms:
				if not HAN.fullmatch(word):
					continue
				if families:
					words[word] |= 1 | CEDICT
					for family in families:
						name = family_classes[family]
						selection[name].add(word)
						motion_evidence[name][word].append(row["id"])
						derivations[family][word].add(row["id"])
				# Project attested nominal morphology, never complete sentences.
				# Balanced military compounds contain two nominal constituents;
				# their aligned pronunciation disambiguates the final bound head.
				if (
					not row["properName"]
					and row["readingStatus"] == "aligned"
					and word.endswith(("将", "將"))
					and row["readings"][-1] == "jiang4"
				):
					if word in selection["militaryNoun"] and 1 < len(word) <= 4:
						general_nouns[word].add(row["id"])
					if len(word) == 4 and word[1] in selection["militaryNoun"]:
						general_nouns[word[2:]].add(row["id"])
				if not row["properName"] and any(VERB_GLOSS.match(g) for g in row["glosses"]):
					words[word] |= 2 | CEDICT
				if len(word) > 1 and "重" in word:
					for offset, ch in enumerate(word):
						if ch == "重":
							reading = row["readings"][offset] if row["readingStatus"] == "aligned" else "?"
							readings[word][offset].add(reading)
		elif "重" in forms:
			for word in row["examples"]:
				if len(word) > 1 and HAN.fullmatch(word):
					for offset, ch in enumerate(word):
						if ch == "重":
							readings[word][offset].add(row["readings"][0])
	# Keep unpronounced entries separate from explicit contrary readings.
	# A strong, complete, multi-character predicate can analyze nominalized
	# re-V terms; weak/single-character evidence still cannot disambiguate 重酬.
	opaque = {}
	for word in words:
		if len(word) > 1 and "重" in word and word not in readings:
			opaque[word] = [offset for offset, ch in enumerate(word) if ch == "重"]
	# Other readings and unknown/conflicting senses veto productive re- analysis.
	blockers = {
		word: sorted(i for i, choices in positions.items() if choices != {"chong2"})
		for word, positions in sorted(readings.items())
	}
	blockers = {word: positions for word, positions in blockers.items() if positions}
	return (
		json.dumps(
			{
				"schemaVersion": 1,
				"sources": [
					{
						"id": "openhownet",
						"url": "https://github.com/thunlp/OpenHowNet",
						"sha256": HOW_SHA256,
						"license": "OPENHOWNET-LICENSE.txt",
						"sourceBit": HOW,
					},
					{
						"id": "cppjieba",
						"url": "https://github.com/yanyiwu/cppjieba/tree/b3602bef7d1f67521a61788a74fb5801a0e62cd3",
						"sha256": JIEBA_SHA256,
						"license": "CPPJIEBA-LICENSE.txt",
						"sourceBit": JIEBA,
					},
					{
						"id": "cc-cedict+kfcd",
						"url": "https://www.mdbg.net/chinese/dictionary?page=cedict",
						"sha256": RECORDS_SHA256,
						"licenses": ["CC-BY-SA-4.0.txt", "KFCD-LICENSE.txt"],
						"sourceBit": CEDICT,
					},
				],
				"modifications": (
					"Union POS alternatives, source masks, explicit infinitive gloss verb candidates; "
					"source-authored form pairs; explicit/opaque 重 evidence kept separate; "
					"HowNet container/human classifier selection and military/human noun senses. "
					"Aligned nominal heads projected from dictionary military compounds with record IDs. "
					"Root location/directed-motion candidates retain their HowNet sense IDs. "
					"Rotation-agent roles and nominal definition heads, transfer-theme roots and "
					"indefinite quantities retain source sense/record IDs; all are candidates, not labels. "
					"Pinned taxonomy living roots, physiological body parts with explicit hosts, "
					"human-host stature, animate age and restricted age units, and reviewed development "
					"definition heads retain sense/record IDs. "
					"Derived compilation CC-BY-SA-4.0; original MIT and CC-BY notices retained."
				),
				"counts": {
					"words": len(words),
					"verbCandidates": sum(bool(v & 2) for v in words.values()),
					"repeatBlockers": len(blockers),
					"opaqueRepeatBlockers": len(opaque),
					"selectionClasses": {name: len(values) for name, values in sorted(selection.items())},
					"multiSourceWords": sum((v >> 12).bit_count() > 1 for v in words.values()),
					"generalNouns": len(general_nouns),
				},
				"words": dict(sorted(words.items())),
				"repeatBlockers": blockers,
				"opaqueRepeatBlockers": dict(sorted(opaque.items())),
				"selection": {name: sorted(values) for name, values in sorted(selection.items())},
				"selectionEvidence": {
					name: {word: sorted(set(ids)) for word, ids in sorted(values.items())}
					for name, values in sorted(motion_evidence.items())
				},
				"semanticProjection": {
					"sha256": hashlib.sha256(PROJECTION_PATH.read_bytes()).hexdigest(),
					"taxonomySha256": TAXONOMY_SHA256,
					"families": {
						name: {word: sorted(ids) for word, ids in sorted(entries.items())}
						for name, entries in sorted(derivations.items())
					},
				},
				"formAliases": {word: next(iter(forms)) for word, forms in sorted(aliases.items()) if len(forms) == 1},
				"generalNouns": {word: sorted(ids) for word, ids in sorted(general_nouns.items())},
			},
			ensure_ascii=False,
			separators=(",", ":"),
		)
		+ "\n"
	).encode("utf-8")


if __name__ == "__main__":
	parser = argparse.ArgumentParser(description=__doc__)
	parser.add_argument("--check", action="store_true")
	args = parser.parse_args()
	content = generate()
	if args.check:
		if OUTPUT.read_bytes() != content:
			raise ValueError("Stale grammar lexical evidence")
	else:
		OUTPUT.write_bytes(content)
	print(json.loads(content)["counts"])
