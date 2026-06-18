# Dota 2 RAG Assistant M3 Basic RAG Chat Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a backend chat pipeline that classifies Dota 2 questions, retrieves indexed text chunks, builds a constrained Chinese prompt, calls Ollama, and returns an answer with source metadata.

**Architecture:** M3 keeps orchestration in `app/rag/chat_service.py`, with classification, prompt building, and generation split into focused modules. Tests use deterministic embeddings and fake generators so RAG behavior is repeatable; runtime uses the existing local vector index plus Ollama chat API.

**Tech Stack:** Python 3.11, FastAPI, Pydantic, httpx, pytest, local vector adapter from M2, Ollama `/api/chat`.

---

## File Structure

- Create `backend/app/rag/classifier.py`: keyword-based M3 question classifier for `knowledge`, `patch`, `stats`, and `advice`.
- Create `backend/app/rag/prompt_builder.py`: prompt assembly from question, classification, retrieved chunks, and generation rules.
- Create `backend/app/rag/generator.py`: `Generator` protocol, fake test generator, and Ollama chat generator.
- Create `backend/app/rag/chat_service.py`: retrieval thresholding, missing-coverage handling, source extraction, and generation orchestration.
- Create `backend/app/api/chat.py`: `POST /api/chat` endpoint.
- Modify `backend/app/main.py`: register the chat router.
- Test `backend/tests/test_classifier.py`: category detection.
- Test `backend/tests/test_prompt_builder.py`: prompt contains Chinese answer rules, English term preservation, and source context.
- Test `backend/tests/test_generator.py`: Ollama chat response parsing with mocked httpx transport.
- Test `backend/tests/test_chat_service.py`: answer with sources and explicit uncertainty when retrieval is insufficient.
- Test `backend/tests/test_chat_api.py`: end-to-end API chat with seeded local index and fake app-state generator override.
- Modify `README.md`: M3 chat smoke commands.

## Task 1: Question Classifier

**Files:**
- Create: `backend/app/rag/classifier.py`
- Test: `backend/tests/test_classifier.py`

- [ ] **Step 1: Write failing classifier tests**

Create `backend/tests/test_classifier.py`:

```python
from app.rag.classifier import classify_question


def test_classifies_patch_questions() -> None:
    assert classify_question("7.36 BKB 改了什么?") == "patch"


def test_classifies_stats_questions() -> None:
    assert classify_question("当前 Juggernaut 胜率怎么样?") == "stats"


def test_classifies_advice_questions() -> None:
    assert classify_question("对面很多控制我应该出 BKB 吗?") == "advice"


def test_defaults_to_knowledge() -> None:
    assert classify_question("Roshan 会掉什么?") == "knowledge"
```

- [ ] **Step 2: Run classifier tests and verify RED**

Run:

```powershell
cd backend
$env:TEMP="$PWD\.tmp"; $env:TMP=$env:TEMP
.\.conda\python.exe -m pytest tests/test_classifier.py -v -p no:cacheprovider --basetemp .tmp\pytest-m3-classifier
```

Expected: FAIL because `app.rag.classifier` does not exist.

- [ ] **Step 3: Add classifier implementation**

Create `backend/app/rag/classifier.py`:

```python
QuestionType = str


PATCH_TERMS = ("patch", "版本", "改动", "更新", "7.")
STATS_TERMS = ("胜率", "pick rate", "ban rate", "登场率", "数据", "meta", "热门")
ADVICE_TERMS = ("应该", "怎么打", "怎么出", "建议", "克制", "counter", "对线", "团战")


def _contains_any(question: str, terms: tuple[str, ...]) -> bool:
    lowered = question.lower()
    return any(term.lower() in lowered for term in terms)


def classify_question(question: str) -> QuestionType:
    if _contains_any(question, PATCH_TERMS):
        return "patch"
    if _contains_any(question, STATS_TERMS):
        return "stats"
    if _contains_any(question, ADVICE_TERMS):
        return "advice"
    return "knowledge"
```

