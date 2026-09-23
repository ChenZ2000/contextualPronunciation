"""Manually specified reading/position oracles, independent of the importer.

Values identify only speech substitutions; unchanged defaults and unsupported
readings are NOT counted as validated corrections. Anchors are separate from
the production rendering map.
"""

LEXICON_CASES = (
	("仙乐飘飘", {1: ("yue4", "越")}),
	("音乐观众很快乐", {1: ("yue4", "越")}),
	("乐观的音乐家", {4: ("yue4", "越")}),
	("我们正在欣赏乐曲", {6: ("yue4", "越"), 7: ("qu3", "取")}),
	("礼乐文明", {1: ("yue4", "越")}),
	("管弦乐", {2: ("yue4", "越")}),
	("单于来了", {0: ("chan2", "蝉")}),
	("躯壳", {1: ("qiao4", "俏")}),
	("龟裂", {0: ("jun1", "君")}),
	("薄荷", {0: ("bo4", "薄")}),
	("脉脉含情", {0: ("mo4", "墨"), 1: ("mo4", "墨")}),
	("数落", {0: ("shu3", "鼠")}),
	("处理数据", {0: ("chu3", "楚")}),
	("调试程序", {0: ("tiao2", "条")}),
	("看守大门", {0: ("kan1", "刊")}),
	("长久以来", {0: ("chang2", "常")}),
	("假期结束", {0: ("jia4", "架")}),
	("强迫", {0: ("qiang3", "抢")}),
	("角色扮演", {0: ("jue2", "决")}),
	("仙乐飘飘之后再盛汤", {1: ("yue4", "越"), 7: ("cheng2", "乘")}),
)


def expected_text(source: str, positions: dict, renderings: dict) -> str:
	result = list(source)
	for position, (reading, _anchor) in positions.items():
		result[position] = renderings[reading]
	return "".join(result)


# Source homographs, named entities, particles, unsupported anchors, defaults,
# and incomplete context must not be converted into confident reading claims.
UNCHANGED_CASES = (
	"便宜",
	"同行",
	"朝阳",
	"乐高",
	"乐观",
	"快乐",
	"长大",
	"头发很长",
	"睡着",
	"着火",
	"了不起",
	"的确",
	"参差不齐",
	"仙",
	"乐",
	"未知词龘龘",
)
