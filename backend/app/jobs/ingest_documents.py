from collections.abc import Callable

from pydantic import BaseModel

from app.data_sources.seed_documents import load_seed_documents
from app.rag.chunker import chunk_document
from app.rag.embeddings import Embedder
from app.rag.schemas import DocumentInput
from app.vector_store.milvus import LocalVectorStore


class IngestResult(BaseModel):
    documents: int
    chunks: int
    sources: list[str]


OfficialDocumentsLoader = Callable[[], list[DocumentInput]]


def ingest_seed_documents(
    store: LocalVectorStore,
    embedder: Embedder,
    official_documents_loader: OfficialDocumentsLoader | None = None,
) -> IngestResult:
    documents = load_seed_documents()
    if official_documents_loader is not None:
        documents.extend(official_documents_loader())
    chunks = [chunk for document in documents for chunk in chunk_document(document)]
    entries = [(chunk, embedder.embed(chunk.text)) for chunk in chunks]
    store.upsert(entries)
    return IngestResult(
        documents=len(documents),
        chunks=len(chunks),
        sources=store.list_sources(),
    )
