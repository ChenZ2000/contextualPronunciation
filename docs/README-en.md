# User guide

[Project overview](../README.md) · English · [简体中文](USAGE-zh_CN.md)

This guide covers version 0.8.3; test builds may precede a public Release. Download the add-on from [GitHub Releases](https://github.com/ChenZ2000/contextualPronunciation/releases/latest). Install a `.nvda-addon` and restart NVDA. The supported stable version is NVDA 2026.2; the project also tests 2026.3beta2 in CI.

## Start reading

Use your usual Mandarin voice and read normally. Default corrections apply automatically to supported text, including repeated actions such as 重吸收, serving phrases such as 也给我盛了一碗, and coordinated nouns such as 天兵和天将一起去吃饭. Spelling and character mode preserve the original characters.

All processing takes place on your computer. The add-on does not upload or record the text you read.

Version 0.8.1 keeps lè in 快乐/快樂 whether a sentence mark follows or not.
Body locations and growth expressions such as 身上长、背上长了、胸前长了、
长个子了、各自长了, and the honor idiom 给我长脸了/长脸了 select zhǎng.
Length and face-shape descriptions such as 头发很长、绳子长三米、一张长脸
select cháng. In 头发长长了 the two syllables are zhǎng then cháng; ambiguous
头发长了 retains your voice's original interpretation.

Version 0.8.2 also recognizes clipped stature 个 in 长个/长个了, questions,
negation, potential complements and new quantified objects. It uses the actual
head: 菖蒲长了 selects growth, while 菖蒲的照片长了 selects the photograph's
length. Result quantity in 长胖一点 does not masquerade as a noun object.
Age comparisons such as 长我两岁/他比我长三岁 select zhǎng; duration in
寿命比我长三年 retains the length sense.

Version 0.8.3 distinguishes the stature noun in 长个/长个了 (gè, fourth
tone, without an added 儿) from the neutral classifier in 长个东西. The latter
selects zhǎng through the actual classifier/object structure, also with new
heads, modifiers, quantities and locations such as 树上长个奇怪的东西.
Short words with independently resolved neutral readings retain their complete
spelling, including 数落、亲家、朋友、麻烦、妈妈、桌子, so a homophone rewrite
does not break the voice's lexical entry. Homographs, unknown words and suffixes
alone do not establish neutral tone. Actual neutral pronunciation still depends
on the voice; personal rules, disabled rules and spelling mode remain effective.

## Colloquial 懵: context required

Version 0.8.0 removes the old unconditional `meng1` fallback. The add-on uses first-tone `mēng` only with positive evidence for the colloquial confusion sense: 一脸懵 / 懵圈, 我懵了, 看懵 / 被问懵, 有点懵, 懵得说不出话, 越想越懵 and similar grammatical combinations. New subjects, objects and complement clauses do not need complete phrases added individually.

An isolated 懵 (also 懵。 or “懵”), 懵懂 / 懵然, and lexical mentions such as 懵的读音 or 输入懵 keep the original characters. Preservation means keeping the voice's existing reading, **not** globally forcing second tone or changing normative dictionary readings. Spelling mode and text split into separate speech items do not borrow neighbouring context.

Matched speech still temporarily uses 擝 (U+64DD), whose pinned Unihan reading is first tone. Actual recognition of this rare character depends on your voice; it can appear in Speech Viewer but does not change your document. Test both positive and negative examples with your normal voice. Disable `colloquialMeng` to preserve all affected colloquial forms, or apply a local `keep` rule. Explicit personal rules retain precedence.

The matcher is bounded and conservative, not an exhaustive semantic classifier. Ambiguous names, unfamiliar constructions, formatting boundaries and very long dependencies can be left unchanged. See [linguistic evidence and acceptance examples](COLLOQUIAL_MENG.md). The static braille table does not run this dynamic speech rule.

## Settings

Open **NVDA Settings → Context-aware pronunciation**. Changes take effect when you apply or save the settings. You can use NVDA configuration profiles to choose different settings for different tasks.

| Setting | Default | Effect |
|---|---|---|
| Enable contextual pronunciation rewriting | On | Enables text rewriting in the speech pipeline |
| Correct supported Chinese polyphones | On | Applies the supported Mandarin pronunciation rules |
| Normalize curly apostrophes inside Latin words | On | Converts an in-word curly apostrophe to a straight apostrophe for speech, as in `doesn’t` |

Readings use one automatic policy based on lexical senses, actual argument heads
and complements. Strict mode has been removed; old profile values are ignored
without needing to recreate the profile. Unsupported ambiguity keeps the source
character. Attested key-reading variants in 密钥/公钥/私钥 are preserved rather
than forcing yuè; personal reading rules remain available.

The dictionary lexicon and bounded grammar are active whenever Chinese corrections are enabled. The retired extended-lexicon setting no longer gates them. Boundary protection distinguishes 降调音频 (调 → diào) from 调音师 (调 → tiáo). Use a local `keep` rule for a specific unwanted correction.

Chinese corrections specify Mandarin readings under every voice and language tag. Use a voice that supports Mandarin. For Cantonese, Japanese or other readings of Han characters, turn off Chinese corrections in the relevant profile.

## Custom context templates

All three custom-rule fields support multiple lines. Press **Enter** or numeric-keypad Enter to insert a line break, or paste multiple lines. **Tab** moves to the next control and **Ctrl+S** applies settings. Enter inside these fields does not close the settings dialog.

Use **Context templates** for a reading tied to surrounding text. Enter one template per line in the form `left context[target:pinyin]right context`. The target is one character; provide context on at least one side. Use ordinary text for a literal match or a supported placeholder for a class of text.

```text
仙[乐:yuè]
[盛:chéng]{number}{container}
```

- `仙[乐:yuè]` makes 乐 read yuè after 仙, including within a sentence such as 仙乐飘飘. `仙[乐:yue4]` is equivalent.
- `[盛:chéng]{number}{container}` selects chéng before a number and a listed container, as in 盛一碗 or 盛两杯. `{number}` matches up to 12 Chinese or Arabic numeral characters; `{container}` matches built-in entries such as 碗、杯、勺、盆.
- `{space}` allows zero to four supported spaces. For example, `[盛:chéng]{number}{space}{container}` also covers 盛一 碗. Other available classes are listed in the [rule data](../addon/globalPlugins/contextualPronunciation/data/contributions.toml).

To preserve a character for the synthesizer or a later NVDA speech-dictionary rule, replace the reading with `keep`:

```text
仙[乐:keep]
```

Choose this preservation rule instead of the yuè rule for the same context. Each template contains one target. Use half-width `[]`, `:`, and `{}` as shown. Pinyin can use tone marks or tone numbers; ü can be entered as `v`, for example `lǜ` or `lv4`. Available readings are limited to the add-on's supported homophone mappings. Conflicting custom templates of equal priority preserve the original character.

## Custom literal rules

Use **Custom literal rules** when you want to specify an exact phrase. Enter one line per phrase, separating the three fields with the half-width pipe character `|`:

```text
仙乐|乐|yue4
盛汤|盛|keep
```

The fields are **phrase | target character | reading ID or keep**. The first line selects yuè for 乐 in 仙乐; the second preserves 盛 in 盛汤. Reading IDs use numbered pinyin, such as `yue4`, `chang2` and `lv4`. A phrase must contain 2–64 characters, with the target appearing exactly once. Enter each phrase/target pair once.

If a custom literal rule and a custom template both match the same position, the literal rule takes priority. Usually one format is enough for a particular correction.

## Disable a rule or restore your settings

**Disabled rule IDs** accepts built-in rule identifiers separated by commas or newlines. For example, `rowIndefiniteQuantity` disables the rule for indefinite row counts such as 多行. IDs are recorded in the [core rules](../addon/globalPlugins/contextualPronunciation/data/rules_zh_CN.json) and [syntax frames](../addon/globalPlugins/contextualPronunciation/data/syntax_frames.toml), and a maintainer can identify one when troubleshooting. An unrecognized ID produces an error when you save. Other matching rules may still affect the same character; use a local `keep` rule to preserve a specific phrase.

To undo a personal rule or re-enable a disabled rule, remove its line or ID and click **Apply**. To return to the defaults in the current profile, clear all three text fields and turn all four checkboxes on. If a rule is rejected, correct the field indicated by the error before saving.

## Speech dictionaries and WorldVoice

The add-on first analyzes the speech text, then rechecks supported 和 / 边 / 邊 / 行 contexts after NVDA's dictionary and symbol processing. It sends temporary homophones to the synthesizer to express the selected readings. Speech Viewer may therefore show substitute characters; documents, clipboard contents and accessibility objects retain the original text.

WorldVoice 6.2 is covered by source-level integration tests in both language-detection modes. Its dictionary output can participate in pronunciation correction. Its Unicode replacement order follows the WorldVoice setting: **before** runs those replacements before this add-on; **after** may receive characters this add-on has already changed. A local `keep` rule can preserve text needed by a later replacement. These integration tests use voice substitutes; results with an actual voice should be checked by listening.

## Optional braille output

In NVDA's braille settings, select **Chinese common braille 2018 - contextual phrases (experimental)** as the output table. It extends the existing `zhcn-cbs.ctb` table with reviewed fixed contexts.

This table operates independently of speech settings. Custom speech templates, lexical decisions and dynamic sentence analysis do not automatically carry over to braille. The table covers a limited set of contexts. Expanding the word at the cursor to computer braille uses NVDA's normal behavior and bypasses those context rules. To revert, select your previous output table.

## Troubleshooting

| Symptom | What to check |
|---|---|
| A supported phrase still sounds wrong | Confirm that rewriting and Chinese corrections are enabled, then check the same full sentence. Record the voice and versions when reporting it. |
| A Cantonese or Japanese reading changes | Turn off Chinese corrections in that language's NVDA profile. |
| Speech Viewer shows different characters | This is the temporary pronunciation text sent to the voice. Check the document itself to see the original characters. |
| A custom rule cannot be saved | Check the target character, pinyin and field format. Correct the line named by the error. |
| Turning off rewriting still preserves apostrophes | The installed mandatory symbol dictionary remains active. Disable or uninstall the add-on and restart NVDA to remove it. |
| Apostrophes sound different in typed-word echo | Report the typing sequence as well as the word; early echo segmentation has a separate processing path. |

Unknown words, ambiguous sentences and text split across speech commands may retain the synthesizer's own reading. Voice-specific behavior can also affect the final audio.

## Report a pronunciation problem

Open [an issue](https://github.com/ChenZ2000/contextualPronunciation/issues) with:

- A complete, anonymized sentence and the target character.
- Expected pinyin with tone and the actual reading you hear.
- NVDA version, add-on version, synthesizer and voice.
- Relevant settings, custom rules and other speech add-ons.
- A contrasting sentence with a different intended reading, when available.

For example: `也给我盛了一碗 — 盛 should be chéng; I hear shèng.` Complete context helps maintainers reproduce the structural decision. See [Contributing](../CONTRIBUTING.md) for development, and [Sources and references](REFERENCES.md#english) for dictionary provenance.
