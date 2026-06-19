# M9 Demo Acceptance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a deterministic demo acceptance suite and manual browser checklist so the local Dota 2 RAG assistant can be validated against realistic demo questions.

**Architecture:** Keep M9 mostly in tests and docs. Add a reusable backend acceptance case fixture, use existing `ChatService` test doubles for stable assertions, make only narrow classifier/prompt/alias fixes when an acceptance case exposes a gap, and document browser smoke-test steps without expanding the UI or data sources.

**Tech Stack:** Python 3.11+/pytest backend tests, existing deterministic embedder/local vector store/fake generator helpers, React/Vite frontend verification, Markdown docs.

---

## File Structure

- Create `backend/tests/fixtures/demo_acceptance.py`: reusable demo acceptance cases and helpers.
- Create `backend/tests/test_demo_acceptance.py`: deterministic backend acceptance tests for route, source, stats, patch, and missing-coverage behavior.
- Modify `backend/app/rag/classifier.py`: only if M9 cases expose missing patch/advice signals.
- Modify `backend/app/rag/prompt_builder.py`: only if M9 cases expose missing prompt contract language.
- Create `docs/demo-checklist.md`: manual browser demo checklist for local verification.

## Task 1: Demo Acceptance Fixture

**Files:**
- Create: `backend/tests/fixtures/demo_acceptance.py`
- Test: `backend/tests/test_demo_acceptance.py`

- [ ] **Step 1: Write the failing fixture import test**

Create `backend/tests/test_demo_acceptance.py`:

```python
from tests.fixtures.demo_acceptance import DEMO_ACCEPTANCE_CASES, DemoAcceptanceCase


def test_demo_acceptance_cases_cover_required_question_types() -> None:
    question_types = {case.expected_type for case in DEMO_ACCEPTANCE_CASES}

    assert question_types == {"knowledge", "advice", "stats", "patch", "knowledge_missing"}


def test_demo_acceptance_cases_are_readable_contracts() -> None:
    for case in DEMO_ACCEPTANCE_CASES:
        assert isinstance(case, DemoAcceptanceCase)
        assert case.question
        assert case.expected_type
        assert not (case.requires_sources and case.allows_missing_coverage)
```

- [ ] **Step 2: Run the test to verify it fails**

Run from `backend/` using the project test environment:

```powershell
C:\WINDOWS\System32\WindowsPowerShell\v1.0\powershell.exe -Command "`$env:TEMP='C:\Users\jaime\OneDrive\Desktop\dota2-rag-assistant\backend\.tmp'; `$env:TMP=`$env:TEMP; `$env:PYTHONPATH='C:\Users\jaime\OneDrive\Desktop\dota2-rag-assistant\backend\.tmp\py312-packages;C:\Users\jaime\OneDrive\Desktop\dota2-rag-assistant\backend'; C:\Users\jaime\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -m pytest tests/test_demo_acceptance.py -v -p no:cacheprovider --basetemp .tmp\pytest-m9-fixture"
```

Expected: FAIL with `ModuleNotFoundError: No module named 'tests.fixtures.demo_acceptance'`.

- [ ] **Step 3: Add the demo acceptance fixture**

Create `backend/tests/fixtures/demo_acceptance.py`:

```python
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DemoAcceptanceCase:
    question: str
    expected_type: str
    expected_terms: tuple[str, ...] = ()
    requires_sources: bool = False
    requires_stats: bool = False
    allows_missing_coverage: bool = False


DEMO_ACCEPTANCE_CASES: tuple[DemoAcceptanceCase, ...] = (
    DemoAcceptanceCase(
        question="BKB有什么用？",
        expected_type="knowledge",
        expected_terms=("Black King Bar", "BKB"),
        requires_sources=True,
    ),
    DemoAcceptanceCase(
        question="What does BKB do?",
        expected_type="knowledge",
        expected_terms=("Black King Bar", "BKB"),
        requires_sources=True,
    ),
    DemoAcceptanceCase(
        question="Roshan 会掉什么？",
        expected_type="knowledge",
        expected_terms=("Roshan",),
        requires_sources=True,
    ),
    DemoAcceptanceCase(
        question="肉山掉什么？",
        expected_type="knowledge",
        expected_terms=("Roshan",),
        requires_sources=True,
    ),
    DemoAcceptanceCase(
        question="黑皇杖什么时候出？",
        expected_type="advice",
        expected_terms=("Black King Bar", "BKB"),
        requires_sources=True,
    ),
    DemoAcceptanceCase(
        question="Blink Dagger怎么用？",
        expected_type="advice",
        expected_terms=("Blink Dagger",),
        requires_sources=True,
    ),
    DemoAcceptanceCase(
        question="跳刀怎么用？",
        expected_type="advice",
        expected_terms=("Blink Dagger",),
        requires_sources=True,
    ),
    DemoAcceptanceCase(
        question="Axe win rate meta",
        expected_type="stats",
        expected_terms=("Axe", "52.0%", "25.0%"),
        requires_stats=True,
    ),
    DemoAcceptanceCase(
        question="斧王胜率",
        expected_type="stats",
        expected_terms=("Axe", "52.0%"),
        requires_stats=True,
    ),
    DemoAcceptanceCase(
        question="7.36 BKB 改了什么？",
        expected_type="patch",
        expected_terms=("Black King Bar", "BKB"),
        requires_sources=True,
    ),
    DemoAcceptanceCase(
        question="最近版本 Roshan 有什么变化？",
        expected_type="patch",
        expected_terms=("Roshan",),
        requires_sources=True,
    ),
    DemoAcceptanceCase(
        question="Chen 的神杖效果是什么？",
        expected_type="knowledge_missing",
        allows_missing_coverage=True,
    ),
)
```

