"""Reusable RAG question-answer service functions."""

from __future__ import annotations

import json
import re
from collections import Counter
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any

from .chunker import Chunk
from .config import DEFAULT_INDEX_PATH, DEFAULT_TOP_K, load_embedding_config, load_llm_config
from .embeddings import EmbeddingClient
from .index_store import load_chunks
from .llm import LLMClient
from .prompts import (
    ANSWERABILITY_SYSTEM_PROMPT,
    SYSTEM_PROMPT,
    build_answerability_prompt,
    build_clarification_prompt,
    build_user_prompt,
)
from .retriever import RetrievalResult, retrieve


MAX_REWRITE_QUERIES = 3


@dataclass(frozen=True)
class RagAnswer:
    question: str
    answer: str
    contexts: list[RetrievalResult]
    answerability: dict[str, object] | None = None
    rewritten_queries: list[str] = field(default_factory=list)
    used_rewrite: bool = False


def list_book_stats(index_path: Path = DEFAULT_INDEX_PATH) -> dict[str, object]:
    if not index_path.exists():
        raise FileNotFoundError(f"Index file does not exist: {index_path}")
    stats = _list_book_stats_cached(str(index_path), index_path.stat().st_mtime)
    return {
        "index_path": str(index_path),
        "total_books": len(stats),
        "total_chunks": sum(book["chunk_count"] for book in stats),
        "books": stats,
    }


@lru_cache(maxsize=4)
def _list_book_stats_cached(index_path: str, mtime: float) -> tuple[dict[str, object], ...]:
    del mtime
    counts: Counter[str] = Counter()
    with Path(index_path).open("r", encoding="utf-8") as file:
        for line in file:
            stripped = line.strip()
            if not stripped:
                continue
            raw = json.loads(stripped)
            counts[str(raw.get("book_name") or "未知书籍")] += 1
    return tuple(
        {"book_name": book_name, "chunk_count": chunk_count}
        for book_name, chunk_count in counts.items()
    )


def retrieve_contexts(
    question: str,
    top_k: int = DEFAULT_TOP_K,
    index_path: Path = DEFAULT_INDEX_PATH,
) -> list[RetrievalResult]:
    chunks = load_chunks(index_path)
    embedding_client = EmbeddingClient(load_embedding_config())
    return _retrieve_with_client(question, chunks, embedding_client, top_k)


def answer_question(
    question: str,
    top_k: int = DEFAULT_TOP_K,
    index_path: Path = DEFAULT_INDEX_PATH,
) -> RagAnswer:
    chunks = load_chunks(index_path)
    embedding_client = EmbeddingClient(load_embedding_config())
    llm_client = LLMClient(load_llm_config())

    contexts = _retrieve_with_client(question, chunks, embedding_client, top_k)
    first_answerability = _judge_answerability(llm_client, question, contexts)
    if first_answerability is None:
        answer = llm_client.answer(build_user_prompt(question, contexts))
        return RagAnswer(
            question=question,
            answer=answer,
            contexts=contexts,
            answerability=None,
            rewritten_queries=[],
            used_rewrite=False,
        )

    if _is_answerable(first_answerability):
        answer = llm_client.answer(build_user_prompt(question, contexts))
        return RagAnswer(
            question=question,
            answer=answer,
            contexts=contexts,
            answerability=first_answerability,
            rewritten_queries=[],
            used_rewrite=False,
        )

    rewrite_queries = _rewrite_queries(first_answerability)
    if not rewrite_queries:
        answer = llm_client.chat(
            SYSTEM_PROMPT,
            build_clarification_prompt(question, contexts, first_answerability),
            temperature=0,
        )
        return RagAnswer(
            question=question,
            answer=answer,
            contexts=contexts,
            answerability=first_answerability,
            rewritten_queries=rewrite_queries,
            used_rewrite=False,
        )

    rewrite_result_sets = [
        _retrieve_with_client(rewrite_query, chunks, embedding_client, top_k)
        for rewrite_query in rewrite_queries
    ]
    merged_contexts = _merge_contexts([contexts, *rewrite_result_sets], top_k=top_k)
    second_answerability = _judge_answerability(llm_client, question, merged_contexts)
    if second_answerability is None:
        answer = llm_client.chat(
            SYSTEM_PROMPT,
            build_clarification_prompt(question, merged_contexts, first_answerability),
            temperature=0,
        )
        return RagAnswer(
            question=question,
            answer=answer,
            contexts=merged_contexts,
            answerability=None,
            rewritten_queries=rewrite_queries,
            used_rewrite=True,
        )

    if _is_answerable(second_answerability):
        answer = llm_client.answer(build_user_prompt(question, merged_contexts))
    else:
        answer = llm_client.chat(
            SYSTEM_PROMPT,
            build_clarification_prompt(question, merged_contexts, second_answerability),
            temperature=0,
        )

    return RagAnswer(
        question=question,
        answer=answer,
        contexts=merged_contexts,
        answerability=second_answerability,
        rewritten_queries=rewrite_queries,
        used_rewrite=True,
    )


