# M4 Chat UI Design

## Goal

Build the first usable frontend chat experience for the local Dota 2 RAG assistant. The user should be able to open the app, see local service readiness, ask a Dota 2 question, and inspect the answer sources returned by the existing `/api/chat` endpoint.

## Approved Direction

Use layout option A, "Compact Workbench".

The interface keeps chat as the primary workspace while preserving service status and citations. On desktop, the page uses a compact top status band, a main chat column, and a right-side sources/debug panel. On narrow screens, sources move below the current answer so the input and conversation remain easy to use.

## Scope

M4 includes:

- A frontend chat input connected to `POST /api/chat`.
- Loading, disabled, success, and error states.
- Display of assistant answers, question type, and source citations.
- Retention of the current service health summary from M1.
- Frontend tests for the main chat flow and error handling.

M4 does not include:

- Streaming responses.
- Multi-turn backend conversation memory.
- User accounts, saved sessions, or cloud sync.
- New backend RAG behavior beyond consuming the existing API.
- Large visual redesign of the whole app.

## User Experience

The first viewport should feel like a tool, not a landing page. The user sees the app title, compact service status, a starter prompt area, and a clear message input.

The main interaction is:

1. User types a question such as `What does BKB do?`.
2. User sends the question with a button or Enter.
3. The input disables while the request is running.
4. The answer appears in the chat stream.
5. Sources show source name, entity name, patch version, updated date, score, and URL when present.
6. If the API fails, the app shows a concise error and leaves the question in the input so the user can retry.

Empty state copy should be brief and operational. It should suggest asking about Dota 2 items, heroes, patches, or mechanics without using marketing-style feature descriptions.

## Component Model

Keep the frontend small but split responsibilities enough for tests and later M5 work.

- `src/api.ts`: add a typed `askChat()` client for `/api/chat`.
- `src/types.ts`: add chat response and citation types matching the backend payload.
- `src/App.tsx`: own page state and compose health status plus chat workbench.
- `src/App.test.tsx`: cover rendered UI, successful chat, and failed chat.

Avoid adding routing, global state, or a UI framework in M4.

## Data Flow

The frontend sends:

```json
{
  "message": "What does BKB do?"
}
```

The frontend consumes:

```json
{
  "answer": "Direct conclusion...",
  "question_type": "knowledge",
  "sources": [
    {
      "source_name": "Seed: Black King Bar",
      "source_url": "seed://items/black-king-bar",
      "entity_name": "Black King Bar",
      "entity_type": "item",
      "patch_version": "7.36",
      "updated_at": "2026-06-18",
      "score": 0.23
    }
  ],
  "debug": {
    "retrieved_chunks": 2,
    "top_score": 0.23
  }
}
```

The frontend should tolerate missing optional citation fields, but it should require `answer`, `question_type`, `sources`, and `debug` for the happy path.

## Error Handling

Handle these states explicitly:

- Empty input: do not send; keep focus in the input.
- Request in flight: disable send and prevent duplicate submissions.
- Non-OK API response: show `Chat request failed. Check backend and Ollama, then retry.`
- Network failure: show the same concise retry-oriented error.
- Empty sources: show `No sources returned` near the answer instead of hiding the source area.

## Visual Design

Use a restrained operational style:

- Top band: app title and service status chips.
- Main chat area: stacked messages with stable spacing.
- Right panel on desktop: latest answer sources and debug summary.
- Mobile: single column, sources below answer cards.
- Buttons should use clear command text and stable dimensions.
- Avoid decorative hero sections, nested cards, oversized headings, or one-note color palettes.

## Testing

Frontend tests should verify:

- The health status still renders.
- The chat input and send button render.
- Sending a question calls `/api/chat` and displays answer plus source.
- A failed chat request displays the retry-oriented error.
- The send button is disabled while a request is pending.

Manual verification should use the local stack:

1. Start Ollama Docker container.
2. Ensure `qwen2.5:7b` exists.
3. Start backend on `127.0.0.1:8000`.
4. Ingest seed documents.
5. Start frontend on `127.0.0.1:5173`.
6. Ask `What does BKB do?` and confirm answer plus source citation render.

## Acceptance Criteria

- User can ask a question from the frontend without using PowerShell.
- Successful answers include visible source citations.
- Failed requests produce a clear retry-oriented error.
- Existing health status remains visible.
- `npm test`, `npm run build`, and backend pytest pass before M4 is marked complete.
