# Dota 2 RAG Assistant M1 Skeleton Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first runnable local skeleton: FastAPI backend health API, SQLite initialization, vector-store health adapter, Ollama health check, and a React/Vite UI that displays connection status.

**Architecture:** The backend exposes `/api/health` through a small FastAPI app and keeps service checks behind focused modules so later RAG work can reuse them. The frontend is a compact tool UI that polls the backend and renders backend, SQLite, Milvus, and Ollama status without pretending chat is ready before M3.

**Tech Stack:** Python 3.11+, FastAPI, Pydantic Settings, SQLAlchemy, httpx, pytest, React, Vite, TypeScript, Vitest, Testing Library.

---

## File Structure

- Create `backend/pyproject.toml`: backend package metadata, runtime dependencies, and pytest configuration.
- Create `backend/.env.example`: local environment values for SQLite path, vector path, Ollama URL, and CORS origins.
- Create `backend/app/main.py`: FastAPI app factory and router registration.
- Create `backend/app/core/config.py`: typed settings read from environment.
- Create `backend/app/db/session.py`: SQLite engine creation, connection check, and directory initialization.
- Create `backend/app/vector_store/milvus.py`: M1 vector health adapter that validates configured local vector directory and reports adapter readiness.
- Create `backend/app/services/ollama.py`: Ollama HTTP health probe.
- Create `backend/app/api/health.py`: `/api/health` response assembly.
- Create `backend/tests/test_config.py`, `backend/tests/test_health_services.py`, `backend/tests/test_health_api.py`: settings, service health, and API tests.
- Create `frontend/package.json`, `frontend/tsconfig.json`, `frontend/vite.config.ts`, `frontend/index.html`: frontend build and test setup.
- Create `frontend/src/api/client.ts`: health API client.
- Create `frontend/src/App.tsx`: service status UI.
- Create `frontend/src/App.test.tsx`: frontend rendering tests.
- Create `README.md`: local development commands for M1.

## Task 1: Backend Package And Settings

**Files:**
- Create: `backend/pyproject.toml`
- Create: `backend/.env.example`
- Create: `backend/app/__init__.py`
- Create: `backend/app/core/__init__.py`
- Create: `backend/app/core/config.py`
- Test: `backend/tests/test_config.py`

- [ ] **Step 1: Write the failing config tests**

Create `backend/tests/test_config.py`:

```python
from pathlib import Path

from app.core.config import Settings


def test_settings_uses_default_local_paths() -> None:
    settings = Settings()

    assert settings.app_name == "Dota 2 RAG Assistant"
    assert settings.sqlite_path == Path("data/sqlite/dota2_rag.db")
    assert settings.vector_data_path == Path("data/milvus")
    assert str(settings.ollama_base_url) == "http://localhost:11434"


def test_cors_origins_are_parsed_from_comma_separated_text() -> None:
    settings = Settings(cors_origins="http://localhost:5173,http://127.0.0.1:5173")

    assert settings.cors_origin_list == [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]
```

- [ ] **Step 2: Run the config tests and verify RED**

Run:

```powershell
cd backend
python -m pytest tests/test_config.py -v
```

Expected: FAIL because `app.core.config` does not exist.

- [ ] **Step 3: Add backend package metadata**

Create `backend/pyproject.toml`:

```toml
[project]
name = "dota2-rag-assistant-backend"
version = "0.1.0"
description = "Local-first Dota 2 RAG assistant backend"
requires-python = ">=3.11"
dependencies = [
  "beautifulsoup4>=4.12.3",
  "fastapi>=0.115.0",
  "httpx>=0.27.2",
  "pydantic>=2.9.0",
  "pydantic-settings>=2.5.2",
  "pymilvus>=2.4.7",
  "sqlalchemy>=2.0.35",
  "trafilatura>=1.12.2",
  "uvicorn[standard]>=0.30.6"
]

[project.optional-dependencies]
dev = [
  "pytest>=8.3.3",
  "pytest-asyncio>=0.24.0",
  "respx>=0.21.1"
]

[tool.pytest.ini_options]
pythonpath = ["."]
testpaths = ["tests"]
asyncio_mode = "auto"
```

Create `backend/.env.example`:

```env
APP_NAME="Dota 2 RAG Assistant"
SQLITE_PATH="data/sqlite/dota2_rag.db"
VECTOR_DATA_PATH="data/milvus"
OLLAMA_BASE_URL="http://localhost:11434"
CORS_ORIGINS="http://localhost:5173,http://127.0.0.1:5173"
```

