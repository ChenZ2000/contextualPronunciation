"""Build a reproducible source bundle without vendor code, DLLs or voice data."""

from __future__ import annotations

import argparse
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from build_addon import ROOT, _write_file, checked_manifest


def build(*, output_dir: Path | None = None) -> Path:
	_manifest, name, version = checked_manifest()
	prefix = f"{name}-{version}"
	output_dir = ROOT / "dist" if output_dir is None else output_dir
	output = output_dir / f"{prefix}-source.zip"
	output.parent.mkdir(exist_ok=True)
	# Explicit roots avoid accidentally bundling a future .env or user note.
	root_files = (
		"README.md",
		"LICENSE",
		"CONTRIBUTING.md",
		"CODE_OF_CONDUCT.md",
		"SECURITY.md",
		"CHANGELOG.md",
		"build.ps1",
		"buildVars.py",
		"manifest.ini",
		"manifest.ini.tpl",
		"manifest-translated.ini.tpl",
		"pyproject.toml",
		".gitignore",
		".gitattributes",
	)
	paths = [ROOT / name for name in root_files]
	for directory in ("addon", "data", "docs", "scripts", "tests", "tools", ".github"):
		paths.extend(path for path in (ROOT / directory).rglob("*") if path.is_file())
	with ZipFile(output, "w", compression=ZIP_DEFLATED, compresslevel=9) as archive:
		for path in sorted(paths):
			if "__pycache__" in path.parts or path.suffix in {".pyc", ".pyo"}:
				continue
			_write_file(archive, path, f"{prefix}/{path.relative_to(ROOT).as_posix()}")
	return output


if __name__ == "__main__":
	parser = argparse.ArgumentParser(description=__doc__)
	parser.add_argument("--output-dir", type=Path)
	print(build(output_dir=parser.parse_args().output_dir))
