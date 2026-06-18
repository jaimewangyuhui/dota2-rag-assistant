# Dota 2 RAG Assistant Design

Date: 2026-06-18

## Goal

Build a local-first Dota 2 question-answering assistant with a web chat UI and API backend. The assistant should answer in Chinese while preserving important English Dota 2 terms, such as `Black King Bar / BKB`, `Roshan`, `Blink Dagger`, and hero or ability names.

The first production shape is a data-enhanced RAG assistant: it combines retrieved text knowledge with structured match and hero statistics. It should support basic knowledge questions, patch and mechanic explanations, Meta-oriented questions, and cautious gameplay suggestions.

## Non-Goals For Version 1

Version 1 will not include login, multi-user permissions, live match detection, Dota client integration, advanced admin UI, paid cloud deployment, or real-time professional match analysis. It will also avoid absolute gameplay claims such as "must buy" or "always pick"; advice should be framed as context-dependent.

## Product Scope

The assistant will support these question types:

- Knowledge explanation: hero, item, skill, map, Roshan, warding, BKB, dispel, damage type, and other core mechanics.
- Patch explanation: what changed in a patch and how the change affects heroes, items, or playstyle.
- Data and Meta questions: hero win rate, pick trends, common item choices, and sample-based public match trends.
- Gameplay suggestions: lane, item, counter, timing, and teamfight suggestions based on retrieved knowledge and available statistics.

Answers should use this structure by default:

- Direct conclusion.
- Key reasons.
- Recommended actions or cautions.
- Relevant English terms.
- Sources and data freshness.

If the knowledge base or statistics do not cover a question, the assistant must say so clearly instead of guessing.

## Architecture

The system has five layers:

- Web frontend: React, Vite, and TypeScript chat interface.
- API backend: FastAPI service for chat, ingestion, statistics refresh, and health checks.
- RAG knowledge layer: text ingestion, chunking, embedding, Milvus vector retrieval, prompt assembly.
- Structured statistics layer: OpenDota and local mappings stored in SQLite.
- Local model layer: Ollama for local chat and embedding models.

Data flow:

```text
User question
-> Web chat UI
-> FastAPI backend
-> Question classification
-> Milvus text retrieval
-> Optional SQLite statistics query
-> Context assembly
-> Ollama local model
-> Answer with sources and freshness
-> Web chat UI
```

## Data Sources

Text knowledge sources:

- Official Dota 2 hero, item, and patch information.
- Dota 2 Wiki pages for heroes, abilities, items, mechanics, and patch details.
- Liquipedia basic reference pages, if useful after the core ingestion pipeline works.

Structured data sources:

- OpenDota API for public match samples, hero statistics, and basic trend data.
- Local static mappings for hero IDs, item IDs, patch versions, and display names.

Dotabuff and STRATZ are not required for version 1 because they add access, permission, or scraping complexity. They can be evaluated later.

## Storage Responsibilities

Milvus stores vectorized text chunks. It is responsible for semantic retrieval over hero descriptions, item explanations, patch notes, and mechanics.

SQLite stores structured data that needs filtering, sorting, grouping, and timestamping. This includes heroes, items, patches, hero statistics, popular items, match samples, and refresh logs.

This split is intentional:

- Milvus answers "which text is semantically related to the question?"
- SQLite answers "which rows match this filter or ranking?"

## Vector Database Choice

The vector database will be Milvus.

Local development should start with Milvus Lite to keep setup lightweight. When the project needs larger data volume or service-style deployment, it can move to Milvus Standalone through Docker.

The code should isolate vector operations behind a small adapter so the rest of the RAG pipeline does not depend directly on Milvus implementation details.

## Backend Design

Recommended stack:

- Python 3.11+
- FastAPI
- Pydantic
- SQLAlchemy or SQLModel
- SQLite
- httpx
- BeautifulSoup or trafilatura
- pymilvus and Milvus Lite
- Ollama local API

Initial endpoints:

- `GET /api/health`: return backend, SQLite, Milvus, and Ollama status.
- `POST /api/chat`: answer a user question.
- `GET /api/sources`: list indexed sources.
- `POST /api/ingest/documents`: ingest or re-ingest text knowledge.
- `POST /api/refresh/stats`: refresh OpenDota-derived structured data.

## Frontend Design

The frontend should be a usable chat tool, not a landing page.

Core UI features:

- Chat input and message history.
- Loading, error, and disconnected states.
- Source list below assistant answers.
- Data freshness display for statistics-based answers.
- Optional debug display for question type and retrieved chunks.

The UI should stay compact and practical, optimized for repeated use while playing or studying Dota 2.

## Ingestion Pipeline

Text ingestion:

```text
source page or document
-> fetch
-> extract main text
-> normalize names and metadata
-> split into chunks
-> embed locally
-> store vectors in Milvus
```

Each chunk should include metadata:

