# Dota 2 RAG Assistant M2 Text Ingestion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a small, testable text knowledge ingestion pipeline that chunks Dota 2 documents, embeds them locally, stores them behind a vector-store adapter, and retrieves source-bearing chunks for developer test questions.

**Architecture:** The backend keeps ingestion concerns in `app/rag`, source loading in `app/data_sources`, and vector persistence behind `app/vector_store`. M2 uses a deterministic local embedder for repeatable tests and an Ollama embedder for runtime ingestion, with a JSON-backed local vector index first; the adapter interface keeps the later Milvus Lite swap small and isolated.

**Tech Stack:** Python 3.11, FastAPI, Pydantic, httpx, pytest, local JSON persistence, Ollama embeddings API.

---

## File Structure

- Create `backend/app/rag/schemas.py`: typed document, metadata, chunk, and retrieval result models.
- Create `backend/app/rag/chunker.py`: deterministic chunking for source documents.
- Create `backend/app/rag/embeddings.py`: deterministic test embedder and Ollama runtime embedder.
- Create `backend/app/vector_store/schemas.py`: vector record and search result models.
- Modify `backend/app/vector_store/milvus.py`: keep the existing health check and add a local vector-store adapter with the same public shape planned for Milvus.
- Create `backend/app/data_sources/seed_documents.py`: built-in seed documents for BKB, Roshan, and Blink Dagger.
- Create `backend/app/jobs/ingest_documents.py`: orchestration for seed document ingestion.
- Create `backend/app/rag/retriever.py`: retrieve relevant chunks by query with metadata.
- Create `backend/app/api/ingest.py`: `POST /api/ingest/documents` and `GET /api/sources`.
- Modify `backend/app/main.py`: register ingestion routes.
- Test `backend/tests/test_chunker.py`: chunking and metadata preservation.
- Test `backend/tests/test_embeddings.py`: deterministic embedding shape and similarity signal.
- Test `backend/tests/test_vector_store.py`: upsert, persist, reload, and search.
- Test `backend/tests/test_ingest_job.py`: seed ingestion stores retrievable source-bearing chunks.
- Test `backend/tests/test_ingest_api.py`: API ingestion and source listing.
- Modify `README.md`: M2 commands and retrieval smoke test.

## Task 1: RAG Schemas And Chunking

**Files:**
- Create: `backend/app/rag/__init__.py`
- Create: `backend/app/rag/schemas.py`
- Create: `backend/app/rag/chunker.py`
- Test: `backend/tests/test_chunker.py`

- [ ] **Step 1: Write the failing chunking tests**

Create `backend/tests/test_chunker.py`:

```python
from app.rag.chunker import chunk_document
from app.rag.schemas import DocumentInput, SourceMetadata


def test_chunk_document_preserves_source_metadata() -> None:
    document = DocumentInput(
        text="Black King Bar gives spell immunity. BKB is timing-sensitive.",
        metadata=SourceMetadata(
            source_url="seed://items/black-king-bar",
            source_name="Seed: Black King Bar",
            patch_version="7.36",
            entity_type="item",
            entity_name="Black King Bar",
            updated_at="2026-06-18",
        ),
    )

    chunks = chunk_document(document, max_chars=80, overlap_chars=10)

    assert len(chunks) == 1
    assert chunks[0].text == document.text
    assert chunks[0].metadata.entity_name == "Black King Bar"
    assert chunks[0].metadata.source_url == "seed://items/black-king-bar"


def test_chunk_document_splits_long_text_with_overlap() -> None:
    text = " ".join(f"word{i}" for i in range(40))
    document = DocumentInput(
        text=text,
        metadata=SourceMetadata(
            source_url="seed://mechanics/test",
            source_name="Seed: Test",
            patch_version="7.36",
            entity_type="mechanic",
            entity_name="Test Mechanic",
            updated_at="2026-06-18",
        ),
    )

    chunks = chunk_document(document, max_chars=80, overlap_chars=20)

    assert len(chunks) > 1
    assert chunks[0].chunk_id == "seed://mechanics/test#chunk-0"
    assert chunks[1].chunk_id == "seed://mechanics/test#chunk-1"
    assert chunks[0].metadata == chunks[1].metadata
    assert set(chunks[0].text.split()) & set(chunks[1].text.split())
```

