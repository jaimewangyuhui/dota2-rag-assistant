# M10 Local Runbook And Delivery Design

Date: 2026-06-20

## Goal

Make the project easy to run, verify, and present as a local-first Dota 2 RAG assistant. M10 should turn the current working MVP into a more understandable delivery package for the project owner and for someone reviewing the repository.

This milestone focuses on documentation and small repository hygiene only. It should not add new product features or expand data coverage.

## Current Context

The project has working implementation through M9:

- FastAPI backend with health, chat, ingestion, and stats refresh endpoints.
- React/Vite frontend with chat, sources, refresh controls, and demo question shortcuts.
- Local seed knowledge, official Dota hero and patch ingestion, and OpenDota hero stats.
- Alias handling and demo acceptance tests for common Chinese/English Dota questions.
- Demo checklist in `docs/demo-checklist.md`.
- Backend test suite passing at 100 tests and frontend suite passing at 18 tests.

Current delivery gaps:

- `README.md` still describes mostly M1-M6 and does not reflect M7-M9.
- There is no single runbook that walks through Windows, Conda, Docker Ollama, backend, frontend, refresh, and demo testing.
- Demo checklist exists, but README does not clearly point to it.
- `.vscode/` is repeatedly untracked in `git status`; the project should decide whether to ignore it.
- Test commands are known from development but not clearly collected for later use.

## Scope

M10 will update documentation and repository hygiene:

- Refresh `README.md` to describe current capabilities and quick start.
- Add `docs/local-runbook.md` for detailed local setup and troubleshooting.
- Link `docs/demo-checklist.md` from README and runbook.
- Add `.vscode/` to `.gitignore` unless the project intentionally wants to track editor settings.
- Document backend and frontend verification commands.
- Document known caveats:
  - OpenDota refresh can fail due to network/API availability.
  - Ollama must be running for real generation.
  - Stats are OpenDota public-match samples, not real-time global Meta.
  - Item/ability ingestion is not part of the current version.

## Non-Goals

M10 will not:

- Add item ingestion.
- Add ability ingestion.
- Add new crawlers.
- Change frontend UI.
- Change backend behavior.
- Add one-click scripts unless the runbook shows they are necessary.
- Merge branches or create a PR.

## README Design

`README.md` should become the main entry point.

Recommended sections:

- Project summary.
- Current capabilities.
- Architecture overview.
- Quick start.
- Ollama setup.
- Backend commands.
- Frontend commands.
- Refresh data.
- Demo questions.
- Verification commands.
- Documentation links.
- Current limitations.

The README should be concise enough for a reviewer to skim, with detailed instructions moved into `docs/local-runbook.md`.

## Local Runbook Design

`docs/local-runbook.md` should be a practical step-by-step guide for local development on Windows.

It should include:

- Prerequisites:
  - Git
  - Node/npm
  - Conda or existing `backend/.conda`
  - Docker Desktop for Ollama container, or host Ollama
- Ollama with Docker:
  - Pull/run container.
  - Pull required chat model if needed.
  - Confirm `http://127.0.0.1:11434`.
- Backend startup:
  - Activate Conda or use `backend/.conda/python.exe`.
  - Start Uvicorn on `127.0.0.1:8000`.
  - Check `/api/health`.
- Frontend startup:
  - `npm install`
  - `npm run dev`
  - Open `http://127.0.0.1:5173`.
- Demo data flow:
  - Refresh Knowledge.
  - Refresh Stats when OpenDota is reachable.
  - Ask demo questions.
- Verification:
  - Backend pytest command.
  - Frontend test command.
  - Frontend build command.
- Troubleshooting:
  - Ollama unavailable.
  - OpenDota refresh failed.
  - Conda Python blocked by Windows policy.
  - Port already in use.
  - Empty or stale vector/stat data.

## Git Hygiene

Add `.vscode/` to `.gitignore` so local editor state does not keep appearing as an untracked change.

Do not remove or modify the user's local `.vscode/` directory. The change should only prevent accidental staging.

## Testing And Verification

Because M10 is documentation and git hygiene, verification should focus on:

- Markdown files exist and contain the expected sections.
- `.gitignore` includes `.vscode/`.
- Backend test suite still passes.
- Frontend tests still pass.
- Frontend build still succeeds.

If no application code changes, M10 should not require browser visual verification, but the runbook should point to `docs/demo-checklist.md` for manual demo testing.

## Acceptance Criteria

M10 is complete when:

- `README.md` reflects the current M9 project state.
- `docs/local-runbook.md` provides a usable local setup and troubleshooting guide.
- `docs/demo-checklist.md` is referenced by README or runbook.
- `.vscode/` is ignored without deleting local files.
- Backend tests pass.
- Frontend tests and build pass.
- All M10 changes are committed.

## Risks And Mitigations

- Documentation can drift from reality. Mitigation: base commands on existing project structure and run verification commands before completion.
- Windows shell commands can be brittle. Mitigation: include direct executable alternatives where useful.
- Docker Ollama setup can vary by machine. Mitigation: present both Docker and host-service assumptions, and keep health check guidance clear.
- Scope can expand into scripts or deployment automation. Mitigation: keep M10 documentation-first; defer automation to a later milestone if needed.
