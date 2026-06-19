# M8 Answer Quality Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Improve demo answer quality by adding deterministic Dota 2 alias normalization, stronger question classification, canonical stats lookup, clearer prompts, and golden-question tests.

**Architecture:** Add a focused alias registry in `backend/app/rag/aliases.py`, then thread normalized query data through classification, retrieval, stats lookup, and prompt construction. Keep the UI unchanged and preserve the existing chat API response shape.

**Tech Stack:** Python 3.11, FastAPI backend, pytest, SQLite repository tests, existing deterministic embedder/vector store test helpers.

---

## File Structure

- Create `backend/app/rag/aliases.py`: canonical alias registry and `normalize_question()` helper.
- Create `backend/tests/test_aliases.py`: unit tests for alias matching and query expansion.
- Modify `backend/app/rag/classifier.py`: classify using normalized expanded text.
- Modify `backend/tests/test_classifier.py`: cover mixed Chinese/English/slang routes.
- Modify `backend/app/rag/prompt_builder.py`: accept optional canonical term hints and enforce the answer section contract.
- Modify `backend/tests/test_prompt_builder.py`: assert five section names, canonical hints, and advice guardrails.
- Modify `backend/app/rag/chat_service.py`: normalize once, use expanded text for embeddings, canonical hero for stats lookup, original text for prompts.
- Modify `backend/tests/test_chat_service.py`: cover Chinese hero alias stats and expanded retrieval input behavior.
- Create `backend/tests/test_golden_questions.py`: parameterized demo-question routing and answer-property tests.

## Task 1: Alias Registry

**Files:**
- Create: `backend/app/rag/aliases.py`
- Test: `backend/tests/test_aliases.py`

- [ ] **Step 1: Write the failing alias tests**

Create `backend/tests/test_aliases.py`:

```python
from app.rag.aliases import normalize_question


def test_normalizes_black_king_bar_aliases() -> None:
    normalized = normalize_question("黑皇杖有什么用？")

    assert normalized.original == "黑皇杖有什么用？"
    assert "Black King Bar" in normalized.expanded
    assert "BKB" in normalized.expanded
    assert "Black King Bar / BKB" in normalized.canonical_terms


def test_normalizes_roshan_aliases() -> None:
    normalized = normalize_question("肉山掉什么？")

    assert "Roshan" in normalized.expanded
    assert normalized.canonical_terms == ["Roshan"]


def test_normalizes_axe_hero_aliases() -> None:
    normalized = normalize_question("斧王胜率")

    assert normalized.canonical_hero == "Axe"
    assert "Axe" in normalized.expanded
    assert "Axe" in normalized.canonical_terms


def test_normalizes_blink_dagger_aliases() -> None:
    normalized = normalize_question("跳刀怎么用？")

    assert "Blink Dagger" in normalized.expanded
    assert normalized.canonical_terms == ["Blink Dagger"]


def test_deduplicates_terms_when_question_already_uses_canonical_name() -> None:
    normalized = normalize_question("What does BKB do?")

    assert normalized.expanded.count("BKB") == 1
    assert normalized.canonical_terms == ["Black King Bar / BKB"]
```

- [ ] **Step 2: Run the test to verify it fails**

Run from `backend/`:

```powershell
$env:TEMP='C:\Users\jaime\OneDrive\Desktop\dota2-rag-assistant\backend\.tmp'; $env:TMP=$env:TEMP; .\.conda\python.exe -m pytest tests/test_aliases.py -v -p no:cacheprovider --basetemp .tmp\pytest-m8-aliases
```

Expected: FAIL with `ModuleNotFoundError: No module named 'app.rag.aliases'`.

- [ ] **Step 3: Implement the alias registry**

Create `backend/app/rag/aliases.py`:

