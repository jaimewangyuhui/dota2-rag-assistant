from pathlib import Path

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
from app.rag.schemas import SourceMetadata, TextChunk
from app.vector_store.milvus import LocalVectorStore


def make_client(tmp_path: Path) -> TestClient:
    settings = Settings(
        sqlite_path=tmp_path / "sqlite" / "dota2_rag.db",
        vector_data_path=tmp_path / "vectors",
        vector_index_path=tmp_path / "vectors" / "text_chunks.json",
        opendota_knowledge_sources_enabled=False,
    )
    return TestClient(create_app(settings))


def seed_vector_store(tmp_path: Path) -> None:
    store = LocalVectorStore(tmp_path / "vectors" / "text_chunks.json")
    chunks = [
        TextChunk(
            chunk_id="seed://items/black-king-bar#chunk-0",
            text="Black King Bar, often called BKB, is a core defensive item.",
            metadata=SourceMetadata(
                source_url="seed://items/black-king-bar",
                source_name="Seed: Black King Bar",
                patch_version=None,
                entity_type="item",
                entity_name="Black King Bar",
                updated_at="2026-06-18",
            ),
        ),
        TextChunk(
            chunk_id="https://api.opendota.com/api/constants/heroes/2#chunk-0",
            text=(
                "Axe is an OpenDota hero constant. Primary attribute: str. "
                "Roles: Initiator, Durable, Disabler, Carry."
            ),
            metadata=SourceMetadata(
                source_url="https://api.opendota.com/api/constants/heroes/2",
                source_name="OpenDota Hero: Axe",
                patch_version=None,
                entity_type="hero",
                entity_name="Axe",
                updated_at="2026-06-20",
            ),
        ),
        TextChunk(
            chunk_id="https://api.opendota.com/api/constants/items/blink#chunk-0",
            text="Blink Dagger is an OpenDota item constant. Cost: 2250. Mobility item.",
            metadata=SourceMetadata(
                source_url="https://api.opendota.com/api/constants/items/blink",
                source_name="OpenDota Item: Blink Dagger",
                patch_version=None,
                entity_type="item",
                entity_name="Blink Dagger",
                updated_at="2026-06-20",
            ),
        ),
        TextChunk(
            chunk_id="https://www.dota2.com/heroes/axe#chunk-0",
            text="Axe is an official Dota 2 hero.",
            metadata=SourceMetadata(
                source_url="https://www.dota2.com/heroes/axe",
                source_name="Official Dota 2: Axe",
                patch_version=None,
                entity_type="hero",
                entity_name="Axe",
                updated_at="2026-06-19",
            ),
        ),
    ]
    store.upsert([(chunk, [1.0, 0.0, 0.0]) for chunk in chunks])


def test_knowledge_summary_groups_chunks_by_type_and_source_prefix(tmp_path: Path) -> None:
    seed_vector_store(tmp_path)
    client = make_client(tmp_path)

    response = client.get("/api/knowledge/summary")

    assert response.status_code == 200
    payload = response.json()
    assert payload["total_chunks"] == 4
    assert payload["total_sources"] == 4
    assert payload["by_entity_type"] == {"hero": 2, "item": 2}
    assert payload["by_source_prefix"] == {
        "Official Dota 2": 1,
        "OpenDota Hero": 1,
        "OpenDota Item": 1,
        "Seed": 1,
    }
    assert payload["updated_at"] == "2026-06-20"


def test_knowledge_chunks_returns_previews_and_metadata(tmp_path: Path) -> None:
    seed_vector_store(tmp_path)
    client = make_client(tmp_path)

    response = client.get("/api/knowledge/chunks", params={"q": "Blink", "limit": 10})

    assert response.status_code == 200
    payload = response.json()
    assert len(payload["chunks"]) == 1
    chunk = payload["chunks"][0]
    assert chunk["source_name"] == "OpenDota Item: Blink Dagger"
    assert chunk["entity_type"] == "item"
    assert chunk["entity_name"] == "Blink Dagger"
    assert chunk["preview"] == "Blink Dagger is an OpenDota item constant. Cost: 2250. Mobility item."


def test_knowledge_chunks_filters_by_entity_type_source_prefix_and_limit(
    tmp_path: Path,
) -> None:
    seed_vector_store(tmp_path)
    client = make_client(tmp_path)

    response = client.get(
        "/api/knowledge/chunks",
        params={"entity_type": "hero", "source_prefix": "OpenDota Hero", "limit": 1},
    )

    assert response.status_code == 200
    payload = response.json()
    assert len(payload["chunks"]) == 1
    assert payload["chunks"][0]["source_name"] == "OpenDota Hero: Axe"


def test_knowledge_api_handles_empty_vector_store(tmp_path: Path) -> None:
    client = make_client(tmp_path)

    summary = client.get("/api/knowledge/summary").json()
    chunks = client.get("/api/knowledge/chunks").json()

    assert summary == {
        "total_chunks": 0,
        "total_sources": 0,
        "by_entity_type": {},
        "by_source_prefix": {},
        "updated_at": None,
    }
    assert chunks == {"chunks": []}
