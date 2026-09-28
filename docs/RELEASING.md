# Releases and Store submissions

## Publication policy

`main` is the maintained development/release branch. Publish through **Actions → Publish release from main** after native CI succeeds for the exact commit. The workflow creates the version tag; do not manually create release tags, move published tags or overwrite issued assets. Corrections to an issued package require a new version.

**Store updates are on hold until the first submission is approved.** Publishing a GitHub Release does not submit an update to the NVDA Add-on Store. Do not create a duplicate registration issue or metadata pull request while that review is pending. Recheck the first submission's actual status and obtain the maintainer's go-ahead before the next Store submission.

## Prepare and publish on GitHub

1. Synchronize the numeric `major.minor.patch` version in `manifest.ini`, `buildVars.py` and `pyproject.toml`. Update `CHANGELOG.md`, current guides and `docs/releases/<version>.md`; regenerate installed user help.
2. Reproduce changed data and run relevant tests. Runtime changes require appropriate contrastive, performance, integration and acoustic evidence. Follow [Development](DEVELOPMENT.md). Check licenses, documentation links and archive contents; local instructions, credentials, private text, voices and development-session reports must not be included.
3. Commit or merge to `main`. Wait for a successful `regression.yml` **push** run on that exact commit, including both pinned native NVDA targets. A PR run, another commit or a partial run does not satisfy the gate.
4. Start the publication workflow from `main`:

```powershell
gh workflow run release.yml --repo ChenZ2000/contextualPronunciation --ref main
```

The workflow uses the selected commit, reads the version from its manifest, verifies the exact commit's CI evidence, builds both archives twice and compares bytes, then runs the pinned official Store manifest/schema/API validator locally. This validation does not write to the Store. Ordinary pushes and tag pushes do not publish a Release.

It creates `v<version>` and attaches the add-on, source archive, `SHA256SUMS`, `release-metadata.json`, `ci-verification.json` and `store-submission.md`. It rejects an existing version tag. Advancing `main` during a run does not change its selected source. Store fields are prepared for later review only.

5. Download the public package and verify its hash against `SHA256SUMS`. Check the release tag points to the tested commit. Public CI does not certify every proprietary voice.

## 0.8.0 maintainer acceptance

Before publishing 0.8.0, install the candidate and listen to both the positive and preservation examples in the [context-only 懵 design](COLLOQUIAL_MENG.md). In particular compare isolated 懵, 懵的读音 and 懵懂 against 一脸懵, 看懵了 and 懵得说不出话; include a mixed sentence and character navigation. Keep source SHA and candidate package hash with the result. A successful text test is not proprietary-voice certification.

The three version fields, current guides, installed help and `docs/releases/0.8.0.md` must agree. After maintainer listening acceptance and both native targets passing for the exact main SHA, use the normal **Publish release from main** workflow above. Preparation and candidate builds do not authorize publication, tag creation, replacing 0.7.9 assets or a Store submission.

0.8.0 发布前应先人工试听正例与保留例，并确认 main 同一提交的两个原生 NVDA CI 目标均通过，再触发上述工作流；不需要另建标签或修改工作流。候选包生成不会自动发布，旧版附件不覆盖，商店提交仍是单独授权的操作。

## Local package preparation

```powershell
python scripts/check_repository.py
python scripts/build_public_release.py
```

This performs deterministic package checks and writes release files under ignored `dist/`. It does not create a tag, publish or submit anything. Optional `--tag v<version>` asserts an exact manifest-version match. The normal package builders also work without local AI instructions or private archives.

The add-on ID is `contextualPronunciation`; publisher is `ChenZ2000`. Keep `addon_sourceURL` at the canonical repository root, `https://github.com/ChenZ2000/contextualPronunciation`. Metadata derives the version-specific source URL `https://github.com/ChenZ2000/contextualPronunciation/releases/tag/v<version>`. A moving branch or `/releases/latest` is not a version-specific Store source.

Keep license name `GPL-2.0-or-later`, bundled license text and `addon_licenseURL` pointing to `https://www.gnu.org/licenses/gpl-2.0.html`. Dictionary data retains its own notices. Stable compatibility is declared in the manifest; experimental NVDA API values must not be advertised as a tested final stable API.

## Store submission after approval

Consult the current [NV Access submission guide](https://github.com/nvaccess/addon-datastore/blob/master/docs/submitters/submissionGuide.md) and [API version list](https://github.com/nvaccess/addon-datastore/blob/master/transform/nvdaAPIVersions.json) before a separately authorized submission. Store requirements and review status can change.

After the first submission is approved and the maintainer authorizes an update:

1. Review `store-submission.md` from the immutable Release and verify the public package's bytes again.
2. Use the official [registration issue form](https://github.com/nvaccess/addon-datastore/issues/new?template=registerAddon.yml). Its label starts the official automation; an ordinary issue without that label does not necessarily start validation.
3. Follow the bot's metadata pull request, validation and review results. Record the issue/PR URL; pending review is not acceptance. Follow resubmission instructions if validation fails, without replacing issued assets.
4. Verify actual listing in the [Add-on Store](https://addonstore.nvaccess.org/) after acceptance. NV Access controls review and indexing.

Official validation tools are in `nvaccess/addon-datastore/validation/_validate`. The release workflow pins the upstream revision and locked dependencies; `scripts/check_store_metadata.py` validates the local archive using those tools. Source preparation and package validation do not authorize a Store submission.
