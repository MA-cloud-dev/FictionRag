"""Reusable RAG question-answer service functions."""

from __future__ import annotations

import json
import os
import re
from collections import Counter
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any

from .chunker import Chunk
from .config import (
    DEFAULT_INDEX_PATH,
    DEFAULT_TOP_K,
    ModelRuntimeConfigs,
    RerankerConfig,
    load_embedding_config,
    load_llm_config,
    load_reranker_config,
)
from .embeddings import EmbeddingClient
from .entity_rewriter import generate_entity_rewrites
from .index_store import load_chunks
from .llm import LLMClient
from .prompts import (
    ANSWERABILITY_SYSTEM_PROMPT,
    SYSTEM_PROMPT,
    build_answerability_prompt,
    build_clarification_prompt,
    build_user_prompt,
)
from .reranker import RerankerClient
from .retriever import (
    DEFAULT_BOOK_RESULT_CAP,
    DEFAULT_BOOK_ROUTE_COUNT,
    RetrievalResult,
    retrieve,
)


ONLINE_RERANK_CANDIDATE_TOP_N = 30
ONLINE_RERANK_VECTOR_TOP_N = 100
ONLINE_RERANK_BM25_TOP_N = 100


@dataclass(frozen=True)
class RagAnswer:
    question: str
    answer: str
    contexts: list[RetrievalResult]
    answerability: dict[str, object] | None = None
    rewritten_queries: list[str] = field(default_factory=list)
    used_rewrite: bool = False
    rerank_enabled: bool = False
    rerank_candidate_count: int = 0


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
    model_configs: ModelRuntimeConfigs | None = None,
) -> list[RetrievalResult]:
    chunks = load_chunks(index_path)
    embedding_config = model_configs.embedding if model_configs else load_embedding_config()
    reranker_config = model_configs.reranker if model_configs else None
    embedding_client = EmbeddingClient(embedding_config)
    reranker_client = _build_online_reranker(reranker_config)
    return _retrieve_with_client(question, chunks, embedding_client, top_k, reranker_client)


def answer_question(
    question: str,
    top_k: int = DEFAULT_TOP_K,
    index_path: Path = DEFAULT_INDEX_PATH,
    model_configs: ModelRuntimeConfigs | None = None,
) -> RagAnswer:
    chunks = load_chunks(index_path)
    embedding_config = model_configs.embedding if model_configs else load_embedding_config()
    llm_config = model_configs.llm if model_configs else load_llm_config()
    reranker_config = model_configs.reranker if model_configs else None
    embedding_client = EmbeddingClient(embedding_config)
    llm_client = LLMClient(llm_config)
    reranker_client = _build_online_reranker(reranker_config)

    contexts = _retrieve_with_client(question, chunks, embedding_client, top_k, reranker_client)
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
            rerank_enabled=reranker_client is not None,
            rerank_candidate_count=_rerank_candidate_target(reranker_client),
        )

    if _is_answerable(first_answerability):
        answer = llm_client.answer(build_user_prompt(question, contexts))
        rewrite_queries = generate_entity_rewrites(question)
        if _should_retry_with_rewrite(answer) and rewrite_queries:
            return _answer_with_rewrite(
                question=question,
                first_contexts=contexts,
                rewrite_queries=rewrite_queries,
                chunks=chunks,
                embedding_client=embedding_client,
                llm_client=llm_client,
                reranker_client=reranker_client,
                top_k=top_k,
                first_answerability=first_answerability,
            )
        return RagAnswer(
            question=question,
            answer=answer,
            contexts=contexts,
            answerability=first_answerability,
            rewritten_queries=[],
            used_rewrite=False,
            rerank_enabled=reranker_client is not None,
            rerank_candidate_count=_rerank_candidate_target(reranker_client),
        )

    rewrite_queries = generate_entity_rewrites(question)
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
            rerank_enabled=reranker_client is not None,
            rerank_candidate_count=_rerank_candidate_target(reranker_client),
        )

    return _answer_with_rewrite(
        question=question,
        first_contexts=contexts,
        rewrite_queries=rewrite_queries,
        chunks=chunks,
        embedding_client=embedding_client,
        llm_client=llm_client,
        reranker_client=reranker_client,
        top_k=top_k,
        first_answerability=first_answerability,
    )


