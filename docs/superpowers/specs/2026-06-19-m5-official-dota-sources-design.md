# M5 Official Dota Sources Design

## Goal

Add official Dota 2 website data collection for heroes and patch notes, then convert that collected knowledge into the existing RAG `DocumentInput` format. M5 should expand answer coverage beyond the current seed documents while keeping ingestion local-first, testable, and safe to rerun.

## Approved Scope

M5 includes:

- Official hero knowledge from `https://www.dota2.com/heroes`.
- Official patch note knowledge from `https://www.dota2.com/patches`.
- A small source adapter boundary so official website parsing is isolated from ingestion.
- Fixture-based parser tests that do not require live network access.
- Ingestion support for seed documents plus official hero and patch documents.
- Source metadata that lets answers cite official hero and patch sources.

M5 does not include:

- Official item scraping.
- OpenDota or structured match statistics.
- Frontend UI changes.
- Scheduled background refresh.
- Full historical patch archive ingestion.
- Any scraping from Dotabuff, STRATZ, or unofficial pages.

## Source Strategy

The official website should be treated as an external, unstable source. The implementation should separate three responsibilities:

1. Fetching raw official content.
2. Parsing raw official content into typed intermediate records.
3. Converting intermediate records into `DocumentInput`.

Tests should focus on parsing and conversion using local fixtures. Live fetch behavior can be covered by a narrow mocked HTTP client test.

If a live official page changes shape, the parser should fail loudly in tests when fixtures are updated. Runtime ingestion should return a clear error rather than silently indexing empty official documents.

## Architecture

Create one focused module:

```text
backend/app/data_sources/official_dota.py
```

It should expose:

- `OfficialDotaClient`: fetches official hero and patch pages or data endpoints.
- `OfficialHeroRecord`: typed intermediate hero record.
- `OfficialPatchRecord`: typed intermediate patch record.
- `parse_hero_records(raw: str, source_url: str) -> list[OfficialHeroRecord]`.
- `parse_patch_records(raw: str, source_url: str) -> list[OfficialPatchRecord]`.
- `hero_records_to_documents(records) -> list[DocumentInput]`.
- `patch_records_to_documents(records) -> list[DocumentInput]`.
- `load_official_dota_documents(client) -> list[DocumentInput]`.

The ingestion job should not know about HTML, JSON, CSS selectors, or website structure. It should receive `DocumentInput` objects from the data source module and pass them through the existing chunking, embedding, and vector store flow.

## Data Model

Hero records should capture:

- `name`
- `localized_name`
- `roles`
- `primary_attribute`
- `summary`
- `source_url`
- `updated_at`

Patch records should capture:

- `patch_version`
- `title`
- `summary`
- `sections`
- `source_url`
- `updated_at`

Document metadata should map as follows:

Hero document:

```text
source_url = official hero source URL
source_name = Official Dota 2: <localized hero name>
entity_type = hero
entity_name = <localized hero name>
patch_version = None unless the source provides a specific patch
updated_at = collection date or official date when available
```

Patch document:

```text
source_url = official patch source URL
source_name = Official Dota 2 Patch <patch_version>
entity_type = patch
entity_name = <patch title or patch_version>
patch_version = <patch_version>
updated_at = official patch date when available, otherwise collection date
```

## Ingestion Flow

M5 should keep the current seed ingestion path working and add official documents to the same indexing operation.

The target flow:

```text
POST /api/ingest/documents
-> load seed documents
-> load official hero documents
-> load official patch documents
-> chunk all documents
-> embed chunks
-> upsert into local vector store
-> return document count, chunk count, and source names
```

Runtime configuration should allow official fetching to be disabled for tests or offline development. The default development path can use fixtures or mocked clients in tests, while local manual runs can fetch from the official website.

## Error Handling

Official collection should handle:

- Network failure: return a clear collection error.
- Empty hero result: fail ingestion for official collection instead of indexing nothing.
- Empty patch result: fail ingestion for official collection instead of indexing nothing.
- Unsupported page shape: raise a parser error with the source URL.

Seed documents should remain available as a fallback path in tests. A failing official fetch should not corrupt existing vector store files.

## Testing

Tests should include:

- Hero parser extracts multiple hero records from a fixture.
- Patch parser extracts patch version, title, and sections from a fixture.
- Hero conversion produces `DocumentInput` with `entity_type="hero"`.
- Patch conversion produces `DocumentInput` with `entity_type="patch"`.
- Official document loader combines heroes and patches.
- Ingest job indexes seed plus official documents when an official loader is provided.
- Ingest API still works with deterministic test data and returns official source names.

Tests must not call `dota2.com`.

## Documentation

README should describe:

- How to run local ingestion with official heroes and patches.
- That tests use fixtures and do not require network.
- That items are intentionally out of scope for M5.

## Acceptance Criteria

- M5 adds official Dota 2 hero and patch document support.
- Item scraping remains out of scope.
- Existing M1-M4 behavior still works.
- `/api/ingest/documents` can index official hero and patch documents.
- Questions about at least one hero and one patch retrieve official sources.
- Backend tests pass.
- Frontend tests and build still pass before M5 is considered complete.
