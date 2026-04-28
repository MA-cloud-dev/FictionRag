"""Brute-force cosine similarity retrieval."""

from __future__ import annotations

import math
from dataclasses import dataclass

from .chunker import Chunk


@dataclass(frozen=True)
class RetrievalResult:
    chunk_id: str
    score: float
    text: str
    chunk: Chunk


def cosine_similarity(left: list[float], right: list[float]) -> float:
    if len(left) != len(right):
        raise ValueError("Vectors must have the same dimension")
    if not left:
        return 0.0

    dot = sum(a * b for a, b in zip(left, right))
    left_norm = math.sqrt(sum(a * a for a in left))
    right_norm = math.sqrt(sum(b * b for b in right))
    if left_norm == 0.0 or right_norm == 0.0:
        return 0.0
    return dot / (left_norm * right_norm)


def retrieve(
    question_embedding: list[float],
    chunks: list[Chunk],
    top_k: int = 5,
) -> list[RetrievalResult]:
    if top_k <= 0:
        return []

    results: list[RetrievalResult] = []
    for chunk in chunks:
        if chunk.embedding is None:
            continue
        score = cosine_similarity(question_embedding, chunk.embedding)
        results.append(
            RetrievalResult(
                chunk_id=chunk.id,
                score=score,
                text=chunk.text,
                chunk=chunk,
            )
        )

    results.sort(key=lambda item: item.score, reverse=True)
    return results[:top_k]
