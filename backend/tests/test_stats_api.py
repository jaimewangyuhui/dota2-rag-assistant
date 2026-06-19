from pathlib import Path

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app


FIXTURE_DIR = Path(__file__).parent / "fixtures"


class FixtureOpenDotaClient:
    def fetch_hero_stats(self) -> str:
        return (FIXTURE_DIR / "opendota_hero_stats_sample.json").read_text(encoding="utf-8")


def test_refresh_stats_endpoint_writes_hero_stats(tmp_path: Path) -> None:
    settings = Settings(
        sqlite_path=tmp_path / "sqlite" / "dota2_rag.db",
        vector_data_path=tmp_path / "vectors",
        vector_index_path=tmp_path / "vectors" / "text_chunks.json",
    )
    app = create_app(settings)
    app.state.opendota_client = FixtureOpenDotaClient()
    app.state.stats_refreshed_at = "2026-06-19T09:00:00Z"
    client = TestClient(app)

    response = client.post("/api/refresh/stats")

    assert response.status_code == 200
    assert response.json() == {
        "heroes": 2,
        "refreshed_at": "2026-06-19T09:00:00Z",
    }
