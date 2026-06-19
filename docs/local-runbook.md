# Local Runbook

Date: 2026-06-20

This guide starts the Dota 2 RAG Assistant locally on Windows.

## Prerequisites

- Git
- Node.js and npm
- Conda, or the existing `backend/.conda` environment
- Docker Desktop for Docker Ollama, or a host Ollama service

## Docker Ollama

Run Ollama with Docker:

```powershell
docker volume create ollama
docker run -d --name ollama -p 11434:11434 -v ollama:/root/.ollama ollama/ollama
```

Pull a chat model if the container is new:

```powershell
docker exec ollama ollama pull llama3.2
```

Check Ollama:

```powershell
Invoke-RestMethod -Uri http://127.0.0.1:11434/api/version
```

If you run Ollama directly on the host, keep it listening on `http://127.0.0.1:11434`.

## Backend startup

Use the existing Conda Python directly:

```powershell
cd backend
.\.conda\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

If Conda activation works in your shell:

```powershell
cd backend
C:\Users\jaime\miniforge3\Scripts\conda.exe activate C:\Users\jaime\OneDrive\Desktop\dota2-rag-assistant\backend\.conda
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Check health:

```powershell
Invoke-RestMethod -Uri http://127.0.0.1:8000/api/health
```

## Frontend startup

```powershell
cd frontend
npm install
npm run dev
```

Open:

```text
http://127.0.0.1:5173/
```

## Demo Data Flow

Refresh Knowledge:

```powershell
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/api/ingest/documents
```

Refresh Stats:

```powershell
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/api/refresh/stats
```

In the browser, the same actions are available as `Refresh Knowledge` and `Refresh Stats`.

Ask:

```text
What does BKB do?
Axe win rate meta
斧王胜率
```

Use [demo-checklist.md](demo-checklist.md) for manual demo verification.

## Verification

Backend tests:

```powershell
cd backend
C:\WINDOWS\System32\WindowsPowerShell\v1.0\powershell.exe -Command "`$env:TEMP='C:\Users\jaime\OneDrive\Desktop\dota2-rag-assistant\backend\.tmp'; `$env:TMP=`$env:TEMP; `$env:PYTHONPATH='C:\Users\jaime\OneDrive\Desktop\dota2-rag-assistant\backend\.tmp\py312-packages;C:\Users\jaime\OneDrive\Desktop\dota2-rag-assistant\backend'; C:\Users\jaime\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -m pytest -v -p no:cacheprovider --basetemp .tmp\pytest-final"
```

Frontend tests and build:

```powershell
cd frontend
npm test
npm run build
```

## Troubleshooting

### Ollama Unavailable

Check `http://127.0.0.1:11434/api/version`. If it fails, start the Docker container or host Ollama service.

### OpenDota Refresh Failed

The frontend should show `Stats refresh failed. Check OpenDota/network and retry.` Chat remains usable. Stats answers require a successful local stats refresh.

### Conda Python blocked by Windows policy

If `backend/.conda/python.exe` is blocked, use an allowed Python runtime with the project dependencies or reinstall the Conda environment from a trusted shell. During development, tests were also run with a bundled Python plus dependencies installed under `backend/.tmp/py312-packages`.

### Port Already In Use

Backend default port is `8000`; frontend default port is `5173`. Stop the existing process or start the service on a different port.

### Empty Or Stale Local Data

Run `Refresh Knowledge` after backend startup. Run `Refresh Stats` when OpenDota is reachable. Local vector and SQLite data live under backend-managed local data paths.
