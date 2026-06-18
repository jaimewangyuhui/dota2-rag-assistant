from app.rag.chunker import chunk_document
from app.rag.schemas import DocumentInput, SourceMetadata


def test_chunk_document_preserves_source_metadata() -> None:
    document = DocumentInput(
        text="Black King Bar gives spell immunity. BKB is timing-sensitive.",
        metadata=SourceMetadata(
            source_url="seed://items/black-king-bar",
            source_name="Seed: Black King Bar",
            patch_version="7.36",
            entity_type="item",
            entity_name="Black King Bar",
            updated_at="2026-06-18",
        ),
    )

    chunks = chunk_document(document, max_chars=80, overlap_chars=10)

    assert len(chunks) == 1
    assert chunks[0].text == document.text
    assert chunks[0].metadata.entity_name == "Black King Bar"
    assert chunks[0].metadata.source_url == "seed://items/black-king-bar"


def test_chunk_document_splits_long_text_with_overlap() -> None:
    text = " ".join(f"word{i}" for i in range(40))
    document = DocumentInput(
        text=text,
        metadata=SourceMetadata(
            source_url="seed://mechanics/test",
            source_name="Seed: Test",
            patch_version="7.36",
            entity_type="mechanic",
            entity_name="Test Mechanic",
            updated_at="2026-06-18",
        ),
    )

    chunks = chunk_document(document, max_chars=80, overlap_chars=20)

    assert len(chunks) > 1
    assert chunks[0].chunk_id == "seed://mechanics/test#chunk-0"
    assert chunks[1].chunk_id == "seed://mechanics/test#chunk-1"
    assert chunks[0].metadata == chunks[1].metadata
    assert set(chunks[0].text.split()) & set(chunks[1].text.split())
