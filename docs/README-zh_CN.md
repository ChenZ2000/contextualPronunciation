# NVDA 上下文发音规范化

[English](../README.md) · 简体中文

为 NVDA 改善中文多音字朗读。插件结合分词、词典读音和句子结构，在文本送入当前语音合成器前选择合适的普通话读音，同时保留 `doesn't`、`Mike's` 等英文单词中的撇号。

[下载安装](https://github.com/ChenZ2000/contextualPronunciation/releases/latest) · [使用指南](USAGE-zh_CN.md) · [反馈问题](https://github.com/ChenZ2000/contextualPronunciation/issues) · [更新记录](../CHANGELOG.md)

## 主要功能

- **根据上下文纠正多音字。** 结合经过审阅的规则和词典资料，处理重复动作、数量结构、带修饰语的宾语和并列短语。
- **自定义读音。** 为特定语境指定拼音，或保留原字，让已有的语音词典继续处理。
- **离线运行。** 在本机处理朗读文本，不上传或记录朗读内容。
- **可选扩展。** 实验性扩展词组库增加词汇覆盖；可选的国家通用盲文 2018 输出表提供固定语境的读音修正。

默认设置支持的部分例子：

| 语境 | 选择的读音 |
|---|---|
| 重转、重吸收、重捏、重飞 | 重 → chóng，表示再次进行动作 |
| 也给我盛了一碗、盛那碗刚刚煮好的红豆粥 | 盛 → chéng，表示装盛、容纳 |
| 天兵和天将一起去吃饭 | 将 → jiàng，表示军职名词 |
| 系那条又细又长的红色丝带、量小名的身高 | 系 → jì；量 → liáng |
| 下边缘、唱和说、多行文本 | 边 → biān；和 → hé；行 → háng |

对于有歧义或尚未支持的文本，引擎保留原字交给语音合成器朗读。声音设置、自定义规则和问题排查见[使用指南](USAGE-zh_CN.md)。

## 安装与使用

当前发布版本为 **0.7.4**，最低要求及最后测试的稳定版均为 **NVDA 2026.2**。CI 另外验证 **2026.3beta2**。

1. 从 [Releases 页面](https://github.com/ChenZ2000/contextualPronunciation/releases/latest)下载 `.nvda-addon` 文件。
2. 打开文件，按 NVDA 提示安装并重启。
3. 继续使用平时的普通话声音朗读，默认纠正规则会自动生效。
4. 在 **NVDA 设置 → 上下文发音规范化** 中调整功能。“启用上下文发音改写”“纠正已支持的中文多音字”和“严格模式”默认开启，实验性扩展词组库默认关闭。

中文纠正会对所有声音和语言标签下的汉字应用普通话读音。使用粤语、日语等读法时，可在对应的 NVDA 配置方案中关闭中文纠正。

插件会向合成器发送临时的发音替代文本，因此语音查看器可能显示同音替代字；文档和剪贴板内容保持原样。若要停用包括撇号保护在内的全部功能，请禁用或卸载插件并重启 NVDA。

## 工作原理

1. 通过 NVDA 的公开扩展接口接收语音序列。
2. 对文本分词，结合词典和句法信息，在原文位置上决定读音，同时保留语音命令和逐字朗读模式。
3. 使用临时同音字落实读音；在 NVDA 语音词典和符号处理之后，再检查已支持的“和、边、邊、行”语境，减少后续处理造成的误读。

模块职责、数据生成和验证方法见[开发与架构指南](DEVELOPMENT.md)。

## 仓库结构

| 位置 | 维护内容 |
|---|---|
| [`addon/globalPlugins/contextualPronunciation/`](../addon/globalPlugins/contextualPronunciation/) | NVDA 语音接口、设置、分词和句法引擎 |
| [`addon/globalPlugins/contextualPronunciation/data/`](../addon/globalPlugins/contextualPronunciation/data/) | 审阅规则、模板和生成的运行时词库 |
| [`addon/`](../addon/) | 安装包内的帮助、翻译、符号字典和盲文表 |
| [`data/`](../data/)、[`tools/`](../tools/) | 词典源数据、来源记录、生成器和分析工具 |
| [`tests/`](../tests/)、[`scripts/`](../scripts/) | 回归案例、集成验证和打包脚本 |
| [`.github/workflows/`](../.github/workflows/) | NVDA 原生 CI 和发布流程 |
| [`docs/`](./)、[`CONTRIBUTING.md`](../CONTRIBUTING.md) | 使用指南、架构、发布和贡献说明 |

## 构建与参与维护

在 Windows 上准备 Git 和 **64 位 Python 3.13**，执行：

```powershell
git clone https://github.com/ChenZ2000/contextualPronunciation.git
cd contextualPronunciation
python scripts/build_addon.py
```

安装包生成在 `dist/` 中。打包命令使用 Python 标准库和仓库内已有的数据。

开发环境和测试命令见[开发指南](DEVELOPMENT.md#requirements-and-first-build)。修改读音逻辑时，请附上词典来源、需要纠正的正例，以及应保留另一读音的反例。规则、翻译、文档和 PR 的提交方式见[贡献指南](../CONTRIBUTING.md)。

开发和发布统一维护 `main` 分支，日常流程如下：

1. 向 `main` 提交 PR，并附上相关测试。CI 会构建并测试固定的 NVDA 稳定版和 Beta 版。
2. 发布前，更新 `manifest.ini`、`buildVars.py`、`pyproject.toml` 和发布说明。合并修改，等待该 `main` 提交的 CI 通过。
3. 运行 **Actions → Publish release from main**。工作流自动创建版本标签和 Release，附上安装包、校验和及商店提交字段。
4. 通过 NV Access 官方登记表单提交这些字段，由官方机器人创建商店 PR 并进入审核。

完整步骤见[发布指南](RELEASING.md)。

## 资料来源与参考

词典和语法数据主要来自以下项目：

| 来源 | 在本项目中的用途 |
|---|---|
| [CC-CEDICT / MDBG](https://www.mdbg.net/chinese/dictionary?page=cedict) | 词形、拼音和动词义项依据 |
| [开放汉语字典 KFCD](https://github.com/kfcd/hyzd) | 单字义项及例词中的目标字读音 |
| [Unicode Unihan](https://www.unicode.org/reports/tr38/tr38-39.html) | 字音交叉核对和多音字清单 |
| [OpenHowNet / THUNLP](https://github.com/thunlp/OpenHowNet) | 词性候选，以及食物、容器等语义类别 |
| [cppjieba](https://github.com/yanyiwu/cppjieba) | 分词词频和词性候选 |

[参考资料说明](REFERENCES.md#简体中文)列出固定快照、许可、生成文件、语言学资料和测试依赖，并说明教育部辞典、Universal Dependencies 中文关系说明、GF 0019-2018、NVDA、WorldVoice 和 CPP 测试集各自的用途。

## 支持与许可

维护者为 [ChenZ2000](https://github.com/ChenZ2000)，欢迎中英文反馈和贡献。报告误读时，请在 [Issue](https://github.com/ChenZ2000/contextualPronunciation/issues) 中提供完整句子、期望与实际读音、NVDA 和插件版本、语音引擎及相关设置。

程序代码使用 **GPL-2.0-or-later**，见 [LICENSE](../LICENSE)。词典数据保留各自的许可和署名，详见[第三方声明](../addon/THIRD-PARTY-NOTICES.txt)。其他现行指南及历史设计记录可从[文档索引](INDEX.md)查阅。
