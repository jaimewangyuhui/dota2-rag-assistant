# Dota 2 RAG Assistant M6 OpenDota Hero Stats Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a local SQLite-backed OpenDota hero statistics slice so the assistant can answer basic hero win rate, pick rate, sample size, and freshness questions.

**Architecture:** M6 adds a narrow structured-data vertical slice: an OpenDota data source parses `/heroStats`, a SQLite repository stores normalized hero stats, a refresh job/API updates the local snapshot, and chat service answers stats questions from templates instead of asking the LLM to invent numbers.

**Tech Stack:** Python 3.11, FastAPI, Pydantic, SQLAlchemy Core, SQLite, httpx, pytest, existing chat service and deterministic test setup.

---

## File Structure

- Create `backend/app/data_sources/opendota.py`: OpenDota client, parse errors, raw hero-stat parser, normalized record model.
- Create `backend/tests/fixtures/opendota_hero_stats_sample.json`: stable OpenDota fixture with Axe and Juggernaut.
- Create `backend/tests/test_opendota_source.py`: parser and client-shape tests.
- Create `backend/app/db/repositories.py`: `HeroStatsRepository`, SQLite table creation, upsert, lookup, ranking.
- Create `backend/tests/test_stats_repository.py`: repository tests using temporary SQLite.
- Create `backend/app/jobs/refresh_stats.py`: refresh orchestration and result model.
- Create `backend/tests/test_refresh_stats_job.py`: refresh job tests with fixture client.
- Create `backend/app/api/stats.py`: `POST /api/refresh/stats`.
- Modify `backend/app/main.py`: include stats router.
- Modify `backend/app/core/config.py`: add `opendota_base_url`.
- Create `backend/tests/test_stats_api.py`: endpoint tests with fixture client.
- Modify `backend/app/rag/chat_service.py`: template-backed stats answers.
- Modify `backend/app/api/chat.py`: wire optional stats repository into chat service.
- Modify `backend/tests/test_chat_service.py`: stats answer and refresh-needed tests.
- Modify `backend/tests/test_chat_api.py`: API smoke for stats answer after refresh fixture.
- Modify `README.md`: M6 refresh and stats answer notes.

## Task 1: OpenDota Hero Stats Parser

**Files:**
- Create: `backend/app/data_sources/opendota.py`
- Create: `backend/tests/fixtures/opendota_hero_stats_sample.json`
- Create: `backend/tests/test_opendota_source.py`

- [ ] **Step 1: Write OpenDota fixture**

Create `backend/tests/fixtures/opendota_hero_stats_sample.json`:

```json
[
  {
    "id": 2,
    "name": "npc_dota_hero_axe",
    "localized_name": "Axe",
    "primary_attr": "str",
    "roles": ["Initiator", "Durable", "Disabler", "Carry"],
    "pub_pick": 1000,
    "pub_win": 520,
    "pro_pick": 22,
    "pro_win": 7,
    "pro_ban": 36
  },
  {
    "id": 8,
    "name": "npc_dota_hero_juggernaut",
    "localized_name": "Juggernaut",
    "primary_attr": "agi",
    "roles": ["Carry", "Pusher", "Escape"],
    "pub_pick": 500,
    "pub_win": 260,
    "pro_pick": 2,
    "pro_win": 1,
    "pro_ban": 0
  }
]
```

- [ ] **Step 2: Write failing parser tests**

Create `backend/tests/test_opendota_source.py`:

```python
from pathlib import Path

import pytest

from app.data_sources.opendota import (
    OpenDotaParseError,
    parse_hero_stats,
)


FIXTURE_DIR = Path(__file__).parent / "fixtures"


def read_fixture(name: str) -> str:
    return (FIXTURE_DIR / name).read_text(encoding="utf-8")


def test_parse_hero_stats_computes_public_rates() -> None:
    records = parse_hero_stats(
        read_fixture("opendota_hero_stats_sample.json"),
        refreshed_at="2026-06-19T09:00:00Z",
    )

    assert [record.localized_name for record in records] == ["Axe", "Juggernaut"]
    assert records[0].hero_id == 2
    assert records[0].public_pick_count == 1000
    assert records[0].public_win_count == 520
    assert records[0].public_win_rate == 0.52
    assert records[0].public_pick_share == pytest.approx(1000 / 1500)
    assert records[0].pro_ban_count == 36
    assert records[0].refreshed_at == "2026-06-19T09:00:00Z"


def test_parse_hero_stats_rejects_empty_payload() -> None:
    with pytest.raises(OpenDotaParseError, match="No hero stats"):
        parse_hero_stats("[]", refreshed_at="2026-06-19T09:00:00Z")


def test_parse_hero_stats_rejects_missing_required_field() -> None:
    with pytest.raises(OpenDotaParseError, match="localized_name"):
        parse_hero_stats(
            '[{"id": 2, "name": "npc_dota_hero_axe", "pub_pick": 10, "pub_win": 5}]',
            refreshed_at="2026-06-19T09:00:00Z",
        )
```

