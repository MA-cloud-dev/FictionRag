"""Prompt templates for grounded fiction QA."""

from __future__ import annotations

from .retriever import RetrievalResult


SYSTEM_PROMPT = (
    "你是一个小说问答助手。你只能根据用户提供的小说原文片段回答问题。"
    "不要使用常识、猜测或其他作品的信息补充答案。"
    "如果片段中没有足够信息回答，不要直接结束；请先说明原文信息不足，"
    "再根据用户问题和已召回片段，提示用户补充更明确的人物、地点、时间、事件或指代信息。"
)

ANSWERABILITY_SYSTEM_PROMPT = (
    "你是小说 RAG 系统的可回答性判断器。你只能根据用户问题和给定小说原文片段判断是否足够回答。"
    "不要回答用户问题，不要补充常识，不要猜测原文之外的信息。"
    "你必须只输出严格 JSON 对象，不要输出 Markdown 或解释。"
)


def build_context(results: list[RetrievalResult]) -> str:
    sections: list[str] = []
    for index, result in enumerate(results, start=1):
        sections.append(
            f"[片段 {index} | book={result.chunk.book_name} | "
            f"chunk_id={result.chunk_id} | score={result.score:.4f}]\n"
            f"{result.text}"
        )
    return "\n\n".join(sections)


def build_user_prompt(question: str, results: list[RetrievalResult]) -> str:
    context = build_context(results)
    return f"""你只能根据下面提供的小说原文片段回答问题。

要求：
1. 只能使用“小说原文片段”中的信息。
2. 不要使用常识、猜测或其他作品的信息补充答案。
3. 如果原文片段中没有足够信息回答，不要编造答案，也不要只回答“原文中没有足够信息确认。”
   请按下面格式给出澄清建议：
   - 先说明：目前原文片段中没有足够信息确认答案。
   - 再指出问题可能缺少哪些关键信息，例如人物、地点、时间、事件、章节范围或“他/她/这里/后来”等指代对象。
   - 如果召回片段中出现了可用于澄清的候选人物、地点、时间或事件，可以列出 2 到 4 个候选项，请用户确认。
   - 最后给出 1 到 2 个更容易召回的改写问题示例。
4. 如果多个片段来自不同书籍，不要把不同书籍的剧情、人物、设定混合成一个事实。
5. 回答应简洁，并尽量指出依据来自哪些片段编号。

小说原文片段：
{context}

用户问题：
{question}

请给出回答："""


def build_answerability_prompt(question: str, results: list[RetrievalResult]) -> str:
    context = build_context(results)
    return f"""请判断下面的小说原文片段是否足够回答用户问题。

判断要求：
1. 只根据“小说原文片段”判断，不使用常识、猜测或其他作品信息。
2. 只做两类判断：如果片段足够直接回答问题，answerable=true；否则 answerable=false。
3. answerable=true 时，rewrite_queries 必须为空数组。
4. answerable=false 时，必须生成 1 到 3 条 rewrite_queries，用于重新检索。
5. rewrite_queries 只用于检索，不用于回答；必须保留用户原问题意图，不要编造片段中没有的事实。
6. rewrite_queries 应优先把不顺、口语、倒装或抽象的问题，改写成更贴近小说原文表达的检索问题。
7. 如果问题中有明确实体、事件、地点或时间，要尽量保留这些信息；如果有同义表达，可以改成更可能出现在原文中的说法。
8. missing_info 用于记录当前片段为什么不能直接回答，最多 5 条。
9. clarification_questions 是最终仍无法回答时给用户的简短追问，最多 3 条。
10. 只输出一个 JSON 对象，不要使用 Markdown 代码块。

JSON 格式：
{{
  "answerable": false,
  "missing_info": ["缺少的信息"],
  "rewrite_queries": ["改写后的检索问题"],
  "clarification_questions": ["需要用户确认的问题"]
}}

小说原文片段：
{context}

用户问题：
{question}

请输出 JSON："""


def build_clarification_prompt(
    question: str,
    results: list[RetrievalResult],
    answerability: dict[str, object] | None,
) -> str:
    context = build_context(results)
    details = answerability or {}
    return f"""当前系统已经判断给定小说原文片段不足以可靠回答用户问题。

请你不要编造答案，也不要把不同书籍的剧情、人物、设定混合成一个事实。
请基于用户问题、判断结果和小说原文片段，给出对用户有帮助的澄清建议。

输出要求：
1. 先说明：目前原文片段中没有足够信息确认答案。
2. 简要说明缺少哪些信息。
3. 如果片段中出现可用于澄清的候选人物、地点、时间或事件，列出 2 到 4 个候选项让用户确认。
4. 给出 1 到 2 个更容易召回的改写问题示例。
5. 不要声称已经知道答案。

判断结果：
{details}

小说原文片段：
{context}

用户问题：
{question}

请给出澄清建议："""
