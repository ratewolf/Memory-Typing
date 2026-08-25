"""Qt-independent presentation mapping for typing feedback."""

from dataclasses import dataclass
from enum import Enum

from memory_typing.core import TypingState


class TextStatus(Enum):
    """Visual status of a target text segment."""

    CORRECT = "correct"
    INCORRECT = "incorrect"
    REMAINING = "remaining"


@dataclass(frozen=True, slots=True)
class TextSegment:
    """A consecutive target substring sharing one visual status."""

    text: str
    status: TextStatus


def build_text_segments(state: TypingState) -> tuple[TextSegment, ...]:
    """Map engine comparisons to grouped target segments without re-comparing text."""
    statuses = [
        (TextStatus.CORRECT if comparison.is_correct else TextStatus.INCORRECT)
        for comparison in state.comparisons
        if comparison.original_character is not None
    ]
    statuses.extend(TextStatus.REMAINING for _ in range(len(state.original_text) - len(statuses)))

    segments: list[TextSegment] = []
    for character, status in zip(state.original_text, statuses, strict=True):
        if segments and segments[-1].status is status:
            previous = segments[-1]
            segments[-1] = TextSegment(previous.text + character, status)
        else:
            segments.append(TextSegment(character, status))
    return tuple(segments)
