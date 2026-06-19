from collections.abc import Callable, Sequence

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


DocumentLoader = Callable[[], list[DocumentInput]]
OfficialDocumentsLoader = DocumentLoader


def ingest_seed_documents(
    store: LocalVectorStore,
    embedder: Embedder,
    official_documents_loader: OfficialDocumentsLoader | None = None,
    document_loaders: Sequence[DocumentLoader] | None = None,
) -> IngestResult:
    documents = load_seed_documents()
    active_loaders: list[DocumentLoader] = []
    if official_documents_loader is not None:
        active_loaders.append(official_documents_loader)
    if document_loaders is not None:
        active_loaders.extend(document_loaders)
    for loader in active_loaders:
        documents.extend(loader())

    chunks = [chunk for document in documents for chunk in chunk_document(document)]
    entries = [(chunk, embedder.embed(chunk.text)) for chunk in chunks]
    store.upsert(entries)
    return IngestResult(
        documents=len(documents),
        chunks=len(chunks),
        sources=store.list_sources(),
    )
