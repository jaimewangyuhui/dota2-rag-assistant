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

export default App;
