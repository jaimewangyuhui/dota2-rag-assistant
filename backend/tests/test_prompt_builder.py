from app.rag.prompt_builder import build_prompt
from app.rag.schemas import RetrievedChunk, SourceMetadata, TextChunk


def make_retrieved_chunk() -> RetrievedChunk:
    return RetrievedChunk(
        chunk=TextChunk(
            chunk_id="seed://items/black-king-bar#chunk-0",
            text="Black King Bar, often called BKB, grants timed spell immunity.",
            metadata=SourceMetadata(
                source_url="seed://items/black-king-bar",
                source_name="Seed: Black King Bar",
                patch_version="7.36",
                entity_type="item",
                entity_name="Black King Bar",
                updated_at="2026-06-18",
            ),
        ),
        score=0.9,
    )


def test_prompt_contains_answer_rules_and_context() -> None:
    prompt = build_prompt(
        question="BKB 有什么用?",
        question_type="knowledge",
        retrieved_chunks=[make_retrieved_chunk()],
    )

    assert "请用中文回答" in prompt
    assert "保留关键英文 Dota 2 术语" in prompt
    assert "Direct conclusion" in prompt
    assert "直接结论" in prompt
    assert "关键原因" in prompt
    assert "建议/注意" in prompt
    assert "相关术语" in prompt
    assert "来源/数据新鲜度" in prompt
    assert "Black King Bar" in prompt
    assert "seed://items/black-king-bar" in prompt


def test_prompt_includes_canonical_term_hints() -> None:
    prompt = build_prompt(
        question="黑皇杖有什么用？",
        question_type="knowledge",
        retrieved_chunks=[make_retrieved_chunk()],
        canonical_terms=["Black King Bar / BKB"],
    )

    assert "Canonical terms detected: Black King Bar / BKB" in prompt


def test_prompt_warns_when_question_is_advice() -> None:
    prompt = build_prompt(
        question="我应该出 BKB 吗?",
        question_type="advice",
        retrieved_chunks=[make_retrieved_chunk()],
    )

    assert "不要使用 must buy、always pick 这类绝对说法" in prompt
