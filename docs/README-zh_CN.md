# Context-aware Pronunciation 0.7.4 · NVDA 2026.2 / 2026.3beta2

上下文发音规范化插件。0.7.3 修复“下边缘”“唱和说”“多行”的分词和发音问题，新增语音词典处理之后、进入合成队列之前的目标读音检查。默认支持，保留用户设置和字符模式。1,154 个定向语法案例覆盖读音与保留原字。详见 [0.7.3 分词边界与合成前读音](0.7.3-分词边界与合成前读音.md)。

这是技术预览：不会保证所有汉语语境或零延迟。新引擎为有计算预算的符号成分分析，尚不是任意全文的完整语义理解。词法资料包含 357,293 个词头、82,381 个动词候选；候选数不是正确率。运行时不联网、不加载神经模型、不查询 SQLite、不记录朗读内容。详细实现、资料、105 条定向对照与限制见 [0.7.0 组合句法与重动词](0.7.0-组合句法与重动词.md)。

0.7.4 为首次公开仓库发布，发音引擎与 0.7.3 一致。商店稳定通道清单声明 NVDA 2026.2；2026.3beta2 是附加开发验证目标。安装包从 [GitHub Releases](https://github.com/ChenZ2000/contextualPronunciation/releases/latest) 下载。

## 安装与设置

1. 安装 `contextualPronunciation-0.7.4.nvda-addon`，按 NVDA 提示重启。标识不变，可覆盖升级；开发流程不会替你安装、重启或切换语音。
2. NVDA 设置 →“上下文发音规范化”：保留“启用上下文发音改写”“纠正已支持的中文多音字”和“严格模式”。已移除语音适配方案下拉框。旧方案为“关闭”时迁移为关闭中文纠正，避免升级擅自重启曾关闭的功能；需要时重新勾选即可。
3. 普通话规则对所有声音、包括英语、粤语、繁体及日语语言标签下的汉字一视同仁。不会切换声音，也不能让不支持普通话的声音获得普通话能力；方言或其他语言的汉字可能因此被误改。可用中文纠正开关、局部 keep 或 NVDA 配置方案控制。
4. **扩展词组库为实验性，默认关闭**；勾选后启用大规模候选词库。发现误改可先关闭扩展库，原有审阅规则继续生效。
5. 本轮新增规则默认生效，不需扩展库：系领结／系了一条领带／把绳子系在树上 → jì；用尺子量长度／身高量了两次／用卷尺重新量一量／量三米布／量杯 → liáng。联系、心系、重量、数量、校量、估量、商量、量体裁衣等另有保护；动词不一定读二声，名词也不一定读四声。原有审阅规则和钥 yuè 的非严格模式可选偏好保留。没有可用同音映射的注音不强制改写语音。
6. 保留 Doesn't／Doesn’t／Mike's／Mike’s 的词内撇号保护。关闭改写总开关不移除 mandatory 符号字典；彻底恢复需禁用或卸载插件并重启。键入单词回显提前分段的撇号情况仍不在已验证范围内。
7. 新局部句法默认生效：盛豆角／盛红豆粥／盛刚煮好的红豆粥 → chéng；量小名的身高／量住在隔壁的小名的身高 → liáng；系小名的鞋带 → jì。未知姓名不需逐个入库。宾语中心词不明、歧义或结构超限时保留原字。
8. “降调音频”的通用跨词读音锁定属于**扩展词组库**，需要第 4 项开关开启。该句原本已分成“降调／音频”，但默认 diào 没有强制输出；现在发现“调音”跨越已选词边界时，把 diào 也落实到临时语音文本中。“调音师”仍为 tiáo。不新增整句特例，不把所有默认读音一律替换。

0.7.0 新增：重转／重编译／重转码／重压缩 → chóng；“盛那碗刚刚煮好而且非常香甜的红豆粥” → chéng；“量住在那条非常安静的街道旁边的小名的身高” → liáng；“系那条又细又长的红色丝带” → jì。新能力默认生效。重视／重用／重罚及不明复合词仍受保护；有歧义的裸词不强行猜音。

## 全局流程与 WorldVoice 6.2

注册 NVDA 公开的 `filter_speechSequence` 和 `pre_speechQueued`：前者处理原始语音序列，后者在语音词典与符号处理之后检查残留的和、边、邊、行读音。命中规则后，在原文位置上先裁决、再一次性生成临时语音文本；所有声音统一使用同一份不可变映射，包括 chéng → 呈。不会反复重写前一次结果。索引、语言、音高等命令原样保留；逐字／拼读模式不做上下文改写，也不跨命令或分段猜测。

WorldVoice 6.2 把自己的公开词典过滤器移到开头，因此其词典产物可继续参与本插件纠正。已验证词典 `测试词 → 仙乐飘飘` 后接 `仙月飘飘`，前置和后置语言检测下各执行一次。不包装 WorldVoice 内部函数，不改其文件、声音实例、用户词典或 NVDA 核心。

需要注意 WorldVoice 的 Unicode 替换次序：检测为“before”时，其 Unicode 替换先于本插件；检测为“after”时，Unicode 替换晚于本插件。若它要替换的原字已被本插件改写，则后置规则不会再命中。想优先保留原字规则，可在本插件添加局部 keep，或自行选择 WorldVoice 的前置检测；插件不会替你调整设置。

WorldVoice 6.2 兼容性检查使用固定官方源码及隔离声音替身。维护者可另外对合法安装的 WorldVoice 目录运行同一组源码调用链测试；这些结果不代表所有声音的听审。

## 开放词典与规范化数据库

数据由 [CC-CEDICT](https://www.mdbg.net/chinese/dictionary?page=cedict)、[开放汉语字典 KFCD](https://github.com/kfcd/hyzd/tree/04987755b16264636c01d28df4d96fa14dadd210) 和 [Unicode Unihan](https://www.unicode.org/reports/tr38/tr38-39.html) 组成。开放许可不意味着国家审音标准，也不存在这些资源已解决任意语义歧义的保证。

离线源数据库包含 131,436 条词条／字义记录：CC-CEDICT 125,009 条，KFCD 6,427 条。保留原始繁简字形、原始拼音、规范数字调拼音、释义、来源行号与逐条许可。不取异读列表首音，不擅自合并地域读音。开发用 JSONL gzip 与来源清单随源码提供，可另建 SQLite 索引；均不进入朗读热路径。

编译后的实验性扩展库含 183,244 个词头，其中 147,598 个可提供全部或部分注音，35,646 个为阻断词。覆盖 1,218 个非默认读音目标字，623 个具备当前自动替换政策所需的候选条件，7,903 个词头含可渲染非默认候选。繁体扩展来自源词典原有词形，而非逐字繁简转换。**这些数值是词典候选规模，不是已经证实的引擎错误数或句子准确率。**

新的离线 `data/polyphone-coverage.json` 完整列出固定 Unihan 字段中具有多个规范拼音的 8,372 个字、19,570 个字音组合，含历史、地域和异体读音，不代表现代常用多音字数量。每个读音记录词头计数、样例、现有规则、同音映射候选和待补上下文状态。清单不进入朗读路径。用户提供的 go-cc/cc-table 常用表经审查仅作候选参考，未将其错行、错误注音或未核实的转载数据直接导入。

同词异读、专名、儿化不对齐、缺少字音依据及轻声语法风险会阻断或逐位置弃权。字典“某字义下的例词”只能证明目标字，不能替例词其他字补音。例如“薄荷”中来源对“荷”的轻声／本调有差异，只撤回“荷”，保留有依据的“薄”bò。双向最长匹配一致时走快速路径；不一致的小区间才进入词频加权词图。最长词 32 字、分歧区间最多 96 字；不截断超限区间，不覆盖一致词和歧义阻断词。词频采用 NVDA beta 同版本 cppjieba 的开放数据，不是词性预测或读音置信概率。

NVDA 2026.3beta2 的中文分词主要服务词导航和盲文空格；其内部接口不输出拼音。插件不调用私有分词接口、不修改共享分词词典，在 2026.2 与 beta 上使用同一份固定离线资源和同一裁决流程。

0.6.1 使用 [OpenHowNet](https://github.com/thunlp/OpenHowNet) 固定核心数据及官方义原分类树：215,831 条词性／义原记录、117,464 个汉字词头，其中 2,760 个词头的名词义一致支持食物类别，4,455 个支持容纳物类别，451 个支持容器类别；类别可以重叠，不能相加当作新词数。147 个食物和 291 个容纳物多义候选仍保留歧义。它们不是新增 11 万条拼音规则，也不是语境正确率。仅分发所需词法特征与可审计来源，不包含原 API、可执行 pickle、BabelNet 或神经模型。分类树只在离线编译时遍历，词性集合不冒充句中词性预测。

## 易读规则与贡献

设置中一行一个模板，例如：

```text
仙[乐:yuè]
[盛:chéng]{number}{container}
仙[乐:keep]
```

最后一条是局部保留示例，不必与第一条同时输入。支持带调及数字调拼音，ü 不等于 u；每条一个目标，每侧最多 64 字上下文，数字最多 12 位，空格最多 4 位。不执行任意正则或 Python；同级异读冲突时保留原字。旧“短语|目标字|readingId”格式兼容。

贡献文件为 `addon/globalPlugins/contextualPronunciation/data/contributions.toml`，每条保留来源、正例和反例。详见 [贡献规则与盲文接口](贡献规则与盲文接口.md) 和 [0.3.0 全局规范化与开放词典设计](0.3.0-全局规范化与开放词典.md)。

## 国家通用盲文 2018

安装重启后，可手动选择盲文输出表 **Chinese common braille 2018 - contextual phrases (experimental)**。沿用 NVDA 的 `zhcn-cbs.ctb`。审阅模板展开为 12,057 个有限上下文组合（11,697 纠正、360 保护），不是同等数量的独立词条或人工逐句验证结果。生成器合并等价有限选项，连同“量体温／量体重／量体积”的三个基础词组覆盖条件，共输出 455 条匹配指令；避免逐项展开拖慢翻译。0.6.1 仅同步新增繁体“盛裝”的静态保留，不代表动态容纳结构已接入盲文。不会自动切表，不使用语音替代字，不提供盲文输入；选回原表即可恢复。

这是有限固定语境增强：静态表与语音开关独立，自定义设置、数量结构和实验性词库不会动态同步。支持 beta 分词插入的单个 ASCII 词间空格，不跨换行；“量体”覆盖保留基础表原有的两字路由分组。其他更长基础词仍可能优先。“在光标处展开为计算机盲文”会按 NVDA 的设计绕过上下文规则；插件不替用户关闭该设置。不是完整分词连写或 2018 全条款翻译器。

`GlobalPlugin.getReadingAnnotations(text)` 和纯 Python API 共享读音裁决，保留原字、来源、Unicode／UTF-16 原文偏移；未知位置不生成假定读音。API 点位预览是全标调注音，不等于正式表的省调结果。不拦截所有盲文区域。

0.6 的局部句法和跨词锁定已进入这个共享注音 API，但**没有动态接管实际 Liblouis 盲文输出**。静态表维持原有范围；不能把语音中的“呈／梁／吊”送给盲文，也不宣称这些新组合已经自动出现在所有盲文区域。

## 验证范围与局限

自动化覆盖原文不可变、命令保留、语言标签无关、逐字模式、旧配置迁移、WorldVoice 词典顺序、句中重复命中、全部 Unicode 标点／符号边界、整库回读、来源冲突、许可溯源、NVDA 原生链路和实际 Liblouis 输出。

VE Ting-Ting 固定语料仍做完整音素流与独立同音锚点回归；另外有本机 eSpeak 普通话音素和 Microsoft Huihui Desktop 离线 WAV 探测。后两者是观测而非全量准确率门禁：字典缺词、韵律及声学差异必须与真正误读区分，不能按 PCM 是否相同给所有引擎打“正确／错误”标签。新语料仍需实际试听和其他活跃声音验收。

CPP 测试集审计报告判断覆盖率、已判断项的标注一致率、弃权和主动改写差异，不把弃权计为正确，也不是所有汉语场景准确率。最新数据见 `artifacts/cpp-evaluation.json`。

同音字后端不是通用音素 API。Speech Viewer 可能显示临时同音字；原文、剪贴板、无障碍对象不变。严格性能门禁仍生效，但计量的是批量平均耗时的多轮中位数，不是端到端 p99，不包括音频设备、COM、取消和操作系统调度延迟。

## 构建与复现

```powershell
python scripts/prepare_nvda.py
python scripts/prepare_worldvoice.py
python scripts/prepare_cpp.py
python tools/build_dictionary_database.py --check
python tools/build_dictionary_database.py --query 盛汤
# 可选：建立新的离线索引；拒绝覆盖已存在的数据库
python tools/build_dictionary_database.py --sqlite artifacts/dictionary-review.sqlite3
python tools/import_cedict.py --check
python tools/build_segmentation_data.py --check
python tools/build_syntax_data.py --check
python tools/build_grammar_data.py --check
python tools/evaluate_grammar.py
python tools/benchmark_grammar.py
python tools/build_polyphone_coverage.py --check
python tools/build_polyphone_coverage.py --query 行
python tools/build_braille_table.py --check
python tools/pronunciation.py --check-contributions
python tools/pronunciation.py "仙乐飘飘，盛汤" --output artifacts/reading-example.json
python scripts/run_tests.py
python scripts/build_addon.py
# 完整发布门禁：需要 C++ 工具链与本机合法 VE 声库
python scripts/run_regression.py --native --vocalizer --release
# Beta 原生测试使用独立目录和固定源码，不升级正在运行的 NVDA
$env:CONTEXTUAL_PRONUNCIATION_NVDA_VERSION = '2026.3beta2'
python scripts/run_regression.py --native --vocalizer --release
# 下一次恢复测试稳定版
$env:CONTEXTUAL_PRONUNCIATION_NVDA_VERSION = '2026.2'
```

本机还可传 `--installed-worldvoice 安装目录` 测实际安装的 6.2 源码，传 `--cross-engine-probes` 记录 eSpeak／SAPI 离线观测；不切换活跃语音，不保存用户配置。原生编译的 LLVM／ATL 参数见构建脚本。

修改规则后运行 `tools/build_braille_table.py` 和三个声学 fixture 生成命令：`tools/generate_final_renderer_fixture.py`、`tools/boundary_acoustics.py generate`、`tools/sentence_acoustics.py generate`，再执行完整验证；不能只刷新哈希而复用旧音频宣称通过。

Windows CI 使用 2026.2 / 2026.3beta2 双版本矩阵，包含原生编译、测试、数据复现、CPP 和性能门禁。云端性能检查将当前代码与固定基线放在同一台运行器上顺序测量，每项中位耗时不得超过基线的 1.30 倍或基线加 5 微秒两者中的较大值，并检查场景、输入长度和采样数一致；原始报告和超出绝对门限的记录随 CI 保存。热路径测量使用 7 轮、每轮短文本 10,000 次或长文本 20 次，两边使用相同的固定 Python 哈希种子，语法场景短文本各 1,000 次、长文本各 100 次；本机严格验收仍使用原来的绝对门限。完整策略见[开发指南](DEVELOPMENT.md)。

长期开发和发布只维护 `main`。更新版本并等待该提交的双版本 CI 通过后，在 Actions 中选择 **Publish release from main → Run workflow → main**；流程自动读取版本、创建版本标签并构建正式 GitHub Release，无需手工建立发布分支或推送标签。Release 附带 `store-submission.md`，商店 Source URL 指向本版本的 Release 页面，License URL 使用 GNU 官方原文。维护者仍需通过官方表单提交商店审核，具体步骤见[发布指南](RELEASING.md)。

云端不运行专有声库检查，不能据此宣称完成音频验收。Beta 的 5 个 DotPad BLE 测试在上游源码中主动标记未实现；仅对固定版本、具体测试 ID 和相同原因记为跳过，不算通过，不放宽其他跳过。最终证据为 `artifacts/release-verification.json` 与 `artifacts/workflow-report.json`，另一版本的冻结证据保留在 artifacts 子目录。源码包不包含本机音频、配置、专有 DLL 或声库。

代码 GPL-2.0-or-later；CC-CEDICT 数据 CC-BY-SA-4.0，KFCD 原始数据 CC-BY-3.0，Unicode 数据保留原许可，cppjieba 词频及 OpenHowNet 核心投影保留 MIT；词典集合与既有衍生拼音库按 CC-BY-SA-4.0 提供，同时保留各来源许可。详见 [第三方说明](../addon/THIRD-PARTY-NOTICES.txt)。
