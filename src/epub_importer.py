"""EPUB-to-text import helpers for novel sources."""

from __future__ import annotations

from html.parser import HTMLParser
import posixpath
import re
import unicodedata
from pathlib import Path
from typing import Iterable
from xml.etree import ElementTree
from zipfile import ZipFile


_HTML_EXTENSIONS = (".html", ".htm", ".xhtml")
_SKIPPED_NAME_PARTS = {
    "backcover",
    "cover",
    "illustration",
    "introduction",
    "logo",
    "message",
    "title",
}
_SKIPPED_STEMS = {"chapter00"}
_SCENE_SEPARATOR_PATTERN = re.compile(r"^★(?:\s*★){2,}$")
_NATURAL_PART_PATTERN = re.compile(r"(\d+)")
_CREDIT_PREFIXES = (
    "作者",
    "插画",
    "插畫",
    "台版",
    "网译版",
    "转自",
    "图源",
    "扫图",
    "录入",
    "錄入",
    "修图",
    "校对",
    "翻译",
    "译者",
    "譯者",
    "轻之国度",
    "輕之國度",
    "购书人",
    "深夜读书会",
    "读书群",
    "仅供",
    "僅供",
    "下载",
    "下載",
    "请尊重",
    "請尊重",
)
_IMPORT_CHAPTER_PATTERN = re.compile(
    r"^第.+?(?:卷|章)\s+.+?(?:第[一二三四五六七八九十百千万零〇\d]+[话話]|[闲閒][话話]).*$"
    r"|^第[一二三四五六七八九十百千万零〇\d]+[话話]\s*.*$"
    r"|^(?:.+\s+)?(?:序章|终章|終章)$"
    r"|^[闲閒][话話].*$"
    r"|^外[传傳].*$"
)


class EpubImportError(RuntimeError):
    """Raised when an EPUB cannot be imported as clean text."""


