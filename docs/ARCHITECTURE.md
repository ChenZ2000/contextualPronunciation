# Pronunciation architecture / 读音分析架构

This document describes the current engine. Setup and testing are in [DEVELOPMENT.md](DEVELOPMENT.md); rule formats and annotation APIs are in [RULES.md](RULES.md). Dataset versions and licenses are in [REFERENCES.md](REFERENCES.md).

## Processing stages

1. **Original speech items.** Public NVDA extension points supply text and speech commands. The pipeline preserves commands, spelling mode and original character offsets.
2. **Lexical evidence.** Pinned dictionary readings, frequency data, POS alternatives and semantic candidates support bounded segmentation. Conflicting or unknown readings remain explicit.
3. **Context selection.** Reviewed phrases, templates and grammatical frames select readings. User literal rules and preservation take precedence. A syntactic proposal is not authoritative until the resolver selects it.
4. **Speech rendering.** Selected readings with a rendering and `speech=True` use temporary homophones. Decisions may instead retain the original characters while recording known readings. Documents, clipboard content and accessibility objects retain their original text. Residual reviewed 和 / 边 / 邊 / 行 contexts are rechecked after NVDA dictionaries and symbol processing.
5. **Annotations.** The shared API reports original characters, offsets and readings. The optional static braille table has its own compiled coverage; it does not run the dynamic speech parser.

Runtime processing is offline. It does not query source dictionaries, load a neural model, log spoken text or retain utterances between speech items.

## Evidence and ambiguity

| Input | Role | Constraint |
|---|---|---|
| CC-CEDICT, KFCD and Unihan | Word forms, aligned readings, character senses | Do not select the first reading of an ambiguous entry |
| cppjieba frequencies | Bounded arbitration when segmentations disagree | Frequencies are not pronunciation probabilities |
| OpenHowNet and dictionary definition heads | POS alternatives and semantic candidates | A candidate class is not a disambiguated sentence |
| Reviewed templates and argument frames | Reading selection in supported constructions | Every contribution needs sources and positive/negative examples |
| `data/semantic_projection.toml` | Build-time nominal sense families | Retain sense restrictions and generated record IDs |

`grammar_lexicon.json` contains 357,400 POS candidate headwords. Generated classes include 212 rotation candidates, 1,769 transfer-theme candidates and 68 indefinite-quantity candidates. Counts include source-authored simplified/traditional forms and are not accuracy estimates. Manually reviewed heads supplement generated candidates.

Generation matches nominal definition heads and permitted modifiers. It recognizes `engine (loanword)` and `electricity generator`, while rejecting `wheel factory`, software `search engine`, `thread of screw` and `screwdriver (cocktail)`. Family membership and source record IDs remain available in `semanticProjection.families` and `selectionEvidence`.

