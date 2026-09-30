# Development

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

## Workspace maintenance

| Directory | Maintained content | Published |
|---|---|---|
| `addon/` | Runtime, compiled data, translations and generated user help | Yes |
| `data/`, `data/sources/` | Reviewed data, licensed pinned inputs and reproducible summaries | Source bundle |
| `tools/`, `scripts/`, `tests/` | Generators, diagnostics, workflows and regression fixtures | Source bundle |
| `docs/` | Current guides; `docs/releases/` contains published-version notes | Source bundle |
| `artifacts/`, `dist/` | Current reports and built packages | Ignored build output |
| `vendor/` | Reproducible external dependencies | Ignored |
| `local/` | Personal notes, previous runs and development-session archives | Ignored |

Keep only stable entry points and project metadata at the root. Local AI instructions are ignored and excluded from packages. Public build and test scripts must work without them. Directory maintenance and contributor requirements belong in this guide. Do not add private text, voice files or credentials to fixtures.

Preview cache cleanup with `pwsh -File scripts/clean_workspace.ps1 -WhatIf`. Omit `-WhatIf` to run it. Add `-ArchiveOutputs` to move current reports and packages into a timestamped local archive before starting fresh. The script records its actions and uses an atomic directory move that does not traverse links. Builds must not depend on the archive.

## Runtime

`addon/globalPlugins/contextualPronunciation/` contains the global plugin and pure-Python engine:

1. `__init__.py` registers public speech, queue, profile and settings events and unregisters them on termination.
2. `pipeline.py` preserves speech commands and character mode, analyzes string items and commits successful normalization results. The queue guard acts after native dictionaries/symbols on residual reviewed target characters.
3. `rules.py` combines user preservation, reviewed phrases, structural evidence and the always-enabled lexicon into decisions at original offsets before rendering temporary homophones.
4. `segmentation.py`, `syntax.py`, `constituents.py`, `predicates.py`, `nominals.py`, `edges.py`, `motion.py` and `growth.py` provide lexical boundaries and bounded structural analysis. `verb_forms.py` and `argument_roles.py` expose shared complement, recipient and quantity productions. Static POS alternatives are evidence, not an infallible contextual POS classifier. See [event roles and sense selection](ARCHITECTURE.md) for competing transfer/rotation and growth/length frames.
5. `braille_readings.py` exposes original-character annotations. The optional installed static Liblouis table is separate and does not dynamically execute the speech parser.

Runtime data is loaded from packaged JSON/TOML. Templates are bounded and cannot execute arbitrary Python or regular expressions. Speech-time processing does not fetch data, query SQLite or retain previous utterances.

The local performance gate includes short motion predicates and dense 8K motion input with the same 200 µs / 30 ms budgets used for comparable existing scenarios. Hosted CI keeps the fixed baseline for existing workloads. Retired `defaultPlugin` settings cases compare against that baseline's dictionary-enabled plugin cases; new motion scenarios use a separately reported envelope of twice the slowest baseline short-plugin or long-page scenario on that runner. Unknown or missing scenario names fail the schema check. These are batch timing gates, not end-to-end speech latency promises.

## Choose where to make a change

| Change | Main entry points | Validation |
|---|---|---|
| Reviewed phrase or grammatical context | `data/contributions.toml` and `data/syntax_frames.toml` inside the plugin | Add reading and preservation cases, run contribution checks and the grammar evaluator |
| Segmentation or sentence analysis | `segmentation.py`, `syntax.py`, `constituents.py`, `predicates.py`, `nominals.py`, `edges.py`, `motion.py`, `growth.py`, `verb_forms.py`, `argument_roles.py` | Unit and grammar tests, native integration, performance and applicable acoustic checks |
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

GitHub runners use `--hosted-performance`: current code and immutable baseline `82bdb20ae72a849f9cefac6073a1111d82bc52fc` use the same interpreter, fixed Python hash seed and processor core. The harness selects the lowest allowed processor before sampling and pins only its own process and children. It runs five predetermined process rounds, alternating which version runs first for each benchmark. Each hot-path process uses seven rounds of 2,000 short or 4 long calls: total timed calls remain 70,000 and 140 per version. Each grammar process measures 200 short or 20 long samples, retaining totals of 1,000 and 100. Normal warmups run in each process. Each version uses its own benchmark and runtime files; the baseline checkout is never edited.

The comparison uses the median of all five process medians for each scenario, with no dropped rounds or retries inside the benchmark. Existing comparable scenarios must remain within the greater of 1.30 times their baseline median or the baseline median plus 5 microseconds. Their scenario names, input lengths, sample counts and process-round totals must match. The baseline is the initial public commit with the previously validated 0.7.3 runtime. This detects relative regressions; it does not establish an absolute latency guarantee. Baseline changes require explicit review and must not be used to conceal a regression.

The fixed baseline predates the growth, clipped stature and neutral-word capabilities. Their dedicated benchmark now participates in the same-core alternating five-process workflow: each current growth process runs 50 short or 20 long samples, retaining totals of 250 and 100. Its adjacent reference process runs the baseline's own unchanged grammar benchmark. Each new scenario is explicitly labelled `new-feature-envelope`, with a limit of twice the slowest baseline grammar scenario in the same mode and short/page size class (or that reference plus 5 microseconds, whichever is greater). This reuses the existing new-feature multiplier; it is a capability cost budget, not a claim of identical input or semantics in the old baseline. Missing scenarios, modes, invalid timings, altered call totals, interpreter/configuration differences and processor differences fail the gate.

