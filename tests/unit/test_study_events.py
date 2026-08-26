"""Unit tests for the extensible study-event lifecycle."""

from dataclasses import FrozenInstanceError

import pytest

from memory_typing.core import (
    EventAnswer,
    EventContext,
    EventEngine,
    EventPresentation,
    EventResult,
    ExactMatchEvent,
    StudyEvent,
)
from memory_typing.core.study_events import RandomSource
from memory_typing.domain import Sentence


def sentence(text: str = "기억을 연습한다.", *, identifier: str = "sentence-1") -> Sentence:
    return Sentence(identifier, "paragraph-1", 0, text)


class FixedRandom:
    def __init__(self, index: int) -> None:
        self.index = index
        self.stops: list[int] = []

    def randrange(self, stop: int) -> int:
        self.stops.append(stop)
        return self.index


class StubEvent(StudyEvent):
    def __init__(self, event_type: str, *, eligible: bool) -> None:
        self._event_type = event_type
        self.eligible = eligible
        self.prepared_with: RandomSource | None = None

    @property
    def event_type(self) -> str:
        return self._event_type

    def is_eligible(self, context: EventContext) -> bool:
        return self.eligible

    def prepare(self, context: EventContext, random_source: RandomSource) -> EventPresentation:
        self.prepared_with = random_source
        return EventPresentation(f"표시:{self.event_type}", "답을 입력하세요.")

    def evaluate(
        self,
        context: EventContext,
        presentation: EventPresentation,
        answer: EventAnswer,
    ) -> EventResult:
        return EventResult(
            self.event_type,
            context.sentence.id,
            answer.typed_text == self.event_type,
            1.0 if answer.typed_text == self.event_type else 0.0,
            answer.typed_text,
            self.event_type,
        )


def test_engine_filters_ineligible_events_before_preparing() -> None:
    unavailable = StubEvent("unavailable", eligible=False)
    available = StubEvent("available", eligible=True)
    random_source = FixedRandom(0)
    context = EventContext(sentence())
    engine = EventEngine((unavailable, available), random_source=random_source)

    prepared = engine.prepare(context)

    assert engine.eligible_event_types(context) == ("available",)
    assert prepared is not None
    assert prepared.event_type == "available"
    assert prepared.presentation.display_text == "표시:available"
    assert unavailable.prepared_with is None
    assert available.prepared_with is random_source
    assert random_source.stops == [1]


def test_engine_returns_none_when_no_event_is_eligible() -> None:
    engine = EventEngine((StubEvent("never", eligible=False),), seed=1)

    assert engine.prepare(EventContext(sentence())) is None


def test_engine_routes_committed_answer_and_returns_structured_result() -> None:
    engine = EventEngine((StubEvent("recall", eligible=True),), seed=1)
    prepared = engine.prepare(EventContext(sentence()))

    assert prepared is not None
    result = engine.evaluate(prepared, EventAnswer(typed_text="recall"))

    assert result == EventResult(
        event_type="recall",
        sentence_id="sentence-1",
        is_correct=True,
        score=1.0,
        typed_text="recall",
        expected_text="recall",
    )


def test_injected_random_source_deterministically_selects_an_eligible_event() -> None:
    first = StubEvent("first", eligible=True)
    second = StubEvent("second", eligible=True)
    random_source = FixedRandom(1)

    prepared = EventEngine((first, second), random_source=random_source).prepare(
        EventContext(sentence())
    )

    assert prepared is not None
    assert prepared.event_type == "second"
    assert random_source.stops == [2]


def test_seeded_engines_produce_the_same_selection_sequence() -> None:
    events = tuple(StubEvent(name, eligible=True) for name in ("a", "b", "c"))
    context = EventContext(sentence())
    first_engine = EventEngine(events, seed=42)
    second_engine = EventEngine(events, seed=42)

    first_sequence = [first_engine.prepare(context).event_type for _ in range(8)]  # type: ignore[union-attr]
    second_sequence = [second_engine.prepare(context).event_type for _ in range(8)]  # type: ignore[union-attr]

    assert first_sequence == second_sequence


def test_exact_match_event_keeps_original_display_and_typed_text_distinct() -> None:
    source_sentence = sentence("한글, English와 공백!\n")
    context = EventContext(source_sentence)
    engine = EventEngine((ExactMatchEvent(),), seed=0)
    prepared = engine.prepare(context)

    assert prepared is not None
    assert prepared.presentation.display_text == source_sentence.original_text
    wrong = engine.evaluate(prepared, EventAnswer("한글 English와 공백!"))
    correct = engine.evaluate(prepared, EventAnswer(source_sentence.original_text))

    assert wrong.is_correct is False
    assert wrong.score == 0.0
    assert correct.is_correct is True
    assert correct.score == 1.0
    assert source_sentence.original_text == "한글, English와 공백!\n"


def test_exact_match_event_is_not_eligible_for_empty_source() -> None:
    engine = EventEngine((ExactMatchEvent(),), seed=0)

    assert engine.prepare(EventContext(sentence(""))) is None


def test_event_values_are_immutable_and_context_is_validated() -> None:
    context = EventContext(sentence(), attempt_number=2)
    answer = EventAnswer("입력")

    with pytest.raises(FrozenInstanceError):
        answer.typed_text = "변경"  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        context.attempt_number = 3  # type: ignore[misc]
    with pytest.raises(ValueError, match="at least 1"):
        EventContext(sentence(), attempt_number=0)


@pytest.mark.parametrize("score", [-0.01, 1.01])
def test_result_rejects_invalid_score(score: float) -> None:
    with pytest.raises(ValueError, match="between"):
        EventResult("event", "sentence", False, score, "답", "정답")


def test_engine_rejects_ambiguous_configuration_and_event_types() -> None:
    event = StubEvent("same", eligible=True)

    with pytest.raises(ValueError, match="not both"):
        EventEngine((event,), random_source=FixedRandom(0), seed=1)
    with pytest.raises(ValueError, match="duplicate"):
        EventEngine((event, StubEvent("same", eligible=True)))
    with pytest.raises(ValueError, match="must not be empty"):
        EventEngine((StubEvent("", eligible=True),))
