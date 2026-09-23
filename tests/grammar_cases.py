"""Project-authored regression oracles, not a representative Chinese benchmark.

None means preserve that original character; it is NOT a guessed default tone.
Examples are held outside runtime data and contain previously unlisted phrases.
"""

from itertools import product

REPEAT = (
	"重转",
	"请把文件重转一次",
	"重转码",
	"重编译",
	"重下载",
	"重扫描",
	"重剪辑",
	"重配音",
	"重翻译",
	"重校对",
	"重排序",
	"重分配",
	"重合成",
	"重压缩",
	"重编码",
	"重计算",
	"重上传",
	"重安装",
	"重转换",
	"重签署",
	"重审核",
	"重设计",
	"重清理",
	"重拷贝",
	"重分析",
	"重搜索",
	"重讨论",
	"重打印",
	"重转发",
	"重转述",
	"重轉",
	"重轉碼",
	"重編譯",
	"重下載",
	"重掃描",
	"请把昨天从共享目录下载的那份经过同事仔细核对而且已经修正过所有错别字的文档重转换一次",
)

STRUCTURES = (
	("盛那碗刚刚煮好而且非常香甜的红豆粥", "盛", "cheng2"),
	("盛那碗又香又甜的红豆粥", "盛", "cheng2"),
	("盛奶奶早晨刚刚煮好而且已经晾凉的红豆粥", "盛", "cheng2"),
	("盛那杯透明而且无色的液体", "盛", "cheng2"),
	("盛装经过过滤而且已经冷却的液体", "盛", "cheng2"),
	("把刚刚煮好而且非常香甜的红豆粥盛进碗里", "盛", "cheng2"),
	("把这杯透明的液体慢慢地盛进容器里", "盛", "cheng2"),
	("量住在隔壁而且刚上小学的小名的身高", "量", "liang2"),
	("量住在那条非常安静的街道旁边的小名的身高", "量", "liang2"),
	("量孩子的朋友的妹妹的身高", "量", "liang2"),
	("量那张又宽又厚的桌子的长度", "量", "liang2"),
	("把住在隔壁而且刚上小学的小名的身高再仔细地量一下", "量", "liang2"),
	("系那条又细又长的红色丝带", "系", "ji4"),
	("系孩子昨天刚买的那双非常漂亮的鞋子的鞋带", "系", "ji4"),
	("把孩子昨天刚买的那双非常漂亮的鞋子的鞋带系好", "系", "ji4"),
	("量那位在昨天刚刚搬到附近的学校旁边的新公寓而且正在准备参加运动会的小朋友的身高", "量", "liang2"),
	(
		"量那位昨天刚刚从乡下搬到附近那条非常安静而且十分宽敞的街道旁边的新公寓并且正在认真准备参加学校举办的运动会的小朋友的身高",
		"量",
		"liang2",
	),
)

PROTECTIONS = (
	"重视工作",
	"重用人才",
	"重罚违法行为",
	"重判",
	"重击",
	"重惩",
	"重赏",
	"重酬",
	"重创",
	"重伤害",
	"重病",
	"重读音节",
	"重载铁路",
	"重装甲",
	"重生育",
	"重生产",
	"重听",
	"重要任务",
	"很重转不动",
	"太重搬不动",
	"十分重拿不起来",
	"体重增长",
	"重量转移",
	"尊重读者",
	"厚重转为轻盈",
	"重学生",
	"重未知词",
	"重龘靐",
	"重是",
	"重存在",
	"重属于",
	"重不懂",
	"重没有",
	"重可以",
	"重读",
	"重载",
	"重装",
	"重。转",
	"重\n转",
	"重😀转",
	"重\u200b转",
	"重Ａ转",
)

WRONG_HEADS = (
	("盛那碗刚刚煮好而且非常香甜的红豆粥的价格", "盛"),
	("盛透明液体公司的代表", "盛"),
	("盛未知而且红豆粥", "盛"),
	("量住在隔壁而且刚上小学的小名的身高标准", "量"),
	("量孩子说话然后记录身高", "量"),
	("系又细又长的红色丝带的价格", "系"),
	("把红豆粥端来盛先生的面前", "盛"),
	("把红豆粥放下然后参加盛会", "盛"),
	("把身高记录下来商量结果", "量"),
	("把孩子的鞋带放好再联系厂家", "系"),
)

