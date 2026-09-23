"""Fetch only pinned, licensed CPP held-out test text/labels; never load a model."""

from __future__ import annotations

import hashlib
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CPP = ROOT / "vendor/g2pM"
COMMIT = "170526efad0a3ef9b55a9ad4579f73218f9be06c"
# Immutable Git blob bytes use LF. Existing Windows audit evidence uses CRLF;
# verify both sides of that explicit conversion, never accept an unknown hash.
UPSTREAM_HASHES = {
	"data/test.sent": "c34e2073b0c7e468b92903b021a7d42bacc87f88ea6c06863e9fa5cdfd727cbe",
	"data/test.lb": "1101ba8bb0842b4fe273690c4c1899cdaf656ee1d79ebba4fb8dc10fbcc598f8",
	"LICENSE": "c71d239df91726fc519c6eb72d318ec65820627232b2f796219e87dcf35d0ab4",
}
HASHES = {
	"data/test.sent": "b7861d19e025a4ecb5ed24a9f7f6b11108400170e48cf32069c1263264d81907",
	"data/test.lb": "30a661a5bfd8964a9f40ae824acfcf3c820dc59d54489fa0e236ec277d280e7d",
	"LICENSE": "1eb85fc97224598dad1852b5d6483bbcf0aa8608790dcc657a5a2a761ae9c8c6",
}


def prepare(*, download: bool = True):
	for relative, expected in HASHES.items():
		path = CPP / relative
		if not path.exists() and download:
			url = f"https://raw.githubusercontent.com/kakaobrain/g2pM/{COMMIT}/{relative}"
			with urllib.request.urlopen(url, timeout=60) as response:
				content = response.read(8_000_001)
			if len(content) > 8_000_000 or hashlib.sha256(content).hexdigest() != UPSTREAM_HASHES[relative]:
				raise ValueError(f"Unverified CPP download: {relative}")
			content = content.replace(b"\n", b"\r\n")
			if hashlib.sha256(content).hexdigest() != expected:
				raise ValueError(f"CPP line-ending projection differs from audit evidence: {relative}")
			path.parent.mkdir(parents=True, exist_ok=True)
			path.write_bytes(content)
		if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
			raise ValueError(f"Missing/changed CPP source preserved: {relative}; run scripts/prepare_cpp.py")
	print(f"Verified CPP test data: {COMMIT}")


if __name__ == "__main__":
	prepare()
