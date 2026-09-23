"""Independent expected text for sentence-position pronunciation regressions.

These expectations are not produced by the rule engine. Only the speech-only
target character changes; document text, punctuation and other letters do not.
"""

from itertools import product

SERVING_PHRASES = tuple("盛" + noun for noun in "汤饭水粥菜酒药茶面米土沙")
REPORTED_CASES = (
	("我给孩子盛饭之后盛汤", "我给孩子呈饭之后呈汤"),
	("我给孩子盛汤之后盛饭", "我给孩子呈汤之后呈饭"),
	("盛饭盛汤", "呈饭呈汤"),
	("盛饭盛汤很好", "呈饭呈汤很好"),
)
SENTENCE_CASES = (
	*REPORTED_CASES,
	("盛汤盛饭很好", "呈汤呈饭很好"),
	("盛汤之后再盛饭然后盛汤很好", "呈汤之后再呈饭然后呈汤很好"),
	("我给孩子盛汤的时候他正在盛饭", "我给孩子呈汤的时候他正在呈饭"),
	("盛饭盛汤盛饭盛汤都可以", "呈饭呈汤呈饭呈汤都可以"),
	("盛汤很好，盛饭也很好", "呈汤很好，呈饭也很好"),
	("盛汤$之后盛饭|很好", "呈汤$之后呈饭|很好"),
	("丰盛饭菜端上桌之后再盛汤", "丰盛饭菜端上桌之后再呈汤"),
	("盛汤之后欣赏盛开的花", "呈汤之后欣赏盛开的花"),
	("盛汤姆去盛饭店之后帮我盛汤", "盛汤姆去盛饭店之后帮我呈汤"),
	("旺盛水草旁边有人盛水浇花", "旺盛水草旁边有人呈水浇花"),
)
PROTECTED_CASES = (
	"丰盛饭菜",
	"丰盛汤品很好",
	"丰盛饭菜和丰盛酒席",
	"旺盛水草",
	"茂盛水草",
	"盛汤姆今天来访",
	"盛饭店今天营业",
	"盛水准今天提高了",
	"鲜花盛开之后依然茂盛",
)


def serving_sentence_matrix():
	"""12 x 12 objects, 7 joiners, 3 prefixes, 6 suffixes = 18,144 cases."""
	for first, second, joiner, prefix, suffix in product(
		SERVING_PHRASES,
		SERVING_PHRASES,
		("", "之后", "然后", "再", "并且", "的时候", "、"),
		("", "我给孩子", "厨房里正在"),
		("", "很好", "之后就离开", "的时候", "$", "|很好"),
	):
		source = prefix + first + joiner + second + suffix
		expected = prefix + first.replace("盛", "呈") + joiner + second.replace("盛", "呈") + suffix
		yield source, expected
