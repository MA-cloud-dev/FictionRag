"""Structure-aware text chunking for the MVP indexer."""

from __future__ import annotations

from dataclasses import dataclass
import re


DEFAULT_TARGET_CHUNK_SIZE = 800
DEFAULT_MAX_CHUNK_SIZE = 1000
DEFAULT_OVERLAP_PARAGRAPHS = 3

_CHAPTER_PATTERN = re.compile(
    r"^第.+?(?:卷|章)\s+.+?(?:第[一二三四五六七八九十百千万零〇\d]+[话話]|[闲閒][话話]).*$"
    r"|^第[一二三四五六七八九十百千万零〇\d]+[话話]\s*.*$"
    r"|^(?:.+\s+)?(?:序章|终章|終章)$"
    r"|^[闲閒][话話].*$"
    r"|^外[传傳].*$"
)
_SCENE_SEPARATOR = "★★★"
_SENTENCE_BOUNDARY_PATTERN = re.compile(r"(?<=[。！？!?])")


@dataclass(frozen=True)
class Chunk:
    id: str
    book_name: str
    chunk_index: int
    start: int
    end: int
    text: str
    chapter_title: str | None = None
    chapter_index: int = 0
    scene_index: int = 0
    scene_id: str = "scene-000"
    embedding: list[float] | None = None


@dataclass(frozen=True)
class _TextUnit:
    start: int
    end: int
    text: str
    kind: str
    chapter_title: str | None
    chapter_index: int
    scene_index: int
    scene_id: str


@dataclass(frozen=True)
class _ChunkPart:
    start: int
    end: int
    text: str
    chapter_title: str | None
    chapter_index: int
    scene_index: int
    scene_id: str


def split_text(
    text: str,
    chunk_size: int = DEFAULT_TARGET_CHUNK_SIZE,
    overlap: int = DEFAULT_OVERLAP_PARAGRAPHS,
    max_chunk_size: int = DEFAULT_MAX_CHUNK_SIZE,
) -> list[tuple[int, int, str]]:
    """Split text on chapter, scene, and paragraph boundaries.

    ``chunk_size`` is the target chunk size and ``overlap`` is the number of
    trailing paragraphs to repeat into the next chunk within the same scene.
    """

    parts = _split_text_parts(
        text,
        target_chunk_size=chunk_size,
        max_chunk_size=max_chunk_size,
        overlap_paragraphs=overlap,
    )
    return [(part.start, part.end, part.text) for part in parts]


def _split_text_parts(
    text: str,
    target_chunk_size: int = DEFAULT_TARGET_CHUNK_SIZE,
    max_chunk_size: int = DEFAULT_MAX_CHUNK_SIZE,
    overlap_paragraphs: int = DEFAULT_OVERLAP_PARAGRAPHS,
) -> list[_ChunkPart]:
    if target_chunk_size <= 0:
        raise ValueError("target_chunk_size must be greater than 0")
    if max_chunk_size <= 0:
        raise ValueError("max_chunk_size must be greater than 0")
    if target_chunk_size > max_chunk_size:
        raise ValueError("target_chunk_size must be smaller than or equal to max_chunk_size")
    if overlap_paragraphs < 0:
        raise ValueError("overlap_paragraphs must be greater than or equal to 0")
    if not text:
        return []

    chunks: list[_ChunkPart] = []
    current: list[_TextUnit] = []

    for unit in _iter_text_units(text, max_chunk_size=max_chunk_size):
        if unit.kind == "chapter":
            current = _flush_current(chunks, current, overlap_paragraphs=0)
            continue

        if unit.kind == "scene":
            current = _flush_current(chunks, current, overlap_paragraphs=0)
            continue

        if current:
            current_text = _join_units(current)
            next_size = len(current_text) + 2 + len(unit.text)
            if next_size > max_chunk_size or len(current_text) >= target_chunk_size:
                current = _flush_current(
                    chunks,
                    current,
                    overlap_paragraphs=overlap_paragraphs,
                )

        current.append(unit)

    _flush_current(chunks, current, overlap_paragraphs=0)

    return chunks


def build_chunks(
    text: str,
    book_name: str,
    chunk_size: int = DEFAULT_TARGET_CHUNK_SIZE,
    overlap: int = DEFAULT_OVERLAP_PARAGRAPHS,
    max_chunk_size: int = DEFAULT_MAX_CHUNK_SIZE,
) -> list[Chunk]:
    parts = _split_text_parts(
        text,
        target_chunk_size=chunk_size,
        max_chunk_size=max_chunk_size,
        overlap_paragraphs=overlap,
    )
    width = max(6, len(str(len(parts))))

    return [
        Chunk(
            id=f"{book_name}-{index:0{width}d}",
            book_name=book_name,
            chunk_index=index,
            start=part.start,
            end=part.end,
            text=part.text,
            chapter_title=part.chapter_title,
            chapter_index=part.chapter_index,
            scene_index=part.scene_index,
            scene_id=part.scene_id,
        )
        for index, part in enumerate(parts, start=1)
    ]


