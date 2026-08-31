"""Unit tests for sentence-session navigation."""

import pytest

from memory_typing.core import TypingSession
from memory_typing.domain import Sentence


def sentence(identifier: str, order: int, text: str) -> Sentence:
    return Sentence(identifier, "paragraph", order, text)


def test_session_evaluates_current_sentence_with_typing_engine() -> None:
    session = TypingSession((sentence("one", 0, "기억"), sentence("two", 1, "반복")))

    evaluation = session.evaluate("기억", elapsed_seconds=30)

    assert evaluation.sentence.id == "one"
    assert evaluation.sentence_number == 1
    assert evaluation.sentence_count == 2
    assert evaluation.typing_state.is_complete is True
    assert evaluation.typing_state.characters_per_minute == 4.0


def test_incomplete_input_does_not_advance() -> None:
    session = TypingSession((sentence("one", 0, "기억"), sentence("two", 1, "반복")))

    assert session.advance_if_complete(session.evaluate("기")) is False
    assert session.current_sentence.id == "one"


def test_completed_input_advances_and_final_sentence_completes_session() -> None:
    session = TypingSession((sentence("one", 0, "기억"), sentence("two", 1, "반복")))

    assert session.advance_if_complete(session.evaluate("기억")) is True
    assert session.current_sentence.id == "two"
    assert session.is_complete is False
    assert session.advance_if_complete(session.evaluate("반복")) is True
    assert session.is_complete is True


def test_stale_evaluation_cannot_advance_another_sentence() -> None:
    session = TypingSession((sentence("one", 0, "같음"), sentence("two", 1, "같음")))
    first_evaluation = session.evaluate("같음")
    session.advance_if_complete(first_evaluation)

    with pytest.raises(ValueError, match="current sentence"):
        session.advance_if_complete(first_evaluation)


def test_session_requires_at_least_one_sentence() -> None:
    with pytest.raises(ValueError, match="at least one"):
        TypingSession(())