- [ ] **Step 4: Add typed settings**

Create empty package files:

```text
backend/app/__init__.py
backend/app/core/__init__.py
```

Create `backend/app/core/config.py`:

```python
from functools import lru_cache
from pathlib import Path

from pydantic import AnyHttpUrl, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Dota 2 RAG Assistant"
    sqlite_path: Path = Path("data/sqlite/dota2_rag.db")
    vector_data_path: Path = Path("data/milvus")
    ollama_base_url: AnyHttpUrl = "http://localhost:11434"
    cors_origins: str = Field(
        default="http://localhost:5173,http://127.0.0.1:5173",
        description="Comma-separated browser origins allowed to call the API.",
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
```

- [ ] **Step 5: Run config tests and verify GREEN**

Run:

```powershell
cd backend
python -m pytest tests/test_config.py -v
```

Expected: PASS with 2 tests.

- [ ] **Step 6: Commit Task 1**

Run when git is available:

```powershell
git add backend/pyproject.toml backend/.env.example backend/app backend/tests/test_config.py
git commit -m "chore: add backend settings skeleton"
```

## Task 2: Backend Health Checks

**Files:**
- Create: `backend/app/db/__init__.py`
- Create: `backend/app/db/session.py`
- Create: `backend/app/vector_store/__init__.py`
- Create: `backend/app/vector_store/milvus.py`
- Create: `backend/app/services/__init__.py`
- Create: `backend/app/services/ollama.py`
- Test: `backend/tests/test_health_services.py`

- [ ] **Step 1: Write failing service health tests**

Create `backend/tests/test_health_services.py`:

```python
from pathlib import Path

import httpx
import pytest

from app.db.session import check_sqlite
from app.services.ollama import check_ollama
from app.vector_store.milvus import check_vector_store


def test_check_sqlite_creates_parent_directory(tmp_path: Path) -> None:
    database_path = tmp_path / "nested" / "dota2_rag.db"

    result = check_sqlite(database_path)

    assert result.name == "sqlite"
    assert result.ok is True
    assert result.detail == "ready"
    assert database_path.parent.exists()


def test_check_vector_store_creates_local_data_directory(tmp_path: Path) -> None:
    vector_path = tmp_path / "milvus"

    result = check_vector_store(vector_path)

    assert result.name == "milvus"
    assert result.ok is True
    assert result.detail == "local vector directory ready"
    assert vector_path.exists()


@pytest.mark.asyncio
async def test_check_ollama_reports_ready_with_version_response() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/version"
        return httpx.Response(200, json={"version": "0.3.12"})

    transport = httpx.MockTransport(handler)

    result = await check_ollama("http://ollama.test", transport=transport)

    assert result.name == "ollama"
    assert result.ok is True
    assert result.detail == "0.3.12"


@pytest.mark.asyncio
async def test_check_ollama_reports_unavailable_on_connection_error() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused", request=request)

    transport = httpx.MockTransport(handler)

    result = await check_ollama("http://ollama.test", transport=transport)

    assert result.name == "ollama"
    assert result.ok is False
    assert "connection refused" in result.detail
```

- [ ] **Step 2: Run service health tests and verify RED**

Run:

```powershell
cd backend
python -m pytest tests/test_health_services.py -v
```

Expected: FAIL because the service modules do not exist.

- [ ] **Step 3: Add service health models and checks**

Create empty package files:

```text
backend/app/db/__init__.py
backend/app/vector_store/__init__.py
backend/app/services/__init__.py
```

Create `backend/app/db/session.py`:

```python
from pathlib import Path

from pydantic import BaseModel
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine


class ServiceStatus(BaseModel):
    name: str
    ok: bool
    detail: str


def create_sqlite_engine(database_path: Path) -> Engine:
    database_path.parent.mkdir(parents=True, exist_ok=True)
    return create_engine(f"sqlite:///{database_path}", future=True)


def check_sqlite(database_path: Path) -> ServiceStatus:
    try:
        engine = create_sqlite_engine(database_path)
        with engine.connect() as connection:
            connection.execute(text("select 1"))
        return ServiceStatus(name="sqlite", ok=True, detail="ready")
    except Exception as exc:
        return ServiceStatus(name="sqlite", ok=False, detail=str(exc))
```

Create `backend/app/vector_store/milvus.py`:

```python
from pathlib import Path

from app.db.session import ServiceStatus


def check_vector_store(vector_data_path: Path) -> ServiceStatus:
    try:
        vector_data_path.mkdir(parents=True, exist_ok=True)
        return ServiceStatus(
            name="milvus",
            ok=True,
            detail="local vector directory ready",
        )
    except Exception as exc:
        return ServiceStatus(name="milvus", ok=False, detail=str(exc))
```

Create `backend/app/services/ollama.py`:

```python
from typing import Optional

import httpx

from app.db.session import ServiceStatus


async def check_ollama(
    base_url: str,
    transport: Optional[httpx.AsyncBaseTransport] = None,
) -> ServiceStatus:
    try:
        async with httpx.AsyncClient(
            base_url=str(base_url).rstrip("/"),
            timeout=2.0,
            transport=transport,
        ) as client:
            response = await client.get("/api/version")
            response.raise_for_status()
            version = response.json().get("version", "ready")
        return ServiceStatus(name="ollama", ok=True, detail=str(version))
    except Exception as exc:
        return ServiceStatus(name="ollama", ok=False, detail=str(exc))
```

- [ ] **Step 4: Run service health tests and verify GREEN**

Run:

```powershell
cd backend
python -m pytest tests/test_health_services.py -v
```

Expected: PASS with 4 tests.

- [ ] **Step 5: Commit Task 2**

Run when git is available:

```powershell
git add backend/app/db backend/app/vector_store backend/app/services backend/tests/test_health_services.py
git commit -m "feat: add local service health checks"
```

## Task 3: FastAPI Health Endpoint

**Files:**
- Create: `backend/app/api/__init__.py`
- Create: `backend/app/api/health.py`
- Create: `backend/app/main.py`
- Test: `backend/tests/test_health_api.py`

- [ ] **Step 1: Write failing API tests**

Create `backend/tests/test_health_api.py`:

```python
from pathlib import Path

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app


def test_health_endpoint_reports_all_m1_services(tmp_path: Path) -> None:
    settings = Settings(
        sqlite_path=tmp_path / "sqlite" / "dota2_rag.db",
        vector_data_path=tmp_path / "milvus",
        ollama_base_url="http://127.0.0.1:9",
    )
    client = TestClient(create_app(settings))

    response = client.get("/api/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["app"] == "Dota 2 RAG Assistant"
    assert payload["ok"] is False
    assert {service["name"] for service in payload["services"]} == {
        "backend",
        "sqlite",
        "milvus",
        "ollama",
    }
    assert payload["services"][0] == {
        "name": "backend",
        "ok": True,
        "detail": "ready",
    }


def test_cors_allows_local_vite_origin(tmp_path: Path) -> None:
    settings = Settings(
        sqlite_path=tmp_path / "sqlite" / "dota2_rag.db",
        vector_data_path=tmp_path / "milvus",
        cors_origins="http://localhost:5173",
    )
    client = TestClient(create_app(settings))

    response = client.options(
        "/api/health",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
```

- [ ] **Step 2: Run API tests and verify RED**

Run:

```powershell
cd backend
python -m pytest tests/test_health_api.py -v
```

Expected: FAIL because `app.main` and `app.api.health` do not exist.

- [ ] **Step 3: Add API router and app factory**

Create `backend/app/api/__init__.py`:

```python
```

Create `backend/app/api/health.py`:

```python
from fastapi import APIRouter, Request
from pydantic import BaseModel

from app.db.session import ServiceStatus, check_sqlite
from app.services.ollama import check_ollama
from app.vector_store.milvus import check_vector_store

router = APIRouter(prefix="/api", tags=["health"])


class HealthResponse(BaseModel):
    app: str
    ok: bool
    services: list[ServiceStatus]


@router.get("/health", response_model=HealthResponse)
async def health(request: Request) -> HealthResponse:
    settings = request.app.state.settings
    services = [
        ServiceStatus(name="backend", ok=True, detail="ready"),
        check_sqlite(settings.sqlite_path),
        check_vector_store(settings.vector_data_path),
        await check_ollama(str(settings.ollama_base_url)),
    ]
    return HealthResponse(
        app=settings.app_name,
        ok=all(service.ok for service in services),
        services=services,
    )
```

