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

export async function fetchHealth(): Promise<HealthResponse> {
  const response = await fetch("/api/health");
  if (!response.ok) {
    throw new Error(`Health check failed with HTTP ${response.status}`);
  }
  return response.json() as Promise<HealthResponse>;
}