- [ ] **Step 4: Run the fixture tests**

Run from `backend/`:

```powershell
C:\WINDOWS\System32\WindowsPowerShell\v1.0\powershell.exe -Command "`$env:TEMP='C:\Users\jaime\OneDrive\Desktop\dota2-rag-assistant\backend\.tmp'; `$env:TMP=`$env:TEMP; `$env:PYTHONPATH='C:\Users\jaime\OneDrive\Desktop\dota2-rag-assistant\backend\.tmp\py312-packages;C:\Users\jaime\OneDrive\Desktop\dota2-rag-assistant\backend'; C:\Users\jaime\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -m pytest tests/test_demo_acceptance.py -v -p no:cacheprovider --basetemp .tmp\pytest-m9-fixture"
```

Expected: both tests PASS.

- [ ] **Step 5: Commit**

```powershell
git add backend/tests/fixtures/demo_acceptance.py backend/tests/test_demo_acceptance.py
git commit -m "test: add demo acceptance cases"
```

## Task 2: Acceptance Route And Chat Behavior Tests

**Files:**
- Modify: `backend/tests/test_demo_acceptance.py`
- Modify: `backend/app/rag/classifier.py` if required by failing tests.

- [ ] **Step 1: Add failing route and chat behavior tests**

Append to `backend/tests/test_demo_acceptance.py`:

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
from tests.fixtures.demo_acceptance import DEMO_ACCEPTANCE_CASES


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


@pytest.mark.parametrize("case", DEMO_ACCEPTANCE_CASES)
def test_demo_acceptance_routes(case) -> None:
    expected = "knowledge" if case.expected_type == "knowledge_missing" else case.expected_type

    assert classify_question(case.question) == expected


@pytest.mark.asyncio
@pytest.mark.parametrize("case", [case for case in DEMO_ACCEPTANCE_CASES if case.requires_stats])
async def test_demo_acceptance_stats_answers_use_sqlite(tmp_path, case) -> None:
    service = ChatService(
        store=LocalVectorStore(tmp_path / "vectors.json"),
        embedder=DeterministicEmbedder(dimensions=64),
        generator=FakeGenerator("this should not be used"),
        stats_repository=make_stats_repository(tmp_path),
    )

    response = await service.answer(case.question)

    assert response.question_type == "stats"
    assert response.debug.stats_used is True
    for term in case.expected_terms:
        assert term in response.answer
    assert "OpenDota" in response.answer


@pytest.mark.asyncio
async def test_demo_acceptance_missing_coverage_is_explicit(tmp_path) -> None:
    missing_case = next(case for case in DEMO_ACCEPTANCE_CASES if case.allows_missing_coverage)
    service = ChatService(
        store=LocalVectorStore(tmp_path / "vectors.json"),
        embedder=DeterministicEmbedder(dimensions=64),
        generator=FakeGenerator("this should not be used"),
    )

    response = await service.answer(missing_case.question)

    assert response.question_type == "knowledge"
    assert response.sources == []
    assert "当前知识库没有覆盖" in response.answer
