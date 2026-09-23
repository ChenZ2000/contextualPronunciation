"""Guard the single engine-independent production pronunciation policy."""

from __future__ import annotations

import ast
import unittest
from pathlib import Path

from tests.core_loader import load


class GlobalPolicyTests(unittest.TestCase):
	def test_one_immutable_mapping_is_used_with_or_without_broad_matching(self):
		for extended in (False, True):
			rules = load("rules").load_default_rules(extended=extended)
			self.assertEqual("呈", rules.renderings["cheng2"])
			self.assertEqual("航首、崇复、呈汤", rules.transform("行首、重复、盛汤"))
			with self.assertRaises(TypeError):
				rules.renderings["cheng2"] = "成"

	def test_runtime_does_not_import_or_inspect_synthesizers(self):
		root = Path(__file__).resolve().parents[1] / "addon/globalPlugins/contextualPronunciation"
		for path in root.glob("*.py"):
			tree = ast.parse(path.read_text("utf-8"))
			for node in ast.walk(tree):
				if isinstance(node, ast.Import):
					self.assertFalse(any(n.name.startswith(("synthDriverHandler", "synthDrivers")) for n in node.names))
				elif isinstance(node, ast.ImportFrom):
					self.assertFalse((node.module or "").startswith(("synthDriverHandler", "synthDrivers")))
				elif isinstance(node, ast.Attribute):
					self.assertNotIn(node.attr, {"getSynth", "getCurrentLanguage", "synthChanged"})
		self.assertFalse((root / "worldvoice.py").exists())
		self.assertFalse((root / "renderers.py").exists())
