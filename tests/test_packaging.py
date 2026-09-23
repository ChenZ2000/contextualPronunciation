from __future__ import annotations

import gettext
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]


class PackagingTests(unittest.TestCase):
	def setUp(self):
		self._build_directory = tempfile.TemporaryDirectory()
		self.addCleanup(self._build_directory.cleanup)
		self.build_directory = self._build_directory.name

	def test_manifest_and_build_version_must_agree_before_any_write(self):
		from scripts import build_addon

		with mock.patch.object(build_addon.runpy, "run_path", return_value={"addon_info": {"addon_name": "mismatch"}}):
			with self.assertRaisesRegex(ValueError, "metadata mismatch"):
				build_addon.build(output_dir=Path(self.build_directory))
		self.assertEqual([], list(Path(self.build_directory).iterdir()))

	def test_manifest_quoted_descriptions_preserve_apostrophes_and_multiline_values(self):
		from scripts.build_addon import _manifest_value

		for text in (
			'description = """Preserves doesn\'t and Mike\'s."""',
			"description = \"Preserves doesn't and Mike's.\"",
		):
			self.assertEqual("Preserves doesn't and Mike's.", _manifest_value("description", text))
		self.assertEqual("first\nsecond", _manifest_value("description", 'description = """first\nsecond"""'))

	def test_release_rejects_wrong_tag_before_building(self):
		result = subprocess.run(
			[sys.executable, str(ROOT / "scripts/build_public_release.py"), "--tag", "v999.0.0"],
			capture_output=True,
			text=True,
		)
		self.assertNotEqual(0, result.returncode)
		self.assertIn("exact numeric manifest version", result.stderr)

	def test_source_archive_preserves_hashed_bytes_through_windows_git_checkout(self):
		command = [sys.executable, str(ROOT / "scripts/build_source_archive.py"), "--output-dir", self.build_directory]
		completed = subprocess.run(command, cwd=ROOT, check=True, capture_output=True, text=True)
		with tempfile.TemporaryDirectory() as directory:
			base = Path(directory)
			with ZipFile(completed.stdout.strip()) as archive:
				names = archive.namelist()
				prefix = names[0].split("/", 1)[0]
				for required in ("LICENSE", "CONTRIBUTING.md", "SECURITY.md", "docs/RELEASING.md"):
					self.assertIn(f"{prefix}/{required}", names)
				self.assertFalse(any("开发方案" in name or "/diagnostics/" in name for name in names))
				archive.extractall(base / "original")
			original = next((base / "original").iterdir())
			checkout = base / "checkout"
			checkout.mkdir()
			for arguments in (
				["init"],
				["config", "core.autocrlf", "true"],
				["add", "."],
				["checkout-index", "--all", f"--prefix={checkout.as_posix()}/"],
			):
				subprocess.run(["git", "-C", str(original), *arguments], check=True, capture_output=True)
			files = [p for p in original.rglob("*") if p.is_file() and ".git" not in p.parts]
			self.assertGreater(len(files), 40)
			for path in files:
				self.assertEqual(path.read_bytes(), (checkout / path.relative_to(original)).read_bytes(), str(path))

	def test_stable_manifest_declares_only_the_tested_stable_api(self):
		manifest = (ROOT / "manifest.ini").read_text(encoding="utf-8")
		self.assertRegex(manifest, r'minimumNVDAVersion\s*=\s*"2026\.2"')
		self.assertRegex(manifest, r'lastTestedNVDAVersion\s*=\s*"2026\.2"')
		self.assertRegex(manifest, r'docFileName\s*=\s*"readme\.html"')
		self.assertTrue((ROOT / "addon" / "doc" / "zh_CN" / "readme.html").is_file())

	def test_symbol_dictionary_is_mandatory_and_overrides_existing_identifier(self):
		manifest = (ROOT / "manifest.ini").read_text(encoding="utf-8")
		self.assertIn("[[lexicalApostrophe]]", manifest)
		self.assertRegex(manifest, r"(?s)\[\[lexicalApostrophe\]\].*?mandatory\s*=\s*true")
		for locale in ("en", "zh_CN", "zh_HK", "zh_TW"):
			with self.subTest(locale=locale):
				dictionary = (ROOT / "addon" / "locale" / locale / "symbols-lexicalApostrophe.dic").read_text(
					encoding="utf-8"
				)
				self.assertIn("in-word '\t-\tchar\tnorep", dictionary)
				self.assertNotIn("complexSymbols:", dictionary)

	def test_all_python_files_compile(self):
		for path in (ROOT / "addon").rglob("*.py"):
			with self.subTest(path=path):
				compile(path.read_text(encoding="utf-8"), str(path), "exec")

	def test_simplified_chinese_message_catalog_is_loadable(self):
		with (ROOT / "addon" / "locale" / "zh_CN" / "LC_MESSAGES" / "nvda.mo").open("rb") as stream:
			translations = gettext.GNUTranslations(stream)
		self.assertEqual("上下文发音规范化", translations.gettext("Context-aware pronunciation"))

	def test_archive_has_required_layout_and_reproducible_metadata(self):
		command = [sys.executable, str(ROOT / "scripts" / "build_addon.py"), "--output-dir", self.build_directory]
		completed = subprocess.run(command, cwd=ROOT, check=True, capture_output=True, text=True)
		archive_path = Path(completed.stdout.strip())
		first_build = archive_path.read_bytes()
		subprocess.run(command, cwd=ROOT, check=True, capture_output=True, text=True)
		self.assertEqual(first_build, archive_path.read_bytes())
		with ZipFile(archive_path) as archive:
			names = set(archive.namelist())
			self.assertIn("manifest.ini", names)
			self.assertIn("globalPlugins/contextualPronunciation/__init__.py", names)
			self.assertIn("globalPlugins/contextualPronunciation/data/rules_zh_CN.json", names)
			self.assertIn("locale/en/symbols-lexicalApostrophe.dic", names)
			self.assertIn("locale/zh_CN/symbols-lexicalApostrophe.dic", names)
			self.assertIn("locale/zh_HK/symbols-lexicalApostrophe.dic", names)
			self.assertIn("locale/zh_TW/symbols-lexicalApostrophe.dic", names)
			self.assertIn("locale/zh_CN/LC_MESSAGES/nvda.mo", names)
			self.assertIn("doc/zh_CN/readme.html", names)
			self.assertTrue(all(info.date_time == (1980, 1, 1, 0, 0, 0) for info in archive.infolist()))


if __name__ == "__main__":
	unittest.main()
