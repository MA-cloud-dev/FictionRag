from pathlib import Path

from src.evaluator import (
    EvalItem,
    EvalResult,
    RetrievedChunk,
    compute_metrics,
    find_gold_rank,
    load_dataset,
    sample_chunks_by_book,
    save_dataset,
)
from src.retriever import RetrievalResult
from src.chunker import Chunk


def make_chunk(chunk_id: str, book_name: str = "book", chunk_index: int = 1) -> Chunk:
    return Chunk(
        id=chunk_id,
        book_name=book_name,
        chunk_index=chunk_index,
        start=0,
        end=10,
        text=f"text {chunk_id}",
        embedding=[1.0, 0.0],
    )


def test_find_gold_rank_when_present():
    retrieved = [
        RetrievalResult("chunk-a", 0.9, "a", make_chunk("chunk-a")),
        RetrievalResult("chunk-b", 0.8, "b", make_chunk("chunk-b")),
    ]

    assert find_gold_rank("chunk-b", retrieved) == 2


def test_find_gold_rank_when_missing_or_empty():
    assert find_gold_rank("chunk-x", []) is None
    retrieved = [RetrievalResult("chunk-a", 0.9, "a", make_chunk("chunk-a"))]
    assert find_gold_rank("chunk-x", retrieved) is None


def test_compute_metrics_for_known_ranks():
    results = [
        EvalResult(
            question="q1",
            gold_chunk_id="a",
            reference_answer="a",
            retrieved_chunks=[RetrievedChunk("a", 0.9, "a")],
            gold_rank=1,
            hit_at_1=True,
            hit_at_3=True,
            hit_at_5=True,
            reciprocal_rank=1.0,
        ),
        EvalResult(
            question="q2",
            gold_chunk_id="b",
            reference_answer="b",
            retrieved_chunks=[RetrievedChunk("x", 0.9, "x"), RetrievedChunk("b", 0.8, "b")],
            gold_rank=2,
            hit_at_1=False,
            hit_at_3=True,
            hit_at_5=True,
            reciprocal_rank=0.5,
        ),
        EvalResult(
            question="q3",
            gold_chunk_id="c",
            reference_answer="c",
            retrieved_chunks=[],
            gold_rank=None,
            hit_at_1=False,
            hit_at_3=False,
            hit_at_5=False,
            reciprocal_rank=0.0,
        ),
    ]

    metrics = compute_metrics(results, (1, 3, 5))

    assert metrics["sample_count"] == 3
    assert metrics["recall"]["recall_at_1"] == 1 / 3
    assert metrics["recall"]["recall_at_3"] == 2 / 3
    assert metrics["recall"]["recall_at_5"] == 2 / 3
    assert metrics["mrr"] == 0.5
    assert metrics["average_gold_rank"] == 1.5
    assert metrics["missed_count"] == 1


def test_dataset_jsonl_round_trip(tmp_path: Path):
    path = tmp_path / "dataset.jsonl"
    dataset = [
        EvalItem(
            question="问题？",
            gold_chunk_id="book-000001",
            reference_answer="答案",
            gold_text_preview="原文预览",
        )
    ]

    save_dataset(dataset, path)
    loaded = load_dataset(path)

    assert loaded == dataset


def test_sample_chunks_by_book_uses_exact_requested_counts():
    chunks = [
        make_chunk(f"book-{index:06d}", book_name="book", chunk_index=index)
        for index in range(30)
    ] + [
        make_chunk(f"第十卷-{index:06d}", book_name="第十卷", chunk_index=index)
        for index in range(30)
    ]

    sampled = sample_chunks_by_book(
        chunks,
        samples_per_book={"book": 25, "第十卷": 25},
        seed=42,
    )

    assert len(sampled) == 50
    assert sum(chunk.book_name == "book" for chunk in sampled) == 25
    assert sum(chunk.book_name == "第十卷" for chunk in sampled) == 25
