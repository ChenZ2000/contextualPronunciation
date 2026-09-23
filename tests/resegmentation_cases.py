"""Independent reading oracles for lexical edges and row quantities."""

from itertools import product

CASES = (
	*((d + head, "边", "bian1") for d, head in product("上下左右前后内外", ("边缘", "边界", "边框"))),
	*((d + head, "邊", "bian1") for d, head in product("上下左右前後內外", ("邊緣", "邊界", "邊框"))),
	*((a + "和" + b, "和", "he2") for a, b in product(("唱", "说", "吟", "朗读"), ("说", "唱", "跳", "写", "读书"))),
	*(
		(p + "多行" + s, "行", "hang2")
		for p, s in product(("", "支持", "切换到", "很", "许"), ("", "文本", "编辑", "输入框", "选择", "注释", "模式"))
	),
	("😀按钮的下边缘", "边", "bian1"),
	("“唱和说”", "和", "he2"),
	("唱和說是不同的表达方式", "和", "he2"),
	*(
		(s, "行", None)
		for s in (
			"多行不义必自毙",
			"多行不義必自斃",
			"多行善事",
			"多行礼",
			"多行医",
			"多行走",
			"多行驶",
			"很多行吗",
			"很多行不行",
			"至多行",
			"多行星",
			"多行程",
		)
	),
)