Create `backend/app/main.py`:

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.health import router as health_router
from app.core.config import Settings, get_settings


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved_settings = settings or get_settings()
    app = FastAPI(title=resolved_settings.app_name)
    app.state.settings = resolved_settings

    app.add_middleware(
        CORSMiddleware,
        allow_origins=resolved_settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(health_router)
    return app


app = create_app()
```

- [ ] **Step 4: Run API tests and verify GREEN**

Run:

```powershell
cd backend
python -m pytest tests/test_health_api.py -v
```

Expected: PASS with 2 tests.

- [ ] **Step 5: Run all backend tests**

Run:

```powershell
cd backend
python -m pytest -v
```

Expected: PASS with 8 tests.

- [ ] **Step 6: Commit Task 3**

Run when git is available:

```powershell
git add backend/app/api backend/app/main.py backend/tests/test_health_api.py
git commit -m "feat: expose backend health endpoint"
```

## Task 4: Frontend Health Status UI

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/tsconfig.json`
- Create: `frontend/tsconfig.node.json`
- Create: `frontend/vite.config.ts`
- Create: `frontend/index.html`
- Create: `frontend/src/api/client.ts`
- Create: `frontend/src/App.tsx`
- Create: `frontend/src/App.test.tsx`
- Create: `frontend/src/main.tsx`
- Create: `frontend/src/styles.css`

- [ ] **Step 1: Write failing frontend test**

Create `frontend/src/App.test.tsx`:

```tsx
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
```

- [ ] **Step 2: Add frontend package setup**

Create `frontend/package.json`:

```json
{
  "name": "dota2-rag-assistant-frontend",
  "version": "0.1.0",
  "private": true,
  "type": "module",
  "scripts": {
    "dev": "vite --host 127.0.0.1",
    "build": "tsc && vite build",
    "test": "vitest run",
    "preview": "vite preview --host 127.0.0.1"
  },
  "dependencies": {
    "@vitejs/plugin-react": "^4.3.1",
    "vite": "^5.4.8",
    "react": "^18.3.1",
    "react-dom": "^18.3.1",
    "lucide-react": "^0.468.0"
  },
  "devDependencies": {
    "@testing-library/jest-dom": "^6.4.8",
    "@testing-library/react": "^16.0.1",
    "@types/react": "^18.3.11",
    "@types/react-dom": "^18.3.0",
    "jsdom": "^25.0.1",
    "typescript": "^5.6.2",
    "vitest": "^2.1.1"
  }
}
```

Create `frontend/tsconfig.json`:

```json
{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "lib": ["DOM", "DOM.Iterable", "ES2020"],
    "allowJs": false,
    "skipLibCheck": true,
    "esModuleInterop": true,
    "allowSyntheticDefaultImports": true,
    "strict": true,
    "forceConsistentCasingInFileNames": true,
    "module": "ESNext",
    "moduleResolution": "Node",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "react-jsx"
  },
  "include": ["src"],
  "references": [{ "path": "./tsconfig.node.json" }]
}
```

Create `frontend/tsconfig.node.json`:

```json
{
  "compilerOptions": {
    "composite": true,
    "module": "ESNext",
    "moduleResolution": "Node",
    "allowSyntheticDefaultImports": true
  },
  "include": ["vite.config.ts"]
}
```

Create `frontend/vite.config.ts`:

```ts
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": "http://127.0.0.1:8000",
    },
  },
  test: {
    environment: "jsdom",
    setupFiles: ["./src/testSetup.ts"],
  },
});
```

Create `frontend/index.html`:

```html
<!doctype html>
<html lang="zh-CN">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Dota 2 RAG Assistant</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

- [ ] **Step 3: Run frontend test and verify RED**

Run:

```powershell
cd frontend
npm test
```

Expected: FAIL because `src/App.tsx`, `src/api/client.ts`, and `src/testSetup.ts` do not exist.

- [ ] **Step 4: Add frontend client and compact status UI**

Create `frontend/src/testSetup.ts`:

```ts
import "@testing-library/jest-dom/vitest";
```

Create `frontend/src/api/client.ts`:

```ts
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
```

Create `frontend/src/App.tsx`:

```tsx
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
```

Create `frontend/src/main.tsx`:

```tsx
import React from "react";
import ReactDOM from "react-dom/client";

import App from "./App";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
```

Create `frontend/src/styles.css`:

```css
:root {
  color: #18201d;
  background: #eef2ed;
  font-family:
    Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI",
    sans-serif;
}

* {
  box-sizing: border-box;
}

body {
  margin: 0;
}

.shell {
  min-height: 100vh;
  padding: 24px;
}

.workspace {
  max-width: 960px;
  margin: 0 auto;
}

.topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 16px 0 20px;
  border-bottom: 1px solid #c8d1c7;
}

.eyebrow {
  margin: 0 0 4px;
  color: #506358;
  font-size: 0.78rem;
  font-weight: 700;
  text-transform: uppercase;
}

