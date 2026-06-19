from pathlib import Path

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
from app.rag.generator import FakeGenerator


FIXTURE_DIR = Path(__file__).parent / "fixtures"


class FixtureOpenDotaClient:
    def fetch_hero_stats(self) -> str:
        return (FIXTURE_DIR / "opendota_hero_stats_sample.json").read_text(encoding="utf-8")


def test_chat_endpoint_answers_with_sources_after_ingestion(tmp_path: Path) -> None:
    settings = Settings(
        sqlite_path=tmp_path / "sqlite" / "dota2_rag.db",
        vector_data_path=tmp_path / "vectors",
        vector_index_path=tmp_path / "vectors" / "text_chunks.json",
    )
    app = create_app(settings)
    app.state.generator_override = FakeGenerator("BKB 可以提供 spell immunity。")
    client = TestClient(app)
    client.post("/api/ingest/documents")

    response = client.post("/api/chat", json={"message": "BKB 有什么用?"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["answer"] == "BKB 可以提供 spell immunity。"
    assert payload["question_type"] == "knowledge"
    assert payload["sources"][0]["source_name"] == "Seed: Black King Bar"


def test_chat_endpoint_returns_uncertainty_without_index(tmp_path: Path) -> None:
    settings = Settings(
        sqlite_path=tmp_path / "sqlite" / "dota2_rag.db",
        vector_data_path=tmp_path / "vectors",
        vector_index_path=tmp_path / "vectors" / "text_chunks.json",
    )
    app = create_app(settings)
    app.state.generator_override = FakeGenerator("unused")
    client = TestClient(app)

    response = client.post("/api/chat", json={"message": "Chen 的神杖效果是什么?"})

    assert response.status_code == 200
    assert response.json()["answer"] == "当前知识库没有覆盖这个问题，无法基于已索引来源可靠回答。"
    assert response.json()["sources"] == []


def test_chat_endpoint_answers_stats_after_refresh(tmp_path: Path) -> None:
    settings = Settings(
        sqlite_path=tmp_path / "sqlite" / "dota2_rag.db",
        vector_data_path=tmp_path / "vectors",
        vector_index_path=tmp_path / "vectors" / "text_chunks.json",
    )
    app = create_app(settings)
    app.state.opendota_client = FixtureOpenDotaClient()
    app.state.stats_refreshed_at = "2026-06-19T09:00:00Z"
    client = TestClient(app)
    client.post("/api/refresh/stats")

    response = client.post("/api/chat", json={"message": "Axe win rate meta"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["question_type"] == "stats"
    assert "Axe" in payload["answer"]
    assert "52.0%" in payload["answer"]
    assert payload["debug"]["stats_used"] is True
