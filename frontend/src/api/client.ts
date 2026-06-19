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

export type KnowledgeRefreshResponse = {
  documents: number;
  chunks: number;
  sources: string[];
};

export type StatsRefreshResponse = {
  heroes: number;
  refreshed_at: string;
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

export type KnowledgeSummary = {
  total_chunks: number;
  total_sources: number;
  by_entity_type: Record<string, number>;
  by_source_prefix: Record<string, number>;
  updated_at: string | null;
};

export type KnowledgeChunk = {
  chunk_id: string;
  source_name: string;
  source_url: string;
  entity_type: string;
  entity_name: string;
  patch_version: string | null;
  updated_at: string;
  preview: string;
};

export type KnowledgeChunksResponse = {
  chunks: KnowledgeChunk[];
};

export type KnowledgeChunkFilters = {
  q?: string;
  entity_type?: string;
  source_prefix?: string;
  limit?: number;
};

const CHAT_ERROR = "Chat request failed. Check backend and Ollama, then retry.";
const KNOWLEDGE_REFRESH_ERROR =
  "Knowledge refresh failed. Check backend and retry.";
const STATS_REFRESH_ERROR =
  "Stats refresh failed. Check OpenDota/network and retry.";

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

export async function fetchKnowledgeSummary(): Promise<KnowledgeSummary> {
  const response = await fetch("/api/knowledge/summary");
  if (!response.ok) {
    throw new Error(`Knowledge summary failed with HTTP ${response.status}`);
  }
  return response.json() as Promise<KnowledgeSummary>;
}

export async function fetchKnowledgeChunks(
  filters: KnowledgeChunkFilters = {},
): Promise<KnowledgeChunksResponse> {
  const params = new URLSearchParams();
  if (filters.q) params.set("q", filters.q);
  if (filters.entity_type) params.set("entity_type", filters.entity_type);
  if (filters.source_prefix) params.set("source_prefix", filters.source_prefix);
  if (filters.limit) params.set("limit", String(filters.limit));
  const query = params.toString();
  const response = await fetch(`/api/knowledge/chunks${query ? `?${query}` : ""}`);
  if (!response.ok) {
    throw new Error(`Knowledge chunks failed with HTTP ${response.status}`);
  }
  return response.json() as Promise<KnowledgeChunksResponse>;
}
