# Pronunciation architecture / 读音分析架构

This document describes the current engine. Setup and testing are in [DEVELOPMENT.md](DEVELOPMENT.md); rule formats and annotation APIs are in [RULES.md](RULES.md). Dataset versions and licenses are in [REFERENCES.md](REFERENCES.md).

## Processing stages

1. **Original speech items.** Public NVDA extension points supply text and speech commands. The pipeline preserves commands, spelling mode and original character offsets.
2. **Lexical evidence.** Pinned dictionary readings, frequency data, POS alternatives and semantic candidates support bounded segmentation. Conflicting or unknown readings remain explicit.
3. **Context selection.** Reviewed phrases, templates and grammatical frames select readings. User literal rules and preservation take precedence. A syntactic proposal is not authoritative until the resolver selects it.
4. **Speech rendering.** Selected readings use temporary homophones. Documents, clipboard content and accessibility objects retain their original text. Residual reviewed 和 / 边 / 邊 / 行 contexts are rechecked after NVDA dictionaries and symbol processing.
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

## Bounds and validation

Local analysis has character, token, depth, chart and per-item work limits. Repeated stems reuse results within the current speech item. Exhausted or incomplete analyses abstain. Cross-sentence reference, new words, metaphor, dialect and genuinely ambiguous attachment remain outside complete coverage.

Independent reading and preservation oracles live in `tests/grammar_cases.py`. Contrastive tests cover head attachment, transfer versus rotation, repetition, source provenance and user control. CPP evaluation is a separate external benchmark. Acoustic fixtures compare output with same-tone homophone anchors for specified voices; finite tests and matching audio do not establish universal accuracy. See [validation commands and performance policy](DEVELOPMENT.md#tests-and-native-integration).
