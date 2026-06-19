from collections import Counter
from typing import Annotated

from fastapi import APIRouter, Query, Request
from pydantic import BaseModel, Field

from app.rag.schemas import TextChunk
from app.vector_store.milvus import LocalVectorStore

router = APIRouter(prefix="/api/knowledge", tags=["knowledge"])


class KnowledgeSummaryResponse(BaseModel):
    total_chunks: int
    total_sources: int
    by_entity_type: dict[str, int]
    by_source_prefix: dict[str, int]
    updated_at: str | None


class KnowledgeChunkPreview(BaseModel):
    chunk_id: str
    source_name: str
    source_url: str
    entity_type: str
    entity_name: str
    patch_version: str | None
    updated_at: str
    preview: str = Field(min_length=1)


class KnowledgeChunksResponse(BaseModel):
    chunks: list[KnowledgeChunkPreview]


def _store_for_request(request: Request) -> LocalVectorStore:
    settings = request.app.state.settings
    return LocalVectorStore(settings.vector_index_path)


def _source_prefix(source_name: str) -> str:
    if source_name.startswith("OpenDota Hero:"):
        return "OpenDota Hero"
    if source_name.startswith("OpenDota Item:"):
        return "OpenDota Item"
    if source_name.startswith("Seed:"):
        return "Seed"
    if source_name.startswith("Official Dota 2:"):
        return "Official Dota 2"
    return "Other"


def _preview(text: str, max_chars: int = 240) -> str:
    normalized = " ".join(text.split())
    return normalized[:max_chars]


def _matches_query(chunk: TextChunk, query: str | None) -> bool:
    if not query:
        return True
    needle = query.casefold()
    metadata = chunk.metadata
    haystack = " ".join(
        [
            chunk.text,
            metadata.source_name,
            metadata.source_url,
            metadata.entity_name,
            metadata.entity_type,
            metadata.patch_version or "",
        ]
    ).casefold()
    return needle in haystack


def _matches_entity_type(chunk: TextChunk, entity_type: str | None) -> bool:
    return entity_type is None or chunk.metadata.entity_type == entity_type


def _matches_source_prefix(chunk: TextChunk, source_prefix: str | None) -> bool:
    return source_prefix is None or _source_prefix(chunk.metadata.source_name) == source_prefix


def _chunk_preview(chunk: TextChunk) -> KnowledgeChunkPreview:
    return KnowledgeChunkPreview(
        chunk_id=chunk.chunk_id,
        source_name=chunk.metadata.source_name,
        source_url=chunk.metadata.source_url,
        entity_type=chunk.metadata.entity_type,
        entity_name=chunk.metadata.entity_name,
        patch_version=chunk.metadata.patch_version,
        updated_at=chunk.metadata.updated_at,
        preview=_preview(chunk.text),
    )


@router.get("/summary", response_model=KnowledgeSummaryResponse)
def knowledge_summary(request: Request) -> KnowledgeSummaryResponse:
    store = _store_for_request(request)
    chunks = [record.chunk for record in store.records.values()]
    entity_counts = Counter(chunk.metadata.entity_type for chunk in chunks)
    source_prefix_counts = Counter(_source_prefix(chunk.metadata.source_name) for chunk in chunks)
    updated_values = [chunk.metadata.updated_at for chunk in chunks if chunk.metadata.updated_at]
    return KnowledgeSummaryResponse(
        total_chunks=len(chunks),
        total_sources=len({chunk.metadata.source_name for chunk in chunks}),
        by_entity_type=dict(sorted(entity_counts.items())),
        by_source_prefix=dict(sorted(source_prefix_counts.items())),
        updated_at=max(updated_values) if updated_values else None,
    )


@router.get("/chunks", response_model=KnowledgeChunksResponse)
def knowledge_chunks(
    request: Request,
    q: str | None = None,
    entity_type: str | None = None,
    source_prefix: str | None = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> KnowledgeChunksResponse:
    store = _store_for_request(request)
    chunks = [record.chunk for record in store.records.values()]
    filtered = [
        chunk
        for chunk in chunks
        if _matches_query(chunk, q)
        and _matches_entity_type(chunk, entity_type)
        and _matches_source_prefix(chunk, source_prefix)
    ]
    filtered.sort(key=lambda chunk: (chunk.metadata.source_name, chunk.chunk_id))
    return KnowledgeChunksResponse(
        chunks=[_chunk_preview(chunk) for chunk in filtered[:limit]],
    )