def _answer_with_rewrite(
    question: str,
    first_contexts: list[RetrievalResult],
    rewrite_queries: list[str],
    chunks: list[Chunk],
    embedding_client: EmbeddingClient,
    llm_client: LLMClient,
    reranker_client: RerankerClient | None,
    top_k: int,
    first_answerability: dict[str, object],
) -> RagAnswer:
    rewrite_result_sets = [
        _retrieve_with_client(rewrite_query, chunks, embedding_client, top_k, reranker_client)
        for rewrite_query in rewrite_queries
    ]
    merged_contexts = _merge_contexts([first_contexts, *rewrite_result_sets], top_k=top_k)
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
            rerank_enabled=reranker_client is not None,
            rerank_candidate_count=_rerank_candidate_target(reranker_client),
        )

    if _is_answerable(second_answerability):
        answer = llm_client.answer(build_user_prompt(question, merged_contexts))
        if _should_retry_with_rewrite(answer):
            answer = llm_client.chat(
                SYSTEM_PROMPT,
                build_clarification_prompt(question, merged_contexts, second_answerability),
                temperature=0,
            )
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
        rerank_enabled=reranker_client is not None,
        rerank_candidate_count=_rerank_candidate_target(reranker_client),
    )


def _retrieve_with_client(
    query: str,
    chunks: list[Chunk],
    embedding_client: EmbeddingClient,
    top_k: int,
    reranker_client: RerankerClient | None = None,
) -> list[RetrievalResult]:
    query_embedding = embedding_client.embed_text(query)
    if reranker_client is None:
        return retrieve(query_embedding, chunks, top_k=top_k, query_text=query)

    candidates = retrieve(
        query_embedding,
        chunks,
        top_k=max(top_k, ONLINE_RERANK_CANDIDATE_TOP_N),
        vector_top_n=ONLINE_RERANK_VECTOR_TOP_N,
        bm25_top_n=ONLINE_RERANK_BM25_TOP_N,
        query_text=query,
        book_route_count=DEFAULT_BOOK_ROUTE_COUNT,
        book_result_cap=ONLINE_RERANK_CANDIDATE_TOP_N,
    )
    return _rerank_and_select(
        query=query,
        candidates=candidates,
        reranker_client=reranker_client,
        top_k=top_k,
        book_result_cap=DEFAULT_BOOK_RESULT_CAP,
    )


def _build_online_reranker(reranker_config: RerankerConfig | None = None) -> RerankerClient | None:
    if not _online_rerank_enabled():
        return None
    return RerankerClient(reranker_config or load_reranker_config())


def _online_rerank_enabled() -> bool:
    value = os.getenv("FICTIONRAG_ENABLE_RERANK", "true").strip().lower()
    return value not in {"0", "false", "no", "off"}


def _rerank_and_select(
    query: str,
    candidates: list[RetrievalResult],
    reranker_client: RerankerClient,
    top_k: int,
    book_result_cap: int,
) -> list[RetrievalResult]:
    if not candidates:
        return []

    scores = reranker_client.score(query, [candidate.text for candidate in candidates])
    reranked = [
        RetrievalResult(
            chunk_id=candidate.chunk_id,
            score=score,
            text=candidate.text,
            chunk=candidate.chunk,
        )
        for candidate, score in zip(candidates, scores)
    ]
    reranked.sort(key=lambda result: result.score, reverse=True)
    return _apply_book_result_cap(reranked, top_k=top_k, book_result_cap=book_result_cap)


def _apply_book_result_cap(
    results: list[RetrievalResult],
    top_k: int,
    book_result_cap: int,
) -> list[RetrievalResult]:
    selected: list[RetrievalResult] = []
    seen_ids: set[str] = set()
    count_by_book: Counter[str] = Counter()
    for result in results:
        if result.chunk_id in seen_ids:
            continue
        if count_by_book[result.chunk.book_name] >= book_result_cap:
            continue
        selected.append(result)
        seen_ids.add(result.chunk_id)
        count_by_book[result.chunk.book_name] += 1
        if len(selected) == top_k:
            return selected

    for result in results:
        if result.chunk_id in seen_ids:
            continue
        selected.append(result)
        seen_ids.add(result.chunk_id)
        if len(selected) == top_k:
            break
    return selected


def _rerank_candidate_target(reranker_client: RerankerClient | None) -> int:
    if reranker_client is None:
        return 0
    return ONLINE_RERANK_CANDIDATE_TOP_N


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
    return {
        "answerable": answerable,
        "missing_info": _string_list(raw.get("missing_info"), limit=5),
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


def _should_retry_with_rewrite(answer: str) -> bool:
    stripped = answer.strip()
    if not stripped:
        return True
    insufficient_markers = (
        "没有足够信息",
        "没有足够的信息",
        "信息不足",
        "无法确认",
        "无法回答",
        "原文未提供",
        "原文中未提供",
        "不能确定",
    )
    return any(marker in stripped for marker in insufficient_markers)


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
