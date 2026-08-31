"""Pure Unicode string evaluation for typing practice."""

from dataclasses import dataclass
from math import isfinite


@dataclass(frozen=True, slots=True)
class CharacterComparison:
    """The positional comparison for one character of typed input."""

    index: int
    original_character: str | None
    typed_character: str
    is_correct: bool


@dataclass(frozen=True, slots=True)
class TypingState:
    """An immutable snapshot of a typing attempt."""

    original_text: str
    typed_text: str
    comparisons: tuple[CharacterComparison, ...]
    correct_character_count: int
    incorrect_character_count: int
    progress: float
    is_complete: bool
    accuracy: float
    elapsed_seconds: float
    characters_per_minute: float
    words_per_minute: float

    @property
    def is_started(self) -> bool:
        """Return whether the learner has entered at least one character."""
        return bool(self.typed_text)


@dataclass(frozen=True, slots=True)
class TypingEngine:
    """Compare committed Unicode input with an unmodified source text."""

    original_text: str

    def initial_state(self) -> TypingState:
        """Return the state before any input or elapsed time."""
        return self.evaluate("")

    def evaluate(self, typed_text: str, *, elapsed_seconds: float = 0.0) -> TypingState:
        """Evaluate a complete snapshot of committed text.

        ``elapsed_seconds`` is supplied by the caller so this engine remains independent
        from clocks and UI frameworks. Speed uses Unicode code points per minute; words
        per minute follows the conventional five-characters-per-word definition.
        """
        if not isfinite(elapsed_seconds) or elapsed_seconds < 0:
            raise ValueError("elapsed_seconds must be a finite non-negative number")

        comparisons = tuple(
            CharacterComparison(
                index=index,
                original_character=(
                    self.original_text[index] if index < len(self.original_text) else None
                ),
                typed_character=typed_character,
                is_correct=(
                    index < len(self.original_text) and typed_character == self.original_text[index]
                ),
            )
            for index, typed_character in enumerate(typed_text)
        )
        correct_count = sum(comparison.is_correct for comparison in comparisons)
        incorrect_count = len(comparisons) - correct_count
        progress = (
            1.0
            if not self.original_text
            else min(len(typed_text), len(self.original_text)) / len(self.original_text)
        )
        accuracy = 1.0 if not typed_text else correct_count / len(typed_text)
        characters_per_minute = (
            0.0 if elapsed_seconds == 0 else len(typed_text) * 60 / elapsed_seconds
        )

        return TypingState(
            original_text=self.original_text,
            typed_text=typed_text,
            comparisons=comparisons,
            correct_character_count=correct_count,
            incorrect_character_count=incorrect_count,
            progress=progress,
            is_complete=typed_text == self.original_text,
            accuracy=accuracy,
            elapsed_seconds=elapsed_seconds,
            characters_per_minute=characters_per_minute,
            words_per_minute=characters_per_minute / 5,
        )
