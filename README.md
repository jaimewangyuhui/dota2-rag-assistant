# Dota 2 RAG Assistant

Local-first Dota 2 RAG assistant. M1 provides the runnable backend skeleton and a compact frontend service-status view.

## Backend

This project uses a local Conda environment at `backend/.conda`.

```powershell
cd backend
C:\Users\jaime\miniforge3\Scripts\conda.exe activate C:\Users\jaime\OneDrive\Desktop\dota2-rag-assistant\backend\.conda
python -m pip install -e ".[dev]"
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

If your shell cannot activate Conda, use the environment Python directly:

```powershell
cd backend
.\.conda\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Health endpoint:

```text
http://127.0.0.1:8000/api/health
```

## Frontend

```powershell
cd frontend
npm install
npm run dev
```

Frontend URL:

```text
http://127.0.0.1:5173
```

## M1 Verification

```powershell
cd backend
.\.conda\python.exe -m pytest -v -p no:cacheprovider --basetemp .tmp\pytest-full

cd ..\frontend
npm test
npm run build
```

Ollama can be unavailable during M1. The health endpoint still responds and marks `ollama` as unavailable with the connection detail.

## M2 Text Ingestion

Seed the local text knowledge index:

```powershell
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/api/ingest/documents
```

List indexed sources:

```powershell
Invoke-RestMethod -Uri http://127.0.0.1:8000/api/sources
```

The M2 seed index includes `Black King Bar`, `Roshan`, and `Blink Dagger` documents. Runtime ingestion uses a deterministic local embedding for repeatable development checks; `OllamaEmbedder` is available for later model-backed ingestion once the embedding model is pulled.

## M3 Basic RAG Chat

Seed the local index before asking questions:

```powershell
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/api/ingest/documents
```

Ask a question:

```powershell
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/api/chat -ContentType "application/json" -Body '{"message":"What does BKB do?"}'
```

M3 returns `answer`, `question_type`, `sources`, and `debug`. Runtime generation uses `OLLAMA_BASE_URL` and `OLLAMA_CHAT_MODEL`; if the indexed sources do not cover a question, the assistant returns an explicit uncertainty answer instead of guessing.

## M4 Frontend Chat UI

After backend and frontend are running, open:

```text
http://127.0.0.1:5173
```

The browser demo also includes a `Data refresh` panel. Use `Refresh Knowledge` to call `POST /api/ingest/documents` and `Refresh Stats` to call `POST /api/refresh/stats` without leaving the UI.

The chat input includes example question buttons for quick manual testing. Clicking an example fills the input and lets you edit before sending.

Ask:

```text
What does BKB do?
```

The page should show the assistant answer, the `knowledge` question type, and source citations such as `Seed: Black King Bar`.

## M5 Official Heroes And Patches

M5 can index official Dota 2 hero and patch note documents in addition to local seed documents.

Official website fetching is disabled by default so local tests and offline development remain deterministic. Set `OFFICIAL_DOTA_SOURCES_ENABLED=true` before starting the backend to include live official heroes and patches during ingestion.

```powershell
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/api/ingest/documents
```

Tests use local fixtures and do not call `dota2.com`. Official item scraping is intentionally out of scope for M5.

## M6 OpenDota Hero Stats

M6 adds a local SQLite snapshot of OpenDota public-match hero statistics.

Refresh the local stats snapshot:

```powershell
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/api/refresh/stats
```

In the frontend demo, prefer the `Refresh Stats` button for manual testing. If OpenDota is unavailable, the UI shows a retry-oriented error and existing chat remains usable.

Then ask a stats question:

```powershell
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/api/chat -ContentType "application/json" -Body '{"message":"Axe win rate meta"}'
```

M6 stats answers include public win rate, public pick share, sample size, and refresh timestamp. They are OpenDota public-match samples, not real-time global truth. Item trends and match sample analysis are intentionally out of scope for M6.
