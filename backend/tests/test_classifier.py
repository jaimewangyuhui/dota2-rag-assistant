from app.rag.classifier import classify_question


def test_classifies_patch_questions() -> None:
    assert classify_question("7.36 BKB 改了什么?") == "patch"


def test_classifies_stats_questions() -> None:
    assert classify_question("当前 Juggernaut 胜率怎么样?") == "stats"


def test_classifies_advice_questions() -> None:
    assert classify_question("对面很多控制我应该出 BKB 吗?") == "advice"


def test_defaults_to_knowledge() -> None:
    assert classify_question("Roshan 会掉什么?") == "knowledge"
