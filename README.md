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

Ask:

```text
What does BKB do?
```

The page should show the assistant answer, the `knowledge` question type, and source citations such as `Seed: Black King Bar`.