CASES = (
	*((s, "重", "chong2") for s in REPEAT),
	*STRUCTURES,
	*((s, "重", None) for s in PROTECTIONS),
	*((s, target, None) for s, target in WRONG_HEADS),
)

# Oracles authored from the grammatical contrasts, never from engine output.
# A product varies independent slots; this is structural coverage, not random
# natural-language sampling or an open-domain accuracy estimate.
FEEDBACK_CASES = (
	("重吸收", "重", "chong2"),
	("重捏", "重", "chong2"),
	("重飞", "重", "chong2"),
	("盛了一碗饭", "盛", "cheng2"),
	("虾兵和蟹将", "将", "jiang4"),
	("天兵和天将", "将", "jiang4"),
	("蝦兵和蟹將", "將", "jiang4"),
	("天兵和天將", "將", "jiang4"),
	("蟹将和虾兵", "将", "jiang4"),
	("天将和天兵", "将", "jiang4"),
	("将和士兵", "将", "jiang4"),
	("他将和士兵一起离开", "将", None),
	("老师将和士兵一起离开", "将", None),
	("小王将和士兵一起离开", "将", None),
	("士兵和飞机将起飞", "将", None),
	("士兵和汽车将都离开", "将", None),
	("飞机将和士兵一起离开", "将", None),
	("士兵和新买的飞机将起飞", "将", None),
	("新买的飞机将和士兵一起离开", "将", None),
	("士兵和已经维修好的汽车将都离开", "将", None),
	("虾兵和蟹将出发", "将", "jiang4"),
	("天兵和天将都在门口", "将", "jiang4"),
	("重吸收已经释放的物质", "重", "chong2"),
	("把那一碗刚刚煮好而且非常香甜的饭再小心地盛进容器里", "盛", "cheng2"),
	("她给住在隔壁的孩子盛了一大碗刚刚煮好而且热气腾腾的饭", "盛", "cheng2"),
	("那些训练有素的士兵和身经百战的将都已经来到门口", "将", "jiang4"),
	("天将下雨", "将", None),
	("天將下雨", "將", None),
	("天将降大任于斯人也", "将", None),
	("士兵和老师将离开", "将", None),
	("士兵和小王将离开", "将", None),
	("士兵和他将离开", "将", None),
	("天兵和天将军", "将", None),
	("一名经验丰富的老师将参加会议", "将", None),
	("一位老人的将来", "将", None),
	("盛了一碗饭的价格", "盛", None),
	("盛了一位老师的饭", "盛", None),
	("盛了三明治公司的产品", "盛", None),
	("盛了一碗未知的龘靐", "盛", None),
	("很重吸收不了", "重", None),
	("体重吸引了注意", "重", None),
)

