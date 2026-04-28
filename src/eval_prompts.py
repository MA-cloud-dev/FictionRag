"""Prompts used to generate retrieval evaluation questions."""

from __future__ import annotations


EVAL_QUESTION_SYSTEM_PROMPT = (
    "你是 RAG 检索评测数据生成器。你必须只基于给定原文片段生成问题和参考答案，"
    "并且只输出严格 JSON，不要输出 Markdown 或解释。"
)


def build_question_generation_prompt(chunk_id: str, chunk_text: str) -> str:
    return f"""请基于下面这个小说原文片段，生成 1 个适合测试检索系统的问题。

要求：
1. 问题必须能仅凭该片段回答。
2. 问题应询问具体事实、人物、地点、事件、原因或关系。
3. 不要生成需要跨片段、多跳推理或开放式赏析的问题。
4. 参考答案必须简洁，并且只使用该片段的信息。
5. 只输出一个 JSON 对象，不要使用 Markdown 代码块。

JSON 格式：
{{
  "question": "问题文本",
  "reference_answer": "参考答案"
}}

chunk_id:
{chunk_id}

小说原文片段：
{chunk_text}
"""
