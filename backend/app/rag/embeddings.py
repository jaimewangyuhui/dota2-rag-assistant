import hashlib
import math
import re
from typing import Optional, Protocol

import httpx


TOKEN_PATTERN = re.compile(r"[a-zA-Z0-9]+")


class Embedder(Protocol):
    def embed(self, text: str) -> list[float]:
        ...


class AsyncEmbedder(Protocol):
    async def aembed(self, text: str) -> list[float]:
        ...


def cosine_similarity(left: list[float], right: list[float]) -> float:
    dot = sum(a * b for a, b in zip(left, right))
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return dot / (left_norm * right_norm)


class DeterministicEmbedder:
    def __init__(self, dimensions: int = 64) -> None:
        self.dimensions = dimensions

    def embed(self, text: str) -> list[float]:
        vector = [0.0] * self.dimensions
        tokens = TOKEN_PATTERN.findall(text.lower())
        for token in tokens:
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            index = int.from_bytes(digest[:4], "big") % self.dimensions
            vector[index] += 1.0
        norm = math.sqrt(sum(value * value for value in vector))
        if norm == 0:
            return vector
        return [value / norm for value in vector]


class OllamaEmbedder:
    def __init__(
        self,
        base_url: str,
        model: str = "nomic-embed-text",
        transport: Optional[httpx.AsyncBaseTransport] = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.transport = transport

    async def aembed(self, text: str) -> list[float]:
        async with httpx.AsyncClient(
            base_url=self.base_url,
            timeout=30.0,
            transport=self.transport,
        ) as client:
            response = await client.post(
                "/api/embeddings",
                json={"model": self.model, "prompt": text},
            )
            response.raise_for_status()
            payload = response.json()
        return [float(value) for value in payload["embedding"]]