- [ ] **Step 3: Run parser tests and verify RED**

Run:

```powershell
cd backend
$env:TEMP="$PWD\.tmp"; $env:TMP=$env:TEMP
.\.conda\python.exe -m pytest tests/test_opendota_source.py -v -p no:cacheprovider --basetemp .tmp\pytest-m6-opendota-source
```

Expected: FAIL because `app.data_sources.opendota` does not exist.

- [ ] **Step 4: Implement OpenDota parser and client**

Create `backend/app/data_sources/opendota.py`:

```python
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

import httpx


class OpenDotaParseError(ValueError):
    pass


@dataclass(frozen=True)
class OpenDotaHeroStatsRecord:
    hero_id: int
    name: str
    localized_name: str
    primary_attr: str
    roles: list[str]
    public_pick_count: int
    public_win_count: int
    public_win_rate: float
    public_pick_share: float
    pro_pick_count: int
    pro_win_count: int
    pro_ban_count: int
    refreshed_at: str


class OpenDotaClient:
    def __init__(self, base_url: str = "https://api.opendota.com/api", timeout: float = 20.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def fetch_hero_stats(self) -> str:
        response = httpx.get(f"{self.base_url}/heroStats", timeout=self.timeout)
        response.raise_for_status()
        return response.text


def _required(row: dict[str, Any], field: str) -> Any:
    if field not in row:
        raise OpenDotaParseError(f"Missing required OpenDota hero stat field: {field}")
    return row[field]


def parse_hero_stats(raw: str, refreshed_at: str) -> list[OpenDotaHeroStatsRecord]:
    payload = json.loads(raw)
    if not isinstance(payload, list) or not payload:
        raise OpenDotaParseError("No hero stats found in OpenDota payload")

    total_public_picks = sum(int(row.get("pub_pick", 0)) for row in payload)
    records: list[OpenDotaHeroStatsRecord] = []
    for row in payload:
        if not isinstance(row, dict):
            raise OpenDotaParseError("OpenDota hero stat row must be an object")
        hero_id = int(_required(row, "id"))
        name = str(_required(row, "name"))
        localized_name = str(_required(row, "localized_name"))
        public_pick_count = int(_required(row, "pub_pick"))
        public_win_count = int(_required(row, "pub_win"))
        records.append(
            OpenDotaHeroStatsRecord(
                hero_id=hero_id,
                name=name,
                localized_name=localized_name,
                primary_attr=str(row.get("primary_attr", "")),
                roles=[str(role) for role in row.get("roles", [])],
                public_pick_count=public_pick_count,
                public_win_count=public_win_count,
                public_win_rate=public_win_count / public_pick_count if public_pick_count else 0.0,
                public_pick_share=public_pick_count / total_public_picks if total_public_picks else 0.0,
                pro_pick_count=int(row.get("pro_pick", 0)),
                pro_win_count=int(row.get("pro_win", 0)),
                pro_ban_count=int(row.get("pro_ban", 0)),
                refreshed_at=refreshed_at,
            )
        )
    return records
```

- [ ] **Step 5: Run parser tests and verify GREEN**

Run:

```powershell
cd backend
$env:TEMP="$PWD\.tmp"; $env:TMP=$env:TEMP
.\.conda\python.exe -m pytest tests/test_opendota_source.py -v -p no:cacheprovider --basetemp .tmp\pytest-m6-opendota-source
```

Expected: PASS.

- [ ] **Step 6: Commit parser**

Run:

```powershell
git add backend/app/data_sources/opendota.py backend/tests/fixtures/opendota_hero_stats_sample.json backend/tests/test_opendota_source.py
git commit -m "feat: parse opendota hero stats"
```

## Task 2: SQLite Hero Stats Repository

