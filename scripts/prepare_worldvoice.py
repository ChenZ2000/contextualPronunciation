"""Fetch the pinned latest stable WorldVoice used by compatibility tests."""

from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORLDVOICE = ROOT / "vendor/WorldVoice"
COMMIT = "318bc90bf8a7af9e901bb43cd7da036533f443ea"
URL = "https://github.com/tsengwoody/WorldVoice.git"


def prepare():
	def git(*args):
		return subprocess.run(
			["git", "-C", str(WORLDVOICE), *args], check=True, capture_output=True, text=True
		).stdout.strip()

	if not (WORLDVOICE / ".git").exists():
		if WORLDVOICE.exists() and any(WORLDVOICE.iterdir()):
			raise RuntimeError("Refusing to overwrite a non-repository WorldVoice directory")
		WORLDVOICE.mkdir(parents=True, exist_ok=True)
		git("init")
		git("remote", "add", "origin", URL)
		git("fetch", "--depth=1", "origin", COMMIT)
		git("checkout", "--detach", COMMIT)
	if git("rev-parse", "HEAD") != COMMIT or git("status", "--porcelain", "--untracked-files=no"):
		raise RuntimeError("WorldVoice differs from its tested pin; local changes were preserved")
	print(f"Verified WorldVoice 6.2: {COMMIT}")


if __name__ == "__main__":
	prepare()
