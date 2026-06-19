# M7 Frontend Refresh Controls Design

## Goal

Add a compact data refresh control surface to the existing web demo so a user can refresh local knowledge documents and OpenDota hero statistics from the browser instead of using PowerShell commands.

M7 turns the current demo into a more usable local workbench. It should make refresh success, failure, and in-progress states visible without adding a separate admin page.

## Approved Scope

M7 includes:

- Add frontend API client functions for `POST /api/ingest/documents` and `POST /api/refresh/stats`.
- Add a compact `Data refresh` panel to the existing single-page interface.
- Provide two manual actions:
  - `Refresh Knowledge`
  - `Refresh Stats`
- Show in-progress state independently for each action.
- Show the latest success summary for each action.
- Show clear retry-oriented failure messages for each action.
- Refresh service health after a successful refresh action.
- Add frontend tests for refresh success, failure, disabled state, and fetch wiring.
- Update README demo instructions.

M7 does not include:

- Scheduled background refresh.
- A separate admin route.
- Charts, tables, or source browsing.
- New backend endpoints.
- New SQLite tables.
- Item trend ingestion.
- Live OpenDota troubleshooting beyond surfacing the API error clearly.

## UI Design

The page remains a chat-first workbench. Add a small `Data refresh` area near the service status strip, before the chat workbench.

The panel should be dense and practical:

- Two buttons with refresh icons.
- Short status text next to each button.
- Success summaries such as `3 documents, 3 chunks, 4 sources` and `128 heroes refreshed`.
- Error summaries such as `Stats refresh failed. Check OpenDota/network and retry.`

The panel should not use a large hero section, modal, or separate page. It should not explain implementation details in the UI.

## Frontend Architecture

Modify:

```text
frontend/src/api/client.ts
frontend/src/api/client.test.ts
frontend/src/App.tsx
frontend/src/App.test.tsx
frontend/src/styles.css
README.md
```

Responsibilities:

- `client.ts`: expose typed `refreshKnowledge()` and `refreshStats()` functions.
- `client.test.ts`: verify the new client functions call the correct endpoints and raise useful errors on non-2xx responses.
- `App.tsx`: own UI state for each refresh action and render the compact panel.
- `App.test.tsx`: verify user-visible refresh behavior.
- `styles.css`: style the refresh panel consistently with the existing status strip and chat layout.
- `README.md`: describe browser-based refresh controls as the preferred demo path.

## API Shapes

Knowledge refresh uses the existing ingestion endpoint:

```json
{
  "documents": 3,
  "chunks": 3,
  "sources": [
    "Official Dota 2: Axe",
    "Seed: Black King Bar",
    "Seed: Blink Dagger",
    "Seed: Roshan"
  ]
}
```

Stats refresh uses the existing OpenDota endpoint:

```json
{
  "heroes": 128,
  "refreshed_at": "2026-06-19T09:00:00Z"
}
```

The frontend should tolerate missing optional detail fields by falling back to a concise success message.

## State Model

Use separate state for each refresh action:

```text
idle -> loading -> success
idle -> loading -> error
success -> loading -> success
success -> loading -> error
error -> loading -> success
error -> loading -> error
```

Knowledge refresh and stats refresh should not block each other unless the same action is already running. Chat sending should remain independent.

After either refresh succeeds, call `fetchHealth()` and update the service status strip. If the health refresh fails, keep the refresh success visible and show the existing service status error pattern only if the app is otherwise in a health error state.

## Error Handling

- Knowledge refresh HTTP failure: show `Knowledge refresh failed. Check backend and retry.`
- Stats refresh HTTP failure: show `Stats refresh failed. Check OpenDota/network and retry.`
- Network or unexpected failure: use the same user-facing messages as the corresponding HTTP failure.
- Do not clear the user's current chat input or chat history when refresh fails.
- Disable only the button for the action currently running.

## Testing

Frontend tests should cover:

- Client calls `POST /api/ingest/documents` and parses the response.
- Client calls `POST /api/refresh/stats` and parses the response.
- Client functions throw action-specific errors on failed responses.
- The app renders refresh buttons after health loads.
- Clicking `Refresh Knowledge` shows a loading state and then a document/chunk/source summary.
- Clicking `Refresh Stats` shows a loading state and then a hero count/freshness summary.
- A failed stats refresh shows the retry-oriented error while preserving chat controls.
- Buttons are disabled only while their own action is pending.

## Acceptance Criteria

- A user can refresh knowledge documents from the browser.
- A user can refresh hero stats from the browser.
- The UI displays success and failure results for both actions.
- The existing chat demo still works.
- Existing service health display still works.
- Frontend tests pass.
- Frontend build passes.
- Backend tests are not required for M7 unless backend code changes.

