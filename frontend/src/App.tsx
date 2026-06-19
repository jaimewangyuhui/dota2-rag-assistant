import { AlertCircle, CheckCircle2, RefreshCw, Send } from "lucide-react";
import { FormEvent, useEffect, useMemo, useState } from "react";

import {
  askChat,
  ChatResponse,
  fetchHealth,
  HealthResponse,
  fetchKnowledgeChunks,
  fetchKnowledgeSummary,
  KnowledgeChunk,
  KnowledgeRefreshResponse,
  KnowledgeSummary,
  refreshKnowledge,
  refreshStats,
  StatsRefreshResponse,
} from "./api/client";
import "./styles.css";

type LoadState =
  | { status: "loading" }
  | { status: "ready"; health: HealthResponse }
  | { status: "error"; message: string };

type ChatMessage =
  | { id: number; role: "user"; content: string }
  | { id: number; role: "assistant"; content: string; response: ChatResponse };

type RefreshState<T> =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "success"; result: T }
  | { status: "error"; message: string };

const EXAMPLE_QUESTIONS = [
  "What does BKB do?",
  "Roshan drops what?",
  "Axe win rate meta",
  "Blink Dagger怎么用？",
];

function App() {
  const [state, setState] = useState<LoadState>({ status: "loading" });
  const [message, setMessage] = useState("");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [chatError, setChatError] = useState<string | null>(null);
  const [isSending, setIsSending] = useState(false);
  const [knowledgeRefresh, setKnowledgeRefresh] = useState<
    RefreshState<KnowledgeRefreshResponse>
  >({ status: "idle" });
  const [statsRefresh, setStatsRefresh] = useState<
    RefreshState<StatsRefreshResponse>
  >({ status: "idle" });
  const [knowledgeSummary, setKnowledgeSummary] = useState<
    RefreshState<KnowledgeSummary>
  >({ status: "idle" });
  const [knowledgeChunks, setKnowledgeChunks] = useState<
    RefreshState<{ chunks: KnowledgeChunk[] }>
  >({ status: "idle" });
  const [knowledgeQuery, setKnowledgeQuery] = useState("");
  const [knowledgeEntityType, setKnowledgeEntityType] = useState("");
  const [knowledgeSourcePrefix, setKnowledgeSourcePrefix] = useState("");

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

  useEffect(() => {
    let active = true;
    setKnowledgeSummary({ status: "loading" });
    fetchKnowledgeSummary()
      .then((result) => {
        if (active) setKnowledgeSummary({ status: "success", result });
      })
      .catch((error: Error) => {
        if (active) {
          setKnowledgeSummary({ status: "error", message: error.message });
        }
      });
    return () => {
      active = false;
    };
  }, [knowledgeRefresh.status]);

  useEffect(() => {
    let active = true;
    setKnowledgeChunks({ status: "loading" });
    fetchKnowledgeChunks({
      q: knowledgeQuery.trim() || undefined,
      entity_type: knowledgeEntityType || undefined,
      source_prefix: knowledgeSourcePrefix || undefined,
      limit: 50,
    })
      .then((result) => {
        if (active) setKnowledgeChunks({ status: "success", result });
      })
      .catch((error: Error) => {
        if (active) {
          setKnowledgeChunks({ status: "error", message: error.message });
        }
      });
    return () => {
      active = false;
    };
  }, [
    knowledgeQuery,
    knowledgeEntityType,
    knowledgeSourcePrefix,
    knowledgeRefresh.status,
  ]);

  async function refreshServiceHealth() {
    try {
      const health = await fetchHealth();
      setState({ status: "ready", health });
    } catch {
      // Keep the refresh result visible. The next page load will show health errors.
    }
  }

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
      setChatError(
        error instanceof Error
          ? error.message
          : "Chat request failed. Check backend and Ollama, then retry.",
      );
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
          <span className="buildTag">M7 Demo</span>
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
              <span
                className={service.ok ? "statusChip ok" : "statusChip bad"}
                key={service.name}
              >
                {service.ok ? (
                  <CheckCircle2 aria-label="ready" />
                ) : (
                  <AlertCircle aria-label="unavailable" />
                )}
                <span className="serviceName">{service.name}</span>
                <span>{service.detail}</span>
              </span>
            ))}
          </div>
        )}

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
                  className={
                    statsRefresh.status === "loading" ? "spin" : undefined
                  }
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

        <KnowledgePanel
          chunksState={knowledgeChunks}
          entityType={knowledgeEntityType}
          onEntityTypeChange={setKnowledgeEntityType}
          onQueryChange={setKnowledgeQuery}
          onSourcePrefixChange={setKnowledgeSourcePrefix}
          query={knowledgeQuery}
          sourcePrefix={knowledgeSourcePrefix}
          summaryState={knowledgeSummary}
        />

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
                  <p className="messageRole">
                    {item.role === "user" ? "You" : "Assistant"}
                  </p>
                  <p>{item.content}</p>
                  {item.role === "assistant" && (
                    <span className="questionType">
                      {item.response.question_type}
                    </span>
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
              <div className="inputRow">
                <input
                  disabled={isSending}
                  id="chat-input"
                  onChange={(event) => setMessage(event.target.value)}
                  placeholder="What does BKB do?"
                  value={message}
                />
                <button
                  disabled={isSending || message.trim().length === 0}
                  type="submit"
                >
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
                <article
                  className="sourceItem"
                  key={`${source.source_name}-${source.source_url ?? ""}`}
                >
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

function KnowledgePanel({
  chunksState,
  entityType,
  onEntityTypeChange,
  onQueryChange,
  onSourcePrefixChange,
  query,
  sourcePrefix,
  summaryState,
}: {
  chunksState: RefreshState<{ chunks: KnowledgeChunk[] }>;
  entityType: string;
  onEntityTypeChange: (value: string) => void;
  onQueryChange: (value: string) => void;
  onSourcePrefixChange: (value: string) => void;
  query: string;
  sourcePrefix: string;
  summaryState: RefreshState<KnowledgeSummary>;
}) {
  const chunks =
    chunksState.status === "success" ? (chunksState.result.chunks ?? []) : [];

  return (
    <section className="knowledgePanel" aria-label="Knowledge">
      <div className="panelHeader">
        <h2>Knowledge</h2>
        {summaryState.status === "success" && (
          <p>{`${summaryState.result.total_chunks} chunks - ${summaryState.result.total_sources} sources`}</p>
        )}
      </div>

      {summaryState.status === "loading" && (
        <p className="refreshStatus">Loading knowledge...</p>
      )}
      {summaryState.status === "error" && (
        <p className="refreshStatus error" role="alert">
          {summaryState.message}
        </p>
      )}
      {summaryState.status === "success" &&
        summaryState.result.total_chunks === 0 && (
          <p className="refreshStatus">
            No knowledge indexed. Refresh knowledge to inspect chunks.
          </p>
        )}
      {summaryState.status === "success" &&
        summaryState.result.total_chunks > 0 && (
          <div className="knowledgeStats">
            <MetricList values={summaryState.result.by_entity_type} />
            <MetricList values={summaryState.result.by_source_prefix} />
          </div>
        )}

      <div className="knowledgeFilters">
        <label>
          Search knowledge
          <input
            onChange={(event) => onQueryChange(event.target.value)}
            placeholder="Axe, Blink Dagger, BKB"
            value={query}
          />
        </label>
        <label>
          Entity type
          <select
            onChange={(event) => onEntityTypeChange(event.target.value)}
            value={entityType}
          >
            <option value="">All</option>
            <option value="hero">hero</option>
            <option value="item">item</option>
            <option value="objective">objective</option>
            <option value="patch">patch</option>
          </select>
        </label>
        <label>
          Source prefix
          <select
            onChange={(event) => onSourcePrefixChange(event.target.value)}
            value={sourcePrefix}
          >
            <option value="">All</option>
            <option value="OpenDota Hero">OpenDota Hero</option>
            <option value="OpenDota Item">OpenDota Item</option>
            <option value="Seed">Seed</option>
            <option value="Official Dota 2">Official Dota 2</option>
            <option value="Other">Other</option>
          </select>
        </label>
      </div>

      {chunksState.status === "loading" && (
        <p className="refreshStatus">Loading chunks...</p>
      )}
      {chunksState.status === "error" && (
        <p className="refreshStatus error" role="alert">
          {chunksState.message}
        </p>
      )}
      {chunksState.status === "success" && chunks.length === 0 && (
        <p className="refreshStatus">No knowledge chunks match these filters.</p>
      )}
      {chunksState.status === "success" && chunks.length > 0 && (
        <div className="knowledgeList">
          {chunks.map((chunk) => (
            <article className="knowledgeItem" key={chunk.chunk_id}>
              <div>
                <h3>{chunk.source_name}</h3>
                <p>
                  {chunk.entity_type} - {chunk.entity_name}
                </p>
              </div>
              <p>{chunk.preview}</p>
            </article>
          ))}
        </div>
      )}
    </section>
  );
}

function MetricList({ values }: { values: Record<string, number> }) {
  return (
    <div className="metricList">
      {Object.entries(values).map(([name, count]) => (
        <span className="metricChip" key={name}>
          {name} {count}
        </span>
      ))}
    </div>
  );
}

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

export default App;