```

- [ ] **Step 2: Run route and chat tests to verify failures**

Run from `backend/`:

```powershell
C:\WINDOWS\System32\WindowsPowerShell\v1.0\powershell.exe -Command "`$env:TEMP='C:\Users\jaime\OneDrive\Desktop\dota2-rag-assistant\backend\.tmp'; `$env:TMP=`$env:TEMP; `$env:PYTHONPATH='C:\Users\jaime\OneDrive\Desktop\dota2-rag-assistant\backend\.tmp\py312-packages;C:\Users\jaime\OneDrive\Desktop\dota2-rag-assistant\backend'; C:\Users\jaime\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -m pytest tests/test_demo_acceptance.py -v -p no:cacheprovider --basetemp .tmp\pytest-m9-acceptance"
```

Expected: FAIL if `最近版本 Roshan 有什么变化？` is not classified as `patch`, or PASS if M8 already covers it through `版本`.

- [ ] **Step 3: Apply the narrow classifier fix only if the route test fails**

If the route test fails for `最近版本 Roshan 有什么变化？`, update `backend/app/rag/classifier.py`:

```python
PATCH_TERMS = ("patch", "版本", "最近版本", "改动", "变化", "更新", "7.")
```

Do not add a broader patch parser in M9.

- [ ] **Step 4: Run acceptance tests**

Run from `backend/`:

```powershell
C:\WINDOWS\System32\WindowsPowerShell\v1.0\powershell.exe -Command "`$env:TEMP='C:\Users\jaime\OneDrive\Desktop\dota2-rag-assistant\backend\.tmp'; `$env:TMP=`$env:TEMP; `$env:PYTHONPATH='C:\Users\jaime\OneDrive\Desktop\dota2-rag-assistant\backend\.tmp\py312-packages;C:\Users\jaime\OneDrive\Desktop\dota2-rag-assistant\backend'; C:\Users\jaime\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -m pytest tests/test_demo_acceptance.py -v -p no:cacheprovider --basetemp .tmp\pytest-m9-acceptance"
```

Expected: all demo acceptance tests PASS.

- [ ] **Step 5: Commit**

```powershell
git add backend/tests/test_demo_acceptance.py backend/app/rag/classifier.py
git commit -m "test: verify demo acceptance routes"
```

If `classifier.py` was not modified, stage only `backend/tests/test_demo_acceptance.py`.

## Task 3: Source And Prompt Acceptance Tests

**Files:**
- Modify: `backend/tests/test_demo_acceptance.py`
- Modify: `backend/app/rag/prompt_builder.py` if required by failing tests.

- [ ] **Step 1: Add source and prompt-property tests**

Append to `backend/tests/test_demo_acceptance.py`:

```python
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "case",
    [case for case in DEMO_ACCEPTANCE_CASES if case.requires_sources and case.expected_type in {"knowledge", "advice", "patch"}],
)
async def test_demo_acceptance_text_answers_keep_sources_and_terms(tmp_path, case) -> None:
    store = LocalVectorStore(tmp_path / "vectors.json")
    embedder = DeterministicEmbedder(dimensions=64)
    ingest_seed_documents(store=store, embedder=embedder)
    service = ChatService(
        store=store,
        embedder=embedder,
        generator=FakeGenerator(
            "直接结论: Black King Bar / BKB, Roshan, and Blink Dagger are preserved."
        ),
        minimum_score=-1.0,
    )

    response = await service.answer(case.question)

    assert response.question_type == case.expected_type
    assert response.sources
    for term in case.expected_terms:
        assert term in response.answer or any(term in source.entity_name for source in response.sources)


def test_demo_acceptance_prompt_contract_mentions_missing_coverage() -> None:
    from app.rag.prompt_builder import build_prompt

    prompt = build_prompt(
        question="Chen 的神杖效果是什么？",
        question_type="knowledge",
        retrieved_chunks=[],
        canonical_terms=[],
    )

    assert "当前知识库没有覆盖这个问题" in prompt
    assert "来源/数据新鲜度" in prompt
```

- [ ] **Step 2: Run the source and prompt tests**

Run from `backend/`:

```powershell
C:\WINDOWS\System32\WindowsPowerShell\v1.0\powershell.exe -Command "`$env:TEMP='C:\Users\jaime\OneDrive\Desktop\dota2-rag-assistant\backend\.tmp'; `$env:TMP=`$env:TEMP; `$env:PYTHONPATH='C:\Users\jaime\OneDrive\Desktop\dota2-rag-assistant\backend\.tmp\py312-packages;C:\Users\jaime\OneDrive\Desktop\dota2-rag-assistant\backend'; C:\Users\jaime\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -m pytest tests/test_demo_acceptance.py -v -p no:cacheprovider --basetemp .tmp\pytest-m9-source"
```

Expected: PASS if seed retrieval plus prompt contract already satisfy the cases. If a text case has no source because the seed set does not cover it, narrow the test case to route/prompt behavior or add a seed document only if it is already part of the existing seed-document pattern.

- [ ] **Step 3: Make a minimal prompt fix only if the prompt contract test fails**

If the prompt contract test fails, update `backend/app/rag/prompt_builder.py` so the rules include the exact phrase:

```text
如果 context 不足，明确说“当前知识库没有覆盖这个问题”，不要猜测。
```

- [ ] **Step 4: Run M9 acceptance tests**

Run from `backend/`:

```powershell
C:\WINDOWS\System32\WindowsPowerShell\v1.0\powershell.exe -Command "`$env:TEMP='C:\Users\jaime\OneDrive\Desktop\dota2-rag-assistant\backend\.tmp'; `$env:TMP=`$env:TEMP; `$env:PYTHONPATH='C:\Users\jaime\OneDrive\Desktop\dota2-rag-assistant\backend\.tmp\py312-packages;C:\Users\jaime\OneDrive\Desktop\dota2-rag-assistant\backend'; C:\Users\jaime\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -m pytest tests/test_demo_acceptance.py tests/test_golden_questions.py -v -p no:cacheprovider --basetemp .tmp\pytest-m9-source"
```

Expected: all selected tests PASS.

- [ ] **Step 5: Commit**

```powershell
git add backend/tests/test_demo_acceptance.py backend/app/rag/prompt_builder.py
git commit -m "test: verify demo answer properties"
```

If `prompt_builder.py` was not modified, stage only `backend/tests/test_demo_acceptance.py`.

## Task 4: Demo Checklist And Full Verification

**Files:**
- Create: `docs/demo-checklist.md`

- [ ] **Step 1: Create the manual demo checklist**

Create `docs/demo-checklist.md`:

```markdown
# Dota 2 RAG Assistant Demo Checklist

