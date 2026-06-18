# Dota 2 RAG Assistant M4 Chat UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the first usable frontend chat workbench that calls the existing `/api/chat` endpoint and displays answers with source citations.

**Architecture:** M4 stays frontend-focused. The existing React app keeps health checking in the top band, adds a typed chat API client in `src/api/client.ts`, and renders a compact workbench in `src/App.tsx` with chat state owned locally by the page.

**Tech Stack:** React 18, TypeScript, Vite, Vitest, Testing Library, existing FastAPI backend `/api/health` and `/api/chat`.

---

## File Structure

- Modify `frontend/src/api/client.ts`: add chat response types and `askChat(message)`.
- Create `frontend/src/api/client.test.ts`: unit tests for `askChat` success and non-OK handling.
- Modify `frontend/src/App.tsx`: render top health band, chat transcript, input, loading state, error state, citations, and debug summary.
- Modify `frontend/src/App.test.tsx`: cover health rendering, successful chat, retry-oriented failure, empty input, and in-flight disabled button.
- Modify `frontend/src/styles.css`: implement Compact Workbench layout, responsive sources panel, stable button/input dimensions, and status chips.
- Modify `README.md`: add a short M4 frontend smoke section.

## Task 1: Typed Chat API Client

**Files:**
- Modify: `frontend/src/api/client.ts`
- Create: `frontend/src/api/client.test.ts`

- [ ] **Step 1: Write failing API client tests**

Create `frontend/src/api/client.test.ts`:

```typescript
import { afterEach, describe, expect, test, vi } from "vitest";

import { askChat } from "./client";

afterEach(() => {
  vi.restoreAllMocks();
});

describe("askChat", () => {
  test("posts the user message and returns the chat response", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          answer: "Black King Bar grants timed spell immunity.",
          question_type: "knowledge",
          sources: [
            {
              source_name: "Seed: Black King Bar",
              source_url: "seed://items/black-king-bar",
              entity_name: "Black King Bar",
              entity_type: "item",
              patch_version: "7.36",
              updated_at: "2026-06-18",
              score: 0.23,
            },
          ],
          debug: { retrieved_chunks: 2, top_score: 0.23 },
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    );

    const response = await askChat("What does BKB do?");

    expect(fetch).toHaveBeenCalledWith("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: "What does BKB do?" }),
    });
    expect(response.answer).toContain("spell immunity");
    expect(response.sources[0].entity_name).toBe("Black King Bar");
  });

  test("throws a retry-oriented error when the chat response is not OK", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
      new Response("server error", { status: 500 }),
    );

    await expect(askChat("What does BKB do?")).rejects.toThrow(
      "Chat request failed. Check backend and Ollama, then retry.",
    );
  });
});
```

- [ ] **Step 2: Run API client tests and verify RED**

Run:

```powershell
cd frontend
npm test -- src/api/client.test.ts
```

Expected: FAIL because `askChat` is not exported from `src/api/client.ts`.

- [ ] **Step 3: Add chat types and API function**

Modify `frontend/src/api/client.ts`:

```typescript
export type ServiceStatus = {
  name: string;
  ok: boolean;
  detail: string;
};

export type HealthResponse = {
  app: string;
  ok: boolean;
  services: ServiceStatus[];
};

export type ChatSource = {
  source_name: string;
  source_url?: string | null;
  entity_name?: string | null;
  entity_type?: string | null;
  patch_version?: string | null;
  updated_at?: string | null;
  score: number;
};

export type ChatDebug = {
  retrieved_chunks: number;
  top_score: number | null;
};

export type ChatResponse = {
  answer: string;
  question_type: string;
  sources: ChatSource[];
  debug: ChatDebug;
};

const CHAT_ERROR = "Chat request failed. Check backend and Ollama, then retry.";

export async function fetchHealth(): Promise<HealthResponse> {
  const response = await fetch("/api/health");
  if (!response.ok) {
    throw new Error(`Health check failed with HTTP ${response.status}`);
  }
  return response.json() as Promise<HealthResponse>;
}

export async function askChat(message: string): Promise<ChatResponse> {
  const response = await fetch("/api/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message }),
  });
  if (!response.ok) {
    throw new Error(CHAT_ERROR);
  }
  return response.json() as Promise<ChatResponse>;
}
```

- [ ] **Step 4: Run API client tests and verify GREEN**

Run:

```powershell
cd frontend
npm test -- src/api/client.test.ts
```

Expected: PASS with 2 tests.

- [ ] **Step 5: Commit API client**

Run:

```powershell
git add frontend/src/api/client.ts frontend/src/api/client.test.ts
git commit -m "feat: add frontend chat api client"
```

