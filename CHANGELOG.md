# Changelog

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

Earlier local development is documented in the [historical design index](docs/INDEX.md). Those notes describe their named versions and are not current installation instructions.