Date: 2026-06-19

## Local Services

- Backend: `http://127.0.0.1:8000/api/health`
- Frontend: `http://127.0.0.1:5173/`
- Ollama: local Docker or host service

## Browser Smoke Test

1. Open the frontend.
2. Confirm service health loads.
3. Click `Refresh Knowledge`.
4. Confirm a success message such as `documents`, `chunks`, and `sources`.
5. Ask `What does BKB do?`.
6. Confirm the answer appears with sources.
7. Ask `Axe win rate meta` after local stats are available.
8. Confirm the answer includes `Axe`, a win rate, a pick share, and an OpenDota caveat.
9. Trigger `Refresh Stats` when OpenDota/network is unavailable.
10. Confirm the UI shows `Stats refresh failed. Check OpenDota/network and retry.` without clearing the chat input.
11. Click the example question `What does BKB do?`.
12. Confirm it fills the input without sending automatically.

## Demo Questions

- `BKB有什么用？`
- `What does BKB do?`
- `Roshan 会掉什么？`
- `肉山掉什么？`
- `黑皇杖什么时候出？`
- `Blink Dagger怎么用？`
- `跳刀怎么用？`
- `Axe win rate meta`
- `斧王胜率`
- `7.36 BKB 改了什么？`
- `最近版本 Roshan 有什么变化？`
- `Chen 的神杖效果是什么？`

## Expected Behavior

- Text-backed answers should include sources.
- Stats answers should include sample scope, refresh timestamp, and an OpenDota caveat.
- Unsupported questions should say the local knowledge base does not cover the question.
- The assistant should answer in Chinese while preserving important English Dota 2 terms.
```

- [ ] **Step 2: Run backend full test suite**

Run from `backend/`:

```powershell
C:\WINDOWS\System32\WindowsPowerShell\v1.0\powershell.exe -Command "`$env:TEMP='C:\Users\jaime\OneDrive\Desktop\dota2-rag-assistant\backend\.tmp'; `$env:TMP=`$env:TEMP; `$env:PYTHONPATH='C:\Users\jaime\OneDrive\Desktop\dota2-rag-assistant\backend\.tmp\py312-packages;C:\Users\jaime\OneDrive\Desktop\dota2-rag-assistant\backend'; C:\Users\jaime\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -m pytest -v -p no:cacheprovider --basetemp .tmp\pytest-m9-final"
```

Expected: all backend tests PASS.

- [ ] **Step 3: Run frontend tests**

Run from `frontend/`:

```powershell
npm test
```

Expected: all frontend tests PASS.

- [ ] **Step 4: Run frontend build**

Run from `frontend/`:

```powershell
npm run build
```

Expected: Vite build succeeds.

- [ ] **Step 5: Inspect git status**

Run from repo root:

```powershell
git status --short --branch
```

Expected: only intended M9 files are changed or committed. Existing untracked `.vscode/` may remain and should not be staged.

- [ ] **Step 6: Commit checklist**

```powershell
git add docs/demo-checklist.md
git commit -m "docs: add demo acceptance checklist"
```

If verification required small fixes, include those files in the same commit only when they are directly related to M9 acceptance.

## Self-Review

- Spec coverage: the plan covers demo acceptance cases, backend deterministic acceptance tests, narrow classifier/prompt fixes, missing-coverage behavior, manual browser checklist, and full verification.
- Scope check: no item ingestion, no ability ingestion, no new provider, no frontend redesign.
- Type consistency: `DemoAcceptanceCase` fields match the spec: `question`, `expected_type`, `expected_terms`, `requires_sources`, `requires_stats`, and `allows_missing_coverage`.
- Execution style: each behavior change is introduced by a failing test, followed by minimal implementation, verification, and a commit.
