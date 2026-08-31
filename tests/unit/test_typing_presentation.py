"""Tests for UI-independent target text presentation mapping."""

from memory_typing.core import TypingEngine
from memory_typing.ui.typing_presentation import TextSegment, TextStatus, build_text_segments


def test_segments_use_engine_comparisons_for_correct_incorrect_and_remaining() -> None:
    state = TypingEngine("가나다라마바사").evaluate("가X다")

    assert build_text_segments(state) == (
        TextSegment("가", TextStatus.CORRECT),
        TextSegment("나", TextStatus.INCORRECT),
        TextSegment("다", TextStatus.CORRECT),
        TextSegment("라마바사", TextStatus.REMAINING),
    )


def test_overflow_input_does_not_change_original_target_segments() -> None:
    state = TypingEngine("abc").evaluate("abc extra")

    assert build_text_segments(state) == (TextSegment("abc", TextStatus.CORRECT),)
    assert state.incorrect_character_count == 6


def test_empty_target_has_no_segments() -> None:
    assert build_text_segments(TypingEngine("").initial_state()) == ()
