from pydantic import BaseModel

from app.rag.classifier import classify_question
from app.rag.embeddings import Embedder
from app.rag.generator import Generator
from app.rag.prompt_builder import build_prompt
from app.rag.schemas import RetrievedChunk
from app.vector_store.milvus import LocalVectorStore


UNCERTAINTY_ANSWER = "当前知识库没有覆盖这个问题，无法基于已索引来源可靠回答。"


class SourceCitation(BaseModel):
    source_name: str
    source_url: str
    entity_name: str
    entity_type: str
    patch_version: str | None
    updated_at: str
    score: float


class ChatDebug(BaseModel):
    retrieved_chunks: int
    top_score: float | None


class ChatAnswer(BaseModel):
    answer: str
    question_type: str
    sources: list[SourceCitation]
    debug: ChatDebug


def _sources_from_chunks(chunks: list[RetrievedChunk]) -> list[SourceCitation]:
    citations: list[SourceCitation] = []
    seen: set[str] = set()
    for retrieved in chunks:
        metadata = retrieved.chunk.metadata
        key = metadata.source_url
        if key in seen:
            continue
        seen.add(key)
        citations.append(
            SourceCitation(
                source_name=metadata.source_name,
                source_url=metadata.source_url,
                entity_name=metadata.entity_name,
                entity_type=metadata.entity_type,
                patch_version=metadata.patch_version,
                updated_at=metadata.updated_at,
                score=retrieved.score,
            )
        )
    return citations


class ChatService:
    def __init__(
        self,
        store: LocalVectorStore,
        embedder: Embedder,
        generator: Generator,
        retrieval_limit: int = 4,
        minimum_score: float = 0.05,
    ) -> None:
        self.store = store
        self.embedder = embedder
        self.generator = generator
        self.retrieval_limit = retrieval_limit
        self.minimum_score = minimum_score

    async def answer(self, question: str) -> ChatAnswer:
        question_type = classify_question(question)
        retrieved = self.store.search(self.embedder.embed(question), limit=self.retrieval_limit)
        supported = [item for item in retrieved if item.score >= self.minimum_score]
        top_score = supported[0].score if supported else None
        debug = ChatDebug(retrieved_chunks=len(supported), top_score=top_score)

        if not supported:
            return ChatAnswer(
                answer=UNCERTAINTY_ANSWER,
                question_type=question_type,
                sources=[],
                debug=debug,
            )

        prompt = build_prompt(
            question=question,
            question_type=question_type,
            retrieved_chunks=supported,
        )
        answer = await self.generator.generate(prompt)
        return ChatAnswer(
            answer=answer,
            question_type=question_type,
            sources=_sources_from_chunks(supported),
            debug=debug,
        )
