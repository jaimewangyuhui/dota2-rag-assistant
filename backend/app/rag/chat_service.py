from pydantic import BaseModel

from app.db.repositories import HeroStatsRepository, HeroStatsRow
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
    stats_used: bool = False


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
        stats_repository: HeroStatsRepository | None = None,
    ) -> None:
        self.store = store
        self.embedder = embedder
        self.generator = generator
        self.retrieval_limit = retrieval_limit
        self.minimum_score = minimum_score
        self.stats_repository = stats_repository

    async def answer(self, question: str) -> ChatAnswer:
        question_type = classify_question(question)
        if question_type == "stats" and self.stats_repository is not None:
            stats_answer = self._answer_stats_question(question)
            if stats_answer is not None:
                return stats_answer

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

    def _answer_stats_question(self, question: str) -> ChatAnswer | None:
        if self.stats_repository is None:
            return None

        hero = self.stats_repository.find_hero(question)
        if hero is not None:
            return ChatAnswer(
                answer=_format_hero_stats_answer(hero),
                question_type="stats",
                sources=[],
                debug=ChatDebug(retrieved_chunks=0, top_score=None, stats_used=True),
            )

        top = self.stats_repository.top_heroes(limit=3)
        if top:
            names = ", ".join(
                f"{row.localized_name} ({row.public_pick_share * 100:.1f}% pick share)"
                for row in top
            )
            return ChatAnswer(
                answer=(
                    "当前本地 OpenDota 公共比赛样本里，选取占比较高的英雄包括："
                    f"{names}。数据刷新时间：{top[0].refreshed_at}。"
                    "这些是样本统计，不代表实时全局 Meta。"
                ),
                question_type="stats",
                sources=[],
                debug=ChatDebug(retrieved_chunks=0, top_score=None, stats_used=True),
            )

        return ChatAnswer(
            answer="当前本地还没有英雄统计数据。请先调用 POST /api/refresh/stats 刷新 OpenDota 数据。",
            question_type="stats",
            sources=[],
            debug=ChatDebug(retrieved_chunks=0, top_score=None, stats_used=False),
        )


def _format_hero_stats_answer(hero: HeroStatsRow) -> str:
    return (
        f"{hero.localized_name} 在当前本地 OpenDota 公共比赛样本中："
        f"胜率约 {hero.public_win_rate * 100:.1f}%，"
        f"选取占比约 {hero.public_pick_share * 100:.1f}%，"
        f"样本数 {hero.public_pick_count:,} 场。"
        f"数据刷新时间：{hero.refreshed_at}。"
        "这些统计来自 OpenDota 公共比赛样本，不代表实时全局 Meta，也不应单独决定选人。"
    )
