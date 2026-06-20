import json

import httpx
import pytest

from app.rag.generator import OllamaChatGenerator


@pytest.mark.asyncio
async def test_ollama_chat_generator_limits_response_length() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.read())
        assert payload["options"]["num_predict"] == 180
        return httpx.Response(200, json={"message": {"content": "short answer"}})

    generator = OllamaChatGenerator(
        base_url="http://ollama.test",
        transport=httpx.MockTransport(handler),
    )

    assert await generator.generate("prompt") == "short answer"
