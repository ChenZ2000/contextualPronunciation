"""Generate installed help from the canonical user guides (Python-Markdown 3.10.2)."""

from __future__ import annotations

import argparse
import html
import posixpath
import re
from pathlib import Path
from urllib.parse import quote, urlsplit, urlunsplit

ROOT = Path(__file__).resolve().parents[1]
GUIDES = {"en": "docs/README-en.md", "zh_CN": "docs/USAGE-zh_CN.md"}
STYLE = """
body { max-width: 64rem; margin: auto; padding: 1.5rem; font: 1rem/1.65 system-ui, sans-serif;
  color: #17212b; background: #fff; overflow-wrap: anywhere; }
a { color: #0055a4; } a:focus-visible { outline: 3px solid #9b4300; outline-offset: 3px; }
table { border-collapse: collapse; width: 100%; } th, td { border: 1px solid #687785;
  padding: .5rem; text-align: left; vertical-align: top; }
pre { white-space: pre-wrap; padding: 1rem; background: #f1f4f7; }
code { font-family: ui-monospace, monospace; } nav { border-bottom: 1px solid #687785; }
"""


def help_link(url, source, locale):
	parts = urlsplit(html.unescape(url))
	if parts.scheme or parts.netloc or not parts.path:
		return url
	path = posixpath.normpath(posixpath.join(posixpath.dirname(source), parts.path))
	for target_locale, guide in GUIDES.items():
		if path == guide:
			local = "readme.html" if target_locale == locale else f"../{target_locale}/readme.html"
			return html.escape(urlunsplit(("", "", local, parts.query, parts.fragment)), quote=True)
	# Contributor/reference files are available in the repository, not bundled
	# as stale development reports in the user-facing help.
	web = "https://github.com/ChenZ2000/contextualPronunciation/blob/main/" + quote(path)
	return html.escape(urlunsplit((*urlsplit(web)[:3], parts.query, parts.fragment)), quote=True)


def generate(source, locale):
	import markdown

	if markdown.__version__ != "3.10.2":
		raise ValueError("Use Python-Markdown 3.10.2 for reproducible installed help")
	md = markdown.Markdown(extensions=["tables", "fenced_code", "toc"], extension_configs={"toc": {"toc_depth": "2-3"}})
	body = md.convert((ROOT / source).read_text("utf-8"))
	body = re.sub(r'href="([^"]+)"', lambda m: 'href="' + help_link(m[1], source, locale) + '"', body)
	body = body.replace("<th>", '<th scope="col">')
	chinese = locale == "zh_CN"
	title = "上下文发音规范化使用指南" if chinese else "Context-aware Pronunciation user guide"
	contents = "目录" if chinese else "Contents"
	skip = "跳到正文" if chinese else "Skip to content"
	lang = "zh-CN" if chinese else "en"
	return (
		f'<!doctype html>\n<html lang="{lang}">\n<head>\n<meta charset="utf-8">\n'
		'<meta name="viewport" content="width=device-width, initial-scale=1">\n'
		f"<title>{title}</title>\n<style>{STYLE}</style>\n</head>\n<body>\n"
		f"<!-- Generated from {source} by tools/build_user_help.py. -->\n"
		f'<a href="#content">{skip}</a>\n<nav aria-label="{contents}">{md.toc}</nav>\n'
		f'<main id="content">\n{body}\n</main>\n</body>\n</html>\n'
	).encode()


def main():
	parser = argparse.ArgumentParser(description=__doc__)
	parser.add_argument("--check", action="store_true")
	args = parser.parse_args()
	for locale, source in GUIDES.items():
		output = ROOT / "addon/doc" / locale / "readme.html"
		content = generate(source, locale)
		if args.check:
			if output.read_bytes() != content:
				raise ValueError(f"Stale installed help: {output.relative_to(ROOT)}")
		else:
			output.write_bytes(content)
	print("Installed user guides: English and Simplified Chinese are current")


if __name__ == "__main__":
	main()