- [ ] **Step 2: Run the tests and verify RED**

Run:

```powershell
cd backend
$env:TEMP="$PWD\.tmp"; $env:TMP=$env:TEMP
.\.conda\python.exe -m pytest tests/test_chunker.py -v -p no:cacheprovider --basetemp .tmp\pytest-m2-chunker
```

Expected: FAIL with `ModuleNotFoundError: No module named 'app.rag'`.

- [ ] **Step 3: Add schema models**

Create `backend/app/rag/__init__.py`:

```python
```

Create `backend/app/rag/schemas.py`:

```python
from pydantic import BaseModel, Field


class SourceMetadata(BaseModel):
    source_url: str
    source_name: str
    patch_version: str | None = None
    entity_type: str
    entity_name: str
    updated_at: str


class DocumentInput(BaseModel):
    text: str = Field(min_length=1)
    metadata: SourceMetadata


class TextChunk(BaseModel):
    chunk_id: str
    text: str = Field(min_length=1)
    metadata: SourceMetadata


class RetrievedChunk(BaseModel):
    chunk: TextChunk
    score: float
```

- [ ] **Step 4: Add chunker implementation**

Create `backend/app/rag/chunker.py`:

```python
from app.rag.schemas import DocumentInput, TextChunk


def _normalize_text(text: str) -> str:
    return " ".join(text.split())


def _split_words(text: str, max_chars: int, overlap_chars: int) -> list[str]:
    words = text.split()
    chunks: list[str] = []
    current: list[str] = []

    for word in words:
        candidate = " ".join([*current, word])
        if current and len(candidate) > max_chars:
            chunks.append(" ".join(current))
            overlap: list[str] = []
            overlap_length = 0
            for previous in reversed(current):
                next_length = overlap_length + len(previous) + (1 if overlap else 0)
                if next_length > overlap_chars:
                    break
                overlap.insert(0, previous)
                overlap_length = next_length
            current = [*overlap, word]
        else:
            current.append(word)

    if current:
        chunks.append(" ".join(current))
    return chunks


def chunk_document(
    document: DocumentInput,
    max_chars: int = 900,
    overlap_chars: int = 120,
) -> list[TextChunk]:
    normalized = _normalize_text(document.text)
    parts = _split_words(normalized, max_chars=max_chars, overlap_chars=overlap_chars)
    return [
        TextChunk(
            chunk_id=f"{document.metadata.source_url}#chunk-{index}",
            text=part,
            metadata=document.metadata,
        )
        for index, part in enumerate(parts)
    ]
```

- [ ] **Step 5: Run chunking tests and verify GREEN**

Run:

```powershell
cd backend
$env:TEMP="$PWD\.tmp"; $env:TMP=$env:TEMP
.\.conda\python.exe -m pytest tests/test_chunker.py -v -p no:cacheprovider --basetemp .tmp\pytest-m2-chunker
```

Expected: PASS with 2 tests.

- [ ] **Step 6: Commit Task 1**

```powershell
git add backend/app/rag backend/tests/test_chunker.py
git commit -m "feat: add document chunking models"
```

## Task 2: Local Embedding Interface

**Files:**
- Create: `backend/app/rag/embeddings.py`
- Test: `backend/tests/test_embeddings.py`

- [ ] **Step 1: Write failing embedding tests**

Create `backend/tests/test_embeddings.py`:

