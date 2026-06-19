import pytest

from app.data_sources.opendota import OpenDotaHeroStatsRecord
from app.db.repositories import HeroStatsRepository
from app.db.session import create_sqlite_engine
from app.jobs.ingest_documents import ingest_seed_documents
from app.rag.chat_service import ChatService
from app.rag.classifier import classify_question
from app.rag.embeddings import DeterministicEmbedder
from app.rag.generator import FakeGenerator
from app.vector_store.milvus import LocalVectorStore


@pytest.mark.parametrize(
    ("question", "expected_type"),
    [
        ("BKB有什么用？", "knowledge"),
        ("What does BKB do?", "knowledge"),
        ("黑皇杖什么时候出？", "advice"),
        ("Roshan 会掉什么？", "knowledge"),
        ("肉山掉什么？", "knowledge"),
        ("Axe win rate meta", "stats"),
        ("斧王胜率", "stats"),
        ("Blink Dagger怎么用？", "advice"),
        ("跳刀怎么用？", "advice"),
    ],
)
def test_golden_question_routes(question: str, expected_type: str) -> None:
    assert classify_question(question) == expected_type


def make_stats_repository(tmp_path) -> HeroStatsRepository:
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
async def test_golden_stats_alias_answer_uses_local_stats(tmp_path) -> None:
    service = ChatService(
        store=LocalVectorStore(tmp_path / "vectors.json"),
        embedder=DeterministicEmbedder(dimensions=64),
        generator=FakeGenerator("this should not be used"),
        stats_repository=make_stats_repository(tmp_path),
    )

    response = await service.answer("斧王胜率")

    assert response.question_type == "stats"
    assert response.debug.stats_used is True
    assert "Axe" in response.answer
    assert "52.0%" in response.answer
    assert "2026-06-19T09:00:00Z" in response.answer


@pytest.mark.asyncio
async def test_golden_bkb_alias_answer_keeps_sources(tmp_path) -> None:
    store = LocalVectorStore(tmp_path / "vectors.json")
    embedder = DeterministicEmbedder(dimensions=64)
    ingest_seed_documents(store=store, embedder=embedder)
    service = ChatService(
        store=store,
        embedder=embedder,
        generator=FakeGenerator("直接结论: Black King Bar / BKB helps against many spells."),
    )

    response = await service.answer("黑皇杖有什么用？")

    assert response.question_type == "knowledge"
    assert "Black King Bar" in response.answer
    assert response.sources
