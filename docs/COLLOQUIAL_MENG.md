# Context-only colloquial 懵 / 口语“懵”的语境识别

[Architecture](ARCHITECTURE.md) · [Rules](RULES.md) · [User guide](README-en.md) · [使用指南](USAGE-zh_CN.md)

## Policy / 策略

0.8.0 removes the unconditional `meng1` fallback. First tone is selected only for supported uses of colloquial 懵 meaning a confused, dazed or bewildered state. A bare character, a lexical mention, a reviewed literary word, or insufficient evidence keeps the original text. **Preservation is not a new second-tone instruction.** A voice that previously reads an unmatched original as second tone retains that behaviour; another voice may differ. The add-on does not reclassify normative dictionary readings.

0.8.0 不再将“所有未被保护的懵”默认改成一声。只有已支持的口语“突然糊涂、发呆、不知所措”用法才选择一声。单字、字词提及、审定书面词或证据不足者保留原文。**保留不是新增二声规则**：用户声库原来读二声的未匹配项继续交给该声库；其他声音的读法可能不同。不改变词典规范字音，也不把“懵懂”等书面词统一改成二声。

“口语场景”指目标词的用法，不是整篇文章的文体：新闻报道中的“他被问懵了”仍可命中；聊天中讨论“懵的读音”仍须保留。不能因为句中某处命中就把同句所有“懵”一起替换。

## Linguistic evidence / 语言学依据

