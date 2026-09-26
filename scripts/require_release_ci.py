"""Require a successful main-branch push workflow for the exact release commit."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path


def verified_run(runs: list[dict], commit: str) -> dict:
	if not re.fullmatch(r"[0-9a-f]{40}", commit):
		raise ValueError("Expected a full Git commit SHA")
	for run in runs:
		if (
			run.get("headSha") == commit
			and run.get("headBranch") == "main"
			and run.get("event") == "push"
			and run.get("status") == "completed"
			and run.get("conclusion") == "success"
		):
			return {"commit": commit, "runId": run["databaseId"], "url": run["url"]}
	# No success may be inferred from a PR, another commit or a partial run.
	raise ValueError("Wait for the exact main commit's complete native regression to pass before publishing")


def main() -> None:
	parser = argparse.ArgumentParser(description=__doc__)
	parser.add_argument("--repository", required=True)
	args = parser.parse_args()
	commit = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
	output = subprocess.check_output(
		[
			"gh",
			"run",
			"list",
			"--repo",
			args.repository,
			"--workflow",
			"regression.yml",
			"--commit",
			commit,
			"--event",
			"push",
			"--limit",
			"30",
			"--json",
			"databaseId,headSha,headBranch,event,status,conclusion,url",
		],
		text=True,
	)
	result = verified_run(json.loads(output), commit)
	Path("dist").mkdir(exist_ok=True)
	Path("dist/ci-verification.json").write_text(json.dumps(result, indent=2) + "\n", "utf-8")
	print(json.dumps(result))


if __name__ == "__main__":
	main()
