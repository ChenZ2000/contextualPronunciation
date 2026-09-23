"""Fetch an immutable NVDA checkout without resetting or overwriting local work."""

from __future__ import annotations

import argparse
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NVDA_VERSION = os.environ.get("CONTEXTUAL_PRONUNCIATION_NVDA_VERSION", "2026.2")
NVDA_COMMITS = {
	"2026.2": "f62c980589d1ac30babf68ad48177e9ad29a2e84",
	"2026.3beta2": "b416601eecd01813e9dd89ca9e85cb914acd936a",
}
if NVDA_VERSION not in NVDA_COMMITS:
	raise ValueError("Only explicitly pinned NVDA targets may be built/tested")
NVDA = ROOT / "vendor" / f"nvda-{NVDA_VERSION}"
NVDA_COMMIT = NVDA_COMMITS[NVDA_VERSION]
NVDA_URL = "https://github.com/nvaccess/nvda.git"


def git(*arguments: str, capture: bool = False) -> str:
	result = subprocess.run(["git", "-C", str(NVDA), *arguments], check=True, text=True, capture_output=capture)
	return result.stdout.strip() if capture else ""


def prepare(*, submodules: bool = False) -> None:
	if not (NVDA / ".git").exists():
		if NVDA.exists() and any(NVDA.iterdir()):
			raise RuntimeError(f"Refusing to overwrite non-repository directory: {NVDA}")
		NVDA.mkdir(parents=True, exist_ok=True)
		git("init")
		git("remote", "add", "origin", NVDA_URL)
		git("fetch", "--depth=1", "origin", NVDA_COMMIT)
		git("checkout", "--detach", NVDA_COMMIT)
	if git("rev-parse", "HEAD", capture=True) != NVDA_COMMIT:
		raise RuntimeError("NVDA revision differs from the tested pin; preserve local work and use a separate checkout")
	if git("status", "--porcelain", "--untracked-files=no", capture=True):
		raise RuntimeError("NVDA has tracked changes; refusing to refresh/build a modified checkout")
	if submodules:
		git("submodule", "update", "--init", "--recursive", "--jobs", "4")
	print(f"Verified NVDA {NVDA_VERSION}: {NVDA_COMMIT}")


if __name__ == "__main__":
	parser = argparse.ArgumentParser(description=__doc__)
	parser.add_argument("--submodules", action="store_true")
	args = parser.parse_args()
	prepare(submodules=args.submodules)
