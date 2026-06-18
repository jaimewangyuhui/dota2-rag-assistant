import httpx
import pytest

from app.rag.generator import FakeGenerator, OllamaChatGenerator


@pytest.mark.asyncio
async def test_fake_generator_returns_configured_answer() -> None:
    generator = FakeGenerator("BKB 可以提供短时间 spell immunity。")

    assert await generator.generate("prompt") == "BKB 可以提供短时间 spell immunity。"


@pytest.mark.asyncio
async def test_ollama_chat_generator_reads_message_content() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/chat"
        payload = request.read().decode("utf-8")
        assert "dota2-rag" in payload
        return httpx.Response(200, json={"message": {"content": "Roshan 会掉 Aegis。"}})

    generator = OllamaChatGenerator(
        base_url="http://ollama.test",
        model="dota2-rag",
        transport=httpx.MockTransport(handler),
    )

    assert await generator.generate("prompt") == "Roshan 会掉 Aegis。"
