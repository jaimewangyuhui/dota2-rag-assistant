# M6 OpenDota Hero Stats Design

## Goal

Add a small structured statistics layer powered by OpenDota hero statistics so the assistant can answer basic Meta questions about hero win rate, pick rate, sample size, and data freshness.

M6 is the first stats milestone. It should produce a reliable local SQLite-backed slice rather than a broad analytics system.

## Approved Scope

M6 includes:

- Fetching hero statistics from `https://api.opendota.com/api/heroStats`.
- Normalizing OpenDota hero rows into local hero stat records.
- Persisting the normalized records in SQLite.
- Exposing `POST /api/refresh/stats` to refresh local hero statistics.
- Providing repository/query functions for hero name lookup and top hero ranking.
- Teaching chat service stats questions to use local SQLite stats before falling back to vector-only RAG.
- Returning data freshness and sample caveats in stats answers.

M6 does not include:

- Item popularity or item builds.
- Match sample ingestion.
- Skill bracket or rank filtering.
- Frontend charts or new UI controls.
- Scheduled background refresh.
- Pro-only Meta analysis.
- Predictions or "best hero" claims without caveats.

## Source Strategy

OpenDota is treated as a public external data provider. Runtime refresh can call OpenDota, but automated tests must not call the network.

The implementation should separate:

1. Fetching raw OpenDota JSON.
2. Parsing raw hero stat rows.
3. Persisting normalized rows in SQLite.
4. Querying normalized rows for chat answers.

The design uses OpenDota `pub_pick` and `pub_win` as the default M6 sample because they are broad public-match fields and support straightforward `pick_rate`, `win_rate`, and `sample_size` calculations. `pro_pick`, `pro_win`, and `pro_ban` can be stored for a future milestone, but M6 chat answers should describe public sample stats unless a new spec explicitly expands the scope.

## Data Model

Create a SQLite table named `hero_stats`.

Columns:

- `hero_id` integer primary key.
- `name` text, such as `npc_dota_hero_axe`.
- `localized_name` text, such as `Axe`.
- `primary_attr` text.
- `roles_json` text storing the OpenDota roles array as JSON.
- `public_pick_count` integer.
- `public_win_count` integer.
- `public_win_rate` real, calculated as `public_win_count / public_pick_count` when pick count is nonzero.
- `public_pick_share` real, calculated as `public_pick_count / total_public_pick_count` across the refreshed snapshot.
- `pro_pick_count` integer.
- `pro_win_count` integer.
- `pro_ban_count` integer.
- `refreshed_at` text ISO timestamp in UTC.

The repository should create the table if it does not exist. M6 does not need Alembic migrations.

## Backend Architecture

New modules:

```text
backend/app/data_sources/opendota.py
backend/app/db/repositories.py
backend/app/jobs/refresh_stats.py
backend/app/api/stats.py
```

Responsibilities:

- `opendota.py`: OpenDota client and parser for `/api/heroStats`.
- `repositories.py`: SQLite table creation, upsert, lookup, and ranking queries.
- `refresh_stats.py`: orchestration job that fetches, normalizes, calculates rates, and writes SQLite.
- `stats.py`: FastAPI endpoint for manual refresh.

Existing files to modify:

- `backend/app/main.py`: include stats router.
- `backend/app/rag/chat_service.py`: inject optional stats repository or settings path and answer `stats` questions from SQLite.
- `backend/app/api/chat.py`: wire chat service to SQLite-backed stats lookup.
- `backend/app/core/config.py`: add `opendota_base_url`, defaulting to `https://api.opendota.com/api`.

## Refresh Flow

```text
POST /api/refresh/stats
-> OpenDotaClient.fetch_hero_stats()
-> parse hero stat rows
-> calculate total public picks
-> calculate public win rate and public pick share
-> upsert rows into SQLite
-> return record count and refreshed_at
```

The endpoint should fail clearly if OpenDota is unavailable or returns an unsupported shape. Existing stored stats should remain untouched if fetch or parse fails before the final upsert.

## Chat Flow

For `question_type == "stats"`:

1. Try to detect a hero name from the question using local hero stats names and simple lowercase matching.
2. If a hero is found and stats exist, return a Chinese answer with:
   - hero name,
   - public win rate,
   - public pick share,
   - sample size,
   - refresh timestamp,
   - caveat that OpenDota public-match data is sample-based and not real-time truth.
3. If no hero is detected, return a short top-heroes summary sorted by public pick share or win rate, with the same freshness caveat.
4. If no stats are available, return a clear message asking the user to run `POST /api/refresh/stats`.

M6 should not ask the LLM to invent statistics. Numeric stats answers should be template-backed, not generated from a freeform prompt.

## API Shape

`POST /api/refresh/stats`

Response:

```json
{
  "heroes": 128,
  "refreshed_at": "2026-06-19T09:00:00Z"
}
```

Optional future GET endpoints are out of scope for M6 unless needed for tests. Chat API is the primary user-facing stats path in this milestone.

## Error Handling

- Network failure: return an HTTP 502-style refresh error from the API layer.
- Empty OpenDota result: raise a parse error and do not upsert.
- Missing required fields: raise a parse error identifying the missing field.
- Hero not found in chat question: answer with a top-hero summary if stats exist.
- No local stats yet: answer with a refresh instruction instead of guessing.

## Testing

Backend tests should cover:

- OpenDota parser accepts a fixture row and computes normalized values.
- Parser rejects empty or malformed payloads.
- Repository creates `hero_stats`, upserts rows, looks up by hero name, and returns rankings.
- Refresh job fetches via fixture client and writes expected rows.
- `POST /api/refresh/stats` works with an app-state fixture client and does not call live network.
- Chat service answers a hero stats question from SQLite without invoking the LLM for numeric stats.
- Chat service returns a clear refresh-needed message when stats are absent.

All OpenDota tests must use local fixtures or injected clients.

## Documentation

README should describe:

- How to refresh stats with `POST /api/refresh/stats`.
- That M6 uses OpenDota public-match hero statistics.
- That answers include sample caveats and refresh timestamps.
- That item trends and match samples are intentionally out of scope for M6.

## Acceptance Criteria

- Local SQLite stores refreshed hero stats.
- `POST /api/refresh/stats` returns hero count and refresh timestamp.
- A stats question such as "Axe win rate?" returns a template-backed answer with win rate, pick share, sample size, and freshness.
- Stats answers do not claim real-time global truth.
- Existing knowledge and patch chat still works.
- Backend tests pass.
- Frontend tests and build still pass before M6 is considered complete.

## References

- OpenDota API documentation: `https://docs.opendota.com/`
- OpenDota hero stats endpoint: `https://api.opendota.com/api/heroStats`
