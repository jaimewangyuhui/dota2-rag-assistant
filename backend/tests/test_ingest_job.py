from pathlib import Path

from app.jobs.ingest_documents import ingest_seed_documents
from app.rag.embeddings import DeterministicEmbedder
from app.rag.retriever import Retriever
from app.vector_store.milvus import LocalVectorStore


def test_ingest_seed_documents_makes_bkb_retrievable(tmp_path: Path) -> None:
    store = LocalVectorStore(tmp_path / "vectors.json")
    embedder = DeterministicEmbedder(dimensions=64)

    result = ingest_seed_documents(store=store, embedder=embedder)

    assert result.documents == 3
    assert result.chunks >= 3
    retrieved = Retriever(store=store, embedder=embedder).retrieve("BKB spell immunity", limit=2)
    assert retrieved[0].chunk.metadata.entity_name == "Black King Bar"
    assert retrieved[0].chunk.metadata.source_url == "seed://items/black-king-bar"
