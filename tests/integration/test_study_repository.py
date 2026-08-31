"""SQLite integration tests for durable study history."""

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from memory_typing.core import TypingEngine
from memory_typing.domain import Book, Chapter, Paragraph, Sentence
from memory_typing.storage import BookRepository, Database, StudyRepository


def stored_book() -> Book:
    sentence = Sentence("sentence", "paragraph", 0, "기억을 반복한다.")
    paragraph = Paragraph("paragraph", "chapter", 0, sentence.original_text, (sentence,))
    chapter = Chapter("chapter", "book", 0, "첫 장", paragraph.original_text, (paragraph,))
    return Book("book", "기억", chapter.original_text, (chapter,))


def make_repositories(tmp_path: Path) -> tuple[BookRepository, StudyRepository]:
    database = Database(tmp_path / "memory-typing.sqlite3")
    book_repository = BookRepository(database)
    book_repository.add(stored_book())
    times = iter(
        (
            datetime(2026, 8, 31, 1, 0, tzinfo=UTC),
            datetime(2026, 8, 31, 1, 1, tzinfo=UTC),
            datetime(2026, 8, 31, 1, 2, tzinfo=UTC),
            datetime(2026, 8, 31, 1, 3, tzinfo=UTC),
        )
    )
    ids = iter(("session", "attempt-1", "attempt-2"))
    study_repository = StudyRepository(
        database,
        id_factory=lambda: next(ids),
        clock=lambda: next(times),
    )
    return book_repository, study_repository


def test_session_and_sentence_attempt_round_trip(tmp_path: Path) -> None:
    _, repository = make_repositories(tmp_path)
    session = repository.start_session("chapter")
    state = TypingEngine("기억을 반복한다.").evaluate("기억을 반복한다.", elapsed_seconds=30)

    attempt = repository.record_sentence_attempt(session.id, "sentence", state)
    completed = repository.complete_session(session.id)

    assert completed.completed_at == datetime(2026, 8, 31, 1, 2, tzinfo=UTC)
    assert repository.get_session(session.id) == completed
    assert repository.list_sessions(chapter_id="chapter") == (completed,)
    assert repository.list_sentence_attempts(session.id) == (attempt,)
    assert attempt.typed_text == "기억을 반복한다."
    assert attempt.attempt_number == 1
    assert attempt.accuracy == 1.0
    assert attempt.is_complete is True
    assert attempt.elapsed_seconds == 30


def test_attempt_numbers_increment_within_the_same_session(tmp_path: Path) -> None:
    _, repository = make_repositories(tmp_path)
    session = repository.start_session("chapter")
    state = TypingEngine("기억을 반복한다.").evaluate("기억")

    first = repository.record_sentence_attempt(session.id, "sentence", state)
    second = repository.record_sentence_attempt(session.id, "sentence", state)

    assert (first.attempt_number, second.attempt_number) == (1, 2)


def test_attempt_rejects_text_from_another_source_sentence(tmp_path: Path) -> None:
    _, repository = make_repositories(tmp_path)
    session = repository.start_session("chapter")

    with pytest.raises(ValueError, match="original_text"):
        repository.record_sentence_attempt(
            session.id,
            "sentence",
            TypingEngine("다른 문장").evaluate("다른 문장"),
        )


def test_domain_rejects_completion_before_session_start(tmp_path: Path) -> None:
    database = Database(tmp_path / "memory-typing.sqlite3")
    BookRepository(database).add(stored_book())
    times = iter(
        (
            datetime(2026, 8, 31, 1, 0, tzinfo=UTC),
            datetime(2026, 8, 31, 1, 0, tzinfo=UTC) - timedelta(seconds=1),
        )
    )
    repository = StudyRepository(database, clock=lambda: next(times))
    session = repository.start_session("chapter")

    with pytest.raises(ValueError, match="must not precede"):
        repository.complete_session(session.id)
