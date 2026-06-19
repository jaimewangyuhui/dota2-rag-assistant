# Dota 2 RAG Assistant

Local-first Dota 2 question-answering assistant with a FastAPI backend, React/Vite frontend, local text retrieval, and OpenDota hero statistics.

The assistant answers in Chinese by default while preserving important English Dota 2 terms such as `Black King Bar / BKB`, `Roshan`, `Blink Dagger`, and hero names.

## Current capabilities

- Web chat UI with source display and demo question shortcuts.
- Backend health, chat, document ingestion, source listing, and stats refresh APIs.
- Read-only knowledge browser APIs and frontend panel for inspecting indexed chunks.
- Local seed knowledge for BKB, Roshan, and Blink Dagger.
- Optional official Dota 2 hero and patch document ingestion.
- OpenDota hero and item constants ingested into the local vector knowledge base.
- OpenDota hero stats stored in local SQLite.
- Alias handling for common Chinese/English Dota terms.
- M9 demo acceptance tests for knowledge, advice, stats, patch, and missing-coverage questions.

## Architecture

```text
frontend React/Vite
-> FastAPI backend
-> question classification and alias normalization
-> local vector retrieval over indexed text
-> optional SQLite hero stats lookup
-> Ollama local generation
-> answer with sources and freshness
```

## Quick Start

Detailed setup is in [docs/local-runbook.md](docs/local-runbook.md).

Start backend:

```powershell
cd backend
.\.conda\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Start frontend:

```powershell
cd frontend
npm install
npm run dev
```

Open:

```text
http://127.0.0.1:5173/
```

Health endpoint:

```text
http://127.0.0.1:8000/api/health
```

## Data Refresh

Refresh text knowledge:

```powershell
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/api/ingest/documents
```

Refresh OpenDota hero stats:

```powershell
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/api/refresh/stats
```

The frontend also exposes `Refresh Knowledge` and `Refresh Stats` buttons.

## Knowledge Browser

The frontend Knowledge panel shows indexed chunk/source counts, entity/source
breakdowns, and preview rows from the local vector store. Use the search box and
filters to inspect local OpenDota hero/item documents before asking chat
questions.

Knowledge browser API endpoints:

```text
GET http://127.0.0.1:8000/api/knowledge/summary
GET http://127.0.0.1:8000/api/knowledge/chunks?q=Axe&entity_type=hero&source_prefix=OpenDota%20Hero&limit=50
```

## Demo Questions

- `What does BKB do?`
- `Blink Dagger cost mobility`
- `Axe roles strength initiator`
- `BKB有什么用？`
- `Roshan 会掉什么？`
- `肉山掉什么？`
- `黑皇杖什么时候出？`
- `Blink Dagger怎么用？`
- `Axe win rate meta`
- `斧王胜率`

Manual demo steps are in [docs/demo-checklist.md](docs/demo-checklist.md).

## Verification

Backend:

```powershell
cd backend
C:\WINDOWS\System32\WindowsPowerShell\v1.0\powershell.exe -Command "`$env:TEMP='C:\Users\jaime\OneDrive\Desktop\dota2-rag-assistant\backend\.tmp'; `$env:TMP=`$env:TEMP; `$env:PYTHONPATH='C:\Users\jaime\OneDrive\Desktop\dota2-rag-assistant\backend\.tmp\py312-packages;C:\Users\jaime\OneDrive\Desktop\dota2-rag-assistant\backend'; C:\Users\jaime\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -m pytest -v -p no:cacheprovider --basetemp .tmp\pytest-final"
```

Frontend:

```powershell
cd frontend
npm test
npm run build
```

## Current Limitations

- Ollama must be running for real local generation.
- OpenDota refresh can fail when the network or API is unavailable.
- Stats answers use OpenDota public-match samples and are not real-time global Meta.
- Full item and ability ingestion are not included yet.
- The project is optimized for local demo and development, not production hosting.

## Documentation

- [Local runbook](docs/local-runbook.md)
- [Demo checklist](docs/demo-checklist.md)
- [M10 design](docs/superpowers/specs/2026-06-20-m10-local-runbook-design.md)
