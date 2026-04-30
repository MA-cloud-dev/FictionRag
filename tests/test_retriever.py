from src.chunker import Chunk
from src.retriever import build_bm25_index, cosine_similarity, retrieve


def make_chunk(
    chunk_id: str,
    embedding: list[float],
    chunk_index: int = 1,
    scene_id: str = "scene-000",
    text: str | None = None,
    book_name: str = "book",
) -> Chunk:
    return Chunk(
        id=chunk_id,
        book_name=book_name,
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


def test_retrieve_accepts_reusable_bm25_index():
    chunks = [
        make_chunk("vector", [1.0, 0.0], text="普通的港口旅行段落"),
        make_chunk("keyword", [0.0, 1.0], text="兑换之后，成了米里斯银币三枚。"),
    ]
    bm25_index = build_bm25_index(chunks)

    results = retrieve(
        [1.0, 0.0],
        chunks,
        top_k=2,
        vector_top_n=1,
        query_text="米里斯银币三枚",
        bm25_index=bm25_index,
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


def test_rescue_slot_preserves_top_four_and_replaces_only_fifth():
    chunks = [
        make_chunk("one", [1.0, 0.0], chunk_index=1, scene_id="scene-a", text="普通段落一"),
        make_chunk("two", [1.0, 0.0], chunk_index=2, scene_id="scene-a", text="普通段落二"),
        make_chunk("three", [1.0, 0.0], chunk_index=3, scene_id="scene-a", text="普通段落三"),
        make_chunk("four", [1.0, 0.0], chunk_index=4, scene_id="scene-a", text="普通段落四"),
        make_chunk("five", [1.0, 0.0], chunk_index=5, scene_id="scene-a", text="普通段落五"),
        make_chunk(
            "rescue",
            [0.0, 1.0],
            chunk_index=10,
            scene_id="scene-b",
            text="线索显示小偷留下痕迹，瑞杰路德追上去教训了对方。",
        ),
    ]

    results = retrieve(
        [1.0, 0.0],
        chunks,
        top_k=5,
        vector_top_n=5,
        top_scene_count=1,
        query_text="是谁发现小偷的痕迹并追上去教训了对方",
    )

    assert [result.chunk_id for result in results] == [
        "one",
        "two",
        "three",
        "four",
        "rescue",
    ]


def test_rescue_slot_keeps_fifth_without_strong_evidence():
    chunks = [
        make_chunk("one", [1.0, 0.0], chunk_index=1, scene_id="scene-a", text="普通段落一"),
        make_chunk("two", [1.0, 0.0], chunk_index=2, scene_id="scene-a", text="普通段落二"),
        make_chunk("three", [1.0, 0.0], chunk_index=3, scene_id="scene-a", text="普通段落三"),
        make_chunk("four", [1.0, 0.0], chunk_index=4, scene_id="scene-a", text="普通段落四"),
        make_chunk("five", [1.0, 0.0], chunk_index=5, scene_id="scene-a", text="普通段落五"),
        make_chunk("weak", [0.0, 1.0], chunk_index=10, scene_id="scene-b", text="没有相关线索"),
    ]

    results = retrieve(
        [1.0, 0.0],
        chunks,
        top_k=5,
        vector_top_n=5,
        top_scene_count=1,
        query_text="是谁发现小偷的痕迹并追上去教训了对方",
    )

    assert [result.chunk_id for result in results] == [
        "one",
        "two",
        "three",
        "four",
        "five",
    ]


def test_scene_expansion_does_not_merge_same_scene_id_across_books():
    chunks = [
        make_chunk(
            "book-a-seed",
            [1.0, 0.0],
            chunk_index=1,
            scene_id="chapter-001-scene-000",
            book_name="book-a",
        ),
        make_chunk(
            "book-a-after",
            [0.9, 0.1],
            chunk_index=2,
            scene_id="chapter-001-scene-000",
            book_name="book-a",
        ),
        make_chunk(
            "book-b-same-scene",
            [0.8, 0.2],
            chunk_index=1,
            scene_id="chapter-001-scene-000",
            book_name="book-b",
        ),
    ]

    results = retrieve(
        [1.0, 0.0],
        chunks,
        top_k=3,
        vector_top_n=1,
        top_scene_count=1,
        book_route_count=0,
    )

    assert [result.chunk_id for result in results] == ["book-a-seed", "book-a-after"]


def test_neighbor_expansion_does_not_cross_books_with_same_chunk_index():
    chunks = [
        make_chunk(
            "book-a-before",
            [0.7, 0.3],
            chunk_index=1,
            scene_id="scene-a",
            book_name="book-a",
        ),
        make_chunk(
            "book-a-seed",
            [1.0, 0.0],
            chunk_index=2,
            scene_id="scene-a",
            book_name="book-a",
        ),
        make_chunk(
            "book-b-before",
            [0.6, 0.4],
            chunk_index=1,
            scene_id="scene-b",
            book_name="book-b",
        ),
        make_chunk(
            "book-b-after",
            [0.5, 0.5],
            chunk_index=3,
            scene_id="scene-b",
            book_name="book-b",
        ),
    ]

    results = retrieve(
        [1.0, 0.0],
        chunks,
        top_k=3,
        vector_top_n=1,
        top_scene_count=1,
        neighbor_before=1,
        neighbor_after=1,
        book_route_count=0,
    )

    assert [result.chunk_id for result in results] == ["book-a-before", "book-a-seed"]


def test_book_routing_caps_single_book_dominance():
    chunks = [
        make_chunk(
            f"book-a-{index}",
            [1.0 - index * 0.01, index * 0.01],
            chunk_index=index,
            book_name="book-a",
        )
        for index in range(1, 7)
    ] + [
        make_chunk("book-b-hit", [0.8, 0.2], chunk_index=1, book_name="book-b"),
        make_chunk("book-c-hit", [0.7, 0.3], chunk_index=1, book_name="book-c"),
    ]

    results = retrieve(
        [1.0, 0.0],
        chunks,
        top_k=5,
        book_route_count=3,
        book_result_cap=3,
    )

    assert sum(result.chunk.book_name == "book-a" for result in results) == 3
    assert "book-b-hit" in [result.chunk_id for result in results]


def test_book_routing_still_expands_scene_within_selected_book():
    chunks = [
        make_chunk(
            "book-a-seed",
            [1.0, 0.0],
            chunk_index=2,
            scene_id="scene-a",
            book_name="book-a",
        ),
        make_chunk(
            "book-a-after",
            [0.8, 0.2],
            chunk_index=3,
            scene_id="scene-a",
            book_name="book-a",
        ),
        make_chunk(
            "book-b-seed",
            [0.9, 0.1],
            chunk_index=1,
            scene_id="scene-b",
            book_name="book-b",
        ),
    ]

    results = retrieve(
        [1.0, 0.0],
        chunks,
        top_k=3,
        vector_top_n=1,
        top_scene_count=1,
        neighbor_before=0,
        neighbor_after=1,
        book_route_count=1,
    )

    assert [result.chunk_id for result in results] == ["book-a-seed", "book-a-after"]
