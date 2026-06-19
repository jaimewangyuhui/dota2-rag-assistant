from pathlib import Path

from app.data_sources.official_dota import (
    OfficialDotaClient,
    hero_records_to_documents,
    load_official_dota_documents,
    parse_hero_records,
    parse_patch_records,
    patch_records_to_documents,
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


def test_parse_patch_records_from_official_fixture() -> None:
    records = parse_patch_records(
        read_fixture("official_patch_sample.json"),
        source_url="https://www.dota2.com/patches",
    )

    assert len(records) == 1
    assert records[0].patch_version == "7.36"
    assert records[0].title == "Gameplay Update 7.36"
    assert records[0].sections[0].heading == "General"
    assert records[0].source_url == "https://www.dota2.com/patches/7.36"


def test_patch_records_convert_to_documents() -> None:
    records = parse_patch_records(
        read_fixture("official_patch_sample.json"),
        source_url="https://www.dota2.com/patches",
    )

    documents = patch_records_to_documents(records)

    assert len(documents) == 1
    assert documents[0].metadata.source_name == "Official Dota 2 Patch 7.36"
    assert documents[0].metadata.entity_type == "patch"
    assert documents[0].metadata.entity_name == "Gameplay Update 7.36"
    assert documents[0].metadata.patch_version == "7.36"
    assert "Added innate abilities for heroes." in documents[0].text


class FixtureOfficialClient(OfficialDotaClient):
    def fetch_heroes(self) -> str:
        return read_fixture("official_heroes_sample.json")

    def fetch_patches(self) -> str:
        return read_fixture("official_patch_sample.json")


def test_load_official_dota_documents_combines_heroes_and_patches() -> None:
    documents = load_official_dota_documents(FixtureOfficialClient())

    assert [document.metadata.entity_type for document in documents] == [
        "hero",
        "hero",
        "patch",
    ]
    assert documents[-1].metadata.source_name == "Official Dota 2 Patch 7.36"
