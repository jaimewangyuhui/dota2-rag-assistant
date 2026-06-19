# M11 OpenDota Knowledge Ingestion Design

Date: 2026-06-20

## Goal

Expand the local Dota 2 RAG knowledge base by crawling OpenDota hero and item constants, converting them into searchable text documents, and storing their chunks in the existing local vector store.

This milestone focuses on OpenDota-backed knowledge coverage for heroes and items. It should make questions about hero roles, hero attributes, item cost, item components, and basic item metadata retrievable through the same `/api/ingest/documents` flow already used by seed and official Dota documents.

## Non-Goals

- Do not build a separate scraper service or scheduler.
- Do not replace the existing official Dota source loader.
- Do not add a production Milvus deployment.
- Do not claim item behavior details that are not present in the OpenDota constants payload.
- Do not build a frontend admin screen for source selection in this milestone.

## Data Sources

Use the existing `opendota_base_url` setting, defaulting to `https://api.opendota.com/api`.

Required endpoints:

- `/constants/heroes`
- `/constants/items`

The OpenDota payloads are treated as public API JSON, not HTML pages. The implementation should use `httpx`, consistent with the existing OpenDota stats client.

## Architecture

Add a new focused source module:

```text
backend/app/data_sources/opendota_knowledge.py
```

Responsibilities:

- Fetch hero and item constants from OpenDota.
- Parse raw JSON into typed records.
- Convert records into `DocumentInput` values with `SourceMetadata`.
- Expose `load_opendota_knowledge_documents(client=None, refreshed_at=None)`.

The ingestion job remains responsible for chunking, embedding, and vector upsert. The new source module should not know about vector storage.

## Document Shape

Hero documents should include the available fields useful for retrieval:

- OpenDota internal name.
- Localized display name.
- Primary attribute.
- Attack type, if available.
- Roles.
- Legs, if available.
- Aliases derived from the internal name and localized name.

Hero metadata:

- `source_url`: `https://api.opendota.com/api/constants/heroes/<hero_id>`
- `source_name`: `OpenDota Hero: <localized_name>`
- `entity_type`: `hero`
- `entity_name`: `<localized_name>`
- `updated_at`: ingestion date

Item documents should include the available fields useful for retrieval:

- OpenDota item key and display hint.
- Cost, if available.
- Components, if available.
- Shop flags such as secret shop or side shop, if available.
- Attributes, notes, abilities, or lore when present in the payload.

Item metadata:

- `source_url`: `https://api.opendota.com/api/constants/items/<item_key>`
- `source_name`: `OpenDota Item: <item_key>`
- `entity_type`: `item`
- `entity_name`: normalized item display name
- `updated_at`: ingestion date

The document text should be explicit and compact. It should avoid pretending that sparse OpenDota fields are full gameplay descriptions.

## Ingestion Integration

Update the ingestion job so it can combine multiple optional document loaders:

```text
seed documents
+ optional official Dota documents
+ optional OpenDota knowledge documents
-> chunk_document
-> DeterministicEmbedder
-> LocalVectorStore.upsert
```

Add a setting:

```text
opendota_knowledge_sources_enabled: bool = True
```

`POST /api/ingest/documents` should include OpenDota knowledge documents when the setting is true. Tests may inject loaders directly to avoid network calls.

## Error Handling

The parser should raise a source-specific `OpenDotaKnowledgeParseError` when required JSON shapes are missing or empty.

Network failures should naturally surface from `httpx` during manual refresh, matching current official Dota ingestion behavior. The frontend already shows ingestion failure states, so this milestone does not add new UI error handling.

## Testing

Backend tests should cover:

- Hero constants parsing from a fixture with at least Axe.
- Item constants parsing from a fixture with at least Blink Dagger and Black King Bar-style fields when available.
- Document conversion for `hero` and `item` metadata.
- Ingestion with an injected OpenDota knowledge loader stores retrievable hero and item chunks.
- API ingestion can include injected OpenDota knowledge documents without network access.

Expected retrieval examples:

- `Axe roles strength initiator`
- `Blink Dagger cost mobility`
- `Black King Bar item cost`

## Acceptance Criteria

- A developer can refresh documents through `/api/ingest/documents` and get OpenDota hero and item sources in the response.
- OpenDota hero and item documents are chunked and stored in the existing vector store.
- Search can retrieve relevant OpenDota chunks for sample hero and item questions.
- Existing seed, official Dota, stats, chat, frontend, and demo tests still pass.

## Risks And Mitigations

- OpenDota item constants may not include complete gameplay descriptions. Mitigation: represent available metadata honestly and keep official Dota source ingestion as a future quality layer.
- Endpoint shapes can vary. Mitigation: parser tests cover both dictionary-style constants and common object payload fields.
- Ingestion can become slower when network sources are enabled. Mitigation: this milestone keeps the feature behind a setting and allows tests to inject local loaders.
