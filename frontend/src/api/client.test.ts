import { afterEach, describe, expect, test, vi } from "vitest";

import { askChat, refreshKnowledge, refreshStats } from "./client";

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
