# M12 Knowledge Browser Design

Date: 2026-06-20

## Goal

Add a read-only knowledge browser so a local user can inspect what is currently stored in the RAG vector knowledge base from the web UI.

The feature should make it obvious whether OpenDota heroes and items were ingested, how many chunks exist, and which sources/entities are available. It should support quick searching for examples such as `Axe`, `Blink Dagger`, and `Black King Bar`.

## Non-Goals

- Do not add delete, edit, or reindex controls.
- Do not expose raw embedding vectors.
- Do not build a separate admin app.
- Do not add pagination beyond a simple `limit` parameter.
- Do not change chat retrieval behavior.

## Backend API

Create a new API module:

```text
backend/app/api/knowledge.py
```

Add two read-only endpoints under `/api`:

### `GET /api/knowledge/summary`

Returns:

- `total_chunks`: total vector chunks.
- `total_sources`: unique source count.
- `by_entity_type`: counts grouped by `chunk.metadata.entity_type`.
- `by_source_prefix`: counts grouped into `OpenDota Hero`, `OpenDota Item`, `Seed`, `Official Dota 2`, and `Other`.
- `updated_at`: latest `chunk.metadata.updated_at` value when available.

### `GET /api/knowledge/chunks`

Query parameters:

- `q`: optional case-insensitive search over source name, entity name, source URL, and chunk text.
- `entity_type`: optional exact metadata entity type filter.
- `source_prefix`: optional source name prefix filter.
- `limit`: integer default `50`, minimum `1`, maximum `200`.

Returns a list of chunk previews:

- `chunk_id`
- `source_name`
- `source_url`
- `entity_type`
- `entity_name`
- `patch_version`
- `updated_at`
- `preview`

The preview should be short enough for the UI, around 240 characters.

## Backend Design

Add a small service/repository helper that reads the existing `LocalVectorStore` records and projects them into summary and preview response models. Keep this read-only and avoid coupling the UI to the JSON file shape.

Recommended files:

- `backend/app/api/knowledge.py`: FastAPI routes and response models.
- `backend/app/main.py`: include the new router.
- `backend/tests/test_knowledge_api.py`: API tests using a temporary vector store.

The implementation can use the current in-memory `LocalVectorStore.records` dictionary. It should not add new storage.

## Frontend Design

Add a compact `Knowledge` panel to the existing workbench, near the data refresh controls or below the chat/source layout.

The panel should show:

- Total chunk count.
- Source count.
- Entity type counts, especially `hero`, `item`, and `objective`.
- Source prefix counts, especially `OpenDota Hero`, `OpenDota Item`, `Seed`, and `Official Dota 2`.
- Search input.
- Entity type filter select.
- Source prefix filter select.
- Chunk preview list.

The UI should remain practical and dense, consistent with the current local demo interface. It should not become a landing page or a separate marketing-style view.

Recommended files:

- `frontend/src/api/client.ts`: knowledge summary/chunk client functions and types.
- `frontend/src/api/client.test.ts`: client tests.
- `frontend/src/App.tsx`: state and panel rendering.
- `frontend/src/App.test.tsx`: UI behavior tests.
- `frontend/src/styles.css`: compact panel styling.

## Empty And Error States

If there are no chunks, show a concise empty state telling the user to refresh knowledge.

If the backend request fails, show a concise error state inside the panel. Chat and refresh controls should remain usable.

Search with no results should show `No knowledge chunks match these filters.`

## Testing

Backend tests:

- Summary returns counts for seed, OpenDota hero, and OpenDota item chunks.
- Chunk listing returns previews and metadata.
- `q`, `entity_type`, `source_prefix`, and `limit` filters work together.
- Empty vector store returns zero counts and an empty chunk list.

Frontend tests:

- Client calls the two knowledge endpoints and parses responses.
- App renders summary counts.
- App renders chunk preview rows.
- Search/filter controls call the chunk endpoint with expected query params.
- Knowledge request errors are shown without breaking the chat UI.

## Acceptance Criteria

- After knowledge refresh, the browser shows OpenDota hero and item counts.
- Searching `Axe` shows `OpenDota Hero: Axe` when present in the vector store.
- Searching `Blink Dagger` shows `OpenDota Item: Blink Dagger` when present in the vector store.
- The feature is read-only.
- Backend tests, frontend tests, and frontend build pass.

## Risks And Mitigations

- Large local stores could make a single list request heavy. Mitigation: cap `limit` at `200` and default to `50`.
- Source names are string conventions. Mitigation: use stable prefix grouping and put unknown values into `Other`.
- The current vector store is local JSON, not production Milvus. Mitigation: read through `LocalVectorStore` so the API shape remains stable if storage changes later.
