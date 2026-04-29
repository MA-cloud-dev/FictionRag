"""Brute-force cosine similarity and BM25 sparse retrieval."""

from __future__ import annotations

from collections import Counter, defaultdict
import math
from dataclasses import dataclass
import re

from .chunker import Chunk


DEFAULT_VECTOR_TOP_N = 20
DEFAULT_BM25_TOP_N = 20
DEFAULT_TOP_SCENE_COUNT = 3
DEFAULT_NEIGHBOR_RADIUS = 1
DEFAULT_NEIGHBOR_BEFORE = 2
DEFAULT_NEIGHBOR_AFTER = 1
BM25_K1 = 1.5
BM25_B = 0.75
VECTOR_SCORE_WEIGHT = 0.8
BM25_SCORE_WEIGHT = 0.2
RESCUE_SLOT_RANK = 5
RESCUE_MIN_BM25_NORM = 0.35
RESCUE_MIN_RARE_COVERAGE = 0.2
RESCUE_MIN_SCORE = 0.45
RESCUE_SCORE_MARGIN = 0.08

_ALNUM_PATTERN = re.compile(r"[A-Za-z0-9]+")
_RESCUE_STOP_TERMS = {
    "什么",
    "哪些",
    "多少",
    "如何",
    "为何",
    "为什么",
    "是谁",
    "根据",
    "原文",
    "小说",
    "片段",
    "主角",
    "他们",
    "她们",
    "这个",
    "那个",
    "时候",
}


@dataclass(frozen=True)
class RetrievalResult:
    chunk_id: str
    score: float
    text: str
    chunk: Chunk


@dataclass(frozen=True)
class _RescueEvidence:
    bm25_norm: float
    vector_norm: float
    rare_coverage: float
    score: float


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
    vector_top_n: int = DEFAULT_VECTOR_TOP_N,
    top_scene_count: int = DEFAULT_TOP_SCENE_COUNT,
    neighbor_radius: int = DEFAULT_NEIGHBOR_RADIUS,
    query_text: str | None = None,
    bm25_top_n: int = DEFAULT_BM25_TOP_N,
    neighbor_before: int | None = None,
    neighbor_after: int | None = None,
) -> list[RetrievalResult]:
    if top_k <= 0:
        return []
    if vector_top_n <= 0:
        return []
    if bm25_top_n <= 0:
        return []
    if top_scene_count <= 0:
        return []
    if neighbor_radius < 0:
        raise ValueError("neighbor_radius must be greater than or equal to 0")
    if neighbor_before is None:
        neighbor_before = DEFAULT_NEIGHBOR_BEFORE
    if neighbor_after is None:
        neighbor_after = DEFAULT_NEIGHBOR_AFTER
    if neighbor_before < 0:
        raise ValueError("neighbor_before must be greater than or equal to 0")
    if neighbor_after < 0:
        raise ValueError("neighbor_after must be greater than or equal to 0")

    results = _build_vector_results(question_embedding, chunks)
    vector_results = results
    bm25_scores: dict[str, float] = {}
    if query_text:
        bm25_scores = _bm25_scores(query_text, chunks)
        results = _fuse_vector_and_bm25_results(
            vector_results=results,
            chunks=[result.chunk for result in results],
            query_text=query_text,
            vector_top_n=vector_top_n,
            bm25_top_n=bm25_top_n,
            bm25_scores=bm25_scores,
        )

    results.sort(key=lambda item: item.score, reverse=True)
    if not _has_scene_metadata(results):
        return results[:top_k]

    expanded = _expand_by_scene(
        results=results,
        chunks=[result.chunk for result in results],
        top_k=top_k,
        vector_top_n=vector_top_n,
        top_scene_count=top_scene_count,
        neighbor_before=neighbor_before,
        neighbor_after=neighbor_after,
    )
    if query_text and bm25_scores:
        expanded = _apply_rescue_slot(
            baseline_results=expanded,
            fused_results=results,
            vector_results=vector_results,
            chunks=[result.chunk for result in results],
            query_text=query_text,
            bm25_scores=bm25_scores,
            top_k=top_k,
            vector_top_n=vector_top_n,
            bm25_top_n=bm25_top_n,
            neighbor_before=neighbor_before,
            neighbor_after=neighbor_after,
        )
    return expanded


def _build_vector_results(
    question_embedding: list[float],
    chunks: list[Chunk],
) -> list[RetrievalResult]:
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
    return results


