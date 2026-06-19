# M7.1 Demo Polish Design

## Goal

Make the current browser demo easier to try by updating the visible milestone label and adding example question buttons that fill the chat input.

This is a small frontend-only polish pass before starting M8 answer quality work.

## Approved Scope

M7.1 includes:

- Change the visible build tag from `M4` to `M7 Demo`.
- Add a compact example question row near the chat input.
- Provide four example questions:
  - `What does BKB do?`
  - `Roshan drops what?`
  - `Axe win rate meta`
  - `Blink Dagger怎么用？`
- Clicking an example fills the chat input.
- Clicking an example does not automatically submit the question.
- Keep the existing refresh panel, chat form, source panel, and service status behavior unchanged.
- Add frontend tests for the visible label and example button behavior.

M7.1 does not include:

- Backend changes.
- New data sources.
- Answer quality or prompt changes.
- Auto-send behavior.
- New routing or a separate demo page.

## UI Design

The demo remains a compact workbench. The build tag should communicate the current usable demo state, so it becomes `M7 Demo`.

Example questions should sit inside the chat panel above the input field. They should be small, button-like controls that are easy to scan and tap. They should not add explanatory copy or crowd the conversation stream.

## Frontend Architecture

Modify:

```text
frontend/src/App.tsx
frontend/src/App.test.tsx
frontend/src/styles.css
README.md
```

Responsibilities:

- `App.tsx`: define the example questions and fill `message` when an example is clicked.
- `App.test.tsx`: verify `M7 Demo` is shown and clicking an example updates the input without sending.
- `styles.css`: style the example row using the existing light workbench style.
- `README.md`: mention that the demo includes example questions for quick testing.

## Behavior

The user flow is:

```text
Open demo
-> Click an example question
-> Input value updates
-> Send button becomes enabled
-> User can edit or click Send
```

If a chat request is already sending, example buttons should be disabled to avoid changing the input mid-request.

## Testing

Frontend tests should cover:

- The build tag displays `M7 Demo`.
- The example buttons render.
- Clicking `What does BKB do?` fills the chat input.
- Clicking an example does not call `/api/chat` until the user clicks `Send`.
- Example buttons are disabled while a chat request is pending.

## Acceptance Criteria

- The demo no longer shows `M4`.
- The demo shows four example questions.
- Example questions fill the input and do not auto-submit.
- Existing chat tests still pass.
- Frontend tests pass.
- Frontend build passes.

