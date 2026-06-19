# M7.1 Demo Polish Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Update the browser demo label and add example question buttons that fill the chat input without auto-sending.

**Architecture:** Keep the change frontend-only. `App.tsx` owns a small constant list of examples and reuses existing `message` state. `App.test.tsx` drives the behavior first, and `styles.css` adds compact button-row styling.

**Tech Stack:** React 18, TypeScript, Vite, Vitest, Testing Library, lucide-react.

---

## File Structure

- Modify `frontend/src/App.test.tsx`: add tests for the demo label and example question buttons.
- Modify `frontend/src/App.tsx`: change the build tag and render example buttons.
- Modify `frontend/src/styles.css`: style the example row and buttons.
- Modify `README.md`: mention example buttons in the browser demo instructions.

## Task 1: Add Demo Polish Behavior

**Files:**
- Modify: `frontend/src/App.test.tsx`
- Modify: `frontend/src/App.tsx`

- [ ] **Step 1: Write failing tests**

Append these tests inside the existing `describe("App", () => { ... })` block in `frontend/src/App.test.tsx`:

```tsx
  test("shows the current demo build tag", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
      new Response(JSON.stringify(healthResponse), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );

    render(<App />);

    await screen.findByText("M7 Demo");
    expect(screen.queryByText("M4")).not.toBeInTheDocument();
  });

  test("fills the chat input from an example question without sending", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
      new Response(JSON.stringify(healthResponse), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );

    render(<App />);

    const input = await screen.findByLabelText("Ask a Dota 2 question");
    fireEvent.click(screen.getByRole("button", { name: "What does BKB do?" }));

    expect(input).toHaveValue("What does BKB do?");
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(screen.getByRole("button", { name: "Send" })).toBeEnabled();
  });

  test("disables example questions while chat is pending", async () => {
    let resolveChat: (value: Response) => void = () => undefined;
    vi.spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(
        new Response(JSON.stringify(healthResponse), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        }),
      )
      .mockImplementationOnce(
        () =>
          new Promise<Response>((resolve) => {
            resolveChat = resolve;
          }),
      );

    render(<App />);

    const input = await screen.findByLabelText("Ask a Dota 2 question");
    fireEvent.change(input, { target: { value: "What does BKB do?" } });
    fireEvent.click(screen.getByRole("button", { name: "Send" }));

    expect(screen.getByRole("button", { name: "What does BKB do?" })).toBeDisabled();

    resolveChat(
      new Response(
        JSON.stringify({
          answer: "Black King Bar grants timed spell immunity.",
          question_type: "knowledge",
          sources: [],
          debug: { retrieved_chunks: 0, top_score: null },
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    );

    await waitFor(() => {
      expect(screen.getByRole("button", { name: "What does BKB do?" })).toBeEnabled();
    });
  });
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```powershell
npm test -- src/App.test.tsx
```

Expected: FAIL because `M7 Demo` and the example buttons do not exist yet.

- [ ] **Step 3: Implement the minimal UI behavior**

In `frontend/src/App.tsx`, add this constant after the `RefreshState` type:

```tsx
const EXAMPLE_QUESTIONS = [
  "What does BKB do?",
  "Roshan drops what?",
  "Axe win rate meta",
  "Blink Dagger怎么用？",
];
```

Change:

```tsx
<span className="buildTag">M4</span>
```

to:

```tsx
<span className="buildTag">M7 Demo</span>
```

Add this JSX inside `<form className="chatForm" onSubmit={submitQuestion}>`, after the `<label>` and before `<div className="inputRow">`:

```tsx
              <div className="exampleRow" aria-label="Example questions">
                {EXAMPLE_QUESTIONS.map((example) => (
                  <button
                    disabled={isSending}
                    key={example}
                    onClick={() => setMessage(example)}
                    type="button"
                  >
                    {example}
                  </button>
                ))}
              </div>
```

- [ ] **Step 4: Run app tests to verify they pass**

Run:

```powershell
npm test -- src/App.test.tsx
```

Expected: PASS for all app tests.

## Task 2: Style And Document Demo Polish

**Files:**
- Modify: `frontend/src/styles.css`
- Modify: `README.md`

- [ ] **Step 1: Add example row styles**

Add this CSS near `.chatForm label` in `frontend/src/styles.css`:

```css
.exampleRow {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 10px;
}

.exampleRow button {
  min-height: 32px;
  padding: 0 10px;
  border: 1px solid #b7c5bc;
  border-radius: 6px;
  background: #f4f6f1;
  color: #33423a;
  font-size: 0.82rem;
  font-weight: 700;
  cursor: pointer;
}

.exampleRow button:disabled {
  cursor: not-allowed;
  opacity: 0.58;
}
```

- [ ] **Step 2: Update README**

Under `## M4 Frontend Chat UI`, after the paragraph about the `Data refresh` panel, add:

```markdown
The chat input includes example question buttons for quick manual testing. Clicking an example fills the input and lets you edit before sending.
```

- [ ] **Step 3: Run full frontend verification**

Run:

```powershell
npm test
npm run build
```

Expected: frontend tests pass and the Vite build succeeds.

- [ ] **Step 4: Manually verify browser demo**

Open or reload `http://127.0.0.1:5173` and verify:

- The build tag reads `M7 Demo`.
- Four example question buttons are visible.
- Clicking `What does BKB do?` fills the input.
- The question is not sent until `Send` is clicked.

- [ ] **Step 5: Commit M7.1 implementation**

Run:

```powershell
git add frontend/src/App.tsx frontend/src/App.test.tsx frontend/src/styles.css README.md
git commit -m "feat: polish demo question shortcuts"
```

## Task 3: Final Status

- [ ] **Step 1: Check repository status**

Run:

```powershell
git status --short --branch
```

Expected: implementation changes are committed. Untracked `.vscode/` may remain.

- [ ] **Step 2: Report verification**

Report test/build results, browser demo status, and remaining untracked files.

