# User guide

[Project overview](../README.md) · English · [简体中文](USAGE-zh_CN.md)

This guide covers Context-aware Pronunciation 0.7.4. Install the `.nvda-addon` from [Releases](https://github.com/ChenZ2000/contextualPronunciation/releases/latest) and restart NVDA. The supported stable version is NVDA 2026.2; the project also tests 2026.3beta2 in CI.

## Start reading

Use your usual Mandarin voice and read normally. Default corrections apply automatically to supported text, including repeated actions such as 重吸收, serving phrases such as 也给我盛了一碗, and coordinated nouns such as 天兵和天将一起去吃饭. Spelling and character mode preserve the original characters.

All processing takes place on your computer. The add-on does not upload or record the text you read.

## Settings

Open **NVDA Settings → Context-aware pronunciation**. Changes take effect when you apply or save the settings. You can use NVDA configuration profiles to choose different settings for different tasks.

| Setting | Default | Effect |
|---|---|---|
| Enable contextual pronunciation rewriting | On | Enables text rewriting in the speech pipeline |
| Correct supported Chinese polyphones | On | Applies the supported Mandarin pronunciation rules |
| Use extended phrase lexicon | Off | Enables experimental dictionary-based coverage; some ambiguous phrases may be misread |
| Normalize curly apostrophes inside Latin words | On | Converts an in-word curly apostrophe to a straight apostrophe for speech, as in `doesn’t` |
| Strict mode | On | Keeps ambiguous text unchanged; turning it off currently also selects the literary yuè preference in 密钥、公钥、私钥 |

Start with the defaults. To try the extended lexicon, enable it and compare text you read regularly. For example, its boundary protection distinguishes 降调音频 (调 → diào) from 调音师 (调 → tiáo). Turn it off again if it introduces unwanted changes.

Chinese corrections specify Mandarin readings under every voice and language tag. Use a voice that supports Mandarin. For Cantonese, Japanese or other readings of Han characters, turn off Chinese corrections in the relevant profile.

## Add a personal pronunciation rule

Enter one rule per line in **Context templates**, then apply the settings. For example:

```text
仙[乐:yuè]
[盛:chéng]{number}{container}
```

The first line selects yuè for 乐 after 仙. The second selects chéng for 盛 before a recognized number and container expression. Tone marks and numbered pinyin are accepted, such as `yuè` and `yue4`.

To preserve the original character in a context, use `keep`:

```text
仙[乐:keep]
```

Use this as an alternative to the first pronunciation rule. It lets later processing, such as your NVDA speech dictionary, receive the original character. Each template targets one character; supported context placeholders and limits are documented in the [rule contribution guide](贡献规则与盲文接口.md) (Chinese).

The **Custom literal rules** field accepts the earlier `phrase|target|reading ID` format:

```text
仙乐|乐|yue4
盛汤|盛|keep
```

Reading IDs use numbered pinyin; `lv4` represents lǜ. A reading must have a supported homophone mapping. If NVDA reports an invalid rule, correct the indicated line before saving. **Disabled rule IDs** accepts existing rule IDs separated by commas or newlines; use it when investigating a specific built-in rule with a maintainer.

## Speech dictionaries and WorldVoice

The add-on first analyzes the speech text, then rechecks supported 和 / 边 / 邊 / 行 contexts after NVDA's dictionary and symbol processing. It sends temporary homophones to the synthesizer to express the selected readings. Speech Viewer may therefore show substitute characters; documents, clipboard contents and accessibility objects retain the original text.

WorldVoice 6.2 is covered by source-level integration tests in both language-detection modes. Its dictionary output can participate in pronunciation correction. Its Unicode replacement order follows the WorldVoice setting: **before** runs those replacements before this add-on; **after** may receive characters this add-on has already changed. A local `keep` rule can preserve text needed by a later replacement. These integration tests use voice substitutes; results with an actual voice should be checked by listening.

## Optional braille output

In NVDA's braille settings, select **Chinese common braille 2018 - contextual phrases (experimental)** as the output table. It extends the existing `zhcn-cbs.ctb` table with reviewed fixed contexts.

This table operates independently of speech settings. Custom speech templates, extended lexical decisions and dynamic sentence analysis do not automatically carry over to braille. The table covers a limited set of contexts. Expanding the word at the cursor to computer braille uses NVDA's normal behavior and bypasses those context rules. To revert, select your previous output table.

## Troubleshooting

| Symptom | What to check |
|---|---|
| A supported phrase still sounds wrong | Confirm that rewriting and Chinese corrections are enabled, then check the same full sentence with the extended lexicon off. Record the voice and versions when reporting it. |
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