OpenHowNet supplies sense and role structure, not sentence pronunciation. Projection uses a root sense or explicit semantic role rather than any matching word inside a definition. See [OpenHowNet](https://github.com/thunlp/OpenHowNet). Physical tool functions are also checked against definitions such as [教育部《螺絲起子》](https://dict.revised.moe.edu.tw/dictView.jsp?ID=66368).

## Grammar and argument attachment

`constituents.py` identifies complete noun phrases, heads, modifiers, coordination and supported relative clauses. A noun inside a modifier cannot supply the meaning of an unrelated predicate. `verb_forms.py` recognizes complements and repeated predicates independently of pronunciation. `argument_roles.py` distinguishes recipients and quantity ellipsis; `motion.py` selects competing motion and transfer frames.

The instrument frame for 弹 / 彈 reuses the same noun chart for quantified, possessed and modified objects. A keyboard/plucked-string instrument must be the argument head; a mention inside a company name or another clause is insufficient. `containment.py` handles an omitted contents argument when 盛装 retains a parsed container goal or heads an action nominal. Attire governors remain protected. 装盛 / 裝盛 has a reviewed lexical default. The pronunciation sources are [MOE 彈琴](https://dict.revised.moe.edu.tw/dictView.jsp?ID=51192), [MOE 盛](https://dict.revised.moe.edu.tw/dictView.jsp?ID=8518) and [MOE 皿 with 裝盛](https://pedia.cloud.edu.tw/Entry/Detail/?search=皿&title=皿).

| Sentence | Evidence | Result |
|---|---|---|
| 让风车转起来 | Caused-motion object; phase complement | zhuàn |
| 汽轮机会转／引擎会转 | Mechanical subject; modal | zhuàn |
| 轴承转不起来 | Subject; negative potential complement | zhuàn |
| 螺丝刀转呀转／车轮转了又转 | Repeated predicates share arguments | Both stems: zhuàn |
| 出去转一转／去公园转转 | Serial motion or locative argument | zhuàn |
| 风车旁边的邮件能给他转吗 | Theme head 邮件; recipient 他 | zhuǎn, original glyph retained |
| 把螺丝刀转给经理 | Object being transferred; recipient | zhuǎn, original glyph retained |
| 给我转一转车轮 | Object 车轮; beneficiary 我 | zhuàn |
| 发动机转起来给大家看 | Mechanical subject; purpose clause | zhuàn |
| 我转了好多给客户 | Quantity expresses an omitted theme | zhuǎn, original glyph retained |

The reading distinction follows [教育部《轉》](https://stroke-order.learningweb.moe.edu.tw/dictMean.jsp?ID=36681&la=0). Terminology draws on [UD Chinese directional compounds](https://universaldependencies.org/zh/dep/compound-dir.html) and [object roles](https://universaldependencies.org/zh/dep/iobj.html); project-specific phase, recipient and purpose annotations supplement these terms. The engine does not claim a complete UD parse.

Action extents and durations such as 三次、两遍、三天 cannot become omitted transferred items merely because 给客户 follows. Explicit recipients and objects take precedence over incidental mechanical or place nouns. Mixed coordinated subjects must not borrow a feature from only one conjunct.

## Productive predicate forms

Supported forms include V, VV, V一V, V了V, V呀V, V啊V, V着V着, V了又V and V了再V, plus reviewed phase, direction, result, potential and aspect complements. Repetition shares argument structure; it does not itself determine a reading. The same mechanism serves existing 盛, 量 and 系 frames, as in 盛呀盛红豆粥、量呀量身高、系呀系鞋带.

Closed, standalone 转呀转／转啊转啊 uses a scoped motion default. Directional and transfer evidence can prevent that default. Compounds such as 转账 and 转身 cannot be split to manufacture a repeated bare verb. Groups have at most eight stems and do not cross punctuation.

The approach draws on slot/POS constraints in [北京大学构式知识库规范](https://ccl.pku.edu.cn/static/doc/CCGD_spec.pdf) and sustained versus repeated events discussed in [《汉语学习》2025 年第 3 期](https://hyxx.ybu.edu.cn/__local/B/BA/33/10324DB43AA58C6F4B98DADAD42_4FE5044B_A9171F.pdf). Papers are references, not bundled models or runtime dependencies.

## Defaults and user control

`chong-reinstall-default` selects chóng in 重装／重裝, including omitted objects. CC-CEDICT record `cc-cedict:110745` supports the reinstall reading. Explicit heavy-equipment and loaded-hiking expressions retain their protections. This rule does not globally increase the preference for chóng in every occurrence of 重.

Disabled rules and user `keep` remain authoritative. The resolver works on original text before rendering. An unavailable homophone can leave speech unchanged while an annotation still records a known reading. Absence of an annotation means unknown, not a guessed default.

`colloquialMeng` now calls the bounded positive-evidence matcher in `colloquial_meng.py`. It returns `meng1` only for supported colloquial words or constructions; otherwise it abstains. Reviewed literary phrases still precede structural rules; user literal rules and user templates retain their existing priority. No sentence-wide flag, unbounded scan, recursive propagation or new runtime lexicon is introduced. Each candidate uses at most 24 code points on each side and fixed inventories. Explicit reiteration checks at most one peer. Long bare runs cannot inherit a remote cue. See [the linguistic design and independent test inventory](COLLOQUIAL_MENG.md).

`colloquialMeng` 现调用 `colloquial_meng.py` 中的有限窗口正向证据匹配器，只在已支持的口语词或语法构式中返回 `meng1`，否则弃权。不再为所有未保护的“懵”设置默认声调。每个候选最多检查左右各 24 个码点及固定规则集合；重叠仅检查一个同伴，不递归传播、不跨语音项、不缓存用户文本。书面保护与个人规则优先级不变，长串单字也不会继承远处的一声依据。

The speech renderer remains 擝 (U+64DD), first-tone `mēng` in the pinned Unicode 17.0.0 Unihan data. The old 蒙 renderer and 矇 can default to `méng`. This is a text-rendering choice, not all-voice acoustic certification. Unmatched originals retain the synthesizer's existing reading; no universal `meng2` rewrite is installed. Documents, character offsets and clipboard contents remain unchanged, while Speech Viewer can show temporary homophones. The static braille table does not compile the dynamic positive-context rule.

语音替代仍用固定 Unihan 标为一声的“擝”，不退回多音字“蒙／矇”。未命中者保留原文及当前声库原有读音，不强制二声。替代字支持和实际声调仍需在目标声库试听；文档、剪贴板和原字符位置不变，Speech Viewer 可能显示临时同音字。静态盲文表不编译该动态口语规则。

## Neutral-tone rendering / 轻声输出

`annotationOnly` readings have no entry in the homophone map. Reviewed `speech: false` phrase decisions overwrite lexical decisions before the speech-only projection filters them out, while the shared annotation API retains their readings. Applying this to both syllables of 折腾 / 倒腾 / 捣腾 / 闹腾 / 掀腾 and their traditional forms preserves the whole word for the voice's lexicon. It fixes the previous 折腾 → 遮腾 and 倒腾 → 导腾 rewrites. User rules retain their normal precedence; the policy is not a global neutral-tone rule for 腾.

`annotationOnly` 读音不进入同音字映射。审定词组的 `speech: false` 决策先覆盖词典决策，再由仅语音投影过滤；共享注音接口仍保留其读音。折腾、倒腾、捣腾、闹腾、掀腾及其繁体形式的两个音节采用此策略，将完整词保留给声库词典，修复原先“折腾→遮腾、倒腾→导腾”的改写。用户规则保持原优先级，该策略不将所有“腾”都改为轻声。

There is no universal neutral-tone homophone or supported cross-driver command to force `teng5`. NVDA's public `PhonemeCommand` accepts IPA, but the pinned eSpeak and SAPI5 adapters cannot encode these Mandarin syllables; the reviewed Vocalizer driver uses fallback text. The add-on therefore preserves words rather than injecting phoneme commands. Automated tests verify reading decisions, text preservation and command handling; these changes still require acoustic checks on actual voices. See the [driver investigation](../tests/fixtures/vocalizer_expressive2/README.md) and [references](REFERENCES.md).

不存在可通用于声库的轻声同音字或强制 `teng5` 命令。NVDA 公开的 `PhonemeCommand` 接收 IPA，但固定版本的 eSpeak、SAPI5 适配器无法编码这些普通话音节，已审查的 Vocalizer 驱动只读回退文本。因此插件保留完整词形，不注入音素命令。自动测试验证读音决策、文本保留和命令处理；这些改动的实际声调仍需在真实声音上检查。参见[驱动调查](../tests/fixtures/vocalizer_expressive2/README.md)及[资料来源](REFERENCES.md)。

## Growth, length and honor / “长”的语境选择

`growth.py` selects zhǎng for a locally attached body location, growing subject,
growth-product object or growth complement. Reviewed noun senses in
`syntax_frames.toml` remain candidates until the noun chart identifies the head.
“身上长、背上长了、胸前长了” support an omitted product; “皮肤的文章很长”
uses the article head rather than borrowing the body-part modifier. Degree,
measured extent and adjectival 的/地 select cháng. Shared morphology in
`verb_forms.py` recognizes complements and repetition before sense selection;
“头发长长了” has a zhǎng stem and a cháng result, while “长长的头发” has two
adjectival cháng syllables.

“长个子” selects stature growth, including aspect inserted before its object
or an aspect-marked stature subject (“个子长了”).
Distributive adverbs such as 各自/分别 may accompany an omitted growing subject,
as in “各自长了”; a parsed length-bearing head retains the length sense.
The reviewed honor expression “长脸” uses zhǎng in “长脸了、给我长脸了”, with
the beneficiary attached independently. “一张长脸、长脸型、拉长脸” instead
select cháng. Ambiguous “长脸的孩子” and bare “头发长了” remain unchanged.

Pinned lexical words with an independently resolved zhǎng reading, including
生长、增长、校长、长辈, lock that inventory default for speech just as cháng
alternatives are rendered. Productive lexical forms yield to grammar and
cannot restore an unselected reading. User preservation and disabled senses
remain authoritative. The offline pronunciation tool reports argument heads,
localizers, aspects, beneficiaries and distinct stem/result dependencies.

Analysis uses a 96-character local window and the existing item/chart work
budgets. It does not cross punctuation or speech items. Constructed tests and
a separate short/8K latency gate cover these supported constructions; they do
not establish complete Chinese ambiguity resolution.

“快乐/快樂” explicitly locks lè before voice processing, whether punctuation
follows or not. This is a sourced lexical reading from
[MOE 快樂](https://dict.revised.moe.edu.tw/dictView.jsp?ID=78094).
The growth and length distinction follows
[MOE 長](https://dict.revised.moe.edu.tw/dictView.jsp?ID=7910), with
[拉長臉](https://dict.revised.moe.edu.tw/dictView.jsp?ID=59153) as a contrast.

## Unified selection and productive nominal senses

There is one automatic reading policy. Lexical variants are candidates, actual
heads and complements select productive senses, and unresolved ambiguity is
preserved. Strict mode no longer appears in configuration, runtime options or
speech/braille APIs. Legacy profile keys are ignored. The old medium-confidence
yuè key preference remains an inactive record so saved disabled-rule IDs stay
valid; an explicit personal rule can choose a variant.

`data/semantic_projection.toml` binds build-time nominal definition-head families
to semantic classes. The generator also projects living taxonomy roots,
physiological body parts with explicit hosts, and human-host stature senses from
pinned HowNet. Parenthetic restrictions and original sense/record IDs remain in
`grammar_lexicon.json`; runtime classes are competing candidates, not sentence POS
labels. The offline pronunciation tool reports the selected head's candidate
evidence alongside dependency offsets.

The growth grammar recognizes clipped 个/個 only at a complete nominal boundary,
including aspect and finite question particles. An overt following noun instead
uses the shared bare-classifier object production. No missing 子/儿 or fictional
source offset is inserted. Stature subjects, product-final aspect, independent
quantity complements and shared potential morphology support productive forms
without complete-sentence entries. Dense clipped nouns use the same validated
production directly, avoiding a redundant NP chart and speech-only dependencies.

Age quantities use animate age and explicitly restricted age-unit senses, with
independent human/pronominal comparands and original `extent:age` offsets.
“长我两岁 / 他比我长三岁” select zhǎng; an age mention inside an NP cannot
override its actual length-bearing head. Numeric overlaps such as dictionary
“长三” yield to productive quantity analysis. A closed quantity needs no general
object chart, while a following modifier requires the full head analysis.
The pronunciation follows [MOE 長 age/growth senses](https://stroke-order.learningweb.moe.edu.tw/dictMean.jsp?ID=38263).

## Bounds and validation

The syntax lexicon indexes candidate lengths by the first two source-word
characters, with a separate singleton fallback. It retains the same longest
word and original limits while avoiding unrelated candidates. This index holds
licensed lexical entries only. Speech-only analysis omits final dependency
record allocation; full offline analysis retains the same selected heads and
dependencies. Reading-decision parity is checked across the growth and motion
corpora, and startup reports include the static index's allocation cost.

Local analysis has character, token, depth, chart and per-item work limits. Repeated stems reuse results within the current speech item. Exhausted or incomplete analyses abstain. Cross-sentence reference, new words, metaphor, dialect and genuinely ambiguous attachment remain outside complete coverage.

Independent reading and preservation oracles live in `tests/grammar_cases.py`. Contrastive tests cover head attachment, transfer versus rotation, repetition, source provenance and user control. CPP evaluation is a separate external benchmark. Acoustic fixtures compare output with same-tone homophone anchors for specified voices; finite tests and matching audio do not establish universal accuracy. See [validation commands and performance policy](DEVELOPMENT.md#tests-and-native-integration).
