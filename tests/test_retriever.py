from src.chunker import Chunk
from src.retriever import cosine_similarity, retrieve


def make_chunk(chunk_id: str, embedding: list[float]) -> Chunk:
    return Chunk(
        id=chunk_id,
        book_name="book",
        chunk_index=1,
        start=0,
        end=1,
        text=f"text {chunk_id}",
        embedding=embedding,
    )


def test_cosine_similarity_handles_zero_vector():
    assert cosine_similarity([0.0, 0.0], [1.0, 0.0]) == 0.0


def test_retrieve_sorts_by_score_descending():
    chunks = [
        make_chunk("low", [0.0, 1.0]),
        make_chunk("high", [1.0, 0.0]),
        make_chunk("middle", [0.5, 0.5]),
    ]

    results = retrieve([1.0, 0.0], chunks, top_k=3)

    assert [result.chunk_id for result in results] == ["high", "middle", "low"]


def test_retrieve_top_k_can_exceed_chunk_count():
    chunks = [make_chunk("one", [1.0, 0.0])]

    results = retrieve([1.0, 0.0], chunks, top_k=5)

    assert len(results) == 1
    assert results[0].chunk_id == "one"
