from pydantic import BaseModel

from app.rag.schemas import RetrievedChunk, TextChunk


class VectorRecord(BaseModel):
    chunk: TextChunk
    vector: list[float]


class VectorSearchResult(RetrievedChunk):
    pass
