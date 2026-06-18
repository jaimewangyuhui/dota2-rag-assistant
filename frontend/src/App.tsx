import { AlertCircle, CheckCircle2, RefreshCw } from "lucide-react";
import { useEffect, useState } from "react";

import { fetchHealth, HealthResponse } from "./api/client";
import "./styles.css";

type LoadState =
  | { status: "loading" }
  | { status: "ready"; health: HealthResponse }
  | { status: "error"; message: string };

function App() {
  const [state, setState] = useState<LoadState>({ status: "loading" });

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

  return (
    <main className="shell">
      <section className="workspace" aria-label="Service status">
        <header className="topbar">
          <div>
            <p className="eyebrow">Local Dota 2 RAG</p>
            <h1>Dota 2 RAG Assistant</h1>
          </div>
          <span className="buildTag">M1</span>
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
          <div className="statusGrid">
            {state.health.services.map((service) => (
              <article className="statusCard" key={service.name}>
                <div className="statusTitle">
                  {service.ok ? (
                    <CheckCircle2 aria-label="ready" className="okIcon" />
                  ) : (
                    <AlertCircle aria-label="unavailable" className="badIcon" />
                  )}
                  <h2>{service.name}</h2>
                </div>
                <p>{service.detail}</p>
              </article>
            ))}
          </div>
        )}
      </section>
    </main>
  );
}

export default App;
