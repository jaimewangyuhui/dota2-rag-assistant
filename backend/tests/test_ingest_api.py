from pathlib import Path

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app


def test_ingest_documents_endpoint_indexes_seed_documents(tmp_path: Path) -> None:
    settings = Settings(
        sqlite_path=tmp_path / "sqlite" / "dota2_rag.db",
        vector_data_path=tmp_path / "vectors",
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
