# M12 Knowledge Browser Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a read-only knowledge browser that lets the user inspect local vector-store contents from API endpoints and the existing React UI.

**Architecture:** Backend exposes read-only summary and chunk-preview endpoints backed by `LocalVectorStore.records`. Frontend adds typed client functions and a compact Knowledge panel that loads summary and preview rows, then lets the user search and filter without changing chat behavior.

**Tech Stack:** FastAPI, Pydantic, existing local JSON vector store, pytest, React, TypeScript, Vite, Vitest, Testing Library.

---

## File Structure

- Create `backend/app/api/knowledge.py`: response models, summary grouping, filter logic, and two routes.
- Modify `backend/app/main.py`: include the knowledge router.
- Create `backend/tests/test_knowledge_api.py`: API tests with temporary vector records.
- Modify `frontend/src/api/client.ts`: add `KnowledgeSummary`, `KnowledgeChunk`, `fetchKnowledgeSummary`, and `fetchKnowledgeChunks`.
- Modify `frontend/src/api/client.test.ts`: verify endpoint calls and query params.
- Modify `frontend/src/App.tsx`: add Knowledge panel state, effects, search/filter controls, and preview rendering.
- Modify `frontend/src/App.test.tsx`: verify counts, previews, filtering, and error state.
- Modify `frontend/src/styles.css`: add dense Knowledge panel styles.
- Modify `README.md` and `docs/demo-checklist.md`: describe the Knowledge panel.

## Verification Commands

Backend:

```powershell
C:\WINDOWS\System32\WindowsPowerShell\v1.0\powershell.exe -Command "`$env:TEMP='C:\Users\jaime\OneDrive\Desktop\dota2-rag-assistant\backend\.tmp'; `$env:TMP=`$env:TEMP; `$env:PYTHONPATH='C:\Users\jaime\OneDrive\Desktop\dota2-rag-assistant\backend\.tmp\py312-packages;C:\Users\jaime\OneDrive\Desktop\dota2-rag-assistant\backend'; C:\Users\jaime\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -m pytest -v -p no:cacheprovider --basetemp backend\.tmp\pytest-m12"
```

Frontend:

```powershell
npm test
npm run build
```

Run frontend commands from `frontend`.

---

### Task 1: Backend Knowledge API

**Files:**
- Create: `backend/app/api/knowledge.py`
- Modify: `backend/app/main.py`
- Create: `backend/tests/test_knowledge_api.py`

- [ ] **Step 1: Write failing backend API tests**

Create `backend/tests/test_knowledge_api.py`:

```python
from pathlib import Path

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
from app.rag.schemas import SourceMetadata, TextChunk
from app.vector_store.milvus import LocalVectorStore


def make_client(tmp_path: Path) -> TestClient:
    settings = Settings(
        sqlite_path=tmp_path / "sqlite" / "dota2_rag.db",
        vector_data_path=tmp_path / "vectors",
        vector_index_path=tmp_path / "vectors" / "text_chunks.json",
        opendota_knowledge_sources_enabled=False,
    )
    return TestClient(create_app(settings))


def seed_vector_store(tmp_path: Path) -> None:
    store = LocalVectorStore(tmp_path / "vectors" / "text_chunks.json")
    chunks = [
        TextChunk(
            chunk_id="seed://items/black-king-bar#chunk-0",
            text="Black King Bar, often called BKB, is a core defensive item.",
            metadata=SourceMetadata(
                source_url="seed://items/black-king-bar",
                source_name="Seed: Black King Bar",
                patch_version=None,
                entity_type="item",
                entity_name="Black King Bar",
                updated_at="2026-06-18",
            ),
        ),
        TextChunk(
            chunk_id="https://api.opendota.com/api/constants/heroes/2#chunk-0",
            text=(
                "Axe is an OpenDota hero constant. Primary attribute: str. "
                "Roles: Initiator, Durable, Disabler, Carry."
            ),
            metadata=SourceMetadata(
                source_url="https://api.opendota.com/api/constants/heroes/2",
                source_name="OpenDota Hero: Axe",
                patch_version=None,
                entity_type="hero",
                entity_name="Axe",
                updated_at="2026-06-20",
            ),
        ),
        TextChunk(
            chunk_id="https://api.opendota.com/api/constants/items/blink#chunk-0",
            text="Blink Dagger is an OpenDota item constant. Cost: 2250. Mobility item.",
            metadata=SourceMetadata(
                source_url="https://api.opendota.com/api/constants/items/blink",
                source_name="OpenDota Item: Blink Dagger",
                patch_version=None,
                entity_type="item",
                entity_name="Blink Dagger",
                updated_at="2026-06-20",
            ),
        ),
        TextChunk(
            chunk_id="https://www.dota2.com/heroes/axe#chunk-0",
            text="Axe is an official Dota 2 hero.",
            metadata=SourceMetadata(
                source_url="https://www.dota2.com/heroes/axe",
                source_name="Official Dota 2: Axe",
                patch_version=None,
                entity_type="hero",
                entity_name="Axe",
                updated_at="2026-06-19",
            ),
        ),
    ]
    store.upsert([(chunk, [1.0, 0.0, 0.0]) for chunk in chunks])


def test_knowledge_summary_groups_chunks_by_type_and_source_prefix(tmp_path: Path) -> None:
    seed_vector_store(tmp_path)
    client = make_client(tmp_path)

    response = client.get("/api/knowledge/summary")

    assert response.status_code == 200
    payload = response.json()
    assert payload["total_chunks"] == 4
    assert payload["total_sources"] == 4
    assert payload["by_entity_type"] == {"hero": 2, "item": 2}
    assert payload["by_source_prefix"] == {
        "Official Dota 2": 1,
        "OpenDota Hero": 1,
        "OpenDota Item": 1,
        "Seed": 1,
    }
    assert payload["updated_at"] == "2026-06-20"


def test_knowledge_chunks_returns_previews_and_metadata(tmp_path: Path) -> None:
    seed_vector_store(tmp_path)
    client = make_client(tmp_path)

    response = client.get("/api/knowledge/chunks", params={"q": "Blink", "limit": 10})

    assert response.status_code == 200
    payload = response.json()
    assert len(payload["chunks"]) == 1
    chunk = payload["chunks"][0]
    assert chunk["source_name"] == "OpenDota Item: Blink Dagger"
    assert chunk["entity_type"] == "item"
    assert chunk["entity_name"] == "Blink Dagger"
    assert chunk["preview"] == "Blink Dagger is an OpenDota item constant. Cost: 2250. Mobility item."


def test_knowledge_chunks_filters_by_entity_type_source_prefix_and_limit(tmp_path: Path) -> None:
    seed_vector_store(tmp_path)
    client = make_client(tmp_path)

    response = client.get(
        "/api/knowledge/chunks",
        params={"entity_type": "hero", "source_prefix": "OpenDota Hero", "limit": 1},
    )

    assert response.status_code == 200
    payload = response.json()
    assert len(payload["chunks"]) == 1
    assert payload["chunks"][0]["source_name"] == "OpenDota Hero: Axe"


def test_knowledge_api_handles_empty_vector_store(tmp_path: Path) -> None:
    client = make_client(tmp_path)

    summary = client.get("/api/knowledge/summary").json()
    chunks = client.get("/api/knowledge/chunks").json()

    assert summary == {
        "total_chunks": 0,
        "total_sources": 0,
        "by_entity_type": {},
        "by_source_prefix": {},
        "updated_at": None,
    }
    assert chunks == {"chunks": []}
```

- [ ] **Step 2: Run backend API test to verify RED**

Run:

```powershell
C:\WINDOWS\System32\WindowsPowerShell\v1.0\powershell.exe -Command "`$env:TEMP='C:\Users\jaime\OneDrive\Desktop\dota2-rag-assistant\backend\.tmp'; `$env:TMP=`$env:TEMP; `$env:PYTHONPATH='C:\Users\jaime\OneDrive\Desktop\dota2-rag-assistant\backend\.tmp\py312-packages;C:\Users\jaime\OneDrive\Desktop\dota2-rag-assistant\backend'; C:\Users\jaime\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -m pytest backend/tests/test_knowledge_api.py -v -p no:cacheprovider --basetemp backend\.tmp\pytest-m12-knowledge-api"
```

