"""Import plain-text sources into the content domain model."""

import re
from collections.abc import Callable
from pathlib import Path
from uuid import uuid4

from memory_typing.domain import Book, Chapter, Paragraph, Sentence

IdFactory = Callable[[], str]

_BLANK_LINE_SEPARATOR = re.compile(r"(?:\r\n|\n|\r)(?:[ \t]*(?:\r\n|\n|\r))+")
_SENTENCE_END = re.compile(r"[.!?。？！]+[\"'”’）)]*(?=\s|$)")


def _new_id() -> str:
    return str(uuid4())


class TxtImporter:
    """Convert one TXT source into one book and one chapter."""

    def __init__(self, id_factory: IdFactory = _new_id) -> None:
        self._id_factory = id_factory

    def import_file(self, path: str | Path, *, encoding: str = "utf-8") -> Book:
        """Decode and import a TXT file without universal-newline conversion."""
        source_path = Path(path)
        original_text = source_path.read_bytes().decode(encoding)
        return self.import_text(original_text, title=source_path.stem)

    def import_text(self, original_text: str, *, title: str) -> Book:
        """Import an exact source string with a caller-provided book title."""
        book_id = self._id_factory()
        chapter_id = self._id_factory()
        paragraphs = tuple(
            self._make_paragraph(chapter_id, source_order, paragraph_text)
            for source_order, paragraph_text in enumerate(_split_paragraphs(original_text))
        )
        chapter = Chapter(
            id=chapter_id,
            book_id=book_id,
            source_order=0,
            title=title,
            original_text=original_text,
            paragraphs=paragraphs,
        )
        return Book(
            id=book_id,
            title=title,
            original_text=original_text,
            chapters=(chapter,),
        )

    def _make_paragraph(self, chapter_id: str, source_order: int, original_text: str) -> Paragraph:
        paragraph_id = self._id_factory()
        sentences = tuple(
            Sentence(
                id=self._id_factory(),
                paragraph_id=paragraph_id,
                source_order=sentence_order,
                original_text=sentence_text,
            )
            for sentence_order, sentence_text in enumerate(_split_sentences(original_text))
        )
        return Paragraph(
            id=paragraph_id,
            chapter_id=chapter_id,
            source_order=source_order,
            original_text=original_text,
            sentences=sentences,
        )


def _split_paragraphs(original_text: str) -> tuple[str, ...]:
    """Split on blank lines while retaining every character inside a paragraph."""
    return tuple(
        block for block in _BLANK_LINE_SEPARATOR.split(original_text) if block.strip() != ""
    )


def _split_sentences(original_text: str) -> tuple[str, ...]:
    """Split only at explicit terminal punctuation followed by whitespace or EOF."""
    boundaries = [match.end() for match in _SENTENCE_END.finditer(original_text)]
    sentences: list[str] = []
    start = 0
    for boundary in boundaries:
        if boundary < len(original_text):
            sentences.append(original_text[start:boundary])
            start = boundary
    if start < len(original_text):
        sentences.append(original_text[start:])
    return tuple(sentences)
