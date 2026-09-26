# Development and architecture

## Requirements and first build

Use Windows, Git, [uv](https://docs.astral.sh/uv/) and 64-bit Python 3.13. Clone the repository as shown in the [README](../README.md#build-and-contribute), then run these commands from its root:

```powershell
python scripts/prepare_nvda.py
python scripts/prepare_worldvoice.py
python scripts/prepare_cpp.py
python scripts/run_tests.py
python tools/evaluate_grammar.py
python scripts/check_repository.py
python scripts/build_addon.py
python scripts/build_source_archive.py
```

The preparation scripts fetch and verify pinned development sources. The ordinary test suite runs independently of your active NVDA session. Test reports go to ignored `artifacts/`, packages to `dist/`, and downloaded sources and tools to `vendor/`. See [Tests and native integration](#tests-and-native-integration) for the additional C++ build environment required by the full regression workflow.

`python scripts/build_addon.py` produces an installable archive without compiling native code or requiring SCons. It preserves the standard NVDA archive layout and template-compatible `buildVars.py` metadata, uses a single root `manifest.ini`, stable ZIP timestamps and deterministic file ordering. `python scripts/build_source_archive.py` includes the code, generators, licensed source data, tests and community documents. It excludes vendor trees, recordings and private diagnostics. This custom packager is intentional; the NVDA Store validates the archive and manifest rather than requiring a particular build system.

## Runtime

`addon/globalPlugins/contextualPronunciation/` contains the global plugin and pure-Python engine:

1. `__init__.py` registers public speech, queue, profile and settings events and unregisters them on termination.
2. `pipeline.py` preserves speech commands and character mode, analyzes string items and commits successful normalization results. The queue guard acts after native dictionaries/symbols on residual reviewed target characters.
3. `rules.py` combines user preservation, reviewed phrases, structural evidence and the optional lexicon into decisions at original offsets before rendering temporary homophones.
4. `segmentation.py`, `syntax.py`, `constituents.py`, `predicates.py`, `nominals.py` and `edges.py` provide lexical boundaries and bounded structural analysis. Static POS alternatives are evidence, not an infallible contextual POS classifier.
5. `braille_readings.py` exposes original-character annotations. The optional installed static Liblouis table is separate and does not dynamically execute the speech parser.

Runtime data is loaded from packaged JSON/TOML. Templates are bounded and cannot execute arbitrary Python or regular expressions. Speech-time processing does not fetch data, query SQLite or retain previous utterances.

## Choose where to make a change

| Change | Main entry points | Validation |
|---|---|---|
| Reviewed phrase or grammatical context | `data/contributions.toml` and `data/syntax_frames.toml` inside the plugin | Add reading and preservation cases, run contribution checks and the grammar evaluator |
| Segmentation or sentence analysis | `segmentation.py`, `syntax.py`, `constituents.py`, `predicates.py`, `nominals.py`, `edges.py` | Unit and grammar tests, native integration, performance and applicable acoustic checks |
| Dictionary snapshot or lexical features | Root `data/sources/` and the corresponding generator under `tools/` | Review the source/license, regenerate outputs and run the affected `--check` commands |
| Settings or NVDA integration | `settings.py`, `__init__.py`, `pipeline.py`, `lifecycle.py` | Settings/profile, command-preservation and native integration tests |
| UI translation or installed help | `addon/locale/` and `addon/doc/` | Compile changed translation catalogs; check links and package contents |
| Repository documentation | `README.md` and current guides under `docs/` | Keep English/Chinese guidance aligned; run `scripts/check_repository.py` |

Runtime module paths above are relative to `addon/globalPlugins/contextualPronunciation/`. Source dictionary changes go through their generators so that provenance and generated files remain reproducible. The [reference guide](REFERENCES.md) maps each dataset to its role and output.

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

The acoustic fixture oracles intentionally reference the stable 2026.2 symbol processor. A beta workflow therefore prepares that separate stable source checkout as well as its beta native build. It does not assume a stable checkout already exists, and does not silently replace the fixture oracle with beta behavior.

Performance reports separate initialization, per-call measurements and batch-median guardrails. They exclude synthesis, audio playback and device scheduling. Local regression and `--release` retain the established absolute budgets.

GitHub runners use `--hosted-performance`: current code and immutable baseline `82bdb20ae72a849f9cefac6073a1111d82bc52fc` are measured sequentially on the same runner and Python interpreter. The baseline is the initial public commit with the previously validated 0.7.3 runtime. The hot-path benchmark uses seven rounds of 10,000 short or 20 long calls for each version with the same fixed Python hash seed; grammar benchmarks retain 1,000 individual samples for short text and 100 for long text. Every scenario must remain within the greater of 1.30 times its baseline median or the baseline median plus 5 microseconds. Scenario names, input lengths and sample counts must match. This detects relative regressions; it does not establish an absolute latency guarantee. Baseline changes require explicit review and must not be used to conceal a regression.

CI retains both raw reports, startup timings, comparison results and any absolute-budget failure in the workflow report. The relative policy addresses variable hosted hardware; it does not turn an exceeded absolute budget into a pass. The local strict release mode rejects the hosted option. Investigate failures before changing either policy.

## Optional acoustic verification

`--vocalizer --release` adds fresh offline acoustic rendering against a legally installed Vocalizer Expressive voice. This local verification path is separate from cloud publication and never means that all voices are certified. `--installed-worldvoice <path>` tests a local source pipeline without reading live settings; `--cross-engine-probes` records eSpeak/SAPI observations. Do not upload licensed voice resources or captured user speech.

When changing runtime rules, regenerate `tools/generate_final_renderer_fixture.py`, `tools/boundary_acoustics.py generate` and `tools/sentence_acoustics.py generate`, then rerun relevant rendering. Runtime hashes must describe what was actually rendered; updating a hash alone cannot refresh acoustic evidence.

## Documentation

The English project overview is `README.md`; its Chinese counterpart is `docs/README-zh_CN.md`. Detailed user instructions are `docs/README-en.md` and `docs/USAGE-zh_CN.md`. Keep their features, settings, examples and compatibility information aligned. Source provenance belongs in `docs/REFERENCES.md`, development procedures here, and release steps in `docs/RELEASING.md`.

Add new current guides to `CURRENT_DOCS` in `scripts/check_repository.py` so CI checks their relative links. Update `docs/INDEX.md` to make them discoverable. Versioned research notes remain historical evidence; their `artifacts/` references describe local output. Installed help uses semantic HTML with headings and language tags. Check links in both Markdown and HTML when either form changes.