Expected: FAIL with `404 Not Found` for the new endpoints.

- [ ] **Step 3: Implement `backend/app/api/knowledge.py`**

Create `backend/app/api/knowledge.py`:

```python
from collections import Counter
from typing import Annotated

from fastapi import APIRouter, Query, Request
from pydantic import BaseModel, Field

from app.rag.schemas import TextChunk
from app.vector_store.milvus import LocalVectorStore

router = APIRouter(prefix="/api/knowledge", tags=["knowledge"])


class KnowledgeSummaryResponse(BaseModel):
    total_chunks: int
    total_sources: int
    by_entity_type: dict[str, int]
    by_source_prefix: dict[str, int]
    updated_at: str | None


class KnowledgeChunkPreview(BaseModel):
    chunk_id: str
    source_name: str
    source_url: str
    entity_type: str
    entity_name: str
    patch_version: str | None
    updated_at: str
    preview: str = Field(min_length=1)


class KnowledgeChunksResponse(BaseModel):
    chunks: list[KnowledgeChunkPreview]


def _store_for_request(request: Request) -> LocalVectorStore:
    settings = request.app.state.settings
    return LocalVectorStore(settings.vector_index_path)


def _source_prefix(source_name: str) -> str:
    if source_name.startswith("OpenDota Hero:"):
        return "OpenDota Hero"
    if source_name.startswith("OpenDota Item:"):
        return "OpenDota Item"
    if source_name.startswith("Seed:"):
        return "Seed"
    if source_name.startswith("Official Dota 2:"):
        return "Official Dota 2"
    return "Other"


def _preview(text: str, max_chars: int = 240) -> str:
    normalized = " ".join(text.split())
    return normalized[:max_chars]


def _matches_query(chunk: TextChunk, query: str | None) -> bool:
    if not query:
        return True
    needle = query.casefold()
    metadata = chunk.metadata
    haystack = " ".join(
        [
            chunk.text,
            metadata.source_name,
            metadata.source_url,
            metadata.entity_name,
            metadata.entity_type,
            metadata.patch_version or "",
        ]
    ).casefold()
    return needle in haystack


def _matches_entity_type(chunk: TextChunk, entity_type: str | None) -> bool:
    return entity_type is None or chunk.metadata.entity_type == entity_type


def _matches_source_prefix(chunk: TextChunk, source_prefix: str | None) -> bool:
    return source_prefix is None or _source_prefix(chunk.metadata.source_name) == source_prefix


def _chunk_preview(chunk: TextChunk) -> KnowledgeChunkPreview:
    return KnowledgeChunkPreview(
        chunk_id=chunk.chunk_id,
        source_name=chunk.metadata.source_name,
        source_url=chunk.metadata.source_url,
        entity_type=chunk.metadata.entity_type,
        entity_name=chunk.metadata.entity_name,
        patch_version=chunk.metadata.patch_version,
        updated_at=chunk.metadata.updated_at,
        preview=_preview(chunk.text),
    )


@router.get("/summary", response_model=KnowledgeSummaryResponse)
def knowledge_summary(request: Request) -> KnowledgeSummaryResponse:
    store = _store_for_request(request)
    chunks = [record.chunk for record in store.records.values()]
    entity_counts = Counter(chunk.metadata.entity_type for chunk in chunks)
    source_prefix_counts = Counter(_source_prefix(chunk.metadata.source_name) for chunk in chunks)
    updated_values = [chunk.metadata.updated_at for chunk in chunks if chunk.metadata.updated_at]
    return KnowledgeSummaryResponse(
        total_chunks=len(chunks),
        total_sources=len({chunk.metadata.source_name for chunk in chunks}),
        by_entity_type=dict(sorted(entity_counts.items())),
        by_source_prefix=dict(sorted(source_prefix_counts.items())),
        updated_at=max(updated_values) if updated_values else None,
    )


@router.get("/chunks", response_model=KnowledgeChunksResponse)
def knowledge_chunks(
    request: Request,
    q: str | None = None,
    entity_type: str | None = None,
    source_prefix: str | None = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> KnowledgeChunksResponse:
    store = _store_for_request(request)
    chunks = [record.chunk for record in store.records.values()]
    filtered = [
        chunk
        for chunk in chunks
        if _matches_query(chunk, q)
        and _matches_entity_type(chunk, entity_type)
        and _matches_source_prefix(chunk, source_prefix)
    ]
    filtered.sort(key=lambda chunk: (chunk.metadata.source_name, chunk.chunk_id))
    return KnowledgeChunksResponse(
        chunks=[_chunk_preview(chunk) for chunk in filtered[:limit]],
    )
```

