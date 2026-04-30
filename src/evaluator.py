"""Quantitative retrieval evaluation for the FictionRag MVP."""

from __future__ import annotations

import json
import random
import re
import hashlib
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from .chunker import Chunk
from .config import PROJECT_ROOT
from .embeddings import EmbeddingClient
from .eval_prompts import EVAL_QUESTION_SYSTEM_PROMPT, build_question_generation_prompt
from .index_store import load_chunks
from .llm import LLMClient
from .retriever import RetrievalResult, build_bm25_index, retrieve
from .reranker import RerankerClient


DEFAULT_EVAL_DIR = PROJECT_ROOT / "rag_eval"
DEFAULT_SAMPLE_SIZE = 50
DEFAULT_SEED = 42
DEFAULT_TOP_KS = (1, 3, 5)
DEFAULT_RERANK_CANDIDATE_TOP_N = 30
DEFAULT_RERANK_VECTOR_TOP_N = 100
DEFAULT_RERANK_BM25_TOP_N = 100
BASELINE_ROUTE3_RECALL_AT_1 = 0.6599
BASELINE_ROUTE3_RECALL_AT_3 = 0.7513
BASELINE_ROUTE3_RECALL_AT_5 = 0.7868
BASELINE_ROUTE3_MRR = 0.7084
BASELINE_ROUTE3_MISSED_COUNT = 42


@dataclass(frozen=True)
class EvalItem:
    question: str
    gold_chunk_id: str
    reference_answer: str
    gold_text_preview: str
    gold_book_name: str | None = None


@dataclass(frozen=True)
class RetrievedChunk:
    chunk_id: str
    score: float
    text_preview: str
    book_name: str | None = None
    base_score: float | None = None
    rerank_score: float | None = None


@dataclass(frozen=True)
class EvalResult:
    question: str
    gold_chunk_id: str
    reference_answer: str
    retrieved_chunks: list[RetrievedChunk]
    gold_rank: int | None
    hit_at_1: bool
    hit_at_3: bool
    hit_at_5: bool
    reciprocal_rank: float
    gold_book_name: str | None = None
    candidate_rank: int | None = None
    candidate_hit_at_30: bool = False
    gold_base_score: float | None = None
    gold_rerank_score: float | None = None
    failure_reason: str | None = None


