# M7 Frontend Refresh Controls Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add browser-based knowledge and stats refresh controls to the existing Dota 2 RAG demo.

**Architecture:** Keep M7 frontend-only by calling the existing backend endpoints from `frontend/src/api/client.ts`. `App.tsx` owns two independent refresh state machines and renders a compact panel near service health. Tests drive client fetch behavior first, then user-visible app behavior.

**Tech Stack:** React 18, TypeScript, Vite, Vitest, Testing Library, lucide-react, existing FastAPI endpoints.

---

## File Structure

- Modify `frontend/src/api/client.ts`: add response types and `refreshKnowledge()` / `refreshStats()` functions.
- Modify `frontend/src/api/client.test.ts`: add client tests for both refresh functions and error messages.
- Modify `frontend/src/App.tsx`: add refresh state, handlers, panel rendering, and health recheck after success.
- Modify `frontend/src/App.test.tsx`: add UI tests for refresh success, failure, and independent disabled states.
- Modify `frontend/src/styles.css`: add compact refresh panel styling that fits the existing workbench.
- Modify `README.md`: document browser demo refresh controls.

## Commands

Run frontend commands from:

```powershell
cd C:\Users\jaime\OneDrive\Desktop\dota2-rag-assistant\frontend
```

Use:

```powershell
npm test
npm run build
```

## Task 1: Add Refresh API Client Functions

**Files:**
- Modify: `frontend/src/api/client.test.ts`
- Modify: `frontend/src/api/client.ts`

- [ ] **Step 1: Write failing client tests**

Add imports:

```ts
import { askChat, refreshKnowledge, refreshStats } from "./client";
```

Append these tests to `frontend/src/api/client.test.ts`:

```ts
describe("refreshKnowledge", () => {
  test("posts to the document ingestion endpoint and returns the summary", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          documents: 3,
          chunks: 3,
          sources: [
            "Official Dota 2: Axe",
            "Seed: Black King Bar",
            "Seed: Blink Dagger",
            "Seed: Roshan",
          ],
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    );

    const response = await refreshKnowledge();

    expect(fetch).toHaveBeenCalledWith("/api/ingest/documents", {
      method: "POST",
    });
    expect(response.documents).toBe(3);
    expect(response.chunks).toBe(3);
    expect(response.sources).toHaveLength(4);
  });

  test("throws a retry-oriented error when document ingestion fails", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
      new Response("server error", { status: 500 }),
    );

    await expect(refreshKnowledge()).rejects.toThrow(
      "Knowledge refresh failed. Check backend and retry.",
    );
  });
});

describe("refreshStats", () => {
  test("posts to the stats refresh endpoint and returns the summary", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          heroes: 128,
          refreshed_at: "2026-06-19T09:00:00Z",
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    );

    const response = await refreshStats();

    expect(fetch).toHaveBeenCalledWith("/api/refresh/stats", {
      method: "POST",
    });
    expect(response.heroes).toBe(128);
    expect(response.refreshed_at).toBe("2026-06-19T09:00:00Z");
  });

  test("throws a retry-oriented error when stats refresh fails", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
      new Response("server error", { status: 502 }),
    );

    await expect(refreshStats()).rejects.toThrow(
      "Stats refresh failed. Check OpenDota/network and retry.",
    );
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```powershell
npm test -- src/api/client.test.ts
```

Expected: FAIL because `refreshKnowledge` and `refreshStats` are not exported from `./client`.

- [ ] **Step 3: Implement client functions**

Add these types and constants in `frontend/src/api/client.ts` after `HealthResponse`:

```ts
export type KnowledgeRefreshResponse = {
  documents: number;
  chunks: number;
  sources: string[];
};

export type StatsRefreshResponse = {
  heroes: number;
  refreshed_at: string;
};
```

Add constants after `CHAT_ERROR`:

```ts
const KNOWLEDGE_REFRESH_ERROR =
  "Knowledge refresh failed. Check backend and retry.";
const STATS_REFRESH_ERROR =
  "Stats refresh failed. Check OpenDota/network and retry.";
```

Add functions after `askChat`:

```ts
export async function refreshKnowledge(): Promise<KnowledgeRefreshResponse> {
  const response = await fetch("/api/ingest/documents", {
    method: "POST",
  });
  if (!response.ok) {
    throw new Error(KNOWLEDGE_REFRESH_ERROR);
  }
  return response.json() as Promise<KnowledgeRefreshResponse>;
}

