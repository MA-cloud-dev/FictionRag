"""JSONL index persistence for chunks and embeddings."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from .chunker import Chunk


class IndexStoreError(RuntimeError):
    """Raised when the local index cannot be read or written."""


def save_chunks(chunks: list[Chunk], index_path: Path) -> None:
    index_path.parent.mkdir(parents=True, exist_ok=True)
    with index_path.open("w", encoding="utf-8") as file:
        for chunk in chunks:
            file.write(json.dumps(asdict(chunk), ensure_ascii=False) + "\n")


def load_chunks(index_path: Path) -> list[Chunk]:
    if not index_path.exists():
        raise IndexStoreError(f"Index file does not exist: {index_path}. Run index first.")

    chunks: list[Chunk] = []
    with index_path.open("r", encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                raw = json.loads(stripped)
                chunks.append(_chunk_from_dict(raw))
            except (json.JSONDecodeError, TypeError, KeyError, ValueError) as exc:
                raise IndexStoreError(
                    f"Invalid index record at line {line_number}: {exc}"
                ) from exc

    if not chunks:
        raise IndexStoreError(f"Index file is empty: {index_path}. Re-run index.")
    return chunks


def _chunk_from_dict(raw: dict[str, Any]) -> Chunk:
    embedding = raw.get("embedding")
    if embedding is not None:
        embedding = [float(value) for value in embedding]

    return Chunk(
        id=str(raw["id"]),
        book_name=str(raw["book_name"]),
        chunk_index=int(raw["chunk_index"]),
        start=int(raw["start"]),
        end=int(raw["end"]),
        text=str(raw["text"]),
        embedding=embedding,
    )
