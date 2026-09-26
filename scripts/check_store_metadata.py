"""Validate local release bytes with an explicitly provided official Store checkout.

This pre-publication check uses upstream schema/manifest/API validators. It does
not download a release or submit an issue. Run the upstream full URL validation
after the release is public, as documented in docs/RELEASING.md.
"""

from __future__ import annotations

import argparse
import json
import runpy
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def check(validator_root: Path) -> None:
	validator_root = validator_root.resolve()
	sys.path.insert(0, str(validator_root / "validation"))
	from _validate import validate
	from _validate.createJson import generateJsonFile
	from _validate.manifestLoader import getAddonManifest

	metadata = runpy.run_path(str(ROOT / "buildVars.py"))["addon_info"]
	version, name = metadata["addon_version"], metadata["addon_name"]
	package = ROOT / "dist" / f"{name}-{version}.nvda-addon"
	manifest = getAddonManifest(str(package))
	if manifest.errors:
		raise ValueError(f"Official NVDA manifest validation failed: {manifest.errors}")
	repository = metadata["addon_sourceURL"].rstrip("/")
	output = ROOT / "artifacts/store-metadata"
	generateJsonFile(
		manifest,
		str(package),
		str(output),
		metadata["addon_updateChannel"],
		"ChenZ2000",
		f"{repository}/releases/tag/v{version}",
		f"{repository}/releases/download/v{version}/{package.name}",
		"GPL-2.0-or-later",
		metadata["addon_licenseURL"],
	)
	path = output / name / f"{version}.json"
	data = validate.getAddonMetadata(str(path))
	versions = str(validator_root / "transform/nvdaAPIVersions.json")
	errors = [
		*validate.checkDownloadUrlFormat(data["URL"]),
		*validate.checkSha256(str(package), data["sha256"]),
		*validate.checkLastTestedVersionExist(data, versions),
		*validate.checkMinRequiredVersionExist(data, versions),
		*validate.checkSummaryMatchesDisplayName(manifest, data),
		*validate.checkDescriptionMatches(manifest, data),
		*validate.checkChangelogMatches(manifest, data),
		*validate.checkUrlMatchesHomepage(manifest, data),
		*validate.checkAddonId(manifest, str(path), data),
		*validate.checkMinNVDAVersionMatches(manifest, data),
		*validate.checkLastTestedNVDAVersionMatches(manifest, data),
		*validate.checkVersions(manifest, str(path), data),
	]
	if errors:
		raise ValueError("Official Store validation failed:\n" + "\n".join(errors))
	print(
		json.dumps(
			{"passed": True, "scope": "Official local-byte/schema/API checks; no URL download", "version": version}
		)
	)


if __name__ == "__main__":
	parser = argparse.ArgumentParser(description=__doc__)
	parser.add_argument("--validator-root", type=Path, required=True)
	check(parser.parse_args().validator_root)
