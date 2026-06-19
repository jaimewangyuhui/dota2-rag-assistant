from __future__ import annotations

import json
from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.engine import Engine, RowMapping

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
            slug_name = row.name.removeprefix("npc_dota_hero_").replace("_", " ")
            if row.localized_name.lower() in lowered or slug_name in lowered:
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


def _row_from_mapping(row: RowMapping) -> HeroStatsRow:
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