## Task 2: Successful Chat Workbench Flow

**Files:**
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/App.test.tsx`

- [ ] **Step 1: Write failing successful chat UI test**

Modify `frontend/src/App.test.tsx` to include this test alongside the existing health test:

```typescript
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, test, vi } from "vitest";

import App from "./App";

const healthResponse = {
  app: "Dota 2 RAG Assistant",
  ok: true,
  services: [
    { name: "backend", ok: true, detail: "ready" },
    { name: "sqlite", ok: true, detail: "ready" },
    { name: "milvus", ok: true, detail: "local vector directory ready" },
    { name: "ollama", ok: true, detail: "0.30.10" },
  ],
};

afterEach(() => {
  vi.restoreAllMocks();
});

test("sends a chat question and displays the answer with sources", async () => {
  vi.spyOn(globalThis, "fetch")
    .mockResolvedValueOnce(
      new Response(JSON.stringify(healthResponse), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    )
    .mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          answer: "Black King Bar grants timed spell immunity.",
          question_type: "knowledge",
          sources: [
            {
              source_name: "Seed: Black King Bar",
              source_url: "seed://items/black-king-bar",
              entity_name: "Black King Bar",
              entity_type: "item",
              patch_version: "7.36",
              updated_at: "2026-06-18",
              score: 0.23,
            },
          ],
          debug: { retrieved_chunks: 2, top_score: 0.23 },
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    );

  render(<App />);

  const input = await screen.findByLabelText("Ask a Dota 2 question");
  fireEvent.change(input, { target: { value: "What does BKB do?" } });
  fireEvent.click(screen.getByRole("button", { name: "Send" }));

  await waitFor(() => {
    expect(screen.getByText("Black King Bar grants timed spell immunity.")).toBeInTheDocument();
  });
  expect(screen.getByText("Seed: Black King Bar")).toBeInTheDocument();
  expect(screen.getByText("Patch 7.36")).toBeInTheDocument();
  expect(screen.getByText("knowledge")).toBeInTheDocument();
});
```

- [ ] **Step 2: Run App tests and verify RED**

Run:

```powershell
cd frontend
npm test -- src/App.test.tsx
```

Expected: FAIL because the chat input labelled `Ask a Dota 2 question` does not exist.

- [ ] **Step 3: Implement minimal successful chat UI**

Modify `frontend/src/App.tsx`:

```typescript
import { AlertCircle, CheckCircle2, RefreshCw, Send } from "lucide-react";
import { FormEvent, useEffect, useMemo, useState } from "react";

import { askChat, ChatResponse, fetchHealth, HealthResponse } from "./api/client";
import "./styles.css";

type LoadState =
  | { status: "loading" }
  | { status: "ready"; health: HealthResponse }
  | { status: "error"; message: string };

type ChatMessage =
  | { id: number; role: "user"; content: string }
  | { id: number; role: "assistant"; content: string; response: ChatResponse };

