"""SQLite integration tests for content persistence."""

import sqlite3
from pathlib import Path

import pytest

from memory_typing.core.txt_importer import TxtImporter
from memory_typing.domain import Book, Chapter, Paragraph, Sentence
from memory_typing.storage import SCHEMA_VERSION, BookRepository, Database


def build_book(*, book_id: str = "book-1") -> Book:
    sentence_0 = Sentence("sentence-1", "paragraph-1", 0, "인간의 기억은 ")
    sentence_1 = Sentence("sentence-2", "paragraph-1", 1, "반복을 통해 강화된다.")
    paragraph = Paragraph(
        "paragraph-1",
        "chapter-1",
        0,
        "인간의 기억은 반복을 통해 강화된다.",
        (sentence_0, sentence_1),
    )
    chapter = Chapter("chapter-1", book_id, 0, "기억", paragraph.original_text, (paragraph,))
    return Book(book_id, "기억 연습", chapter.original_text, (chapter,))


def make_repository(tmp_path: Path) -> tuple[Database, BookRepository]:
    database = Database(tmp_path / "memory-typing.sqlite3")
    return database, BookRepository(database)


def test_fresh_database_is_initialized_automatically(tmp_path: Path) -> None:
    database_path = tmp_path / "nested" / "memory-typing.sqlite3"
    database = Database(database_path)

    assert database_path.exists()
    with database.connect() as connection:
        version = connection.execute("PRAGMA user_version").fetchone()[0]
        table_names = {
            row["name"]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }
    assert version == SCHEMA_VERSION
    assert {"books", "chapters", "paragraphs", "sentences"} <= table_names


def test_insert_and_retrieve_complete_book_hierarchy(tmp_path: Path) -> None:
    _, repository = make_repository(tmp_path)
    expected = build_book()

    repository.add(expected)

    assert repository.get(expected.id) == expected
    assert repository.get("missing-book") is None


def test_sentence_source_order_is_used_when_retrieving(tmp_path: Path) -> None:
    database, repository = make_repository(tmp_path)
    repository.add(build_book())
    with database.connect() as connection:
        connection.execute("UPDATE sentences SET source_order = 10 WHERE id = 'sentence-1'")
        connection.execute("UPDATE sentences SET source_order = 5 WHERE id = 'sentence-2'")

    restored = repository.get("book-1")

    assert restored is not None
    assert [sentence.id for sentence in restored.chapters[0].paragraphs[0].sentences] == [
        "sentence-2",
        "sentence-1",
    ]
    assert [sentence.source_order for sentence in restored.chapters[0].paragraphs[0].sentences] == [
        5,
        10,
    ]


def test_korean_unicode_and_exact_whitespace_round_trip(tmp_path: Path) -> None:
    _, repository = make_repository(tmp_path)
    source = "  인간의 기억은 반복을 통해 강화된다.\n다음 줄도 보존한다.  "
    ids = iter(f"stable-{index}" for index in range(10))
    expected = TxtImporter(id_factory=lambda: next(ids)).import_text(source, title="한글 책")

    repository.add(expected)
    restored = repository.get(expected.id)

    assert restored == expected
    assert restored is not None
    assert restored.original_text == source


def test_duplicate_stable_id_fails_without_damaging_existing_data(tmp_path: Path) -> None:
    _, repository = make_repository(tmp_path)
    expected = build_book()
    repository.add(expected)

    with pytest.raises(sqlite3.IntegrityError):
        repository.add(expected)

    assert repository.get(expected.id) == expected


def test_foreign_keys_reject_orphans_and_parent_deletion(tmp_path: Path) -> None:
    database, repository = make_repository(tmp_path)
    repository.add(build_book())

    with pytest.raises(sqlite3.IntegrityError), database.connect() as connection:
        connection.execute(
            """
            INSERT INTO sentences (id, paragraph_id, source_order, original_text)
            VALUES ('orphan', 'missing-paragraph', 0, '고아 문장')
            """
        )

    with pytest.raises(sqlite3.IntegrityError), database.connect() as connection:
        connection.execute("DELETE FROM books WHERE id = 'book-1'")

    assert repository.get("book-1") == build_book()


def test_mismatched_hierarchy_is_rejected_before_writing(tmp_path: Path) -> None:
    _, repository = make_repository(tmp_path)
    mismatched = build_book(book_id="different-book")
    mismatched_chapter = Chapter(
        id=mismatched.chapters[0].id,
        book_id="unrelated-book",
        source_order=0,
        title=mismatched.chapters[0].title,
        original_text=mismatched.chapters[0].original_text,
        paragraphs=mismatched.chapters[0].paragraphs,
    )
    invalid_book = Book(
        id=mismatched.id,
        title=mismatched.title,
        original_text=mismatched.original_text,
        chapters=(mismatched_chapter,),
    )

    with pytest.raises(ValueError, match="chapter book_id"):
        repository.add(invalid_book)

    assert repository.get(invalid_book.id) is None
