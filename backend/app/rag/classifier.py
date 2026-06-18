QuestionType = str


PATCH_TERMS = ("patch", "版本", "改动", "更新", "7.")
STATS_TERMS = ("胜率", "pick rate", "ban rate", "登场率", "数据", "meta", "热门")
ADVICE_TERMS = ("应该", "怎么打", "怎么出", "建议", "克制", "counter", "对线", "团战")


def _contains_any(question: str, terms: tuple[str, ...]) -> bool:
    lowered = question.lower()
    return any(term.lower() in lowered for term in terms)


def classify_question(question: str) -> QuestionType:
    if _contains_any(question, PATCH_TERMS):
        return "patch"
    if _contains_any(question, STATS_TERMS):
        return "stats"
    if _contains_any(question, ADVICE_TERMS):
        return "advice"
    return "knowledge"