function App() {
  const [state, setState] = useState<LoadState>({ status: "loading" });
  const [message, setMessage] = useState("");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [chatError, setChatError] = useState<string | null>(null);
  const [isSending, setIsSending] = useState(false);

  useEffect(() => {
    let active = true;
    fetchHealth()
      .then((health) => {
        if (active) setState({ status: "ready", health });
      })
      .catch((error: Error) => {
        if (active) setState({ status: "error", message: error.message });
      });
    return () => {
      active = false;
    };
  }, []);

  const latestAnswer = useMemo(
    () => [...messages].reverse().find((item) => item.role === "assistant"),
    [messages],
  );

  async function submitQuestion(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const question = message.trim();
    if (!question || isSending) return;

    setChatError(null);
    setIsSending(true);
    setMessages((current) => [
      ...current,
      { id: Date.now(), role: "user", content: question },
    ]);

    try {
      const response = await askChat(question);
      setMessages((current) => [
        ...current,
        {
          id: Date.now() + 1,
          role: "assistant",
          content: response.answer,
          response,
        },
      ]);
      setMessage("");
    } catch (error) {
      setChatError(error instanceof Error ? error.message : "Chat request failed. Check backend and Ollama, then retry.");
    } finally {
      setIsSending(false);
    }
  }

  return (
    <main className="shell">
      <section className="workspace" aria-label="Dota 2 RAG workbench">
        <header className="topbar">
          <div>
            <p className="eyebrow">Local Dota 2 RAG</p>
            <h1>Dota 2 RAG Assistant</h1>
          </div>
          <span className="buildTag">M4</span>
        </header>

        {state.status === "loading" && (
          <div className="notice">
            <RefreshCw aria-hidden className="spin" />
            <span>Checking local services</span>
          </div>
        )}

        {state.status === "error" && (
          <div className="notice error">
            <AlertCircle aria-hidden />
            <span>{state.message}</span>
          </div>
        )}

        {state.status === "ready" && (
          <div className="statusStrip" aria-label="Service status">
            {state.health.services.map((service) => (
              <span className={service.ok ? "statusChip ok" : "statusChip bad"} key={service.name}>
                {service.ok ? <CheckCircle2 aria-label="ready" /> : <AlertCircle aria-label="unavailable" />}
                {service.name}: {service.detail}
              </span>
            ))}
          </div>
        )}

        <div className="workbench">
          <section className="chatPanel" aria-label="Chat">
            <div className="chatStream">
              {messages.length === 0 && (
                <div className="emptyState">
                  Ask about Dota 2 items, heroes, patches, or mechanics.
                </div>
              )}
              {messages.map((item) => (
                <article className={`message ${item.role}`} key={item.id}>
                  <p className="messageRole">{item.role === "user" ? "You" : "Assistant"}</p>
                  <p>{item.content}</p>
                  {item.role === "assistant" && (
                    <span className="questionType">{item.response.question_type}</span>
                  )}
                </article>
              ))}
              {isSending && <div className="notice">Asking local model...</div>}
            </div>

            {chatError && (
              <div className="notice error" role="alert">
                <AlertCircle aria-hidden />
                <span>{chatError}</span>
              </div>
            )}

            <form className="chatForm" onSubmit={submitQuestion}>
              <label htmlFor="chat-input">Ask a Dota 2 question</label>
              <div className="inputRow">
                <input
                  id="chat-input"
                  value={message}
                  onChange={(event) => setMessage(event.target.value)}
                  disabled={isSending}
                  placeholder="What does BKB do?"
                />
                <button disabled={isSending || message.trim().length === 0} type="submit">
                  <Send aria-hidden />
                  Send
                </button>
              </div>
            </form>
          </section>

          <aside className="sourcePanel" aria-label="Sources">
            <h2>Sources</h2>
            {!latestAnswer || latestAnswer.role !== "assistant" ? (
              <p>No sources returned</p>
            ) : latestAnswer.response.sources.length === 0 ? (
              <p>No sources returned</p>
            ) : (
              latestAnswer.response.sources.map((source) => (
                <article className="sourceItem" key={`${source.source_name}-${source.source_url ?? ""}`}>
                  <h3>{source.source_name}</h3>
                  {source.entity_name && <p>{source.entity_name}</p>}
                  {source.patch_version && <p>Patch {source.patch_version}</p>}
                  {source.updated_at && <p>Updated {source.updated_at}</p>}
                  <p>Score {source.score.toFixed(2)}</p>
                </article>
              ))
            )}
            {latestAnswer?.role === "assistant" && (
              <p className="debugLine">
                Retrieved {latestAnswer.response.debug.retrieved_chunks} chunks
              </p>
            )}
          </aside>
        </div>
      </section>
    </main>
  );
}

export default App;
```

- [ ] **Step 4: Run App tests and verify GREEN**

Run:

```powershell
cd frontend
npm test -- src/App.test.tsx
```

Expected: PASS for health and successful chat tests.

- [ ] **Step 5: Commit successful chat UI**

Run:

```powershell
git add frontend/src/App.tsx frontend/src/App.test.tsx
git commit -m "feat: add chat workbench flow"
```

## Task 3: Error, Empty Input, and Pending States

**Files:**
- Modify: `frontend/src/App.test.tsx`
- Modify: `frontend/src/App.tsx`

- [ ] **Step 1: Add failing interaction state tests**

Add these tests to `frontend/src/App.test.tsx`:

```typescript
test("keeps an empty question from being sent", async () => {
  const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
    new Response(JSON.stringify(healthResponse), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    }),
  );

  render(<App />);

  await screen.findByLabelText("Ask a Dota 2 question");
  fireEvent.click(screen.getByRole("button", { name: "Send" }));

  expect(fetchMock).toHaveBeenCalledTimes(1);
});

