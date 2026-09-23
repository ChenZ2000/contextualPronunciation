"""Build a byte-for-byte reproducible NVDA add-on archive."""

from __future__ import annotations

import argparse
import re
import runpy
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

ROOT = Path(__file__).resolve().parents[1]
ADDON_ROOT = ROOT / "addon"
MANIFEST = ROOT / "manifest.ini"
DIST = ROOT / "dist"
_ZIP_TIMESTAMP = (1980, 1, 1, 0, 0, 0)


def _manifest_value(name: str, text: str) -> str:
	match = re.search(rf"(?m)^{re.escape(name)}[ \t]*=[ \t]*(.*)$", text)
	if not match:
		raise ValueError(f"Missing {name!r} in manifest.ini")
	value = match.group(1).strip()
	if value.startswith(('"""', "'''")):
		quote = value[:3]
		start = match.start(1) + 3
		end = text.find(quote, start)
		if end < 0:
			raise ValueError(f"Unclosed manifest field: {name}")
		return text[start:end].strip()
	if value.startswith(('"', "'")):
		if value[-1:] != value[:1]:
			raise ValueError(f"Unclosed manifest field: {name}")
		return value[1:-1]
	return value


def _write_file(archive: ZipFile, source: Path, destination: str) -> None:
	info = ZipInfo(destination, date_time=_ZIP_TIMESTAMP)
	info.compress_type = ZIP_DEFLATED
	info.create_system = 3
	info.external_attr = (0o100644 & 0xFFFF) << 16
	archive.writestr(info, source.read_bytes(), compress_type=ZIP_DEFLATED, compresslevel=9)


def checked_manifest() -> tuple[str, str, str]:
	manifest_text = MANIFEST.read_text(encoding="utf-8")
	name = _manifest_value("name", manifest_text)
	version = _manifest_value("version", manifest_text)
	metadata = runpy.run_path(str(ROOT / "buildVars.py"))["addon_info"]
	for field, key in (
		("name", "addon_name"),
		("summary", "addon_summary"),
		("description", "addon_description"),
		("author", "addon_author"),
		("url", "addon_url"),
		("changelog", "addon_changelog"),
		("version", "addon_version"),
		("minimumNVDAVersion", "addon_minimumNVDAVersion"),
		("lastTestedNVDAVersion", "addon_lastTestedNVDAVersion"),
	):
		if _manifest_value(field, manifest_text) != metadata[key]:
			raise ValueError(f"Manifest/build metadata mismatch: {field}; refusing to create/overwrite a package")
	return manifest_text, name, version


def build(*, output_dir: Path | None = None) -> Path:
	_manifest, name, version = checked_manifest()
	if not (ADDON_ROOT / "globalPlugins" / name / "__init__.py").is_file():
		raise FileNotFoundError(f"Global plugin package for {name!r} was not found")

	output_dir = DIST if output_dir is None else output_dir
	output_dir.mkdir(parents=True, exist_ok=True)
	output = output_dir / f"{name}-{version}.nvda-addon"
	with ZipFile(output, "w", compression=ZIP_DEFLATED, compresslevel=9) as archive:
		_write_file(archive, MANIFEST, "manifest.ini")
		for path in sorted(ADDON_ROOT.rglob("*")):
			if not path.is_file() or "__pycache__" in path.parts or path.suffix in {".pyc", ".pyo"}:
				continue
			destination = path.relative_to(ADDON_ROOT).as_posix()
			# The official SCons route generates this intermediate file. The
			# canonical root manifest above must remain the sole archive entry.
			if destination == "manifest.ini":
				continue
			_write_file(archive, path, destination)
	return output


if __name__ == "__main__":
	parser = argparse.ArgumentParser(description=__doc__)
	parser.add_argument("--output-dir", type=Path)
	print(build(output_dir=parser.parse_args().output_dir))
