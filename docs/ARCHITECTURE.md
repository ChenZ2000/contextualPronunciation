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

`colloquialMeng` supplies a broad `meng1` default for 懵 after reviewed literary protections and explicit user rules. It covers informal uses such as 一脸懵逼 and 懵了; `meng-literary-protection` preserves established third-tone contexts such as 懵懂. This is a configurable colloquial compatibility policy, not a claim that normative dictionaries changed the character's reading. The temporary rendering is now 擝 (U+64DD), whose pinned Unicode 17.0.0 Unihan `kMandarin` reading is `mēng`. The previous 蒙 rendering could be spoken as `méng`; 矇 has the same second-tone default and is not a suitable substitute. The shared rendering map is used by both default and extended modes. This fixes the ambiguous text rendering, not every voice's Unicode coverage: a voice that does not recognize 擝 can still mispronounce or omit it. Tests verify independent lexical evidence and the NVDA text pipeline, not target-voice audio.

`colloquialMeng` 在审定书面词保护和用户规则之后，为“懵”提供广泛的 `meng1` 默认，覆盖“一脸懵逼、懵了”等口语用法；`meng-literary-protection` 保留“懵懂”等三声语境。这是可配置的口语兼容政策，并不表示规范词典已改变字音。语音临时替代字改为“擝”（U+64DD），固定版本 Unicode 17.0.0 Unihan 的 `kMandarin` 将其标为 `mēng`。原替代字“蒙”可能被读成二声；“矇”的默认音也是二声，不作为替代。基础与扩展模式共用同一映射。这修复的是替代文本的多音歧义，不能补全声库的字库：不支持“擝”的声音仍可能误读或漏读。测试验证独立字音证据和 NVDA 文本管线，不冒充目标声音的音频验证。

## Neutral-tone rendering / 轻声输出

`annotationOnly` readings have no entry in the homophone map. Reviewed `speech: false` phrase decisions overwrite lexical decisions before the speech-only projection filters them out, while the shared annotation API retains their readings. Applying this to both syllables of 折腾 / 倒腾 / 捣腾 / 闹腾 / 掀腾 and their traditional forms preserves the whole word for the voice's lexicon. It fixes the previous 折腾 → 遮腾 and 倒腾 → 导腾 rewrites. User rules retain their normal precedence; the policy is not a global neutral-tone rule for 腾.

`annotationOnly` 读音不进入同音字映射。审定词组的 `speech: false` 决策先覆盖词典决策，再由仅语音投影过滤；共享注音接口仍保留其读音。折腾、倒腾、捣腾、闹腾、掀腾及其繁体形式的两个音节采用此策略，将完整词保留给声库词典，修复原先“折腾→遮腾、倒腾→导腾”的改写。用户规则保持原优先级，该策略不将所有“腾”都改为轻声。

There is no universal neutral-tone homophone or supported cross-driver command to force `teng5`. NVDA's public `PhonemeCommand` accepts IPA, but the pinned eSpeak and SAPI5 adapters cannot encode these Mandarin syllables; the reviewed Vocalizer driver uses fallback text. The add-on therefore preserves words rather than injecting phoneme commands. Automated tests verify reading decisions, text preservation and command handling; these changes still require acoustic checks on actual voices. See the [driver investigation](../tests/fixtures/vocalizer_expressive2/README.md) and [references](REFERENCES.md).

不存在可通用于声库的轻声同音字或强制 `teng5` 命令。NVDA 公开的 `PhonemeCommand` 接收 IPA，但固定版本的 eSpeak、SAPI5 适配器无法编码这些普通话音节，已审查的 Vocalizer 驱动只读回退文本。因此插件保留完整词形，不注入音素命令。自动测试验证读音决策、文本保留和命令处理；这些改动的实际声调仍需在真实声音上检查。参见[驱动调查](../tests/fixtures/vocalizer_expressive2/README.md)及[资料来源](REFERENCES.md)。

## Bounds and validation

Local analysis has character, token, depth, chart and per-item work limits. Repeated stems reuse results within the current speech item. Exhausted or incomplete analyses abstain. Cross-sentence reference, new words, metaphor, dialect and genuinely ambiguous attachment remain outside complete coverage.

Independent reading and preservation oracles live in `tests/grammar_cases.py`. Contrastive tests cover head attachment, transfer versus rotation, repetition, source provenance and user control. CPP evaluation is a separate external benchmark. Acoustic fixtures compare output with same-tone homophone anchors for specified voices; finite tests and matching audio do not establish universal accuracy. See [validation commands and performance policy](DEVELOPMENT.md#tests-and-native-integration).
