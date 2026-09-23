# Releases and NVDA Add-on Store submission

## Official requirements

Follow the current [NV Access submission guide](https://github.com/nvaccess/addon-datastore/blob/master/docs/submitters/submissionGuide.md), [API version list](https://github.com/nvaccess/addon-datastore/blob/master/transform/nvdaAPIVersions.json), and [NVDA Add-on Template documentation](https://github.com/nvaccess/AddonTemplate). Requirements can change; check them for each release.

The add-on ID is `contextualPronunciation`, the publisher is `ChenZ2000`, and the source is `https://github.com/ChenZ2000/contextualPronunciation`. Keep a numeric `major.minor.patch` version. HTTPS URLs must be permanent, and an issued `.nvda-addon` download URL must always refer to the same bytes. Never replace a released asset or move a released tag to change its contents; make a new patch version.

The stable manifest currently declares minimum and last-tested NVDA API 2026.2. Although CI also tests 2026.3beta2, API 2026.3 was marked experimental in the Store list when preparing 0.7.4. Declaring an experimental last-tested API requires the `beta` or `dev` channel. Do not claim a future final version was tested merely because a beta passed.

## Prepare a release

1. Update the version and matching metadata in `manifest.ini`, `buildVars.py` and `pyproject.toml`; update CHANGELOG.md and the user guides/installed help. Add `docs/releases/<version>.md` for the release notes.
2. Reproduce affected data, run relevant tests and check licenses, archive contents and document links. If runtime logic changed, perform the applicable acoustic checks with licensed resources and describe their limits.
3. Merge the reviewed commit to `main` and wait for both native CI targets to pass. CI measures performance against a fixed baseline on the same runner, retaining raw timings and absolute-budget observations; local strict release checks retain absolute budgets. See [the performance policy](DEVELOPMENT.md). Protect the release scope: no private logs, credentials, voices, local paths or user content may enter Git or an asset.
4. Create an annotated tag matching the manifest, for example `git tag -a v0.7.4 -m "Release 0.7.4"`, then `git push origin v0.7.4`. Only the maintainer should create release tags.
5. The release workflow requires a completed successful `regression.yml` push run on `main` for the exact tagged commit, including both native targets. A PR result, another commit or a partial run cannot satisfy that gate. It then builds both archives twice and compares bytes, checks the local package with a pinned official Store manifest/schema/API validator, and publishes the add-on, source bundle, `SHA256SUMS`, `release-metadata.json` and `ci-verification.json` using the workflow's limited repository token. It fails on a tag/version mismatch and refuses to overwrite an existing release. Reusing the exact commit's verified CI result avoids recompiling NVDA again simply to package identical source.
6. Download the public add-on asset again and compare its SHA-256 with `SHA256SUMS` before submitting it to the Store. Cloud checks do not claim proprietary voice certification.

`python scripts/build_public_release.py --tag v0.7.4` performs the same local package checks. It writes artifacts under `dist/`; it does not publish or submit anything. `dist/store-submission.md` contains the issue-form fields for manual review.

## Validate against the official Store tools

The current tools live inside `nvaccess/addon-datastore`, under `validation/_validate`, rather than the archived standalone validation repository. Check out a known upstream commit and install its locked dependencies using uv. The validator compares the actual downloaded package to manifest/JSON metadata and the official API list.

From that checkout, use the current command-line help for `_validate.createJson` to create metadata for the release URL, then run:

```powershell
uv run --directory validation python -m _validate.validate "../addons/contextualPronunciation/0.7.4.json" ../transform/nvdaAPIVersions.json
```

The metadata file is prepared locally for validation; the official issue automation creates the Store pull request. Keep generated validation files under ignored `artifacts/` or the ignored upstream checkout.

## Submit and follow up

Use the official [Add-on registration issue form](https://github.com/nvaccess/addon-datastore/issues/new?template=registerAddon.yml). With GitHub CLI, submit the same exact headings and attach the `autoSubmissionFromIssue` label:

```powershell
gh issue create --repo nvaccess/addon-datastore --title "[Submit add-on]: contextualPronunciation 0.7.4" --label autoSubmissionFromIssue --body-file dist/store-submission.md
```

This sends a public submission as the authenticated maintainer; inspect the body before running it. Do not submit duplicate issues while review is pending. Store submissions are a separate maintainer action; the release workflow does not automatically send them.

The official bot creates a metadata pull request and runs validation and security checks. A first submission requires NV Access to approve the publisher for this add-on, which may take up to two weeks. Staff may also review VirusTotal findings. Record the issue/PR URL and actual status; a pending review is not Store acceptance. If validation fails, fix the cause and follow the bot's resubmission instructions. A permanent release URL must keep its original bytes.

After acceptance, verify the bot's confirmation and actual listing in [the Add-on Store](https://addonstore.nvaccess.org/). NV Access controls review, merge and indexing; this repository cannot guarantee their decision or date. Translation system registration is optional and separate.