def _fuse_vector_and_bm25_results(
    vector_results: list[RetrievalResult],
    chunks: list[Chunk],
    query_text: str,
    vector_top_n: int,
    bm25_top_n: int,
    bm25_scores: dict[str, float] | None = None,
) -> list[RetrievalResult]:
    if bm25_scores is None:
        bm25_scores = _bm25_scores(query_text, chunks)
    vector_scores = {
        result.chunk_id: result.score
        for result in vector_results[:vector_top_n]
    }
    bm25_scores = dict(
        sorted(bm25_scores.items(), key=lambda item: item[1], reverse=True)[:bm25_top_n]
    )

    max_vector_score = max(vector_scores.values(), default=0.0)
    max_bm25_score = max(bm25_scores.values(), default=0.0)
    candidate_ids = set(vector_scores) | set(bm25_scores)
    if not candidate_ids:
        return vector_results

    vector_result_by_id = {result.chunk_id: result for result in vector_results}
    fused: list[RetrievalResult] = []
    for result in vector_results:
        vector_score = vector_scores.get(result.chunk_id, 0.0)
        bm25_score = bm25_scores.get(result.chunk_id, 0.0)
        score = VECTOR_SCORE_WEIGHT * _normalize_score(
            vector_score,
            max_vector_score,
        ) + BM25_SCORE_WEIGHT * _normalize_score(
            bm25_score,
            max_bm25_score,
        )
        fused.append(
            RetrievalResult(
                chunk_id=result.chunk_id,
                score=score,
                text=result.text,
                chunk=result.chunk,
            )
        )

    # Keep every vector result for neighbor expansion, but ensure sparse-only hits
    # are represented even if their vector score was outside the dense top-N.
    for chunk_id in candidate_ids:
        if chunk_id in vector_result_by_id:
            continue
        chunk = next((chunk for chunk in chunks if chunk.id == chunk_id), None)
        if chunk is None:
            continue
        bm25_score = bm25_scores.get(chunk_id, 0.0)
        fused.append(
            RetrievalResult(
                chunk_id=chunk.id,
                score=_normalize_score(bm25_score, max_bm25_score),
                text=chunk.text,
                chunk=chunk,
            )
        )

    fused.sort(key=lambda item: item.score, reverse=True)
    return fused


def _apply_rescue_slot(
    baseline_results: list[RetrievalResult],
    fused_results: list[RetrievalResult],
    vector_results: list[RetrievalResult],
    chunks: list[Chunk],
    query_text: str,
    bm25_scores: dict[str, float],
    top_k: int,
    vector_top_n: int,
    bm25_top_n: int,
    neighbor_before: int,
    neighbor_after: int,
) -> list[RetrievalResult]:
    if top_k < RESCUE_SLOT_RANK or len(baseline_results) < RESCUE_SLOT_RANK:
        return baseline_results

    locked_results = baseline_results[: RESCUE_SLOT_RANK - 1]
    baseline_slot = baseline_results[RESCUE_SLOT_RANK - 1]
    locked_ids = {result.chunk_id for result in locked_results}

    result_by_id = {result.chunk_id: result for result in fused_results}
    chunks_by_index = {chunk.chunk_index: chunk for chunk in chunks}
    chunk_by_id = {chunk.id: chunk for chunk in chunks}
    vector_scores = {result.chunk_id: result.score for result in vector_results[:vector_top_n]}
    bm25_top_ids = [
        chunk_id
        for chunk_id, _score in sorted(
            bm25_scores.items(),
            key=lambda item: item[1],
            reverse=True,
        )[:bm25_top_n]
    ]
    vector_top_ids = [result.chunk_id for result in vector_results[:vector_top_n]]

    candidate_ids: set[str] = {baseline_slot.chunk_id}
    for seed_id in bm25_top_ids + vector_top_ids:
        seed = chunk_by_id.get(seed_id)
        if seed is None:
            continue
        for offset in range(-neighbor_before, neighbor_after + 1):
            chunk = chunks_by_index.get(seed.chunk_index + offset)
            if chunk is not None:
                candidate_ids.add(chunk.id)

    candidate_ids.difference_update(locked_ids)
    if not candidate_ids:
        return baseline_results

    evidence_context = _build_rescue_evidence_context(query_text, chunks)
    max_vector_score = max(vector_scores.values(), default=0.0)
    max_bm25_score = max(bm25_scores.values(), default=0.0)

    def evidence_for(chunk_id: str) -> _RescueEvidence:
        return _score_rescue_candidate(
            chunk_id=chunk_id,
            bm25_scores=bm25_scores,
            vector_scores=vector_scores,
            max_bm25_score=max_bm25_score,
            max_vector_score=max_vector_score,
            evidence_context=evidence_context,
        )

    baseline_evidence = evidence_for(baseline_slot.chunk_id)
    ranked_candidates = sorted(
        (
            (
                evidence_for(chunk_id),
                result_by_id.get(chunk_id),
            )
            for chunk_id in candidate_ids
        ),
        key=lambda item: (
            item[0].score,
            item[0].bm25_norm,
            item[0].rare_coverage,
        ),
        reverse=True,
    )

    for candidate_evidence, candidate in ranked_candidates:
        if candidate is None:
            continue
        if candidate.chunk_id == baseline_slot.chunk_id:
            return baseline_results
        if not _is_strong_rescue(candidate_evidence, baseline_evidence):
            return baseline_results

        rescued: list[RetrievalResult] = []
        seen_ids: set[str] = set()
        for result in locked_results + [candidate] + baseline_results[RESCUE_SLOT_RANK - 1 :]:
            if result.chunk_id in seen_ids:
                continue
            seen_ids.add(result.chunk_id)
            rescued.append(result)
            if len(rescued) == top_k:
                break
        return rescued

    return baseline_results


