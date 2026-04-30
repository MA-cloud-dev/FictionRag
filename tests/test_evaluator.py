from pathlib import Path

from src.evaluator import (
    EvalItem,
    EvalResult,
    RetrievedChunk,
    apply_book_result_cap,
    compute_metrics,
    evaluate_dataset,
    find_gold_rank,
    load_dataset,
    sample_chunks_by_book,
    save_dataset,
)
from src.retriever import RetrievalResult
from src.chunker import Chunk


def make_chunk(
    chunk_id: str,
    book_name: str = "book",
    chunk_index: int = 1,
    embedding: list[float] | None = None,
) -> Chunk:
    return Chunk(
        id=chunk_id,
        book_name=book_name,
        chunk_index=chunk_index,
        start=0,
        end=10,
        text=f"text {chunk_id}",
        embedding=embedding or [1.0, 0.0],
    )


class FakeEmbeddingClient:
    class Config:
        model = "fake-embedding"

    config = Config()

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [[1.0, 0.0] for _text in texts]


class FakeRerankerClient:
    class Config:
        model = "fake-reranker"

    config = Config()

    def __init__(self, scores_by_document: dict[str, float]) -> None:
        self.scores_by_document = scores_by_document
        self.calls = 0

    def score(self, query: str, documents: list[str]) -> list[float]:
        self.calls += 1
        return [self.scores_by_document.get(document, 0.0) for document in documents]


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


def test_rerank_records_candidate_hit_and_promotes_gold(tmp_path: Path):
    chunks = [
        make_chunk("wrong", chunk_index=1),
        make_chunk("gold", chunk_index=2),
        make_chunk("other", chunk_index=3),
    ]
    dataset = [
        EvalItem(
            question="问题？",
            gold_chunk_id="gold",
            reference_answer="答案",
            gold_text_preview="gold",
            gold_book_name="book",
        )
    ]
    reranker = FakeRerankerClient(
        {
            "text wrong": 0.1,
            "text gold": 0.9,
            "text other": 0.2,
        }
    )

    results = evaluate_dataset(
        dataset=dataset,
        chunks=chunks,
        embedding_client=FakeEmbeddingClient(),
        top_k=1,
        rerank_enabled=True,
        reranker_client=reranker,
        rerank_cache_path=tmp_path / "rerank_scores.jsonl",
        rerank_candidate_top_n=3,
        book_route_count=0,
    )

    assert results[0].gold_rank == 1
    assert results[0].candidate_hit_at_30 is True
    assert results[0].candidate_rank == 2
    assert results[0].gold_rerank_score == 0.9
    assert results[0].retrieved_chunks[0].chunk_id == "gold"
    assert results[0].retrieved_chunks[0].base_score is not None
    assert results[0].retrieved_chunks[0].rerank_score == 0.9


def test_rerank_records_candidate_miss(tmp_path: Path):
    chunks = [
        make_chunk("wrong", chunk_index=1),
        make_chunk("gold", embedding=[0.0, 1.0], chunk_index=2),
    ]
    dataset = [
        EvalItem(
            question="问题？",
            gold_chunk_id="gold",
            reference_answer="答案",
            gold_text_preview="gold",
            gold_book_name="book",
        )
    ]

    results = evaluate_dataset(
        dataset=dataset,
        chunks=chunks,
        embedding_client=FakeEmbeddingClient(),
        top_k=1,
        rerank_enabled=True,
        reranker_client=FakeRerankerClient({"text wrong": 0.5}),
        rerank_cache_path=tmp_path / "rerank_scores.jsonl",
        rerank_candidate_top_n=1,
        book_route_count=0,
    )

    assert results[0].candidate_hit_at_30 is False
    assert results[0].candidate_rank is None
    assert results[0].failure_reason == "candidate_miss"


def test_rerank_cache_reuses_scores(tmp_path: Path):
    chunks = [make_chunk("one", chunk_index=1)]
    dataset = [
        EvalItem(
            question="问题？",
            gold_chunk_id="one",
            reference_answer="答案",
            gold_text_preview="one",
            gold_book_name="book",
        )
    ]
    cache_path = tmp_path / "rerank_scores.jsonl"
    reranker = FakeRerankerClient({"text one": 0.7})

    evaluate_dataset(
        dataset=dataset,
        chunks=chunks,
        embedding_client=FakeEmbeddingClient(),
        top_k=1,
        rerank_enabled=True,
        reranker_client=reranker,
        rerank_cache_path=cache_path,
        rerank_candidate_top_n=1,
        book_route_count=0,
    )
    evaluate_dataset(
        dataset=dataset,
        chunks=chunks,
        embedding_client=FakeEmbeddingClient(),
        top_k=1,
        rerank_enabled=True,
        reranker_client=reranker,
        rerank_cache_path=cache_path,
        rerank_candidate_top_n=1,
        book_route_count=0,
    )

    assert reranker.calls == 1


def test_apply_book_result_cap_limits_single_book():
    results = [
        RetrievalResult("a1", 1.0, "a1", make_chunk("a1", book_name="book-a")),
        RetrievalResult("a2", 0.9, "a2", make_chunk("a2", book_name="book-a")),
        RetrievalResult("a3", 0.8, "a3", make_chunk("a3", book_name="book-a")),
        RetrievalResult("b1", 0.7, "b1", make_chunk("b1", book_name="book-b")),
    ]

    selected = apply_book_result_cap(results, top_k=3, book_result_cap=2)

    assert [result.chunk_id for result in selected] == ["a1", "a2", "b1"]