- [ ] **Step 4: Include the router in `backend/app/main.py`**

Modify `backend/app/main.py` to import and include the knowledge router:

```python
from app.api import chat, health, ingest, knowledge, stats
```

and:

```python
app.include_router(knowledge.router)
```

- [ ] **Step 5: Run backend API tests to verify GREEN**

Run:

```powershell
C:\WINDOWS\System32\WindowsPowerShell\v1.0\powershell.exe -Command "`$env:TEMP='C:\Users\jaime\OneDrive\Desktop\dota2-rag-assistant\backend\.tmp'; `$env:TMP=`$env:TEMP; `$env:PYTHONPATH='C:\Users\jaime\OneDrive\Desktop\dota2-rag-assistant\backend\.tmp\py312-packages;C:\Users\jaime\OneDrive\Desktop\dota2-rag-assistant\backend'; C:\Users\jaime\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -m pytest backend/tests/test_knowledge_api.py -v -p no:cacheprovider --basetemp backend\.tmp\pytest-m12-knowledge-api"
```

Expected: PASS.

- [ ] **Step 6: Commit backend API**

```powershell
git add backend/app/api/knowledge.py backend/app/main.py backend/tests/test_knowledge_api.py
git commit -m "feat: add knowledge browser api"
```

---

### Task 2: Frontend Knowledge Client

**Files:**
- Modify: `frontend/src/api/client.ts`
- Modify: `frontend/src/api/client.test.ts`

- [ ] **Step 1: Add failing client tests**

Append to `frontend/src/api/client.test.ts`:

```typescript
import { fetchKnowledgeChunks, fetchKnowledgeSummary } from "./client";

test("fetchKnowledgeSummary calls summary endpoint", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        total_chunks: 4,
        total_sources: 4,
        by_entity_type: { hero: 2, item: 2 },
        by_source_prefix: { "OpenDota Hero": 1, "OpenDota Item": 1, Seed: 1 },
        updated_at: "2026-06-20",
      }),
    }),
  );

  const result = await fetchKnowledgeSummary();

  expect(fetch).toHaveBeenCalledWith("http://127.0.0.1:8000/api/knowledge/summary");
  expect(result.total_chunks).toBe(4);
  expect(result.by_entity_type.hero).toBe(2);
});

test("fetchKnowledgeChunks sends filters as query params", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        chunks: [
          {
            chunk_id: "blink#chunk-0",
            source_name: "OpenDota Item: Blink Dagger",
            source_url: "https://api.opendota.com/api/constants/items/blink",
            entity_type: "item",
            entity_name: "Blink Dagger",
            patch_version: null,
            updated_at: "2026-06-20",
            preview: "Blink Dagger is an OpenDota item constant.",
          },
        ],
      }),
    }),
  );

  const result = await fetchKnowledgeChunks({
    q: "Blink",
    entity_type: "item",
    source_prefix: "OpenDota Item",
    limit: 25,
  });

  expect(fetch).toHaveBeenCalledWith(
    "http://127.0.0.1:8000/api/knowledge/chunks?q=Blink&entity_type=item&source_prefix=OpenDota+Item&limit=25",
  );
  expect(result.chunks[0].source_name).toBe("OpenDota Item: Blink Dagger");
});
```

If `frontend/src/api/client.test.ts` already imports from `./client`, merge these names into the existing import instead of duplicating imports.

- [ ] **Step 2: Run client tests to verify RED**

Run from `frontend`:

```powershell
npm test -- src/api/client.test.ts
```