def run_evaluation(
    index_path: Path,
    output_dir: Path,
    sample_size: int,
    seed: int,
    top_k: int,
    force_generate: bool,
    llm_client: LLMClient,
    embedding_client: EmbeddingClient,
    samples_per_book: dict[str, int] | None = None,
    book_route_count: int = 0,
    book_result_cap: int | None = None,
    rerank_enabled: bool = False,
    reranker_client: RerankerClient | None = None,
    rerank_candidate_top_n: int = DEFAULT_RERANK_CANDIDATE_TOP_N,
    rerank_vector_top_n: int = DEFAULT_RERANK_VECTOR_TOP_N,
    rerank_bm25_top_n: int = DEFAULT_RERANK_BM25_TOP_N,
) -> dict[str, Any]:
    if sample_size <= 0:
        raise ValueError("sample_size must be greater than 0")
    if top_k < max(DEFAULT_TOP_KS):
        raise ValueError(f"top_k must be at least {max(DEFAULT_TOP_KS)}")

    output_dir.mkdir(parents=True, exist_ok=True)
    dataset_path = output_dir / "dataset.jsonl"
    results_path = output_dir / "results.jsonl"
    summary_path = output_dir / "summary.md"
    embedding_cache_path = output_dir / "question_embeddings.jsonl"
    rerank_cache_path = output_dir / "rerank_scores.jsonl"
    if rerank_enabled and reranker_client is None:
        raise ValueError("reranker_client is required when rerank_enabled is True")

    chunks = load_chunks(index_path)
    generation_errors: list[str] = []
    dataset_reused = dataset_path.exists() and not force_generate
    if dataset_reused:
        dataset = load_dataset(dataset_path)
    else:
        dataset, generation_errors = generate_dataset(
            chunks=chunks,
            llm_client=llm_client,
            sample_size=sample_size,
            seed=seed,
            samples_per_book=samples_per_book,
        )
        if not dataset:
            raise ValueError("No valid eval items were generated.")
        save_dataset(dataset, dataset_path)

    rerank_stats: dict[str, int] = {
        "cache_hits": 0,
        "api_scored": 0,
        "api_calls": 0,
    }
    results = evaluate_dataset(
        dataset=dataset,
        chunks=chunks,
        embedding_client=embedding_client,
        top_k=top_k,
        embedding_cache_path=embedding_cache_path,
        book_route_count=book_route_count,
        book_result_cap=book_result_cap,
        rerank_enabled=rerank_enabled,
        reranker_client=reranker_client,
        rerank_cache_path=rerank_cache_path,
        rerank_candidate_top_n=rerank_candidate_top_n,
        rerank_vector_top_n=rerank_vector_top_n,
        rerank_bm25_top_n=rerank_bm25_top_n,
        rerank_stats=rerank_stats,
    )
    save_results(results, results_path)

    metrics = compute_metrics(results, DEFAULT_TOP_KS)
    summary_markdown = build_summary_markdown(
        metrics=metrics,
        dataset=dataset,
        results=results,
        generation_errors=generation_errors,
        index_path=index_path,
        output_dir=output_dir,
        sample_size=sample_size,
        seed=seed,
        top_k=top_k,
        dataset_reused=dataset_reused,
        embedding_model=embedding_client.config.model,
        llm_model=llm_client.config.model,
        samples_per_book=samples_per_book,
        book_route_count=book_route_count,
        book_result_cap=book_result_cap,
        rerank_enabled=rerank_enabled,
        reranker_model=(reranker_client.config.model if reranker_client else None),
        rerank_candidate_top_n=rerank_candidate_top_n,
        rerank_vector_top_n=rerank_vector_top_n,
        rerank_bm25_top_n=rerank_bm25_top_n,
        rerank_stats=rerank_stats,
    )
    summary_path.write_text(summary_markdown, encoding="utf-8")

    return {
        "dataset_path": dataset_path,
        "results_path": results_path,
        "summary_path": summary_path,
        "metrics": metrics,
        "dataset_count": len(dataset),
        "dataset_reused": dataset_reused,
        "rerank_stats": rerank_stats,
    }


def generate_dataset(
    chunks: list[Chunk],
    llm_client: LLMClient,
    sample_size: int,
    seed: int,
    samples_per_book: dict[str, int] | None = None,
) -> tuple[list[EvalItem], list[str]]:
    sampled_chunks = (
        sample_chunks_by_book(chunks, samples_per_book=samples_per_book, seed=seed)
        if samples_per_book
        else sample_chunks(chunks, sample_size=sample_size, seed=seed)
    )
    items: list[EvalItem] = []
    errors: list[str] = []

    for chunk in sampled_chunks:
        prompt = build_question_generation_prompt(chunk.id, chunk.text)
        try:
            content = llm_client.chat(EVAL_QUESTION_SYSTEM_PROMPT, prompt, temperature=0)
            parsed = parse_json_object(content)
            question = str(parsed["question"]).strip()
            reference_answer = str(parsed["reference_answer"]).strip()
            if not question or not reference_answer:
                raise ValueError("question/reference_answer cannot be empty")
            items.append(
                EvalItem(
                    question=question,
                    gold_chunk_id=chunk.id,
                    reference_answer=reference_answer,
                    gold_text_preview=text_preview(chunk.text),
                    gold_book_name=chunk.book_name,
                )
            )
        except Exception as exc:  # Keep eval generation robust across single bad samples.
            errors.append(f"{chunk.id}: {exc}")

    return items, errors


def sample_chunks(chunks: list[Chunk], sample_size: int, seed: int) -> list[Chunk]:
    if not chunks:
        return []
    count = min(sample_size, len(chunks))
    rng = random.Random(seed)
    return rng.sample(chunks, count)


def sample_chunks_by_book(
    chunks: list[Chunk],
    samples_per_book: dict[str, int],
    seed: int,
) -> list[Chunk]:
    chunks_by_book: dict[str, list[Chunk]] = defaultdict(list)
    for chunk in chunks:
        chunks_by_book[chunk.book_name].append(chunk)

    rng = random.Random(seed)
    sampled: list[Chunk] = []
    for book_name, count in samples_per_book.items():
        if book_name not in chunks_by_book:
            raise ValueError(f"No chunks found for book_name: {book_name}")
        book_chunks = chunks_by_book[book_name]
        if len(book_chunks) < count:
            raise ValueError(
                f"Not enough chunks for book_name {book_name}: "
                f"requested {count}, available {len(book_chunks)}"
            )
        sampled.extend(rng.sample(book_chunks, count))
    rng.shuffle(sampled)
    return sampled


