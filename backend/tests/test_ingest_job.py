from pathlib import Path

from app.jobs.ingest_documents import ingest_seed_documents
from app.rag.embeddings import DeterministicEmbedder
from app.rag.retriever import Retriever
from app.rag.schemas import DocumentInput, SourceMetadata
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


def official_test_documents() -> list[DocumentInput]:
    return [
        DocumentInput(
            text="Axe is an official Dota 2 hero with Initiator and Durable roles.",
            metadata=SourceMetadata(
                source_url="https://www.dota2.com/heroes/axe",
                source_name="Official Dota 2: Axe",
                patch_version=None,
                entity_type="hero",
                entity_name="Axe",
                updated_at="2026-06-19",
            ),
        ),
        DocumentInput(
            text="Gameplay Update 7.36 added innate abilities for heroes.",
            metadata=SourceMetadata(
                source_url="https://www.dota2.com/patches/7.36",
                source_name="Official Dota 2 Patch 7.36",
                patch_version="7.36",
                entity_type="patch",
                entity_name="Gameplay Update 7.36",
                updated_at="2026-06-18",
            ),
        ),
    ]


def test_ingest_seed_documents_can_include_official_documents(tmp_path: Path) -> None:
    store = LocalVectorStore(tmp_path / "vectors.json")
    embedder = DeterministicEmbedder(dimensions=64)

    result = ingest_seed_documents(
        store=store,
        embedder=embedder,
        official_documents_loader=official_test_documents,
    )

    assert result.documents == 5
    assert "Official Dota 2: Axe" in result.sources
    retrieved = Retriever(store=store, embedder=embedder).retrieve("Axe official hero", limit=1)
    assert retrieved[0].chunk.metadata.entity_name == "Axe"
