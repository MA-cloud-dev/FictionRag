"""Fixed-size text chunking for the MVP indexer."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Chunk:
    id: str
    book_name: str
    chunk_index: int
    start: int
    end: int
    text: str
    embedding: list[float] | None = None


def split_text(text: str, chunk_size: int = 1000, overlap: int = 200) -> list[tuple[int, int, str]]:
    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than 0")
    if overlap < 0:
        raise ValueError("overlap must be greater than or equal to 0")
    if overlap >= chunk_size:
        raise ValueError("overlap must be smaller than chunk_size")
    if not text:
        return []

    chunks: list[tuple[int, int, str]] = []
    step = chunk_size - overlap
    start = 0

    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunks.append((start, end, text[start:end]))
        start += step

    return chunks


def build_chunks(
    text: str,
    book_name: str,
    chunk_size: int = 1000,
    overlap: int = 200,
) -> list[Chunk]:
    parts = split_text(text, chunk_size=chunk_size, overlap=overlap)
    width = max(6, len(str(len(parts))))

    return [
        Chunk(
            id=f"{book_name}-{index:0{width}d}",
            book_name=book_name,
            chunk_index=index,
            start=start,
            end=end,
            text=chunk_text,
        )
        for index, (start, end, chunk_text) in enumerate(parts, start=1)
    ]
