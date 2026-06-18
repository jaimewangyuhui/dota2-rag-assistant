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
