from pathlib import Path

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
from app.rag.schemas import DocumentInput, SourceMetadata


def test_ingest_documents_endpoint_indexes_seed_documents(tmp_path: Path) -> None:
    settings = Settings(
        sqlite_path=tmp_path / "sqlite" / "dota2_rag.db",
        vector_data_path=tmp_path / "vectors",
        vector_index_path=tmp_path / "vectors" / "text_chunks.json",
    )
    client = TestClient(create_app(settings))

    response = client.post("/api/ingest/documents")

    assert response.status_code == 200
    payload = response.json()
    assert payload["documents"] == 3
    assert payload["chunks"] >= 3
    assert "Seed: Black King Bar" in payload["sources"]


def test_sources_endpoint_lists_indexed_sources(tmp_path: Path) -> None:
    settings = Settings(
        sqlite_path=tmp_path / "sqlite" / "dota2_rag.db",
        vector_data_path=tmp_path / "vectors",
        vector_index_path=tmp_path / "vectors" / "text_chunks.json",
    )
    client = TestClient(create_app(settings))
    client.post("/api/ingest/documents")

    response = client.get("/api/sources")

    assert response.status_code == 200
    assert response.json()["sources"] == [
        "Seed: Black King Bar",
        "Seed: Blink Dagger",
        "Seed: Roshan",
    ]


def official_api_documents() -> list[DocumentInput]:
    return [
        DocumentInput(
            text="Axe is an official Dota 2 hero.",
            metadata=SourceMetadata(
                source_url="https://www.dota2.com/heroes/axe",
                source_name="Official Dota 2: Axe",
                patch_version=None,
                entity_type="hero",
                entity_name="Axe",
                updated_at="2026-06-19",
            ),
        )
    ]


def test_ingest_documents_endpoint_can_index_official_documents(tmp_path: Path) -> None:
    settings = Settings(
        sqlite_path=tmp_path / "sqlite" / "dota2_rag.db",
        vector_data_path=tmp_path / "vectors",
        vector_index_path=tmp_path / "vectors" / "text_chunks.json",
    )
    app = create_app(settings)
    app.state.official_documents_loader = official_api_documents
    client = TestClient(app)

    response = client.post("/api/ingest/documents")

    assert response.status_code == 200
    payload = response.json()
    assert payload["documents"] == 4
    assert "Official Dota 2: Axe" in payload["sources"]
