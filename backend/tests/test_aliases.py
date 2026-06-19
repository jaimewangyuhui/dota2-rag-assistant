from app.rag.aliases import normalize_question


def test_normalizes_black_king_bar_aliases() -> None:
    normalized = normalize_question("黑皇杖有什么用？")

    assert normalized.original == "黑皇杖有什么用？"
    assert "Black King Bar" in normalized.expanded
    assert "BKB" in normalized.expanded
    assert "Black King Bar / BKB" in normalized.canonical_terms


def test_normalizes_roshan_aliases() -> None:
    normalized = normalize_question("肉山掉什么？")

    assert "Roshan" in normalized.expanded
    assert normalized.canonical_terms == ["Roshan"]


def test_normalizes_axe_hero_aliases() -> None:
    normalized = normalize_question("斧王胜率")

    assert normalized.canonical_hero == "Axe"
    assert "Axe" in normalized.expanded
    assert "Axe" in normalized.canonical_terms


def test_normalizes_blink_dagger_aliases() -> None:
    normalized = normalize_question("跳刀怎么用？")

    assert "Blink Dagger" in normalized.expanded
    assert normalized.canonical_terms == ["Blink Dagger"]


def test_deduplicates_terms_when_question_already_uses_canonical_name() -> None:
    normalized = normalize_question("What does BKB do?")

    assert normalized.expanded.count("BKB") == 1
    assert normalized.canonical_terms == ["Black King Bar / BKB"]