- `source_url`
- `source_name`
- `patch_version`
- `entity_type`
- `entity_name`
- `updated_at`

Structured statistics ingestion:

```text
OpenDota API
-> fetch raw JSON
-> normalize hero, item, and match IDs
-> compute or store relevant statistics
-> write to SQLite
-> record refresh timestamp
```

Version 1 only needs enough data to answer sample-based Meta and item trend questions. It should not claim global real-time accuracy.

## RAG Answer Strategy

Question classification categories:

- `knowledge`
- `patch`
- `stats`
- `advice`

Retrieval strategy:

- Knowledge and patch questions query Milvus first.
- Stats questions query SQLite first, then optionally retrieve explanatory text from Milvus.
- Advice questions query both Milvus and SQLite when relevant.

Generation rules:

- Prefer concise Chinese explanations with English terms preserved.
- Include sources for text-backed answers.
- Include data timestamp and sample caveat for statistics-backed answers.
- Say "当前知识库没有覆盖" or equivalent when retrieval is insufficient.
- Avoid unsupported claims.

## Project Structure

```text
dota2-rag-assistant/
  backend/
    app/
      api/
        chat.py
        ingest.py
        stats.py
      core/
        config.py
        logging.py
      rag/
        classifier.py
        retriever.py
        prompt_builder.py
        generator.py
      data_sources/
        opendota.py
        dota_wiki.py
        patch_notes.py
      db/
        models.py
        session.py
        repositories.py
      vector_store/
        milvus.py
        schemas.py
      jobs/
        refresh_stats.py
        ingest_documents.py
      tests/
    pyproject.toml
    .env.example

  frontend/
    src/
      components/
        ChatPanel.tsx
        SourceList.tsx
        DataFreshness.tsx
      api/
        client.ts
      App.tsx
    package.json

  data/
    raw/
    processed/
    milvus/
    sqlite/

  docs/
    architecture.md
    data-sources.md
    roadmap.md

  docker/
    docker-compose.milvus.yml

  README.md
```

## Milestones

### M1: Project Skeleton And Local Services

Create the FastAPI backend, React frontend, environment configuration, SQLite initialization, Milvus Lite adapter, and Ollama health check.

Acceptance criteria:

- `GET /api/health` reports backend, SQLite, Milvus, and Ollama status.
- The frontend can display service connection status.

### M2: Text Knowledge Ingestion

Create document and chunk models, ingest a small set of hero, item, and patch data, create local embeddings, and store vectors in Milvus.

Acceptance criteria:

- A developer can retrieve relevant chunks for test questions.
- Each retrieved chunk includes source metadata.

### M3: Basic RAG Chat

Implement question classification, Milvus retrieval, prompt building, Ollama generation, and source return.

Acceptance criteria:

- Questions such as "BKB 有什么用?" and "Roshan 会掉什么?" return useful answers with sources.
- Missing-coverage questions produce an explicit uncertainty response.

### M4: OpenDota Statistics Layer

Fetch and store OpenDota-derived statistics in SQLite. Add query functions for hero stats, public match samples, and popular item trends.

Acceptance criteria:

- The assistant can answer sample-based Meta questions.
- Statistics answers include sample scope and refresh timestamp.

### M5: Web Chat Experience

Build the usable local web chat interface with source display, freshness display, loading states, and error states.

Acceptance criteria:

- A user can ask multiple questions in the browser.
- Answers show sources and data freshness where applicable.
- Ollama or backend failures are shown clearly.

## Testing Strategy

Backend tests:

- Unit tests for question classification.
- Unit tests for prompt construction.
- Repository tests for SQLite reads and writes.
- Vector adapter tests using a small local Milvus Lite collection.
- API tests for health, chat, ingestion, and stats refresh endpoints.

RAG quality checks:

- Golden questions for heroes, items, mechanics, patch notes, and Meta data.
- Regression checks to ensure answers cite sources and avoid unsupported claims.

Frontend tests:

- Component tests for chat rendering, source display, loading states, and error states.
- Manual browser verification for the first version.

## Risks And Mitigations

- Local model quality may be weaker than cloud models. Mitigation: keep prompts constrained and rely on retrieved context.
- OpenDota data may be incomplete or delayed. Mitigation: display sample scope and refresh timestamp.
- Dota 2 terminology may mismatch between Chinese and English. Mitigation: maintain static alias mappings for heroes, items, abilities, and common abbreviations.
- Milvus setup may be heavier than Chroma. Mitigation: start with Milvus Lite and keep vector storage behind an adapter.
- Advice questions can become speculative. Mitigation: distinguish retrieved facts from recommendations and use cautious language.

## Future Extensions

- Add reranking for better retrieval quality.
- Add STRATZ or other richer data providers.
- Add Discord or chat platform bot integration.
- Add user-configurable skill bracket and preferred role.
- Add replay or match ID analysis.
- Add cloud deployment with Milvus Standalone and Postgres.
