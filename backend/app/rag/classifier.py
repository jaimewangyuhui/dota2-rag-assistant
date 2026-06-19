from app.rag.aliases import normalize_question


QuestionType = str


PATCH_TERMS = ("patch", "版本", "改动", "更新", "7.")
STATS_TERMS = (
    "胜率",
    "win rate",
    "pick rate",
    "ban rate",
    "登场率",
    "数据",
    "meta",
    "热门",
)
ADVICE_TERMS = (
    "应该",
    "怎么打",
    "怎么用",
    "怎么出",
    "建议",
    "克制",
    "counter",
    "对线",
    "团战",
)


def _contains_any(question: str, terms: tuple[str, ...]) -> bool:
    lowered = question.lower()
    return any(term.lower() in lowered for term in terms)


def classify_question(question: str) -> QuestionType:
    normalized = normalize_question(question)
    candidate = normalized.expanded
    if _contains_any(candidate, PATCH_TERMS):
        return "patch"
    if _contains_any(candidate, STATS_TERMS):
        return "stats"
    if _contains_any(candidate, ADVICE_TERMS):
        return "advice"
    return "knowledge"
