from pathlib import Path

import httpx
import pytest

from app.db.session import check_sqlite
from app.services.ollama import check_ollama
from app.vector_store.milvus import check_vector_store


def test_check_sqlite_creates_parent_directory(tmp_path: Path) -> None:
    database_path = tmp_path / "nested" / "dota2_rag.db"

    result = check_sqlite(database_path)

    assert result.name == "sqlite"
    assert result.ok is True
    assert result.detail == "ready"
    assert database_path.parent.exists()


def test_check_vector_store_creates_local_data_directory(tmp_path: Path) -> None:
    vector_path = tmp_path / "milvus"

    result = check_vector_store(vector_path)

    assert result.name == "milvus"
    assert result.ok is True
    assert result.detail == "local vector directory ready"
    assert vector_path.exists()


@pytest.mark.asyncio
async def test_check_ollama_reports_ready_with_version_response() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/version"
        return httpx.Response(200, json={"version": "0.3.12"})

    transport = httpx.MockTransport(handler)

    result = await check_ollama("http://ollama.test", transport=transport)

    assert result.name == "ollama"
    assert result.ok is True
    assert result.detail == "0.3.12"


@pytest.mark.asyncio
async def test_check_ollama_reports_unavailable_on_connection_error() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused", request=request)

    transport = httpx.MockTransport(handler)

    result = await check_ollama("http://ollama.test", transport=transport)

    assert result.name == "ollama"
    assert result.ok is False
    assert "connection refused" in result.detail
