"""SQLite connection management and schema initialization."""

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

SCHEMA_VERSION = 2

_SCHEMA_V1 = """
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

_SCHEMA_V2 = """
CREATE TABLE IF NOT EXISTS study_sessions (
    id TEXT PRIMARY KEY,
    chapter_id TEXT NOT NULL,
    started_at TEXT NOT NULL,
    completed_at TEXT,
    FOREIGN KEY (chapter_id) REFERENCES chapters(id) ON UPDATE RESTRICT ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS sentence_attempts (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    sentence_id TEXT NOT NULL,
    attempt_number INTEGER NOT NULL CHECK (attempt_number >= 1),
    typed_text TEXT NOT NULL,
    correct_character_count INTEGER NOT NULL CHECK (correct_character_count >= 0),
    incorrect_character_count INTEGER NOT NULL CHECK (incorrect_character_count >= 0),
    accuracy REAL NOT NULL CHECK (accuracy >= 0.0 AND accuracy <= 1.0),
    elapsed_seconds REAL NOT NULL CHECK (elapsed_seconds >= 0.0),
    characters_per_minute REAL NOT NULL CHECK (characters_per_minute >= 0.0),
    words_per_minute REAL NOT NULL CHECK (words_per_minute >= 0.0),
    is_complete INTEGER NOT NULL CHECK (is_complete IN (0, 1)),
    created_at TEXT NOT NULL,
    FOREIGN KEY (session_id) REFERENCES study_sessions(id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    FOREIGN KEY (sentence_id) REFERENCES sentences(id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    UNIQUE (session_id, sentence_id, attempt_number)
);

CREATE INDEX IF NOT EXISTS idx_study_sessions_chapter_started
    ON study_sessions(chapter_id, started_at);
CREATE INDEX IF NOT EXISTS idx_sentence_attempts_session_created
    ON sentence_attempts(session_id, created_at);
CREATE INDEX IF NOT EXISTS idx_sentence_attempts_sentence_created
    ON sentence_attempts(sentence_id, created_at);
"""

_MIGRATIONS = {
    1: _SCHEMA_V1,
    2: _SCHEMA_V2,
}


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
            while version < SCHEMA_VERSION:
                next_version = version + 1
                connection.executescript(_MIGRATIONS[next_version])
                connection.execute(f"PRAGMA user_version = {next_version}")
                version = next_version
