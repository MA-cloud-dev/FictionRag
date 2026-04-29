from src.chunker import Chunk
from src.retriever import cosine_similarity, retrieve


def make_chunk(
    chunk_id: str,
    embedding: list[float],
    chunk_index: int = 1,
    scene_id: str = "scene-000",
    text: str | None = None,
) -> Chunk:
    return Chunk(
        id=chunk_id,
        book_name="book",
        chunk_index=chunk_index,
        start=0,
        end=1,
        text=text or f"text {chunk_id}",
        scene_id=scene_id,
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


def test_retrieve_without_query_text_keeps_vector_only_sorting():
    chunks = [
        make_chunk("keyword", [0.0, 1.0], text="米里斯银币三枚"),
        make_chunk("vector", [1.0, 0.0], text="unrelated text"),
    ]

    results = retrieve([1.0, 0.0], chunks, top_k=2, query_text=None)

    assert [result.chunk_id for result in results] == ["vector", "keyword"]


def test_retrieve_top_k_can_exceed_chunk_count():
    chunks = [make_chunk("one", [1.0, 0.0])]

    results = retrieve([1.0, 0.0], chunks, top_k=5)

    assert len(results) == 1
    assert results[0].chunk_id == "one"


def test_retrieve_uses_bm25_to_recall_exact_keyword_match():
    chunks = [
        make_chunk("vector", [1.0, 0.0], text="普通的港口旅行段落"),
        make_chunk("keyword", [0.0, 1.0], text="兑换之后，成了米里斯银币三枚。"),
        make_chunk("other", [0.9, 0.0], text="另一段无关文字"),
    ]

    results = retrieve(
        [1.0, 0.0],
        chunks,
        top_k=2,
        vector_top_n=1,
        query_text="米里斯银币三枚",
    )

    assert "keyword" in [result.chunk_id for result in results]


def test_retrieve_deduplicates_vector_and_bm25_hits():
    chunks = [
        make_chunk("both", [1.0, 0.0], text="艾莉丝讲的是流畅的魔神语。"),
        make_chunk("other", [0.0, 1.0], text="普通段落"),
    ]

    results = retrieve(
        [1.0, 0.0],
        chunks,
        top_k=2,
        query_text="艾莉丝使用哪种语言说话 魔神语",
    )

    chunk_ids = [result.chunk_id for result in results]
    assert chunk_ids.count("both") == 1
    assert len(chunk_ids) == len(set(chunk_ids))


def test_retrieve_expands_top_scene_and_neighbor_chunks():
    chunks = [
        make_chunk("two-before", [0.0, 1.0], chunk_index=0, scene_id="scene-a"),
        make_chunk("before", [0.0, 1.0], chunk_index=1, scene_id="scene-a"),
        make_chunk("seed", [1.0, 0.0], chunk_index=2, scene_id="scene-b"),
        make_chunk("same-scene", [0.0, 1.0], chunk_index=3, scene_id="scene-b"),
        make_chunk("neighbor", [0.0, 1.0], chunk_index=4, scene_id="scene-c"),
    ]

    results = retrieve(
        [1.0, 0.0],
        chunks,
        top_k=3,
        vector_top_n=1,
        top_scene_count=1,
        neighbor_radius=1,
    )

    assert [result.chunk_id for result in results] == ["two-before", "before", "seed"]


def test_bm25_seed_participates_in_scene_expansion():
    chunks = [
        make_chunk(
            "two-before",
            [0.92, 0.39],
            chunk_index=1,
            scene_id="scene-b",
            text="普通段落",
        ),
        make_chunk(
            "before",
            [0.0, 1.0],
            chunk_index=2,
            scene_id="scene-b",
            text="前文",
        ),
        make_chunk(
            "seed",
            [0.91, 0.41],
            chunk_index=3,
            scene_id="scene-b",
            text="兑换之后，成了米里斯银币三枚。",
        ),
        make_chunk(
            "after",
            [0.0, 1.0],
            chunk_index=4,
            scene_id="scene-b",
            text="后文",
        ),
    ]

    results = retrieve(
        [1.0, 0.0],
        chunks,
        top_k=3,
        vector_top_n=2,
        top_scene_count=1,
        neighbor_radius=1,
        query_text="米里斯银币三枚",
    )

    assert [result.chunk_id for result in results] == ["two-before", "before", "seed"]
