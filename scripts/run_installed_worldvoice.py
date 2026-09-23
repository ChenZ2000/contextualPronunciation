"""Test the user's installed WorldVoice source without loading its live profile.

Uses real installed pipeline/detector/speak code in an isolated subprocess with
in-memory voices. This is explicitly NOT a live audio or GUI acceptance test.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UPSTREAM = ROOT / "vendor/WorldVoice/addon/synthDrivers/WorldVoice"


def main():
	parser = argparse.ArgumentParser(description=__doc__)
	parser.add_argument("--addon", type=Path, required=True)
	args = parser.parse_args()
	addon = args.addon.resolve()
	manifest = (addon / "manifest.ini").read_text("utf-8-sig")
	match = re.search(r'^version\s*=\s*["\']?([^"\'\r\n]+)', manifest, re.M)
	version = match.group(1).strip() if match else None
	if version != "6.2":
		raise ValueError("Installed source must be reviewed WorldVoice 6.2")
	source = addon / "synthDrivers/WorldVoice"
	# These Python modules may be imported transitively by the source harness.
	paths = [source / "__init__.py", source / "_speechcommand.py"]
	for directory in ("pipeline", "languageDetection"):
		paths.extend(sorted((source / directory).rglob("*.py")))
	if len(paths) < 5 or not all(path.is_file() for path in paths):
		raise ValueError("Incomplete installed WorldVoice sources")
	source_hashes, differences = {}, []
	for path in paths:
		relative = path.relative_to(source).as_posix()
		content = path.read_bytes()
		source_hashes[relative] = hashlib.sha256(content).hexdigest()
		# Store raw installed hashes, but compare source meaning across CRLF/LF.
		if path.read_text("utf-8-sig") != (UPSTREAM / relative).read_text("utf-8-sig"):
			differences.append(relative)
	if differences:
		raise ValueError(f"Installed code differs from reviewed source, preserved for review: {differences}")
	environment = dict(os.environ, CONTEXTUAL_WORLDVOICE_SOURCE=str(source))
	result = subprocess.run(
		[sys.executable, "-m", "unittest", "tests.test_worldvoice", "tests.test_global_plugin_integration", "-v"],
		cwd=ROOT,
		env=environment,
		text=True,
		encoding="utf-8",
		errors="replace",
		capture_output=True,
	)
	log = ROOT / "artifacts/installed-worldvoice-tests.log"
	log.write_text(result.stdout + result.stderr, "utf-8")
	from run_tests import source_hashes as project_source_hashes

	count = re.search(r"Ran (\d+) tests", result.stderr)
	report = {
		"testedAtUtc": datetime.now(UTC).isoformat(),
		"version": version,
		"installedAddon": str(addon),
		"sourceDirectory": str(source),
		"upstreamTextMatches": not differences,
		"installedFilesSha256": source_hashes,
		"sourceSha256": project_source_hashes(),
		"testsRun": int(count.group(1)) if count else 0,
		"passed": result.returncode == 0 and count is not None and "skipped=" not in result.stderr,
		"logSha256": hashlib.sha256(log.read_bytes()).hexdigest(),
		"scope": (
			"Installed source-chain only; substitute voices; "
			"no real WorldVoice audio, UI or saved user configuration loaded"
		),
	}
	(ROOT / "artifacts/installed-worldvoice.json").write_text(
		json.dumps(report, ensure_ascii=False, indent=2) + "\n", "utf-8"
	)
	print(result.stdout + result.stderr)
	return 0 if report["passed"] else 1


if __name__ == "__main__":
	raise SystemExit(main())
