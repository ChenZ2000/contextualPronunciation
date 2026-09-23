# Development and architecture

## Requirements and first build

Use Windows, Git, uv and 64-bit Python 3.13. Start in a fresh checkout and follow the commands in the [README](../README.md). Ordinary tests prepare fixed NVDA, WorldVoice and CPP source snapshots; they do not start NVDA or change a live profile. Outputs go to ignored `artifacts/` and `dist/`, with downloaded tools and source under ignored `vendor/`.

`python scripts/build_addon.py` produces an installable archive without compiling native code or requiring SCons. It preserves the standard NVDA archive layout and template-compatible `buildVars.py` metadata, uses a single root `manifest.ini`, stable ZIP timestamps and deterministic file ordering. `python scripts/build_source_archive.py` includes the code, generators, licensed source data, tests and community documents. It excludes vendor trees, recordings and private diagnostics. This custom packager is intentional; the NVDA Store validates the archive and manifest rather than requiring a particular build system.

## Runtime

`addon/globalPlugins/contextualPronunciation/` contains the global plugin and pure-Python engine:

1. `__init__.py` registers public speech, queue, profile and settings events and unregisters them on termination.
2. `pipeline.py` preserves speech commands and character mode, analyzes string items and commits successful normalization results. The queue guard acts after native dictionaries/symbols on residual reviewed target characters.
3. `rules.py` combines user preservation, reviewed phrases, structural evidence and the optional lexicon into decisions at original offsets before rendering temporary homophones.
4. `segmentation.py`, `syntax.py`, `constituents.py`, `predicates.py`, `nominals.py` and `edges.py` provide lexical boundaries and bounded structural analysis. Static POS alternatives are evidence, not an infallible contextual POS classifier.
5. `braille_readings.py` exposes original-character annotations. The optional installed static Liblouis table is separate and does not dynamically execute the speech parser.

Runtime data is loaded from packaged JSON/TOML. Templates are bounded and cannot execute arbitrary Python or regular expressions. Speech-time processing does not fetch data, query SQLite or retain previous utterances.

## Reproducing data

Sources, hashes and attribution are recorded in `data/`, `data/sources/`, generator constants and `addon/THIRD-PARTY-NOTICES.txt`. The `--check` modes reconstruct outputs and compare bytes:

```powershell
python tools/import_cedict.py --check
python tools/build_segmentation_data.py --check
python tools/build_syntax_data.py --check
python tools/build_grammar_data.py --check
python tools/build_polyphone_coverage.py --check
python tools/build_dictionary_database.py --check
python tools/build_braille_table.py --check
python tools/pronunciation.py --check-contributions
```

Do not change source pins or hashes merely to hide a mismatch. Retain source licenses and document derivations. A corpus size is not an accuracy figure.

The CPP development downloader verifies the pinned LF Git-blob hash, then converts line endings to the exact CRLF form used by the existing Windows audit evidence and verifies that second hash. It never accepts arbitrary downloaded bytes or overwrites a changed cached file. This makes a fresh checkout reproducible without relying on a pre-existing Windows Git checkout.

## Tests and native integration

`python scripts/run_tests.py` requires the pinned development sources and rejects skipped add-on tests. `python tools/evaluate_grammar.py` checks independently specified reading and preservation oracles. `python scripts/run_regression.py --native --jobs 2` additionally compiles NVDA and runs its upstream tests, the native plugin chain, lint, all reproducibility checks and performance gates.

Native builds require the toolchain specified by the pinned NVDA source: Visual Studio C++, Windows SDK, ATL and Clang. CI uses the same `windows-2025-vs2026` runner family as that source. Local optional LLVM/ATL adapters are documented by `scripts/build_nvda.ps1`; no prebuilt local NVDA DLL is distributed in this repository.

Choose the other pinned test target explicitly:

```powershell
$env:CONTEXTUAL_PRONUNCIATION_NVDA_VERSION = '2026.3beta2'
python scripts/run_regression.py --native --jobs 2
$env:CONTEXTUAL_PRONUNCIATION_NVDA_VERSION = '2026.2'
```

The beta has five upstream unimplemented DotPad BLE tests; the validator permits only those exact IDs/reasons and records them as skips. On a local computer with an existing screen color effect, `--allow-external-screen-effect` records only NVDA's own protective screen-curtain skip. Never reset a user's display merely to run this test.

Performance reports separate initialization, per-call measurements and batch-median guardrails. They exclude synthesis, audio playback and device scheduling. Keep the established gates; investigate performance regressions instead of silently relaxing limits.

## Optional acoustic verification

`--vocalizer --release` adds fresh offline acoustic rendering against a legally installed Vocalizer Expressive voice. This local verification path is separate from cloud publication and never means that all voices are certified. `--installed-worldvoice <path>` tests a local source pipeline without reading live settings; `--cross-engine-probes` records eSpeak/SAPI observations. Do not upload licensed voice resources or captured user speech.

When changing runtime rules, regenerate `tools/generate_final_renderer_fixture.py`, `tools/boundary_acoustics.py generate` and `tools/sentence_acoustics.py generate`, then rerun relevant rendering. Runtime hashes must describe what was actually rendered; updating a hash alone cannot refresh acoustic evidence.

## Documentation

Current entry points are the README, English/Chinese user guides, this file and RELEASING.md. Versioned research notes remain historical evidence. Their local `artifacts/` references are intentionally absent from Git. Installed help uses semantic HTML with headings and language tags. Verify all relative links when editing either form.
