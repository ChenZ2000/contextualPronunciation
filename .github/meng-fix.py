"""Apply the reviewed fix to the exact 0.7.9 baseline (temporary validation only)."""
from pathlib import Path
import json

ROOT = Path.cwd()

def edit(name, old, new):
    path = ROOT / name
    raw = path.read_bytes()
    newline = b"\r\n" if b"\r\n" in raw else b"\n"
    text = raw.decode("utf-8").replace("\r\n", "\n")
    assert old in text, (name, old[:80])
    path.write_bytes(text.replace(old, new).encode("utf-8").replace(b"\n", newline))

edit("addon/globalPlugins/contextualPronunciation/data/rules_zh_CN.json",
     '"meng1": {"replacement": "蒙"}',
     '"meng1": {"replacement": "擝", "source": "Unicode 17.0.0 Unihan: U+64DD kMandarin mēng (pinned snapshot in data/sources); avoid polyphonic 蒙/矇, whose kMandarin default is méng. Lexical evidence, not all-voice acoustic certification."}')

name = "tests/test_colloquial_tones.py"
path = ROOT / name
text = path.read_text("utf-8")
# Only speech-output expectations change. Original-text controls remain intact.
text = "".join(line if 'for text in ("蒙",' in line else line.replace("蒙", "擝") for line in text.splitlines(keepends=True))
path.write_text(text, "utf-8")
edit(name, "import unittest\n", "import gzip\nimport hashlib\nimport json\nimport unittest\nfrom pathlib import Path\n")
edit(name, '\t"一脸懵逼",\n', '\t"一脸懵逼",\n\t"一脸懵",\n\t"一臉懵",\n')
edit(name, '\t"懵得答不上话",\n', '\t"懵得答不上话",\n\t"懵得说不出话",\n')
edit(name, 'for text in ("蒙", "檬", "夢", "梦", "濛",', 'for text in ("蒙", "矇", "擝", "蒙古", "蒙面", "启蒙", "檬", "夢", "梦", "濛",')
edit(name, '\tdef test_colloquial_meng_is_productive_in_every_default_mode(self):', '''	def test_meng_renderer_has_first_tone_in_independent_pinned_source(self):
		# Checking only the selected reading or replacement text missed the
		# 0.7.9 bug: 蒙 (also 矇) defaults to meng2 in this independent source.
		# Lexical evidence is not an acoustic guarantee for every synthesizer.
		from tools.import_cedict import PINS, UNIHAN, read_unihan

		source = gzip.decompress(UNIHAN.read_bytes())
		self.assertEqual(PINS["unihan"], hashlib.sha256(source).hexdigest())
		defaults, readings, _common = read_unihan(source.decode("utf-8").splitlines())
		for ambiguous in ("蒙", "矇"):
			self.assertEqual("meng2", defaults[ambiguous])
		for extended, rules in self.defaults.items():
			with self.subTest(extended=extended):
				renderer = rules.renderings["meng1"]
				self.assertEqual("meng1", defaults[renderer])
				self.assertEqual({"meng1"}, readings[renderer])
				self.assertEqual(1, len(renderer))
				self.assertEqual(2, len(renderer.encode("utf-16-le")))

	def test_meng_listening_probe_uses_current_output_without_claiming_certified_anchors(self):
		fixture = Path(__file__).parent / "fixtures/vocalizer_expressive2/renderer_cases.json"
		cases = json.loads(fixture.read_text("utf-8"))["cases"]
		groups = {}
		for case in cases:
			if case["id"].startswith("meng1_colloquial_"):
				groups.setdefault(case["compareGroup"], {})[case["role"]] = case
		self.assertEqual(
			{"一脸懵逼", "一脸懵", "懵了", "懵圈", "看懵了", "懵得说不出话", "被新通知整懵了"},
			{group["source"]["text"] for group in groups.values()},
		)
		for group in groups.values():
			self.assertEqual({"source", "candidate", "previous_renderer"}, set(group))
			source = group["source"]["text"]
			self.assertEqual(source.replace("懵", "蒙"), group["previous_renderer"]["text"])
			for rules in self.defaults.values():
				self.assertEqual(rules.transform(source), group["candidate"]["text"])
				self.assertEqual("meng1", group["candidate"]["expectedReading"])
			for case in group.values():
				self.assertEqual(source.index("懵"), case["targetCharIndex"])

	def test_colloquial_meng_is_productive_in_every_default_mode(self):''')

