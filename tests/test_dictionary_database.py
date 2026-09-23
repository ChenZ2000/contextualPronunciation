from __future__ import annotations

import gzip
import json
import random
import tempfile
import unittest
from collections import defaultdict
from pathlib import Path

from tests.core_loader import load
from tools import build_dictionary_database as database
from tools.import_cedict import HAN
from tools.open_dictionary import merge_examples, records


class DictionaryDatabaseTests(unittest.TestCase):
	def merge(self, words, lines):
		readings = {"薄": {"bao2", "bo2", "bo4"}, "荷": {"he2", "he4"}, "乐": {"le4", "yue4"}}
		defaults = {"薄": "bao2", "荷": "he2", "乐": "le4"}
		return merge_examples(
			words, lines, han_pattern=HAN, character_readings=readings, defaults=defaults, max_length=32
		)

	def test_partial_source_never_fills_other_characters(self):
		words = defaultdict(set)
		self.merge(words, ["薄\t薄\tbo4\t薄荷油\t一种植物\t"])
		self.assertEqual({("bo4", None, None)}, words["薄荷油"])

	def test_conflicting_position_abstains_without_destroying_other_readings(self):
		words = {"薄荷": {("bo4", "he5")}}
		self.merge(words, ["荷\t荷\the2\t薄荷\t\t"])
		self.assertEqual({("bo4", None)}, words["薄荷"])
		# Neutral is NOT a wildcard: no invented he2 replacement may be emitted.
		rules = load("rules").load_default_rules()
		annotations = load("braille_readings").annotate("薄荷", rules)
		self.assertEqual([(0, "bo4")], [(a.start, a.reading) for a in annotations])

	def test_source_alternatives_and_existing_blockers_survive_reordering(self):
		lines = ["乐\t樂\tyue4\t仙乐\t音乐\t", "乐\t樂\tle4\t仙乐\t快乐\t"]
		for seed in range(8):
			random.Random(seed).shuffle(lines)
			words = defaultdict(set)
			self.merge(words, lines)
			self.assertEqual({None}, words["仙乐"])
		words = {"仙乐": {None}}
		self.merge(words, lines[:1])
		self.assertEqual({None}, words["仙乐"])

	def test_multiple_regional_readings_are_not_silently_reduced_to_first(self):
		line = "乐\t樂\tle4/yue4\t仙乐\t\t"
		record = next(records([line]))
		self.assertEqual(["le4", "yue4"], record["readings"])
		words = defaultdict(set)
		self.merge(words, [line])
		self.assertEqual({None}, words["仙乐"])

	def test_canonical_database_reproduces_and_retains_licenses_and_sources(self):
		for path, content in database.generate().items():
			self.assertEqual(content, path.read_bytes(), str(path))
		catalog = json.loads(database.CATALOG.read_text("utf-8"))
		with gzip.open(database.DATABASE, "rt", encoding="utf-8") as stream:
			ids = set()
			for line in stream:
				record = json.loads(line)
				self.assertNotIn(record["id"], ids)
				ids.add(record["id"])
				self.assertEqual(catalog["sources"][record["source"]]["license"], record["license"])
		self.assertEqual(sum(catalog["recordCounts"].values()), len(ids))
		self.assertTrue(any(r["kind"] == "characterSense" for r in database.query("盛汤")))

	def test_sqlite_writer_will_not_overwrite_existing_file(self):
		with tempfile.TemporaryDirectory() as directory:
			path = Path(directory) / "existing.sqlite3"
			path.touch()
			with self.assertRaises(ValueError):
				database.build_sqlite(path)