class _BlockTextParser(HTMLParser):
    _BLOCK_TAGS = {
        "address",
        "article",
        "aside",
        "blockquote",
        "br",
        "dd",
        "div",
        "dl",
        "dt",
        "figcaption",
        "footer",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "header",
        "hr",
        "li",
        "main",
        "nav",
        "ol",
        "p",
        "pre",
        "section",
        "table",
        "td",
        "th",
        "tr",
        "ul",
    }
    _IGNORED_TAGS = {"head", "script", "style", "svg"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.paragraphs: list[str] = []
        self._current: list[str] = []
        self._ignored_depth = 0

    def handle_starttag(self, tag: str, attrs) -> None:
        tag = tag.lower()
        if tag in self._IGNORED_TAGS:
            self._ignored_depth += 1
            return
        if tag in self._BLOCK_TAGS:
            self._flush()

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in self._IGNORED_TAGS and self._ignored_depth:
            self._ignored_depth -= 1
            return
        if tag in self._BLOCK_TAGS:
            self._flush()

    def handle_data(self, data: str) -> None:
        if self._ignored_depth:
            return
        text = _normalize_inline_text(data)
        if text:
            self._current.append(text)

    def close(self) -> None:
        super().close()
        self._flush()

    def _flush(self) -> None:
        if not self._current:
            return
        paragraph = _normalize_paragraph("".join(self._current))
        if paragraph:
            self.paragraphs.append(paragraph)
        self._current.clear()


def import_epub_to_text(
    epub_path: Path,
    output_path: Path,
    include_prefix: str | None = None,
) -> tuple[int, int]:
    """Extract clean plain text from ``epub_path`` and write it to ``output_path``."""
    text = extract_epub_text(epub_path, include_prefix=include_prefix)
    if not text:
        raise EpubImportError(f"No importable text found in EPUB: {epub_path}")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(text, encoding="utf-8")
    paragraph_count = len([part for part in text.split("\n\n") if part.strip()])
    return paragraph_count, len(text)


def extract_epub_text(epub_path: Path, include_prefix: str | None = None) -> str:
    if not epub_path.exists():
        raise FileNotFoundError(f"EPUB file does not exist: {epub_path}")
    if not epub_path.is_file():
        raise ValueError(f"EPUB path is not a file: {epub_path}")

    with ZipFile(epub_path) as archive:
        html_paths = _ordered_html_paths(archive)
        paragraphs: list[str] = []
        previous: str | None = None
        for html_path in html_paths:
            if _should_skip_html_path(html_path):
                continue
            raw = archive.read(html_path)
            document_paragraphs = _extract_html_paragraphs(raw)
            if _should_skip_document(document_paragraphs):
                continue
            if include_prefix and not _document_matches_prefix(
                document_paragraphs,
                include_prefix,
            ):
                continue
            for paragraph in document_paragraphs:
                if paragraph == previous:
                    continue
                paragraphs.append(paragraph)
                previous = paragraph

    paragraphs = _trim_front_matter(_drop_table_of_contents(paragraphs))
    return "\n\n".join(paragraphs).strip() + "\n" if paragraphs else ""


def _ordered_html_paths(archive: ZipFile) -> list[str]:
    paths = _spine_html_paths(archive)
    if paths:
        return paths

    names = [
        name
        for name in archive.namelist()
        if name.lower().endswith(_HTML_EXTENSIONS) and "/text/" in name.lower()
    ]
    return sorted(names, key=_natural_sort_key)


def _spine_html_paths(archive: ZipFile) -> list[str]:
    rootfile_path = _rootfile_path(archive)
    if rootfile_path is None:
        return []

    try:
        opf_root = ElementTree.fromstring(archive.read(rootfile_path))
    except ElementTree.ParseError as exc:
        raise EpubImportError(f"Invalid OPF XML in {rootfile_path}: {exc}") from exc

    manifest: dict[str, str] = {}
    for item in _iter_by_local_name(opf_root, "item"):
        item_id = item.attrib.get("id")
        href = item.attrib.get("href")
        if item_id and href:
            manifest[item_id] = posixpath.normpath(
                posixpath.join(posixpath.dirname(rootfile_path), href)
            )

    ordered: list[str] = []
    names = set(archive.namelist())
    for itemref in _iter_by_local_name(opf_root, "itemref"):
        idref = itemref.attrib.get("idref")
        href = manifest.get(idref or "")
        if href and href in names and href.lower().endswith(_HTML_EXTENSIONS):
            ordered.append(href)
    return ordered


def _rootfile_path(archive: ZipFile) -> str | None:
    if "META-INF/container.xml" not in archive.namelist():
        return None
    try:
        root = ElementTree.fromstring(archive.read("META-INF/container.xml"))
    except ElementTree.ParseError as exc:
        raise EpubImportError(f"Invalid container.xml: {exc}") from exc

    for rootfile in _iter_by_local_name(root, "rootfile"):
        full_path = rootfile.attrib.get("full-path")
        if full_path:
            return full_path
    return None


def _iter_by_local_name(root: ElementTree.Element, local_name: str) -> Iterable[ElementTree.Element]:
    for element in root.iter():
        if element.tag.rsplit("}", 1)[-1] == local_name:
            yield element


def _should_skip_html_path(path: str) -> bool:
    lower_path = path.lower()
    stem = Path(lower_path).stem
    if stem in _SKIPPED_STEMS:
        return True
    return any(part in lower_path for part in _SKIPPED_NAME_PARTS)


def _extract_html_paragraphs(raw: bytes) -> list[str]:
    content = raw.decode("utf-8", errors="ignore")
    parser = _BlockTextParser()
    parser.feed(content)
    parser.close()
    return _merge_leading_arc_title(parser.paragraphs)


def _merge_leading_arc_title(paragraphs: list[str]) -> list[str]:
    if len(paragraphs) < 2:
        return paragraphs

    first = paragraphs[0]
    second = paragraphs[1]
    if _looks_like_arc_title(first) and _looks_like_chapter_title(second):
        return [f"{first} {second}"] + paragraphs[2:]
    return paragraphs


def _looks_like_arc_title(text: str) -> bool:
    return len(text) <= 30 and ("期" in text or "篇" in text)


def _looks_like_chapter_title(text: str) -> bool:
    return bool(_IMPORT_CHAPTER_PATTERN.match(text))


def _trim_front_matter(paragraphs: list[str]) -> list[str]:
    """Drop leading blurbs, tables of contents, and credits before body text."""
    for index, paragraph in enumerate(paragraphs):
        if _looks_like_chapter_title(paragraph):
            return paragraphs[index:]
    return paragraphs


def _drop_table_of_contents(paragraphs: list[str]) -> list[str]:
    cleaned: list[str] = []
    in_toc = False
    toc_titles: set[str] = set()

    for paragraph in paragraphs:
        if _is_toc_heading(paragraph):
            in_toc = True
            toc_titles.clear()
            continue

        if in_toc:
            normalized_title = _normalize_toc_title(paragraph)
            if _looks_like_chapter_title(paragraph):
                if normalized_title in toc_titles:
                    in_toc = False
                    cleaned.append(paragraph)
                else:
                    toc_titles.add(normalized_title)
                continue
            in_toc = False

        cleaned.append(paragraph)

    return cleaned


def _is_toc_heading(text: str) -> bool:
    normalized = unicodedata.normalize("NFKC", text).strip().upper()
    return normalized in {"CONTENTS", "目录", "目錄"}


def _normalize_toc_title(text: str) -> str:
    return re.sub(r"\s+", "", text)


def _should_skip_document(paragraphs: list[str]) -> bool:
    if not paragraphs:
        return True
    first = unicodedata.normalize("NFKC", paragraphs[0]).strip().upper()
    return first in {"CONTENTS", "目录", "目錄"}


def _document_matches_prefix(paragraphs: list[str], include_prefix: str) -> bool:
    prefix = include_prefix.strip()
    if not prefix:
        return True
    return any(paragraph.startswith(prefix) for paragraph in paragraphs[:3])


def _normalize_inline_text(text: str) -> str:
    text = text.replace("\xa0", " ").replace("\u3000", " ")
    return re.sub(r"\s+", " ", text).strip()


def _normalize_paragraph(text: str) -> str:
    text = text.replace("\xa0", " ").replace("\u3000", " ")
    text = re.sub(r"\s+", " ", text).strip()
    if _is_credit_line(text):
        return ""
    if _SCENE_SEPARATOR_PATTERN.match(text):
        return "★★★"
    return text


def _is_credit_line(text: str) -> bool:
    if not text:
        return False
    return text.startswith(_CREDIT_PREFIXES)


def _natural_sort_key(value: str) -> list[int | str]:
    return [
        int(part) if part.isdigit() else part.lower()
        for part in _NATURAL_PART_PATTERN.split(value)
    ]