h1,
h2,
p {
  margin: 0;
}

h1 {
  font-size: clamp(1.65rem, 3vw, 2.4rem);
}

.buildTag {
  display: inline-flex;
  min-width: 44px;
  min-height: 32px;
  align-items: center;
  justify-content: center;
  border: 1px solid #839186;
  border-radius: 6px;
  color: #33423a;
  font-weight: 800;
}

.notice {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 22px;
  color: #33423a;
}

.notice.error {
  color: #9b1c1c;
}

.spin {
  animation: spin 1s linear infinite;
}

.statusGrid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 12px;
  margin-top: 22px;
}

.statusCard {
  min-height: 116px;
  padding: 14px;
  border: 1px solid #c3cdc2;
  border-radius: 8px;
  background: #fbfcfa;
}

.statusTitle {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
}

.statusTitle h2 {
  font-size: 1rem;
}

.statusCard p {
  color: #536159;
  line-height: 1.45;
  overflow-wrap: anywhere;
}

.okIcon {
  color: #207245;
}

.badIcon {
  color: #b83232;
}

@keyframes spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}
```

- [ ] **Step 5: Run frontend test and verify GREEN**

Run:

```powershell
cd frontend
npm test
```

Expected: PASS with 1 test.

- [ ] **Step 6: Build the frontend**

Run:

```powershell
cd frontend
npm run build
```

Expected: PASS and create `frontend/dist`.

- [ ] **Step 7: Commit Task 4**

Run when git is available:

```powershell
git add frontend
git commit -m "feat: add frontend service status view"
```

## Task 5: Local Run Documentation And M1 Verification

**Files:**
- Create: `README.md`
- Modify: `backend/app/api/health.py`
- Test: backend and frontend full checks

- [ ] **Step 1: Write the README content**

Create `README.md`:

````markdown
# Dota 2 RAG Assistant

Local-first Dota 2 RAG assistant. M1 provides the runnable backend skeleton and a compact frontend service-status view.

## Backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Health endpoint:

```text
http://127.0.0.1:8000/api/health
```

## Frontend

```powershell
cd frontend
npm install
npm run dev
```

Frontend URL:

```text
http://127.0.0.1:5173
```

## M1 Verification

```powershell
cd backend
python -m pytest -v

cd ..\frontend
npm test
npm run build
```

Ollama can be unavailable during M1. The health endpoint still responds and marks `ollama` as unavailable with the connection detail.
````

- [ ] **Step 2: Run backend verification**

Run:

```powershell
cd backend
python -m pytest -v
```

Expected: PASS with all backend tests.

- [ ] **Step 3: Run frontend verification**

Run:

```powershell
cd frontend
npm test
npm run build
```

Expected: PASS for tests and build.

- [ ] **Step 4: Start backend manually**

Run:

```powershell
cd backend
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Expected: server listens on `http://127.0.0.1:8000`.

- [ ] **Step 5: Start frontend manually**

Run in a second terminal:

```powershell
cd frontend
npm run dev
```

Expected: Vite prints a local URL at `http://127.0.0.1:5173`.

- [ ] **Step 6: Browser acceptance check**

Open `http://127.0.0.1:5173`.

Expected:

- Page title reads `Dota 2 RAG Assistant`.
- Four service rows or cards are visible: `backend`, `sqlite`, `milvus`, and `ollama`.
- Backend, SQLite, and Milvus are ready when local directories are writable.
- Ollama is either ready with a version or unavailable with a clear connection detail.

- [ ] **Step 7: Commit Task 5**

Run when git is available:

```powershell
git add README.md
git commit -m "docs: add local m1 run instructions"
```

## Self-Review

- Spec coverage: This plan implements M1 acceptance criteria from the design document: FastAPI backend, environment configuration, SQLite initialization, Milvus adapter boundary, Ollama health check, and frontend service connection status.
- Deferred scope: Text ingestion, question classification, RAG retrieval, OpenDota refresh, and full chat UI belong to M2-M5 and are intentionally excluded from this M1 plan.
- Placeholder scan: The plan contains no deferred implementation labels; every created file has concrete content or an explicit empty package file.
- Type consistency: Service health uses the shared `ServiceStatus` Pydantic model across SQLite, vector-store, Ollama, and API response assembly. Frontend `HealthResponse` mirrors the backend response shape.
- Test path consistency: Backend tests run from `backend` with `pythonpath = ["."]`; frontend tests run from `frontend` with Vitest and jsdom.
