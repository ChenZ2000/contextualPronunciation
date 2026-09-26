"""Audit publication paths, credentials and current documentation links."""

from __future__ import annotations

import re
import subprocess
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
PRIVATE_ROOTS = {"vendor", "artifacts", "dist", "diagnostics", "private", "local", ".venv", ".git"}
PRIVATE_SUFFIXES = {".wav", ".mp3", ".flac", ".dmp", ".log", ".pem", ".key", ".pfx", ".p12", ".sqlite3"}
CURRENT_DOCS = (
	"README.md",
	"CONTRIBUTING.md",
	"CODE_OF_CONDUCT.md",
	"SECURITY.md",
	"CHANGELOG.md",
	"docs/README-en.md",
	"docs/README-zh_CN.md",
	"docs/USAGE-zh_CN.md",
	"docs/REFERENCES.md",
	"docs/DEVELOPMENT.md",
	"docs/RELEASING.md",
	"docs/INDEX.md",
)


def public_files() -> list[Path]:
	result = subprocess.run(
		["git", "-C", str(ROOT), "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
		check=True,
		capture_output=True,
	)
	return [ROOT / name.decode("utf-8") for name in result.stdout.split(b"\0") if name]


def check_paths(paths: list[Path]) -> None:
	for path in paths:
		relative = path.relative_to(ROOT)
		if (
			path.is_symlink()
			or relative.parts[0] in PRIVATE_ROOTS
			or "__pycache__" in relative.parts
			or path.suffix in PRIVATE_SUFFIXES
			or path.name.startswith(".env")
			and path.name != ".env.example"
		):
			raise ValueError(f"Private/generated path in publication: {relative.as_posix()}")
		if path.stat().st_size >= 50 * 1024 * 1024:
			raise ValueError(f"Unexpected large public file: {relative.as_posix()}")
		if path.suffix in {".gz", ".mo"}:
			continue
		value = path.read_bytes()
		patterns = (
			rb"gh[pousr]_" + rb"[A-Za-z0-9]{30,}",
			rb"github_pat_" + rb"[A-Za-z0-9_]{40,}",
			rb"-----BEGIN " + rb"(?:RSA |EC |OPENSSH )?PRIVATE KEY-----",
		)
		if any(re.search(pattern, value) for pattern in patterns):
			raise ValueError(f"Possible credential in {relative.as_posix()}; value intentionally omitted")
		if re.search(rb"[CD]:[/\\]Users[/\\](?!Public|Default)[^/\\\s]+", value):
			raise ValueError(f"Machine-specific user path in {relative.as_posix()}")


class Links(HTMLParser):
	def __init__(self):
		super().__init__()
		self.links: list[str] = []

	def handle_starttag(self, tag, attrs):
		for name, value in attrs:
			if name in {"href", "src"} and value:
				self.links.append(value)


def check_links() -> None:
	paths = [ROOT / name for name in CURRENT_DOCS]
	paths.extend((ROOT / "addon/doc").rglob("*.html"))
	missing = []
	for path in paths:
		text = path.read_text("utf-8")
		if path.suffix == ".html":
			parser = Links()
			parser.feed(text)
			links = parser.links
		else:
			links = re.findall(r"\[[^\]\n]*\]\(([^)\n]+)\)", text)
		for link in links:
			parsed = urlsplit(link)
			if parsed.scheme or parsed.netloc or not parsed.path:
				continue
			target = (path.parent / unquote(parsed.path)).resolve()
			if not target.is_relative_to(ROOT) or not target.exists():
				missing.append(f"{path.relative_to(ROOT).as_posix()}: {link}")
	if missing:
		raise ValueError("Broken current documentation links:\n" + "\n".join(missing))


def main() -> None:
	paths = public_files()
	check_paths(paths)
	check_links()
	print(f"Publication audit passed: {len(paths)} files; current guides and installed HTML links resolve")


if __name__ == "__main__":
	main()
