# M9 Demo Acceptance Design

Date: 2026-06-19

## Goal

Turn the current local Dota 2 RAG assistant into a more reliable demo by validating real user questions end to end, then fixing only the small gaps that block the demo experience.

M9 is not a data-expansion milestone. It is an acceptance and hardening milestone: define the questions the demo must handle, run them through the backend and browser flow, and add focused tests or small fixes when the behavior is weak.

## Current Context

The project already has:

- A working FastAPI backend and React/Vite frontend.
- Local document ingestion and vector retrieval.
- Official Dota hero and patch document ingestion.
- OpenDota hero stats refresh and SQLite stats lookup.
- Chat UI with source display, data refresh controls, and demo question shortcuts.
- M8 alias handling for `BKB`, `Black King Bar`, `黑皇杖`, `Roshan`, `肉山`, `Axe`, `斧王`, `Blink Dagger`, and `跳刀`.
- Backend golden-question tests for routing and a few answer properties.

The remaining risk is not basic plumbing. The remaining risk is demo realism: a user may ask a normal Dota question and get a weak answer, no source, a confusing missing-data response, or a classification miss.

## Scope

M9 will define and validate a small demo acceptance suite.

The suite should cover:

- Knowledge questions:
  - `BKB有什么用？`
  - `What does BKB do?`
  - `Roshan 会掉什么？`
  - `肉山掉什么？`
- Advice questions:
  - `黑皇杖什么时候出？`
  - `Blink Dagger怎么用？`
  - `跳刀怎么用？`
- Stats questions:
  - `Axe win rate meta`
  - `斧王胜率`
- Patch questions:
  - `7.36 BKB 改了什么？`
  - `最近版本 Roshan 有什么变化？`
- Missing-coverage questions:
  - A question about a hero, item, or mechanic not currently covered by local data.

Each question should have an expected route and an expected answer property. M9 should not require exact generated text because local model output can vary. It should check stable properties instead, such as:

- Correct `question_type`.
- Sources are present for text-backed answers.
- Stats answers use SQLite and include sample caveats.
- Missing-coverage answers are explicit and do not hallucinate.
- Prompt or generated answer preserves important English Dota terms.

## Non-Goals

M9 will not:

- Add full item ingestion.
- Add ability ingestion.
- Add another external provider.
- Add charting or dashboard UI.
- Replace the generator with fixed canned answers.
- Evaluate model quality with subjective scoring or large benchmark suites.
- Claim real-time global Meta accuracy.

## Backend Design

### Demo Acceptance Fixtures

Add a small test fixture or module that lists demo questions and expected properties.

The fixture should be easy to read and extend. A simple list of dataclass-style cases or pytest parameters is enough.

Each case should include:

- `question`
- `expected_type`
- `expected_terms`
- `requires_sources`
- `requires_stats`
- `allows_missing_coverage`

### Backend Acceptance Tests

Add tests that exercise the existing chat service with deterministic components where possible.

Tests should use:

- `DeterministicEmbedder`
- `LocalVectorStore`
- `FakeGenerator`
- Seed or official document ingestion where needed
- A small SQLite stats repository fixture for `Axe`

The goal is to protect routing, retrieval inputs, source presence, and stats behavior without depending on Ollama output.

### Prompt And Missing-Coverage Checks

If acceptance tests reveal weak prompt behavior, M9 may make small prompt changes. Examples:

- Strengthen instructions for missing coverage.
- Ensure source and freshness language appears in the answer contract.
- Keep Chinese section names and English Dota terms.

These changes should stay minimal and be covered by tests.

### Alias Or Classification Fixes

If demo questions reveal a classification miss, M9 may add narrow terms to the existing alias or classifier modules.

Examples:

- Patch wording such as `最近版本`.
- Advice wording such as `什么时候出`.
- Drop/objective wording if it affects route or retrieval.

No broad alias database should be added in M9.

## Frontend And Browser Verification

Frontend changes are not required by default.

M9 should include manual browser verification using the existing demo UI:

- Refresh knowledge.
- Ask at least one knowledge question.
- Ask one stats question if local stats exist.
- Confirm the error state remains clear when OpenDota refresh fails.
- Confirm example question buttons still fill the input correctly.

If the browser verification reveals only text or minor state confusion, M9 may add a very small UI polish. Anything larger should become a later milestone.

## Acceptance Criteria

M9 is complete when:

- A demo acceptance question set exists in tests or test fixtures.
- The acceptance suite covers knowledge, advice, stats, patch, and missing-coverage cases.
- Backend tests verify stable answer properties rather than exact LLM prose.
- Any discovered classification, prompt, or alias gaps in the demo set are fixed with narrow changes.
- Backend full test suite passes.
- Frontend tests and build pass if frontend code is touched.
- A short demo checklist is documented for manual browser testing.

## Risks And Mitigations

- Model output is nondeterministic. Mitigation: test prompt, route, sources, stats path, and deterministic fake-generator responses.
- Demo scope can expand into a full Dota data project. Mitigation: keep M9 limited to the named acceptance questions and small fixes.
- Missing OpenDota connectivity can make live stats refresh fail. Mitigation: tests use local SQLite fixtures, and UI should keep clear error messaging.
- Official data may not include every item/mechanic yet. Mitigation: missing coverage should be explicit and treated as acceptable for unsupported questions.

## Follow-Up Milestones

After M9, likely next milestones are:

- M10: local runbook, README, and one-command startup polish.
- M11: item and ability data ingestion, if the project should answer item-heavy questions.
- M12: merge/PR cleanup and final portfolio-ready demo pass.
