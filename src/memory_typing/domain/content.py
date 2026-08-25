"""Immutable content hierarchy for imported source text."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Sentence:
    """A canonical source sentence within a paragraph."""

    id: str
    paragraph_id: str
    source_order: int
    original_text: str


@dataclass(frozen=True, slots=True)
class Paragraph:
    """An ordered source paragraph and its sentences."""

    id: str
    chapter_id: str
    source_order: int
    original_text: str
    sentences: tuple[Sentence, ...]


@dataclass(frozen=True, slots=True)
class Chapter:
    """An ordered chapter within a book."""

    id: str
    book_id: str
    source_order: int
    title: str
    original_text: str
    paragraphs: tuple[Paragraph, ...]


@dataclass(frozen=True, slots=True)
class Book:
    """An imported book with its exact source text."""

    id: str
    title: str
    original_text: str
    chapters: tuple[Chapter, ...]