edit("tests/test_nvda_symbol_integration.py",
     '\tdef test_polyphones_reach_real_symbol_processor_at_every_user_level(self):', '''	def test_colloquial_meng_renderer_survives_real_symbol_processing(self):
		from tests.test_pipeline import CharacterModeCommand

		normalizer = pipeline.SpeechSequenceNormalizer(
			rules=rules_module.load_default_rules(),
			character_mode_command_type=CharacterModeCommand,
		)
		options = pipeline.RuntimeOptions()
		source = "一脸懵逼，一脸懵；懵懂；蒙、矇"
		sequence = normalizer.normalize([source], options=options)
		self.assertEqual(["一脸擝逼，一脸擝；懵懂；蒙、矇"], sequence)
		for locale in ("zh_CN", "en"):
			processor = self._processor(locale)
			for level_name in ("NONE", "SOME", "MOST", "ALL", "CHAR"):
				with self.subTest(locale=locale, level=level_name):
					level = getattr(self.character_processing.SymbolLevel, level_name)
					queued = [processor.processText(sequence[0], level)]
					guard = pipeline.FailOpenSpeechFilter(normalizer=normalizer, options_provider=lambda: options)
					guard.guard_queued_readings(queued)
					self.assertIn("一脸擝逼", queued[0])
					self.assertEqual(2, queued[0].count("擝"))
					self.assertIn("懵懂", queued[0])
					self.assertIn("蒙", queued[0])
					self.assertIn("矇", queued[0])
		self.assertEqual("一脸懵逼，一脸懵；懵懂；蒙、矇", source)

	def test_polyphones_reach_real_symbol_processor_at_every_user_level(self):''')

path = ROOT / "tests/fixtures/vocalizer_expressive2/renderer_cases.json"
raw = path.read_bytes()
newline = b"\r\n" if b"\r\n" in raw else b"\n"
data = json.loads(raw)
phrases = ("一脸懵逼", "一脸懵", "懵了", "懵圈", "看懵了", "懵得说不出话", "被新通知整懵了")
for index, phrase in enumerate(phrases):
    group = f"meng1_colloquial_{index}"
    for role, text in (("source", phrase), ("candidate", phrase.replace("懵", "擝")), ("previous_renderer", phrase.replace("懵", "蒙"))):
        data["cases"].append({"id": f"{group}_{role}", "text": text, "targetCharIndex": phrase.index("懵"), "compareGroup": group, "role": role, "expectedReading": "meng1" if role != "previous_renderer" else "voice-dependent; observed meng2 in 0.7.9", "note": "Listening probe input, not certified audio. No first-tone anchor is assumed; unknown/omitted characters or second tone are failures, not successful correction."})
path.write_bytes((json.dumps(data, ensure_ascii=False, indent=2) + "\n").encode("utf-8").replace(b"\n", newline))

edit("docs/ARCHITECTURE.md",
     "蒙 is the temporary rendering, but its own multiple readings mean that the chosen annotation is not an acoustic guarantee.",
     "The temporary rendering is now 擝 (U+64DD), whose pinned Unicode 17.0.0 Unihan `kMandarin` reading is `mēng`. The previous 蒙 rendering could be spoken as `méng`; 矇 has the same second-tone default and is not a suitable substitute. The shared rendering map is used by both default and extended modes. This fixes the ambiguous text rendering, not every voice's Unicode coverage: a voice that does not recognize 擝 can still mispronounce or omit it. Tests verify independent lexical evidence and the NVDA text pipeline, not target-voice audio.")
edit("docs/ARCHITECTURE.md",
     "语音临时替代字“蒙”本身多音，选定注音不等于实际声调保证。",
     "语音临时替代字改为“擝”（U+64DD），固定版本 Unicode 17.0.0 Unihan 的 `kMandarin` 将其标为 `mēng`。原替代字“蒙”可能被读成二声；“矇”的默认音也是二声，不作为替代。基础与扩展模式共用同一映射。这修复的是替代文本的多音歧义，不能补全声库的字库：不支持“擝”的声音仍可能误读或漏读。测试验证独立字音证据和 NVDA 文本管线，不冒充目标声音的音频验证。")
edit("docs/RULES.md", "语音临时替换为“蒙”", "语音临时替换为“擝”（U+64DD，`mēng`）")
edit("docs/RULES.md", "temporarily renders 蒙 for unprotected 懵", "temporarily renders 擝 (U+64DD, `mēng`) for unprotected 懵")
edit("docs/RULES.md",
     "“蒙”本身也有多个读音，因此文本与注音测试不能证明每个声音的实际声调，仍需在目标声库上实测。",
     "0.7.9 原来的“蒙”替代字可能被读成二声；现用固定 Unihan 资料标为一声的“擝”。“擝”是生僻字，声库仍须支持它；文本、字音来源与注音测试不等于实际声调验证，仍需在目标声库上实测。无法识别该字时可停用 `colloquialMeng` 恢复原文，不会自动退回已知有二声歧义的“蒙”。")
