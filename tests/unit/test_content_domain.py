"""Tests for immutable content domain models."""

from dataclasses import FrozenInstanceError

import pytest

from memory_typing.domain import Book, Chapter, Paragraph, Sentence


def test_content_entities_preserve_ids_order_and_original_text() -> None:
    sentence = Sentence("sentence-id", "paragraph-id", 0, "  원문 그대로.  ")
    paragraph = Paragraph("paragraph-id", "chapter-id", 0, "  원문 그대로.  ", (sentence,))
    chapter = Chapter("chapter-id", "book-id", 0, "제1장", "  원문 그대로.  ", (paragraph,))
    book = Book("book-id", "책", "  원문 그대로.  ", (chapter,))

    assert book.chapters[0].paragraphs[0].sentences[0].original_text == "  원문 그대로.  "
    assert sentence.paragraph_id == paragraph.id
    assert paragraph.chapter_id == chapter.id
    assert chapter.book_id == book.id
    assert sentence.source_order == 0


def test_domain_models_are_immutable() -> None:
    sentence = Sentence("sentence-id", "paragraph-id", 0, "원문")

    with pytest.raises(FrozenInstanceError):
        sentence.original_text = "빈칸"  # type: ignore[misc]
