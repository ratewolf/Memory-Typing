"""Immutable study-history models stored independently from the UI."""

from dataclasses import dataclass
from datetime import datetime


def _require_aware(value: datetime, field_name: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must include a timezone")


@dataclass(frozen=True, slots=True)
class StudySession:
    """One learner visit to a chapter."""

    id: str
    chapter_id: str
    started_at: datetime
    completed_at: datetime | None = None

    def __post_init__(self) -> None:
        if not self.id or not self.chapter_id:
            raise ValueError("study session IDs must not be empty")
        _require_aware(self.started_at, "started_at")
        if self.completed_at is not None:
            _require_aware(self.completed_at, "completed_at")
            if self.completed_at < self.started_at:
                raise ValueError("completed_at must not precede started_at")


@dataclass(frozen=True, slots=True)
class SentenceAttempt:
    """A persisted typing result for one stable source sentence."""

    id: str
    session_id: str
    sentence_id: str
    attempt_number: int
    typed_text: str
    correct_character_count: int
    incorrect_character_count: int
    accuracy: float
    elapsed_seconds: float
    characters_per_minute: float
    words_per_minute: float
    is_complete: bool
    created_at: datetime

    def __post_init__(self) -> None:
        if not self.id or not self.session_id or not self.sentence_id:
            raise ValueError("sentence attempt IDs must not be empty")
        if self.attempt_number < 1:
            raise ValueError("attempt_number must be at least 1")
        if self.correct_character_count < 0 or self.incorrect_character_count < 0:
            raise ValueError("character counts must not be negative")
        if not 0.0 <= self.accuracy <= 1.0:
            raise ValueError("accuracy must be between 0.0 and 1.0")
        if min(self.elapsed_seconds, self.characters_per_minute, self.words_per_minute) < 0:
            raise ValueError("time and speed values must not be negative")
        _require_aware(self.created_at, "created_at")
