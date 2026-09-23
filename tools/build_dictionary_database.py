"""Build/query an attributed offline dictionary corpus, separate from runtime.

JSONL gzip is deterministic and shipped with source. Optional SQLite is a local
development index, not imported by NVDA or included in the add-on package.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import sqlite3
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.import_cedict import CEDICT, LINE, PINS, numbered  # noqa: E402
from tools.open_dictionary import COMMIT, SOURCE_SHA256, SOURCE_URL, read_snapshot, records  # noqa: E402

DATABASE = ROOT / "data/dictionary-records.jsonl.gz"
CATALOG = ROOT / "data/dictionary-sources.json"


def source_records():
	content = CEDICT.read_bytes()
	if hashlib.sha256(content).hexdigest() != PINS["cedict"]:
		raise ValueError("CC-CEDICT source pin changed")
	for line_number, line in enumerate(gzip.decompress(content).decode("utf-8").splitlines(), 1):
		if not line or line.startswith("#"):
			continue
		match = LINE.fullmatch(line)
		if match is None:
			raise ValueError(f"Invalid CEDICT line {line_number}")
		traditional, simplified, raw, gloss = match.groups()
		readings = [numbered(token) for token in raw.split()]
		yield {
			"id": f"cc-cedict:{line_number}",
			"source": "cc-cedict",
			"sourceLine": line_number,
			"kind": "word",
			"forms": {"simplified": simplified, "traditional": traditional},
			"rawPinyin": raw,
			"readings": readings,
			"readingStatus": "aligned" if len(readings) == len(simplified) and all(readings) else "unaligned",
			"properName": raw != raw.lower(),
			"glosses": gloss.split("/"),
			"license": "CC-BY-SA-4.0",
		}
	yield from records(read_snapshot())


def generate():
	counts = Counter()
	lines = []
	for record in source_records():
		counts[record["source"]] += 1
		lines.append(json.dumps(record, ensure_ascii=False, separators=(",", ":")))
	raw = ("\n".join(lines) + "\n").encode("utf-8")
	content = gzip.compress(raw, compresslevel=9, mtime=0)
	catalog = {
		"schemaVersion": 1,
		"purpose": "Source records for offline review, NOT validated runtime pronunciation rules",
		"recordCounts": dict(sorted(counts.items())),
		"recordsSha256": hashlib.sha256(content).hexdigest(),
		"normalization": [
			"NFC-compatible numbered pinyin via the same parser as runtime templates",
			"Preserve original forms, raw pinyin, sense glosses, source lines and licenses",
			"No silent first-pronunciation choice, default-tone completion or script conversion",
			"Character-sense readings annotate the target only, never the entire example",
		],
		"sources": {
			"cc-cedict": {
				"title": "CC-CEDICT, MDBG snapshot 2026-09-07",
				"url": "https://www.mdbg.net/chinese/dictionary?page=cedict",
				"snapshot": "data/sources/cedict-20260907.txt.gz",
				"sha256": PINS["cedict"],
				"license": "CC-BY-SA-4.0",
				"licenseUrl": "https://creativecommons.org/licenses/by-sa/4.0/",
			},
			"kfcd-hyzd": {
				"title": "开放汉语字典 / KFCD, © 2009–2020 开放词典",
				"url": SOURCE_URL,
				"commit": COMMIT,
				"snapshot": "data/sources/hyzd-simplified-0498775.tsv",
				"sha256": SOURCE_SHA256,
				"license": "CC-BY-3.0",
				"licenseUrl": "https://creativecommons.org/licenses/by/3.0/",
			},
			"unihan": {
				"title": "Unicode Unihan 17.0.0 (character-reading cross-check, not sense records)",
				"url": "https://www.unicode.org/reports/tr38/tr38-39.html",
				"snapshot": "data/sources/Unihan_Readings-17.0.0.txt.gz",
				"uncompressedSha256": PINS["unihan"],
				"license": "Unicode-3.0",
			},
		},
		"reviewedButNotImported": [
			{
				"source": "mozillazg/phrase-pinyin-data",
				"url": "https://github.com/mozillazg/phrase-pinyin-data",
				"reason": (
					"Aggregate lists identify third-party dictionary sources; "
					"repository MIT notice alone does not resolve every upstream dataset license."
				),
			},
			{
				"source": "mapull/chinese-dictionary",
				"url": "https://github.com/mapull/chinese-dictionary",
				"reason": "Upstream explicitly warns that some original data sources cannot be established.",
			},
			{
				"source": "Wiktionary / Kaikki",
				"url": "https://kaikki.org/zhwiktionary/index.html",
				"reason": (
					"Useful future source; extraction of regional readings, multi-pronunciation senses "
					"and alignment needs a separately tested importer."
				),
			},
		],
	}
	return {DATABASE: content, CATALOG: (json.dumps(catalog, ensure_ascii=False, indent=2) + "\n").encode()}


def query(term: str):
	"""Exact headword or character-sense example match; no documents are logged."""
	with gzip.open(DATABASE, "rt", encoding="utf-8") as stream:
		for line in stream:
			record = json.loads(line)
			if term in record["forms"].values() or term in record.get("examples", ()):
				yield record


def build_sqlite(path: Path):
	# Never overwrite an existing database or a user-selected file silently.
	if path.exists():
		raise ValueError("SQLite target already exists; choose a new output path")
	path.parent.mkdir(parents=True, exist_ok=True)
	with sqlite3.connect(path) as connection:
		connection.execute("CREATE TABLE sources (id TEXT PRIMARY KEY, metadata TEXT NOT NULL)")
		connection.execute(
			"CREATE TABLE entries (id TEXT PRIMARY KEY, source TEXT NOT NULL, simplified TEXT NOT NULL, "
			"traditional TEXT NOT NULL, kind TEXT NOT NULL, data TEXT NOT NULL)"
		)
		connection.execute("CREATE TABLE examples (entryId TEXT NOT NULL, phrase TEXT NOT NULL)")
		catalog = json.loads(CATALOG.read_text("utf-8"))
		connection.executemany(
			"INSERT INTO sources VALUES (?, ?)",
			((key, json.dumps(value, ensure_ascii=False)) for key, value in catalog["sources"].items()),
		)
		with gzip.open(DATABASE, "rt", encoding="utf-8") as stream:
			for line in stream:
				record = json.loads(line)
				connection.execute(
					"INSERT INTO entries VALUES (?, ?, ?, ?, ?, ?)",
					(
						record["id"],
						record["source"],
						record["forms"]["simplified"],
						record["forms"]["traditional"],
						record["kind"],
						line.strip(),
					),
				)
				connection.executemany(
					"INSERT INTO examples VALUES (?, ?)",
					((record["id"], phrase) for phrase in record.get("examples", ())),
				)
		connection.execute("CREATE INDEX by_simplified ON entries(simplified)")
		connection.execute("CREATE INDEX by_traditional ON entries(traditional)")
		connection.execute("CREATE INDEX by_example ON examples(phrase)")
		if connection.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
			raise ValueError("SQLite integrity check failed")


def main():
	parser = argparse.ArgumentParser(description=__doc__)
	parser.add_argument("--check", action="store_true")
	parser.add_argument("--query")
	parser.add_argument("--sqlite", type=Path)
	args = parser.parse_args()
	if args.query:
		print(json.dumps(list(query(args.query)), ensure_ascii=False, indent=2))
		return
	for path, content in generate().items():
		if args.check:
			if path.read_bytes() != content:
				raise ValueError(f"Stale dictionary database: {path}")
		else:
			path.write_bytes(content)
		print(f"{path.relative_to(ROOT)}: {len(content)} bytes; {hashlib.sha256(content).hexdigest()}")
	if args.sqlite:
		build_sqlite(args.sqlite)
		print(f"SQLite index: {args.sqlite}")


if __name__ == "__main__":
	main()
