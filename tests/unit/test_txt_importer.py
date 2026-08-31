"""Tests for conservative plain-text importing."""

from collections.abc import Iterator

from memory_typing.core.txt_importer import TxtImporter


def sequential_ids() -> Iterator[str]:
    index = 0
    while True:
        yield f"id-{index}"
        index += 1


def make_importer() -> TxtImporter:
    ids = sequential_ids()
    return TxtImporter(id_factory=lambda: next(ids))


def test_korean_blank_line_separated_paragraphs_preserve_order() -> None:
    source = "첫 번째 문단입니다. 기억을 연습합니다.\n\n두 번째 문단입니다."
    book = make_importer().import_text(source, title="기억 연습")
    chapter = book.chapters[0]

    assert book.original_text == source
    assert chapter.original_text == source
    assert [paragraph.source_order for paragraph in chapter.paragraphs] == [0, 1]
    assert [paragraph.original_text for paragraph in chapter.paragraphs] == [
        "첫 번째 문단입니다. 기억을 연습합니다.",
        "두 번째 문단입니다.",
    ]


def test_korean_punctuation_splits_sentences_conservatively() -> None:
    source = "정말 기억할까? 그렇다! 반복하면 강화된다."
    paragraph = make_importer().import_text(source, title="한국어").chapters[0].paragraphs[0]

    assert [sentence.original_text for sentence in paragraph.sentences] == [
        "정말 기억할까?",
        " 그렇다!",
        " 반복하면 강화된다.",
    ]
    assert "".join(sentence.original_text for sentence in paragraph.sentences) == source


def test_english_punctuation_is_preserved() -> None:
    source = "Memory grows. Does repetition help? Yes, it does!"
    sentences = (
        make_importer().import_text(source, title="English").chapters[0].paragraphs[0].sentences
    )

    assert [sentence.original_text for sentence in sentences] == [
        "Memory grows.",
        " Does repetition help?",
        " Yes, it does!",
    ]


def test_commas_and_semicolons_do_not_split_sentences() -> None:
    source = "첫째, 서두르지 않는다; 둘째, 원문을 보존한다."
    sentences = (
        make_importer().import_text(source, title="보수적 분리").chapters[0].paragraphs[0].sentences
    )

    assert len(sentences) == 1
    assert sentences[0].original_text == source


def test_mixed_language_and_internal_spacing_are_preserved() -> None:
    source = "기억은  Memory와 연결된다.\n다음 line도  그대로다."
    paragraph = make_importer().import_text(source, title="혼합").chapters[0].paragraphs[0]

    assert paragraph.original_text == source
    assert "".join(sentence.original_text for sentence in paragraph.sentences) == source


def test_blank_lines_with_horizontal_whitespace_separate_paragraphs() -> None:
    source = "앞 문단\n \t\n뒤 문단\n\n\n마지막 문단"
    paragraphs = make_importer().import_text(source, title="빈 줄").chapters[0].paragraphs

    assert [paragraph.original_text for paragraph in paragraphs] == [
        "앞 문단",
        "뒤 문단",
        "마지막 문단",
    ]


def test_leading_and_trailing_whitespace_inside_paragraph_is_preserved() -> None:
    source = "  들여쓰기 문장.  다음 문장.  "
    paragraph = make_importer().import_text(source, title="공백").chapters[0].paragraphs[0]

    assert paragraph.original_text == source
    assert "".join(sentence.original_text for sentence in paragraph.sentences) == source
    assert paragraph.sentences[0].original_text.startswith("  ")
    assert paragraph.sentences[-1].original_text.endswith("  ")


def test_empty_file_creates_book_and_chapter_without_paragraphs() -> None:
    book = make_importer().import_text("", title="빈 파일")

    assert book.original_text == ""
    assert len(book.chapters) == 1
    assert book.chapters[0].paragraphs == ()


def test_all_entities_receive_unique_stable_ids() -> None:
    book = make_importer().import_text("첫 문장. 둘째 문장.\n\n새 문단.", title="ID")
    chapter = book.chapters[0]
    paragraphs = chapter.paragraphs
    sentences = tuple(sentence for paragraph in paragraphs for sentence in paragraph.sentences)
    ids = [book.id, chapter.id]
    ids.extend(paragraph.id for paragraph in paragraphs)
    ids.extend(sentence.id for sentence in sentences)

    assert len(ids) == len(set(ids))
    assert set(ids) == {f"id-{index}" for index in range(len(ids))}
    assert [sentence.source_order for sentence in paragraphs[0].sentences] == [0, 1]


def test_import_file_preserves_crlf_and_uses_filename_as_title(tmp_path) -> None:
    path = tmp_path / "나의 책.txt"
    raw_source = "첫 문단.\r\n\r\n둘째 문단."
    path.write_bytes(raw_source.encode("utf-8"))

    book = make_importer().import_file(path)

    assert book.title == "나의 책"
    assert book.original_text == raw_source
    assert [paragraph.original_text for paragraph in book.chapters[0].paragraphs] == [
        "첫 문단.",
        "둘째 문단.",
    ]