def parse_json_object(content: str) -> dict[str, Any]:
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


def evaluate_dataset(
    dataset: list[EvalItem],
    chunks: list[Chunk],
    embedding_client: EmbeddingClient,
    top_k: int,
    embedding_cache_path: Path | None = None,
    book_route_count: int = 0,
    book_result_cap: int | None = None,
    rerank_enabled: bool = False,
    reranker_client: RerankerClient | None = None,
    rerank_cache_path: Path | None = None,
    rerank_candidate_top_n: int = DEFAULT_RERANK_CANDIDATE_TOP_N,
    rerank_vector_top_n: int = DEFAULT_RERANK_VECTOR_TOP_N,
    rerank_bm25_top_n: int = DEFAULT_RERANK_BM25_TOP_N,
    rerank_stats: dict[str, int] | None = None,
) -> list[EvalResult]:
    results: list[EvalResult] = []
    if rerank_enabled and reranker_client is None:
        raise ValueError("reranker_client is required when rerank_enabled is True")
    if rerank_candidate_top_n < top_k:
        raise ValueError("rerank_candidate_top_n must be greater than or equal to top_k")
    if rerank_vector_top_n <= 0:
        raise ValueError("rerank_vector_top_n must be greater than 0")
    if rerank_bm25_top_n <= 0:
        raise ValueError("rerank_bm25_top_n must be greater than 0")
    if rerank_stats is None:
        rerank_stats = {"cache_hits": 0, "api_scored": 0, "api_calls": 0}

    question_embeddings = embed_eval_questions(
        questions=[item.question for item in dataset],
        embedding_client=embedding_client,
        cache_path=embedding_cache_path,
    )
    bm25_index = build_bm25_index(chunks)
    rerank_cache = (
        load_rerank_score_cache(rerank_cache_path)
        if rerank_enabled and rerank_cache_path is not None
        else {}
    )
    for item, question_embedding in zip(dataset, question_embeddings):
        candidate_rank: int | None = None
        gold_base_score: float | None = None
        gold_rerank_score: float | None = None
        if rerank_enabled:
            candidates = retrieve(
                question_embedding,
                chunks,
                top_k=rerank_candidate_top_n,
                vector_top_n=rerank_vector_top_n,
                bm25_top_n=rerank_bm25_top_n,
                query_text=item.question,
                bm25_index=bm25_index,
                book_route_count=book_route_count,
                book_result_cap=rerank_candidate_top_n,
            )
            candidate_rank = find_gold_rank(item.gold_chunk_id, candidates)
            base_scores = {result.chunk_id: result.score for result in candidates}
            gold_base_score = base_scores.get(item.gold_chunk_id)
            rerank_scores = score_rerank_candidates(
                question=item.question,
                candidates=candidates,
                reranker_client=reranker_client,
                cache=rerank_cache,
                cache_path=rerank_cache_path,
                stats=rerank_stats,
            )
            gold_rerank_score = rerank_scores.get(item.gold_chunk_id)
            retrieved = rerank_and_select_results(
                candidates=candidates,
                rerank_scores=rerank_scores,
                top_k=top_k,
                book_result_cap=book_result_cap,
            )
        else:
            retrieved = retrieve(
                question_embedding,
                chunks,
                top_k=top_k,
                query_text=item.question,
                bm25_index=bm25_index,
                book_route_count=book_route_count,
                book_result_cap=book_result_cap,
            )
            candidates = retrieved
            base_scores = {result.chunk_id: result.score for result in retrieved}
            rerank_scores: dict[str, float] = {}

        gold_rank = find_gold_rank(item.gold_chunk_id, retrieved)
        failure_reason = classify_failure_reason(
            gold_rank=gold_rank,
            candidate_rank=candidate_rank,
            gold_chunk_id=item.gold_chunk_id,
            unbounded_reranked=sort_by_rerank_score(candidates, rerank_scores)
            if rerank_enabled
            else [],
            top_k=top_k,
        )
        results.append(
            EvalResult(
                question=item.question,
                gold_chunk_id=item.gold_chunk_id,
                reference_answer=item.reference_answer,
                retrieved_chunks=[
                    RetrievedChunk(
                        chunk_id=result.chunk_id,
                        score=result.score,
                        text_preview=text_preview(result.text),
                        book_name=result.chunk.book_name,
                        base_score=base_scores.get(result.chunk_id),
                        rerank_score=rerank_scores.get(result.chunk_id),
                    )
                    for result in retrieved
                ],
                gold_rank=gold_rank,
                hit_at_1=is_hit_at_k(gold_rank, 1),
                hit_at_3=is_hit_at_k(gold_rank, 3),
                hit_at_5=is_hit_at_k(gold_rank, 5),
                reciprocal_rank=(1.0 / gold_rank) if gold_rank else 0.0,
                gold_book_name=item.gold_book_name,
                candidate_rank=candidate_rank,
                candidate_hit_at_30=candidate_rank is not None,
                gold_base_score=gold_base_score,
                gold_rerank_score=gold_rerank_score,
                failure_reason=failure_reason,
            )
        )
    return results


