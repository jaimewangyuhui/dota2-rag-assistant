from pathlib import Path

import pytest

from app.data_sources.opendota_knowledge import (
    OpenDotaKnowledgeClient,
    OpenDotaKnowledgeParseError,
    hero_records_to_documents,
    item_records_to_documents,
    load_opendota_knowledge_documents,
    parse_hero_constants,
    parse_item_constants,
)


FIXTURES = Path(__file__).parent / "fixtures"


def read_fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


class FakeOpenDotaKnowledgeClient:
    base_url = "https://api.opendota.com/api"

    def fetch_heroes(self) -> str:
        return read_fixture("opendota_heroes_constants_sample.json")

    def fetch_items(self) -> str:
        return read_fixture("opendota_items_constants_sample.json")


def test_parse_hero_constants_reads_dictionary_payload() -> None:
    records = parse_hero_constants(
        read_fixture("opendota_heroes_constants_sample.json"),
        refreshed_at="2026-06-20",
        base_url="https://api.opendota.com/api",
    )

    assert len(records) == 2
    axe = records[0]
    assert axe.hero_id == 2
    assert axe.key == "npc_dota_hero_axe"
    assert axe.localized_name == "Axe"
    assert axe.primary_attr == "str"
    assert axe.attack_type == "Melee"
    assert axe.roles == ["Initiator", "Durable", "Disabler", "Carry"]
    assert axe.aliases == ["axe", "npc dota hero axe"]
    assert axe.source_url == "https://api.opendota.com/api/constants/heroes/2"


def test_parse_item_constants_reads_dictionary_payload() -> None:
    records = parse_item_constants(
        read_fixture("opendota_items_constants_sample.json"),
        refreshed_at="2026-06-20",
        base_url="https://api.opendota.com/api",
    )

    assert len(records) == 2
    blink = records[0]
    assert blink.key == "blink"
    assert blink.item_id == 1
    assert blink.display_name == "Blink Dagger"
    assert blink.cost == 2250
    assert blink.components == []
    assert "Teleport to a target point" in blink.notes
    assert blink.source_url == "https://api.opendota.com/api/constants/items/blink"


def test_records_to_documents_create_searchable_metadata() -> None:
    heroes = parse_hero_constants(
        read_fixture("opendota_heroes_constants_sample.json"),
        refreshed_at="2026-06-20",
        base_url="https://api.opendota.com/api",
    )
    items = parse_item_constants(
        read_fixture("opendota_items_constants_sample.json"),
        refreshed_at="2026-06-20",
        base_url="https://api.opendota.com/api",
    )

    hero_doc = hero_records_to_documents(heroes)[0]
    item_doc = item_records_to_documents(items)[0]

    assert hero_doc.metadata.source_name == "OpenDota Hero: Axe"
    assert hero_doc.metadata.entity_type == "hero"
    assert hero_doc.metadata.entity_name == "Axe"
    assert "Roles: Initiator, Durable, Disabler, Carry." in hero_doc.text
    assert "Aliases: axe, npc dota hero axe." in hero_doc.text

    assert item_doc.metadata.source_name == "OpenDota Item: Blink Dagger"
    assert item_doc.metadata.entity_type == "item"
    assert item_doc.metadata.entity_name == "Blink Dagger"
    assert "Cost: 2250." in item_doc.text
    assert "mobility" in item_doc.text.lower()


def test_load_opendota_knowledge_documents_combines_heroes_and_items() -> None:
    documents = load_opendota_knowledge_documents(
        client=FakeOpenDotaKnowledgeClient(),
        refreshed_at="2026-06-20",
    )

    assert len(documents) == 4
    assert {document.metadata.entity_type for document in documents} == {"hero", "item"}
    assert "OpenDota Hero: Axe" in {document.metadata.source_name for document in documents}
    assert "OpenDota Item: Black King Bar" in {
        document.metadata.source_name for document in documents
    }


def test_parse_hero_constants_rejects_empty_payload() -> None:
    with pytest.raises(OpenDotaKnowledgeParseError, match="No OpenDota hero constants"):
        parse_hero_constants(
            "{}",
            refreshed_at="2026-06-20",
            base_url="https://api.opendota.com/api",
        )


def test_parse_item_constants_rejects_empty_payload() -> None:
    with pytest.raises(OpenDotaKnowledgeParseError, match="No OpenDota item constants"):
        parse_item_constants(
            "{}",
            refreshed_at="2026-06-20",
            base_url="https://api.opendota.com/api",
        )


def test_client_fetches_hero_and_item_constants(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []

    class FakeResponse:
        text = "{}"

        def raise_for_status(self) -> None:
            return None

    def fake_get(url: str, timeout: float) -> FakeResponse:
        calls.append(f"{url}|{timeout}")
        return FakeResponse()

    monkeypatch.setattr("app.data_sources.opendota_knowledge.httpx.get", fake_get)

    client = OpenDotaKnowledgeClient(base_url="https://example.test/api", timeout=12.0)

    assert client.fetch_heroes() == "{}"
    assert client.fetch_items() == "{}"
    assert calls == [
        "https://example.test/api/constants/heroes|12.0",
        "https://example.test/api/constants/items|12.0",
    ]
