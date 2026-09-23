"""Generate the final Vocalizer renderer regression fixture from live rules.

This helper imports only the NVDA-independent rule engine.  It does not load
NVDA, Vocalizer, an audio device, or any user configuration.
"""

from __future__ import annotations

import hashlib
import json
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
RULE_ENGINE_PATH = ROOT / "addon/globalPlugins/contextualPronunciation/rules.py"
RULE_DATA_PATH = ROOT / "addon/globalPlugins/contextualPronunciation/data/rules_zh_CN.json"
OUTPUT_PATH = ROOT / "tests/fixtures/vocalizer_expressive2/final_renderer_regression.json"


@dataclass(frozen=True, slots=True)
class Scenario:
	id: str
	tier: str
	character: str
	source: str
	alternate_anchor: str
	expected_reading: str
	rule_kind: str
	strict: bool = True
	extended: bool = False


SCENARIOS = (
	Scenario("bian1_lower_edge", "P0", "边", "下边缘", "鞭", "biān", "syntax-spatial-edge"),
	Scenario("bian1_upper_frame", "P0", "边", "上边框", "鞭", "biān", "syntax-spatial-edge"),
	Scenario("he2_coordinated_verbs", "P0", "和", "唱和说", "盒", "hé", "syntax-coordinated-predicates"),
	Scenario("he2_coordinated_actions", "P0", "和", "唱和跳", "盒", "hé", "syntax-coordinated-predicates"),
	Scenario("hang2_multirow", "P0", "行", "多行", "杭", "háng", "structural:rowIndefiniteQuantity"),
	Scenario("hang2_multirow_input", "P0", "行", "多行输入框", "杭", "háng", "structural:rowIndefiniteQuantity"),
	Scenario("hang2_row_head", "P0", "行", "行首位置", "杭", "háng", "phrase"),
	Scenario("hang2_row_ordinal", "P0", "行", "当前是第十二行", "杭", "háng", "structural:rowOrdinal"),
	Scenario("chong2_repeat", "P0", "重", "请重复一次", "虫", "chóng", "phrase"),
	Scenario("chong2_productive_transfer", "P0", "重", "请把文件重转一次", "虫", "chóng", "syntax-repeat-predicate"),
	Scenario("chong2_productive_compile", "P0", "重", "请重编译", "虫", "chóng", "syntax-repeat-predicate"),
	Scenario("chong2_productive_compress", "P0", "重", "请重压缩", "虫", "chóng", "syntax-repeat-predicate"),
	Scenario("chong2_reabsorb", "P0", "重", "重吸收", "虫", "chóng", "syntax-repeat-predicate"),
	Scenario("chong2_reshape", "P0", "重", "重捏", "虫", "chóng", "syntax-repeat-predicate"),
	Scenario("chong2_refly", "P0", "重", "重飞", "虫", "chóng", "syntax-repeat-predicate"),
	Scenario("cheng2_aspect_quantity", "P0", "盛", "盛了一碗饭", "乘", "chéng", "syntax-serving-object"),
	Scenario("cheng2_modified_quantity", "P0", "盛", "盛了一大碗刚煮好的饭", "乘", "chéng", "syntax-serving-object"),
	Scenario("jiang4_crab_conjunct", "P0", "将", "虾兵和蟹将", "酱", "jiàng", "syntax-general-nominal"),
	Scenario("jiang4_celestial_conjunct", "P0", "将", "天兵和天将", "酱", "jiàng", "syntax-general-nominal"),
	Scenario("jiang4_reverse_conjunct", "P0", "将", "蟹将和虾兵", "酱", "jiàng", "syntax-general-nominal"),
	Scenario("jiang4_classified", "P0", "将", "一员勇猛的将", "酱", "jiàng", "syntax-general-nominal"),
	Scenario("cheng2_elliptical_object", "P0", "盛", "也给我盛了一碗", "乘", "chéng", "syntax-serving-object"),
	Scenario(
		"cheng2_elliptical_continuation", "P0", "盛", "盛好了两大碗就回去了", "乘", "chéng", "syntax-serving-object"
	),
	Scenario("jiang4_coordinated_subject", "P0", "将", "天兵和天将一起去吃饭", "酱", "jiàng", "syntax-general-nominal"),
	Scenario("jiang4_reverse_subject", "P0", "将", "蟹将和虾兵一起去吃饭", "酱", "jiàng", "syntax-general-nominal"),
	Scenario(
		"jiang4_modal_overlap", "P0", "将", "天兵和天将要去吃饭", "酱", "jiàng", "syntax-general-nominal", extended=True
	),
	Scenario(
		"jiang4_modified_subject",
		"P0",
		"将",
		"身经百战的将和那些训练有素的士兵一起去吃饭",
		"酱",
		"jiàng",
		"syntax-general-nominal",
	),
	Scenario(
		"cheng2_coordinated_object",
		"P0",
		"盛",
		"盛那碗刚刚煮好而且非常香甜的红豆粥",
		"乘",
		"chéng",
		"syntax-serving-object",
	),
	Scenario(
		"cheng2_preposed_object", "P0", "盛", "把刚刚煮好的红豆粥盛进碗里", "乘", "chéng", "syntax-serving-object"
	),
	Scenario(
		"liang2_nested_clause",
		"P0",
		"量",
		"量住在那条非常安静的街道旁边的小名的身高",
		"良",
		"liáng",
		"syntax-measurement-object",
	),
	Scenario(
		"ji4_coordinated_adjectives", "P0", "系", "系那条又细又长的红色丝带", "季", "jì", "syntax-fastening-object"
	),
	Scenario("cheng2_serve_soup", "P0", "盛", "请给客人盛汤", "乘", "chéng", "phrase"),
	Scenario(
		"cheng2_serve_quantity",
		"P0",
		"盛",
		"我来盛一碗饭",
		"乘",
		"chéng",
		"structural:servingQuantity",
	),
	Scenario("bing3_hold_breath", "P1", "屏", "请屏住呼吸", "饼", "bǐng", "phrase"),
	Scenario("tan2_popup", "P1", "弹", "关闭弹窗", "坛", "tán", "phrase"),
	Scenario("yue4_secret_key", "optional", "钥", "读取密钥文件", "越", "yuè", "preference", strict=False),
	Scenario("hang2_spaced_label", "P0", "行", "行 12", "杭", "háng", "structural:rowLabel"),
	Scenario("hang2_spaced_count", "P0", "行", "12 行 8 列", "杭", "háng", "structural:rowColumnCount"),
	Scenario("cheng2_half_bowl", "P0", "盛", "盛半碗饭", "乘", "chéng", "structural:servingQuantity"),
	Scenario("yue4_celestial_music", "P1", "乐", "仙乐飘飘", "越", "yuè", "template:yue-music-prefix"),
	Scenario("yue4_music_audience", "P1", "乐", "音乐观众很多", "越", "yuè", "template:yue-music-prefix"),
	Scenario("yue4_orchestra", "P1", "乐", "管弦乐演奏", "越", "yuè", "template:yue-music-prefix"),
	Scenario("yue4_vocal_music", "P1", "乐", "声乐练习", "越", "yuè", "template:yue-music-prefix"),
	Scenario("hang2_indefinite_rows", "P0", "行", "这几行很好", "杭", "háng", "structural:rowIndefiniteQuantity"),
	Scenario("hang2_teen_rows", "P0", "行", "十几行写在这里", "杭", "háng", "structural:rowIndefiniteQuantity"),
	Scenario("hang2_how_many_rows", "P0", "行", "表格有多少行", "杭", "háng", "structural:rowIndefiniteQuantity"),
	Scenario("hang2_vertical_rows", "P0", "行", "文字排成竖行", "杭", "háng", "phrase"),
	Scenario("bing3_hold_silent_breath", "P1", "屏", "孩子屏息等待", "饼", "bǐng", "phrase"),
	Scenario("tan2_play_piano", "P1", "弹", "她正在弹琴", "坛", "tán", "phrase"),
	Scenario("tan2_spring", "P1", "弹", "这根弹簧很长", "坛", "tán", "phrase"),
	Scenario("hang2_row_not_feasible", "P0", "行", "这几行不行", "杭", "háng", "structural:rowIndefiniteQuantity"),
	Scenario("ji4_shoelace", "P0", "系", "我给孩子系鞋带", "季", "jì", "template:ji-fasten-object"),
	Scenario("ji4_seatbelt", "P0", "系", "请系好安全带", "季", "jì", "template:ji-fasten-result-object"),
	Scenario("ji4_object_first", "P0", "系", "请把鞋带系上", "季", "jì", "template:ji-object-before-verb"),
	Scenario("liang2_temperature", "P0", "量", "我给孩子量体温", "良", "liáng", "template:liang-measure-object"),
	Scenario("liang2_measure", "P0", "量", "请测量尺寸", "良", "liáng", "template:liang-measure-verb"),
	Scenario("liang2_blood_pressure", "P0", "量", "量一下血压", "良", "liáng", "template:liang-measure-result-object"),
	Scenario("ji4_bow_tie", "P0", "系", "请系领结", "季", "jì", "template:ji-fasten-object"),
	Scenario("ji4_rope", "P0", "系", "我来系绳子", "季", "jì", "template:ji-fasten-object"),
	Scenario("ji4_red_scarf", "P0", "系", "孩子系红领巾", "季", "jì", "template:ji-fasten-object"),
	Scenario("ji4_quantity", "P0", "系", "他系了一条领带", "季", "jì", "template:ji-fasten-result-quantity-object"),
	Scenario("ji4_knot", "P0", "系", "请系个活扣", "季", "jì", "template:ji-fasten-knot"),
	Scenario("ji4_location", "P0", "系", "把绳子系在树上", "季", "jì", "template:ji-fastener-location"),
	Scenario("liang2_length", "P0", "量", "用尺子量长度", "良", "liáng", "template:liang-measure-object"),
	Scenario("liang2_height", "P0", "量", "孩子量身高", "良", "liáng", "template:liang-measure-object"),
	Scenario("liang2_diameter", "P0", "量", "请量直径", "良", "liáng", "template:liang-measure-object"),
	Scenario("liang2_tool", "P0", "量", "用卷尺仔细量一下", "良", "liáng", "template:liang-physical-tool-method"),
	Scenario("liang2_object_first", "P0", "量", "身高量了两次", "良", "liáng", "template:liang-object-before-verb"),
	Scenario("liang2_owned", "P0", "量", "量孩子的身高", "良", "liáng", "template:liang-owned-measurement"),
	Scenario("liang2_unit", "P0", "量", "量三米布", "良", "liáng", "template:liang-physical-quantity"),
	Scenario("liang2_instrument", "P0", "量", "这是量杯", "良", "liáng", "template:liang-measuring-instrument"),
	Scenario("cheng2_bean_object", "P0", "盛", "请盛豆角", "乘", "chéng", "syntax-serving-object"),
	Scenario("cheng2_compound_food", "P0", "盛", "盛红豆粥", "乘", "chéng", "syntax-serving-object"),
	Scenario("cheng2_relative_food", "P0", "盛", "盛刚煮好的红豆粥", "乘", "chéng", "syntax-serving-object"),
	Scenario("cheng2_liquid", "P0", "盛", "盛液体", "乘", "chéng", "syntax-serving-object"),
	Scenario("cheng2_load_liquid", "P0", "盛", "盛装液体", "乘", "chéng", "syntax-serving-object"),
	Scenario("cheng2_liquid_container", "P0", "盛", "盛装液体的容器", "乘", "chéng", "syntax-serving-object"),
	Scenario("cheng2_liquid_quantity", "P0", "盛", "盛了半瓶透明液体", "乘", "chéng", "syntax-serving-object"),
	Scenario("cheng2_loaded_liquid", "P0", "盛", "盛装的液体", "乘", "chéng", "syntax-serving-object"),
	Scenario("cheng2_decorations", "P0", "盛", "盛装饰品", "乘", "chéng", "syntax-serving-object"),
	Scenario("cheng2_experienced_gas", "P0", "盛", "盛过气体", "乘", "chéng", "syntax-serving-object"),
	Scenario("cheng2_edible", "P0", "盛", "盛装食物", "乘", "chéng", "syntax-serving-object"),
	Scenario("liang2_unknown_owner", "P0", "量", "量小名的身高", "良", "liáng", "syntax-measurement-object"),
	Scenario("liang2_relative_owner", "P0", "量", "量住在隔壁的小名的身高", "良", "liáng", "syntax-measurement-object"),
	Scenario("ji4_owned_fastener", "P0", "系", "系小名的鞋带", "季", "jì", "syntax-fastening-object"),
	Scenario("diao4_lowered_audio", "P0", "调", "降调音频", "掉", "diào", "crossing-reading-lock", extended=True),
	Scenario("diao4_raised_audio", "P0", "调", "升调音频", "掉", "diào", "crossing-reading-lock", extended=True),
	Scenario("tiao2_audio_engineer", "P0", "调", "调音师", "迢", "tiáo", "lexical", extended=True),
)


