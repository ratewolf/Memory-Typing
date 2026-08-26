"""Unit tests for explicit JSON content importing."""

import json
from collections.abc import Callable
from typing import Any

import pytest

from memory_typing.core import JsonImporter, JsonImportError


def valid_data() -> dict[str, Any]:
    return {
        "format_version": 1,
        "book": {
            "id": "book-memory",
            "title": "기억 연습",
            "chapters": [
                {
                    "id": "chapter-one",
                    "title": "첫 장",
                    "paragraphs": [
                        {
                            "id": "paragraph-one",
                            "sentences": [
                                {"id": "sentence-one", "text": "첫 문장이다."},
                                {"id": "sentence-two", "text": "구두점 없이도 경계가 분명하다"},
                            ],
                        },
                        {
                            "id": "paragraph-two",
                            "sentences": [
                                {"id": "sentence-three", "text": "한글과 English,  공백!"}
                            ],
                        },
                    ],
                },
                {"id": "chapter-two", "title": "둘째 장", "paragraphs": []},
            ],
        },
    }


def test_explicit_arrays_define_hierarchy_boundaries_and_source_order() -> None:
    book = JsonImporter().import_data(valid_data())

    assert book.id == "book-memory"
    assert [chapter.id for chapter in book.chapters] == ["chapter-one", "chapter-two"]
    first_chapter = book.chapters[0]
    assert [paragraph.source_order for paragraph in first_chapter.paragraphs] == [0, 1]
    assert [sentence.source_order for sentence in first_chapter.paragraphs[0].sentences] == [0, 1]
    assert [sentence.original_text for sentence in first_chapter.paragraphs[0].sentences] == [
        "첫 문장이다.",
        "구두점 없이도 경계가 분명하다",
    ]


def test_parent_original_text_is_normalized_from_explicit_sentences() -> None:
    book = JsonImporter().import_data(valid_data())
    first_chapter = book.chapters[0]

    assert first_chapter.paragraphs[0].original_text == (
        "첫 문장이다. 구두점 없이도 경계가 분명하다"
    )
    assert first_chapter.original_text == (
        "첫 문장이다. 구두점 없이도 경계가 분명하다\n\n한글과 English,  공백!"
    )
    assert book.original_text == first_chapter.original_text


def test_ids_and_parent_references_are_stable_and_explicit() -> None:
    first = JsonImporter().import_data(valid_data())
    second = JsonImporter().import_data(valid_data())
    sentence = first.chapters[0].paragraphs[0].sentences[0]

    assert first == second
    assert first.chapters[0].book_id == first.id
    assert first.chapters[0].paragraphs[0].chapter_id == first.chapters[0].id
    assert sentence.paragraph_id == first.chapters[0].paragraphs[0].id


def test_import_file_reads_utf8_json(tmp_path) -> None:
    path = tmp_path / "책.json"
    path.write_text(json.dumps(valid_data(), ensure_ascii=False), encoding="utf-8")

    book = JsonImporter().import_file(path)

    assert book.title == "기억 연습"
    assert book.chapters[0].paragraphs[1].sentences[0].original_text == ("한글과 English,  공백!")


@pytest.mark.parametrize("text", [" 앞 공백", "뒤 공백 ", "\t탭", "줄바꿈\n"])
def test_sentence_edge_whitespace_is_rejected(text: str) -> None:
    data = valid_data()
    data["book"]["chapters"][0]["paragraphs"][0]["sentences"][0]["text"] = text

    with pytest.raises(JsonImportError, match="앞뒤에는 공백"):
        JsonImporter().import_data(data)


@pytest.mark.parametrize("text", ["", "   "])
def test_empty_sentence_is_rejected(text: str) -> None:
    data = valid_data()
    data["book"]["chapters"][0]["paragraphs"][0]["sentences"][0]["text"] = text

    with pytest.raises(JsonImportError, match="비어 있지 않은 문자열"):
        JsonImporter().import_data(data)


def test_punctuation_does_not_change_explicit_sentence_boundaries() -> None:
    data = valid_data()
    sentences = data["book"]["chapters"][0]["paragraphs"][0]["sentences"]
    sentences[0]["text"] = "마침표가 둘이다. 그래도 한 문장이다."
    sentences[1]["text"] = "종결 부호가 없어도 별도 문장"

    imported = JsonImporter().import_data(data)

    assert [item.original_text for item in imported.chapters[0].paragraphs[0].sentences] == [
        "마침표가 둘이다. 그래도 한 문장이다.",
        "종결 부호가 없어도 별도 문장",
    ]


@pytest.mark.parametrize("version", [None, 0, 2, "1", True])
def test_unsupported_or_invalid_format_version_is_rejected(version: object) -> None:
    data = valid_data()
    data["format_version"] = version

    with pytest.raises(JsonImportError, match="format_version"):
        JsonImporter().import_data(data)


def test_duplicate_id_anywhere_in_book_is_rejected() -> None:
    data = valid_data()
    data["book"]["chapters"][0]["paragraphs"][0]["sentences"][0]["id"] = "chapter-one"

    with pytest.raises(JsonImportError, match="중복 ID"):
        JsonImporter().import_data(data)


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (lambda data: data.pop("book"), "book"),
        (lambda data: data["book"].pop("title"), "book.title"),
        (lambda data: data["book"].pop("chapters"), "book.chapters"),
        (lambda data: data["book"]["chapters"][0].pop("paragraphs"), "paragraphs"),
        (
            lambda data: data["book"]["chapters"][0]["paragraphs"][0].pop("sentences"),
            "sentences",
        ),
    ],
)
def test_missing_required_structure_has_a_precise_error(
    mutation: Callable[[dict[str, Any]], object], message: str
) -> None:
    data = valid_data()
    mutation(data)

    with pytest.raises(JsonImportError, match=message):
        JsonImporter().import_data(data)


def test_malformed_json_reports_source_location() -> None:
    with pytest.raises(JsonImportError, match=r"2행 1열"):
        JsonImporter().import_text('{"format_version": 1,\n}')
