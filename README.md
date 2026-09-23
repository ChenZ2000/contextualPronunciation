# Context-aware Pronunciation for NVDA

[中文使用说明](docs/README-zh_CN.md) · [English user guide](docs/README-en.md) · [Download](https://github.com/ChenZ2000/contextualPronunciation/releases/latest) · [Report a problem](https://github.com/ChenZ2000/contextualPronunciation/issues)

An offline NVDA add-on that corrects selected Mandarin polyphonic characters using lexical evidence and bounded grammatical analysis. It also preserves apostrophes inside words such as `doesn't`. It works through NVDA's public speech extension points, without changing the active synthesizer or original document.

Examples include 重转 / 重吸收 (`chóng`), 盛了一碗饭 (`chéng`), 天兵和天将 (`jiàng`), 下边缘 (`biān`), 唱和说 (`hé`), and 多行文本 (`háng`). The grammar also checks counterexamples such as 重视, 附和说法 and 多行不义. These examples describe supported contexts, not perfect interpretation of arbitrary Chinese.

## Install

1. Download the `.nvda-addon` asset from [GitHub Releases](https://github.com/ChenZ2000/contextualPronunciation/releases/latest), then open it with NVDA.
2. Restart NVDA when prompted. Version **0.7.4** requires NVDA **2026.2** and declares that stable API as last tested. NVDA **2026.3beta2** is an additional CI target, not a declaration that a future final API has been tested.
3. Open NVDA Settings → **Context-aware pronunciation**. Contextual rewriting, supported Chinese corrections and strict mode are enabled by default. The extended phrase lexicon is experimental and off by default.

Add-on Store availability depends on NV Access accepting the submission. A GitHub Release is usable independently of Store approval. See [the release and submission process](docs/RELEASING.md).

## Behavior and limits

- Speech is analyzed before rendering. A public queue listener rechecks residual 和 / 边 / 邊 / 行 targets after NVDA dictionaries and symbols have run. Commands and spelling mode are preserved; context does not cross command boundaries.
- Pronunciation is rendered using temporary homophones because synthesizers do not share a general external token or phoneme interface. Speech Viewer may show the temporary text. Documents, the clipboard and accessibility objects remain unchanged.
- Mandarin rules apply regardless of voice or language tag. They can be inappropriate for Cantonese, Japanese or other readings of Han characters; use the Chinese correction switch, a configuration profile, or local `keep` rules.
- No network service, speech recording, telemetry, neural model or runtime database is used. Unknown or ambiguous cases can remain unchanged. There is no promise of zero latency or universal accuracy.
- An optional experimental Chinese common braille 2018 table provides fixed reviewed contexts. It does not dynamically consume the speech parser or custom speech settings and is not a complete implementation of every standard provision.
- Disabling contextual rewriting leaves the mandatory apostrophe symbol dictionary installed. Disable or uninstall the add-on and restart NVDA to remove that dictionary as well.

The current engine has **1,154 project-authored reading/preservation cases** and additional command, settings, Unicode, packaging and integration tests. The corpus is a regression suite, not an open-domain accuracy measurement. Cloud CI cannot certify every voice or run proprietary Vocalizer audio checks.

## Build and develop

Use Python 3.13 (64-bit), Git and [uv](https://docs.astral.sh/uv/). Run from the repository root:

```powershell
python scripts/prepare_nvda.py
python scripts/prepare_worldvoice.py
python scripts/prepare_cpp.py
python scripts/run_tests.py
python tools/evaluate_grammar.py
python scripts/build_addon.py
python scripts/build_source_archive.py
```

The source snapshots and their licenses are committed, so the package builder itself needs only Python's standard library. Development integrations fetch pinned open-source dependencies into ignored `vendor/`. Building NVDA's native components additionally requires its documented Visual Studio/Windows SDK/Clang toolchain.

```powershell
# Native NVDA tests, reproducible data, lint and performance checks
python scripts/run_regression.py --native --jobs 2
# Local acoustic verification additionally needs a licensed installed voice
python scripts/run_regression.py --native --vocalizer --release --jobs 2
```

See [development and architecture](docs/DEVELOPMENT.md), [release instructions](docs/RELEASING.md), and [contribution guidelines](CONTRIBUTING.md). Public CI runs stable and beta native targets. Version tags publish reproducible add-on/source archives and SHA-256 checksums only after both targets pass. No proprietary voice data or credentials are required by GitHub Actions.

## Repository layout

| Path | Purpose |
|---|---|
| `addon/` | Installable `globalPlugins`, symbol dictionaries, translations, help, licenses and optional braille table |
| `manifest.ini`, `buildVars.py` | Matching NVDA manifest and template-compatible build metadata |
| `data/sources/`, `data/` | Attributed, pinned dictionary snapshots and generated audit data |
| `tests/` | Unit, grammar and acoustic input fixtures; no captured speech |
| `scripts/`, `tools/` | Reproducible packaging, integrations, data generators and offline probes |
| `docs/` | Current community guides and clearly identified historical design notes |
| `.github/` | Native CI, tag-based releases, issue/PR templates and dependency updates |

Generated packages, recordings, downloaded dependencies, local diagnostics, credentials and private configuration are ignored. [Documentation index](docs/INDEX.md).

## License and maintenance

Maintained by [ChenZ2000](https://github.com/ChenZ2000). Support and pronunciation reports belong in [GitHub Issues](https://github.com/ChenZ2000/contextualPronunciation/issues); English and Chinese are welcome.

Program code is **GPL-2.0-or-later**; see [LICENSE](LICENSE). Dictionary data retains its separate CC-BY-SA-4.0, CC-BY-3.0, Unicode and MIT terms. See [third-party notices](addon/THIRD-PARTY-NOTICES.txt) for attribution, modifications, source pins and full license locations. Inclusion of a source does not imply its authors endorse this add-on.
