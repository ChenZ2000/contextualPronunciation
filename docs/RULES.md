# 规则贡献与读音接口 / Rules and annotation API

开发环境和测试命令见 [Development](DEVELOPMENT.md)，语义选择原理见 [Architecture](ARCHITECTURE.md)，来源版本和许可见 [References](REFERENCES.md)。

## 选择修改位置

| 修改内容 | 位置 |
|---|---|
| 已审定固定词与保护 | 插件内 `data/rules_zh_CN.json` |
| 有界上下文模板与有限词类 | 插件内 `data/contributions.toml` |
| 语义论元框架 | 插件内 `data/syntax_frames.toml` |
| 名词释义投影类别 | 根目录 `data/semantic_projection.toml`，运行 `tools/build_grammar_data.py` |
| 可组合动词形态／句法 | `verb_forms.py`、`constituents.py`、`argument_roles.py` 等共用模块 |

生产性结构应修改共用语法，不逐条加入完整运行时例句。词性和语义类是候选，必须分析实际中心词与附着关系。贡献应附词典或语言学来源、纠正正例、另一义项的反例及证据不足时的处理。

## 模板格式

`contributions.toml` 中每条规则必须有稳定 ID、上下文、来源与正反例：

```toml
[[rules]]
id = "example-celestial-music"
pattern = "仙[乐:yuè]"
source = "教育部简编本 仙樂 https://dict.concised.moe.edu.tw/dictView.jsp?ID=27272&la=0&powerMode=0"
positive = ["仙乐飘飘", "听见仙乐以后"]
negative = ["快乐", "乐观", "乐高"]
```

已有等价规则时不重复加入。用户设置只填 `pattern`，每行一条。

- `[字:拼音]` 恰好指定一个目标，其余文字按字面匹配。
- `[字:keep]` 保留该位置，并从共享注音中撤回读音。
- 支持 `yuè/yue4`、`lǜ/lv4/lu:4`；无调 `de` 表示 `de5`。
- `{number}` 匹配 1–12 位指定数字，不截取超长数字的一部分；`{space}` 匹配 0–4 个行内空白。
- 命名类来自 `[classes]`，最多 64 个选项，每项 1–8 字。
- 每条最多 160 字符，每侧最多 64 字上下文和 4 个占位符；用户最多 256 条。正则元字符按字面处理。

同级不同读音冲突时弃权。用户固定词规则优先于用户模板；用户模板优先于内置模板；内置核心保护优先于内置模板。合法拼音只证明格式受支持，仍须核对目标字是否有该读音。

## 词典与生成数据

`data/sources/` 保存固定版本、带校验和的许可源文件。`kind=word` 的对齐拼音序列与 `kind=characterSense` 的候选读音集合不同。词库 `?` 表示未知位置，API 对应 `None`，不能补成默认读音。

简繁词形来自源词典，不做逐字自动转换。同一字位来源冲突时撤回该字位；专名或整词异读阻断不能凭单个例词解封。词频仅用于有界分词裁决，不能为测试句伪造频率。新词义投影保留来源记录及括号内义项限制。

```powershell
python tools/build_dictionary_database.py --query 重装
python tools/build_polyphone_coverage.py --query 转
python tools/pronunciation.py "把螺丝刀转给经理"
python tools/pronunciation.py --check-contributions
```

`pronunciation.py` 展示原文位置、词法范围、实际语音文本、来源及句法建议。`selected` 表示建议是否被最终采用。可用 `--templates 文件` 读取 UTF-8 模板、`--output 文件` 写入诊断。只使用匿名测试文本。

更新数据后运行对应生成器及 `--check`，命令见 [Development](DEVELOPMENT.md#reproducing-data)。`data/polyphone-coverage.json` 是固定 Unihan 字段的多读音字清单，`data/lexicon_coverage.json` 是词库候选清单；均不表示每字所有语境已经实现。

## 共享读音 API

活跃插件的 `getReadingAnnotations(text)` 返回不可变注音元组，服从启用、严格模式及用户规则。纯 Python `braille_readings.annotate(text, compiled_rules)` 不加载 NVDA。

| 字段 | 含义 |
|---|---|
| `start/end` | 原文 Unicode code point 半开区间 |
| `utf16_start/utf16_end` | 原文 UTF-16 code unit 半开区间 |
| `character` | 原字，不是语音替代字 |
| `reading` | 带数字本调拼音，如 `yue4`、`cheng2` |
| `source` | 规则 ID 或词库来源 |
| `dots/cells` | 全标调注音；未支持编码为 `null` |

`😀仙乐` 中“乐”的 code point 区间是 `[2,3)`，UTF-16 区间是 `[3,4)`。消费者不得混用偏移。缺席区间表示未知，不能自动填入确定默认音。

## 静态盲文表

`tools/build_braille_table.py` 编译支持的固定上下文及可枚举模板；动态句法与数字规则明确列为未编入。个人语音设置不会写回静态表。全标调预览不等于国家通用盲文的省调、连写结果。

编译器可合并等价有限类，但必须保留保护优先、冲突审计及位置映射。`--reference-output 新文件.ctb` 生成未合并差分参照，拒绝覆盖已有文件；原生 Liblouis 测试比较盲文格及全部位置映射。`data/braille_contexts.toml` 只处理基础表较长条目阻挡纠正的审定固定语境，须记录点位、边界及来源。

正式盲文输出使用原文和读音信息，不能接收语音临时替代字。光标处计算机盲文展开仍由 NVDA 处理。覆盖范围见 `data/braille_coverage.json`；真实硬件路由和阅读体验需单独验证。
