from pathlib import Path

from app.data_sources.official_dota import (
    hero_records_to_documents,
    parse_hero_records,
)


FIXTURE_DIR = Path(__file__).parent / "fixtures"


def read_fixture(name: str) -> str:
    return (FIXTURE_DIR / name).read_text(encoding="utf-8")


def test_parse_hero_records_from_official_fixture() -> None:
    records = parse_hero_records(
        read_fixture("official_heroes_sample.json"),
        source_url="https://www.dota2.com/heroes",
    )

    assert [record.localized_name for record in records] == ["Axe", "Juggernaut"]
    assert records[0].roles == ["Initiator", "Durable", "Disabler"]
    assert records[0].primary_attribute == "str"
    assert records[0].source_url == "https://www.dota2.com/heroes/axe"


def test_hero_records_convert_to_documents() -> None:
    records = parse_hero_records(
        read_fixture("official_heroes_sample.json"),
        source_url="https://www.dota2.com/heroes",
    )

    documents = hero_records_to_documents(records)

    assert len(documents) == 2
    assert documents[0].metadata.source_name == "Official Dota 2: Axe"
    assert documents[0].metadata.entity_type == "hero"
    assert documents[0].metadata.entity_name == "Axe"
    assert documents[0].metadata.patch_version is None
    assert "Roles: Initiator, Durable, Disabler" in documents[0].text
    assert "Axe thrives in the chaos of battle" in documents[0].text