**Files:**
- Create: `backend/app/db/repositories.py`
- Create: `backend/tests/test_stats_repository.py`

- [ ] **Step 1: Write failing repository tests**

Create `backend/tests/test_stats_repository.py`:

```python
from pathlib import Path

from app.data_sources.opendota import OpenDotaHeroStatsRecord
from app.db.repositories import HeroStatsRepository
from app.db.session import create_sqlite_engine


def axe_record() -> OpenDotaHeroStatsRecord:
    return OpenDotaHeroStatsRecord(
        hero_id=2,
        name="npc_dota_hero_axe",
        localized_name="Axe",
        primary_attr="str",
        roles=["Initiator", "Durable"],
        public_pick_count=1000,
        public_win_count=520,
        public_win_rate=0.52,
        public_pick_share=0.25,
        pro_pick_count=22,
        pro_win_count=7,
        pro_ban_count=36,
        refreshed_at="2026-06-19T09:00:00Z",
    )


def juggernaut_record() -> OpenDotaHeroStatsRecord:
    return OpenDotaHeroStatsRecord(
        hero_id=8,
        name="npc_dota_hero_juggernaut",
        localized_name="Juggernaut",
        primary_attr="agi",
        roles=["Carry"],
        public_pick_count=500,
        public_win_count=260,
        public_win_rate=0.52,
        public_pick_share=0.125,
        pro_pick_count=2,
        pro_win_count=1,
        pro_ban_count=0,
        refreshed_at="2026-06-19T09:00:00Z",
    )


def repository(tmp_path: Path) -> HeroStatsRepository:
    return HeroStatsRepository(create_sqlite_engine(tmp_path / "sqlite" / "dota2_rag.db"))


def test_repository_upserts_and_finds_hero_by_name(tmp_path: Path) -> None:
    repo = repository(tmp_path)
    repo.upsert_hero_stats([axe_record()])

    found = repo.find_hero("tell me axe win rate")

    assert found is not None
    assert found.localized_name == "Axe"
    assert found.public_win_rate == 0.52
    assert found.roles == ["Initiator", "Durable"]


def test_repository_returns_top_heroes_by_pick_share(tmp_path: Path) -> None:
    repo = repository(tmp_path)
    repo.upsert_hero_stats([juggernaut_record(), axe_record()])

    top = repo.top_heroes(limit=1)

    assert [record.localized_name for record in top] == ["Axe"]


def test_repository_reports_empty_when_no_stats_exist(tmp_path: Path) -> None:
    repo = repository(tmp_path)

    assert repo.find_hero("Axe win rate") is None
    assert repo.top_heroes(limit=3) == []
```

- [ ] **Step 2: Run repository tests and verify RED**

Run:

```powershell
cd backend
$env:TEMP="$PWD\.tmp"; $env:TMP=$env:TEMP
.\.conda\python.exe -m pytest tests/test_stats_repository.py -v -p no:cacheprovider --basetemp .tmp\pytest-m6-stats-repo
```

Expected: FAIL because `app.db.repositories` does not exist.

- [ ] **Step 3: Implement repository**

Create `backend/app/db/repositories.py`:

```python
from __future__ import annotations

import json
from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.engine import Engine

from app.data_sources.opendota import OpenDotaHeroStatsRecord


@dataclass(frozen=True)
class HeroStatsRow:
    hero_id: int
    name: str
    localized_name: str
    primary_attr: str
    roles: list[str]
    public_pick_count: int
    public_win_count: int
    public_win_rate: float
    public_pick_share: float
    pro_pick_count: int
    pro_win_count: int
    pro_ban_count: int
    refreshed_at: str


class HeroStatsRepository:
    def __init__(self, engine: Engine) -> None:
        self.engine = engine
        self.create_tables()

    def create_tables(self) -> None:
        with self.engine.begin() as connection:
            connection.execute(
                text(
                    """
                    create table if not exists hero_stats (
                        hero_id integer primary key,
                        name text not null,
                        localized_name text not null,
                        primary_attr text not null,
                        roles_json text not null,
                        public_pick_count integer not null,
                        public_win_count integer not null,
                        public_win_rate real not null,
                        public_pick_share real not null,
                        pro_pick_count integer not null,
                        pro_win_count integer not null,
                        pro_ban_count integer not null,
                        refreshed_at text not null
                    )
                    """
                )
            )

    def upsert_hero_stats(self, records: list[OpenDotaHeroStatsRecord]) -> None:
        with self.engine.begin() as connection:
            for record in records:
                connection.execute(
                    text(
                        """
                        insert into hero_stats (
                            hero_id, name, localized_name, primary_attr, roles_json,
                            public_pick_count, public_win_count, public_win_rate, public_pick_share,
                            pro_pick_count, pro_win_count, pro_ban_count, refreshed_at
                        )
                        values (
                            :hero_id, :name, :localized_name, :primary_attr, :roles_json,
                            :public_pick_count, :public_win_count, :public_win_rate, :public_pick_share,
                            :pro_pick_count, :pro_win_count, :pro_ban_count, :refreshed_at
                        )
                        on conflict(hero_id) do update set
                            name = excluded.name,
                            localized_name = excluded.localized_name,
                            primary_attr = excluded.primary_attr,
                            roles_json = excluded.roles_json,
                            public_pick_count = excluded.public_pick_count,
                            public_win_count = excluded.public_win_count,
                            public_win_rate = excluded.public_win_rate,
                            public_pick_share = excluded.public_pick_share,
                            pro_pick_count = excluded.pro_pick_count,
                            pro_win_count = excluded.pro_win_count,
                            pro_ban_count = excluded.pro_ban_count,
                            refreshed_at = excluded.refreshed_at
                        """
                    ),
                    {
                        **record.__dict__,
                        "roles_json": json.dumps(record.roles),
                    },
                )

    def find_hero(self, question: str) -> HeroStatsRow | None:
        lowered = question.lower()
        for row in self.top_heroes(limit=1000):
            if row.localized_name.lower() in lowered or row.name.removeprefix("npc_dota_hero_").replace("_", " ") in lowered:
                return row
        return None

    def top_heroes(self, limit: int = 5) -> list[HeroStatsRow]:
        with self.engine.connect() as connection:
            rows = connection.execute(
                text(
                    """
                    select * from hero_stats
                    order by public_pick_share desc, public_win_rate desc
                    limit :limit
                    """
                ),
                {"limit": limit},
            ).mappings()
            return [_row_from_mapping(row) for row in rows]


def _row_from_mapping(row) -> HeroStatsRow:
    return HeroStatsRow(
        hero_id=int(row["hero_id"]),
        name=str(row["name"]),
        localized_name=str(row["localized_name"]),
        primary_attr=str(row["primary_attr"]),
        roles=[str(role) for role in json.loads(row["roles_json"])],
        public_pick_count=int(row["public_pick_count"]),
        public_win_count=int(row["public_win_count"]),
        public_win_rate=float(row["public_win_rate"]),
        public_pick_share=float(row["public_pick_share"]),
        pro_pick_count=int(row["pro_pick_count"]),
        pro_win_count=int(row["pro_win_count"]),
        pro_ban_count=int(row["pro_ban_count"]),
        refreshed_at=str(row["refreshed_at"]),
    )
```

- [ ] **Step 4: Run repository tests and verify GREEN**

Run:

```powershell
cd backend
$env:TEMP="$PWD\.tmp"; $env:TMP=$env:TEMP
.\.conda\python.exe -m pytest tests/test_stats_repository.py -v -p no:cacheprovider --basetemp .tmp\pytest-m6-stats-repo
```

Expected: PASS.

- [ ] **Step 5: Commit repository**

Run:

```powershell
git add backend/app/db/repositories.py backend/tests/test_stats_repository.py
git commit -m "feat: store hero stats in sqlite"
```

## Task 3: Refresh Job And API

**Files:**
- Create: `backend/app/jobs/refresh_stats.py`
- Create: `backend/app/api/stats.py`
- Modify: `backend/app/main.py`
- Modify: `backend/app/core/config.py`
- Create: `backend/tests/test_refresh_stats_job.py`
- Create: `backend/tests/test_stats_api.py`

- [ ] **Step 1: Write failing refresh job test**

Create `backend/tests/test_refresh_stats_job.py`:

