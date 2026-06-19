# M10 Local Runbook Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Update repository documentation and hygiene so the Dota 2 RAG assistant is easy to run, verify, and demo locally.

**Architecture:** Keep M10 documentation-first. Add lightweight tests that assert the README/runbook/gitignore contract, then update `README.md`, create `docs/local-runbook.md`, and ignore local `.vscode/` without deleting user files.

**Tech Stack:** Markdown docs, pytest for documentation contract checks, existing backend/frontend test commands.

---

## File Structure

- Modify `README.md`: current project overview, quick start, commands, links, limitations.
- Create `docs/local-runbook.md`: detailed Windows local setup, Docker Ollama, backend/frontend startup, verification, troubleshooting.
- Modify `.gitignore`: add `.vscode/`.
- Create `backend/tests/test_docs_delivery.py`: documentation and git hygiene contract tests.

## Task 1: Documentation Contract Tests

**Files:**
- Create: `backend/tests/test_docs_delivery.py`

- [ ] **Step 1: Write failing documentation tests**

Create `backend/tests/test_docs_delivery.py`:

```python
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def read_repo_file(relative_path: str) -> str:
    return (REPO_ROOT / relative_path).read_text(encoding="utf-8")


def test_readme_links_current_demo_and_runbook_docs() -> None:
    readme = read_repo_file("README.md")

    assert "Current capabilities" in readme
    assert "docs/local-runbook.md" in readme
    assert "docs/demo-checklist.md" in readme
    assert "M9" in readme


def test_local_runbook_covers_required_local_setup_topics() -> None:
    runbook = read_repo_file("docs/local-runbook.md")

    for expected in [
        "Docker Ollama",
        "Backend startup",
        "Frontend startup",
        "Refresh Knowledge",
        "Refresh Stats",
        "Verification",
        "Troubleshooting",
        "Conda Python blocked by Windows policy",
    ]:
        assert expected in runbook


def test_gitignore_ignores_local_vscode_directory() -> None:
    gitignore = read_repo_file(".gitignore")

    assert ".vscode/" in gitignore
```

- [ ] **Step 2: Run tests to verify they fail**

Run from `backend/`:

```powershell
C:\WINDOWS\System32\WindowsPowerShell\v1.0\powershell.exe -Command "`$env:TEMP='C:\Users\jaime\OneDrive\Desktop\dota2-rag-assistant\backend\.tmp'; `$env:TMP=`$env:TEMP; `$env:PYTHONPATH='C:\Users\jaime\OneDrive\Desktop\dota2-rag-assistant\backend\.tmp\py312-packages;C:\Users\jaime\OneDrive\Desktop\dota2-rag-assistant\backend'; C:\Users\jaime\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -m pytest tests/test_docs_delivery.py -v -p no:cacheprovider --basetemp .tmp\pytest-m10-docs"
```

Expected: FAIL because `docs/local-runbook.md` does not exist and README/.gitignore do not yet satisfy the contract.

- [ ] **Step 3: Commit only if the failing test file needs a checkpoint**

Do not commit yet if the next task will immediately make these tests pass.

## Task 2: README, Runbook, And Gitignore

**Files:**
- Modify: `README.md`
- Create: `docs/local-runbook.md`
- Modify: `.gitignore`
- Test: `backend/tests/test_docs_delivery.py`

- [ ] **Step 1: Update `.gitignore`**

Add this line near other local/editor ignores in `.gitignore`:

```gitignore
.vscode/
```

- [ ] **Step 2: Replace README with current project overview**

Replace `README.md` with:

```markdown
# Dota 2 RAG Assistant

Local-first Dota 2 question-answering assistant with a FastAPI backend, React/Vite frontend, local text retrieval, and OpenDota hero statistics.

The assistant answers in Chinese by default while preserving important English Dota 2 terms such as `Black King Bar / BKB`, `Roshan`, `Blink Dagger`, and hero names.

## Current capabilities

- Web chat UI with source display and demo question shortcuts.
- Backend health, chat, document ingestion, source listing, and stats refresh APIs.
- Local seed knowledge for BKB, Roshan, and Blink Dagger.
- Optional official Dota 2 hero and patch document ingestion.
- OpenDota hero stats stored in local SQLite.
- Alias handling for common Chinese/English Dota terms.
- Demo acceptance tests for knowledge, advice, stats, patch, and missing-coverage questions.

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

## Quick start

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

## Data refresh

Refresh text knowledge:

```powershell
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/api/ingest/documents
```

Refresh OpenDota hero stats:

```powershell
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/api/refresh/stats
```

The frontend also exposes `Refresh Knowledge` and `Refresh Stats` buttons.

## Demo questions

- `What does BKB do?`
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

## Current limitations

- Ollama must be running for real local generation.
- OpenDota refresh can fail when the network or API is unavailable.
- Stats answers use OpenDota public-match samples and are not real-time global Meta.
- Full item and ability ingestion are not included yet.
- The project is optimized for local demo and development, not production hosting.

## Documentation

- [Local runbook](docs/local-runbook.md)
- [Demo checklist](docs/demo-checklist.md)
- [M10 design](docs/superpowers/specs/2026-06-20-m10-local-runbook-design.md)
```

