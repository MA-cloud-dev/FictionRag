import pytest

from src.chunker import split_text


def test_empty_text_returns_no_chunks():
    assert split_text("") == []


def test_split_text_uses_fixed_size_and_overlap():
    text = "".join(str(index % 10) for index in range(2500))

    chunks = split_text(text, chunk_size=1000, overlap=200)

    assert len(chunks) == 4
    assert chunks[0][0] == 0
    assert chunks[0][1] == 1000
    assert chunks[1][0] == 800
    assert chunks[1][1] == 1800
    assert chunks[0][2][-200:] == chunks[1][2][:200]


def test_overlap_must_be_smaller_than_chunk_size():
    with pytest.raises(ValueError, match="overlap"):
        split_text("abc", chunk_size=1000, overlap=1000)