Expected: FAIL because `fetchKnowledgeSummary` and `fetchKnowledgeChunks` are not exported.

- [ ] **Step 3: Add client types and functions**

Modify `frontend/src/api/client.ts`:

```typescript
export type KnowledgeSummary = {
  total_chunks: number;
  total_sources: number;
  by_entity_type: Record<string, number>;
  by_source_prefix: Record<string, number>;
  updated_at: string | null;
};

export type KnowledgeChunk = {
  chunk_id: string;
  source_name: string;
  source_url: string;
  entity_type: string;
  entity_name: string;
  patch_version: string | null;
  updated_at: string;
  preview: string;
};

export type KnowledgeChunksResponse = {
  chunks: KnowledgeChunk[];
};

export type KnowledgeChunkFilters = {
  q?: string;
  entity_type?: string;
  source_prefix?: string;
  limit?: number;
};

export async function fetchKnowledgeSummary(): Promise<KnowledgeSummary> {
  return requestJson<KnowledgeSummary>("/api/knowledge/summary");
}

export async function fetchKnowledgeChunks(
  filters: KnowledgeChunkFilters = {},
): Promise<KnowledgeChunksResponse> {
  const params = new URLSearchParams();
  if (filters.q) params.set("q", filters.q);
  if (filters.entity_type) params.set("entity_type", filters.entity_type);
  if (filters.source_prefix) params.set("source_prefix", filters.source_prefix);
  if (filters.limit) params.set("limit", String(filters.limit));
  const query = params.toString();
  return requestJson<KnowledgeChunksResponse>(
    `/api/knowledge/chunks${query ? `?${query}` : ""}`,
  );
}
```

Place these near the other exported API types/functions and reuse the existing `requestJson` helper.

- [ ] **Step 4: Run client tests to verify GREEN**

Run from `frontend`:

```powershell
npm test -- src/api/client.test.ts
```

Expected: PASS.

- [ ] **Step 5: Commit frontend client**

```powershell
git add frontend/src/api/client.ts frontend/src/api/client.test.ts
git commit -m "feat: add knowledge browser client"
```

---

### Task 3: Frontend Knowledge Panel

**Files:**
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/App.test.tsx`
- Modify: `frontend/src/styles.css`

- [ ] **Step 1: Add failing UI tests**

Update `frontend/src/App.test.tsx` test setup so mocked API exports include:

```typescript
fetchKnowledgeSummary: vi.fn(),
fetchKnowledgeChunks: vi.fn(),
```

Import the mocks if needed:

```typescript
import {
  askChat,
  fetchHealth,
  fetchKnowledgeChunks,
  fetchKnowledgeSummary,
  refreshKnowledge,
  refreshStats,
} from "./api/client";
```

Add tests:

```typescript
test("renders knowledge summary and chunk previews", async () => {
  vi.mocked(fetchKnowledgeSummary).mockResolvedValue({
    total_chunks: 632,
    total_sources: 631,
    by_entity_type: { hero: 128, item: 503, objective: 1 },
    by_source_prefix: { "OpenDota Hero": 128, "OpenDota Item": 500, Seed: 3 },
    updated_at: "2026-06-20",
  });
  vi.mocked(fetchKnowledgeChunks).mockResolvedValue({
    chunks: [
      {
        chunk_id: "axe#chunk-0",
        source_name: "OpenDota Hero: Axe",
        source_url: "https://api.opendota.com/api/constants/heroes/2",
        entity_type: "hero",
        entity_name: "Axe",
        patch_version: null,
        updated_at: "2026-06-20",
        preview: "Axe is an OpenDota hero constant.",
      },
    ],
  });

  render(<App />);

  expect(await screen.findByText("Knowledge")).toBeInTheDocument();
  expect(await screen.findByText("632 chunks")).toBeInTheDocument();
  expect(screen.getByText("hero 128")).toBeInTheDocument();
  expect(screen.getByText("OpenDota Hero 128")).toBeInTheDocument();
  expect(screen.getByText("OpenDota Hero: Axe")).toBeInTheDocument();
  expect(screen.getByText("Axe is an OpenDota hero constant.")).toBeInTheDocument();
});