- [ ] **Step 3: Add local runbook**

Create `docs/local-runbook.md`:

```markdown
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

## Demo data flow

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

### Ollama unavailable

Check `http://127.0.0.1:11434/api/version`. If it fails, start the Docker container or host Ollama service.

### OpenDota refresh failed

The frontend should show `Stats refresh failed. Check OpenDota/network and retry.` Chat remains usable. Stats answers require a successful local stats refresh.

### Conda Python blocked by Windows policy

If `backend/.conda/python.exe` is blocked, use an allowed Python runtime with the project dependencies or reinstall the Conda environment from a trusted shell. During development, tests were also run with a bundled Python plus dependencies installed under `backend/.tmp/py312-packages`.

### Port already in use

Backend default port is `8000`; frontend default port is `5173`. Stop the existing process or start the service on a different port.

### Empty or stale local data

Run `Refresh Knowledge` after backend startup. Run `Refresh Stats` when OpenDota is reachable. Local vector and SQLite data live under backend-managed local data paths.
```

- [ ] **Step 4: Run documentation tests**

Run from `backend/`:

```powershell
C:\WINDOWS\System32\WindowsPowerShell\v1.0\powershell.exe -Command "`$env:TEMP='C:\Users\jaime\OneDrive\Desktop\dota2-rag-assistant\backend\.tmp'; `$env:TMP=`$env:TEMP; `$env:PYTHONPATH='C:\Users\jaime\OneDrive\Desktop\dota2-rag-assistant\backend\.tmp\py312-packages;C:\Users\jaime\OneDrive\Desktop\dota2-rag-assistant\backend'; C:\Users\jaime\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -m pytest tests/test_docs_delivery.py -v -p no:cacheprovider --basetemp .tmp\pytest-m10-docs"
```

Expected: all documentation contract tests PASS.

- [ ] **Step 5: Commit**

```powershell
git add README.md docs/local-runbook.md .gitignore backend/tests/test_docs_delivery.py
git commit -m "docs: update local runbook and delivery guide"
```

## Task 3: Full Verification

**Files:**
- No expected source changes.

- [ ] **Step 1: Run backend full test suite**

Run from `backend/`:

```powershell
C:\WINDOWS\System32\WindowsPowerShell\v1.0\powershell.exe -Command "`$env:TEMP='C:\Users\jaime\OneDrive\Desktop\dota2-rag-assistant\backend\.tmp'; `$env:TMP=`$env:TEMP; `$env:PYTHONPATH='C:\Users\jaime\OneDrive\Desktop\dota2-rag-assistant\backend\.tmp\py312-packages;C:\Users\jaime\OneDrive\Desktop\dota2-rag-assistant\backend'; C:\Users\jaime\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -m pytest -v -p no:cacheprovider --basetemp .tmp\pytest-m10-final"
```

Expected: all backend tests PASS.

- [ ] **Step 2: Run frontend tests**

Run from `frontend/`:

```powershell
npm test
```

Expected: all frontend tests PASS.

- [ ] **Step 3: Run frontend build**

Run from `frontend/`:

```powershell
npm run build
```

Expected: Vite build succeeds.

- [ ] **Step 4: Inspect git status**

Run from repo root:

```powershell
git status --short --branch
```

Expected: branch is ahead by M10 commits with no unintended untracked `.vscode/` entry.

- [ ] **Step 5: Commit any verification-only doc corrections**

Only if verification uncovered a documentation correction:

```powershell
git add README.md docs/local-runbook.md .gitignore backend/tests/test_docs_delivery.py
git commit -m "docs: fix local delivery notes"
```

## Self-Review

- Spec coverage: README refresh, local runbook, demo checklist links, `.vscode/` ignore, verification commands, and known caveats are covered.
- Scope check: no feature work, no UI changes, no backend behavior changes, no new data source.
- Type consistency: documentation tests use only file-path checks and section-string contracts.
- Execution style: documentation changes are preceded by failing contract tests and followed by full verification.
