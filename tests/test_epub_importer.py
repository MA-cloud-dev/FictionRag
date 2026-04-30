from pathlib import Path
from zipfile import ZipFile

from src.epub_importer import extract_epub_text, import_epub_to_text


def write_minimal_epub(path: Path, chapter2_html: str | None = None) -> None:
    container_xml = """<?xml version="1.0" encoding="UTF-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
    <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>
"""
    opf = """<?xml version="1.0" encoding="UTF-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0">
    <manifest>
    <item id="title" href="Text/title.xhtml" media-type="application/xhtml+xml"/>
    <item id="toc" href="Text/toc.xhtml" media-type="application/xhtml+xml"/>
    <item id="intro" href="Text/introduction.xhtml" media-type="application/xhtml+xml"/>
    <item id="chapter2" href="Text/chapter2.xhtml" media-type="application/xhtml+xml"/>
    <item id="chapter1" href="Text/chapter1.xhtml" media-type="application/xhtml+xml"/>
    <item id="message" href="Text/message.xhtml" media-type="application/xhtml+xml"/>
  </manifest>
  <spine>
    <itemref idref="title"/>
    <itemref idref="toc"/>
    <itemref idref="chapter2"/>
    <itemref idref="chapter1"/>
    <itemref idref="intro"/>
    <itemref idref="message"/>
  </spine>
</package>
"""
    with ZipFile(path, "w") as archive:
        archive.writestr("mimetype", "application/epub+zip")
        archive.writestr("META-INF/container.xml", container_xml)
        archive.writestr("OEBPS/content.opf", opf)
        archive.writestr("OEBPS/Text/title.xhtml", "<h1>标题</h1><p>作者信息</p>")
        archive.writestr("OEBPS/Text/toc.xhtml", "<h1>ＣＯＮＴＥＮＴＳ</h1><p>目录项</p>")
        archive.writestr("OEBPS/Text/introduction.xhtml", "<h1>简介</h1><p>广告文案</p>")
        archive.writestr("OEBPS/Text/message.xhtml", "<h1>制作信息</h1><p>请勿商业使用</p>")
        archive.writestr(
            "OEBPS/Text/chapter1.xhtml",
            "<h1>第一话「后到章节」</h1><p>图源：测试</p><p>第一段。</p><p>★ ★ ★</p><p>第二段。</p>",
        )
        archive.writestr(
            "OEBPS/Text/chapter2.xhtml",
            chapter2_html or "<h1>第二话「先到章节」</h1><p>第三段。</p>",
        )


def test_extract_epub_text_merges_leading_arc_and_chapter_titles(tmp_path: Path):
    epub_path = tmp_path / "book.epub"
    write_minimal_epub(
        epub_path,
        chapter2_html="<h1>少年期 家庭教师</h1><h2>序章</h2><p>正文。</p>",
    )

    text = extract_epub_text(epub_path)

    assert "少年期 家庭教师 序章" in text


def test_extract_epub_text_uses_spine_order_and_filters_front_matter(tmp_path: Path):
    epub_path = tmp_path / "book.epub"
    write_minimal_epub(epub_path)

    text = extract_epub_text(epub_path)

    assert "标题" not in text
    assert "目录项" not in text
    assert "简介" not in text
    assert "制作信息" not in text
    assert "图源" not in text
    assert text.index("第二话") < text.index("第一话")
    assert "★★★" in text


def test_import_epub_to_text_writes_clean_text(tmp_path: Path):
    epub_path = tmp_path / "book.epub"
    output_path = tmp_path / "book.txt"
    write_minimal_epub(epub_path)

    paragraph_count, character_count = import_epub_to_text(epub_path, output_path)

    assert output_path.exists()
    assert paragraph_count == 6
    assert character_count == len(output_path.read_text(encoding="utf-8"))


def test_extract_epub_text_can_filter_by_prefix(tmp_path: Path):
    epub_path = tmp_path / "book.epub"
    write_minimal_epub(epub_path)

    text = extract_epub_text(epub_path, include_prefix="第一话")

    assert "第一话「后到章节」" in text
    assert "第二话「先到章节」" not in text


def test_extract_epub_text_trims_intro_and_contents_before_first_chapter(tmp_path: Path):
    epub_path = tmp_path / "book.epub"
    write_minimal_epub(
        epub_path,
        chapter2_html=(
            "<h1>简介</h1><p>宣传文案。</p><p>CONTENTS</p>"
            "<p>第一话「正文标题」</p><p>第二话「目录项」</p>"
            "<h2>第一话 「正文标题」</h2><p>正文。</p>"
        ),
    )

    text = extract_epub_text(epub_path)

    assert text.startswith("第一话 「正文标题」")
    assert "简介" not in text
    assert "宣传文案" not in text
    assert "CONTENTS" not in text
    assert "第二话「目录项」" not in text
