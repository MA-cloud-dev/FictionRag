"""Reusable RAG question-answer service functions."""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from .config import DEFAULT_INDEX_PATH, DEFAULT_TOP_K, load_embedding_config, load_llm_config
from .embeddings import EmbeddingClient
from .index_store import load_chunks
from .llm import LLMClient
from .prompts import build_user_prompt
from .retriever import RetrievalResult, retrieve


@dataclass(frozen=True)
class RagAnswer:
    question: str
    answer: str
    contexts: list[RetrievalResult]


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
    question_embedding = embedding_client.embed_text(question)
    return retrieve(question_embedding, chunks, top_k=top_k, query_text=question)


def answer_question(
    question: str,
    top_k: int = DEFAULT_TOP_K,
    index_path: Path = DEFAULT_INDEX_PATH,
) -> RagAnswer:
    contexts = retrieve_contexts(
        question=question,
        top_k=top_k,
        index_path=index_path,
    )
    user_prompt = build_user_prompt(question, contexts)
    llm_client = LLMClient(load_llm_config())
    answer = llm_client.answer(user_prompt)
    return RagAnswer(question=question, answer=answer, contexts=contexts)
