"""Prepare deterministic public release assets; no publishing or Store writes."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import runpy
import tempfile
import tomllib
from pathlib import Path
from zipfile import ZipFile

from build_addon import ROOT, build, checked_manifest
from build_source_archive import build as build_source


def prepare(tag: str) -> dict:
	_manifest, name, version = checked_manifest()
	if not re.fullmatch(r"\d+\.\d+\.\d+", version) or tag != f"v{version}":
		raise ValueError("Release tag must be v plus the exact numeric manifest version")
	metadata = runpy.run_path(str(ROOT / "buildVars.py"))["addon_info"]
	project = tomllib.loads((ROOT / "pyproject.toml").read_text("utf-8"))["project"]
	if project["version"] != version:
		raise ValueError("pyproject.toml version differs from the manifest")
	if not (ROOT / "docs/releases" / f"{version}.md").is_file():
		raise ValueError("Versioned release notes are required")
	channel = metadata["addon_updateChannel"]
	if channel not in {"stable", "beta", "dev"}:
		raise ValueError("An explicit Store channel is required")
	for key in ("addon_url", "addon_sourceURL", "addon_licenseURL"):
		if not metadata[key].startswith("https://"):
			raise ValueError(f"HTTPS URL required: {key}")
	packages = []
	with tempfile.TemporaryDirectory() as directory:
		for builder in (build, build_source):
			path = builder()
			verification = builder(output_dir=Path(directory))
			if path.read_bytes() != verification.read_bytes():
				raise ValueError(f"Package is not reproducible: {path.name}")
			with ZipFile(path) as archive:
				names = archive.namelist()
				if len(names) != len(set(names)):
					raise ValueError("Duplicate archive entries")
				for entry in names:
					parts = Path(entry).parts
					if (
						any(part in {"vendor", "artifacts", "diagnostics", ".git", "__pycache__"} for part in parts)
						or Path(entry).suffix in {".dll", ".exe", ".wav", ".pyc", ".pem", ".key", ".log"}
						or any(part.startswith(".env") for part in parts)
					):
						raise ValueError(f"Forbidden release archive entry: {entry}")
			packages.append(
				{
					"name": path.name,
					"bytes": path.stat().st_size,
					"sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
				}
			)
	repository = metadata["addon_sourceURL"].rstrip("/")
	report = {
		"addonId": name,
		"version": version,
		"tag": tag,
		"channel": channel,
		"minimumNVDA": metadata["addon_minimumNVDAVersion"],
		"lastTestedNVDA": metadata["addon_lastTestedNVDAVersion"],
		"sourceURL": f"{repository}/tree/{tag}",
		"packages": packages,
		"acousticScope": "Public build checks do not certify proprietary voices or all synthesizers",
	}
	dist = ROOT / "dist"
	(dist / "release-metadata.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", "utf-8")
	(dist / "SHA256SUMS").write_text("".join(f"{p['sha256']}  {p['name']}\n" for p in packages), "utf-8")
	url = f"{repository}/releases/download/{tag}/{name}-{version}.nvda-addon"
	fields = (
		("Download URL", url),
		("Source URL", report["sourceURL"]),
		("Publisher", "ChenZ2000"),
		("Channel", channel),
		("License Name", "GPL-2.0-or-later"),
		("License URL", metadata["addon_licenseURL"]),
	)
	(dist / "store-submission.md").write_text(
		"\n\n".join(f"### {key}\n\n{value}" for key, value in fields) + "\n", "utf-8"
	)
	return report


if __name__ == "__main__":
	parser = argparse.ArgumentParser(description=__doc__)
	parser.add_argument("--tag", required=True)
	print(json.dumps(prepare(parser.parse_args().tag), ensure_ascii=False, indent=2))
