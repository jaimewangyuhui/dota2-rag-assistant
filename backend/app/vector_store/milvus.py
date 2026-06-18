import json
from pathlib import Path

from app.db.session import ServiceStatus
from app.rag.embeddings import cosine_similarity
from app.rag.schemas import TextChunk
from app.vector_store.schemas import VectorRecord, VectorSearchResult


def check_vector_store(vector_data_path: Path) -> ServiceStatus:
    try:
        vector_data_path.mkdir(parents=True, exist_ok=True)
        return ServiceStatus(
            name="milvus",
            ok=True,
            detail="local vector directory ready",
        )
    except Exception as exc:
        return ServiceStatus(name="milvus", ok=False, detail=str(exc))


class LocalVectorStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.records = self._load()

    def _load(self) -> dict[str, VectorRecord]:
        if not self.path.exists():
            return {}
        payload = json.loads(self.path.read_text(encoding="utf-8"))
        return {item["chunk"]["chunk_id"]: VectorRecord.model_validate(item) for item in payload}

    def _save(self) -> None:
        payload = [record.model_dump(mode="json") for record in self.records.values()]
        self.path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def upsert(self, entries: list[tuple[TextChunk, list[float]]]) -> None:
        for chunk, vector in entries:
            self.records[chunk.chunk_id] = VectorRecord(chunk=chunk, vector=vector)
        self._save()

    def search(self, query_vector: list[float], limit: int = 5) -> list[VectorSearchResult]:
        scored = [
            VectorSearchResult(
                chunk=record.chunk,
                score=cosine_similarity(query_vector, record.vector),
            )
            for record in self.records.values()
        ]
        scored.sort(key=lambda result: result.score, reverse=True)
        return scored[:limit]

    def list_sources(self) -> list[str]:
        return sorted({record.chunk.metadata.source_name for record in self.records.values()})

    def clear(self) -> None:
        self.records = {}
        self._save()
