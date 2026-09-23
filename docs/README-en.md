# Context-aware Pronunciation 0.7.4: user guide

Requires NVDA 2026.2. Download the `.nvda-addon` from [Releases](https://github.com/ChenZ2000/contextualPronunciation/releases/latest), install it, and restart NVDA when prompted. The stable manifest declares 2026.2; 2026.3beta2 is separately exercised in development tests.

## Settings

Open NVDA Settings → Context-aware pronunciation. Keep contextual rewriting, Chinese polyphone corrections and strict mode enabled for the reviewed default rules. The extended phrase lexicon is experimental and off by default; it can improve coverage but can also misinterpret ambiguous text.

Supported structures include repeated actions such as 重转, quantified objects such as 盛了一碗饭, coordinated military nouns such as 天兵和天将一起去吃饭, spatial nouns such as 下边缘, coordinated actions such as 唱和说, and row counts such as 多行文本. Existing lexical protections and explicit user `keep` decisions take precedence where applicable.

Local templates are entered one per line:

```text
仙[乐:yuè]
[盛:chéng]{number}{container}
仙[乐:keep]
```

The last line illustrates an alternative preservation rule; it need not be entered with the first. Both tone marks and numbered pinyin are accepted. The template language is bounded and does not execute Python or arbitrary regular expressions. The earlier `phrase|character|readingId` format is also supported. See the [contribution guide](../CONTRIBUTING.md).

## Speech pipeline and voices

The public `filter_speechSequence` extension analyzes original speech items. The public `pre_speechQueued` event rechecks residual 和, 边, 邊 and 行 after NVDA's dictionary and symbol processing. Selected readings are rendered as temporary homophones. Separate strings or inserted spaces are not treated as universally enforceable synthesizer token boundaries.

Commands retain their identity, spelling mode is preserved, and context does not cross commands. Source documents and clipboard text are unchanged; Speech Viewer can show the temporary homophones. Runtime errors preserve the original speech sequence and use a bounded generic log message without the text being read.

Mandarin rules apply to Han characters under every voice and language tag, including Japanese or Cantonese configurations. They cannot add Mandarin capability to a voice. Turn off Chinese corrections or use a separate NVDA profile if that behavior is inappropriate.

WorldVoice 6.2 is checked using its pinned real pipeline with isolated voice substitutes, in both language-detection modes. Its later Unicode rules may receive characters already rewritten by this add-on. Use a local `keep` rule when another add-on must receive the original characters. No private WorldVoice methods or installed files are patched.

## Apostrophes and disabling

The mandatory symbol dictionary preserves in-word apostrophes in forms such as Doesn't, Doesn’t, Mike's and Mike’s. Turning off contextual rewriting does not remove that installed dictionary. To remove all add-on behavior, disable or uninstall the add-on and restart NVDA. Early word-echo segmentation is outside the verified apostrophe scope.

## Optional braille table

You can manually choose **Chinese common braille 2018 - contextual phrases (experimental)** as the output table. It includes NVDA's existing `zhcn-cbs.ctb` and adds reviewed finite contexts. It never inserts speech homophones into braille. Dynamic parsing, numeric structures, extended lexical decisions and custom speech templates do not automatically synchronize with this static table. Computer-braille expansion at the cursor intentionally bypasses contextual rules. Select the original output table to revert.

## Privacy, limitations and feedback

Runtime processing is offline and does not record spoken text, upload content or query a service. Rules use bounded symbolic parsing and attributed lexical evidence, not a neural language model. Unknown and ambiguous text can remain unchanged, and no exhaustive Chinese accuracy or zero-latency guarantee is made.

There are 1,154 targeted grammar regression cases plus integration tests. Audio checks on one synthesizer do not certify others, and PCM differences can reflect prosody. Please report an anonymous reproducible sentence, the expected reading, the actual reading, NVDA/add-on/voice versions and relevant settings in [Issues](https://github.com/ChenZ2000/contextualPronunciation/issues).

Code is GPL-2.0-or-later. Data retains the licenses in the [third-party notices](../addon/THIRD-PARTY-NOTICES.txt). See [the project README](../README.md) for building and development.
