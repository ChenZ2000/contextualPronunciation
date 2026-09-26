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

### 安装并启用

当前发布版本为 **0.7.4**，最低要求及最后测试的稳定版均为 **NVDA 2026.2**。CI 另外验证 **2026.3beta2**。

1. 从 [Releases 页面](https://github.com/ChenZ2000/contextualPronunciation/releases/latest)下载 `.nvda-addon` 文件。
2. 打开文件，按 NVDA 提示安装并重启。
3. 继续使用平时的普通话声音朗读，默认纠正规则会自动生效。
4. 在 **NVDA 设置 → 上下文发音规范化** 中调整以下选项，点击“应用”或“确定”后立即生效。

### 设置选项

| 选项 | 默认值 | 作用 |
|---|---|---|
| 启用上下文发音改写 | 开启 | 控制中文读音改写和弯撇号规范化。关闭后暂停这两类改写。 |
| 纠正已支持的中文多音字 | 开启 | 启用内置中文纠正和个人读音规则。关闭后，中文读音交给原语音处理，撇号处理仍可保留。 |
| 使用扩展词组库（实验性；可能引入错误读音） | 关闭 | 增加基于词典的词组覆盖。可用熟悉的文本对照试听，出现误改时关闭；关闭后仍可使用已审阅规则和个人规则。 |
| 规范化拉丁单词内的弯撇号 | 开启 | 在朗读时把单词内的 `’` 转成 `'`，例如 `doesn’t` → `doesn't`。关闭后保留弯撇号形式。 |
| 严格模式（歧义文本保持原样） | 开启 | 使用保守的读音策略。当前关闭后会额外为“密钥、公钥、私钥”的“钥”启用 yuè 读音偏好。一般保持开启即可。 |

“**上下文模板**”“**自定义固定词规则**”“**禁用规则 ID**”三个文本框默认均为空，填写方法见下面的子章节。个人中文规则需要同时开启“上下文发音改写”和“中文多音字纠正”。这些设置可以分别保存在不同的 NVDA 配置方案中。

中文纠正会对所有声音和语言标签下的汉字应用普通话读音。使用粤语、日语等读法时，可在对应的 NVDA 配置方案中关闭中文纠正。

关闭改写或撇号规范化选项后，已安装的撇号保护符号字典仍会生效。要停用插件的全部功能，请禁用或卸载插件并重启 NVDA。

### 自定义上下文模板

在“**上下文模板**”中，每行输入一条“`前文[目标字:拼音]后文`”规则。目标字为单个汉字，前文和后文至少填写一侧；普通文字按原样匹配，也可以使用已支持的占位符表示一类文本。

```text
仙[乐:yuè]
[盛:chéng]{number}{container}
```

- `仙[乐:yuè]`：指定“仙”后面的“乐”读 yuè，放在“仙乐飘飘”等完整句子中也能匹配。写成 `仙[乐:yue4]` 效果相同。
- `[盛:chéng]{number}{container}`：指定“盛”后面接数量和已列出的容器时读 chéng，例如“盛一碗”“盛两杯”。`{number}` 匹配最多 12 个中文或阿拉伯数字字符；`{container}` 匹配“碗、杯、勺、盆”等内置词项。
- `{space}`：允许出现零到四个已支持的空白字符。例如 `[盛:chéng]{number}{space}{container}` 还可匹配“盛一 碗”。其他可用类别列在[规则数据文件](../addon/globalPlugins/contextualPronunciation/data/contributions.toml)中。

希望保留原字，交给原语音或后续的 NVDA 语音词典处理时，将拼音改为 `keep`：

```text
仙[乐:keep]
```

对同一语境，可用这条保留规则替换上面的 yuè 规则。每条模板只指定一个目标字，请按示例使用英文半角 `[]`、`:` 和 `{}`。拼音支持声调符号或数字声调，ü 可写成 `v`，例如 `lǜ` 或 `lv4`。可用读音受插件已有同音映射范围限制；同优先级的个人模板出现读音冲突时，会保留原字。

### 自定义固定词规则

希望为一个确定的短语指定读音时，在“**自定义固定词规则**”中每行填写一条，用英文半角竖线 `|` 分隔三个字段：

```text
仙乐|乐|yue4
盛汤|盛|keep
```

三个字段依次为“**短语 | 目标字 | 读音 ID 或 keep**”。第一行让“仙乐”中的“乐”读 yuè；第二行保留“盛汤”中的“盛”。读音 ID 使用数字声调，如 `yue4`、`chang2`、`lv4`。短语长度为 2–64 个字符，目标字必须在短语中恰好出现一次，同一短语和目标字的组合只填写一条。

两种个人规则都可以在扩展词组库关闭时使用。同一位置同时匹配个人固定词规则和个人上下文模板时，固定词规则优先。通常为一处读音选择一种格式即可。

### 禁用规则与恢复设置

“**禁用规则 ID**”接受用英文逗号或换行分隔的内置规则标识。例如，填写 `rowIndefiniteQuantity` 可停用处理“多行”等不定行数的一条规则。可用 ID 记录在[核心规则](../addon/globalPlugins/contextualPronunciation/data/rules_zh_CN.json)和[句法框架](../addon/globalPlugins/contextualPronunciation/data/syntax_frames.toml)中，也可在排查时由维护者协助确认。填写未知 ID 会在保存时提示错误。其他匹配规则仍可能影响同一个字；希望某个短语保留原字时，可使用局部 `keep` 规则。

撤销个人规则或恢复某条内置规则时，删除相应行或 ID，再点击“应用”。要恢复当前配置方案中的默认设置，请清空三个文本框，关闭扩展词组库，并开启其余四个复选框。若保存时提示规则无效，请按错误信息修改相应字段后再保存。

插件会向合成器发送临时的发音替代文本，因此语音查看器可能显示同音替代字；文档和剪贴板内容保持原样。WorldVoice、可选盲文输出及常见问题见[使用指南](USAGE-zh_CN.md)。

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