def _load_rule_engine():
	from tests.core_loader import load

	return load("rules").load_default_rules(extended=False)


def _single_changed_index(source: str, transformed: str) -> int:
	if len(source) != len(transformed):
		raise ValueError(f"Renderer rewrite changed length: {source!r} -> {transformed!r}")
	changed = [index for index, pair in enumerate(zip(source, transformed, strict=True)) if pair[0] != pair[1]]
	if len(changed) != 1:
		raise ValueError(f"Expected one changed character: {source!r} -> {transformed!r}")
	return changed[0]


def build_fixture() -> dict[str, object]:
	# The same immutable rendering map is used for every engine and voice.
	rules = _load_rule_engine()
	from tests.core_loader import load

	broader = load("rules").load_default_rules()
	cases: list[dict[str, object]] = []
	transformations: list[dict[str, object]] = []
	for scenario in SCENARIOS:
		transformed = (broader if scenario.extended else rules).transform(scenario.source, strict=scenario.strict)
		index = _single_changed_index(scenario.source, transformed)
		if scenario.source[index] != scenario.character:
			raise ValueError(f"Changed character is not {scenario.character!r}: {scenario.source!r}")
		anchor_text = transformed[:index] + scenario.alternate_anchor + transformed[index + 1 :]
		group = f"final_{scenario.id}"
		common = {
			"compareGroup": group,
			"targetCharIndex": index,
			"tier": scenario.tier,
			"expectedReading": scenario.expected_reading,
			"ruleKind": scenario.rule_kind,
			"strict": scenario.strict,
			"extended": scenario.extended,
		}
		cases.extend(
			(
				{
					"id": f"{scenario.id}_source",
					"text": scenario.source,
					"role": "source",
					**common,
				},
				{
					"id": f"{scenario.id}_transformed",
					"text": transformed,
					"role": "transformed",
					"rendererCandidate": transformed[index],
					**common,
				},
				{
					"id": f"{scenario.id}_common_anchor",
					"text": anchor_text,
					"role": "anchor",
					"anchorCharacter": scenario.alternate_anchor,
					"anchorConfidence": "common",
					**common,
				},
			),
		)
		transformations.append(
			{
				"id": scenario.id,
				"source": scenario.source,
				"transformed": transformed,
				"commonAnchor": anchor_text,
				"targetCharIndex": index,
				"expectedReading": scenario.expected_reading,
				"ruleKind": scenario.rule_kind,
				"strict": scenario.strict,
				"extended": scenario.extended,
			},
		)

	rule_bytes = RULE_DATA_PATH.read_bytes()
	return {
		"schemaVersion": 1,
		"purpose": "当前规则引擎输出到 Vocalizer Expressive 2.2 的最终完整音素流回归",
		"generatedFrom": {
			"runtimeSha256": {
				path.relative_to(ROOT).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
				for path in sorted(RULE_ENGINE_PATH.parent.rglob("*"))
				if path.is_file() and path.suffix in {".py", ".json", ".toml"}
			},
			"ruleEngine": str(RULE_ENGINE_PATH.relative_to(ROOT)).replace("\\", "/"),
			"ruleData": str(RULE_DATA_PATH.relative_to(ROOT)).replace("\\", "/"),
			"ruleDataSha256": hashlib.sha256(rule_bytes).hexdigest(),
			"ruleEngineSha256": hashlib.sha256(RULE_ENGINE_PATH.read_bytes()).hexdigest(),
			"renderer": "addon/globalPlugins/contextualPronunciation/rules.py",
			"rendererSha256": hashlib.sha256(RULE_ENGINE_PATH.read_bytes()).hexdigest(),
			"strict": "Default scenarios are strict; optional key preference is explicitly non-strict",
		},
		"method": (
			"每组由 source、规则引擎实时生成的 transformed、以及仅将目标字换成另一枚常用同音字的 "
			"common_anchor 组成；以同一次 Ting-Ting 离线渲染中的完整音素流严格相等为自动判据。"
		),
		"limitations": [
			"Vocalizer 音素编号为引擎私有值，只能在相同版本、声库、operating point 和同一次运行内比较。",
			"完整音素流相等仅验证音段序列一致；不独立验证声调或韵律。不相等不能单凭此判错。",
			"若引擎音素标记没有可独立解释的声调信息，则只能用同音锚点等价关系验证，仍需最终人工听取 WAV。",
		],
		"transformations": transformations,
		"cases": cases,
	}


def main() -> int:
	fixture = build_fixture()
	OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
	OUTPUT_PATH.write_text(json.dumps(fixture, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
	print(OUTPUT_PATH)
	for item in fixture["transformations"]:
		print(f"{item['id']}: {item['source']} -> {item['transformed']} | {item['commonAnchor']}")
	return 0


if __name__ == "__main__":
	raise SystemExit(main())
