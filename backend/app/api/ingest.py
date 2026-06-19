from fastapi import APIRouter, Request
from pydantic import BaseModel

from app.data_sources.official_dota import load_official_dota_documents
from app.data_sources.opendota_knowledge import (
    OpenDotaKnowledgeClient,
    load_opendota_knowledge_documents,
)
from app.jobs.ingest_documents import DocumentLoader, IngestResult, ingest_seed_documents
from app.rag.embeddings import DeterministicEmbedder
from app.rag.schemas import DocumentInput
from app.vector_store.milvus import LocalVectorStore

router = APIRouter(prefix="/api", tags=["ingestion"])


class SourcesResponse(BaseModel):
    sources: list[str]


def _store_for_request(request: Request) -> LocalVectorStore:
    settings = request.app.state.settings
    return LocalVectorStore(settings.vector_index_path)


def _opendota_loader_for_request(request: Request) -> DocumentLoader:
    settings = request.app.state.settings

    def load_documents() -> list[DocumentInput]:
        return load_opendota_knowledge_documents(
            client=OpenDotaKnowledgeClient(base_url=settings.opendota_base_url)
        )

    return load_documents


@router.post("/ingest/documents", response_model=IngestResult)
def ingest_documents(request: Request) -> IngestResult:
    store = _store_for_request(request)
    embedder = DeterministicEmbedder(dimensions=64)
    settings = request.app.state.settings
    document_loaders: list[DocumentLoader] = []

    official_documents_loader = getattr(request.app.state, "official_documents_loader", None)
    if official_documents_loader is None and settings.official_dota_sources_enabled:
        official_documents_loader = load_official_dota_documents
    if official_documents_loader is not None:
        document_loaders.append(official_documents_loader)

    opendota_knowledge_loader = getattr(
        request.app.state,
        "opendota_knowledge_documents_loader",
        None,
    )
    if opendota_knowledge_loader is None and settings.opendota_knowledge_sources_enabled:
        opendota_knowledge_loader = _opendota_loader_for_request(request)
    if opendota_knowledge_loader is not None:
        document_loaders.append(opendota_knowledge_loader)

    return ingest_seed_documents(
        store=store,
        embedder=embedder,
        document_loaders=document_loaders,
    )


@router.get("/sources", response_model=SourcesResponse)
def list_sources(request: Request) -> SourcesResponse:
    store = _store_for_request(request)
    return SourcesResponse(sources=store.list_sources())
