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
      expect(
        screen.getByText("Black King Bar grants timed spell immunity."),
      ).toBeInTheDocument();
    });
    expect(screen.getByText("Seed: Black King Bar")).toBeInTheDocument();
    expect(screen.getByText("Patch 7.36")).toBeInTheDocument();
    expect(screen.getByText("knowledge")).toBeInTheDocument();
  });
});