def score_rerank_candidates(
    question: str,
    candidates: list[RetrievalResult],
    reranker_client: RerankerClient | None,
    cache: dict[str, float],
    cache_path: Path | None,
    stats: dict[str, int],
) -> dict[str, float]:
    if reranker_client is None:
        raise ValueError("reranker_client is required")
    scores: dict[str, float] = {}
    missing: list[RetrievalResult] = []
    missing_keys: list[str] = []
    for result in candidates:
        key = _rerank_cache_key(
            model=reranker_client.config.model,
            question=question,
            chunk_id=result.chunk_id,
            text=result.text,
        )
        if key in cache:
            scores[result.chunk_id] = cache[key]
            stats["cache_hits"] = stats.get("cache_hits", 0) + 1
            continue
        missing.append(result)
        missing_keys.append(key)

    if missing:
        documents = [result.text for result in missing]
        missing_scores = reranker_client.score(question, documents)
        stats["api_calls"] = stats.get("api_calls", 0) + 1
        stats["api_scored"] = stats.get("api_scored", 0) + len(missing_scores)
        for result, key, score in zip(missing, missing_keys, missing_scores):
            cache[key] = score
            scores[result.chunk_id] = score
        if cache_path is not None:
            save_rerank_score_cache(cache, cache_path)

    return scores


def rerank_and_select_results(
    candidates: list[RetrievalResult],
    rerank_scores: dict[str, float],
    top_k: int,
    book_result_cap: int | None,
) -> list[RetrievalResult]:
    reranked = sort_by_rerank_score(candidates, rerank_scores)
    cap = book_result_cap or 0
    if cap <= 0:
        return reranked[:top_k]
    return apply_book_result_cap(reranked, top_k=top_k, book_result_cap=cap)


def sort_by_rerank_score(
    candidates: list[RetrievalResult],
    rerank_scores: dict[str, float],
) -> list[RetrievalResult]:
    reranked = [
        RetrievalResult(
            chunk_id=result.chunk_id,
            score=rerank_scores.get(result.chunk_id, 0.0),
            text=result.text,
            chunk=result.chunk,
        )
        for result in candidates
    ]
    reranked.sort(key=lambda result: result.score, reverse=True)
    return reranked


def apply_book_result_cap(
    results: list[RetrievalResult],
    top_k: int,
    book_result_cap: int,
) -> list[RetrievalResult]:
    selected: list[RetrievalResult] = []
    seen_ids: set[str] = set()
    count_by_book: dict[str, int] = defaultdict(int)
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


def classify_failure_reason(
    gold_rank: int | None,
    candidate_rank: int | None,
    gold_chunk_id: str,
    unbounded_reranked: list[RetrievalResult],
    top_k: int,
) -> str | None:
    if gold_rank is not None:
        return None
    if candidate_rank is None:
        return "candidate_miss"
    if any(result.chunk_id == gold_chunk_id for result in unbounded_reranked[:top_k]):
        return "book_cap_filtered"
    return "rerank_lost"