export async function refreshStats(): Promise<StatsRefreshResponse> {
  const response = await fetch("/api/refresh/stats", {
    method: "POST",
  });
  if (!response.ok) {
    throw new Error(STATS_REFRESH_ERROR);
  }
  return response.json() as Promise<StatsRefreshResponse>;
}
```

- [ ] **Step 4: Run client tests to verify they pass**

Run:

```powershell
npm test -- src/api/client.test.ts
```

Expected: PASS for `askChat`, `refreshKnowledge`, and `refreshStats`.

- [ ] **Step 5: Commit client layer**

Run:

```powershell
git add frontend/src/api/client.ts frontend/src/api/client.test.ts
git commit -m "feat: add frontend refresh api client"
```

## Task 2: Add Refresh Panel Behavior

**Files:**
- Modify: `frontend/src/App.test.tsx`
- Modify: `frontend/src/App.tsx`

- [ ] **Step 1: Write failing UI tests**

Append these tests to `frontend/src/App.test.tsx`:

```tsx
  test("refreshes knowledge documents from the browser", async () => {
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
            documents: 3,
            chunks: 3,
            sources: [
              "Official Dota 2: Axe",
              "Seed: Black King Bar",
              "Seed: Blink Dagger",
              "Seed: Roshan",
            ],
          }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        ),
      )
      .mockResolvedValueOnce(
        new Response(JSON.stringify(healthResponse), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        }),
      );

    render(<App />);

    await screen.findByLabelText("Data refresh");
    fireEvent.click(screen.getByRole("button", { name: "Refresh Knowledge" }));

    expect(screen.getByText("Refreshing knowledge...")).toBeInTheDocument();
    await waitFor(() => {
      expect(
        screen.getByText("3 documents, 3 chunks, 4 sources"),
      ).toBeInTheDocument();
    });
  });

  test("refreshes hero stats from the browser", async () => {
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
            heroes: 128,
            refreshed_at: "2026-06-19T09:00:00Z",
          }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        ),
      )
      .mockResolvedValueOnce(
        new Response(JSON.stringify(healthResponse), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        }),
      );

    render(<App />);

    await screen.findByLabelText("Data refresh");
    fireEvent.click(screen.getByRole("button", { name: "Refresh Stats" }));

    expect(screen.getByText("Refreshing stats...")).toBeInTheDocument();
    await waitFor(() => {
      expect(
        screen.getByText("128 heroes refreshed at 2026-06-19T09:00:00Z"),
      ).toBeInTheDocument();
    });
  });

  test("shows a stats refresh error without clearing chat controls", async () => {
    vi.spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(
        new Response(JSON.stringify(healthResponse), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        }),
      )
      .mockResolvedValueOnce(new Response("bad gateway", { status: 502 }));

    render(<App />);

    const input = await screen.findByLabelText("Ask a Dota 2 question");
    fireEvent.change(input, { target: { value: "Axe win rate meta" } });
    fireEvent.click(screen.getByRole("button", { name: "Refresh Stats" }));

    await waitFor(() => {
      expect(
        screen.getByText("Stats refresh failed. Check OpenDota/network and retry."),
      ).toBeInTheDocument();
    });
    expect(screen.getByDisplayValue("Axe win rate meta")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Send" })).toBeEnabled();
  });

  test("disables only the refresh action that is currently pending", async () => {
    let resolveKnowledge: (value: Response) => void = () => undefined;
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
            resolveKnowledge = resolve;
          }),
      )
      .mockResolvedValueOnce(
        new Response(JSON.stringify(healthResponse), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        }),
      );

    render(<App />);

    await screen.findByLabelText("Data refresh");
    const knowledgeButton = screen.getByRole("button", {
      name: "Refresh Knowledge",
    });
    const statsButton = screen.getByRole("button", { name: "Refresh Stats" });

    fireEvent.click(knowledgeButton);

    expect(knowledgeButton).toBeDisabled();
    expect(statsButton).toBeEnabled();

    resolveKnowledge(
      new Response(
        JSON.stringify({
          documents: 3,
          chunks: 3,
          sources: ["Seed: Black King Bar"],
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    );

    await waitFor(() => {
      expect(knowledgeButton).toBeEnabled();
    });
  });
```

- [ ] **Step 2: Run app tests to verify they fail**

Run:

```powershell
npm test -- src/App.test.tsx
```

Expected: FAIL because the app does not render `Data refresh`, `Refresh Knowledge`, or `Refresh Stats`.

- [ ] **Step 3: Implement refresh state and handlers**

Update the import in `frontend/src/App.tsx`:

```tsx
import {
  askChat,
  ChatResponse,
  fetchHealth,
  HealthResponse,
  KnowledgeRefreshResponse,
  refreshKnowledge,
  refreshStats,
  StatsRefreshResponse,
} from "./api/client";
```

Add types after `ChatMessage`:

```tsx
type RefreshState<T> =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "success"; result: T }
  | { status: "error"; message: string };
