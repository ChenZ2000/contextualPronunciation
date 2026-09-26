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

### Install and enable

The current release is **0.7.4**, with **NVDA 2026.2** as its minimum and last-tested stable version. CI also tests **2026.3beta2**.

1. Download the `.nvda-addon` file from [Releases](https://github.com/ChenZ2000/contextualPronunciation/releases/latest).
2. Open the file, accept NVDA's installation prompt and restart NVDA when prompted.
3. Continue reading with your usual Mandarin voice. The default corrections take effect automatically.
4. Open **NVDA Settings → Context-aware pronunciation** to adjust the options below. Click **Apply** or **OK** to use the new settings immediately.

### Settings

| Option | Default | What it does |
|---|---|---|
| Enable contextual pronunciation rewriting | On | Controls Chinese pronunciation rewriting and curly-apostrophe normalization. Turn it off to pause these changes. |
| Correct supported Chinese polyphones | On | Enables built-in Chinese corrections and your custom pronunciation rules. Turn it off to leave Chinese readings to the voice while keeping apostrophe handling. |
| Use extended phrase lexicon (experimental; may introduce wrong readings) | Off | Adds dictionary-based phrase coverage. Try it with familiar text and turn it off if it introduces misreadings. Reviewed rules and custom rules also work with this option off. |
| Normalize curly apostrophes inside Latin words | On | Converts in-word `’` to `'` for speech, for example `doesn’t` → `doesn't`. Turn it off to keep the curly form. |
| Strict mode (leave ambiguous text unchanged) | On | Uses the conservative reading policy. Turning it off currently enables the additional yuè preference for 钥 in 密钥、公钥、私钥. Keep it on for the default behavior. |

The three text fields—**Context templates**, **Custom literal rules** and **Disabled rule IDs**—start empty and are explained below. Custom Chinese rules require both contextual rewriting and Chinese corrections to be enabled. Settings can be saved separately in NVDA configuration profiles.

Chinese corrections specify Mandarin readings for every voice and language tag. For Cantonese, Japanese or another reading of Han characters, turn off Chinese corrections in the relevant NVDA configuration profile.

The installed apostrophe-protection symbol dictionary remains active when the rewriting or normalization option is off. To remove all add-on behavior, disable or uninstall the add-on and restart NVDA.

### Custom context templates

Use **Context templates** for a reading tied to surrounding text. Enter one template per line in the form `left context[target:pinyin]right context`. The target is one character; provide context on at least one side. Use ordinary text for a literal match or a supported placeholder for a class of text.

```text
仙[乐:yuè]
[盛:chéng]{number}{container}
```

- `仙[乐:yuè]` makes 乐 read yuè after 仙, including within a sentence such as 仙乐飘飘. `仙[乐:yue4]` is equivalent.
- `[盛:chéng]{number}{container}` selects chéng before a number and a listed container, as in 盛一碗 or 盛两杯. `{number}` matches up to 12 Chinese or Arabic numeral characters; `{container}` matches built-in entries such as 碗、杯、勺、盆.
- `{space}` allows zero to four supported spaces. For example, `[盛:chéng]{number}{space}{container}` also covers 盛一 碗. Other available classes are listed in the [rule data](addon/globalPlugins/contextualPronunciation/data/contributions.toml).

To preserve a character for the synthesizer or a later NVDA speech-dictionary rule, replace the reading with `keep`:

```text
仙[乐:keep]
```

Choose this preservation rule instead of the yuè rule for the same context. Each template contains one target. Use half-width `[]`, `:`, and `{}` as shown. Pinyin can use tone marks or tone numbers; ü can be entered as `v`, for example `lǜ` or `lv4`. Available readings are limited to the add-on's supported homophone mappings. Conflicting custom templates of equal priority preserve the original character.

### Custom literal rules

Use **Custom literal rules** when you want to specify an exact phrase. Enter one line per phrase, separating the three fields with the half-width pipe character `|`:

```text
仙乐|乐|yue4
盛汤|盛|keep
```

The fields are **phrase | target character | reading ID or keep**. The first line selects yuè for 乐 in 仙乐; the second preserves 盛 in 盛汤. Reading IDs use numbered pinyin, such as `yue4`, `chang2` and `lv4`. A phrase must contain 2–64 characters, with the target appearing exactly once. Enter each phrase/target pair once.

Both custom formats work with the extended lexicon off. If a custom literal rule and a custom template both match the same position, the literal rule takes priority. Usually one format is enough for a particular correction.

### Disable a rule or restore your settings

**Disabled rule IDs** accepts built-in rule identifiers separated by commas or newlines. For example, `rowIndefiniteQuantity` disables the rule for indefinite row counts such as 多行. IDs are recorded in the [core rules](addon/globalPlugins/contextualPronunciation/data/rules_zh_CN.json) and [syntax frames](addon/globalPlugins/contextualPronunciation/data/syntax_frames.toml), and a maintainer can identify one when troubleshooting. An unrecognized ID produces an error when you save. Other matching rules may still affect the same character; use a local `keep` rule to preserve a specific phrase.

To undo a personal rule or re-enable a disabled rule, remove its line or ID and click **Apply**. To return to the defaults in the current profile, clear all three text fields, turn the extended lexicon off and turn the other four checkboxes on. If a rule is rejected, correct the field indicated by the error before saving.

The add-on sends temporary pronunciation text to the synthesizer, so Speech Viewer may show substitute characters. Your document and clipboard text stay unchanged. See the [user guide](docs/README-en.md) for WorldVoice, optional braille output and troubleshooting.

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