def embed_eval_questions(
    questions: list[str],
    embedding_client: EmbeddingClient,
    cache_path: Path | None = None,
) -> list[list[float]]:
    if not questions:
        return []
    if cache_path is None:
        return embedding_client.embed_texts(questions)

    cache = load_embedding_cache(cache_path)
    keys = [
        _embedding_cache_key(embedding_client.config.model, question)
        for question in questions
    ]
    missing_questions: list[str] = []
    missing_keys: list[str] = []
    for key, question in zip(keys, questions):
        if key in cache:
            continue
        missing_keys.append(key)
        missing_questions.append(question)

    if missing_questions:
        missing_embeddings = embedding_client.embed_texts(missing_questions)
        for key, embedding in zip(missing_keys, missing_embeddings):
            cache[key] = embedding
        save_embedding_cache(cache, cache_path)

    return [cache[key] for key in keys]


def load_embedding_cache(path: Path) -> dict[str, list[float]]:
    if not path.exists():
        return {}
    cache: dict[str, list[float]] = {}
    for raw in load_jsonl(path):
        key = raw.get("key")
        embedding = raw.get("embedding")
        if isinstance(key, str) and isinstance(embedding, list):
            cache[key] = [float(value) for value in embedding]
    return cache


def save_embedding_cache(cache: dict[str, list[float]], path: Path) -> None:
    records = [
        {"key": key, "embedding": embedding}
        for key, embedding in sorted(cache.items())
    ]
    save_jsonl(records, path)


def _embedding_cache_key(model: str, question: str) -> str:
    digest = hashlib.sha256(f"{model}\n{question}".encode("utf-8")).hexdigest()
    return digest


def load_rerank_score_cache(path: Path | None) -> dict[str, float]:
    if path is None or not path.exists():
        return {}
    cache: dict[str, float] = {}
    for raw in load_jsonl(path):
        key = raw.get("key")
        score = raw.get("score")
        if isinstance(key, str) and isinstance(score, (int, float)):
            cache[key] = float(score)
    return cache


def save_rerank_score_cache(cache: dict[str, float], path: Path) -> None:
    records = [
        {"key": key, "score": score}
        for key, score in sorted(cache.items())
    ]
    save_jsonl(records, path)


def _rerank_cache_key(
    model: str,
    question: str,
    chunk_id: str,
    text: str,
) -> str:
    text_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
    digest = hashlib.sha256(
        f"{model}\n{question}\n{chunk_id}\n{text_hash}".encode("utf-8")
    ).hexdigest()
    return digest


def find_gold_rank(gold_chunk_id: str, retrieved: list[RetrievalResult]) -> int | None:
    for index, result in enumerate(retrieved, start=1):
        if result.chunk_id == gold_chunk_id:
            return index
    return None


def is_hit_at_k(gold_rank: int | None, k: int) -> bool:
    return gold_rank is not None and gold_rank <= k


def compute_metrics(results: list[EvalResult], top_ks: tuple[int, ...]) -> dict[str, Any]:
    total = len(results)
    if total == 0:
        return {
            "sample_count": 0,
            "top1_hit_rate": 0.0,
            "mrr": 0.0,
            "average_gold_rank": None,
            "missed_count": 0,
            "recall": {f"recall_at_{k}": 0.0 for k in top_ks},
        }

    found_ranks = [result.gold_rank for result in results if result.gold_rank is not None]
    recall = {
        f"recall_at_{k}": sum(is_hit_at_k(result.gold_rank, k) for result in results) / total
        for k in top_ks
    }
    return {
        "sample_count": total,
        "top1_hit_rate": recall.get("recall_at_1", 0.0),
        "mrr": sum(result.reciprocal_rank for result in results) / total,
        "average_gold_rank": (sum(found_ranks) / len(found_ranks)) if found_ranks else None,
        "missed_count": total - len(found_ranks),
        "recall": recall,
    }


def compute_metrics_by_book(
    results: list[EvalResult],
    top_ks: tuple[int, ...],
) -> dict[str, dict[str, Any]]:
    results_by_book: dict[str, list[EvalResult]] = defaultdict(list)
    for result in results:
        book_name = result.gold_book_name or _book_name_from_chunk_id(result.gold_chunk_id)
        results_by_book[book_name].append(result)
    return {
        book_name: compute_metrics(book_results, top_ks)
        for book_name, book_results in sorted(results_by_book.items())
    }