test("shows a retry-oriented error and keeps the question when chat fails", async () => {
  vi.spyOn(globalThis, "fetch")
    .mockResolvedValueOnce(
      new Response(JSON.stringify(healthResponse), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    )
    .mockResolvedValueOnce(new Response("server error", { status: 500 }));

  render(<App />);

  const input = await screen.findByLabelText("Ask a Dota 2 question");
  fireEvent.change(input, { target: { value: "What does BKB do?" } });
  fireEvent.click(screen.getByRole("button", { name: "Send" }));

  await waitFor(() => {
    expect(
      screen.getByText("Chat request failed. Check backend and Ollama, then retry."),
    ).toBeInTheDocument();
  });
  expect(screen.getByDisplayValue("What does BKB do?")).toBeInTheDocument();
});

test("disables the send button while a chat request is pending", async () => {
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

  expect(screen.getByRole("button", { name: "Send" })).toBeDisabled();
  expect(screen.getByText("Asking local model...")).toBeInTheDocument();

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
    expect(screen.getByRole("button", { name: "Send" })).not.toBeDisabled();
  });
});
```

- [ ] **Step 2: Run interaction tests and verify RED**

Run:

```powershell
cd frontend
npm test -- src/App.test.tsx
```

Expected: FAIL if any required state is missing or inaccessible.

- [ ] **Step 3: Adjust App state handling to satisfy tests**

If Task 2 implementation already satisfies a test, leave that code unchanged. Otherwise update `frontend/src/App.tsx` so:

```typescript
const question = message.trim();
if (!question || isSending) return;
```

and failed requests do not call `setMessage("")`; only successful requests clear the input:

```typescript
try {
  const response = await askChat(question);
  setMessages((current) => [
    ...current,
    {
      id: Date.now() + 1,
      role: "assistant",
      content: response.answer,
      response,
    },
  ]);
  setMessage("");
} catch (error) {
  setChatError(
    error instanceof Error
      ? error.message
      : "Chat request failed. Check backend and Ollama, then retry.",
  );
} finally {
  setIsSending(false);
}
```

- [ ] **Step 4: Run App tests and verify GREEN**

Run:

```powershell
cd frontend
npm test -- src/App.test.tsx
```

Expected: PASS for all App tests.

- [ ] **Step 5: Commit interaction states**

Run:

```powershell
git add frontend/src/App.tsx frontend/src/App.test.tsx
git commit -m "feat: handle chat ui states"
```

## Task 4: Compact Workbench Styling and M4 Docs

**Files:**
- Modify: `frontend/src/styles.css`
- Modify: `README.md`

- [ ] **Step 1: Add style expectations to the App tests**

Add assertions to the successful chat test in `frontend/src/App.test.tsx`:

```typescript
expect(screen.getByLabelText("Dota 2 RAG workbench")).toBeInTheDocument();
expect(screen.getByLabelText("Sources")).toBeInTheDocument();
```

- [ ] **Step 2: Run App tests and verify RED or existing GREEN**

Run:

```powershell
cd frontend
npm test -- src/App.test.tsx
```

Expected: PASS if Task 2 already added these labels; otherwise FAIL with missing accessible regions.

- [ ] **Step 3: Replace styles with Compact Workbench CSS**

Modify `frontend/src/styles.css`:

```css
:root {
  color: #17201c;
  background: #edf1ee;
  font-family:
    Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI",
    sans-serif;
}

* {
  box-sizing: border-box;
}

body {
  margin: 0;
}

button,
input {
  font: inherit;
}

.shell {
  min-height: 100vh;
  padding: 24px;
}

.workspace {
  max-width: 1180px;
  margin: 0 auto;
}

.topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 16px 0 18px;
  border-bottom: 1px solid #c8d1c7;
}

.eyebrow {
  margin: 0 0 4px;
  color: #506358;
  font-size: 0.78rem;
  font-weight: 700;
  text-transform: uppercase;
}

h1,
h2,
h3,
p {
  margin: 0;
}

h1 {
  font-size: 2rem;
}

.buildTag {
  display: inline-flex;
  min-width: 44px;
  min-height: 32px;
  align-items: center;
  justify-content: center;
  border: 1px solid #839186;
  border-radius: 6px;
  color: #33423a;
  font-weight: 800;
}

.notice {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 16px;
  color: #33423a;
}

.notice.error {
  color: #9b1c1c;
}

.spin {
  animation: spin 1s linear infinite;
}

.statusStrip {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin: 16px 0 18px;
}

.statusChip {
  display: inline-flex;
  min-height: 34px;
  align-items: center;
  gap: 7px;
  padding: 6px 10px;
  border: 1px solid #c3cdc2;
  border-radius: 6px;
  background: #fbfcfa;
  color: #3a4a41;
  font-size: 0.9rem;
}

.statusChip svg {
  width: 16px;
  height: 16px;
}

.statusChip.ok svg {
  color: #207245;
}

.statusChip.bad svg {
  color: #b83232;
}

.workbench {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 300px;
  gap: 16px;
  align-items: start;
}

.chatPanel,
.sourcePanel {
  border: 1px solid #c3cdc2;
  border-radius: 8px;
  background: #fbfcfa;
}