```python
from pathlib import Path

from app.db.repositories import HeroStatsRepository
from app.db.session import create_sqlite_engine
from app.jobs.refresh_stats import refresh_hero_stats


FIXTURE_DIR = Path(__file__).parent / "fixtures"


class FixtureOpenDotaClient:
    def fetch_hero_stats(self) -> str:
        return (FIXTURE_DIR / "opendota_hero_stats_sample.json").read_text(encoding="utf-8")


def test_refresh_hero_stats_writes_records(tmp_path: Path) -> None:
    repo = HeroStatsRepository(create_sqlite_engine(tmp_path / "sqlite" / "dota2_rag.db"))

    result = refresh_hero_stats(
        repository=repo,
        client=FixtureOpenDotaClient(),
        refreshed_at="2026-06-19T09:00:00Z",
    )

    assert result.heroes == 2
    assert result.refreshed_at == "2026-06-19T09:00:00Z"
    assert repo.find_hero("Axe win rate") is not None
```

- [ ] **Step 2: Run refresh job test and verify RED**

Run:

```powershell
cd backend
$env:TEMP="$PWD\.tmp"; $env:TMP=$env:TEMP
.\.conda\python.exe -m pytest tests/test_refresh_stats_job.py -v -p no:cacheprovider --basetemp .tmp\pytest-m6-refresh-job
```

Expected: FAIL because `app.jobs.refresh_stats` does not exist.

- [ ] **Step 3: Implement refresh job**

Create `backend/app/jobs/refresh_stats.py`:

```python
from __future__ import annotations

from datetime import UTC, datetime
from typing import Protocol

from pydantic import BaseModel

from app.data_sources.opendota import OpenDotaClient, parse_hero_stats
from app.db.repositories import HeroStatsRepository


class HeroStatsClient(Protocol):
    def fetch_hero_stats(self) -> str:
        ...


class RefreshStatsResult(BaseModel):
    heroes: int
    refreshed_at: str


def utc_now_iso() -> str:
    return datetime.now(tz=UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def refresh_hero_stats(
    repository: HeroStatsRepository,
    client: HeroStatsClient | None = None,
    refreshed_at: str | None = None,
) -> RefreshStatsResult:
    active_client = client or OpenDotaClient()
    timestamp = refreshed_at or utc_now_iso()
    records = parse_hero_stats(active_client.fetch_hero_stats(), refreshed_at=timestamp)
    repository.upsert_hero_stats(records)
    return RefreshStatsResult(heroes=len(records), refreshed_at=timestamp)
```

- [ ] **Step 4: Run refresh job test and verify GREEN**

Run:

```powershell
cd backend
$env:TEMP="$PWD\.tmp"; $env:TMP=$env:TEMP
.\.conda\python.exe -m pytest tests/test_refresh_stats_job.py -v -p no:cacheprovider --basetemp .tmp\pytest-m6-refresh-job
```

Expected: PASS.

- [ ] **Step 5: Write failing stats API test**

Create `backend/tests/test_stats_api.py`:

```python
from pathlib import Path

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app


FIXTURE_DIR = Path(__file__).parent / "fixtures"


class FixtureOpenDotaClient:
    def fetch_hero_stats(self) -> str:
        return (FIXTURE_DIR / "opendota_hero_stats_sample.json").read_text(encoding="utf-8")


def test_refresh_stats_endpoint_writes_hero_stats(tmp_path: Path) -> None:
    settings = Settings(
        sqlite_path=tmp_path / "sqlite" / "dota2_rag.db",
        vector_data_path=tmp_path / "vectors",
        vector_index_path=tmp_path / "vectors" / "text_chunks.json",
    )
    app = create_app(settings)
    app.state.opendota_client = FixtureOpenDotaClient()
    app.state.stats_refreshed_at = "2026-06-19T09:00:00Z"
    client = TestClient(app)

    response = client.post("/api/refresh/stats")

    assert response.status_code == 200
    assert response.json() == {
        "heroes": 2,
        "refreshed_at": "2026-06-19T09:00:00Z",
    }
```

- [ ] **Step 6: Run stats API test and verify RED**

Run:

```powershell
cd backend
$env:TEMP="$PWD\.tmp"; $env:TMP=$env:TEMP
.\.conda\python.exe -m pytest tests/test_stats_api.py -v -p no:cacheprovider --basetemp .tmp\pytest-m6-stats-api
```

Expected: FAIL because `/api/refresh/stats` does not exist.

- [ ] **Step 7: Add stats API and config**

Modify `backend/app/core/config.py`:

```python
    opendota_base_url: str = "https://api.opendota.com/api"
```

Create `backend/app/api/stats.py`:

```python
from fastapi import APIRouter, HTTPException, Request

from app.data_sources.opendota import OpenDotaClient
from app.db.repositories import HeroStatsRepository
from app.db.session import create_sqlite_engine
from app.jobs.refresh_stats import RefreshStatsResult, refresh_hero_stats

router = APIRouter(prefix="/api", tags=["stats"])


@router.post("/refresh/stats", response_model=RefreshStatsResult)
def refresh_stats(request: Request) -> RefreshStatsResult:
    settings = request.app.state.settings
    repository = HeroStatsRepository(create_sqlite_engine(settings.sqlite_path))
    client = getattr(request.app.state, "opendota_client", None)
    if client is None:
        client = OpenDotaClient(base_url=settings.opendota_base_url)
    refreshed_at = getattr(request.app.state, "stats_refreshed_at", None)
    try:
        return refresh_hero_stats(
            repository=repository,
            client=client,
            refreshed_at=refreshed_at,
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
```

Modify `backend/app/main.py`:

```python
from app.api.stats import router as stats_router
```

and include the router:

```python
    app.include_router(stats_router)
```

- [ ] **Step 8: Run stats API test and verify GREEN**

Run:

```powershell
cd backend
$env:TEMP="$PWD\.tmp"; $env:TMP=$env:TEMP
.\.conda\python.exe -m pytest tests/test_stats_api.py tests/test_refresh_stats_job.py -v -p no:cacheprovider --basetemp .tmp\pytest-m6-stats-api
```

Expected: PASS.

- [ ] **Step 9: Commit refresh API**

Run:

```powershell
git add backend/app/jobs/refresh_stats.py backend/app/api/stats.py backend/app/main.py backend/app/core/config.py backend/tests/test_refresh_stats_job.py backend/tests/test_stats_api.py
git commit -m "feat: refresh opendota hero stats"
```

## Task 4: Template-Backed Stats Chat

**Files:**
- Modify: `backend/app/rag/chat_service.py`
- Modify: `backend/app/api/chat.py`
- Modify: `backend/tests/test_chat_service.py`
- Modify: `backend/tests/test_chat_api.py`

- [ ] **Step 1: Add failing chat service stats tests**

Append to `backend/tests/test_chat_service.py`:

```python
from app.data_sources.opendota import OpenDotaHeroStatsRecord
from app.db.repositories import HeroStatsRepository
from app.db.session import create_sqlite_engine


def stats_repository(tmp_path) -> HeroStatsRepository:
    repo = HeroStatsRepository(create_sqlite_engine(tmp_path / "sqlite" / "dota2_rag.db"))
    repo.upsert_hero_stats(
        [
            OpenDotaHeroStatsRecord(
                hero_id=2,
                name="npc_dota_hero_axe",
                localized_name="Axe",
                primary_attr="str",
                roles=["Initiator"],
                public_pick_count=1000,
                public_win_count=520,
                public_win_rate=0.52,
                public_pick_share=0.25,
                pro_pick_count=22,
                pro_win_count=7,
                pro_ban_count=36,
                refreshed_at="2026-06-19T09:00:00Z",
            )
        ]
    )
    return repo


@pytest.mark.asyncio
async def test_chat_service_answers_stats_question_from_sqlite(tmp_path) -> None:
    store = LocalVectorStore(tmp_path / "vectors.json")
    embedder = DeterministicEmbedder(dimensions=64)
    service = ChatService(
        store=store,
        embedder=embedder,
        generator=FakeGenerator("this should not be used"),
        stats_repository=stats_repository(tmp_path),
    )

    response = await service.answer("Axe pick rate and win rate meta")

    assert response.question_type == "stats"
    assert "Axe" in response.answer
    assert "52.0%" in response.answer
    assert "25.0%" in response.answer
    assert "1,000" in response.answer
    assert "2026-06-19T09:00:00Z" in response.answer
    assert response.sources == []


@pytest.mark.asyncio
async def test_chat_service_stats_question_requires_refresh_when_empty(tmp_path) -> None:
    store = LocalVectorStore(tmp_path / "vectors.json")
    embedder = DeterministicEmbedder(dimensions=64)
    service = ChatService(
        store=store,
        embedder=embedder,
        generator=FakeGenerator("this should not be used"),
        stats_repository=HeroStatsRepository(create_sqlite_engine(tmp_path / "sqlite" / "dota2_rag.db")),
    )

    response = await service.answer("Axe win rate meta")

    assert response.question_type == "stats"
    assert "POST /api/refresh/stats" in response.answer
    assert response.sources == []
```

