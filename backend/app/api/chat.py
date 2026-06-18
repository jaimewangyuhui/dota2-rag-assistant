from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

from app.rag.chat_service import ChatAnswer, ChatService
from app.rag.embeddings import DeterministicEmbedder
from app.rag.generator import OllamaChatGenerator
from app.vector_store.milvus import LocalVectorStore

router = APIRouter(prefix="/api", tags=["chat"])


class ChatRequest(BaseModel):
    message: str = Field(min_length=1)


def _generator_for_request(request: Request):
    override = getattr(request.app.state, "generator_override", None)
    if override is not None:
        return override
    settings = request.app.state.settings
    return OllamaChatGenerator(
        base_url=str(settings.ollama_base_url),
        model=settings.ollama_chat_model,
    )


@router.post("/chat", response_model=ChatAnswer)
async def chat(payload: ChatRequest, request: Request) -> ChatAnswer:
    settings = request.app.state.settings
    service = ChatService(
        store=LocalVectorStore(settings.vector_index_path),
        embedder=DeterministicEmbedder(dimensions=64),
        generator=_generator_for_request(request),
    )
    return await service.answer(payload.message)
