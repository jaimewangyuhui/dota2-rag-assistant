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