- [ ] **Step 4: Run classifier tests and verify GREEN**

Run:

```powershell
cd backend
$env:TEMP="$PWD\.tmp"; $env:TMP=$env:TEMP
.\.conda\python.exe -m pytest tests/test_classifier.py -v -p no:cacheprovider --basetemp .tmp\pytest-m3-classifier
```

Expected: PASS with 4 tests.

- [ ] **Step 5: Commit Task 1**

```powershell
git add backend/app/rag/classifier.py backend/tests/test_classifier.py
git commit -m "feat: classify chat questions"
```

## Task 2: Prompt Builder

**Files:**
- Create: `backend/app/rag/prompt_builder.py`
- Test: `backend/tests/test_prompt_builder.py`

- [ ] **Step 1: Write failing prompt builder tests**

Create `backend/tests/test_prompt_builder.py`:

```python
from app.rag.prompt_builder import build_prompt
from app.rag.schemas import RetrievedChunk, SourceMetadata, TextChunk


def make_retrieved_chunk() -> RetrievedChunk:
    return RetrievedChunk(
        chunk=TextChunk(
            chunk_id="seed://items/black-king-bar#chunk-0",
            text="Black King Bar, often called BKB, grants timed spell immunity.",
            metadata=SourceMetadata(
                source_url="seed://items/black-king-bar",
                source_name="Seed: Black King Bar",
                patch_version="7.36",
                entity_type="item",
                entity_name="Black King Bar",
                updated_at="2026-06-18",
            ),
        ),
        score=0.9,
    )


def test_prompt_contains_answer_rules_and_context() -> None:
    prompt = build_prompt(
        question="BKB 有什么用?",
        question_type="knowledge",
        retrieved_chunks=[make_retrieved_chunk()],
    )

    assert "请用中文回答" in prompt
    assert "保留关键英文 Dota 2 术语" in prompt
    assert "Direct conclusion" in prompt
    assert "Black King Bar" in prompt
    assert "seed://items/black-king-bar" in prompt


def test_prompt_warns_when_question_is_advice() -> None:
    prompt = build_prompt(
        question="我应该出 BKB 吗?",
        question_type="advice",
        retrieved_chunks=[make_retrieved_chunk()],
    )

    assert "不要使用 must buy、always pick 这类绝对说法" in prompt
```

- [ ] **Step 2: Run prompt builder tests and verify RED**

Run:

```powershell
cd backend
$env:TEMP="$PWD\.tmp"; $env:TMP=$env:TEMP
.\.conda\python.exe -m pytest tests/test_prompt_builder.py -v -p no:cacheprovider --basetemp .tmp\pytest-m3-prompt
```

Expected: FAIL because `app.rag.prompt_builder` does not exist.

- [ ] **Step 3: Add prompt builder implementation**

Create `backend/app/rag/prompt_builder.py`:

```python
from app.rag.schemas import RetrievedChunk


def _format_chunk(index: int, retrieved: RetrievedChunk) -> str:
    metadata = retrieved.chunk.metadata
    return (
        f"[{index}] {metadata.source_name} | {metadata.source_url} | "
        f"entity={metadata.entity_name} | patch={metadata.patch_version or 'unknown'} | "
        f"updated_at={metadata.updated_at} | score={retrieved.score:.3f}\n"
        f"{retrieved.chunk.text}"
    )


def build_prompt(
    question: str,
    question_type: str,
    retrieved_chunks: list[RetrievedChunk],
) -> str:
    context = "\n\n".join(
        _format_chunk(index, chunk)
        for index, chunk in enumerate(retrieved_chunks, start=1)
    )
    advice_rule = ""
    if question_type == "advice":
        advice_rule = "\n- 不要使用 must buy、always pick 这类绝对说法；建议必须写成视局势而定。"

    return f"""你是一个 Dota 2 RAG 助手。请用中文回答，并保留关键英文 Dota 2 术语，例如 Black King Bar / BKB、Roshan、Blink Dagger。

问题类型: {question_type}

回答结构必须包含:
- Direct conclusion
- Key reasons
- Recommended actions or cautions
- Relevant English terms
- Sources and data freshness

规则:
- 只使用给定 context 支持的内容。
- 如果 context 不足，明确说“当前知识库没有覆盖这个问题”，不要猜测。
- 保留 source_name、source_url、updated_at 相关信息。{advice_rule}

context:
{context}

user question:
{question}
"""
```