```python
import httpx
import pytest

from app.rag.embeddings import DeterministicEmbedder, OllamaEmbedder, cosine_similarity


def test_deterministic_embedder_returns_stable_vectors() -> None:
    embedder = DeterministicEmbedder(dimensions=16)

    first = embedder.embed("Black King Bar BKB spell immunity")
    second = embedder.embed("Black King Bar BKB spell immunity")

    assert first == second
    assert len(first) == 16


def test_deterministic_embedder_scores_related_text_higher() -> None:
    embedder = DeterministicEmbedder(dimensions=32)
    query = embedder.embed("BKB spell immunity")
    related = embedder.embed("Black King Bar gives spell immunity")
    unrelated = embedder.embed("Roshan drops Aegis")

    assert cosine_similarity(query, related) > cosine_similarity(query, unrelated)


@pytest.mark.asyncio
async def test_ollama_embedder_reads_embedding_response() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/embeddings"
        return httpx.Response(200, json={"embedding": [0.1, 0.2, 0.3]})

    embedder = OllamaEmbedder(
        base_url="http://ollama.test",
        model="nomic-embed-text",
        transport=httpx.MockTransport(handler),
    )

    assert await embedder.aembed("BKB") == [0.1, 0.2, 0.3]
```

- [ ] **Step 2: Run embedding tests and verify RED**

Run:

```powershell
cd backend
$env:TEMP="$PWD\.tmp"; $env:TMP=$env:TEMP
.\.conda\python.exe -m pytest tests/test_embeddings.py -v -p no:cacheprovider --basetemp .tmp\pytest-m2-embeddings
```

Expected: FAIL because `app.rag.embeddings` does not exist.

- [ ] **Step 3: Add embedding implementations**

Create `backend/app/rag/embeddings.py`:

```python
import hashlib
import math
import re
from typing import Optional, Protocol

import httpx


TOKEN_PATTERN = re.compile(r"[a-zA-Z0-9]+")


class Embedder(Protocol):
    def embed(self, text: str) -> list[float]:
        ...


class AsyncEmbedder(Protocol):
    async def aembed(self, text: str) -> list[float]:
        ...


def cosine_similarity(left: list[float], right: list[float]) -> float:
    dot = sum(a * b for a, b in zip(left, right))
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return dot / (left_norm * right_norm)


class DeterministicEmbedder:
    def __init__(self, dimensions: int = 64) -> None:
        self.dimensions = dimensions

    def embed(self, text: str) -> list[float]:
        vector = [0.0] * self.dimensions
        tokens = TOKEN_PATTERN.findall(text.lower())
        for token in tokens:
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            index = int.from_bytes(digest[:4], "big") % self.dimensions
            vector[index] += 1.0
        norm = math.sqrt(sum(value * value for value in vector))
        if norm == 0:
            return vector
        return [value / norm for value in vector]


class OllamaEmbedder:
    def __init__(
        self,
        base_url: str,
        model: str = "nomic-embed-text",
        transport: Optional[httpx.AsyncBaseTransport] = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.transport = transport

    async def aembed(self, text: str) -> list[float]:
        async with httpx.AsyncClient(
            base_url=self.base_url,
            timeout=30.0,
            transport=self.transport,
        ) as client:
            response = await client.post(
                "/api/embeddings",
                json={"model": self.model, "prompt": text},
            )
            response.raise_for_status()
            payload = response.json()
        return [float(value) for value in payload["embedding"]]
```

- [ ] **Step 4: Run embedding tests and verify GREEN**

Run:

```powershell
cd backend
$env:TEMP="$PWD\.tmp"; $env:TMP=$env:TEMP
.\.conda\python.exe -m pytest tests/test_embeddings.py -v -p no:cacheprovider --basetemp .tmp\pytest-m2-embeddings
```

Expected: PASS with 3 tests.

- [ ] **Step 5: Commit Task 2**

```powershell
git add backend/app/rag/embeddings.py backend/tests/test_embeddings.py
git commit -m "feat: add local embedding adapters"
```

## Task 3: Vector Store Adapter

**Files:**
- Create: `backend/app/vector_store/schemas.py`
- Modify: `backend/app/vector_store/milvus.py`
- Test: `backend/tests/test_vector_store.py`

- [ ] **Step 1: Write failing vector-store tests**

Create `backend/tests/test_vector_store.py`:

```python
from pathlib import Path

from app.rag.schemas import SourceMetadata, TextChunk
from app.vector_store.milvus import LocalVectorStore


def make_chunk(chunk_id: str, text: str, entity_name: str) -> TextChunk:
    return TextChunk(
        chunk_id=chunk_id,
        text=text,
        metadata=SourceMetadata(
            source_url=f"seed://{chunk_id}",
            source_name=f"Seed: {entity_name}",
            patch_version="7.36",
            entity_type="item",
            entity_name=entity_name,
            updated_at="2026-06-18",
        ),
    )


def test_vector_store_upserts_and_searches_chunks(tmp_path: Path) -> None:
    store = LocalVectorStore(tmp_path / "vectors.json")
    store.upsert(
        [
            (make_chunk("bkb-1", "Black King Bar blocks many spells", "Black King Bar"), [1.0, 0.0]),
            (make_chunk("roshan-1", "Roshan drops Aegis", "Roshan"), [0.0, 1.0]),
        ]
    )

    results = store.search([1.0, 0.0], limit=1)

    assert len(results) == 1
    assert results[0].chunk.chunk_id == "bkb-1"
    assert results[0].chunk.metadata.source_name == "Seed: Black King Bar"


def test_vector_store_persists_records(tmp_path: Path) -> None:
    path = tmp_path / "vectors.json"
    store = LocalVectorStore(path)
    store.upsert([(make_chunk("bkb-1", "Black King Bar", "Black King Bar"), [1.0, 0.0])])

    reloaded = LocalVectorStore(path)

    assert reloaded.list_sources() == ["Seed: Black King Bar"]
    assert reloaded.search([1.0, 0.0], limit=1)[0].chunk.chunk_id == "bkb-1"
```

- [ ] **Step 2: Run vector-store tests and verify RED**

Run:

```powershell
cd backend
$env:TEMP="$PWD\.tmp"; $env:TMP=$env:TEMP
.\.conda\python.exe -m pytest tests/test_vector_store.py -v -p no:cacheprovider --basetemp .tmp\pytest-m2-vector
```

Expected: FAIL because `LocalVectorStore` does not exist.

- [ ] **Step 3: Add vector-store schemas**

Create `backend/app/vector_store/schemas.py`:

```python
from pydantic import BaseModel

from app.rag.schemas import RetrievedChunk, TextChunk


class VectorRecord(BaseModel):
    chunk: TextChunk
    vector: list[float]


class VectorSearchResult(RetrievedChunk):
    pass
```

- [ ] **Step 4: Extend vector-store adapter**

Modify `backend/app/vector_store/milvus.py` to contain:

```python
import json
from pathlib import Path

from app.db.session import ServiceStatus
from app.rag.embeddings import cosine_similarity
from app.rag.schemas import TextChunk
from app.vector_store.schemas import VectorRecord, VectorSearchResult


def check_vector_store(vector_data_path: Path) -> ServiceStatus:
    try:
        vector_data_path.mkdir(parents=True, exist_ok=True)
        return ServiceStatus(
            name="milvus",
            ok=True,
            detail="local vector directory ready",
        )
    except Exception as exc:
        return ServiceStatus(name="milvus", ok=False, detail=str(exc))


class LocalVectorStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.records = self._load()

    def _load(self) -> dict[str, VectorRecord]:
        if not self.path.exists():
            return {}
        payload = json.loads(self.path.read_text(encoding="utf-8"))
        return {
            item["chunk"]["chunk_id"]: VectorRecord.model_validate(item)
            for item in payload
        }

    def _save(self) -> None:
        payload = [record.model_dump(mode="json") for record in self.records.values()]
        self.path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def upsert(self, entries: list[tuple[TextChunk, list[float]]]) -> None:
        for chunk, vector in entries:
            self.records[chunk.chunk_id] = VectorRecord(chunk=chunk, vector=vector)
        self._save()

    def search(self, query_vector: list[float], limit: int = 5) -> list[VectorSearchResult]:
        scored = [
            VectorSearchResult(
                chunk=record.chunk,
                score=cosine_similarity(query_vector, record.vector),
            )
            for record in self.records.values()
        ]
        scored.sort(key=lambda result: result.score, reverse=True)
        return scored[:limit]

    def list_sources(self) -> list[str]:
        return sorted({record.chunk.metadata.source_name for record in self.records.values()})

    def clear(self) -> None:
        self.records = {}
        self._save()
```

- [ ] **Step 5: Run vector-store tests and verify GREEN**

Run:

```powershell
cd backend
$env:TEMP="$PWD\.tmp"; $env:TMP=$env:TEMP
.\.conda\python.exe -m pytest tests/test_vector_store.py -v -p no:cacheprovider --basetemp .tmp\pytest-m2-vector
```

Expected: PASS with 2 tests.

- [ ] **Step 6: Commit Task 3**

```powershell
git add backend/app/vector_store backend/tests/test_vector_store.py
git commit -m "feat: add local vector store adapter"
```

## Task 4: Seed Document Ingestion Job

**Files:**
- Create: `backend/app/data_sources/__init__.py`
- Create: `backend/app/data_sources/seed_documents.py`
- Create: `backend/app/jobs/__init__.py`
- Create: `backend/app/jobs/ingest_documents.py`
- Create: `backend/app/rag/retriever.py`
- Test: `backend/tests/test_ingest_job.py`

- [ ] **Step 1: Write failing ingestion job test**

Create `backend/tests/test_ingest_job.py`:

```python
from pathlib import Path

from app.jobs.ingest_documents import ingest_seed_documents
from app.rag.embeddings import DeterministicEmbedder
from app.rag.retriever import Retriever
from app.vector_store.milvus import LocalVectorStore


def test_ingest_seed_documents_makes_bkb_retrievable(tmp_path: Path) -> None:
    store = LocalVectorStore(tmp_path / "vectors.json")
    embedder = DeterministicEmbedder(dimensions=64)

    result = ingest_seed_documents(store=store, embedder=embedder)

    assert result.documents == 3
    assert result.chunks >= 3
    retrieved = Retriever(store=store, embedder=embedder).retrieve("BKB spell immunity", limit=2)
    assert retrieved[0].chunk.metadata.entity_name == "Black King Bar"
    assert retrieved[0].chunk.metadata.source_url == "seed://items/black-king-bar"
```

- [ ] **Step 2: Run ingestion job test and verify RED**

Run:

```powershell
cd backend
$env:TEMP="$PWD\.tmp"; $env:TMP=$env:TEMP
.\.conda\python.exe -m pytest tests/test_ingest_job.py -v -p no:cacheprovider --basetemp .tmp\pytest-m2-ingest-job
```

Expected: FAIL because `app.jobs.ingest_documents` does not exist.

- [ ] **Step 3: Add seed documents**

Create `backend/app/data_sources/__init__.py`:

```python
```

Create `backend/app/data_sources/seed_documents.py`:

```python
from app.rag.schemas import DocumentInput, SourceMetadata


def load_seed_documents() -> list[DocumentInput]:
    return [
        DocumentInput(
            text=(
                "Black King Bar, often called BKB, is a core defensive item. "
                "It grants a timed spell immunity effect that helps heroes commit "
                "during fights, dodge disables, and protect key damage windows."
            ),
            metadata=SourceMetadata(
                source_url="seed://items/black-king-bar",
                source_name="Seed: Black King Bar",
                patch_version="7.36",
                entity_type="item",
                entity_name="Black King Bar",
                updated_at="2026-06-18",
            ),
        ),
        DocumentInput(
            text=(
                "Roshan is the major neutral objective near the river. "
                "Roshan can drop Aegis of the Immortal and later additional rewards, "
                "so teams often fight around Roshan timing and vision."
            ),
            metadata=SourceMetadata(
                source_url="seed://objectives/roshan",
                source_name="Seed: Roshan",
                patch_version="7.36",
                entity_type="objective",
                entity_name="Roshan",
                updated_at="2026-06-18",
            ),
        ),
        DocumentInput(
            text=(
                "Blink Dagger gives instant repositioning over a short distance. "
                "It is commonly used to initiate fights, escape before taking damage, "
                "or reach high-value targets."
            ),
            metadata=SourceMetadata(
                source_url="seed://items/blink-dagger",
                source_name="Seed: Blink Dagger",
                patch_version="7.36",
                entity_type="item",
                entity_name="Blink Dagger",
                updated_at="2026-06-18",
            ),
        ),
    ]
```

- [ ] **Step 4: Add ingestion job and retriever**

Create `backend/app/jobs/__init__.py`:

```python
```