def _build_rescue_evidence_context(
    query_text: str,
    chunks: list[Chunk],
) -> tuple[set[str], dict[str, set[str]], dict[str, float]]:
    query_terms = {
        term
        for term in set(_tokenize_for_bm25(query_text))
        if term not in _RESCUE_STOP_TERMS
    }
    if not query_terms:
        return set(), {}, {}

    document_terms = {
        chunk.id: set(_tokenize_for_bm25(chunk.text))
        for chunk in chunks
    }
    document_frequency: Counter[str] = Counter()
    for terms in document_terms.values():
        document_frequency.update(query_terms & terms)

    total_documents = len(chunks)
    rare_cutoff = max(3, int(total_documents * 0.1))
    rare_terms = {
        term
        for term in query_terms
        if 0 < document_frequency.get(term, 0) <= rare_cutoff
    }
    if not rare_terms:
        rare_terms = query_terms

    term_weights = {
        term: math.log(
            1.0
            + (total_documents - document_frequency.get(term, 0) + 0.5)
            / (document_frequency.get(term, 0) + 0.5)
        )
        for term in rare_terms
    }
    return rare_terms, document_terms, term_weights


def _score_rescue_candidate(
    chunk_id: str,
    bm25_scores: dict[str, float],
    vector_scores: dict[str, float],
    max_bm25_score: float,
    max_vector_score: float,
    evidence_context: tuple[set[str], dict[str, set[str]], dict[str, float]],
) -> _RescueEvidence:
    bm25_norm = _normalize_score(bm25_scores.get(chunk_id, 0.0), max_bm25_score)
    vector_norm = _normalize_score(vector_scores.get(chunk_id, 0.0), max_vector_score)
    rare_terms, document_terms, term_weights = evidence_context
    rare_coverage = 0.0
    if rare_terms:
        terms = document_terms.get(chunk_id, set())
        total_weight = sum(term_weights.values())
        matched_weight = sum(
            term_weights[term]
            for term in rare_terms
            if term in terms
        )
        rare_coverage = matched_weight / total_weight if total_weight > 0.0 else 0.0
    score = 0.7 * bm25_norm + 0.2 * rare_coverage + 0.1 * vector_norm
    return _RescueEvidence(
        bm25_norm=bm25_norm,
        vector_norm=vector_norm,
        rare_coverage=rare_coverage,
        score=score,
    )


def _is_strong_rescue(
    candidate: _RescueEvidence,
    baseline: _RescueEvidence,
) -> bool:
    if candidate.bm25_norm < RESCUE_MIN_BM25_NORM:
        return False
    if candidate.rare_coverage < RESCUE_MIN_RARE_COVERAGE:
        return False
    if candidate.score < RESCUE_MIN_SCORE:
        return False
    return candidate.score >= baseline.score + RESCUE_SCORE_MARGIN


def _normalize_score(score: float, max_score: float) -> float:
    if max_score <= 0.0:
        return 0.0
    return score / max_score


def _bm25_scores(query_text: str, chunks: list[Chunk]) -> dict[str, float]:
    query_terms = Counter(_tokenize_for_bm25(query_text))
    if not query_terms or not chunks:
        return {}

    document_terms = [_tokenize_for_bm25(chunk.text) for chunk in chunks]
    document_lengths = [len(terms) for terms in document_terms]
    average_length = sum(document_lengths) / len(document_lengths)
    if average_length == 0.0:
        return {}

    document_frequencies: Counter[str] = Counter()
    for terms in document_terms:
        document_frequencies.update(set(terms))

    total_documents = len(chunks)
    scores: dict[str, float] = {}
    for chunk, terms, document_length in zip(chunks, document_terms, document_lengths):
        if document_length == 0:
            continue
        term_counts = Counter(terms)
        score = 0.0
        for term, query_count in query_terms.items():
            term_frequency = term_counts.get(term, 0)
            if term_frequency == 0:
                continue
            document_frequency = document_frequencies[term]
            idf = math.log(
                1.0
                + (total_documents - document_frequency + 0.5)
                / (document_frequency + 0.5)
            )
            denominator = term_frequency + BM25_K1 * (
                1.0 - BM25_B + BM25_B * document_length / average_length
            )
            score += (
                query_count
                * idf
                * term_frequency
                * (BM25_K1 + 1.0)
                / denominator
            )
        if score > 0.0:
            scores[chunk.id] = score
    return scores


