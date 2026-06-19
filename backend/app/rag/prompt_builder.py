from app.rag.schemas import RetrievedChunk


def _format_chunk(index: int, retrieved: RetrievedChunk) -> str:
    metadata = retrieved.chunk.metadata
    return (
        f"[{index}] {metadata.source_name} | {metadata.source_url} | "
        f"entity={metadata.entity_name} | patch={metadata.patch_version or 'unknown'} | "
        f"updated_at={metadata.updated_at} | score={retrieved.score:.3f}\n"
        f"{retrieved.chunk.text}"
    )


def build_prompt(
    question: str,
    question_type: str,
    retrieved_chunks: list[RetrievedChunk],
    canonical_terms: list[str] | None = None,
) -> str:
    context = "\n\n".join(
        _format_chunk(index, chunk)
        for index, chunk in enumerate(retrieved_chunks, start=1)
    )
    term_hint = ""
    if canonical_terms:
        term_hint = f"\nCanonical terms detected: {', '.join(canonical_terms)}\n"

    advice_rule = ""
    if question_type == "advice":
        advice_rule = "\n- 不要使用 must buy、always pick 这类绝对说法；建议必须写成视局势而定。"

    return f"""你是一个 Dota 2 RAG 助手。请用中文回答，并保留关键英文 Dota 2 术语，例如 Black King Bar / BKB、Roshan、Blink Dagger。

问题类型: {question_type}{term_hint}

回答结构必须包含:
- 直接结论 (Direct conclusion)
- 关键原因 (Key reasons)
- 建议/注意 (Recommended actions or cautions)
- 相关术语 (Relevant English terms)
- 来源/数据新鲜度 (Sources and data freshness)

规则:
- 只使用给定 context 支持的内容。
- 如果 context 不足，明确说“当前知识库没有覆盖这个问题”，不要猜测。
- 保留 source_name、source_url、updated_at 相关信息。{advice_rule}

context:
{context}

user question:
{question}
"""
