import pytest

from app.data_sources.opendota import OpenDotaHeroStatsRecord
from app.db.repositories import HeroStatsRepository
from app.db.session import create_sqlite_engine
from app.jobs.ingest_documents import ingest_seed_documents
from app.rag.chat_service import ChatService
from app.rag.classifier import classify_question
from app.rag.embeddings import DeterministicEmbedder
from app.rag.generator import FakeGenerator
from app.rag.prompt_builder import build_prompt
from app.vector_store.milvus import LocalVectorStore
from tests.fixtures.demo_acceptance import DEMO_ACCEPTANCE_CASES, DemoAcceptanceCase


def test_demo_acceptance_cases_cover_required_question_types() -> None:
    question_types = {case.expected_type for case in DEMO_ACCEPTANCE_CASES}

    assert question_types == {"knowledge", "advice", "stats", "patch", "knowledge_missing"}


def test_demo_acceptance_cases_are_readable_contracts() -> None:
    for case in DEMO_ACCEPTANCE_CASES:
        assert isinstance(case, DemoAcceptanceCase)
        assert case.question
        assert case.expected_type
        assert not (case.requires_sources and case.allows_missing_coverage)


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


@pytest.mark.parametrize("case", DEMO_ACCEPTANCE_CASES)
def test_demo_acceptance_routes(case: DemoAcceptanceCase) -> None:
    expected = "knowledge" if case.expected_type == "knowledge_missing" else case.expected_type

    assert classify_question(case.question) == expected


@pytest.mark.asyncio
@pytest.mark.parametrize("case", [case for case in DEMO_ACCEPTANCE_CASES if case.requires_stats])
async def test_demo_acceptance_stats_answers_use_sqlite(tmp_path, case: DemoAcceptanceCase) -> None:
    service = ChatService(
        store=LocalVectorStore(tmp_path / "vectors.json"),
        embedder=DeterministicEmbedder(dimensions=64),
        generator=FakeGenerator("this should not be used"),
        stats_repository=make_stats_repository(tmp_path),
    )

    response = await service.answer(case.question)

    assert response.question_type == "stats"
    assert response.debug.stats_used is True
    for term in case.expected_terms:
        assert term in response.answer
    assert "OpenDota" in response.answer


@pytest.mark.asyncio
async def test_demo_acceptance_missing_coverage_is_explicit(tmp_path) -> None:
    missing_case = next(case for case in DEMO_ACCEPTANCE_CASES if case.allows_missing_coverage)
    service = ChatService(
        store=LocalVectorStore(tmp_path / "vectors.json"),
        embedder=DeterministicEmbedder(dimensions=64),
        generator=FakeGenerator("this should not be used"),
    )

    response = await service.answer(missing_case.question)

    assert response.question_type == "knowledge"
    assert response.sources == []
    assert "当前知识库没有覆盖" in response.answer


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "case",
    [
        case
        for case in DEMO_ACCEPTANCE_CASES
        if case.requires_sources and case.expected_type in {"knowledge", "advice", "patch"}
    ],
)
async def test_demo_acceptance_text_answers_keep_sources_and_terms(
    tmp_path,
    case: DemoAcceptanceCase,
) -> None:
    store = LocalVectorStore(tmp_path / "vectors.json")
    embedder = DeterministicEmbedder(dimensions=64)
    ingest_seed_documents(store=store, embedder=embedder)
    service = ChatService(
        store=store,
        embedder=embedder,
        generator=FakeGenerator(
            "直接结论: Black King Bar / BKB, Roshan, and Blink Dagger are preserved."
        ),
        minimum_score=-1.0,
    )

    response = await service.answer(case.question)

    assert response.question_type == case.expected_type
    assert response.sources
    for term in case.expected_terms:
        assert term in response.answer or any(term in source.entity_name for source in response.sources)


def test_demo_acceptance_prompt_contract_mentions_missing_coverage() -> None:
    prompt = build_prompt(
        question="Chen 的神杖效果是什么？",
        question_type="knowledge",
        retrieved_chunks=[],
        canonical_terms=[],
    )

    assert "当前知识库没有覆盖这个问题" in prompt
    assert "来源/数据新鲜度" in prompt
