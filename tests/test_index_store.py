from pathlib import Path

from src.chunker import Chunk
from src.index_store import load_chunks, save_chunks


def test_save_and_load_chunks_round_trip(tmp_path: Path):
    index_path = tmp_path / "chunks.jsonl"
    chunks = [
        Chunk(
            id="book-000001",
            book_name="book",
            chunk_index=1,
            start=0,
            end=3,
            text="abc",
            embedding=[0.1, 0.2],
        )
    ]

    save_chunks(chunks, index_path)
    loaded = load_chunks(index_path)

    assert loaded == chunks


def test_save_chunks_overwrites_existing_index(tmp_path: Path):
    index_path = tmp_path / "chunks.jsonl"
    first = [
        Chunk(
            id="book-000001",
            book_name="book",
            chunk_index=1,
            start=0,
            end=3,
            text="abc",
            embedding=[0.1],
        )
    ]
    second = [
        Chunk(
            id="book-000002",
            book_name="book",
            chunk_index=2,
            start=3,
            end=6,
            text="def",
            embedding=[0.2],
        )
    ]

    save_chunks(first, index_path)
    save_chunks(second, index_path)
    loaded = load_chunks(index_path)

    assert loaded == second