def _tokenize_for_bm25(text: str) -> list[str]:
    tokens: list[str] = []
    cjk_buffer: list[str] = []
    word_buffer: list[str] = []

    def flush_cjk() -> None:
        if not cjk_buffer:
            return
        sequence = "".join(cjk_buffer)
        for size in range(2, 5):
            if len(sequence) < size:
                continue
            for index in range(0, len(sequence) - size + 1):
                tokens.append(sequence[index : index + size])
        cjk_buffer.clear()

    def flush_word() -> None:
        if not word_buffer:
            return
        token = "".join(word_buffer).lower()
        if _ALNUM_PATTERN.fullmatch(token):
            tokens.append(token)
        word_buffer.clear()

    for char in text:
        if _is_cjk(char):
            flush_word()
            cjk_buffer.append(char)
            continue
        if char.isascii() and char.isalnum():
            flush_cjk()
            word_buffer.append(char)
            continue
        flush_cjk()
        flush_word()

    flush_cjk()
    flush_word()
    return tokens


def _is_cjk(char: str) -> bool:
    codepoint = ord(char)
    return (
        0x3400 <= codepoint <= 0x4DBF
        or 0x4E00 <= codepoint <= 0x9FFF
        or 0xF900 <= codepoint <= 0xFAFF
        or 0x20000 <= codepoint <= 0x2A6DF
        or 0x2A700 <= codepoint <= 0x2B73F
        or 0x2B740 <= codepoint <= 0x2B81F
        or 0x2B820 <= codepoint <= 0x2CEAF
    )


def _has_scene_metadata(results: list[RetrievalResult]) -> bool:
    return any(result.chunk.scene_id != "scene-000" for result in results)


def _expand_by_scene(
    results: list[RetrievalResult],
    chunks: list[Chunk],
    top_k: int,
    vector_top_n: int,
    top_scene_count: int,
    neighbor_before: int,
    neighbor_after: int,
) -> list[RetrievalResult]:
    candidates = results[:vector_top_n]
    if not candidates:
        return []

    scene_scores: dict[str, float] = {}
    scene_best_rank: dict[str, int] = {}
    scene_candidates: dict[str, list[RetrievalResult]] = defaultdict(list)
    for rank, result in enumerate(candidates, start=1):
        scene_id = result.chunk.scene_id
        scene_candidates[scene_id].append(result)
        if scene_id not in scene_scores or result.score > scene_scores[scene_id]:
            scene_scores[scene_id] = result.score
            scene_best_rank[scene_id] = rank

    selected_scenes = sorted(
        scene_scores,
        key=lambda scene_id: (-scene_scores[scene_id], scene_best_rank[scene_id]),
    )[:top_scene_count]

    chunks_by_scene: dict[str, list[Chunk]] = defaultdict(list)
    chunks_by_index = {chunk.chunk_index: chunk for chunk in chunks}
    for chunk in chunks:
        chunks_by_scene[chunk.scene_id].append(chunk)
    for scene_chunks in chunks_by_scene.values():
        scene_chunks.sort(key=lambda chunk: chunk.chunk_index)

    selected_ids: set[str] = set()
    selected_order: list[str] = []

    def add_chunk(chunk: Chunk | None) -> None:
        if chunk is None or chunk.id in selected_ids:
            return
        selected_ids.add(chunk.id)
        selected_order.append(chunk.id)

    for scene_id in selected_scenes:
        for result in scene_candidates.get(scene_id, []):
            for offset in range(-neighbor_before, neighbor_after + 1):
                add_chunk(chunks_by_index.get(result.chunk.chunk_index + offset))

        for chunk in chunks_by_scene.get(scene_id, []):
            add_chunk(chunk)

    result_by_id = {result.chunk_id: result for result in results}
    expanded = [
        result_by_id[chunk_id]
        for chunk_id in selected_order
        if chunk_id in result_by_id
    ][:top_k]

    expanded.sort(key=lambda result: result.chunk.chunk_index)
    return expanded