```

Add state inside `App()` after chat state:

```tsx
  const [knowledgeRefresh, setKnowledgeRefresh] =
    useState<RefreshState<KnowledgeRefreshResponse>>({ status: "idle" });
  const [statsRefresh, setStatsRefresh] =
    useState<RefreshState<StatsRefreshResponse>>({ status: "idle" });
```

Add this helper inside `App()` before `submitQuestion`:

```tsx
  async function refreshServiceHealth() {
    try {
      const health = await fetchHealth();
      setState({ status: "ready", health });
    } catch {
      // Keep the refresh result visible. The next page load will show health errors.
    }
  }
```

Add handlers before `submitQuestion`:

```tsx
  async function submitKnowledgeRefresh() {
    if (knowledgeRefresh.status === "loading") return;
    setKnowledgeRefresh({ status: "loading" });
    try {
      const result = await refreshKnowledge();
      setKnowledgeRefresh({ status: "success", result });
      await refreshServiceHealth();
    } catch (error) {
      setKnowledgeRefresh({
        status: "error",
        message:
          error instanceof Error
            ? error.message
            : "Knowledge refresh failed. Check backend and retry.",
      });
    }
  }

  async function submitStatsRefresh() {
    if (statsRefresh.status === "loading") return;
    setStatsRefresh({ status: "loading" });
    try {
      const result = await refreshStats();
      setStatsRefresh({ status: "success", result });
      await refreshServiceHealth();
    } catch (error) {
      setStatsRefresh({
        status: "error",
        message:
          error instanceof Error
            ? error.message
            : "Stats refresh failed. Check OpenDota/network and retry.",
      });
    }
  }
```

- [ ] **Step 4: Render the refresh panel**

Add this JSX after the service status block and before `<div className="workbench">`:

```tsx
        <section className="refreshPanel" aria-label="Data refresh">
          <div>
            <h2>Data refresh</h2>
          </div>
          <div className="refreshActions">
            <div className="refreshAction">
              <button
                disabled={knowledgeRefresh.status === "loading"}
                onClick={submitKnowledgeRefresh}
                type="button"
              >
                <RefreshCw
                  aria-hidden
                  className={
                    knowledgeRefresh.status === "loading" ? "spin" : undefined
                  }
                />
                Refresh Knowledge
              </button>
              <RefreshStatus
                idleText="Knowledge ready"
                loadingText="Refreshing knowledge..."
                state={knowledgeRefresh}
                successText={(result) =>
                  `${result.documents} documents, ${result.chunks} chunks, ${result.sources.length} sources`
                }
              />
            </div>
            <div className="refreshAction">
              <button
                disabled={statsRefresh.status === "loading"}
                onClick={submitStatsRefresh}
                type="button"
              >
                <RefreshCw
                  aria-hidden
                  className={statsRefresh.status === "loading" ? "spin" : undefined}
                />
                Refresh Stats
              </button>
              <RefreshStatus
                idleText="Stats ready"
                loadingText="Refreshing stats..."
                state={statsRefresh}
                successText={(result) =>
                  `${result.heroes} heroes refreshed at ${result.refreshed_at}`
                }
              />
            </div>
          </div>
        </section>
