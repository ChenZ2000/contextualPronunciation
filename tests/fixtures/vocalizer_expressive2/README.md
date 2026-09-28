# Vocalizer Expressive 2.2 只读回归探针

这里的 fixture 用来验证插件的“读音判定”和“合成器 renderer”是两件独立的事。规则层先判定目标拼音，例如 `盛汤 → cheng2`；renderer 再为当前 voice 选择能稳定发出该音的临时同音字，例如 `成` 或 `乘`。临时文本不会改写文档、剪贴板、盲文或可访问性对象。需要特别说明的是：NVDA 2026.2 的 Speech Viewer 和“重复最后朗读内容”位于公开 `filter_speechSequence` 之后，因此会看见临时同音字；这是公开 Filter 方案的可观察限制，不能宣称它们仍显示原字。

## 安全边界

[`tools/probe_vocalizer_expressive2.py`](../../../tools/probe_vocalizer_expressive2.py) 有三个模式：

- `static` 只读 manifest 和 Python 源码，不加载厂商 DLL；
- `inventory` 在独立 Python 进程加载 Vocalizer DLL，只枚举语言、voice 和版本；
- `render` 在独立进程中直接接收 Vocalizer PCM 回调并写入 WAV，不创建 `nvwave.WavePlayer`，不会抢占 NVDA 的输出设备。

脚本不会安装插件、修改 NVDA 配置、写入 NVDA 或已有插件目录，也不会播放声音。`render` 仅在指定的输出目录创建 WAV 和 JSON。如果厂商 DLL 不支持与正在运行的 NVDA 并发初始化，helper 只会失败退出；不要为运行它而重启 NVDA，也不要复制、修改或重新分发声库文件。

## 使用方法

在仓库根目录运行：

```powershell
python tools/probe_vocalizer_expressive2.py static --report artifacts/vocalizer-static.json
python tools/probe_vocalizer_expressive2.py inventory --report artifacts/vocalizer-inventory.json
python tools/probe_vocalizer_expressive2.py render `
  --voice Ting-Ting `
  --fixture tests/fixtures/vocalizer_expressive2/renderer_cases.json `
  --output-dir artifacts/vocalizer-expressive2-ting-ting
```

`render` 生成每条语料的 WAV、PCM SHA-256、时长、全部 Vocalizer marker，以及按三种可能坐标单位抽取的目标字符音素 marker。`targetMarkerComparisons` 会指出候选是否与同组 anchor 返回完全相同的私有音素 ID。

这些数字不是 IPA，也不能跨 Vocalizer 版本、voice、声库质量或 operating point 比较。选择 renderer 时必须同时满足：

1. 同一次运行中的目标音素 marker 与正确 anchor 相符；
2. 人工听取整个 WAV，目标声调、相邻字连读和停顿都正确；
3. 对插件实际会命中的句子重复验证，而不只听孤立字；
4. 在 Ting-Ting 之外，对用户启用的普通话 voice 分别建 profile；
5. 声库或驱动版本变化后重新标定，不沿用旧结论。

## 当前驱动中已确认的行为

当前安装的 `vocalizer_expressive2_driver` 2026.6.6 有以下行为，静态探针会再次从源码核对：

- `supportedCommands` 没有声明 `PhonemeCommand`；
- `speak()` 虽有 `PhonemeCommand` 分支，却只朗读它的 fallback `text`，不使用 IPA；
- 每个字符串块会先 `strip()`；
- 两个文本块之间会插入 NVDA 的 `CHUNK_SEPARATOR`；
- 普通字符串中的 ESC 会被删除，不能从通用插件偷偷注入 Vocalizer 原生命令；
- 低层回调能产生 22,050 Hz、单声道、16-bit PCM，并暴露 text-unit、word、phoneme 和 bookmark marker；
- 驱动有按 voice 加载私有 `.rules` / `.dcb` tuning 数据的代码，但这是可选的 Vocalizer 专用适配面，不是跨语音引擎方案。

因此，通用插件不应发送 `PhonemeCommand` 或原生 ESC/SSML。默认 renderer 应使用经当前 voice 声学校准的同音字；未来只有在特定驱动明确声明并真正实现公开音素能力时，才启用专用 adapter。

## “盛开 / 盛汤”的语言学断言

- `盛开` 的“盛”读 `shèng`，不是待修正项；它必须作为 `chéng` 规则的保护性反例。
- `盛汤、盛饭、盛粥、盛一碗` 中表示把食物装入器皿的动词“盛”读 `chéng`。

fixture 同时收录 `成 / 乘`、`航 / 杭`、`崇 / 虫` 候选。候选字词在语义上可能很怪，所以必须检查整句韵律；不能仅因为孤立目标音素相同就自动选定。

## 口语“懵”的一声回归

`renderer_cases.json` 新增 `meng1_colloquial_*` 组，覆盖“一脸懵逼、一脸懵、懵了、懵圈、看懵了、懵得说不出话”及新语境。每组并列原文、当前“擝”替代输出和旧版“蒙”替代输出。使用上面的 `render` 命令生成当前目标声库的 WAV；这些条目只是待渲染输入，不是已有试听结果。

这一组不把“蒙”“矇”或尚未试听的“擝”标为 `anchor`，因此不会因自身比较相等而产生“一声已通过”的假结论。必须确认整个词的目标音确实为一声；二声、三声、读字母、未知字符提示、漏字均不是通过。“擝”是生僻字，固定 Unihan 的一声证据不能证明声库支持它。未支持的声音可停用 `colloquialMeng` 保留原文，不应静默退回已知多音的“蒙”。

The `meng1_colloquial_*` cases compare original text, the current 擝 renderer and the old 蒙 renderer. They are listening-probe inputs, not recorded results. No first-tone acoustic anchor is assumed. Verify the target tone and complete word on the actual voice; an unknown/omitted character or a different tone is not a pass. The pinned Unicode reading does not certify voice coverage.