def compute_candidate_metrics(results: list[EvalResult]) -> dict[str, Any]:
    total = len(results)
    candidate_hits = sum(result.candidate_hit_at_30 for result in results)
    rerank_lost = sum(
        result.candidate_hit_at_30 and result.gold_rank is None
        for result in results
    )
    return {
        "candidate_hit_count": candidate_hits,
        "candidate_miss_count": total - candidate_hits,
        "candidate_hit_rate": (candidate_hits / total) if total else 0.0,
        "rerank_lost_count": rerank_lost,
    }


def compute_candidate_metrics_by_book(results: list[EvalResult]) -> dict[str, dict[str, Any]]:
    results_by_book: dict[str, list[EvalResult]] = defaultdict(list)
    for result in results:
        book_name = result.gold_book_name or _book_name_from_chunk_id(result.gold_chunk_id)
        results_by_book[book_name].append(result)
    return {
        book_name: compute_candidate_metrics(book_results)
        for book_name, book_results in sorted(results_by_book.items())
    }


def _book_name_from_chunk_id(chunk_id: str) -> str:
    if "-" not in chunk_id:
        return "unknown"
    return chunk_id.rsplit("-", 1)[0]


def save_dataset(dataset: list[EvalItem], path: Path) -> None:
    save_jsonl([asdict(item) for item in dataset], path)


def load_dataset(path: Path) -> list[EvalItem]:
    items: list[EvalItem] = []
    for raw in load_jsonl(path):
        items.append(
            EvalItem(
                question=str(raw["question"]),
                gold_chunk_id=str(raw["gold_chunk_id"]),
                reference_answer=str(raw["reference_answer"]),
                gold_text_preview=str(raw["gold_text_preview"]),
                gold_book_name=(
                    str(raw["gold_book_name"])
                    if raw.get("gold_book_name") is not None
                    else None
                ),
            )
        )
    if not items:
        raise ValueError(f"Eval dataset is empty: {path}")
    return items


def save_results(results: list[EvalResult], path: Path) -> None:
    save_jsonl([asdict(result) for result in results], path)


