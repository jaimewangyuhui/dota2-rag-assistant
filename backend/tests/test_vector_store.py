from pathlib import Path

from app.rag.schemas import SourceMetadata, TextChunk
from app.vector_store.milvus import LocalVectorStore


def make_chunk(chunk_id: str, text: str, entity_name: str) -> TextChunk:
    return TextChunk(
        chunk_id=chunk_id,
        text=text,
        metadata=SourceMetadata(
            source_url=f"seed://{chunk_id}",
            source_name=f"Seed: {entity_name}",
            patch_version="7.36",
            entity_type="item",
            entity_name=entity_name,
            updated_at="2026-06-18",
        ),
    )


def test_vector_store_upserts_and_searches_chunks(tmp_path: Path) -> None:
    store = LocalVectorStore(tmp_path / "vectors.json")
    store.upsert(
        [
            (
                make_chunk("bkb-1", "Black King Bar blocks many spells", "Black King Bar"),
                [1.0, 0.0],
            ),
            (make_chunk("roshan-1", "Roshan drops Aegis", "Roshan"), [0.0, 1.0]),
        ]
    )

    results = store.search([1.0, 0.0], limit=1)

    assert len(results) == 1
    assert results[0].chunk.chunk_id == "bkb-1"
    assert results[0].chunk.metadata.source_name == "Seed: Black King Bar"


def test_vector_store_persists_records(tmp_path: Path) -> None:
    path = tmp_path / "vectors.json"
    store = LocalVectorStore(path)
    store.upsert([(make_chunk("bkb-1", "Black King Bar", "Black King Bar"), [1.0, 0.0])])

    reloaded = LocalVectorStore(path)

    assert reloaded.list_sources() == ["Seed: Black King Bar"]
    assert reloaded.search([1.0, 0.0], limit=1)[0].chunk.chunk_id == "bkb-1"