test("knowledge filters request chunk previews with query params", async () => {
  vi.mocked(fetchKnowledgeSummary).mockResolvedValue({
    total_chunks: 1,
    total_sources: 1,
    by_entity_type: { item: 1 },
    by_source_prefix: { "OpenDota Item": 1 },
    updated_at: "2026-06-20",
  });
  vi.mocked(fetchKnowledgeChunks).mockResolvedValue({ chunks: [] });

  render(<App />);

  const search = await screen.findByLabelText("Search knowledge");
  await userEvent.clear(search);
  await userEvent.type(search, "Blink");
  await userEvent.selectOptions(screen.getByLabelText("Entity type"), "item");
  await userEvent.selectOptions(screen.getByLabelText("Source prefix"), "OpenDota Item");

  await waitFor(() => {
    expect(fetchKnowledgeChunks).toHaveBeenLastCalledWith({
      q: "Blink",
      entity_type: "item",
      source_prefix: "OpenDota Item",
      limit: 50,
    });
  });
});

test("knowledge panel shows errors without removing chat controls", async () => {
  vi.mocked(fetchKnowledgeSummary).mockRejectedValue(new Error("summary failed"));
  vi.mocked(fetchKnowledgeChunks).mockRejectedValue(new Error("chunks failed"));

  render(<App />);

  expect(await screen.findByText("summary failed")).toBeInTheDocument();
  expect(screen.getByLabelText("Ask a Dota 2 question")).toBeInTheDocument();
});
```

Adapt exact import names to the existing test file structure.

- [ ] **Step 2: Run App tests to verify RED**

Run from `frontend`:

```powershell
npm test -- src/App.test.tsx
```

Expected: FAIL because the Knowledge panel does not exist.

- [ ] **Step 3: Add Knowledge panel state and effects in `App.tsx`**

Modify imports:

```typescript
  fetchKnowledgeChunks,
  fetchKnowledgeSummary,
  KnowledgeChunk,
  KnowledgeSummary,
```

Add state:

```typescript
  const [knowledgeSummary, setKnowledgeSummary] = useState<
    RefreshState<KnowledgeSummary>
  >({ status: "idle" });
  const [knowledgeChunks, setKnowledgeChunks] = useState<
    RefreshState<{ chunks: KnowledgeChunk[] }>
  >({ status: "idle" });
  const [knowledgeQuery, setKnowledgeQuery] = useState("");
  const [knowledgeEntityType, setKnowledgeEntityType] = useState("");
  const [knowledgeSourcePrefix, setKnowledgeSourcePrefix] = useState("");
```

Add effects:

```typescript
  useEffect(() => {
    let active = true;
    setKnowledgeSummary({ status: "loading" });
    fetchKnowledgeSummary()
      .then((result) => {
        if (active) setKnowledgeSummary({ status: "success", result });
      })
      .catch((error: Error) => {
        if (active) setKnowledgeSummary({ status: "error", message: error.message });
      });
    return () => {
      active = false;
    };
  }, [knowledgeRefresh.status]);

  useEffect(() => {
    let active = true;
    setKnowledgeChunks({ status: "loading" });
    fetchKnowledgeChunks({
      q: knowledgeQuery.trim() || undefined,
      entity_type: knowledgeEntityType || undefined,
      source_prefix: knowledgeSourcePrefix || undefined,
      limit: 50,
    })
      .then((result) => {
        if (active) setKnowledgeChunks({ status: "success", result });
      })
      .catch((error: Error) => {
        if (active) setKnowledgeChunks({ status: "error", message: error.message });
      });
    return () => {
      active = false;
    };
  }, [knowledgeQuery, knowledgeEntityType, knowledgeSourcePrefix, knowledgeRefresh.status]);
```

- [ ] **Step 4: Render Knowledge panel in `App.tsx`**

Add this component call below the refresh panel:

```tsx
        <KnowledgePanel
          chunksState={knowledgeChunks}
          entityType={knowledgeEntityType}
          onEntityTypeChange={setKnowledgeEntityType}
          onQueryChange={setKnowledgeQuery}
          onSourcePrefixChange={setKnowledgeSourcePrefix}
          query={knowledgeQuery}
          sourcePrefix={knowledgeSourcePrefix}
          summaryState={knowledgeSummary}
        />