- [ ] **Step 2: Run chat service tests and verify RED**

Run:

```powershell
cd backend
$env:TEMP="$PWD\.tmp"; $env:TMP=$env:TEMP
.\.conda\python.exe -m pytest tests/test_chat_service.py -v -p no:cacheprovider --basetemp .tmp\pytest-m6-chat-service
```

Expected: FAIL because `ChatService` does not accept `stats_repository`.

- [ ] **Step 3: Implement stats answer path**

Modify `backend/app/rag/chat_service.py`.

Add imports:

```python
from app.db.repositories import HeroStatsRepository, HeroStatsRow
```

Change `ChatDebug`:

```python
class ChatDebug(BaseModel):
    retrieved_chunks: int
    top_score: float | None
    stats_used: bool = False
```

Change `ChatService.__init__`:

```python
        stats_repository: HeroStatsRepository | None = None,
```

and assign:

```python
        self.stats_repository = stats_repository
```

At the start of `answer`, after `question_type = classify_question(question)`:

```python
        if question_type == "stats" and self.stats_repository is not None:
            stats_answer = self._answer_stats_question(question)
            if stats_answer is not None:
                return stats_answer
```

Add methods:

```python
    def _answer_stats_question(self, question: str) -> ChatAnswer | None:
        if self.stats_repository is None:
            return None
        hero = self.stats_repository.find_hero(question)
        if hero is not None:
            return ChatAnswer(
                answer=_format_hero_stats_answer(hero),
                question_type="stats",
                sources=[],
                debug=ChatDebug(retrieved_chunks=0, top_score=None, stats_used=True),
            )
        top = self.stats_repository.top_heroes(limit=3)
        if top:
            names = ", ".join(
                f"{row.localized_name} ({row.public_pick_share * 100:.1f}% pick share)"
                for row in top
            )
            return ChatAnswer(
                answer=(
                    f"当前本地 OpenDota 公共比赛样本里，选取占比较高的英雄包括：{names}。"
                    f"数据刷新时间：{top[0].refreshed_at}。"
                    "这些是样本统计，不代表实时全局 Meta。"
                ),
                question_type="stats",
                sources=[],
                debug=ChatDebug(retrieved_chunks=0, top_score=None, stats_used=True),
            )
        return ChatAnswer(
            answer="当前本地还没有英雄统计数据。请先调用 POST /api/refresh/stats 刷新 OpenDota 数据。",
            question_type="stats",
            sources=[],
            debug=ChatDebug(retrieved_chunks=0, top_score=None, stats_used=False),
        )


def _format_hero_stats_answer(hero: HeroStatsRow) -> str:
    return (
        f"{hero.localized_name} 在当前本地 OpenDota 公共比赛样本中："
        f"胜率约 {hero.public_win_rate * 100:.1f}%，"
        f"选取占比约 {hero.public_pick_share * 100:.1f}%，"
        f"样本数 {hero.public_pick_count:,} 场。"
        f"数据刷新时间：{hero.refreshed_at}。"
        "这些统计来自 OpenDota 公共比赛样本，不代表实时全局 Meta，也不应单独决定选人。"
    )
```

- [ ] **Step 4: Wire chat API repository**

Modify `backend/app/api/chat.py`.

Add imports:

```python
from app.db.repositories import HeroStatsRepository
from app.db.session import create_sqlite_engine
```

Pass repository to `ChatService`:

```python
        stats_repository=HeroStatsRepository(create_sqlite_engine(settings.sqlite_path)),
```

- [ ] **Step 5: Run chat service tests and verify GREEN**

Run:

```powershell
cd backend
$env:TEMP="$PWD\.tmp"; $env:TMP=$env:TEMP
.\.conda\python.exe -m pytest tests/test_chat_service.py -v -p no:cacheprovider --basetemp .tmp\pytest-m6-chat-service
```

Expected: PASS.

- [ ] **Step 6: Add chat API stats smoke test**

Append to `backend/tests/test_chat_api.py`:

```python
from pathlib import Path


FIXTURE_DIR = Path(__file__).parent / "fixtures"


class FixtureOpenDotaClient:
    def fetch_hero_stats(self) -> str:
        return (FIXTURE_DIR / "opendota_hero_stats_sample.json").read_text(encoding="utf-8")


def test_chat_endpoint_answers_stats_after_refresh(tmp_path: Path) -> None:
    settings = Settings(
        sqlite_path=tmp_path / "sqlite" / "dota2_rag.db",
        vector_data_path=tmp_path / "vectors",
        vector_index_path=tmp_path / "vectors" / "text_chunks.json",
    )
    app = create_app(settings)
    app.state.opendota_client = FixtureOpenDotaClient()
    app.state.stats_refreshed_at = "2026-06-19T09:00:00Z"
    client = TestClient(app)
    client.post("/api/refresh/stats")

    response = client.post("/api/chat", json={"message": "Axe win rate meta"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["question_type"] == "stats"
    assert "Axe" in payload["answer"]
    assert "52.0%" in payload["answer"]
    assert payload["debug"]["stats_used"] is True
```

- [ ] **Step 7: Run chat API tests and verify GREEN**

Run:

```powershell
cd backend
$env:TEMP="$PWD\.tmp"; $env:TMP=$env:TEMP
.\.conda\python.exe -m pytest tests/test_chat_api.py tests/test_chat_service.py -v -p no:cacheprovider --basetemp .tmp\pytest-m6-chat-api
```

Expected: PASS.

- [ ] **Step 8: Commit stats chat**

Run:

```powershell
git add backend/app/rag/chat_service.py backend/app/api/chat.py backend/tests/test_chat_service.py backend/tests/test_chat_api.py
git commit -m "feat: answer hero stats questions"
```

## Task 5: Documentation And Final Verification

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Add M6 README instructions**

Append to `README.md`:

```markdown
## M6 OpenDota Hero Stats

M6 adds a local SQLite snapshot of OpenDota public-match hero statistics.

Refresh the local stats snapshot:

```powershell
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/api/refresh/stats
```

Then ask a stats question:

```powershell
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/api/chat -ContentType "application/json" -Body '{"message":"Axe win rate meta"}'
```

M6 stats answers include public win rate, public pick share, sample size, and refresh timestamp. They are OpenDota public-match samples, not real-time global truth. Item trends and match sample analysis are intentionally out of scope for M6.
```

- [ ] **Step 2: Run M6 targeted backend tests**

Run:

```powershell
cd backend
$env:TEMP="$PWD\.tmp"; $env:TMP=$env:TEMP
.\.conda\python.exe -m pytest tests/test_opendota_source.py tests/test_stats_repository.py tests/test_refresh_stats_job.py tests/test_stats_api.py tests/test_chat_service.py tests/test_chat_api.py -v -p no:cacheprovider --basetemp .tmp\pytest-m6-targeted
```

Expected: PASS.

- [ ] **Step 3: Run full backend tests**

Run:

```powershell
cd backend
$env:TEMP="$PWD\.tmp"; $env:TMP=$env:TEMP
.\.conda\python.exe -m pytest -v -p no:cacheprovider --basetemp .tmp\pytest-m6-final
```

Expected: PASS.

- [ ] **Step 4: Run frontend regression tests and build**

Run:

```powershell
cd frontend
npm test
npm run build
```

Expected: PASS.

- [ ] **Step 5: Optional live smoke**

With backend running, run:

```powershell
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/api/refresh/stats | ConvertTo-Json -Depth 8
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/api/chat -ContentType "application/json" -Body '{"message":"Axe win rate meta"}' | ConvertTo-Json -Depth 8
```

Expected: refresh returns a hero count greater than 100 and chat answer includes `Axe`, win rate, pick share, sample size, and freshness.

- [ ] **Step 6: Commit docs and final fixes**

Run:

```powershell
git add README.md
git commit -m "docs: add m6 opendota stats instructions"
```

## Self-Review Notes

- Spec coverage: this plan covers OpenDota fetch/parse, SQLite persistence, refresh API, chat stats answers, freshness caveats, tests, and README.
- Scope: this plan intentionally excludes items, item builds, match samples, frontend charts, scheduled refresh, skill brackets, and pro-only analysis.
- Type consistency: `OpenDotaHeroStatsRecord` feeds `HeroStatsRepository.upsert_hero_stats`; repository returns `HeroStatsRow`; chat service formats `HeroStatsRow`.
- Test isolation: all OpenDota tests use fixtures or injected clients and do not call live network.
