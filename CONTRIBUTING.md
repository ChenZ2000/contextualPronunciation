# Contributing

English and Chinese contributions are welcome. Follow the [code of conduct](CODE_OF_CONDUCT.md). Use an issue for a reproducible problem and a pull request for a proposed change; the maintainer is ChenZ2000.

## Pronunciation reports

Provide an anonymized complete sentence, the target character, expected pinyin including tone, actual reading, NVDA version, add-on version, voice/engine and settings. Include a contrasting sentence when the same character should keep its other reading. Do not post private documents, recordings containing personal information, credentials or proprietary voice files.

## Development

Read [DEVELOPMENT.md](docs/DEVELOPMENT.md), prepare the pinned dependencies, then run `python scripts/run_tests.py`. Run Ruff using the pinned version:

```powershell
uv tool run --from ruff==0.15.9 ruff check addon tests tools scripts buildVars.py
uv tool run --from ruff==0.15.9 ruff format --check addon tests tools scripts buildVars.py
```

Keep changes focused. For pronunciation logic, add independently specified positive and negative cases; do not derive the expected reading from the implementation being tested. Explain the grammatical evidence, ambiguity boundaries and how explicit user preservation works. Add dictionary evidence in the existing auditable data format, not an unlicensed bulk scrape. Regenerate the affected derived data and fixtures and run their reproducibility checks.

The runtime must keep NVDA commands and spelling mode intact, stay offline, avoid logging spoken text, respect work budgets and fail open. Do not patch private synthesizer methods, fetch dependencies at speech time, or add voice resources to the package.

## Translations and documentation

UI translations live under `addon/locale/<language>/LC_MESSAGES/nvda.po`; include the compiled `.mo` when updating a catalog. Localized manifests are in `addon/locale/<language>/manifest.ini`. User help is `addon/doc/<language>/readme.html`. Keep installed help and the current guides under `docs/` consistent, including relative links. Crowdin registration is a separate optional process and is not currently configured.

## Pull requests and releases

Describe the user-visible trigger and resulting behavior, validation performed and remaining limitations. Target pull requests at `main`, the only maintained development/release branch; contributor and Dependabot branches are temporary proposals. Public native CI runs on both pinned NVDA versions. After review and successful CI, a maintainer runs **Publish release from main**; the workflow creates the version tag. [RELEASING.md](docs/RELEASING.md) explains packaging, immutable download assets and Store submission. External contributors do not need proprietary Vocalizer resources to run ordinary tests or build the add-on.

Code contributions use GPL-2.0-or-later. Data contributions must retain their source licenses and attribution; the existing data compilations have separate terms described in [third-party notices](addon/THIRD-PARTY-NOTICES.txt). By contributing, you confirm that you have the right to supply the contribution under the applicable terms. No copyright transfer is required.
