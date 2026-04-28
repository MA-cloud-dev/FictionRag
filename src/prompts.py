"""Prompt templates for grounded fiction QA."""

from __future__ import annotations

from .retriever import RetrievalResult


SYSTEM_PROMPT = (
    "你是一个小说问答助手。你只能根据用户提供的小说原文片段回答问题。"
    "不要使用常识、猜测或其他作品的信息补充答案。"
    "如果片段中没有足够信息回答，请明确回答：原文中没有足够信息确认。"
)


def build_context(results: list[RetrievalResult]) -> str:
    sections: list[str] = []
    for index, result in enumerate(results, start=1):
        sections.append(
            f"[片段 {index} | chunk_id={result.chunk_id} | score={result.score:.4f}]\n"
            f"{result.text}"
        )
    return "\n\n".join(sections)


def build_user_prompt(question: str, results: list[RetrievalResult]) -> str:
    context = build_context(results)
    return f"""你只能根据下面提供的小说原文片段回答问题。

要求：
1. 只能使用“小说原文片段”中的信息。
2. 不要使用常识、猜测或其他作品的信息补充答案。
3. 如果原文片段中没有足够信息回答，请明确回答：“原文中没有足够信息确认。”
4. 回答应简洁，并尽量指出依据来自哪些片段编号。

小说原文片段：
{context}

用户问题：
{question}

请给出回答："""
