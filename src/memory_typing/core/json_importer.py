"""Import explicitly structured JSON books without guessing text boundaries."""

import json
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from memory_typing.domain import Book, Chapter, Paragraph, Sentence

FORMAT_VERSION = 1


class JsonImportError(ValueError):
    """Raised when a JSON book does not follow the supported data format."""


class JsonImporter:
    """Build the content hierarchy from explicit, stable JSON data."""

    def import_file(self, path: str | Path, *, encoding: str = "utf-8") -> Book:
        """Decode and validate one JSON book file."""
        source_path = Path(path)
        return self.import_text(source_path.read_text(encoding=encoding))

    def import_text(self, source: str) -> Book:
        """Parse a JSON string and return its validated book."""
        try:
            data = json.loads(source)
        except json.JSONDecodeError as error:
            raise JsonImportError(
                f"올바른 JSON이 아닙니다 ({error.lineno}행 {error.colno}열)."
            ) from error
        return self.import_data(data)

    def import_data(self, data: Any) -> Book:
        """Validate decoded JSON data and build immutable domain models."""
        root = _object(data, "최상위 값")
        version = root.get("format_version")
        if type(version) is not int or version != FORMAT_VERSION:
            raise JsonImportError(
                f"format_version은 {FORMAT_VERSION}이어야 합니다 (입력값: {version!r})."
            )

        book_data = _object(root.get("book"), "book")
        used_ids: set[str] = set()
        book_id = _stable_id(book_data.get("id"), "book.id", used_ids)
        title = _non_empty_string(book_data.get("title"), "book.title")
        chapter_data_items = _array(book_data.get("chapters"), "book.chapters")
        chapters: list[Chapter] = []

        for chapter_order, chapter_value in enumerate(chapter_data_items):
            path = f"book.chapters[{chapter_order}]"
            chapter_data = _object(chapter_value, path)
            chapter_id = _stable_id(chapter_data.get("id"), f"{path}.id", used_ids)
            chapter_title = _non_empty_string(chapter_data.get("title"), f"{path}.title")
            paragraph_data_items = _array(chapter_data.get("paragraphs"), f"{path}.paragraphs")
            paragraphs: list[Paragraph] = []

            for paragraph_order, paragraph_value in enumerate(paragraph_data_items):
                paragraph_path = f"{path}.paragraphs[{paragraph_order}]"
                paragraph_data = _object(paragraph_value, paragraph_path)
                paragraph_id = _stable_id(
                    paragraph_data.get("id"), f"{paragraph_path}.id", used_ids
                )
                sentence_data_items = _array(
                    paragraph_data.get("sentences"), f"{paragraph_path}.sentences"
                )
                sentences: list[Sentence] = []

                for sentence_order, sentence_value in enumerate(sentence_data_items):
                    sentence_path = f"{paragraph_path}.sentences[{sentence_order}]"
                    sentence_data = _object(sentence_value, sentence_path)
                    sentence_id = _stable_id(
                        sentence_data.get("id"), f"{sentence_path}.id", used_ids
                    )
                    text = _sentence_text(sentence_data.get("text"), f"{sentence_path}.text")
                    sentences.append(Sentence(sentence_id, paragraph_id, sentence_order, text))

                paragraph_text = " ".join(item.original_text for item in sentences)
                paragraphs.append(
                    Paragraph(
                        paragraph_id,
                        chapter_id,
                        paragraph_order,
                        paragraph_text,
                        tuple(sentences),
                    )
                )

            chapter_text = _join_non_empty(item.original_text for item in paragraphs)
            chapters.append(
                Chapter(
                    chapter_id,
                    book_id,
                    chapter_order,
                    chapter_title,
                    chapter_text,
                    tuple(paragraphs),
                )
            )

        book_text = _join_non_empty(item.original_text for item in chapters)
        return Book(book_id, title, book_text, tuple(chapters))


def _object(value: Any, path: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise JsonImportError(f"{path}은(는) 객체여야 합니다.")
    return value


def _array(value: Any, path: str) -> list[Any]:
    if not isinstance(value, list):
        raise JsonImportError(f"{path}은(는) 배열이어야 합니다.")
    return value


def _non_empty_string(value: Any, path: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise JsonImportError(f"{path}은(는) 비어 있지 않은 문자열이어야 합니다.")
    return value


def _stable_id(value: Any, path: str, used_ids: set[str]) -> str:
    identifier = _non_empty_string(value, path)
    if identifier != identifier.strip():
        raise JsonImportError(f"{path}의 앞뒤에는 공백을 넣을 수 없습니다.")
    if identifier in used_ids:
        raise JsonImportError(f"중복 ID가 있습니다: {identifier}")
    used_ids.add(identifier)
    return identifier


def _sentence_text(value: Any, path: str) -> str:
    text = _non_empty_string(value, path)
    if text != text.strip():
        raise JsonImportError(
            f"{path}의 앞뒤에는 공백을 넣을 수 없습니다. 문장 간 공백은 자동으로 추가됩니다."
        )
    return text


def _join_non_empty(texts: Iterable[str]) -> str:
    return "\n\n".join(text for text in texts if text)
