"""Extensible, framework-independent study-event lifecycle."""

from abc import ABC, abstractmethod
from collections.abc import Iterable
from dataclasses import dataclass
from random import Random
from typing import Protocol

from memory_typing.domain import Sentence


class RandomSource(Protocol):
    """Small random interface required by the event engine and events."""

    def randrange(self, stop: int) -> int:
        """Return an integer in ``range(stop)``."""
        ...


@dataclass(frozen=True, slots=True)
class EventContext:
    """Stable source data available while deciding and running an event."""

    sentence: Sentence
    previous_sentence: Sentence | None = None
    attempt_number: int = 1

    def __post_init__(self) -> None:
        if self.attempt_number < 1:
            raise ValueError("attempt_number must be at least 1")


@dataclass(frozen=True, slots=True)
class EventPresentation:
    """Data to display without changing the canonical source sentence."""

    display_text: str
    prompt: str


@dataclass(frozen=True, slots=True)
class EventAnswer:
    """Committed learner input submitted to an event."""

    typed_text: str


@dataclass(frozen=True, slots=True)
class EventResult:
    """Structured outcome returned by an event evaluation."""

    event_type: str
    sentence_id: str
    is_correct: bool
    score: float
    typed_text: str
    expected_text: str

    def __post_init__(self) -> None:
        if not 0.0 <= self.score <= 1.0:
            raise ValueError("score must be between 0.0 and 1.0")


class StudyEvent(ABC):
    """Contract implemented by every kind of study event."""

    @property
    @abstractmethod
    def event_type(self) -> str:
        """Return the stable event type identifier."""

    @abstractmethod
    def is_eligible(self, context: EventContext) -> bool:
        """Return whether this event may run for the supplied context."""

    @abstractmethod
    def prepare(self, context: EventContext, random_source: RandomSource) -> EventPresentation:
        """Build presentation data for an eligible event."""

    @abstractmethod
    def evaluate(
        self,
        context: EventContext,
        presentation: EventPresentation,
        answer: EventAnswer,
    ) -> EventResult:
        """Evaluate a committed answer against canonical or explicit answer data."""


@dataclass(frozen=True, slots=True)
class PreparedEvent:
    """One selected event and the immutable data needed to evaluate it."""

    event_type: str
    context: EventContext
    presentation: EventPresentation


class EventEngine:
    """Select eligible events and coordinate preparation and evaluation."""

    def __init__(
        self,
        events: Iterable[StudyEvent],
        *,
        random_source: RandomSource | None = None,
        seed: int | None = None,
    ) -> None:
        if random_source is not None and seed is not None:
            raise ValueError("provide random_source or seed, not both")

        event_by_type: dict[str, StudyEvent] = {}
        for event in events:
            if not event.event_type:
                raise ValueError("event_type must not be empty")
            if event.event_type in event_by_type:
                raise ValueError(f"duplicate event_type: {event.event_type}")
            event_by_type[event.event_type] = event

        self._events = tuple(event_by_type.values())
        self._event_by_type = event_by_type
        self._random_source = random_source if random_source is not None else Random(seed)

    def eligible_event_types(self, context: EventContext) -> tuple[str, ...]:
        """Return eligible event identifiers in registration order."""
        return tuple(event.event_type for event in self._events if event.is_eligible(context))

    def prepare(self, context: EventContext) -> PreparedEvent | None:
        """Select and prepare one eligible event, or return ``None`` when none apply."""
        eligible = tuple(event for event in self._events if event.is_eligible(context))
        if not eligible:
            return None
        event = eligible[self._random_source.randrange(len(eligible))]
        presentation = event.prepare(context, self._random_source)
        return PreparedEvent(event.event_type, context, presentation)

    def evaluate(self, prepared: PreparedEvent, answer: EventAnswer) -> EventResult:
        """Route an answer to the event that produced the presentation."""
        try:
            event = self._event_by_type[prepared.event_type]
        except KeyError as error:
            raise ValueError(f"unknown event_type: {prepared.event_type}") from error
        return event.evaluate(prepared.context, prepared.presentation, answer)


class ExactMatchEvent(StudyEvent):
    """Minimal example event that displays and checks the complete source sentence."""

    @property
    def event_type(self) -> str:
        return "exact_match"

    def is_eligible(self, context: EventContext) -> bool:
        return bool(context.sentence.original_text)

    def prepare(self, context: EventContext, random_source: RandomSource) -> EventPresentation:
        return EventPresentation(
            display_text=context.sentence.original_text,
            prompt="보이는 문장을 그대로 입력하세요.",
        )

    def evaluate(
        self,
        context: EventContext,
        presentation: EventPresentation,
        answer: EventAnswer,
    ) -> EventResult:
        expected_text = context.sentence.original_text
        is_correct = answer.typed_text == expected_text
        return EventResult(
            event_type=self.event_type,
            sentence_id=context.sentence.id,
            is_correct=is_correct,
            score=1.0 if is_correct else 0.0,
            typed_text=answer.typed_text,
            expected_text=expected_text,
        )
