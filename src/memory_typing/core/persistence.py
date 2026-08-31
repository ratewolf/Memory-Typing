"""Framework-independent ports used to persist library and study data."""

from __future__ import annotations

from typing import Protocol

from memory_typing.core.typing_engine import TypingState
from memory_typing.domain import Book, SentenceAttempt, StudySession


class PersistenceError(RuntimeError):
    """Raised when durable local data cannot be read or written."""


class ContentConflictError(PersistenceError):
    """Raised when imported stable IDs conflict with stored content."""


class ContentStore(Protocol):
    """Persistent operations required by the book-selection UI."""

    def add(self, book: Book) -> None: ...

    def get(self, book_id: str) -> Book | None: ...

    def list_all(self) -> tuple[Book, ...]: ...


class StudyRecordStore(Protocol):
    """Persistent operations required while a typing session is active."""

    def start_session(self, chapter_id: str) -> StudySession: ...

    def record_sentence_attempt(
        self,
        session_id: str,
        sentence_id: str,
        typing_state: TypingState,
    ) -> SentenceAttempt: ...

    def complete_session(self, session_id: str) -> StudySession: ...