```

Add helper components below `RefreshStatus`:

```tsx
function KnowledgePanel({
  chunksState,
  entityType,
  onEntityTypeChange,
  onQueryChange,
  onSourcePrefixChange,
  query,
  sourcePrefix,
  summaryState,
}: {
  chunksState: RefreshState<{ chunks: KnowledgeChunk[] }>;
  entityType: string;
  onEntityTypeChange: (value: string) => void;
  onQueryChange: (value: string) => void;
  onSourcePrefixChange: (value: string) => void;
  query: string;
  sourcePrefix: string;
  summaryState: RefreshState<KnowledgeSummary>;
}) {
  return (
    <section className="knowledgePanel" aria-label="Knowledge">
      <div className="panelHeader">
        <h2>Knowledge</h2>
        {summaryState.status === "success" && (
          <p>
            {summaryState.result.total_chunks} chunks - {summaryState.result.total_sources} sources
          </p>
        )}
      </div>

      {summaryState.status === "loading" && <p className="refreshStatus">Loading knowledge...</p>}
      {summaryState.status === "error" && (
        <p className="refreshStatus error" role="alert">
          {summaryState.message}
        </p>
      )}
      {summaryState.status === "success" && summaryState.result.total_chunks === 0 && (
        <p className="refreshStatus">No knowledge indexed. Refresh knowledge to inspect chunks.</p>
      )}
      {summaryState.status === "success" && summaryState.result.total_chunks > 0 && (
        <div className="knowledgeStats">
          <MetricList values={summaryState.result.by_entity_type} />
          <MetricList values={summaryState.result.by_source_prefix} />
        </div>
      )}

      <div className="knowledgeFilters">
        <label>
          Search knowledge
          <input
            onChange={(event) => onQueryChange(event.target.value)}
            placeholder="Axe, Blink Dagger, BKB"
            value={query}
          />
        </label>
        <label>
          Entity type
          <select onChange={(event) => onEntityTypeChange(event.target.value)} value={entityType}>
            <option value="">All</option>
            <option value="hero">hero</option>
            <option value="item">item</option>
            <option value="objective">objective</option>
            <option value="patch">patch</option>
          </select>
        </label>
        <label>
          Source prefix
          <select
            onChange={(event) => onSourcePrefixChange(event.target.value)}
            value={sourcePrefix}
          >
            <option value="">All</option>
            <option value="OpenDota Hero">OpenDota Hero</option>
            <option value="OpenDota Item">OpenDota Item</option>
            <option value="Seed">Seed</option>
            <option value="Official Dota 2">Official Dota 2</option>
            <option value="Other">Other</option>
          </select>
        </label>
      </div>

      {chunksState.status === "loading" && <p className="refreshStatus">Loading chunks...</p>}
      {chunksState.status === "error" && (
        <p className="refreshStatus error" role="alert">
          {chunksState.message}
        </p>
      )}
      {chunksState.status === "success" && chunksState.result.chunks.length === 0 && (
        <p className="refreshStatus">No knowledge chunks match these filters.</p>
      )}
      {chunksState.status === "success" && chunksState.result.chunks.length > 0 && (
        <div className="knowledgeList">
          {chunksState.result.chunks.map((chunk) => (
            <article className="knowledgeItem" key={chunk.chunk_id}>
              <div>
                <h3>{chunk.source_name}</h3>
                <p>
                  {chunk.entity_type} - {chunk.entity_name}
                </p>
              </div>
              <p>{chunk.preview}</p>
            </article>
          ))}
        </div>
      )}
    </section>
  );
}

function MetricList({ values }: { values: Record<string, number> }) {
  return (
    <div className="metricList">
      {Object.entries(values).map(([name, count]) => (
        <span className="metricChip" key={name}>
          {name} {count}
        </span>
      ))}
    </div>
  );
}
```

- [ ] **Step 5: Add CSS**

Append to `frontend/src/styles.css`:

```css
.knowledgePanel {
  border-top: 1px solid var(--border);
  padding: 18px 0;
}

