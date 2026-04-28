import pytest

from src.chunker import build_chunks, split_text


def test_empty_text_returns_no_chunks():
    assert split_text("") == []


def test_build_chunks_uses_chapter_and_scene_metadata():
    text = "\n\n".join(
        [
            "第四卷 少年期冒险者入门篇 第一话「温恩港」",
            "温恩港。",
            "这里是魔大陆唯一的港都。",
            "★★★",
            "我们决定前往冒险者公会。",
        ]
    )

    chunks = build_chunks(text, book_name="book", chunk_size=20, max_chunk_size=40, overlap=1)

    assert len(chunks) == 2
    assert chunks[0].chapter_title == "第四卷 少年期冒险者入门篇 第一话「温恩港」"
    assert chunks[0].chapter_index == 1
    assert chunks[0].scene_index == 0
    assert chunks[0].scene_id == "chapter-001-scene-000"
    assert "第四卷" not in chunks[0].text
    assert "★★★" not in chunks[0].text
    assert chunks[1].scene_index == 1
    assert chunks[1].scene_id == "chapter-001-scene-001"


def test_split_text_keeps_scene_boundaries():
    text = "\n\n".join(
        [
            "第一话「测试」",
            "aaa",
            "bbb",
            "ccc",
            "ddd",
            "★★★",
            "eee",
        ]
    )

    chunks = split_text(text, chunk_size=15, max_chunk_size=20, overlap=3)

    assert len(chunks) == 2
    assert chunks[0][2] == "aaa\n\nbbb\n\nccc\n\nddd"
    assert chunks[1][2] == "eee"


def test_split_text_overlaps_last_three_paragraphs_within_scene():
    text = "\n\n".join(["第一话「测试」", "aaa", "bbb", "ccc", "ddd", "eee"])

    chunks = split_text(text, chunk_size=15, max_chunk_size=20, overlap=3)

    assert len(chunks) == 2
    assert chunks[0][2] == "aaa\n\nbbb\n\nccc\n\nddd"
    assert chunks[1][2] == "bbb\n\nccc\n\nddd\n\neee"


def test_long_paragraph_falls_back_to_sentence_splitting():
    text = "\n\n".join(
        [
            "第一话「测试」",
            "一二三四五。六七八九十。十一十二十三十四十五。",
        ]
    )

    chunks = split_text(text, chunk_size=8, max_chunk_size=10, overlap=0)

    assert [chunk[2] for chunk in chunks] == [
        "一二三四五。",
        "六七八九十。",
        "十一十二十三十四十五",
        "。",
    ]
    assert all(len(chunk[2]) <= 10 for chunk in chunks)


def test_target_chunk_size_must_not_exceed_max_chunk_size():
    with pytest.raises(ValueError, match="target_chunk_size"):
        split_text("abc", chunk_size=1001, max_chunk_size=1000)
