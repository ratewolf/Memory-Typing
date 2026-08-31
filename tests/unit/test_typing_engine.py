"""Unit tests for the pure typing engine."""

from dataclasses import FrozenInstanceError

import pytest

from memory_typing.core.typing_engine import TypingEngine


def test_initial_state_for_non_empty_text() -> None:
    state = TypingEngine("hello").initial_state()

    assert state.original_text == "hello"
    assert state.typed_text == ""
    assert state.comparisons == ()
    assert state.correct_character_count == 0
    assert state.incorrect_character_count == 0
    assert state.progress == 0.0
    assert state.is_complete is False
    assert state.accuracy == 1.0
    assert state.elapsed_seconds == 0.0
    assert state.characters_per_minute == 0.0
    assert state.words_per_minute == 0.0
    assert state.is_started is False


def test_empty_target_is_complete_until_text_is_entered() -> None:
    engine = TypingEngine("")

    empty_state = engine.initial_state()
    entered_state = engine.evaluate("가")

    assert empty_state.progress == 1.0
    assert empty_state.is_complete is True
    assert entered_state.progress == 1.0
    assert entered_state.is_complete is False
    assert entered_state.correct_character_count == 0
    assert entered_state.incorrect_character_count == 1


def test_exact_english_input_is_complete() -> None:
    state = TypingEngine("Memory Typing!").evaluate("Memory Typing!")

    assert state.correct_character_count == 14
    assert state.incorrect_character_count == 0
    assert state.progress == 1.0
    assert state.accuracy == 1.0
    assert state.is_complete is True


def test_korean_text_is_compared_as_unicode() -> None:
    text = "인간의 기억은 반복을 통해 강화된다."
    state = TypingEngine(text).evaluate(text)

    assert state.correct_character_count == len(text)
    assert state.incorrect_character_count == 0
    assert state.is_complete is True


def test_mixed_korean_english_spaces_and_punctuation() -> None:
    text = "기억 Memory, 반복 2회!"
    state = TypingEngine(text).evaluate(text)

    assert all(comparison.is_correct for comparison in state.comparisons)
    assert state.correct_character_count == len(text)
    assert state.is_complete is True


def test_newlines_are_compared_as_characters() -> None:
    state = TypingEngine("첫 줄\nsecond line").evaluate("첫 줄\nsecond line")

    newline = state.comparisons[3]
    assert newline.original_character == "\n"
    assert newline.typed_character == "\n"
    assert newline.is_correct is True


def test_partial_input_reports_positional_progress() -> None:
    state = TypingEngine("abcdef").evaluate("abc")

    assert state.correct_character_count == 3
    assert state.incorrect_character_count == 0
    assert state.progress == 0.5
    assert state.is_complete is False


def test_wrong_characters_are_reported_by_position() -> None:
    state = TypingEngine("abcd").evaluate("axyd")

    assert [comparison.is_correct for comparison in state.comparisons] == [
        True,
        False,
        False,
        True,
    ]
    assert state.correct_character_count == 2
    assert state.incorrect_character_count == 2
    assert state.accuracy == 0.5
    assert state.is_complete is False


def test_correction_is_a_fresh_predictable_evaluation() -> None:
    engine = TypingEngine("기억")

    wrong = engine.evaluate("기엌")
    corrected = engine.evaluate("기억")
    deleted = engine.evaluate("기")

    assert wrong.incorrect_character_count == 1
    assert corrected.incorrect_character_count == 0
    assert corrected.is_complete is True
    assert deleted.typed_text == "기"
    assert deleted.progress == 0.5
    assert engine.original_text == "기억"


def test_input_longer_than_target_counts_overflow_as_incorrect() -> None:
    state = TypingEngine("abc").evaluate("abcde")

    assert state.correct_character_count == 3
    assert state.incorrect_character_count == 2
    assert state.progress == 1.0
    assert state.accuracy == pytest.approx(0.6)
    assert state.is_complete is False
    assert state.comparisons[-1].original_character is None


def test_elapsed_time_produces_typing_speed_metrics() -> None:
    state = TypingEngine("abcdefghij").evaluate("abcdefghij", elapsed_seconds=30)

    assert state.elapsed_seconds == 30
    assert state.characters_per_minute == 20.0
    assert state.words_per_minute == 4.0
    assert state.is_started is True


@pytest.mark.parametrize("elapsed_seconds", [-1, float("inf"), float("nan")])
def test_invalid_elapsed_time_is_rejected(elapsed_seconds: float) -> None:
    with pytest.raises(ValueError, match="finite non-negative"):
        TypingEngine("text").evaluate("text", elapsed_seconds=elapsed_seconds)


def test_state_and_engine_are_immutable() -> None:
    engine = TypingEngine("text")
    state = engine.evaluate("test")

    with pytest.raises(FrozenInstanceError):
        state.typed_text = "changed"  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        engine.original_text = "changed"  # type: ignore[misc]
