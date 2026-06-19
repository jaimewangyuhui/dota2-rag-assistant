from fastapi import APIRouter, Request
from pydantic import BaseModel

from app.data_sources.official_dota import load_official_dota_documents
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
    settings = request.app.state.settings
    official_documents_loader = getattr(request.app.state, "official_documents_loader", None)
    if official_documents_loader is None and settings.official_dota_sources_enabled:
        official_documents_loader = load_official_dota_documents
    return ingest_seed_documents(
        store=store,
        embedder=embedder,
        official_documents_loader=official_documents_loader,
    )


@router.get("/sources", response_model=SourcesResponse)
def list_sources(request: Request) -> SourcesResponse:
    store = _store_for_request(request)
    return SourcesResponse(sources=store.list_sources())
