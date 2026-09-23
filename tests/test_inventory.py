from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class InventoryTests(unittest.TestCase):
	@classmethod
	def setUpClass(cls):
		cls.data = json.loads((ROOT / "data" / "polyphone_inventory.json").read_text(encoding="utf-8"))

	def test_ids_are_unique_and_required_fields_are_present(self):
		items = self.data["items"]
		ids = [item["id"] for item in items]
		self.assertEqual(len(ids), len(set(ids)))
		self.assertGreaterEqual(len(items), 75)
		for item in items:
			with self.subTest(item=item["id"]):
				self.assertIn(item["tier"], {"P0", "P1", "P2", "P3"})
				self.assertTrue(item["character"])
				self.assertTrue(item["readings"])
				self.assertIsInstance(item["defaultEnabled"], bool)

	def test_only_implemented_items_are_enabled(self):
		for item in self.data["items"]:
			with self.subTest(item=item["id"]):
				if item["defaultEnabled"]:
					self.assertTrue(item["status"].startswith("implemented_"))

	def test_required_user_and_engine_verified_targets_are_catalogued(self):
		by_id = {item["id"]: item for item in self.data["items"]}
		for item_id in ("xing-hang", "zhong-chong", "sheng-cheng", "ping-bing", "tan-dan"):
			with self.subTest(item=item_id):
				self.assertTrue(by_id[item_id]["defaultEnabled"])
		self.assertFalse(by_id["diao-tiao"]["defaultEnabled"])
		self.assertFalse(by_id["yao-yue"]["defaultEnabled"])

	def test_default_inventory_and_runtime_rule_targets_stay_synchronized(self):
		runtime = json.loads(
			(ROOT / "addon" / "globalPlugins" / "contextualPronunciation" / "data" / "rules_zh_CN.json").read_text(
				encoding="utf-8",
			),
		)
		enabled_characters = {item["character"] for item in self.data["items"] if item["defaultEnabled"]}
		high_confidence = {
			target
			for target, definition in runtime["characters"].items()
			if definition["structuralRules"]
			or any(group.get("reading") and group["confidence"] == "high" for group in definition["phraseGroups"])
		}
		self.assertEqual(enabled_characters, high_confidence)

	def test_debug_gold_label_is_tiao_not_diao(self):
		matrix = json.loads((ROOT / "tests/fixtures/vocalizer_expressive2/p1_polyphone_matrix.json").read_text("utf-8"))
		entry = next(item for item in matrix["entries"] if item["id"] == "diao-tiao")
		debug_readings = [
			reading["id"]
			for reading in entry["readings"]
			if any("调试" in phrase["text"] for phrase in reading["phrases"])
		]
		self.assertEqual(["tiao2"], debug_readings)

	def test_engine_verified_inventory_matches_ting_ting_findings(self):
		findings = json.loads((ROOT / "data" / "ting_ting_p1_probe_findings.json").read_text(encoding="utf-8"))
		verified_characters = {
			item["character"] for item in self.data["items"] if item["status"] == "implemented_engine_verified"
		}
		self.assertEqual(verified_characters, {item["character"] for item in findings["definiteMisreads"]})


if __name__ == "__main__":
	unittest.main()
