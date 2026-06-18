from typing import Optional, Protocol

import httpx


class Generator(Protocol):
    async def generate(self, prompt: str) -> str:
        ...


class FakeGenerator:
    def __init__(self, answer: str) -> None:
        self.answer = answer

    async def generate(self, prompt: str) -> str:
        return self.answer


class OllamaChatGenerator:
    def __init__(
        self,
        base_url: str,
        model: str = "qwen2.5:7b",
        transport: Optional[httpx.AsyncBaseTransport] = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.transport = transport

    async def generate(self, prompt: str) -> str:
        async with httpx.AsyncClient(
            base_url=self.base_url,
            timeout=60.0,
            transport=self.transport,
        ) as client:
            response = await client.post(
                "/api/chat",
                json={
                    "model": self.model,
                    "messages": [{"role": "user", "content": prompt}],
                    "stream": False,
                },
            )
            response.raise_for_status()
            payload = response.json()
        return str(payload["message"]["content"]).strip()