edit("docs/RULES.md",
     "蒙 is also polyphonic, so text and annotation tests do not establish the actual tone of every voice. Acoustic verification on the target voice is still required.",
     "The 0.7.9 蒙 renderer could produce second tone; the replacement 擝 is first tone in the pinned Unihan data. 擝 is rare and must be supported by the voice. Text, lexical-source and annotation tests do not certify its actual tone. Verify it on the target voice; disabling `colloquialMeng` restores the original text if unsupported, rather than silently falling back to the ambiguous 蒙 renderer.")
edit("docs/REFERENCES.md", "- **Neutral-tone 腾:**", "- **First-tone speech rendering:** the pinned [Unicode 17.0.0 Unihan snapshot](../data/sources/Unihan_Readings-17.0.0.txt.gz) records `U+64DD kMandarin mēng` for 擝, whereas 蒙 (U+8499) and 矇 (U+77C7) default to `méng`. The independent regression verifies the snapshot checksum and requires the renderer to have a first-tone default with no competing reading in that source. This is evidence for a temporary speech character, not a change to standard spelling or acoustic certification of every voice.\n- **Neutral-tone 腾:**")
edit("docs/REFERENCES.md", "- **“腾”的轻声：**", "- **一声语音替代字：** 固定版本 [Unicode 17.0.0 Unihan 快照](../data/sources/Unihan_Readings-17.0.0.txt.gz) 将“擝”记为 `U+64DD kMandarin mēng`；“蒙”（U+8499）和“矇”（U+77C7）的默认音则为 `méng`。独立回归校验快照哈希，并要求替代字在该来源中的默认音为一声、没有竞争读音。这是临时语音替代字的证据，不是规范书写变更，也不是所有声库的声学认证。\n- **“腾”的轻声：**")
edit("CHANGELOG.md", "## 0.7.9\n", """## Unreleased

- Fix colloquial 懵 speech rendering: `meng1` now uses 擝 (U+64DD) instead of the polyphonic 蒙, which could be read as second-tone `méng` despite the correct annotation. Preserve productive context matching, literary protections, user overrides and original offsets.
- Add the exact 一脸懵 / 一脸懵逼 reproducers, independent pinned-Unicode default-tone checks and real NVDA symbol-pipeline regressions. These are text/lexical checks; target-voice acoustic support for the rare renderer must still be verified.
- 修复口语“懵”的语音替代：一声 `meng1` 改用“擝”，不再交给多音字“蒙”让声库重新选择二声。新语境覆盖、“懵懂”等保护、用户覆盖与原文位置保持不变；生僻字支持及实际声调仍需目标声库验证。

## 0.7.9
""")
path = ROOT / "tests/fixtures/vocalizer_expressive2/README.md"
raw = path.read_bytes()
newline = b"\r\n" if b"\r\n" in raw else b"\n"
addition = """
## 口语“懵”的一声回归

`renderer_cases.json` 新增 `meng1_colloquial_*` 组，覆盖“一脸懵逼、一脸懵、懵了、懵圈、看懵了、懵得说不出话”及新语境。每组并列原文、当前“擝”替代输出和旧版“蒙”替代输出。使用上面的 `render` 命令生成当前目标声库的 WAV；这些条目只是待渲染输入，不是已有试听结果。

这一组不把“蒙”“矇”或尚未试听的“擝”标为 `anchor`，因此不会因自身比较相等而产生“一声已通过”的假结论。必须确认整个词的目标音确实为一声；二声、三声、读字母、未知字符提示、漏字均不是通过。“擝”是生僻字，固定 Unihan 的一声证据不能证明声库支持它。未支持的声音可停用 `colloquialMeng` 保留原文，不应静默退回已知多音的“蒙”。

The `meng1_colloquial_*` cases compare original text, the current 擝 renderer and the old 蒙 renderer. They are listening-probe inputs, not recorded results. No first-tone acoustic anchor is assumed. Verify the target tone and complete word on the actual voice; an unknown/omitted character or a different tone is not a pass. The pinned Unicode reading does not certify voice coverage.
"""
path.write_bytes(raw + addition.encode("utf-8").replace(b"\n", newline))
