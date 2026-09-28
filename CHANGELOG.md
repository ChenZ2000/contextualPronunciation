# Changelog

## 0.8.0

- Replace the unconditional colloquial 懵 fallback with bounded positive grammatical evidence. Isolated 懵, literary words, lexical mentions and unsupported contexts keep the original text and synthesizer reading; no global second-tone rule is installed.
- Generalize first-tone matching through colloquial lexemes, facial states, state predicates, resultatives, degree/result/duration complements, grounded subjects, questions, comparison and bounded reiteration. Retain literary protection, personal-rule priority and speech-item/spelling boundaries.
- Use 擝 (U+64DD) instead of the ambiguous 蒙 speech renderer from the published 0.7.9 package. Rare-character support still requires target-voice listening checks.
- Add independent constructed positive, negative and mixed cases, real NVDA symbol-pipeline contrasts and dedicated fail-closed short/8K performance gates. Synchronize metadata, bilingual guides, installed help and [0.8.0 release notes](docs/releases/0.8.0.md).
- 删除“未命中保护词即默认一声”的过度规范化，仅对有依据的口语语境选一声；单字、书面词和字音讨论保留声库原有读音。新增可组合语法用例、反例、混合语境和性能门禁，保留个人覆盖与逐字模式。

## 0.7.9

- Default colloquial 懵 to mēng in 一脸懵逼, 懵了 and other contexts, while preserving 懵懂 and reviewed literary forms with third-tone readings. The colloquial policy can be disabled with `colloquialMeng`.
- Annotate neutral-tone 腾 in 折腾, 倒腾, 捣腾, 闹腾, 掀腾 and traditional forms; preserve complete words for the synthesizer instead of rewriting their first syllables to homophones.
- Protect word boundaries such as 曲折／腾挪 and 打倒／腾空 without blocking 折腾空调 or 倒腾飞机. Add regression coverage for speech decisions, annotations, user rules and configuration modes.
- These changes do not force neutral-tone audio in every synthesizer. See the [release notes](docs/releases/0.7.9.md) for scope and limitations.

## 0.7.8

- Default 装盛 / 裝盛 to chéng; recognize 盛装 action nominals and container goals while preserving attire contexts.
- Parse quantified, possessed and modified instrument objects in 弹…琴 / 彈…琴 instead of requiring adjacent characters.
- Fix multiline custom-rule editing by preserving native Enter handling before NVDA's dialog-wide OK shortcut.

- Enable the full dictionary and bounded grammar whenever Chinese corrections are enabled; remove the extended-lexicon checkbox.
- Correct counted work trips, counted nights versus astronomical 宿, and both syllables in 倔强. Default 重装 / 重裝 to chóng for reinstall, with explicit heavy-equipment protections.
- Select rotation, roaming and transfer readings using noun-phrase heads, recipients, beneficiaries, purpose clauses and productive verb complements. Expand dictionary-derived mechanical candidates and share arguments across 转呀转, 转着转着 and 转了又转.
- Reuse repeated-predicate morphology for existing 盛, 量 and 系 argument frames. Preserve user rules, original offsets and work budgets.
- Consolidate current documentation, generate installed help from user guides, and exclude local AI instructions and development-session reports from public packages.
- Add contrastive semantic, source-provenance, synthesis and performance regressions. See [release notes](docs/releases/0.7.8.md) for validation scope and installation.

## 0.7.4

First public GitHub repository release. The pronunciation runtime is unchanged from 0.7.3.

- Add repository URLs, maintainer metadata and an NVDA 2026.2 stable API declaration; keep 2026.3beta2 as an additional CI target.
- Add reproducible tag-based release automation, SHA-256 checksums, source archives and Store submission preparation.
- Add English/Chinese community documentation, contribution and security guidance, issue templates and a root GPL license.
- Exclude local dependencies, recordings, diagnostics and private configuration; retain licensed source snapshots needed for reproducibility.

## 0.7.3

- Resolve spatial noun and coordinated predicate boundaries such as 下边缘 and 唱和说.
- Correct bare 多行 and row-related continuations while preserving action readings.
- Recheck residual target readings after speech dictionaries and symbols, before queuing speech.
- Expand the targeted grammar corpus to 1,154 cases in both default and extended modes.

## 0.7.2

- Improve omitted objects with aspect markers, such as 也给我盛了一碗.
- Improve coordinated military subjects followed by predicates, such as 天兵和天将一起去吃饭.

Current instructions are in the [documentation index](docs/INDEX.md). Earlier implementation states remain available in Git history.
