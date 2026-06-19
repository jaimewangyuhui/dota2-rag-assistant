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
