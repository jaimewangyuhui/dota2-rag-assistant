from pathlib import Path

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app


def test_health_endpoint_reports_all_m1_services(tmp_path: Path) -> None:
    settings = Settings(
        sqlite_path=tmp_path / "sqlite" / "dota2_rag.db",
        vector_data_path=tmp_path / "milvus",
        ollama_base_url="http://127.0.0.1:9",
    )
    client = TestClient(create_app(settings))

    response = client.get("/api/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["app"] == "Dota 2 RAG Assistant"
    assert payload["ok"] is False
    assert {service["name"] for service in payload["services"]} == {
        "backend",
        "sqlite",
        "milvus",
        "ollama",
    }
    assert payload["services"][0] == {
        "name": "backend",
        "ok": True,
        "detail": "ready",
    }


def test_cors_allows_local_vite_origin(tmp_path: Path) -> None:
    settings = Settings(
        sqlite_path=tmp_path / "sqlite" / "dota2_rag.db",
        vector_data_path=tmp_path / "milvus",
        cors_origins="http://localhost:5173",
    )
    client = TestClient(create_app(settings))

    response = client.options(
        "/api/health",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