CI retains all process reports under `artifacts/hosted-performance-samples/`, their execution order and processor affinity, the aggregates, the original unpinned reports, startup timings, comparison results and any absolute-budget failure in the workflow report. Growth evidence includes `paired-current-growth-performance.json` and `baseline-growth-reference.json`; the comparison report also records the aggregate growth absolute observation. Aggregate reports do not claim pooled p95/p99 values; per-process quantiles remain in the raw reports. Hosted absolute growth overruns are recorded without stopping before the mandatory same-runner gate; an exceeded absolute budget remains a failed absolute observation. Local regression and strict release still reject those overruns, and strict release rejects the hosted option. Investigate failures before changing either policy.

## Optional acoustic verification

`--vocalizer --release` adds fresh offline acoustic rendering against a legally installed Vocalizer Expressive voice. This local verification path is separate from cloud publication and never means that all voices are certified. `--installed-worldvoice <path>` tests a local source pipeline without reading live settings; `--cross-engine-probes` records eSpeak/SAPI observations. Do not upload licensed voice resources or captured user speech.

When changing runtime rules, regenerate `tools/generate_final_renderer_fixture.py`, `tools/boundary_acoustics.py generate` and `tools/sentence_acoustics.py generate`, then rerun relevant rendering. Runtime hashes must describe what was actually rendered; updating a hash alone cannot refresh acoustic evidence.

Also regenerate `python tools/neutral_acoustics.py generate`. The optional
`--vocalizer` workflow renders this fixture and requires actual plain-text output
to match an independent SDK Pinyin tone control in both phonemes and PCM, while
differing from the competing tone. Runtime never sends SDK markup. Numeric
phoneme equality alone cannot establish a Mandarin tone. Generated WAVs remain
local; passing this audit does not claim human listening or coverage of other voices.

The modified growth location 树上长个奇怪的东西 uses explicit zhǎng/zhàng
SDK controls: the polyphonic anchor 涨 produces different PCM there, while the
actual 掌 output matches explicit zhǎng. This case belongs in the SDK fixture;
do not treat a matching private phoneme ID as a tone assertion.

## Documentation

The English project overview is `README.md`; its Chinese counterpart is `docs/README-zh_CN.md`. Detailed user instructions are `docs/README-en.md` and `docs/USAGE-zh_CN.md`. Keep their features, settings, examples and compatibility information aligned. Source provenance belongs in `docs/REFERENCES.md`, development procedures here, and release steps in `docs/RELEASING.md`.

Add new current guides to `CURRENT_DOCS` in `scripts/check_repository.py` so CI checks their relative links. Update `docs/INDEX.md` to make them discoverable. Keep development-session reports and machine-specific measurements under ignored `local/` or `artifacts/`. Consolidate durable design decisions into `ARCHITECTURE.md` and rule/API contracts into `RULES.md`. Published changes belong in `CHANGELOG.md` and `docs/releases/`.

The installed English and Chinese help is generated from the corresponding user guide; edit Markdown first, then regenerate semantic HTML:

```powershell
uv run --no-project --with markdown==3.10.2 python tools/build_user_help.py
uv run --no-project --with markdown==3.10.2 python tools/build_user_help.py --check
python scripts/check_repository.py
```

CI checks generated help, links and publication exclusions. The package builder uses the checked-in HTML and does not need Markdown or network access.

## Context-only colloquial 懵 regression

The [linguistic design](COLLOQUIAL_MENG.md) distinguishes sourced usage from constructed policy examples. `tests/meng_cases.py` supplies independent positive, negative and mixed expectations; it does not derive them from runtime rules.

```powershell
python -m unittest tests.test_meng_contexts tests.test_colloquial_tones
python tools/evaluate_colloquial_meng.py
python tools/benchmark_colloquial_meng.py
```

Both evaluation and performance are mandatory stages of `scripts/run_regression.py`, including native CI. The dedicated benchmark runs both default and extended engines through the speech sequence normalizer. It fails if any measured median exceeds 200 microseconds for short inputs or 30 milliseconds for long inputs; each case has at least 100 timed calls. Existing global benchmarks, immutable-baseline comparison and their limits are unchanged. Timing is host-specific and excludes startup, synthesis and NVDA event dispatch, not an end-to-end latency promise. Evidence belongs under ignored `artifacts/` and is uploaded by CI. Missing evidence or failure must not be described as a pass.

## Growth and length validation

`tests/growth_cases.py` contains independent body-location, growth, stature,
honor, length and preservation expectations, including vocabulary combinations
outside runtime phrase entries. `growth.py` attaches those arguments locally;
the reviewed nominal classes live in `syntax_frames.toml`. Use the ordinary
pronunciation explainer to inspect heads, localizers, beneficiaries, aspects and
stem/result offsets. Ambiguous hair growth/length and face descriptions abstain.

```powershell
python -m unittest tests.test_growth tests.test_reported_readings
python tools/evaluate_grammar.py
python tools/benchmark_growth.py
```

Local regression runs the growth/neutral benchmark with unchanged 200 µs short /
30 ms long median budgets and at least 100 measured calls per case in both modes.
It includes clipped stature, classifier objects with modifiers, quantities and
locations, measurement contrasts, complete neutral words and dense pages.
Hosted CI records that absolute check with `--observe-absolute` and requires the
paired new-feature envelope described above. The original absolute report is
`artifacts/growth-performance.json`. Invalid data still fails observation mode.
Exact
closed predicates avoid unnecessary charts; repeated stems share argument
analysis within one item, including separate readings for a growth stem and
length result. No whole-text result cache or cross-item text retention is used.
