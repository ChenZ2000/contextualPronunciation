from __future__ import annotations

import unittest
from unittest import mock

from tests.core_loader import load
from tests.resegmentation_cases import CASES
from tests.test_global_plugin_integration import _load_plugin


class ResegmentationTests(unittest.TestCase):
	def test_structural_oracles_in_both_modes(self):
		for extended in (False, True):
			r = load("rules").load_default_rules(extended=extended)
			for text, target, expected in CASES:
				i = text.index(target)
				with self.subTest(text=text, extended=extended):
					if expected is None:
						self.assertEqual(target, r.transform(text)[i])
					else:
						self.assertEqual(expected, r.resolve(text)[i].reading_id)
						self.assertEqual(r.resolve(text)[i], r.resolve(text, speech_only=True)[i])

	def test_tokens_and_dependencies_change_before_rendering(self):
		r = load("rules").load_default_rules(extended=False)
		for text, words, relation in (("下边缘", ["下", "边缘"], "amod"), ("唱和说", ["唱", "和", "说"], "conj")):
			self.assertEqual(words, [t.text for t in r.syntax.lexicon.tokenize(text, 0)])
			p = r.syntax.analyze(text, 1)
			self.assertTrue(any(d.relation == relation for d in p.dependencies))
		for text in (
			"下边的人",
			"边唱边说",
			"诗人唱和",
			"唱和诗词",
			"唱和着",
			"附和说法",
			"应和掌声",
			"调和油",
			"唱和龘靐",
		):
			self.assertEqual(text, r.transform(text))
		self.assertEqual("诗人唱褐", load("rules").load_default_rules().transform("诗人唱和"))

	def test_settings_commands_offsets_and_late_fail_open(self):
		e = _load_plugin()
		self.addCleanup(e.plugin.terminate)
		marker = object()
		seq = ["下边缘", marker, "唱和说，多行"]
		e.queue_point.notify(speechSequence=seq, priority=None)
		self.assertEqual(["下编缘", marker, "唱河说，多航"], seq)
		before = list(seq)
		e.queue_point.notify(speechSequence=seq, priority=None)
		self.assertEqual(before, seq)
		self.assertIs(marker, seq[1])
		seq = ["唱和", marker, "说"]
		e.queue_point.notify(speechSequence=seq)
		self.assertEqual(["唱褐", marker, "说"], seq)  # lexical 唱和 remains a single word
		seq = ["唱和说"]
		with mock.patch.object(e.plugin._rules, "transform", side_effect=RuntimeError("private text")):
			e.queue_point.notify(speechSequence=seq)
		self.assertEqual(["唱和说"], seq)
		for phrase, char, rule in (
			("下边缘", "边", "syntax-spatial-edge"),
			("唱和说", "和", "syntax-coordinated-predicates"),
			("多行", "行", "rowIndefiniteQuantity"),
		):
			for kwargs in ({"custom_entries": f"{phrase}|{char}|keep"}, {"disabled_rules": rule}):
				r = load("rules").load_default_rules(extended=False, **kwargs)
				self.assertEqual(phrase, r.transform(phrase))
		text = "😀下边缘"
		a = next(a for a in load("braille_readings").annotate(text, e.plugin._rules) if a.character == "边")
		self.assertEqual((2, 3, "bian1"), (a.start, a.utf16_start, a.reading))
		e.plugin.terminate()
		self.assertEqual([], e.queue_point.handlers)
