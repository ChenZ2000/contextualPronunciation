# Sources and references / 资料来源与参考

[English](#english) · [简体中文](#简体中文) · [Documentation index / 文档索引](INDEX.md)

## English

This page explains which resources supply data, which inform rule design, and which are used for testing. The repository stores fixed snapshots for reproducible builds. Attribution and complete license locations are recorded in [Third-party notices](../addon/THIRD-PARTY-NOTICES.txt).

### Dictionary and lexical data

| Resource and authors | Snapshot used | Purpose and license |
|---|---|---|
| [CC-CEDICT / MDBG](https://www.mdbg.net/chinese/dictionary?page=cedict), Paul Andrew Denisowski and contributors | 2026-09-07 | Simplified/traditional headwords, aligned pinyin, ambiguity evidence and explicit verb definitions; CC-BY-SA-4.0 |
| [开放汉语字典 / KFCD](https://github.com/kfcd/hyzd/tree/04987755b16264636c01d28df4d96fa14dadd210), 开放词典 / Kaifang Cidian | Commit `04987755b16264636c01d28df4d96fa14dadd210` | Character senses and the target character's reading in examples; CC-BY-3.0 |
| [Unicode Unihan](https://www.unicode.org/reports/tr38/tr38-39.html), Unicode, Inc. and contributors | Unicode 17.0.0 | Cross-checking character readings and compiling the polyphone inventory; Unicode-3.0 |
| [OpenHowNet](https://github.com/thunlp/OpenHowNet), THUNLP | Core resources and taxonomy dated 2021-09-20 | Part-of-speech alternatives, semantic classes and classifier relationships for grammatical analysis; MIT |
| [cppjieba](https://github.com/yanyiwu/cppjieba/tree/b3602bef7d1f67521a61788a74fb5801a0e62cd3), yanyiwu and contributors | Commit `b3602bef7d1f67521a61788a74fb5801a0e62cd3` | Word frequencies for segmentation and part-of-speech alternatives for the grammar lexicon; MIT |

OpenHowNet's classes help identify objects such as food, materials and containers. Pinyin decisions also require reading evidence and reviewed rules. cppjieba contributes dictionary data; segmentation and grammatical decisions run in the add-on's Python engine.

Source snapshots live in [`data/sources/`](../data/sources/). [`data/dictionary-sources.json`](../data/dictionary-sources.json) records CC-CEDICT, KFCD and Unihan provenance, hashes and resources reviewed for possible future use. OpenHowNet and cppjieba pins are also recorded in the generators and generated metadata.

### From sources to runtime files

Paths in the output column are relative to [`addon/globalPlugins/contextualPronunciation/data/`](../addon/globalPlugins/contextualPronunciation/data/).

| Generator | Inputs and output |
|---|---|
| [`import_cedict.py`](../tools/import_cedict.py) | CC-CEDICT, KFCD and Unihan → `lexicon_zh_CN.json` and `readings_zh_CN.json` |
| [`build_segmentation_data.py`](../tools/build_segmentation_data.py) | cppjieba frequencies and lexical heads → `segmentation_zh_CN.json` |
| [`build_syntax_data.py`](../tools/build_syntax_data.py) | OpenHowNet senses and taxonomy → `syntax_lexicon.json` |
| [`build_grammar_data.py`](../tools/build_grammar_data.py) | OpenHowNet, cppjieba, CC-CEDICT and KFCD → `grammar_lexicon.json` |
| [`build_dictionary_database.py`](../tools/build_dictionary_database.py) | CC-CEDICT and KFCD → attributed review records in `data/dictionary-records.jsonl.gz` |

The installed add-on uses compiled lexical features and reading data. Full source glosses and offline review records stay in the source bundle. Source-specific licenses remain applicable; the combined derived pronunciation and grammar compilations carry CC-BY-SA-4.0 as detailed in the notices. Reproduction commands are in [Development](DEVELOPMENT.md#reproducing-data).

### Linguistic and braille references

- **Ministry of Education dictionaries, Taiwan:** entries for [重](https://dict.revised.moe.edu.tw/dictView.jsp?ID=8701), [盛](https://dict.concised.moe.edu.tw/dictView.jsp?ID=32353), [將](https://dict.concised.moe.edu.tw/dictView.jsp?ID=23531), [天將](https://dict.revised.moe.edu.tw/dictView.jsp?ID=53102), [蝦兵蟹將](https://dict.revised.moe.edu.tw/dictView.jsp?ID=105310) and [唱和](https://dict.revised.moe.edu.tw/dictView.jsp?ID=124015) support manual checks of readings and senses. They are cited as online references; this project does not redistribute those dictionaries.
- **Usage references:** [汉典：系](https://www.zdic.net/hans/系) and the [People's Daily Overseas Edition discussion of 系](https://paper.people.com.cn/rmrbhwb/html/2014-04/26/content_1420139.htm) inform the fastening rules. Individual citations for these and other lexical decisions remain alongside rules in [`contributions.toml`](../addon/globalPlugins/contextualPronunciation/data/contributions.toml) and [`syntax_frames.toml`](../addon/globalPlugins/contextualPronunciation/data/syntax_frames.toml).
- **Universal Dependencies Chinese:** the [acl](https://universaldependencies.org/zh/dep/acl.html) and [advmod](https://universaldependencies.org/zh/dep/advmod.html) descriptions inform terminology for nominal modifiers and adverbial relationships. The project implements its own bounded parser and does not bundle a UD model or treebank.
- **GF 0019-2018, 国家通用盲文方案:** the [Ministry of Education publication](https://www.moe.gov.cn/jyb_sjzl/ziliao/A19/201807/t20180725_343690.html) is the reference for the optional table's pronunciation and abbreviation rules. The table includes NVDA/Liblouis's `zhcn-cbs.ctb` at runtime and adds fixed contexts; its implemented scope is described in the [user guide](README-en.md#optional-braille-output).

### Integration and evaluation resources

| Resource | Use in development |
|---|---|
| [NVDA](https://github.com/nvaccess/nvda), NV Access and contributors | Public speech APIs, native integration, official unit tests and Liblouis behavior. Fixed 2026.2 and 2026.3beta2 revisions are in [`prepare_nvda.py`](../scripts/prepare_nvda.py). GPL-2.0-or-later; Liblouis has its own LGPL terms. |
| [WorldVoice 6.2](https://github.com/tsengwoody/WorldVoice/tree/318bc90bf8a7af9e901bb43cd7da036533f443ea), tsengwoody and contributors | Dictionary and language-detection order tests using isolated voice substitutes. Upstream GPL license; fetched by [`prepare_worldvoice.py`](../scripts/prepare_worldvoice.py). |
| [CPP / g2pM](https://github.com/kakaobrain/g2pM/tree/170526efad0a3ef9b55a9ad4579f73218f9be06c), Kyubyong Park and Seanie Lee, Interspeech 2020 | External polyphone test text and labels for offline evaluation. Apache-2.0 repository; fetched by [`prepare_cpp.py`](../scripts/prepare_cpp.py). The normal regression path uses the test data without running its neural model. |

These dependencies are downloaded to ignored `vendor/` for development. Locally installed Vocalizer, eSpeak and SAPI voices are used for separate acoustic checks; voice resources and recordings are kept out of public packages. Reports distinguish supported decisions, unchanged text and disagreements with benchmark labels. See [the test strategy](DEVELOPMENT.md#tests-and-native-integration).

## 简体中文

本页说明项目采用的数据、规则设计参考和测试资源。仓库保留固定快照以支持可复现构建；完整署名和许可文件位置见[第三方声明](../addon/THIRD-PARTY-NOTICES.txt)。

### 词典与词法数据

| 资源与作者 | 使用版本 | 用途与许可 |
|---|---|---|
| [CC-CEDICT / MDBG](https://www.mdbg.net/chinese/dictionary?page=cedict)，Paul Andrew Denisowski 及贡献者 | 2026-09-07 快照 | 繁简词形、对齐拼音、歧义证据和显式动词释义；CC-BY-SA-4.0 |
| [开放汉语字典 KFCD](https://github.com/kfcd/hyzd/tree/04987755b16264636c01d28df4d96fa14dadd210)，开放词典 / Kaifang Cidian | 提交 `04987755b16264636c01d28df4d96fa14dadd210` | 单字义项及例词中目标字的读音；CC-BY-3.0 |
| [Unicode Unihan](https://www.unicode.org/reports/tr38/tr38-39.html)，Unicode, Inc. 及贡献者 | Unicode 17.0.0 | 字音交叉核对与多音字清单；Unicode-3.0 |
| [OpenHowNet](https://github.com/thunlp/OpenHowNet)，清华大学 THUNLP | 2021-09-20 核心资源及义原分类树 | 句法分析所用的词性候选、语义类别和量词关系；MIT |
| [cppjieba](https://github.com/yanyiwu/cppjieba/tree/b3602bef7d1f67521a61788a74fb5801a0e62cd3)，yanyiwu 及贡献者 | 提交 `b3602bef7d1f67521a61788a74fb5801a0e62cd3` | 分词词频及语法词库中的词性候选；MIT |

OpenHowNet 的类别用于识别食物、材料、容器等宾语；拼音裁决同时需要字音依据和经过审阅的规则。cppjieba 提供词典数据，分词和语法裁决由插件的 Python 引擎执行。

原始快照位于 [`data/sources/`](../data/sources/)；[`data/dictionary-sources.json`](../data/dictionary-sources.json) 记录 CC-CEDICT、KFCD 和 Unihan 的来源、哈希，以及为未来使用而审查过的其他资料。OpenHowNet 和 cppjieba 的固定版本也记录在生成器和生成数据的元信息中。

### 从资料到运行时数据

下表中的运行时文件均位于 [`addon/globalPlugins/contextualPronunciation/data/`](../addon/globalPlugins/contextualPronunciation/data/)。

| 生成器 | 输入及产物 |
|---|---|
| [`import_cedict.py`](../tools/import_cedict.py) | CC-CEDICT、KFCD、Unihan → `lexicon_zh_CN.json`、`readings_zh_CN.json` |
| [`build_segmentation_data.py`](../tools/build_segmentation_data.py) | cppjieba 词频及词头 → `segmentation_zh_CN.json` |
| [`build_syntax_data.py`](../tools/build_syntax_data.py) | OpenHowNet 义项及分类树 → `syntax_lexicon.json` |
| [`build_grammar_data.py`](../tools/build_grammar_data.py) | OpenHowNet、cppjieba、CC-CEDICT、KFCD → `grammar_lexicon.json` |
| [`build_dictionary_database.py`](../tools/build_dictionary_database.py) | CC-CEDICT、KFCD → `data/dictionary-records.jsonl.gz`，供离线查阅来源 |

安装包使用编译后的词法特征和读音数据，完整来源释义和离线审查记录随源码包提供。各来源许可继续有效；合并的衍生拼音及语法数据按第三方声明中的 CC-BY-SA-4.0 条款分发。复现命令见[开发指南](DEVELOPMENT.md#reproducing-data)。

### 语言学与盲文参考

- **台湾教育部辞典：** [重](https://dict.revised.moe.edu.tw/dictView.jsp?ID=8701)、[盛](https://dict.concised.moe.edu.tw/dictView.jsp?ID=32353)、[將](https://dict.concised.moe.edu.tw/dictView.jsp?ID=23531)、[天將](https://dict.revised.moe.edu.tw/dictView.jsp?ID=53102)、[蝦兵蟹將](https://dict.revised.moe.edu.tw/dictView.jsp?ID=105310)、[唱和](https://dict.revised.moe.edu.tw/dictView.jsp?ID=124015)等条目用于人工核对读音和义项。项目引用在线条目，不打包分发这些辞典。
- **用法参考：** [汉典“系”条目](https://www.zdic.net/hans/系)及[《人民日报海外版》关于“系”的用法说明](https://paper.people.com.cn/rmrbhwb/html/2014-04/26/content_1420139.htm)用于系结规则的核查。各项规则的具体引用保存在 [`contributions.toml`](../addon/globalPlugins/contextualPronunciation/data/contributions.toml) 和 [`syntax_frames.toml`](../addon/globalPlugins/contextualPronunciation/data/syntax_frames.toml) 中。
- **Universal Dependencies 中文关系说明：** [acl](https://universaldependencies.org/zh/dep/acl.html) 和 [advmod](https://universaldependencies.org/zh/dep/advmod.html)用于名词修饰成分和状语关系的术语参考。项目使用自研的有限范围分析器，不打包 UD 模型或树库。
- **GF 0019-2018《国家通用盲文方案》：** [教育部发布页](https://www.moe.gov.cn/jyb_sjzl/ziliao/A19/201807/t20180725_343690.html)是可选盲文表读音与简写规则的参考。该表在运行时引用 NVDA/Liblouis 的 `zhcn-cbs.ctb`，增加固定语境，具体覆盖范围见[使用指南](USAGE-zh_CN.md#可选盲文输出)。

### 集成与评测资源

| 资源 | 开发用途 |
|---|---|
| [NVDA](https://github.com/nvaccess/nvda)，NV Access 及贡献者 | 公开语音接口、原生集成、官方单元测试及 Liblouis 行为验证。2026.2 和 2026.3beta2 的固定提交见 [`prepare_nvda.py`](../scripts/prepare_nvda.py)。NVDA 使用 GPL-2.0-or-later；Liblouis 保留自身 LGPL 许可。 |
| [WorldVoice 6.2](https://github.com/tsengwoody/WorldVoice/tree/318bc90bf8a7af9e901bb43cd7da036533f443ea)，tsengwoody 及贡献者 | 使用隔离声音替身验证词典和语言检测顺序。遵循上游 GPL 许可，由 [`prepare_worldvoice.py`](../scripts/prepare_worldvoice.py) 获取。 |
| [CPP / g2pM](https://github.com/kakaobrain/g2pM/tree/170526efad0a3ef9b55a9ad4579f73218f9be06c)，Kyubyong Park、Seanie Lee，Interspeech 2020 | 采用其多音字测试文本和标签进行离线评估。仓库许可 Apache-2.0，由 [`prepare_cpp.py`](../scripts/prepare_cpp.py) 获取。常规回归使用测试数据，不运行其神经模型。 |

开发依赖下载到 Git 忽略的 `vendor/`。本机安装的 Vocalizer、eSpeak 和 SAPI 声音用于另外的声学检查，声音资源和录音不进入公开包。评测报告分别记录已作出的读音判断、保留原字的情况及与测试集标签的差异，详见[验证方法](DEVELOPMENT.md#tests-and-native-integration)。
