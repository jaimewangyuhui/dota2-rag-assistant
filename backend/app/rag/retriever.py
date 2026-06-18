from app.rag.embeddings import Embedder
from app.rag.schemas import RetrievedChunk
from app.vector_store.milvus import LocalVectorStore


class Retriever:
    def __init__(self, store: LocalVectorStore, embedder: Embedder) -> None:
        self.store = store
        self.embedder = embedder

    def retrieve(self, query: str, limit: int = 5) -> list[RetrievedChunk]:
        return self.store.search(self.embedder.embed(query), limit=limit)