- [ ] **Step 4: Run prompt builder tests and verify GREEN**

Run:

```powershell
cd backend
$env:TEMP="$PWD\.tmp"; $env:TMP=$env:TEMP
.\.conda\python.exe -m pytest tests/test_prompt_builder.py -v -p no:cacheprovider --basetemp .tmp\pytest-m3-prompt
```

Expected: PASS with 2 tests.

- [ ] **Step 5: Commit Task 2**

```powershell
git add backend/app/rag/prompt_builder.py backend/tests/test_prompt_builder.py
git commit -m "feat: build constrained rag prompts"
```

## Task 3: Ollama Chat Generator

**Files:**
- Create: `backend/app/rag/generator.py`
- Test: `backend/tests/test_generator.py`

- [ ] **Step 1: Write failing generator tests**

Create `backend/tests/test_generator.py`:

```python
import httpx
import pytest

from app.rag.generator import FakeGenerator, OllamaChatGenerator


@pytest.mark.asyncio
async def test_fake_generator_returns_configured_answer() -> None:
    generator = FakeGenerator("BKB 可以提供短时间 spell immunity。")

    assert await generator.generate("prompt") == "BKB 可以提供短时间 spell immunity。"


@pytest.mark.asyncio
async def test_ollama_chat_generator_reads_message_content() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/chat"
        payload = request.read().decode("utf-8")
        assert "dota2-rag" in payload
        return httpx.Response(200, json={"message": {"content": "Roshan 会掉 Aegis。"}})

    generator = OllamaChatGenerator(
        base_url="http://ollama.test",
        model="dota2-rag",
        transport=httpx.MockTransport(handler),
    )

    assert await generator.generate("prompt") == "Roshan 会掉 Aegis。"
```

- [ ] **Step 2: Run generator tests and verify RED**

Run:

```powershell
cd backend
$env:TEMP="$PWD\.tmp"; $env:TMP=$env:TEMP
.\.conda\python.exe -m pytest tests/test_generator.py -v -p no:cacheprovider --basetemp .tmp\pytest-m3-generator
```

Expected: FAIL because `app.rag.generator` does not exist.

- [ ] **Step 3: Add generator implementation**

Create `backend/app/rag/generator.py`:

```python
from typing import Optional, Protocol

import httpx


class Generator(Protocol):
    async def generate(self, prompt: str) -> str:
        ...


class FakeGenerator:
    def __init__(self, answer: str) -> None:
        self.answer = answer

    async def generate(self, prompt: str) -> str:
        return self.answer


class OllamaChatGenerator:
    def __init__(
        self,
        base_url: str,
        model: str = "qwen2.5:7b",
        transport: Optional[httpx.AsyncBaseTransport] = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.transport = transport

    async def generate(self, prompt: str) -> str:
        async with httpx.AsyncClient(
            base_url=self.base_url,
            timeout=60.0,
            transport=self.transport,
        ) as client:
            response = await client.post(
                "/api/chat",
                json={
                    "model": self.model,
                    "messages": [{"role": "user", "content": prompt}],
                    "stream": False,
                },
            )
            response.raise_for_status()
            payload = response.json()
        return str(payload["message"]["content"]).strip()
```

- [ ] **Step 4: Run generator tests and verify GREEN**

Run:

```powershell
cd backend
$env:TEMP="$PWD\.tmp"; $env:TMP=$env:TEMP
.\.conda\python.exe -m pytest tests/test_generator.py -v -p no:cacheprovider --basetemp .tmp\pytest-m3-generator
```

Expected: PASS with 2 tests.

- [ ] **Step 5: Commit Task 3**

```powershell
git add backend/app/rag/generator.py backend/tests/test_generator.py
git commit -m "feat: add ollama chat generator"
```

## Task 4: Chat Service Orchestration

**Files:**
- Create: `backend/app/rag/chat_service.py`
- Test: `backend/tests/test_chat_service.py`

- [ ] **Step 1: Write failing chat service tests**

Create `backend/tests/test_chat_service.py`:

```python
import pytest

from app.data_sources.seed_documents import load_seed_documents
from app.jobs.ingest_documents import ingest_seed_documents
from app.rag.chat_service import ChatService
from app.rag.embeddings import DeterministicEmbedder
from app.rag.generator import FakeGenerator
from app.vector_store.milvus import LocalVectorStore


@pytest.mark.asyncio
async def test_chat_service_answers_with_sources(tmp_path) -> None:
    store = LocalVectorStore(tmp_path / "vectors.json")
    embedder = DeterministicEmbedder(dimensions=64)
    ingest_seed_documents(store=store, embedder=embedder)
    service = ChatService(
        store=store,
        embedder=embedder,
        generator=FakeGenerator("BKB 可以提供短时间 spell immunity，用来抵抗很多控制。"),
    )

    response = await service.answer("BKB 有什么用?")

    assert response.question_type == "knowledge"
    assert "BKB" in response.answer
    assert response.sources[0].source_name == "Seed: Black King Bar"
    assert response.debug.retrieved_chunks >= 1


@pytest.mark.asyncio
async def test_chat_service_returns_uncertainty_when_retrieval_is_insufficient(tmp_path) -> None:
    store = LocalVectorStore(tmp_path / "vectors.json")
    embedder = DeterministicEmbedder(dimensions=64)
    service = ChatService(
        store=store,
        embedder=embedder,
        generator=FakeGenerator("this should not be used"),
    )

    response = await service.answer("Chen 的神杖效果是什么?")

    assert response.answer == "当前知识库没有覆盖这个问题，无法基于已索引来源可靠回答。"
    assert response.sources == []
    assert response.debug.retrieved_chunks == 0
```

- [ ] **Step 2: Run chat service tests and verify RED**

Run:

```powershell
cd backend
$env:TEMP="$PWD\.tmp"; $env:TMP=$env:TEMP
.\.conda\python.exe -m pytest tests/test_chat_service.py -v -p no:cacheprovider --basetemp .tmp\pytest-m3-chat-service
```

Expected: FAIL because `app.rag.chat_service` does not exist.

- [ ] **Step 3: Add chat response models and service**

Create `backend/app/rag/chat_service.py`:

```python
from pydantic import BaseModel

from app.rag.classifier import classify_question
from app.rag.embeddings import Embedder
from app.rag.generator import Generator
from app.rag.prompt_builder import build_prompt
from app.rag.schemas import RetrievedChunk
from app.vector_store.milvus import LocalVectorStore


UNCERTAINTY_ANSWER = "当前知识库没有覆盖这个问题，无法基于已索引来源可靠回答。"


class SourceCitation(BaseModel):
    source_name: str
    source_url: str
    entity_name: str
    entity_type: str
    patch_version: str | None
    updated_at: str
    score: float


class ChatDebug(BaseModel):
    retrieved_chunks: int
    top_score: float | None


class ChatAnswer(BaseModel):
    answer: str
    question_type: str
    sources: list[SourceCitation]
    debug: ChatDebug


def _sources_from_chunks(chunks: list[RetrievedChunk]) -> list[SourceCitation]:
    citations: list[SourceCitation] = []
    seen: set[str] = set()
    for retrieved in chunks:
        metadata = retrieved.chunk.metadata
        key = metadata.source_url
        if key in seen:
            continue
        seen.add(key)
        citations.append(
            SourceCitation(
                source_name=metadata.source_name,
                source_url=metadata.source_url,
                entity_name=metadata.entity_name,
                entity_type=metadata.entity_type,
                patch_version=metadata.patch_version,
                updated_at=metadata.updated_at,
                score=retrieved.score,
            )
        )
    return citations


class ChatService:
    def __init__(
        self,
        store: LocalVectorStore,
        embedder: Embedder,
        generator: Generator,
        retrieval_limit: int = 4,
        minimum_score: float = 0.05,
    ) -> None:
        self.store = store
        self.embedder = embedder
        self.generator = generator
        self.retrieval_limit = retrieval_limit
        self.minimum_score = minimum_score

    async def answer(self, question: str) -> ChatAnswer:
        question_type = classify_question(question)
        retrieved = self.store.search(self.embedder.embed(question), limit=self.retrieval_limit)
        supported = [item for item in retrieved if item.score >= self.minimum_score]
        top_score = supported[0].score if supported else None
        debug = ChatDebug(retrieved_chunks=len(supported), top_score=top_score)

        if not supported:
            return ChatAnswer(
                answer=UNCERTAINTY_ANSWER,
                question_type=question_type,
                sources=[],
                debug=debug,
            )

        prompt = build_prompt(
            question=question,
            question_type=question_type,
            retrieved_chunks=supported,
        )
        answer = await self.generator.generate(prompt)
        return ChatAnswer(
            answer=answer,
            question_type=question_type,
            sources=_sources_from_chunks(supported),
            debug=debug,
        )
```

- [ ] **Step 4: Run chat service tests and verify GREEN**

Run:

```powershell
cd backend
$env:TEMP="$PWD\.tmp"; $env:TMP=$env:TEMP
.\.conda\python.exe -m pytest tests/test_chat_service.py -v -p no:cacheprovider --basetemp .tmp\pytest-m3-chat-service
```

Expected: PASS with 2 tests.

- [ ] **Step 5: Commit Task 4**

```powershell
git add backend/app/rag/chat_service.py backend/tests/test_chat_service.py
git commit -m "feat: orchestrate rag chat answers"
```

## Task 5: Chat API Endpoint

**Files:**
- Create: `backend/app/api/chat.py`
- Modify: `backend/app/core/config.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_chat_api.py`

- [ ] **Step 1: Write failing chat API tests**

Create `backend/tests/test_chat_api.py`:

```python
from pathlib import Path

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
from app.rag.generator import FakeGenerator


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
```

- [ ] **Step 2: Run chat API tests and verify RED**

Run:

```powershell
cd backend
$env:TEMP="$PWD\.tmp"; $env:TMP=$env:TEMP
.\.conda\python.exe -m pytest tests/test_chat_api.py -v -p no:cacheprovider --basetemp .tmp\pytest-m3-chat-api
```

Expected: FAIL with 404 because `/api/chat` is not registered.

- [ ] **Step 3: Add chat model setting**

Modify `backend/app/core/config.py` to include:

```python
    ollama_chat_model: str = "qwen2.5:7b"
```

Place it below `ollama_base_url`.

- [ ] **Step 4: Add chat API router and register it**

Create `backend/app/api/chat.py`:

```python
from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

from app.rag.chat_service import ChatAnswer, ChatService
from app.rag.embeddings import DeterministicEmbedder
from app.rag.generator import OllamaChatGenerator
from app.vector_store.milvus import LocalVectorStore

router = APIRouter(prefix="/api", tags=["chat"])


class ChatRequest(BaseModel):
    message: str = Field(min_length=1)


def _generator_for_request(request: Request):
    override = getattr(request.app.state, "generator_override", None)
    if override is not None:
        return override
    settings = request.app.state.settings
    return OllamaChatGenerator(
        base_url=str(settings.ollama_base_url),
        model=settings.ollama_chat_model,
    )


@router.post("/chat", response_model=ChatAnswer)
async def chat(payload: ChatRequest, request: Request) -> ChatAnswer:
    settings = request.app.state.settings
    service = ChatService(
        store=LocalVectorStore(settings.vector_index_path),
        embedder=DeterministicEmbedder(dimensions=64),
        generator=_generator_for_request(request),
    )
    return await service.answer(payload.message)
```

Modify `backend/app/main.py`:

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.chat import router as chat_router
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
    app.include_router(chat_router)
    return app


app = create_app()
```

- [ ] **Step 5: Run chat API tests and verify GREEN**

Run:

```powershell
cd backend
$env:TEMP="$PWD\.tmp"; $env:TMP=$env:TEMP
.\.conda\python.exe -m pytest tests/test_chat_api.py -v -p no:cacheprovider --basetemp .tmp\pytest-m3-chat-api
```

Expected: PASS with 2 tests.

- [ ] **Step 6: Commit Task 5**

```powershell
git add backend/app/api/chat.py backend/app/main.py backend/app/core/config.py backend/tests/test_chat_api.py
git commit -m "feat: expose rag chat API"
```

## Task 6: M3 Documentation And Verification

**Files:**
- Modify: `README.md`
- Test: full backend suite, frontend tests/build, chat endpoint smoke checks

- [ ] **Step 1: Update README with chat commands**

Append to `README.md`:

```markdown
## M3 Basic RAG Chat

Seed the local index before asking questions:

```powershell
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/api/ingest/documents
```

Ask a question:

```powershell
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/api/chat -ContentType "application/json" -Body '{"message":"BKB 有什么用?"}'
```

M3 returns `answer`, `question_type`, `sources`, and `debug`. Runtime generation uses `OLLAMA_BASE_URL` and `OLLAMA_CHAT_MODEL`; if the indexed sources do not cover a question, the assistant returns an explicit uncertainty answer instead of guessing.
```

- [ ] **Step 2: Run all backend tests**

Run:

```powershell
cd backend
$env:TEMP="$PWD\.tmp"; $env:TMP=$env:TEMP
.\.conda\python.exe -m pytest -v -p no:cacheprovider --basetemp .tmp\pytest-m3-final
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

- [ ] **Step 4: Restart backend to load chat route**

If a backend process is already listening on port 8000, stop it and start:

```powershell
cd backend
.\.conda\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Expected: OpenAPI includes `/api/health`, `/api/ingest/documents`, `/api/sources`, and `/api/chat`.

- [ ] **Step 5: Smoke-test chat endpoint**

Run:

```powershell
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/api/ingest/documents
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/api/chat -ContentType "application/json" -Body '{"message":"BKB 有什么用?"}'
```

Expected: response includes a non-empty `answer`, `question_type` equals `knowledge`, and `sources` includes `Seed: Black King Bar`.

- [ ] **Step 6: Commit Task 6**

```powershell
git add README.md
git commit -m "docs: add m3 chat instructions"
```

## Self-Review

- Spec coverage: This plan implements M3 question classification, vector retrieval, prompt assembly, Ollama generation, source return, and explicit uncertainty for missing coverage.
- Deferred scope: Structured stats, OpenDota refresh, and frontend chat UI remain M4-M5.
- Runtime caveat: M3 uses the deterministic M2 vector index for retrieval while adding an Ollama chat generator for answer generation. Pulling a specific Ollama model is an operational step documented by `OLLAMA_CHAT_MODEL`.
- Placeholder scan: No placeholder tasks remain; each test and implementation step includes concrete code.
- Type consistency: `ChatAnswer`, `SourceCitation`, `ChatDebug`, `ChatRequest`, `Generator`, and classifier category strings are introduced before use.
