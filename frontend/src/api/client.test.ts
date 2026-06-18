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
