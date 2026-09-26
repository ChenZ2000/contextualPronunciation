# Context-aware Pronunciation for NVDA

English · [简体中文](docs/README-zh_CN.md)

Improve Mandarin pronunciation in NVDA with context-aware corrections for polyphonic characters. The add-on uses word boundaries, dictionary readings and sentence structure to select a reading before speech reaches your current synthesizer. It also preserves apostrophes in English words such as `doesn't` and `Mike's`.

[Download](https://github.com/ChenZ2000/contextualPronunciation/releases/latest) · [User guide](docs/README-en.md) · [Report a problem](https://github.com/ChenZ2000/contextualPronunciation/issues) · [Changelog](CHANGELOG.md)

## Features

- **Contextual Chinese pronunciation.** Handles repeated actions, quantities, modified objects and coordinated phrases, using both reviewed rules and dictionary evidence.
- **Personal rules.** Set a reading for a particular context or preserve the original text for your existing speech dictionary.
- **Offline operation.** Processes speech locally without uploading or recording the text being read.
- **Optional extensions.** An experimental phrase lexicon adds lexical coverage; an optional Chinese common braille 2018 table adds corrections for fixed contexts.

Examples supported by the default settings:

| Context | Selected reading |
|---|---|
| 重转、重吸收、重捏、重飞 | 重 → chóng, repeating an action |
| 也给我盛了一碗、盛那碗刚刚煮好的红豆粥 | 盛 → chéng, serving or containing |
| 天兵和天将一起去吃饭 | 将 → jiàng, a military noun |
| 系那条又细又长的红色丝带、量小名的身高 | 系 → jì; 量 → liáng |
| 下边缘、唱和说、多行文本 | 边 → biān; 和 → hé; 行 → háng |

The engine preserves ambiguous or unsupported text for the synthesizer to read. See the [user guide](docs/README-en.md) for voice settings, custom rules and troubleshooting.

## Install and use

The current release is **0.7.4**, with **NVDA 2026.2** as its minimum and last-tested stable version. CI also tests **2026.3beta2**.

1. Download the `.nvda-addon` file from [Releases](https://github.com/ChenZ2000/contextualPronunciation/releases/latest).
2. Open the file, accept NVDA's installation prompt and restart NVDA when prompted.
3. Continue reading with your usual Mandarin voice. The default corrections take effect automatically.
4. Open **NVDA Settings → Context-aware pronunciation** to adjust the behavior. Contextual rewriting, Chinese corrections and strict mode start enabled. The experimental phrase lexicon starts disabled.

Chinese corrections specify Mandarin readings for every voice and language tag. For Cantonese, Japanese or another reading of Han characters, turn off Chinese corrections in the relevant NVDA configuration profile.

The add-on sends temporary pronunciation text to the synthesizer, so Speech Viewer may show substitute characters. Your document and clipboard text stay unchanged. To remove all add-on behavior, including apostrophe protection, disable or uninstall the add-on and restart NVDA.

## How it works

1. NVDA supplies a speech sequence through its public extension points.
2. The engine segments text, checks lexical and grammatical evidence, and chooses readings at positions in the original text. Speech commands and spelling mode are preserved.
3. Selected readings are rendered through temporary homophones. A final check after NVDA's speech dictionaries and symbol processing protects supported 和 / 边 / 邊 / 行 contexts from further misreading.

The implementation and test strategy are described in [Development and architecture](docs/DEVELOPMENT.md).

## Repository structure

| Location | What to maintain here |
|---|---|
| [`addon/globalPlugins/contextualPronunciation/`](addon/globalPlugins/contextualPronunciation/) | Speech integration, settings, segmentation and grammar engine |
| [`addon/globalPlugins/contextualPronunciation/data/`](addon/globalPlugins/contextualPronunciation/data/) | Reviewed rules, templates and generated runtime lexicons |
| [`addon/`](addon/) | Installed help, translations, symbol dictionaries and braille table |
| [`data/`](data/), [`tools/`](tools/) | Source dictionaries, attribution, data generators and analysis tools |
| [`tests/`](tests/), [`scripts/`](scripts/) | Regression cases, integration checks and package builders |
| [`.github/workflows/`](.github/workflows/) | Native NVDA CI and release automation |
| [`docs/`](docs/), [`CONTRIBUTING.md`](CONTRIBUTING.md) | User guides, architecture, release process and contribution instructions |

## Build and contribute

To build an installable package, use Windows, Git and **64-bit Python 3.13**:

```powershell
git clone https://github.com/ChenZ2000/contextualPronunciation.git
cd contextualPronunciation
python scripts/build_addon.py
```

The package is written to `dist/`. This packaging command uses Python's standard library and the data already in the repository.

For development, follow the [setup and test commands](docs/DEVELOPMENT.md#requirements-and-first-build). Pronunciation changes should include the dictionary source, a sentence needing correction and a contrasting sentence that must keep its reading. [CONTRIBUTING.md](CONTRIBUTING.md) covers rules, translations, documentation and pull requests.

`main` is the maintained development and release branch. The maintenance cycle is:

1. Submit a PR to `main` with relevant tests. CI builds and tests the pinned stable and beta NVDA targets.
2. For a release, update `manifest.ini`, `buildVars.py`, `pyproject.toml` and the release notes. Merge the changes and wait for CI on that `main` commit.
3. Run **Actions → Publish release from main**. The workflow creates the version tag and Release with packages, checksums and Store submission fields.
4. Submit those fields through NV Access's registration form. The official bot creates the Store PR for review.

See [the release guide](docs/RELEASING.md) for the complete procedure.

## Sources and references

The pronunciation and grammar data comes from these projects:

| Source | Use in this add-on |
|---|---|
| [CC-CEDICT / MDBG](https://www.mdbg.net/chinese/dictionary?page=cedict) | Word forms, pinyin and verb-sense evidence |
| [KFCD open Chinese dictionary](https://github.com/kfcd/hyzd) | Character senses and readings in examples |
| [Unicode Unihan](https://www.unicode.org/reports/tr38/tr38-39.html) | Character-reading cross-checks and polyphone inventory |
| [OpenHowNet / THUNLP](https://github.com/thunlp/OpenHowNet) | Part-of-speech candidates and semantic classes such as food and containers |
| [cppjieba](https://github.com/yanyiwu/cppjieba) | Word frequencies for segmentation and part-of-speech candidates |

The [reference guide](docs/REFERENCES.md#english) records snapshot versions, licenses, generated files, linguistic references and test dependencies. It also explains the use of Ministry of Education dictionaries, Universal Dependencies Chinese, GF 0019-2018, NVDA, WorldVoice and the CPP benchmark.

## Support and license

Maintained by [ChenZ2000](https://github.com/ChenZ2000). Reports and contributions in English or Chinese are welcome. For a pronunciation problem, include the sentence, expected and actual readings, NVDA/add-on versions, voice and relevant settings in [an issue](https://github.com/ChenZ2000/contextualPronunciation/issues).

Program code is **GPL-2.0-or-later**; see [LICENSE](LICENSE). Dictionary data retains its source licenses and attribution in [Third-party notices](addon/THIRD-PARTY-NOTICES.txt). Browse all current guides and historical design notes in the [documentation index](docs/INDEX.md).