```python
from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class AliasEntry:
    canonical: str
    aliases: tuple[str, ...]
    expansion: tuple[str, ...]
    entity_type: str


@dataclass(frozen=True)
class NormalizedQuestion:
    original: str
    expanded: str
    canonical_terms: list[str]
    canonical_hero: str | None = None


ALIAS_ENTRIES: tuple[AliasEntry, ...] = (
    AliasEntry(
        canonical="Axe",
        aliases=("axe", "斧王"),
        expansion=("Axe",),
        entity_type="hero",
    ),
    AliasEntry(
        canonical="Black King Bar / BKB",
        aliases=("bkb", "black king bar", "黑皇杖"),
        expansion=("Black King Bar", "BKB"),
        entity_type="item",
    ),
    AliasEntry(
        canonical="Blink Dagger",
        aliases=("blink dagger", "跳刀"),
        expansion=("Blink Dagger",),
        entity_type="item",
    ),
    AliasEntry(
        canonical="Roshan",
        aliases=("roshan", "肉山"),
        expansion=("Roshan",),
        entity_type="objective",
    ),
)


def _matches_alias(question: str, alias: str) -> bool:
    if alias.isascii() and alias.replace(" ", "").isalnum():
        return re.search(rf"\b{re.escape(alias)}\b", question, flags=re.IGNORECASE) is not None
    return alias.lower() in question.lower()


def _append_missing(parts: list[str], value: str) -> None:
    if not any(existing.lower() == value.lower() for existing in parts):
        parts.append(value)


def normalize_question(question: str) -> NormalizedQuestion:
    parts = [question]
    canonical_terms: list[str] = []
    canonical_hero: str | None = None

    for entry in ALIAS_ENTRIES:
        if not any(_matches_alias(question, alias) for alias in entry.aliases):
            continue

        _append_missing(canonical_terms, entry.canonical)
        for term in entry.expansion:
            if not _matches_alias(" ".join(parts), term):
                parts.append(term)
        if entry.entity_type == "hero":
            canonical_hero = entry.canonical

    return NormalizedQuestion(
        original=question,
        expanded=" ".join(parts),
        canonical_terms=canonical_terms,
        canonical_hero=canonical_hero,
    )
```

- [ ] **Step 4: Run the alias tests**

Run from `backend/`:

```powershell
$env:TEMP='C:\Users\jaime\OneDrive\Desktop\dota2-rag-assistant\backend\.tmp'; $env:TMP=$env:TEMP; .\.conda\python.exe -m pytest tests/test_aliases.py -v -p no:cacheprovider --basetemp .tmp\pytest-m8-aliases
```

Expected: all tests PASS.

- [ ] **Step 5: Commit**

```powershell
git add backend/app/rag/aliases.py backend/tests/test_aliases.py
git commit -m "feat: add dota alias normalization"
```

## Task 2: Classification Uses Normalized Questions

**Files:**
- Modify: `backend/app/rag/classifier.py`
- Modify: `backend/tests/test_classifier.py`

- [ ] **Step 1: Add failing classification tests**

Append these tests to `backend/tests/test_classifier.py`:

```python
def test_classifies_chinese_hero_alias_stats_question() -> None:
    assert classify_question("斧王胜率") == "stats"


def test_classifies_mixed_english_stats_question() -> None:
    assert classify_question("Axe win rate meta") == "stats"


def test_classifies_chinese_item_advice_question() -> None:
    assert classify_question("跳刀怎么用？") == "advice"


def test_classifies_roshan_drop_question_as_knowledge() -> None:
    assert classify_question("肉山掉什么？") == "knowledge"
```

- [ ] **Step 2: Run classifier tests to verify failures**

Run from `backend/`:

```powershell
$env:TEMP='C:\Users\jaime\OneDrive\Desktop\dota2-rag-assistant\backend\.tmp'; $env:TMP=$env:TEMP; .\.conda\python.exe -m pytest tests/test_classifier.py -v -p no:cacheprovider --basetemp .tmp\pytest-m8-classifier
```

Expected: FAIL for the new Chinese alias cases that are not currently recognized.

- [ ] **Step 3: Update classifier implementation**

Replace `backend/app/rag/classifier.py` with:

```python
from app.rag.aliases import normalize_question

QuestionType = str


PATCH_TERMS = ("patch", "版本", "改动", "更新", "7.")
STATS_TERMS = ("胜率", "win rate", "pick rate", "ban rate", "登场率", "数据", "meta", "热门")
ADVICE_TERMS = ("应该", "怎么用", "怎么出", "建议", "克制", "counter", "对线", "团战")


def _contains_any(question: str, terms: tuple[str, ...]) -> bool:
    lowered = question.lower()
    return any(term.lower() in lowered for term in terms)


def classify_question(question: str) -> QuestionType:
    normalized = normalize_question(question)
    candidate = normalized.expanded
    if _contains_any(candidate, PATCH_TERMS):
        return "patch"
    if _contains_any(candidate, STATS_TERMS):
        return "stats"
    if _contains_any(candidate, ADVICE_TERMS):
        return "advice"
    return "knowledge"
```

- [ ] **Step 4: Run classifier and alias tests**

Run from `backend/`:

```powershell
$env:TEMP='C:\Users\jaime\OneDrive\Desktop\dota2-rag-assistant\backend\.tmp'; $env:TMP=$env:TEMP; .\.conda\python.exe -m pytest tests/test_aliases.py tests/test_classifier.py -v -p no:cacheprovider --basetemp .tmp\pytest-m8-classifier
```

Expected: all selected tests PASS.

- [ ] **Step 5: Commit**

```powershell
git add backend/app/rag/classifier.py backend/tests/test_classifier.py
git commit -m "feat: classify normalized dota questions"
```

## Task 3: Prompt Contract And Canonical Hints

**Files:**
- Modify: `backend/app/rag/prompt_builder.py`
- Modify: `backend/tests/test_prompt_builder.py`

- [ ] **Step 1: Add failing prompt tests**

Modify `backend/tests/test_prompt_builder.py` so `test_prompt_contains_answer_rules_and_context` also checks the Chinese section names:

```python
    assert "直接结论" in prompt
    assert "关键原因" in prompt
    assert "建议/注意" in prompt
    assert "相关术语" in prompt
    assert "来源/数据新鲜度" in prompt
```

Add this new test:

```python
def test_prompt_includes_canonical_term_hints() -> None:
    prompt = build_prompt(
        question="黑皇杖有什么用？",
        question_type="knowledge",
        retrieved_chunks=[make_retrieved_chunk()],
        canonical_terms=["Black King Bar / BKB"],
    )

    assert "Canonical terms detected: Black King Bar / BKB" in prompt
```

- [ ] **Step 2: Run prompt tests to verify failures**

Run from `backend/`:

```powershell
$env:TEMP='C:\Users\jaime\OneDrive\Desktop\dota2-rag-assistant\backend\.tmp'; $env:TMP=$env:TEMP; .\.conda\python.exe -m pytest tests/test_prompt_builder.py -v -p no:cacheprovider --basetemp .tmp\pytest-m8-prompt
```

Expected: FAIL because `build_prompt()` does not accept `canonical_terms` yet and does not include the exact Chinese section names.

- [ ] **Step 3: Update prompt builder**