```

Add this helper component after `App` and before `export default App;`:

```tsx
function RefreshStatus<T>({
  idleText,
  loadingText,
  state,
  successText,
}: {
  idleText: string;
  loadingText: string;
  state: RefreshState<T>;
  successText: (result: T) => string;
}) {
  if (state.status === "loading") {
    return <p className="refreshStatus">{loadingText}</p>;
  }
  if (state.status === "success") {
    return <p className="refreshStatus success">{successText(state.result)}</p>;
  }
  if (state.status === "error") {
    return (
      <p className="refreshStatus error" role="alert">
        {state.message}
      </p>
    );
  }
  return <p className="refreshStatus">{idleText}</p>;
}
```

- [ ] **Step 5: Run app tests to verify they pass**

Run:

```powershell
npm test -- src/App.test.tsx
```

Expected: PASS for existing chat tests and new refresh tests.

- [ ] **Step 6: Commit app behavior**

Run:

```powershell
git add frontend/src/App.tsx frontend/src/App.test.tsx
git commit -m "feat: add frontend refresh controls"
```

## Task 3: Style Refresh Panel And Update Demo Docs

**Files:**
- Modify: `frontend/src/styles.css`
- Modify: `README.md`

- [ ] **Step 1: Inspect current style anchors**

Run:

```powershell
rg -n "statusStrip|workbench|button|notice" frontend/src/styles.css
```

Expected: Output shows existing classes used by service status, buttons, notices, and workbench layout.

- [ ] **Step 2: Add compact refresh styles**

Add CSS near the status strip and workbench styles in `frontend/src/styles.css`:

```css
.refreshPanel {
  border: 1px solid #263241;
  border-radius: 8px;
  background: #111923;
  display: grid;
  gap: 12px;
  grid-template-columns: minmax(120px, 0.4fr) minmax(0, 1fr);
  padding: 14px;
}

.refreshPanel h2 {
  font-size: 0.95rem;
  margin: 0;
}

.refreshActions {
  display: grid;
  gap: 10px;
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.refreshAction {
  align-items: start;
  display: grid;
  gap: 8px;
}

.refreshAction button {
  align-items: center;
  display: inline-flex;
  gap: 8px;
  justify-content: center;
  min-height: 40px;
  width: 100%;
}

.refreshStatus {
  color: #94a3b8;
  font-size: 0.85rem;
  line-height: 1.35;
  margin: 0;
}

.refreshStatus.success {
  color: #8bd5a4;
}

.refreshStatus.error {
  color: #fca5a5;
}

@media (max-width: 760px) {
  .refreshPanel,
  .refreshActions {
    grid-template-columns: 1fr;
  }
}
```

If exact colors differ from the current file, keep the existing palette and class names but preserve the layout: one compact panel, two actions, mobile single column.

- [ ] **Step 3: Update README demo instructions**

In `README.md`, under `## M4 Frontend Chat UI`, add:

```markdown
The browser demo also includes a `Data refresh` panel. Use `Refresh Knowledge` to call `POST /api/ingest/documents` and `Refresh Stats` to call `POST /api/refresh/stats` without leaving the UI.
```

Under `## M6 OpenDota Hero Stats`, add:

```markdown
In the frontend demo, prefer the `Refresh Stats` button for manual testing. If OpenDota is unavailable, the UI shows a retry-oriented error and existing chat remains usable.
```

- [ ] **Step 4: Run all frontend tests**

Run:

```powershell
npm test
```

Expected: PASS for all frontend tests.

- [ ] **Step 5: Run frontend build**

Run:

```powershell
npm run build
```

Expected: TypeScript and Vite build complete successfully.

- [ ] **Step 6: Manually verify browser demo**

With the dev server running at `http://127.0.0.1:5173`, reload the page and verify:

- `Data refresh` panel is visible.
- `Refresh Knowledge` shows a loading state and then a document/chunk/source summary.
- `Refresh Stats` shows either a hero refresh summary or the OpenDota/network retry error.
- Existing chat input and source display still work after refresh.

- [ ] **Step 7: Commit style and docs**

Run:

```powershell
git add frontend/src/styles.css README.md
git commit -m "docs: add refresh controls demo instructions"
```

## Task 4: Final Verification

**Files:**
- Read: `git status --short --branch`

- [ ] **Step 1: Run complete frontend verification**

Run:

```powershell
npm test
npm run build
```

Expected: tests pass and build succeeds.

- [ ] **Step 2: Check repository status**

Run:

```powershell
git status --short --branch
```

Expected: M7 tracked changes are committed. Untracked `.vscode/` may remain and should not be staged unless the user explicitly asks.

- [ ] **Step 3: Report completion**

Report:

- Tests run and result.
- Build run and result.
- Browser demo status.
- Any external limitation, especially if OpenDota refresh fails because the provider or local network is unavailable.

