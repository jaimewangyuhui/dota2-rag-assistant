from fastapi import APIRouter, Request
from pydantic import BaseModel

from app.jobs.ingest_documents import IngestResult, ingest_seed_documents
from app.rag.embeddings import DeterministicEmbedder
from app.vector_store.milvus import LocalVectorStore

router = APIRouter(prefix="/api", tags=["ingestion"])


class SourcesResponse(BaseModel):
    sources: list[str]


def _store_for_request(request: Request) -> LocalVectorStore:
    settings = request.app.state.settings
    return LocalVectorStore(settings.vector_index_path)


@router.post("/ingest/documents", response_model=IngestResult)
def ingest_documents(request: Request) -> IngestResult:
    store = _store_for_request(request)
    embedder = DeterministicEmbedder(dimensions=64)
    return ingest_seed_documents(store=store, embedder=embedder)


@router.get("/sources", response_model=SourcesResponse)
def list_sources(request: Request) -> SourcesResponse:
    store = _store_for_request(request)
    return SourcesResponse(sources=store.list_sources())