def _retrieve_with_client(
    query: str,
    chunks: list[Chunk],
    embedding_client: EmbeddingClient,
    top_k: int,
) -> list[RetrievalResult]:
    query_embedding = embedding_client.embed_text(query)
    return retrieve(query_embedding, chunks, top_k=top_k, query_text=query)


def _judge_answerability(
    llm_client: LLMClient,
    question: str,
    contexts: list[RetrievalResult],
) -> dict[str, object] | None:
    prompt = build_answerability_prompt(question, contexts)
    content = llm_client.chat(ANSWERABILITY_SYSTEM_PROMPT, prompt, temperature=0)
    try:
        parsed = _parse_json_object(content)
    except (json.JSONDecodeError, ValueError):
        return None
    return _normalize_answerability(parsed)


def _parse_json_object(content: str) -> dict[str, Any]:
    cleaned = content.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)

    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
        if not match:
            raise
        parsed = json.loads(match.group(0))

    if not isinstance(parsed, dict):
        raise ValueError("Generated content must be a JSON object")
    return parsed


def _normalize_answerability(raw: dict[str, Any]) -> dict[str, object]:
    answerable = _as_bool(raw.get("answerable"))
    rewrite_queries = _string_list(raw.get("rewrite_queries"), limit=MAX_REWRITE_QUERIES)
    if answerable:
        rewrite_queries = []

    return {
        "answerable": answerable,
        "missing_info": _string_list(raw.get("missing_info"), limit=5),
        "rewrite_queries": rewrite_queries,
        "clarification_questions": _string_list(raw.get("clarification_questions"), limit=3),
    }


def _as_bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() == "true"
    return False


def _string_list(value: object, limit: int) -> list[str]:
    if not isinstance(value, list):
        return []
    items: list[str] = []
    seen: set[str] = set()
    for item in value:
        text = str(item).strip()
        if not text or text in seen:
            continue
        items.append(text)
        seen.add(text)
        if len(items) >= limit:
            break
    return items


def _is_answerable(answerability: dict[str, object]) -> bool:
    return bool(answerability.get("answerable"))


def _rewrite_queries(answerability: dict[str, object]) -> list[str]:
    value = answerability.get("rewrite_queries")
    if not isinstance(value, list):
        return []
    return _string_list(value, limit=MAX_REWRITE_QUERIES)


def _merge_contexts(
    result_sets: list[list[RetrievalResult]],
    top_k: int,
) -> list[RetrievalResult]:
    best_by_chunk_id: dict[str, RetrievalResult] = {}
    hit_counts: Counter[str] = Counter()
    first_seen: dict[str, int] = {}
    order = 0
    for results in result_sets:
        seen_in_set: set[str] = set()
        for result in results:
            if result.chunk_id not in first_seen:
                first_seen[result.chunk_id] = order
                order += 1
            if result.chunk_id not in seen_in_set:
                hit_counts[result.chunk_id] += 1
                seen_in_set.add(result.chunk_id)
            current = best_by_chunk_id.get(result.chunk_id)
            if current is None or result.score > current.score:
                best_by_chunk_id[result.chunk_id] = result

    merged = list(best_by_chunk_id.values())
    merged.sort(
        key=lambda item: (
            -hit_counts[item.chunk_id],
            -item.score,
            first_seen[item.chunk_id],
        )
    )
    return merged[:top_k]
