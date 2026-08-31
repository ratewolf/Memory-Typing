"""Repositories that map content domain models to SQLite rows."""

import sqlite3

from memory_typing.core.persistence import ContentConflictError, PersistenceError
from memory_typing.domain import Book, Chapter, Paragraph, Sentence
from memory_typing.storage.database import Database


class BookRepository:
    """Persist and rebuild complete book content hierarchies."""

    def __init__(self, database: Database) -> None:
        self._database = database

    def add(self, book: Book) -> None:
        """Insert a book hierarchy atomically."""
        self._validate_hierarchy(book)
        try:
            with self._database.connect() as connection:
                connection.execute(
                    "INSERT INTO books (id, title, original_text) VALUES (?, ?, ?)",
                    (book.id, book.title, book.original_text),
                )
                for chapter in book.chapters:
                    connection.execute(
                        """
                        INSERT INTO chapters (id, book_id, source_order, title, original_text)
                        VALUES (?, ?, ?, ?, ?)
                        """,
                        (
                            chapter.id,
                            chapter.book_id,
                            chapter.source_order,
                            chapter.title,
                            chapter.original_text,
                        ),
                    )
                    for paragraph in chapter.paragraphs:
                        connection.execute(
                            """
                            INSERT INTO paragraphs (id, chapter_id, source_order, original_text)
                            VALUES (?, ?, ?, ?)
                            """,
                            (
                                paragraph.id,
                                paragraph.chapter_id,
                                paragraph.source_order,
                                paragraph.original_text,
                            ),
                        )
                        connection.executemany(
                            """
                            INSERT INTO sentences (id, paragraph_id, source_order, original_text)
                            VALUES (?, ?, ?, ?)
                            """,
                            (
                                (
                                    sentence.id,
                                    sentence.paragraph_id,
                                    sentence.source_order,
                                    sentence.original_text,
                                )
                                for sentence in paragraph.sentences
                            ),
                        )
        except sqlite3.IntegrityError as error:
            raise ContentConflictError(
                "가져온 콘텐츠의 ID 또는 원문 순서가 기존 데이터와 충돌합니다."
            ) from error
        except sqlite3.Error as error:
            raise PersistenceError("책을 로컬 데이터베이스에 저장할 수 없습니다.") from error

    def get(self, book_id: str) -> Book | None:
        """Retrieve a complete book hierarchy in source order."""
        with self._database.connect() as connection:
            book_row = connection.execute(
                "SELECT id, title, original_text FROM books WHERE id = ?", (book_id,)
            ).fetchone()
            if book_row is None:
                return None

            chapter_rows = connection.execute(
                """
                SELECT id, book_id, source_order, title, original_text
                FROM chapters
                WHERE book_id = ?
                ORDER BY source_order
                """,
                (book_id,),
            ).fetchall()
            return self._build_book(connection, book_row, chapter_rows)

    def list_all(self) -> tuple[Book, ...]:
        """Return every stored book in a deterministic library order."""
        with self._database.connect() as connection:
            book_rows = connection.execute(
                "SELECT id, title, original_text FROM books ORDER BY title, id"
            ).fetchall()
            books: list[Book] = []
            for book_row in book_rows:
                chapter_rows = connection.execute(
                    """
                    SELECT id, book_id, source_order, title, original_text
                    FROM chapters
                    WHERE book_id = ?
                    ORDER BY source_order
                    """,
                    (book_row["id"],),
                ).fetchall()
                books.append(self._build_book(connection, book_row, chapter_rows))
            return tuple(books)

    @staticmethod
    def _build_book(
        connection: sqlite3.Connection,
        book_row: sqlite3.Row,
        chapter_rows: list[sqlite3.Row],
    ) -> Book:
        chapters = tuple(
            BookRepository._build_chapter(connection, chapter_row) for chapter_row in chapter_rows
        )
        return Book(
            id=book_row["id"],
            title=book_row["title"],
            original_text=book_row["original_text"],
            chapters=chapters,
        )

    @staticmethod
    def _build_chapter(connection: sqlite3.Connection, chapter_row: sqlite3.Row) -> Chapter:
        paragraphs = tuple(
            BookRepository._build_paragraph(connection, paragraph_row)
            for paragraph_row in connection.execute(
                """
                SELECT id, chapter_id, source_order, original_text
                FROM paragraphs
                WHERE chapter_id = ?
                ORDER BY source_order
                """,
                (chapter_row["id"],),
            ).fetchall()
        )
        return Chapter(
            id=chapter_row["id"],
            book_id=chapter_row["book_id"],
            source_order=chapter_row["source_order"],
            title=chapter_row["title"],
            original_text=chapter_row["original_text"],
            paragraphs=paragraphs,
        )

    @staticmethod
    def _build_paragraph(connection: sqlite3.Connection, paragraph_row: sqlite3.Row) -> Paragraph:
        sentence_rows = connection.execute(
            """
            SELECT id, paragraph_id, source_order, original_text
            FROM sentences
            WHERE paragraph_id = ?
            ORDER BY source_order
            """,
            (paragraph_row["id"],),
        ).fetchall()
        sentences = tuple(
            Sentence(
                id=row["id"],
                paragraph_id=row["paragraph_id"],
                source_order=row["source_order"],
                original_text=row["original_text"],
            )
            for row in sentence_rows
        )
        return Paragraph(
            id=paragraph_row["id"],
            chapter_id=paragraph_row["chapter_id"],
            source_order=paragraph_row["source_order"],
            original_text=paragraph_row["original_text"],
            sentences=sentences,
        )

    @staticmethod
    def _validate_hierarchy(book: Book) -> None:
        for chapter in book.chapters:
            if chapter.book_id != book.id:
                raise ValueError("chapter book_id does not match its book")
            for paragraph in chapter.paragraphs:
                if paragraph.chapter_id != chapter.id:
                    raise ValueError("paragraph chapter_id does not match its chapter")
                for sentence in paragraph.sentences:
                    if sentence.paragraph_id != paragraph.id:
                        raise ValueError("sentence paragraph_id does not match its paragraph")