def _iter_text_units(text: str, max_chunk_size: int) -> list[_TextUnit]:
    units: list[_TextUnit] = []
    chapter_title: str | None = None
    chapter_index = 0
    scene_index = 0
    scene_id = "scene-000"

    for match in re.finditer(r"[^\S\r\n]*(\S[^\r\n]*)", text):
        line = match.group(1).strip()
        start = match.start(1)
        end = match.end(1)

        if _is_chapter_title(line):
            chapter_index += 1
            chapter_title = line
            scene_index = 0
            scene_id = _format_scene_id(chapter_index, scene_index)
            units.append(
                _TextUnit(
                    start=start,
                    end=end,
                    text=line,
                    kind="chapter",
                    chapter_title=chapter_title,
                    chapter_index=chapter_index,
                    scene_index=scene_index,
                    scene_id=scene_id,
                )
            )
            continue

        if line == _SCENE_SEPARATOR:
            scene_index += 1
            scene_id = _format_scene_id(chapter_index, scene_index)
            units.append(
                _TextUnit(
                    start=start,
                    end=end,
                    text=line,
                    kind="scene",
                    chapter_title=chapter_title,
                    chapter_index=chapter_index,
                    scene_index=scene_index,
                    scene_id=scene_id,
                )
            )
            continue

        for sentence_start, sentence_end, sentence_text in _split_long_line(
            line,
            start=start,
            max_chunk_size=max_chunk_size,
        ):
            units.append(
                _TextUnit(
                    start=sentence_start,
                    end=sentence_end,
                    text=sentence_text,
                    kind="paragraph",
                    chapter_title=chapter_title,
                    chapter_index=chapter_index,
                    scene_index=scene_index,
                    scene_id=scene_id,
                )
            )

    return units


def _split_long_line(
    line: str,
    start: int,
    max_chunk_size: int,
) -> list[tuple[int, int, str]]:
    if len(line) <= max_chunk_size:
        return [(start, start + len(line), line)]

    parts: list[tuple[int, int, str]] = []
    current = ""
    current_start = start
    cursor = start

    for sentence in _sentence_parts(line):
        if current and len(current) + len(sentence) > max_chunk_size:
            parts.append((current_start, current_start + len(current), current))
            current_start = cursor
            current = ""

        if len(sentence) <= max_chunk_size:
            current += sentence
            cursor += len(sentence)
            continue

        if current:
            parts.append((current_start, current_start + len(current), current))
            current = ""

        for index in range(0, len(sentence), max_chunk_size):
            fragment = sentence[index : index + max_chunk_size]
            fragment_start = cursor + index
            parts.append((fragment_start, fragment_start + len(fragment), fragment))
        cursor += len(sentence)
        current_start = cursor

    if current:
        parts.append((current_start, current_start + len(current), current))

    return parts


def _sentence_parts(line: str) -> list[str]:
    parts: list[str] = []
    position = 0
    for match in _SENTENCE_BOUNDARY_PATTERN.finditer(line):
        end = match.end()
        parts.append(line[position:end])
        position = end
    if position < len(line):
        parts.append(line[position:])
    return [part for part in parts if part]


def _flush_current(
    chunks: list[_ChunkPart],
    current: list[_TextUnit],
    overlap_paragraphs: int,
) -> list[_TextUnit]:
    if not current:
        return []

    chunks.append(_part_from_units(current))
    if overlap_paragraphs <= 0:
        return []

    tail_count = min(overlap_paragraphs, max(len(current) - 1, 0))
    return current[-tail_count:] if tail_count else []


def _part_from_units(units: list[_TextUnit]) -> _ChunkPart:
    first = units[0]
    last = units[-1]
    return _ChunkPart(
        start=first.start,
        end=last.end,
        text=_join_units(units),
        chapter_title=first.chapter_title,
        chapter_index=first.chapter_index,
        scene_index=first.scene_index,
        scene_id=first.scene_id,
    )


def _join_units(units: list[_TextUnit]) -> str:
    return "\n\n".join(unit.text for unit in units)


def _is_chapter_title(line: str) -> bool:
    return bool(_CHAPTER_PATTERN.match(line))


def _format_scene_id(chapter_index: int, scene_index: int) -> str:
    return f"chapter-{chapter_index:03d}-scene-{scene_index:03d}"
