import httpx
import pytest

from app.rag.embeddings import DeterministicEmbedder, OllamaEmbedder, cosine_similarity


def test_deterministic_embedder_returns_stable_vectors() -> None:
    embedder = DeterministicEmbedder(dimensions=16)

    first = embedder.embed("Black King Bar BKB spell immunity")
    second = embedder.embed("Black King Bar BKB spell immunity")

    assert first == second
    assert len(first) == 16


def test_deterministic_embedder_scores_related_text_higher() -> None:
    embedder = DeterministicEmbedder(dimensions=32)
    query = embedder.embed("BKB spell immunity")
    related = embedder.embed("Black King Bar gives spell immunity")
    unrelated = embedder.embed("Roshan drops Aegis")

    assert cosine_similarity(query, related) > cosine_similarity(query, unrelated)


@pytest.mark.asyncio
async def test_ollama_embedder_reads_embedding_response() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/embeddings"
        return httpx.Response(200, json={"embedding": [0.1, 0.2, 0.3]})

    embedder = OllamaEmbedder(
        base_url="http://ollama.test",
        model="nomic-embed-text",
        transport=httpx.MockTransport(handler),
    )

    assert await embedder.aembed("BKB") == [0.1, 0.2, 0.3]
