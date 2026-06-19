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
