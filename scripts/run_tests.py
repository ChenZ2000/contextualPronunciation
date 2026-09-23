"""Strict add-on test gate: missing NVDA sources must fail, not silently skip."""

from __future__ import annotations

import hashlib
import json
import platform
import sys
import unicodedata
import unittest
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def source_hashes() -> dict[str, str]:
	paths = [
		p
		for directory in ("addon", "data", "docs", "tests", "tools", "scripts", ".github")
		for p in (ROOT / directory).rglob("*")
		if p.is_file()
		and p.suffix
		in {
			".py",
			".ps1",
			".dic",
			".json",
			".yml",
			".html",
			".po",
			".mo",
			".ini",
			".gz",
			".txt",
			".toml",
			".md",
			".ctb",
			".tsv",
		}
		and "__pycache__" not in p.parts
	]
	paths.extend(
		ROOT / name
		for name in ("README.md", "manifest.ini", "buildVars.py", "pyproject.toml", "build.ps1", ".gitattributes")
	)
	return {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(paths)}


def main() -> int:
	suite = unittest.defaultTestLoader.discover(str(ROOT / "tests"))
	result = unittest.TextTestRunner(verbosity=2).run(suite)
	from tests.test_boundaries import boundary_characters

	boundary_counts: dict[str, int] = {}
	for character in boundary_characters():
		category = unicodedata.category(character)
		boundary_counts[category] = boundary_counts.get(category, 0) + 1
	report = {
		"testedAtUtc": datetime.now(UTC).isoformat(),
		"python": platform.python_version(),
		"unicodeVersion": unicodedata.unidata_version,
		"testsRun": result.testsRun,
		"failures": len(result.failures),
		"errors": len(result.errors),
		"skipped": len(result.skipped),
		"passed": result.wasSuccessful() and not result.skipped,
		"boundaryCodepointsExhausted": sys.maxunicode + 1,
		"acceptedBoundariesByCategory": boundary_counts,
		"sourceSha256": source_hashes(),
	}
	output = ROOT / "artifacts/addon-tests.json"
	output.parent.mkdir(exist_ok=True)
	output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", "utf-8")
	print(f"Strict test report: {output}")
	return 0 if report["passed"] else 1


if __name__ == "__main__":
	raise SystemExit(main())