def save_jsonl(records: list[dict[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        for record in records:
            file.write(json.dumps(record, ensure_ascii=False) + "\n")


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as file:
        for line in file:
            stripped = line.strip()
            if stripped:
                records.append(json.loads(stripped))
    return records


def build_summary_markdown(
    metrics: dict[str, Any],
    dataset: list[EvalItem],
    results: list[EvalResult],
    generation_errors: list[str],
    index_path: Path,
    output_dir: Path,
    sample_size: int,
    seed: int,
    top_k: int,
    dataset_reused: bool,
    embedding_model: str,
    llm_model: str,
    samples_per_book: dict[str, int] | None = None,
    book_route_count: int = 0,
    book_result_cap: int | None = None,
    rerank_enabled: bool = False,
    reranker_model: str | None = None,
    rerank_candidate_top_n: int = DEFAULT_RERANK_CANDIDATE_TOP_N,
    rerank_vector_top_n: int = DEFAULT_RERANK_VECTOR_TOP_N,
    rerank_bm25_top_n: int = DEFAULT_RERANK_BM25_TOP_N,
    rerank_stats: dict[str, int] | None = None,
) -> str:
    recall = metrics["recall"]
    average_rank = metrics["average_gold_rank"]
    average_rank_text = f"{average_rank:.2f}" if average_rank is not None else "N/A"
    misses = select_representative_failures(results, limit=5)
    metrics_by_book = compute_metrics_by_book(results, DEFAULT_TOP_KS)
    candidate_metrics = compute_candidate_metrics(results)
    candidate_metrics_by_book = compute_candidate_metrics_by_book(results)
    rerank_stats = rerank_stats or {}

    lines = [
        "# RAG Retrieval Evaluation Summary",
        "",
        f"- Generated at: {datetime.now().isoformat(timespec='seconds')}",
        f"- Index: `{index_path}`",
        f"- Output dir: `{output_dir}`",
        f"- Dataset reused: `{dataset_reused}`",
        f"- Requested sample size: `{sample_size}`",
        f"- Samples per book: `{samples_per_book or {}}`",
        f"- Effective sample count: `{len(dataset)}`",
        f"- Seed: `{seed}`",
        f"- Retrieval top_k: `{top_k}`",
        f"- Book route count: `{book_route_count}`",
        f"- Book result cap: `{book_result_cap}`",
        f"- Rerank enabled: `{rerank_enabled}`",
        f"- Reranker model: `{reranker_model or ''}`",
        f"- Rerank candidate top_n: `{rerank_candidate_top_n}`",
        f"- Rerank vector top_n: `{rerank_vector_top_n}`",
        f"- Rerank BM25 top_n: `{rerank_bm25_top_n}`",
        f"- Rerank cache hits: `{rerank_stats.get('cache_hits', 0)}`",
        f"- Rerank API scored: `{rerank_stats.get('api_scored', 0)}`",
        f"- Rerank API calls: `{rerank_stats.get('api_calls', 0)}`",
        f"- Embedding model: `{embedding_model}`",
        f"- LLM model for question generation: `{llm_model}`",
        "",
        "## Metrics",
        "",
        "| Metric | Value | Meaning |",
        "| --- | ---: | --- |",
        f"| Recall@1 | {recall['recall_at_1']:.2%} | gold chunk 出现在第 1 个召回结果中的比例。 |",
        f"| Recall@3 | {recall['recall_at_3']:.2%} | gold chunk 出现在前 3 个召回结果中的比例。 |",
        f"| Recall@5 | {recall['recall_at_5']:.2%} | gold chunk 出现在前 5 个召回结果中的比例。 |",
        f"| MRR | {metrics['mrr']:.4f} | gold chunk 排名越靠前越接近 1。未命中按 0 计算。 |",
        f"| Top1 Hit Rate | {metrics['top1_hit_rate']:.2%} | 与 Recall@1 相同，是最严格的直接命中能力。 |",
        f"| Average Gold Rank | {average_rank_text} | 只在命中的样本中计算 gold chunk 的平均排名。 |",
        f"| Missed Count | {metrics['missed_count']} | gold chunk 未出现在 Top {top_k} 的样本数量。 |",
        f"| Candidate Hit@30 | {candidate_metrics['candidate_hit_rate']:.2%} | gold chunk 出现在 rerank 前 Top {rerank_candidate_top_n} 候选池的比例。 |",
        f"| Candidate Miss@30 | {candidate_metrics['candidate_miss_count']} | gold chunk 未进入 rerank 前 Top {rerank_candidate_top_n} 候选池的数量。 |",
        f"| Rerank Lost Count | {candidate_metrics['rerank_lost_count']} | gold chunk 进入候选池但最终没进 Top {top_k} 的数量。 |",
        "",
    ]

    if rerank_enabled:
        lines.extend(
            [
                "## Baseline Comparison",
                "",
                "| Metric | Baseline route=3 cap=3 | Current | Delta |",
                "| --- | ---: | ---: | ---: |",
                _format_baseline_delta_row(
                    "Recall@1",
                    BASELINE_ROUTE3_RECALL_AT_1,
                    recall["recall_at_1"],
                    percent=True,
                ),
                _format_baseline_delta_row(
                    "Recall@3",
                    BASELINE_ROUTE3_RECALL_AT_3,
                    recall["recall_at_3"],
                    percent=True,
                ),
                _format_baseline_delta_row(
                    "Recall@5",
                    BASELINE_ROUTE3_RECALL_AT_5,
                    recall["recall_at_5"],
                    percent=True,
                ),
                _format_baseline_delta_row(
                    "MRR",
                    BASELINE_ROUTE3_MRR,
                    metrics["mrr"],
                    percent=False,
                ),
                _format_baseline_delta_row(
                    "Missed Count",
                    BASELINE_ROUTE3_MISSED_COUNT,
                    metrics["missed_count"],
                    percent=False,
                ),
                "",
            ]
        )

    lines.extend(
        [
        "## Metrics by Book",
        "",
        "| Book | Samples | Recall@1 | Recall@3 | Recall@5 | MRR | Missed | Candidate Hit@30 | Rerank Lost |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )

    for book_name, book_metrics in metrics_by_book.items():
        book_recall = book_metrics["recall"]
        book_candidate = candidate_metrics_by_book.get(book_name, {})
        lines.append(
            f"| {book_name} | {book_metrics['sample_count']} | "
            f"{book_recall['recall_at_1']:.2%} | "
            f"{book_recall['recall_at_3']:.2%} | "
            f"{book_recall['recall_at_5']:.2%} | "
            f"{book_metrics['mrr']:.4f} | "
            f"{book_metrics['missed_count']} | "
            f"{book_candidate.get('candidate_hit_rate', 0.0):.2%} | "
            f"{book_candidate.get('rerank_lost_count', 0)} |"
        )

    lines.extend(
        [
            "",
        "## Interpretation",
        "",
        "- Recall@1 高说明问题向量和原文 chunk 的语义匹配很直接，首条结果通常可用于回答。",
        "- Recall@5 高但 Recall@1 低说明相关片段能被找回，但排序还可以优化，后续可考虑 rerank。",
        "- MRR 对排名敏感，适合观察排序质量；它比 Recall@5 更能反映 gold chunk 是否靠前。",
        "- 未命中样例通常用于分析 chunk 切分、问题生成质量、embedding 模型或 top_k 设置是否需要调整。",
        "",
        "## Failed Example Analysis",
        "",
        ]
    )

    if not misses:
        lines.append("No failed examples. All gold chunks were found within the evaluated Top K.")
    else:
        for index, result in enumerate(misses, start=1):
            top_chunks = ", ".join(chunk.chunk_id for chunk in result.retrieved_chunks[:5])
            top_scores = ", ".join(
                _format_optional_score(chunk.rerank_score if rerank_enabled else chunk.score)
                for chunk in result.retrieved_chunks[:5]
            )
            lines.extend(
                [
                    f"### {index}. {result.question}",
                    "",
                    f"- Reason label: `{result.failure_reason or 'unknown'}`",
                    f"- Gold chunk: `{result.gold_chunk_id}`",
                    f"- Gold book: `{result.gold_book_name or _book_name_from_chunk_id(result.gold_chunk_id)}`",
                    f"- Candidate rank: `{result.candidate_rank}`",
                    f"- Retrieved top chunks: `{top_chunks}`",
                    f"- Top scores: `{top_scores}`",
                    f"- Gold base score: `{_format_optional_score(result.gold_base_score)}`",
                    f"- Gold rerank score: `{_format_optional_score(result.gold_rerank_score)}`",
                    f"- Reference answer: {result.reference_answer}",
                    "",
                ]
            )

    if generation_errors:
        lines.extend(
            [
                "## Generation Errors",
                "",
                f"{len(generation_errors)} chunk(s) failed during question generation.",
                "",
            ]
        )
        for error in generation_errors[:10]:
            lines.append(f"- {error}")

    return "\n".join(lines) + "\n"


def _format_baseline_delta_row(
    name: str,
    baseline: float | int,
    current: float | int,
    percent: bool,
) -> str:
    delta = current - baseline
    if percent:
        return f"| {name} | {baseline:.2%} | {current:.2%} | {delta:+.2%} |"
    if isinstance(baseline, int) and isinstance(current, int):
        return f"| {name} | {baseline} | {current} | {delta:+d} |"
    return f"| {name} | {baseline:.4f} | {current:.4f} | {delta:+.4f} |"


def _format_optional_score(score: float | None) -> str:
    if score is None:
        return "N/A"
    return f"{score:.4f}"


def select_representative_failures(
    results: list[EvalResult],
    limit: int,
) -> list[EvalResult]:
    failures = [result for result in results if result.gold_rank is None]
    if len(failures) <= limit:
        return failures

    selected: list[EvalResult] = []
    seen_ids: set[str] = set()
    for reason in ("candidate_miss", "rerank_lost", "book_cap_filtered"):
        for result in failures:
            if result.failure_reason != reason or result.gold_chunk_id in seen_ids:
                continue
            selected.append(result)
            seen_ids.add(result.gold_chunk_id)
            break

    for result in failures:
        if len(selected) >= limit:
            break
        if result.gold_chunk_id in seen_ids:
            continue
        selected.append(result)
        seen_ids.add(result.gold_chunk_id)
    return selected


def text_preview(text: str, limit: int = 220) -> str:
    normalized = " ".join(text.split())
    if len(normalized) <= limit:
        return normalized
    return normalized[:limit] + "..."
