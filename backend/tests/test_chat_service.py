import pytest

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