Create `backend/app/jobs/ingest_documents.py`:

```python
from pydantic import BaseModel

from app.data_sources.seed_documents import load_seed_documents
from app.rag.chunker import chunk_document
from app.rag.embeddings import Embedder
from app.vector_store.milvus import LocalVectorStore


class IngestResult(BaseModel):
    documents: int
    chunks: int
    sources: list[str]


def ingest_seed_documents(store: LocalVectorStore, embedder: Embedder) -> IngestResult:
    documents = load_seed_documents()
    chunks = [chunk for document in documents for chunk in chunk_document(document)]
    entries = [(chunk, embedder.embed(chunk.text)) for chunk in chunks]
    store.upsert(entries)
    return IngestResult(
        documents=len(documents),
        chunks=len(chunks),
        sources=store.list_sources(),
    )
```

Create `backend/app/rag/retriever.py`:

```python
from app.rag.embeddings import Embedder
from app.rag.schemas import RetrievedChunk
from app.vector_store.milvus import LocalVectorStore


class Retriever:
    def __init__(self, store: LocalVectorStore, embedder: Embedder) -> None:
        self.store = store
        self.embedder = embedder

    def retrieve(self, query: str, limit: int = 5) -> list[RetrievedChunk]:
        return self.store.search(self.embedder.embed(query), limit=limit)
```

- [ ] **Step 5: Run ingestion job test and verify GREEN**

Run:

```powershell
cd backend
$env:TEMP="$PWD\.tmp"; $env:TMP=$env:TEMP
.\.conda\python.exe -m pytest tests/test_ingest_job.py -v -p no:cacheprovider --basetemp .tmp\pytest-m2-ingest-job
```

Expected: PASS with 1 test.

- [ ] **Step 6: Commit Task 4**

```powershell
git add backend/app/data_sources backend/app/jobs backend/app/rag/retriever.py backend/tests/test_ingest_job.py
git commit -m "feat: ingest seed knowledge documents"
```

## Task 5: Ingestion API And Source Listing

**Files:**
- Create: `backend/app/api/ingest.py`
- Modify: `backend/app/main.py`
- Modify: `backend/app/core/config.py`
- Test: `backend/tests/test_ingest_api.py`

- [ ] **Step 1: Write failing API tests**

Create `backend/tests/test_ingest_api.py`:

```python
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
```

- [ ] **Step 2: Run API tests and verify RED**

Run:

```powershell
cd backend
$env:TEMP="$PWD\.tmp"; $env:TMP=$env:TEMP
.\.conda\python.exe -m pytest tests/test_ingest_api.py -v -p no:cacheprovider --basetemp .tmp\pytest-m2-ingest-api
```

Expected: FAIL with 404 responses because ingestion routes are not registered.

- [ ] **Step 3: Add vector index path setting**

Modify `backend/app/core/config.py`:

```python
from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Dota 2 RAG Assistant"
    sqlite_path: Path = Path("data/sqlite/dota2_rag.db")
    vector_data_path: Path = Path("data/milvus")
    vector_index_path: Path = Path("data/milvus/text_chunks.json")
    ollama_base_url: str = "http://localhost:11434"
    cors_origins: str = Field(
        default="http://localhost:5173,http://127.0.0.1:5173",
        description="Comma-separated browser origins allowed to call the API.",
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
```

- [ ] **Step 4: Add ingestion routes**

Create `backend/app/api/ingest.py`:

```python
from fastapi import APIRouter, Request
from pydantic import BaseModel

from app.jobs.ingest_documents import IngestResult, ingest_seed_documents
from app.rag.embeddings import DeterministicEmbedder
from app.vector_store.milvus import LocalVectorStore

router = APIRouter(prefix="/api", tags=["ingestion"])


class SourcesResponse(BaseModel):
    sources: list[str]


def _store_for_request(request: Request) -> LocalVectorStore:
    settings = request.app.state.settings
    return LocalVectorStore(settings.vector_index_path)


@router.post("/ingest/documents", response_model=IngestResult)
def ingest_documents(request: Request) -> IngestResult:
    store = _store_for_request(request)
    embedder = DeterministicEmbedder(dimensions=64)
    return ingest_seed_documents(store=store, embedder=embedder)


@router.get("/sources", response_model=SourcesResponse)
def list_sources(request: Request) -> SourcesResponse:
    store = _store_for_request(request)
    return SourcesResponse(sources=store.list_sources())
```

