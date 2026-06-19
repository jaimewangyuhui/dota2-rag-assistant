import pytest

from app.data_sources.opendota import OpenDotaHeroStatsRecord
from app.db.repositories import HeroStatsRepository
from app.db.session import create_sqlite_engine
from app.jobs.ingest_documents import ingest_seed_documents
from app.rag.chat_service import ChatService
from app.rag.embeddings import DeterministicEmbedder
from app.rag.generator import FakeGenerator
from app.vector_store.milvus import LocalVectorStore


@pytest.mark.asyncio
async def test_chat_service_answers_with_sources(tmp_path) -> None:
    store = LocalVectorStore(tmp_path / "vectors.json")
    embedder = DeterministicEmbedder(dimensions=64)
    ingest_seed_documents(store=store, embedder=embedder)
    service = ChatService(
        store=store,
        embedder=embedder,
        generator=FakeGenerator("BKB 可以提供短时间 spell immunity，用来抵抗很多控制。"),
    )

    response = await service.answer("BKB 有什么用?")

    assert response.question_type == "knowledge"
    assert "BKB" in response.answer
    assert response.sources[0].source_name == "Seed: Black King Bar"
    assert response.debug.retrieved_chunks >= 1


@pytest.mark.asyncio
async def test_chat_service_returns_uncertainty_when_retrieval_is_insufficient(tmp_path) -> None:
    store = LocalVectorStore(tmp_path / "vectors.json")
    embedder = DeterministicEmbedder(dimensions=64)
    service = ChatService(
        store=store,
        embedder=embedder,
        generator=FakeGenerator("this should not be used"),
    )

    response = await service.answer("Chen 的神杖效果是什么?")

    assert response.answer == "当前知识库没有覆盖这个问题，无法基于已索引来源可靠回答。"
    assert response.sources == []
    assert response.debug.retrieved_chunks == 0


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


@pytest.mark.asyncio
async def test_chat_service_answers_chinese_hero_alias_stats_question(tmp_path) -> None:
    store = LocalVectorStore(tmp_path / "vectors.json")
    embedder = DeterministicEmbedder(dimensions=64)
    service = ChatService(
        store=store,
        embedder=embedder,
        generator=FakeGenerator("this should not be used"),
        stats_repository=stats_repository(tmp_path),
    )

    response = await service.answer("斧王胜率")

    assert response.question_type == "stats"
    assert response.debug.stats_used is True
    assert "Axe" in response.answer
    assert "52.0%" in response.answer


class RecordingEmbedder(DeterministicEmbedder):
    def __init__(self) -> None:
        super().__init__(dimensions=64)
        self.last_text: str | None = None

    def embed(self, text: str) -> list[float]:
        self.last_text = text
        return super().embed(text)


@pytest.mark.asyncio
async def test_chat_service_uses_expanded_text_for_retrieval(tmp_path) -> None:
    store = LocalVectorStore(tmp_path / "vectors.json")
    embedder = RecordingEmbedder()
    ingest_seed_documents(store=store, embedder=embedder)
    service = ChatService(
        store=store,
        embedder=embedder,
        generator=FakeGenerator("Black King Bar answer"),
    )

    await service.answer("黑皇杖有什么用？")

    assert embedder.last_text is not None
    assert "黑皇杖有什么用？" in embedder.last_text
    assert "Black King Bar" in embedder.last_text
    assert "BKB" in embedder.last_text
