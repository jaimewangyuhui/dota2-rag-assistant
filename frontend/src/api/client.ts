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

const CHAT_ERROR = "Chat request failed. Check backend and Ollama, then retry.";

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
