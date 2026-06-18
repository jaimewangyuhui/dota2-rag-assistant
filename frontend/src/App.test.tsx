import { render, screen, waitFor } from "@testing-library/react";
import { describe, expect, test, vi } from "vitest";

import App from "./App";

describe("App", () => {
  test("renders service health from the backend", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          app: "Dota 2 RAG Assistant",
          ok: false,
          services: [
            { name: "backend", ok: true, detail: "ready" },
            { name: "sqlite", ok: true, detail: "ready" },
            { name: "milvus", ok: true, detail: "local vector directory ready" },
            { name: "ollama", ok: false, detail: "connection refused" },
          ],
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    );

    render(<App />);

    expect(screen.getByText("Checking local services")).toBeInTheDocument();
    await waitFor(() => {
      expect(screen.getByText("Dota 2 RAG Assistant")).toBeInTheDocument();
    });
    expect(screen.getByText("ollama")).toBeInTheDocument();
    expect(screen.getByText("connection refused")).toBeInTheDocument();
  });
});
