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
