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
    expect(screen.getByLabelText("Dota 2 RAG workbench")).toBeInTheDocument();
    expect(screen.getByLabelText("Sources")).toBeInTheDocument();
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
        screen.getByText(
          "Chat request failed. Check backend and Ollama, then retry.",
        ),
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
      expect(screen.queryByText("Asking local model...")).not.toBeInTheDocument();
    });
    expect(screen.getByLabelText("Ask a Dota 2 question")).not.toBeDisabled();
  });

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
        screen.getByText(
          "Stats refresh failed. Check OpenDota/network and retry.",
        ),
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
});
