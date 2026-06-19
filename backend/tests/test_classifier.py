from app.rag.classifier import classify_question


def test_classifies_chinese_hero_alias_stats_question() -> None:
    assert classify_question("斧王胜率") == "stats"


def test_classifies_mixed_english_stats_question() -> None:
    assert classify_question("Axe win rate meta") == "stats"


def test_classifies_chinese_item_advice_question() -> None:
    assert classify_question("跳刀怎么用？") == "advice"


def test_classifies_roshan_drop_question_as_knowledge() -> None:
    assert classify_question("肉山掉什么？") == "knowledge"


def test_classifies_patch_questions() -> None:
    assert classify_question("7.36 BKB 改了什么?") == "patch"


def test_classifies_stats_questions() -> None:
    assert classify_question("当前 Juggernaut 胜率怎么样?") == "stats"


def test_classifies_advice_questions() -> None:
    assert classify_question("对面很多控制我应该出 BKB 吗?") == "advice"


def test_defaults_to_knowledge() -> None:
    assert classify_question("Roshan 会掉什么?") == "knowledge"
