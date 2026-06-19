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
