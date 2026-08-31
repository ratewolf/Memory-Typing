"""SQLite persistence for study sessions and sentence attempts."""

import sqlite3
from collections.abc import Callable
from datetime import UTC, datetime
from uuid import uuid4

from memory_typing.core.persistence import PersistenceError
from memory_typing.core.typing_engine import TypingState
from memory_typing.domain import SentenceAttempt, StudySession
from memory_typing.storage.database import Database

IdFactory = Callable[[], str]
Clock = Callable[[], datetime]


def _new_id() -> str:
    return str(uuid4())


def _utc_now() -> datetime:
    return datetime.now(UTC)


class StudyRepository:
    """Create and retrieve durable study history."""

    def __init__(
        self,
        database: Database,
        *,
        id_factory: IdFactory = _new_id,
        clock: Clock = _utc_now,
    ) -> None:
        self._database = database
        self._id_factory = id_factory
        self._clock = clock

    def start_session(self, chapter_id: str) -> StudySession:
        """Start one chapter session at the first committed learner input."""
        session = StudySession(self._id_factory(), chapter_id, self._clock())
        try:
            with self._database.connect() as connection:
                connection.execute(
                    """
                    INSERT INTO study_sessions (id, chapter_id, started_at, completed_at)
                    VALUES (?, ?, ?, NULL)
                    """,
                    (session.id, session.chapter_id, _to_text(session.started_at)),
                )
        except sqlite3.Error as error:
            raise PersistenceError("학습 세션을 저장할 수 없습니다.") from error
        return session

    def record_sentence_attempt(
        self,
        session_id: str,
        sentence_id: str,
        typing_state: TypingState,
    ) -> SentenceAttempt:
        """Persist the next attempt number for a sentence within a session."""
        try:
            with self._database.connect() as connection:
                source_row = connection.execute(
                    """
                    SELECT sentences.original_text
                    FROM study_sessions
                    JOIN chapters ON chapters.id = study_sessions.chapter_id
                    JOIN paragraphs ON paragraphs.chapter_id = chapters.id
                    JOIN sentences ON sentences.paragraph_id = paragraphs.id
                    WHERE study_sessions.id = ? AND sentences.id = ?
                    """,
                    (session_id, sentence_id),
                ).fetchone()
                if source_row is None:
                    raise ValueError("sentence does not belong to the study session chapter")
                if source_row["original_text"] != typing_state.original_text:
                    raise ValueError(
                        "typing state original_text does not match the stored sentence"
                    )

                attempt_number = connection.execute(
                    """
                    SELECT COALESCE(MAX(attempt_number), 0) + 1
                    FROM sentence_attempts
                    WHERE session_id = ? AND sentence_id = ?
                    """,
                    (session_id, sentence_id),
                ).fetchone()[0]
                attempt = SentenceAttempt(
                    id=self._id_factory(),
                    session_id=session_id,
                    sentence_id=sentence_id,
                    attempt_number=attempt_number,
                    typed_text=typing_state.typed_text,
                    correct_character_count=typing_state.correct_character_count,
                    incorrect_character_count=typing_state.incorrect_character_count,
                    accuracy=typing_state.accuracy,
                    elapsed_seconds=typing_state.elapsed_seconds,
                    characters_per_minute=typing_state.characters_per_minute,
                    words_per_minute=typing_state.words_per_minute,
                    is_complete=typing_state.is_complete,
                    created_at=self._clock(),
                )
                connection.execute(
                    """
                    INSERT INTO sentence_attempts (
                        id, session_id, sentence_id, attempt_number, typed_text,
                        correct_character_count, incorrect_character_count, accuracy,
                        elapsed_seconds, characters_per_minute, words_per_minute,
                        is_complete, created_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        attempt.id,
                        attempt.session_id,
                        attempt.sentence_id,
                        attempt.attempt_number,
                        attempt.typed_text,
                        attempt.correct_character_count,
                        attempt.incorrect_character_count,
                        attempt.accuracy,
                        attempt.elapsed_seconds,
                        attempt.characters_per_minute,
                        attempt.words_per_minute,
                        int(attempt.is_complete),
                        _to_text(attempt.created_at),
                    ),
                )
        except sqlite3.Error as error:
            raise PersistenceError("문장 학습 시도를 저장할 수 없습니다.") from error
        return attempt

    def complete_session(self, session_id: str) -> StudySession:
        """Mark a session complete after its final sentence is accepted."""
        completed_at = self._clock()
        try:
            with self._database.connect() as connection:
                row = connection.execute(
                    """
                    SELECT id, chapter_id, started_at, completed_at
                    FROM study_sessions
                    WHERE id = ?
                    """,
                    (session_id,),
                ).fetchone()
                if row is None:
                    raise ValueError("unknown study session")
                session = StudySession(
                    id=row["id"],
                    chapter_id=row["chapter_id"],
                    started_at=_from_text(row["started_at"]),
                    completed_at=completed_at,
                )
                connection.execute(
                    "UPDATE study_sessions SET completed_at = ? WHERE id = ?",
                    (_to_text(completed_at), session_id),
                )
        except sqlite3.Error as error:
            raise PersistenceError("학습 세션 완료 상태를 저장할 수 없습니다.") from error
        return session

    def get_session(self, session_id: str) -> StudySession | None:
        """Return one session by stable ID."""
        with self._database.connect() as connection:
            row = connection.execute(
                """
                SELECT id, chapter_id, started_at, completed_at
                FROM study_sessions
                WHERE id = ?
                """,
                (session_id,),
            ).fetchone()
        return None if row is None else _session_from_row(row)

    def list_sessions(self, *, chapter_id: str | None = None) -> tuple[StudySession, ...]:
        """Return sessions in chronological order, optionally for one chapter."""
        query = "SELECT id, chapter_id, started_at, completed_at FROM study_sessions"
        parameters: tuple[str, ...] = ()
        if chapter_id is not None:
            query += " WHERE chapter_id = ?"
            parameters = (chapter_id,)
        query += " ORDER BY started_at, id"
        with self._database.connect() as connection:
            rows = connection.execute(query, parameters).fetchall()
        return tuple(_session_from_row(row) for row in rows)

    def list_sentence_attempts(self, session_id: str) -> tuple[SentenceAttempt, ...]:
        """Return attempts for a session in the order they were recorded."""
        with self._database.connect() as connection:
            rows = connection.execute(
                """
                SELECT id, session_id, sentence_id, attempt_number, typed_text,
                       correct_character_count, incorrect_character_count, accuracy,
                       elapsed_seconds, characters_per_minute, words_per_minute,
                       is_complete, created_at
                FROM sentence_attempts
                WHERE session_id = ?
                ORDER BY created_at, id
                """,
                (session_id,),
            ).fetchall()
        return tuple(_attempt_from_row(row) for row in rows)


def _to_text(value: datetime) -> str:
    return value.astimezone(UTC).isoformat()


def _from_text(value: str) -> datetime:
    return datetime.fromisoformat(value)


def _session_from_row(row: sqlite3.Row) -> StudySession:
    return StudySession(
        id=row["id"],
        chapter_id=row["chapter_id"],
        started_at=_from_text(row["started_at"]),
        completed_at=None if row["completed_at"] is None else _from_text(row["completed_at"]),
    )


def _attempt_from_row(row: sqlite3.Row) -> SentenceAttempt:
    return SentenceAttempt(
        id=row["id"],
        session_id=row["session_id"],
        sentence_id=row["sentence_id"],
        attempt_number=row["attempt_number"],
        typed_text=row["typed_text"],
        correct_character_count=row["correct_character_count"],
        incorrect_character_count=row["incorrect_character_count"],
        accuracy=row["accuracy"],
        elapsed_seconds=row["elapsed_seconds"],
        characters_per_minute=row["characters_per_minute"],
        words_per_minute=row["words_per_minute"],
        is_complete=bool(row["is_complete"]),
        created_at=_from_text(row["created_at"]),
    )