| Evidence | What it supports | What it does not establish |
|---|---|---|
| [杜永道，《人民日报海外版》，2019-03-02](https://paper.people.com.cn/rmrbhwb/html/2019-03/02/content_1911553.htm) | Distinguishes first-tone 蒙 for suddenly becoming confused, including state-change and 问/打 resultatives, from literary 懵 forms. / 区分突然糊涂的一声动词与书面词。 | It recommends spelling the verb 蒙, not changing every 懵 to first tone. / 不是全字默认一声的依据。 |
| [汉典：懵](https://www.zdic.net/hans/懵) and [MOE：懵裡懵懂](https://dict.revised.moe.edu.tw/dictView.jsp?ID=30616&la=0&powerMode=0) | Reviewed literary contrasts and preservation, including 懵懂、懵然、懵头转向. / 支持书面用法与保护。 | They do not prescribe the user's requested colloquial compatibility policy for every modern spelling. |
| [Universal Dependencies: Chinese resultative compounds](https://universaldependencies.org/zh/dep/compound-vv.html) | Resulting states can be adjective complements; potential 得/不 can intervene. / 动结式的结果成分可以是形容词，得／不用于可能式。 | Structural support only; it does not assign the tone of 懵. |
| [AllSet Learning: result complements](https://resources.allsetlearning.com/chinese/grammar/Result_complement), [degree complements](https://resources.allsetlearning.com/chinese/grammar/Degree_complement) | Productive verb + result state and adjective/state + complement structures. / 动结式与程度补语可组合，不必枚举完整句。 | Grammar alone is not a tone dictionary, nor permission to combine any verb with any result. |
| [Wenkai Tay: Mandarin V-V and V-de resultatives](https://taywenkai.com/mandarin-v-v-and-v-de-resultatives/) | Distinguishes compound resultatives from 得 resultative clauses. / 动结式和得字结果式分别分析。 | The bounded matcher does not implement the paper's complete syntactic theory. |
| [Pinned CC-CEDICT](../data/sources/cedict-20260907.txt.gz) | Records 懵圈 as `meng1`, but 懵逼 as `meng3`, and 发懵 with `meng3` plus Taiwan `meng2`. / 不同口语词的来源声调并不一致。 | Occurrence in a dictionary is not proof that all colloquial uses must be first tone. This project intentionally implements the requested compatibility choice, not a fabricated consensus. |
| [Pinned Unicode 17.0.0 Unihan](../data/sources/Unihan_Readings-17.0.0.txt.gz) | First-tone reading for the temporary renderer 擝 (U+64DD). | Character data does not certify synthesizer coverage or acoustics. |

The examples below and in [tests/meng_cases.py](../tests/meng_cases.py) are **constructed policy tests**, not a claimed natural corpus, quotations from these sources, or recordings. Complete sentences and most slot combinations are newly constructed. Source-backed distinctions motivate the families; the maintainer's requested oral compatibility policy supplies the first-tone expectation within those families.

以下及测试文件中的句子是**依据语法构造的策略用例**，不是伪称来源逐句收录的自然语料，也不是音频实测。语法来源支持分类，口语一声预期属于本项目明确约定的兼容策略。报道里的规范“蒙”例子也不冒充原文写作“懵”的语料。

## Positive families / 正向用法族

| Family / 构式 | Constructed examples / 用例 | Generalization / 泛化方式 |
|---|---|---|
| Colloquial words and facial state / 口语词、表情状态 | 一脸懵、一脸懵逼、懵圈、发懵、十二脸懵 | Lexical morphemes; numeral + 脸, including listed simplified/traditional and B spellings. Not every text starting with 比 or B. |
| State change and aspect / 状态变化与体 | 懵了、懵住、懵过、我突然懵掉了 | Recognize adjacent aspect/result markers without enumerating subjects. Avoid lexical tails such as 了解/了然/过敏. |
| Open degree/result complement / 程度、结果补语 | 懵得说不出话、懵到忘记回复、懵成表情包 | 得/到/成/在 followed by a nonempty local complement; new clause content need not be listed. |
| Duration / 时量 | 懵三秒、懵两分钟、懵半小时 | Bounded numeral slot and time-unit inventory; not an arbitrary following numeral. |
| Degree or temporal modifier / 程度、时间副词 | 有点懵、彻底懵、一下子懵、没有那么懵 | Recognized modifiers can attach to unfamiliar subjects and negated degree expressions. |
| Grounded state predicate and questions / 主语、否定与疑问 | 大家都懵、我也不懵、别懵、怎么会懵、懵吗 | Grounded human/pronominal subject or explicit question/imperative; no bare-character inference. |
| Resultative / 动结式与得字式 | 看懵、被老师问懵、把小名绕懵、说得我懵、问不懵 | Reviewed perception, cognitive, impact and overload verb classes; new agents/patients allowed. Bare 读懵/写懵/念懵 abstain because they can mention the character; 读懵了 and 读得懵 have additional evidence. |
| Comparison, coordination, reiteration / 比较、并列与复现 | 越想越懵、既懵又怕、懵不懵、懵归懵、懵来懵去、懵懵的 | Paired local grammatical markers; at most one peer, never recursive propagation through long runs. Bare 懵懵 is not sufficient. |
| State nominalization / 状态名词化 | 懵的表情、懵的状态、懵的时候 | Identifiable state descriptions; a naked 的 is insufficient and character-description tails stay original. |

Unfamiliar verbs can still be covered through independent overt state/complement evidence, for example “把所有人都量子纠缠懵了”. This does **not** license arbitrary unseen verb + 懵 compounds without evidence. Sentence-level words are not all enumerated, but lexical cues, windows and constructions remain finite.

## Preservation and contrasts / 保留与最小对立

| Preserve / 保留 | Match / 命中 |
|---|---|
| 懵；懵。；“懵”；懵、懵！ | 我懵了；一脸懵 |
| 懵懂；他很懵懂；懵然无知；懵于世事 | 他很懵；懵得说不出话 |
| 请问懵的拼音；请看懵这个字 | 被问懵；看懵了 |
| 读懵；输入懵；懵在字典中的解释 | 读得懵；懵在原地 |
| 懵懵；懵懵然；长串懵懵懵… | 懵懵的；你懵不懵 |
| 一脸。懵；懵 了；懵＋换行＋了 | 一脸懵；懵了 |
| 懵Benchmark；懵比例；张懵 | 懵B；我懵 |

Mixed example: `懵，一脸懵，懵懂，懵了` → temporary speech `懵，一脸擝，懵懂，擝了`. Each original character keeps its position. A known colloquial occurrence does not change isolated or literary neighbours.

## Runtime bounds and precedence / 运行时边界与优先级

The matcher in [colloquial_meng.py](../addon/globalPlugins/contextualPronunciation/colloquial_meng.py) uses windows of at most 24 code points on either side of an occurrence or a matched reiterative span (at most five code points). It uses fixed string inventories, bounded numeral/modifier loops and one-peer checks. Fixed cues and reiterations are indexed by their first/last adjacent character at import time; unrelated candidates are not scanned at every target. Protection checks are reused only within the same classification, with no retained utterance cache. There is no new runtime I/O, model, lexicon load, regex backtracking, unbounded sentence search or retained speech cache. With fixed configuration, matching is linear in input length; the existing lexicon/syntax engine retains its own independent limits.

The handler returns `meng1` only on positive evidence, otherwise `None`. Reviewed phrase protections take precedence in the existing resolver. User literal rules and user templates keep their pre-existing precedence; users can disable `colloquialMeng` or specify `keep`. It does not add a competing whole-character default rule or override a user's explicit instruction.

Evidence does not cross spaces, punctuation, controls or separate speech items. Complete phrases inside quotes can match internally, but an individually quoted 懵 does not borrow words outside the quotes. Spelling mode is untouched. Unknown names, unconventional spellings, ellipsis, distant dependencies and ambiguous unpunctuated text are not exhaustively understood. They may remain unchanged; use a personal rule rather than widening the default to every character.

前后窗口、词法线索与构式均有限；不可能仅凭有限局部文本可靠区分全部专名、文言用法与新造口语。目标是扩大有依据的覆盖，而不是为了召回率牺牲孤立字保护。窗口外、拆项后或歧义的输入可以弃权。静态盲文表仅增加相应书面保护，不编译动态口语规则。

## Tests and performance / 测试与性能

Run:

```powershell
python -m unittest tests.test_meng_contexts tests.test_colloquial_tones
python tools/evaluate_colloquial_meng.py
python tools/benchmark_colloquial_meng.py
```

Independent positive/negative/mixed cases and generated grammatical slots run under both default/extended engines with the unified automatic reading policy. Further tests cover literal/template precedence, disabling, original UTF-16 positions, spelling commands, split items, real NVDA symbol processing and bounded source slices. The evaluator deduplicates texts and reports its exact counts; a passing generated inventory is **not** an estimate of real-world accuracy.

The dedicated benchmark is a required regression-workflow stage. Short-input median budget: **200 microseconds**. Long-input median budget: **30 milliseconds**. Each case has at least 100 timed calls in both engine modes. It includes 8K bare runs, dense positives, mixed literary/colloquial text, lexical mentions and adversarial distant cues. Existing overall performance limits and immutable-baseline comparisons are not relaxed. Measurements exclude startup, actual synthesis and NVDA dispatch; artifacts record host and source hashes. Static bounds complement measured guardrails rather than promising every machine's latency.

## Listening acceptance / 人工试听验收

Install the 0.8.0 candidate and restart NVDA. With your normal Mandarin voice, compare:

```text
懵
懵。懵！“懵”
懵懂，懵然无知，懵头转向
请问懵的读音；请看懵这个字；输入懵
一脸懵，一脸懵逼，懵圈
被问懵了，懵得说不出话，越想越懵
懵，一脸懵，懵懂，懵了
```

The first four lines preserve the voice's existing readings. The colloquial positions in the last three lines should produce the requested first tone. Also navigate by character, check continuous reading, and compare with `colloquialMeng` disabled. Use a full text item for phrase checks; separately dispatched characters do not carry phrase context.

The temporary renderer 擝 must be recognized by the voice. Unknown-character announcements, omission or a different tone are failures, not successful acoustic verification. Automated assertions and probe inputs do not certify actual sound. Record the voice, driver/add-on versions and package hash. After listening acceptance and successful native CI for the exact main commit, use [Publish release from main](RELEASING.md). No release is automatically authorized by creating a candidate.

Performance recovery does not relax either budget: adjacent-character indexes replace repeated full-inventory scans. Character-description tails such as “请问懵的字形” and complete reiterations named as text (“请问懵不懵的读音”) are preservation cases, not weak resultative predicates.

The hot path also combines compatible preservation-prefix checks and dispatches end-delimited 越V越懵 directly. Independent linear-reference tests protect the temporal 之后/之後/之前 exception, and precedence tests keep B/ing/duration/complement evidence intact. No benchmark case, sample count or threshold is reduced.
