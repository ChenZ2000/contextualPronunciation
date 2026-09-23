"""Cache a checksum-pinned official actionlint binary; no Go proxy or installation."""

from __future__ import annotations

import hashlib
import urllib.request
from pathlib import Path
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
VERSION = "1.7.12"
ASSET_SHA256 = "6e7241b51e6817ea6a047693d8e6fed13b31819c9a0dd6c5a726e1592d22f6e9"
CACHE = ROOT / "vendor" / f"actionlint-{VERSION}"
ARCHIVE = CACHE / f"actionlint_{VERSION}_windows_amd64.zip"
EXECUTABLE = CACHE / "actionlint.exe"
URL = f"https://github.com/rhysd/actionlint/releases/download/v{VERSION}/{ARCHIVE.name}"


def prepare() -> Path:
	CACHE.mkdir(parents=True, exist_ok=True)
	if not ARCHIVE.exists():
		with urllib.request.urlopen(URL, timeout=60) as response:
			payload = response.read()
		if hashlib.sha256(payload).hexdigest() != ASSET_SHA256:
			raise ValueError("Official actionlint download checksum mismatch")
		ARCHIVE.write_bytes(payload)
	if hashlib.sha256(ARCHIVE.read_bytes()).hexdigest() != ASSET_SHA256:
		raise ValueError("Cached actionlint archive changed; inspect it instead of silently overwriting")
	with ZipFile(ARCHIVE) as archive:
		# Read exactly one known member. Never extract an unvalidated path tree.
		binary = archive.read("actionlint.exe")
	if EXECUTABLE.exists():
		if EXECUTABLE.read_bytes() != binary:
			raise ValueError("Cached actionlint executable changed; refusing to run it")
	else:
		EXECUTABLE.write_bytes(binary)
	return EXECUTABLE


if __name__ == "__main__":
	print(prepare())