.chatPanel {
  min-height: 560px;
  display: flex;
  flex-direction: column;
}

.chatStream {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 16px;
}

.emptyState {
  min-height: 180px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #536159;
  text-align: center;
}

.message {
  max-width: 760px;
  padding: 12px;
  border-radius: 8px;
  line-height: 1.5;
}

.message.user {
  align-self: flex-end;
  background: #e4ece6;
}

.message.assistant {
  align-self: flex-start;
  background: #f4f6f1;
  border: 1px solid #d7ded5;
}

.messageRole {
  margin-bottom: 6px;
  color: #506358;
  font-size: 0.78rem;
  font-weight: 800;
  text-transform: uppercase;
}

.questionType {
  display: inline-flex;
  margin-top: 10px;
  padding: 3px 8px;
  border: 1px solid #b7c5bc;
  border-radius: 6px;
  color: #33423a;
  font-size: 0.78rem;
  font-weight: 800;
}

.chatForm {
  padding: 14px;
  border-top: 1px solid #c3cdc2;
}

.chatForm label {
  display: block;
  margin-bottom: 8px;
  color: #506358;
  font-size: 0.86rem;
  font-weight: 800;
}

.inputRow {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 104px;
  gap: 10px;
}

.inputRow input {
  min-height: 44px;
  min-width: 0;
  padding: 0 12px;
  border: 1px solid #aebcaf;
  border-radius: 6px;
  background: #ffffff;
  color: #17201c;
}

.inputRow button {
  display: inline-flex;
  min-height: 44px;
  align-items: center;
  justify-content: center;
  gap: 7px;
  border: 1px solid #31543e;
  border-radius: 6px;
  background: #31543e;
  color: #ffffff;
  font-weight: 800;
  cursor: pointer;
}

.inputRow button:disabled {
  cursor: not-allowed;
  opacity: 0.58;
}

.inputRow button svg {
  width: 16px;
  height: 16px;
}

.sourcePanel {
  padding: 14px;
}

.sourcePanel h2 {
  margin-bottom: 12px;
  font-size: 1rem;
}

.sourceItem {
  padding: 10px 0;
  border-top: 1px solid #d8dfd6;
}

.sourceItem h3 {
  margin-bottom: 6px;
  font-size: 0.95rem;
}

.sourceItem p,
.sourcePanel > p,
.debugLine {
  color: #536159;
  font-size: 0.9rem;
  line-height: 1.45;
  overflow-wrap: anywhere;
}

.debugLine {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid #d8dfd6;
}

@media (max-width: 820px) {
  .shell {
    padding: 16px;
  }

  .topbar {
    align-items: flex-start;
  }

  h1 {
    font-size: 1.65rem;
  }

  .workbench {
    grid-template-columns: 1fr;
  }

  .chatPanel {
    min-height: 520px;
  }

  .inputRow {
    grid-template-columns: 1fr;
  }
}

@keyframes spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}
```

- [ ] **Step 4: Add README M4 smoke instructions**

Append to `README.md`:

```markdown
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
```

- [ ] **Step 5: Run frontend verification**

Run:

```powershell
cd frontend
npm test
npm run build
```

Expected: tests pass and Vite build completes.

- [ ] **Step 6: Run backend regression tests**

Run:

```powershell
cd backend
$env:TEMP="$PWD\.tmp"; $env:TMP=$env:TEMP
.\.conda\python.exe -m pytest -v -p no:cacheprovider --basetemp .tmp\pytest-m4-final
```

Expected: backend tests pass.

- [ ] **Step 7: Manual local smoke**

Run these commands if the services are not already running:

```powershell
docker start ollama
cd backend
.\.conda\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
cd ..\frontend
npm run dev
```

Then run:

```powershell
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/api/ingest/documents
```

Open `http://127.0.0.1:5173`, ask `What does BKB do?`, and confirm the answer plus `Seed: Black King Bar` source appear.

- [ ] **Step 8: Commit M4 UI and docs**

Run:

```powershell
git add frontend/src/App.tsx frontend/src/App.test.tsx frontend/src/styles.css README.md
git commit -m "feat: add m4 chat workbench ui"
```

## Self-Review Notes

- Spec coverage: the plan covers `/api/chat` integration, loading/disabled/success/error states, citations, health visibility, frontend tests, README usage, frontend build, backend regression tests, and manual smoke.
- Scope: the plan does not add streaming, backend memory, routing, global state, accounts, or new backend RAG behavior.
- Type consistency: `ChatResponse`, `ChatSource`, and `ChatDebug` match the backend payload fields used by the UI tests and rendering code.
