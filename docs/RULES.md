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

## 口语默认与轻声 / Colloquial defaults and neutral tone

`colloquialMeng` 只在有正向口语语法依据时，为“懵”选择 `meng1` 并临时输出“擝”（U+64DD）。它不再是“未命中保护词就改一声”的默认。支持词汇化口语、数量＋脸、状态谓语、动作结果补语、程度／结果／时量补语、带主语的状态、疑问、比较和受限重叠；完整句子不必逐条列入。孤立字、字词提及、书面词和无充分依据的语境保留原文及声库原读音，不全局强制 `meng2`。资料、对比用例和识别边界见 [Colloquial 懵](COLLOQUIAL_MENG.md)。

`colloquialMeng` selects `meng1` and renders 擝 only with positive evidence for a supported colloquial construction. It no longer defaults every unprotected occurrence to first tone. Lexicalized forms, numeral + 脸, state predicates, resultative compounds, degree/result/duration complements, grounded subjects, questions, comparison and bounded reiteration generalize beyond a finite list of complete sentences. Isolated characters, lexical mentions, literary words and unsupported contexts keep the original text and voice reading; no global `meng2` rewrite is added.

`meng-literary-protection` 继续先于口语结构判断，扩充“懵头转向／懵頭轉向、懵懵然”等保护。用户可停用 `colloquialMeng`，或使用固定词、模板与 `keep` 覆盖个别语境。用户固定词优先于用户模板，用户模板仍可覆盖内置书面保护。`meng-literary-protection` still precedes colloquial structural matching and now also covers 懵头转向 / 懵頭轉向 and 懵懵然. Disabling `colloquialMeng`, literal rules, templates and `keep` retain their existing semantics and precedence.

核心读音定义 `"teng5": {"annotationOnly": true}` 登记没有同音替代字的轻声，不能同时指定 `replacement`。词组的 `speech: false` 保留已知读音及原字，仍先于扩展词典裁决；它与撤回注音的 `protect` 不同。当前对折腾、倒腾、捣腾、闹腾、掀腾及各自繁体形式的两个音节使用这一策略，避免“遮腾、导腾”等替换破坏整词识别。新规则不推广到翻腾、扑腾或所有“腾”。用户固定词仍只接受可用同音替代读音或 `keep`；模板可以记录 `teng5`。个人覆盖权限与规则停用机制保持不变。

The core definition `"teng5": {"annotationOnly": true}` registers a neutral-tone reading without a homophone; it cannot also contain `replacement`. A phrase rule with `speech: false` retains its known reading and original character while overriding extended lexical decisions. Unlike `protect`, it does not withdraw the annotation. Both syllables of 折腾, 倒腾, 捣腾, 闹腾, 掀腾 and their traditional forms use this policy, preventing replacements such as 遮腾 and 导腾 from breaking whole-word recognition. The new rules do not extend to 翻腾, 扑腾 or every 腾. User literal rules still accept only available homophone readings or `keep`; templates may annotate `teng5`. Existing user precedence and rule disabling remain unchanged.

完整词交给声库识别轻声；插件没有跨声库强制轻声的通用接口。0.7.9 原来的“蒙”替代字可能被读成二声；现用固定 Unihan 资料标为一声的“擝”。“擝”是生僻字，声库仍须支持它；文本、字音来源与注音测试不等于实际声调验证，仍需在目标声库上实测。无法识别该字时可停用 `colloquialMeng` 恢复原文，不会自动退回已知有二声歧义的“蒙”。

Whole words let the voice apply its neutral-tone lexicon; the add-on has no universal interface to force neutral tone. The 0.7.9 蒙 renderer could produce second tone; the replacement 擝 is first tone in the pinned Unihan data. 擝 is rare and must be supported by the voice. Text, lexical-source and annotation tests do not certify its actual tone. Verify it on the target voice; disabling `colloquialMeng` restores the original text if unsupported, rather than silently falling back to the ambiguous 蒙 renderer.

保护和纠音只使用当前语音文本项，不跨字符串或命令拼接上下文；例如拆成两个文本项的“懵”“懂”无法按完整“懵懂”匹配，但孤立“懵”现已弃权，不再被默认改成一声；“懵”“了”拆项也不会合并判断。轻声规则也保留“曲折｜腾挪”“打倒｜腾空”等已审定跨词竞争语境，不把相邻字一律认作轻声词。

Protection and correction use only the current speech text item; strings and commands are not joined. Separate items containing 懵 and 懂 cannot match the complete protected word, but isolated 懵 now abstains rather than defaulting to first tone; separate 懵 and 了 items are not joined either. Reviewed crossing-word contexts such as 曲折 | 腾挪 and 打倒 | 腾空 also block neutral-word matching.

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
