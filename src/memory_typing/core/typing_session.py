"""Framework-independent navigation through a sequence of sentences."""

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Self

from memory_typing.core.typing_engine import TypingEngine, TypingState
from memory_typing.domain import Sentence


@dataclass(frozen=True, slots=True)
class SessionEvaluation:
    """Typing state tied to one stable sentence in a session."""

    sentence: Sentence
    sentence_number: int
    sentence_count: int
    typing_state: TypingState


class TypingSession:
    """Evaluate and advance through an ordered, non-empty sentence sequence."""

    def __init__(self, sentences: tuple[Sentence, ...]) -> None:
        if not sentences:
            raise ValueError("a typing session requires at least one sentence")
        self._sentences = sentences
        self._current_index = 0
        self._is_complete = False

    @classmethod
    def from_iterable(cls, sentences: Iterable[Sentence]) -> Self:
        """Create a session from any iterable of sentences."""
        return cls(tuple(sentences))

    @property
    def current_sentence(self) -> Sentence:
        """Return the sentence currently being studied."""
        return self._sentences[self._current_index]

    @property
    def is_complete(self) -> bool:
        """Return whether the final sentence has been completed."""
        return self._is_complete

    def evaluate(self, typed_text: str, *, elapsed_seconds: float = 0.0) -> SessionEvaluation:
        """Evaluate committed Unicode text for the current sentence."""
        state = TypingEngine(self.current_sentence.original_text).evaluate(
            typed_text, elapsed_seconds=elapsed_seconds
        )
        return SessionEvaluation(
            sentence=self.current_sentence,
            sentence_number=self._current_index + 1,
            sentence_count=len(self._sentences),
            typing_state=state,
        )

    def advance_if_complete(self, evaluation: SessionEvaluation) -> bool:
        """Accept a current completed evaluation and move forward if possible."""
        if evaluation.sentence.id != self.current_sentence.id:
            raise ValueError("evaluation does not belong to the current sentence")
        if not evaluation.typing_state.is_complete:
            return False
        if self._current_index == len(self._sentences) - 1:
            self._is_complete = True
        else:
            self._current_index += 1
        return True
