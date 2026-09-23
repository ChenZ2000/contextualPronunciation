"""Reproducible POS/sememe projection from the official OpenHowNet core data.

No API, BabelNet data, similarity model, executable pickle or document text is
distributed. --import-archive is an explicit development operation; ordinary
builds use the pinned, reduced, human-inspectable JSON snapshot.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
import pickle
import re
from collections import defaultdict
from functools import lru_cache
from pathlib import Path
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data/sources/openhownet-core-20210920.json.gz"
OUTPUT = ROOT / "addon/globalPlugins/contextualPronunciation/data/syntax_lexicon.json"
TAXONOMY = ROOT / "data/sources/openhownet-taxonomy-20210920.txt"
TAXONOMY_SHA256 = "d1b44ef0385c243b8f4661b39348df359b764247d2d1d0dd263ad31e6deb73a0"
ARCHIVE_SHA256 = "daaa31e2627e099e03ce15371f472c6f9ec5b3aac71a4e5e2ab5c4f4f38c44d4"
SOURCE_SHA256 = "ef9ccab1ff9c87b31e3dc9b765071b5ecefe9568367eabc5c211e57da1a76ced"
SOURCE_URL = "https://thunlp.oss-cn-qingdao.aliyuncs.com/OpenHowNet/resources.zip"
POS = {"noun": 1, "verb": 2, "adj": 4, "adv": 8, "pron": 16, "prep": 32, "classifier": 64, "det": 128, "num": 256}
FOOD = 512
POSSIBLE_FOOD = 1024
CONTENTS = 1 << 17
POSSIBLE_CONTENTS = 1 << 18
CONTAINER = 1 << 19
_HAN = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff]{1,16}\Z")
_ROOT = re.compile(r"^\{([^{}:,]+)")
FOOD_ROOTS = frozenset({"edible|食物", "fruit|水果", "vegetable|蔬菜"})
CONTENTS_ROOTS = frozenset(
	{
		"liquid|液",
		"water|水",
		"gas|气",
		"material|材料",
		"chemical|化学物",
		"medicine|药物",
		"metal|金属",
		"stone|土石",
		"waste|废物",
		"clothing|衣物",
	}
)


class DataOnlyUnpickler(pickle.Unpickler):
	def find_class(self, module, name):
		raise ValueError("Executable/global pickle contents are forbidden")

	def persistent_load(self, pid):
		raise ValueError("Persistent pickle references are forbidden")


def serialized(value):
	return (json.dumps(value, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")


def descendants(triples, roots):
	"""Follow only explicit hyponym edges, never arbitrary semantic roles."""
	children = defaultdict(set)
	for line in triples.splitlines():
		parent, relation, child = line.split()
		if relation == "hyponym":
			children[parent].add(child)
	result, todo = set(roots), list(roots)
	while todo:
		for child in children[todo.pop()] - result:
			result.add(child)
			todo.append(child)
	return frozenset(result)


@lru_cache(maxsize=1)
def semantic_roots():
	content = TAXONOMY.read_bytes()
	if hashlib.sha256(content).hexdigest() != TAXONOMY_SHA256:
		raise ValueError("Unreviewed sememe taxonomy")
	triples = content.decode("utf-8")
	return descendants(triples, FOOD_ROOTS), descendants(triples, CONTENTS_ROOTS) | {"physical|物质"}


def import_taxonomy(path):
	content = path.read_bytes()
	if hashlib.sha256(content).hexdigest() != ARCHIVE_SHA256:
		raise ValueError("Unreviewed OpenHowNet archive")
	with ZipFile(io.BytesIO(content)) as archive:
		content = archive.read("sememe_triples_taxonomy.txt")
	if hashlib.sha256(content).hexdigest() != TAXONOMY_SHA256:
		raise ValueError("Unreviewed taxonomy member")
	if TAXONOMY.exists() and TAXONOMY.read_bytes() != content:
		raise ValueError("Refusing to overwrite a different taxonomy")
	TAXONOMY.write_bytes(content)


def import_archive(path):
	content = path.read_bytes()
	if hashlib.sha256(content).hexdigest() != ARCHIVE_SHA256:
		raise ValueError("Unreviewed OpenHowNet archive")
	with ZipFile(io.BytesIO(content)) as archive:
		info = archive.getinfo("HowNet_dict_complete")
		if info.file_size != 97668631:
			raise ValueError("Unexpected core member size")
		data = DataOnlyUnpickler(io.BytesIO(archive.read(info))).load()
	# Original IDs, POS and KDML remain available for sense-level audits. Do
	# not retain English glosses, synonym/similarity data or BabelNet resources.
	rows = sorted(
		(key, row["ch_word"], row["ch_grammar"], row["Def"])
		for key, row in data.items()
		if _HAN.fullmatch(row["ch_word"]) and row["ch_grammar"] in POS
	)
	content = gzip.compress(serialized({"archiveSha256": ARCHIVE_SHA256, "rows": rows}), mtime=0)
	if SOURCE.exists() and SOURCE.read_bytes() != content:
		raise ValueError("Refusing to overwrite a different source snapshot")
	SOURCE.write_bytes(content)
	print("Source SHA256:", hashlib.sha256(content).hexdigest())


def food_sense(kdml):
	root = _ROOT.match(kdml)
	if root is None:
		return False
	# Merely mentioning food in a nested role does NOT make something food:
	# a restaurant is a place, a fruit tree is a tree. Plant parts explicitly
	# marked as the patient of eating are an additional reviewed construction.
	return (
		root[1] in semantic_roots()[0]
		or (root[1] == "part|部件" and "{eat|吃:patient={~}}" in kdml)
		or (
			root[1] in {"part|部件", "material|材料", "AlgaeFungi|低植"}
			and ("MaterialOf={edible|食物}" in kdml or "MaterialOf={food|食品}" in kdml)
		)
	)


def contents_sense(kdml):
	"""A material/portable noun, not any noun or anything mentioning a liquid."""
	root = _ROOT.match(kdml)
	if root is None:
		return False
	return (
		root[1] in semantic_roots()[1]
		or (root[1] == "part|部件" and "PartPosition={BodyFluid|体液}" in kdml)
		or (root[1] == "example|实例" and any("restrictive={" + name in kdml for name in semantic_roots()[1]))
		or (root[1] == "tool|用具" and "{decorate|装饰:material={~}}" in kdml)
	)


def container_sense(kdml):
	root = _ROOT.match(kdml)
	return bool(
		root and root[1] == "tool|用具" and ("{put|放置:LocationFin={~}" in kdml or "{store|保存:location={~}" in kdml)
	)


def generate():
	content = SOURCE.read_bytes()
	if hashlib.sha256(content).hexdigest() != SOURCE_SHA256:
		raise ValueError("Unreviewed reduced OpenHowNet snapshot")
	data = json.loads(gzip.decompress(content))
	if data["archiveSha256"] != ARCHIVE_SHA256:
		raise ValueError("Wrong archive provenance")
	flags = defaultdict(int)
	noun_senses = {name: defaultdict(set) for name in ("food", "contents", "container")}
	classifiers = {"food": food_sense, "contents": contents_sense, "container": container_sense}
	for _sense_id, word, pos, kdml in data["rows"]:
		flags[word] |= POS[pos]
		if pos == "noun":
			for name, classify in classifiers.items():
				noun_senses[name][word].add(classify(kdml))
	for name, certain, possible in (
		("food", FOOD, POSSIBLE_FOOD),
		("contents", CONTENTS, POSSIBLE_CONTENTS),
		("container", CONTAINER, 0),
	):
		for word, senses in noun_senses[name].items():
			if True in senses:
				flags[word] |= certain if senses == {True} else possible
	return serialized(
		{
			"schemaVersion": 2,
			"source": {
				"url": SOURCE_URL,
				"archiveSha256": ARCHIVE_SHA256,
				"snapshotSha256": SOURCE_SHA256,
				"taxonomySha256": TAXONOMY_SHA256,
				"license": "OPENHOWNET-LICENSE.txt",
				"modification": (
					"Han headwords <=16; union POS; unanimous noun-sense food/contents/container features; "
					"no pronunciations inferred"
				),
			},
			"counts": {
				"sourceSenses": len(data["rows"]),
				"words": len(flags),
				"unanimousFoodHeads": sum(bool(v & FOOD) for v in flags.values()),
				"ambiguousFoodHeads": sum(bool(v & POSSIBLE_FOOD) for v in flags.values()),
				"unanimousContentsHeads": sum(bool(v & CONTENTS) for v in flags.values()),
				"ambiguousContentsHeads": sum(bool(v & POSSIBLE_CONTENTS) for v in flags.values()),
				"unanimousContainerHeads": sum(bool(v & CONTAINER) for v in flags.values()),
			},
			"words": dict(sorted(flags.items())),
		}
	)


def main():
	parser = argparse.ArgumentParser(description=__doc__)
	parser.add_argument("--import-archive", type=Path)
	parser.add_argument("--import-taxonomy", type=Path)
	parser.add_argument("--check", action="store_true")
	args = parser.parse_args()
	if args.import_taxonomy:
		import_taxonomy(args.import_taxonomy)
		return
	if args.import_archive:
		import_archive(args.import_archive)
		return
	content = generate()
	if args.check:
		if OUTPUT.read_bytes() != content:
			raise ValueError("Stale syntax lexicon")
	else:
		OUTPUT.write_bytes(content)
	print(json.loads(content)["counts"])


if __name__ == "__main__":
	main()
