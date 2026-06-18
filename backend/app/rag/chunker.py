from app.rag.schemas import DocumentInput, TextChunk


def _normalize_text(text: str) -> str:
    return " ".join(text.split())


def _split_words(text: str, max_chars: int, overlap_chars: int) -> list[str]:
    words = text.split()
    chunks: list[str] = []
    current: list[str] = []

    for word in words:
        candidate = " ".join([*current, word])
        if current and len(candidate) > max_chars:
            chunks.append(" ".join(current))
            overlap: list[str] = []
            overlap_length = 0
            for previous in reversed(current):
                next_length = overlap_length + len(previous) + (1 if overlap else 0)
                if next_length > overlap_chars:
                    break
                overlap.insert(0, previous)
                overlap_length = next_length
            current = [*overlap, word]
        else:
            current.append(word)

    if current:
        chunks.append(" ".join(current))
    return chunks


def chunk_document(
    document: DocumentInput,
    max_chars: int = 900,
    overlap_chars: int = 120,
) -> list[TextChunk]:
    normalized = _normalize_text(document.text)
    parts = _split_words(normalized, max_chars=max_chars, overlap_chars=overlap_chars)
    return [
        TextChunk(
            chunk_id=f"{document.metadata.source_url}#chunk-{index}",
            text=part,
            metadata=document.metadata,
        )
        for index, part in enumerate(parts)
    ]