Replace `backend/app/rag/prompt_builder.py` with:

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
    canonical_terms: list[str] | None = None,
) -> str:
    context = "\n\n".join(
        _format_chunk(index, chunk)
        for index, chunk in enumerate(retrieved_chunks, start=1)
    )
    term_hint = ""
    if canonical_terms:
        term_hint = f"\nCanonical terms detected: {', '.join(canonical_terms)}\n"

    advice_rule = ""
    if question_type == "advice":
        advice_rule = "\n- 不要使用 must buy、always pick 这类绝对说法；建议必须写成视局势而定。"

    return f"""你是一个 Dota 2 RAG 助手。请用中文回答，并保留关键英文 Dota 2 术语，例如 Black King Bar / BKB、Roshan、Blink Dagger。
问题类型: {question_type}{term_hint}

回答结构必须包含:
- 直接结论
- 关键原因
- 建议/注意
- 相关术语
- 来源/数据新鲜度

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

- [ ] **Step 4: Run prompt tests**

Run from `backend/`:

```powershell
$env:TEMP='C:\Users\jaime\OneDrive\Desktop\dota2-rag-assistant\backend\.tmp'; $env:TMP=$env:TEMP; .\.conda\python.exe -m pytest tests/test_prompt_builder.py -v -p no:cacheprovider --basetemp .tmp\pytest-m8-prompt
```

Expected: all prompt tests PASS.

- [ ] **Step 5: Commit**

```powershell
git add backend/app/rag/prompt_builder.py backend/tests/test_prompt_builder.py
git commit -m "feat: clarify rag answer prompt contract"
```

## Task 4: Chat Service Normalization And Stats Lookup

**Files:**
- Modify: `backend/app/rag/chat_service.py`
- Modify: `backend/tests/test_chat_service.py`

- [ ] **Step 1: Add failing chat-service tests**

Append these tests to `backend/tests/test_chat_service.py`:

```python
@pytest.mark.asyncio
async def test_chat_service_answers_chinese_hero_alias_stats_question(tmp_path) -> None:
    store = LocalVectorStore(tmp_path / "vectors.json")
    embedder = DeterministicEmbedder(dimensions=64)
    service = ChatService(
        store=store,
        embedder=embedder,
        generator=FakeGenerator("this should not be used"),
        stats_repository=stats_repository(tmp_path),
    )

    response = await service.answer("斧王胜率")

    assert response.question_type == "stats"
    assert response.debug.stats_used is True
    assert "Axe" in response.answer
    assert "52.0%" in response.answer


class RecordingEmbedder(DeterministicEmbedder):
    def __init__(self) -> None:
        super().__init__(dimensions=64)
        self.last_text: str | None = None

    def embed(self, text: str) -> list[float]:
        self.last_text = text
        return super().embed(text)


@pytest.mark.asyncio
async def test_chat_service_uses_expanded_text_for_retrieval(tmp_path) -> None:
    store = LocalVectorStore(tmp_path / "vectors.json")
    embedder = RecordingEmbedder()
    ingest_seed_documents(store=store, embedder=embedder)
    service = ChatService(
        store=store,
        embedder=embedder,
        generator=FakeGenerator("Black King Bar answer"),
    )

    await service.answer("黑皇杖有什么用？")

    assert embedder.last_text is not None
    assert "黑皇杖有什么用？" in embedder.last_text
    assert "Black King Bar" in embedder.last_text
    assert "BKB" in embedder.last_text
```

- [ ] **Step 2: Run chat-service tests to verify failure**

Run from `backend/`:

```powershell
$env:TEMP='C:\Users\jaime\OneDrive\Desktop\dota2-rag-assistant\backend\.tmp'; $env:TMP=$env:TEMP; .\.conda\python.exe -m pytest tests/test_chat_service.py -v -p no:cacheprovider --basetemp .tmp\pytest-m8-chat
```

Expected: FAIL because `斧王` does not resolve to `Axe` stats and retrieval still embeds the raw question.

- [ ] **Step 3: Wire normalization into chat service**

Modify `backend/app/rag/chat_service.py`:

```python
from app.rag.aliases import normalize_question
```

Then update `answer()`:

```python
    async def answer(self, question: str) -> ChatAnswer:
        normalized = normalize_question(question)
        question_type = classify_question(normalized.expanded)
        if question_type == "stats" and self.stats_repository is not None:
            stats_answer = self._answer_stats_question(normalized.expanded, normalized.canonical_hero)
            if stats_answer is not None:
                return stats_answer

        retrieved = self.store.search(self.embedder.embed(normalized.expanded), limit=self.retrieval_limit)
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
            question=normalized.original,
            question_type=question_type,
            retrieved_chunks=supported,
            canonical_terms=normalized.canonical_terms,
        )
        answer = await self.generator.generate(prompt)
        return ChatAnswer(
            answer=answer,
            question_type=question_type,
            sources=_sources_from_chunks(supported),
            debug=debug,
        )
```

Update `_answer_stats_question()` signature and first lookup:

```python
    def _answer_stats_question(self, question: str, canonical_hero: str | None = None) -> ChatAnswer | None:
        if self.stats_repository is None:
            return None

        hero = self.stats_repository.find_hero(canonical_hero or question)
```

- [ ] **Step 4: Run selected backend tests**

Run from `backend/`:

```powershell
$env:TEMP='C:\Users\jaime\OneDrive\Desktop\dota2-rag-assistant\backend\.tmp'; $env:TMP=$env:TEMP; .\.conda\python.exe -m pytest tests/test_aliases.py tests/test_classifier.py tests/test_prompt_builder.py tests/test_chat_service.py -v -p no:cacheprovider --basetemp .tmp\pytest-m8-chat
```

Expected: all selected tests PASS.

- [ ] **Step 5: Commit**

```powershell
git add backend/app/rag/chat_service.py backend/tests/test_chat_service.py
git commit -m "feat: use aliases in chat answers"
```

## Task 5: Golden Questions

**Files:**
- Create: `backend/tests/test_golden_questions.py`

- [ ] **Step 1: Add golden-question tests**

Create `backend/tests/test_golden_questions.py`:

```python
import pytest

from app.data_sources.opendota import OpenDotaHeroStatsRecord
from app.db.repositories import HeroStatsRepository
from app.db.session import create_sqlite_engine
from app.jobs.ingest_documents import ingest_seed_documents
from app.rag.chat_service import ChatService
from app.rag.classifier import classify_question
from app.rag.embeddings import DeterministicEmbedder
from app.rag.generator import FakeGenerator
from app.vector_store.milvus import LocalVectorStore


@pytest.mark.parametrize(
    ("question", "expected_type"),
    [
        ("BKB有什么用？", "knowledge"),
        ("What does BKB do?", "knowledge"),
        ("黑皇杖什么时候出？", "advice"),
        ("Roshan 会掉什么？", "knowledge"),
        ("肉山掉什么？", "knowledge"),
        ("Axe win rate meta", "stats"),
        ("斧王胜率", "stats"),
        ("Blink Dagger怎么用？", "advice"),
        ("跳刀怎么用？", "advice"),
    ],
)
def test_golden_question_routes(question: str, expected_type: str) -> None:
    assert classify_question(question) == expected_type


def make_stats_repository(tmp_path) -> HeroStatsRepository:
    repo = HeroStatsRepository(create_sqlite_engine(tmp_path / "sqlite" / "dota2_rag.db"))
    repo.upsert_hero_stats(
        [
            OpenDotaHeroStatsRecord(
                hero_id=2,
                name="npc_dota_hero_axe",
                localized_name="Axe",
                primary_attr="str",
                roles=["Initiator"],
                public_pick_count=1000,
                public_win_count=520,
                public_win_rate=0.52,
                public_pick_share=0.25,
                pro_pick_count=22,
                pro_win_count=7,
                pro_ban_count=36,
                refreshed_at="2026-06-19T09:00:00Z",
            )
        ]
    )
    return repo


@pytest.mark.asyncio
async def test_golden_stats_alias_answer_uses_local_stats(tmp_path) -> None:
    service = ChatService(
        store=LocalVectorStore(tmp_path / "vectors.json"),
        embedder=DeterministicEmbedder(dimensions=64),
        generator=FakeGenerator("this should not be used"),
        stats_repository=make_stats_repository(tmp_path),
    )

    response = await service.answer("斧王胜率")

    assert response.question_type == "stats"
    assert response.debug.stats_used is True
    assert "Axe" in response.answer
    assert "52.0%" in response.answer
    assert "2026-06-19T09:00:00Z" in response.answer


@pytest.mark.asyncio
async def test_golden_bkb_alias_answer_keeps_sources(tmp_path) -> None:
    store = LocalVectorStore(tmp_path / "vectors.json")
    embedder = DeterministicEmbedder(dimensions=64)
    ingest_seed_documents(store=store, embedder=embedder)
    service = ChatService(
        store=store,
        embedder=embedder,
        generator=FakeGenerator("直接结论: Black King Bar / BKB helps against many spells."),
    )

    response = await service.answer("黑皇杖有什么用？")

    assert response.question_type == "knowledge"
    assert "Black King Bar" in response.answer
    assert response.sources
```

- [ ] **Step 2: Run golden tests**

Run from `backend/`:

```powershell
$env:TEMP='C:\Users\jaime\OneDrive\Desktop\dota2-rag-assistant\backend\.tmp'; $env:TMP=$env:TEMP; .\.conda\python.exe -m pytest tests/test_golden_questions.py -v -p no:cacheprovider --basetemp .tmp\pytest-m8-golden
```

Expected: all golden tests PASS.

- [ ] **Step 3: Commit**

```powershell
git add backend/tests/test_golden_questions.py
git commit -m "test: add m8 golden questions"
```

## Task 6: Full Verification

**Files:**
- No expected source changes.

- [ ] **Step 1: Run the full backend test suite**

Run from `backend/`:

```powershell
$env:TEMP='C:\Users\jaime\OneDrive\Desktop\dota2-rag-assistant\backend\.tmp'; $env:TMP=$env:TEMP; .\.conda\python.exe -m pytest -v -p no:cacheprovider --basetemp .tmp\pytest-m8-final
```

Expected: all backend tests PASS. A Starlette deprecation warning is acceptable if it is the existing warning.

- [ ] **Step 2: Run frontend tests**

Run from `frontend/`:

```powershell
npm test
```

Expected: all frontend tests PASS.

- [ ] **Step 3: Run frontend build**

Run from `frontend/`:

```powershell
npm run build
```

Expected: Vite build succeeds and produces `dist/`.

- [ ] **Step 4: Inspect git status**

Run from repo root:

```powershell
git status --short --branch
```

Expected: only intended M8 files are changed or committed. Existing untracked `.vscode/` may remain and should not be staged.

- [ ] **Step 5: Final M8 commit if verification required a small fix**

Only if a verification fix was needed:

```powershell
git add backend/app/rag backend/tests
git commit -m "fix: stabilize m8 answer quality"
```

## Self-Review

- Spec coverage: alias normalization, classification, retrieval expansion, stats lookup, prompt contract, golden questions, and full verification are each covered by a task.
- Scope check: no new data sources, no item trends, no frontend UI expansion.
- Type consistency: `NormalizedQuestion.original`, `expanded`, `canonical_terms`, and `canonical_hero` are introduced in Task 1 and used consistently later.
- Execution style: each implementation task starts with failing tests and ends with verification plus a commit.