.panelHeader {
  align-items: baseline;
  display: flex;
  gap: 12px;
  justify-content: space-between;
}

.panelHeader h2 {
  font-size: 1rem;
  margin: 0;
}

.panelHeader p {
  color: var(--muted);
  margin: 0;
}

.knowledgeStats,
.knowledgeFilters {
  display: grid;
  gap: 10px;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  margin-top: 12px;
}

.metricList {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.metricChip {
  background: var(--surface-muted);
  border: 1px solid var(--border);
  border-radius: 6px;
  color: var(--text);
  font-size: 0.82rem;
  padding: 5px 8px;
}

.knowledgeFilters label {
  color: var(--muted);
  display: grid;
  font-size: 0.82rem;
  gap: 6px;
}

.knowledgeFilters input,
.knowledgeFilters select {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 6px;
  color: var(--text);
  min-height: 36px;
  padding: 0 10px;
}

.knowledgeList {
  display: grid;
  gap: 10px;
  margin-top: 12px;
}

.knowledgeItem {
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 10px;
}

.knowledgeItem h3 {
  font-size: 0.95rem;
  margin: 0;
}

.knowledgeItem p {
  color: var(--muted);
  margin: 6px 0 0;
}
```

Adjust CSS variable names if the existing stylesheet uses different tokens.

- [ ] **Step 6: Run App tests to verify GREEN**

Run from `frontend`:

```powershell
npm test -- src/App.test.tsx
```

Expected: PASS.

- [ ] **Step 7: Commit frontend panel**

```powershell
git add frontend/src/App.tsx frontend/src/App.test.tsx frontend/src/styles.css
git commit -m "feat: add knowledge browser panel"
```

---

### Task 4: Docs And Final Verification

**Files:**
- Modify: `README.md`
- Modify: `docs/demo-checklist.md`

- [ ] **Step 1: Update docs**

In `README.md`, add to `Current capabilities`:

```markdown
- Read-only knowledge browser for source counts, filters, and chunk previews.
```

In `docs/demo-checklist.md`, add browser smoke steps after knowledge refresh:

```markdown
- Confirm the Knowledge panel shows total chunks and source counts.
- Search `Axe` and confirm `OpenDota Hero: Axe` appears.
- Search `Blink Dagger` and confirm `OpenDota Item: Blink Dagger` appears.
```

- [ ] **Step 2: Run full backend tests**

Run:

```powershell
C:\WINDOWS\System32\WindowsPowerShell\v1.0\powershell.exe -Command "`$env:TEMP='C:\Users\jaime\OneDrive\Desktop\dota2-rag-assistant\backend\.tmp'; `$env:TMP=`$env:TEMP; `$env:PYTHONPATH='C:\Users\jaime\OneDrive\Desktop\dota2-rag-assistant\backend\.tmp\py312-packages;C:\Users\jaime\OneDrive\Desktop\dota2-rag-assistant\backend'; C:\Users\jaime\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -m pytest -v -p no:cacheprovider --basetemp backend\.tmp\pytest-m12-final"
```

Expected: PASS.

- [ ] **Step 3: Run full frontend tests**

Run from `frontend`:

```powershell
npm test
```

Expected: PASS.

- [ ] **Step 4: Run frontend build**

Run from `frontend`:

```powershell
npm run build
```

Expected: PASS.

- [ ] **Step 5: Commit docs**

```powershell
git add README.md docs/demo-checklist.md
git commit -m "docs: describe knowledge browser"
```

- [ ] **Step 6: Final status check**

Run:

```powershell
git status --short --branch
```

Expected: clean worktree, branch ahead of origin with M12 commits.

## Self-Review

- Spec coverage: The plan implements read-only backend summary/chunk endpoints, frontend client functions, UI summary/search/filter/preview behavior, error/empty states, tests, docs, and final verification.
- Placeholder scan: The plan contains no placeholders or deferred implementation markers.
- Type consistency: Backend response fields match frontend types: `total_chunks`, `total_sources`, `by_entity_type`, `by_source_prefix`, `updated_at`, and `chunks`.