GENERATED_CASES = (
	*(
		(prefix + "重" + verb + suffix, "重", "chong2")
		for prefix, verb, suffix in product(
			("", "请", "需要", "失败之后再"),
			("吸收", "捏", "飞", "扫描", "校对", "转码", "编译", "配音"),
			("", "一次", "之后继续"),
		)
	),
	*(
		("盛" + aspect + quantity + modifier + head, "盛", "cheng2")
		for aspect, quantity, modifier, head in product(
			("了", "过", "好", "出了", "满了"),
			("一碗", "两大碗", "三小碗", "半碗", "那一碗"),
			("", "热", "刚煮好的", "刚刚煮好而且非常香甜的"),
			("饭", "汤", "粥"),
		)
	),
	*(
		("盛了" + quantity + modifier + head + "的价格", "盛", None)
		for quantity, modifier, head in product(
			("一碗", "两大碗", "半碗"),
			("", "刚煮好的"),
			("饭", "汤", "粥"),
		)
	),
	*(
		(left + conjunction + modifier + "将" + suffix, "将", "jiang4")
		for left, conjunction, modifier, suffix in product(
			("虾兵", "天兵", "士兵"),
			("和", "与", "及"),
			("蟹", "天", "勇猛的", "身经百战的"),
			("", "的盔甲在门口"),
		)
	),
	*(
		(quantity + modifier + "将", "将", "jiang4")
		for quantity, modifier in product(("一员", "两位", "三名"), ("勇猛的", "身经百战的", "守卫边关的"))
	),
	*(
		(modifier + "将" + conjunction + right + suffix, "将", "jiang4")
		for modifier, conjunction, right, suffix in product(
			("蟹", "天", "勇猛的"), ("和", "与", "及"), ("虾兵", "天兵", "士兵"), ("", "，随后继续前进")
		)
	),
	*(
		(left + "和" + subject + "将" + predicate, "将", None)
		for left, subject, predicate in product(
			("士兵", "天兵"),
			("老师", "游客", "他", "小王"),
			("离开", "参加会议", "回来"),
		)
	),
	*(
		("盛了" + quantity + modifier + head, "盛", "cheng2")
		for quantity, modifier, head in product(("一碗", "兩大碗"), ("", "剛煮好的"), ("飯", "湯", "粥"))
	),
	*(
		("盛了一" + classifier + modifier + head, "盛", "cheng2")
		for classifier, modifier, head in product(("盆", "锅", "勺", "杯"), ("", "刚煮好的"), ("饭", "汤", "粥"))
	),
)

CASES = tuple(dict.fromkeys((*CASES, *FEEDBACK_CASES, *GENERATED_CASES)))

# Ellipsis and coordinated subjects: expectations are based on grammatical
# contrasts, including future 将 and external relative heads as negatives.
CONTINUATION_CASES = (
	("也给我盛了一碗", "盛", "cheng2"),
	("天兵和天将一起去吃饭", "将", "jiang4"),
	*(
		(prefix + "盛" + aspect + quantity + continuation, "盛", "cheng2")
		for prefix, aspect, quantity, continuation in product(
			("也给我", "她给住在隔壁的孩子"),
			("了", "过", "好了", "出了"),
			("一碗", "两大碗", "半杯", "那三小勺", "一盆"),
			("", "就回去了", "给我", "，然后把锅放回去"),
		)
	),
	*(
		(subject + predicate, target, "jiang4")
		for (subject, target), predicate in product(
			(
				("天兵和天将", "将"),
				("虾兵与蟹将", "将"),
				("蟹将和虾兵", "将"),
				("天将与天兵", "将"),
				("那些训练有素的士兵和身经百战的将", "将"),
				("身经百战的将和那些训练有素的士兵", "将"),
				("天兵和天將", "將"),
				("蝦兵與蟹將", "將"),
			),
			(
				"一起去吃饭",
				"一同出发",
				"都在门口",
				"已经出发",
				"非常勇猛",
				"安静地吃饭",
				"要去吃饭",
				"会一起出发",
				"正在准备吃饭",
				"还没吃饭",
				"都已经安全地抵达营地",
				"每天一起去食堂吃饭",
			),
		)
	),
	*(
		(left + "和" + subject + "将" + predicate, "将", None)
		for left, subject, predicate in product(
			("士兵", "天兵"),
			("老师", "游客", "他", "飞机", "新买的飞机", "已经维修好的汽车"),
			("一起离开", "都在门口", "一同出发"),
		)
	),
	*(
		("盛了" + tail, "盛", None)
		for tail in (
			"一位",
			"一名",
			"一碗的价格",
			"一碗未知的龘靐",
			"一碗饭的包装设计",
			"一碗龘靐",
			"一碗盛会的纪念品",
			"一碗刚买的盘子",
			"一碗公司的产品",
		)
	),
)

CASES = tuple(dict.fromkeys((*CASES, *CONTINUATION_CASES)))

from tests.resegmentation_cases import CASES as RESEGMENTATION_CASES  # noqa: E402

CASES = tuple(dict.fromkeys((*CASES, *RESEGMENTATION_CASES)))