Modify `backend/app/main.py`:

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.health import router as health_router
from app.api.ingest import router as ingest_router
from app.core.config import Settings, get_settings


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved_settings = settings or get_settings()
    app = FastAPI(title=resolved_settings.app_name)
    app.state.settings = resolved_settings

    app.add_middleware(
        CORSMiddleware,
        allow_origins=resolved_settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(health_router)
    app.include_router(ingest_router)
    return app


app = create_app()
```

- [ ] **Step 5: Run ingestion API tests and verify GREEN**

Run:

```powershell
cd backend
$env:TEMP="$PWD\.tmp"; $env:TMP=$env:TEMP
.\.conda\python.exe -m pytest tests/test_ingest_api.py -v -p no:cacheprovider --basetemp .tmp\pytest-m2-ingest-api
```

Expected: PASS with 2 tests.

- [ ] **Step 6: Commit Task 5**

```powershell
git add backend/app/api/ingest.py backend/app/main.py backend/app/core/config.py backend/tests/test_ingest_api.py
git commit -m "feat: expose document ingestion API"
```

## Task 6: M2 Documentation And Verification

**Files:**
- Modify: `README.md`
- Test: full backend test suite and API smoke checks

- [ ] **Step 1: Update README with M2 commands**

Append to `README.md`:

```markdown
## M2 Text Ingestion

Seed the local text knowledge index:

```powershell
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/api/ingest/documents
```

List indexed sources:

```powershell
Invoke-RestMethod -Uri http://127.0.0.1:8000/api/sources
```

The M2 seed index includes `Black King Bar`, `Roshan`, and `Blink Dagger` documents. Runtime ingestion uses a deterministic local embedding for repeatable development checks; `OllamaEmbedder` is available for later model-backed ingestion once the embedding model is pulled.
```

- [ ] **Step 2: Run all backend tests**

Run:

```powershell
cd backend
$env:TEMP="$PWD\.tmp"; $env:TMP=$env:TEMP
.\.conda\python.exe -m pytest -v -p no:cacheprovider --basetemp .tmp\pytest-m2-final
```

Expected: PASS with all backend tests.

- [ ] **Step 3: Run frontend tests and build**

Run:

```powershell
cd frontend
npm test
npm run build
```

Expected: PASS for Vitest and Vite build.

- [ ] **Step 4: Start or reuse backend service**

Run if backend is not already running:

```powershell
cd backend
.\.conda\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Expected: backend listens on `http://127.0.0.1:8000`.

- [ ] **Step 5: Smoke-test ingestion endpoints**

Run:

```powershell
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/api/ingest/documents
Invoke-RestMethod -Uri http://127.0.0.1:8000/api/sources
```

Expected: ingestion reports `documents: 3`, at least 3 chunks, and sources include `Seed: Black King Bar`, `Seed: Blink Dagger`, and `Seed: Roshan`.

- [ ] **Step 6: Commit Task 6**

```powershell
git add README.md
git commit -m "docs: add m2 ingestion instructions"
```

## Self-Review

- Spec coverage: This plan implements M2 text ingestion, document/chunk models, embedding creation, vector-style storage, retrieval for test questions, source metadata, `/api/ingest/documents`, and `/api/sources`.
- Intentional adapter choice: The plan keeps `LocalVectorStore` inside `vector_store/milvus.py` as a Milvus-shaped adapter boundary. It stores JSON locally for M2 reliability and leaves a direct Milvus Lite backend for the next storage-hardening pass.
- Deferred scope: Chat generation, prompt building, question classification, OpenDota stats, and full frontend chat belong to M3-M5.
- Placeholder scan: No placeholder tasks remain; each test and implementation step includes concrete code.
- Type consistency: `DocumentInput`, `TextChunk`, `RetrievedChunk`, `VectorRecord`, `IngestResult`, and API response types are introduced before use.
