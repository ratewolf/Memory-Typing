"""SQLite connection management and schema initialization."""

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

SCHEMA_VERSION = 1

_SCHEMA = """
CREATE TABLE IF NOT EXISTS books (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    original_text TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS chapters (
    id TEXT PRIMARY KEY,
    book_id TEXT NOT NULL,
    source_order INTEGER NOT NULL CHECK (source_order >= 0),
    title TEXT NOT NULL,
    original_text TEXT NOT NULL,
    FOREIGN KEY (book_id) REFERENCES books(id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    UNIQUE (book_id, source_order)
);

CREATE TABLE IF NOT EXISTS paragraphs (
    id TEXT PRIMARY KEY,
    chapter_id TEXT NOT NULL,
    source_order INTEGER NOT NULL CHECK (source_order >= 0),
    original_text TEXT NOT NULL,
    FOREIGN KEY (chapter_id) REFERENCES chapters(id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    UNIQUE (chapter_id, source_order)
);

CREATE TABLE IF NOT EXISTS sentences (
    id TEXT PRIMARY KEY,
    paragraph_id TEXT NOT NULL,
    source_order INTEGER NOT NULL CHECK (source_order >= 0),
    original_text TEXT NOT NULL,
    FOREIGN KEY (paragraph_id) REFERENCES paragraphs(id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    UNIQUE (paragraph_id, source_order)
);

CREATE INDEX IF NOT EXISTS idx_chapters_book_order
    ON chapters(book_id, source_order);
CREATE INDEX IF NOT EXISTS idx_paragraphs_chapter_order
    ON paragraphs(chapter_id, source_order);
CREATE INDEX IF NOT EXISTS idx_sentences_paragraph_order
    ON sentences(paragraph_id, source_order);
"""


class Database:
    """Own SQLite connections for one local database file."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize_schema()

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        """Yield a transactional connection with foreign keys enabled."""
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        try:
            yield connection
        except BaseException:
            connection.rollback()
            raise
        else:
            connection.commit()
        finally:
            connection.close()

    def _initialize_schema(self) -> None:
        with self.connect() as connection:
            version = connection.execute("PRAGMA user_version").fetchone()[0]
            if version > SCHEMA_VERSION:
                raise RuntimeError(
                    f"database schema version {version} is newer than supported "
                    f"version {SCHEMA_VERSION}"
                )
            if version == 0:
                connection.executescript(_SCHEMA)
                connection.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
