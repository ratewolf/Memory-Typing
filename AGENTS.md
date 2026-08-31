# AGENTS.md

## Project

This repository contains a personal desktop application called
"Memory Typing".

The application helps the user memorize books by typing their contents.

The core study loop is:

Book
→ Chapter
→ Paragraph / Sentence
→ Typing
→ Study Events
→ Quiz
→ Result
→ Review

This is a personal offline-first desktop application.

Primary language of the UI is Korean.

---

## Technology

Use:

- Python 3.12 or newer
- PySide6 for desktop UI
- SQLite for persistent local storage
- pytest for tests
- ruff for linting/formatting
- pyproject.toml for project configuration

Avoid unnecessary dependencies.

Do not introduce web servers, cloud databases, accounts, telemetry,
analytics, or network requirements unless explicitly requested.

The application should work fully offline.

---

## Architecture

Keep business logic independent from PySide6 whenever possible.

Use these broad layers:

- domain/
  Pure data models and domain concepts.

- core/
  Typing, scoring, event, quiz, and review logic.

- storage/
  SQLite and persistence logic.

- ui/
  PySide6 views and widgets.

UI classes must not contain substantial study logic.

Core logic should be testable without launching Qt.

---

## Critical Text Model Rule

Always distinguish:

- original_text
- display_text
- typed_text

They are not interchangeable.

`original_text` is the canonical source text.

`display_text` is what is currently shown to the learner and may contain
blanks, hints, hidden words, initials, or other event transformations.

`typed_text` is the user's input.

Never destroy or mutate `original_text` merely to create a study event.

Answer evaluation must ultimately refer to `original_text` or an explicit
event answer specification.

---

## Korean IME Requirement

Korean input correctness is a first-class requirement.

Do not implement Hangul input by interpreting individual physical
keypresses.

Do not assume one key press equals one Unicode character.

Qt input methods may have composition/preedit and committed text states.

Prefer standard Qt text editing behavior.

Study evaluation should operate on committed text whenever practical.

Do not break Korean IME composition when adding:

- correctness highlighting
- cursor control
- keyboard shortcuts
- auto-advance
- event transitions

Manual testing on a Korean IME must be included in relevant QA notes.

---

## Typing Engine

TypingEngine must not depend on PySide6.

It should be responsible for concepts such as:

- target text
- typed text
- correct character count
- incorrect character count
- current progress
- completion
- accuracy
- elapsed time
- typing speed

Do not let the UI independently reimplement these calculations.

Prefer pure functions and deterministic behavior where possible.

---

## Study Event Architecture

Study events must be extensible.

Do not hard-code all study events directly into TypingView.

Use an event abstraction such as:

StudyEvent
EventContext
EventResult
EventEngine

Expected event types eventually include:

- blank
- sentence recall
- keyword recall
- previous sentence recall
- initial-consonant hint
- hidden/vanishing text
- quiz
- review

An event must be able to:

1. decide whether it is eligible,
2. prepare its presentation,
3. receive an answer,
4. evaluate the answer,
5. return a structured result.

Random behavior must be injectable or seedable so tests remain deterministic.

---

## Quiz System

Support at least:

- multiple choice
- short answer

Quiz content is authored by the user.

Do not require AI or network access to create or grade quizzes.

A quiz should be attachable to:

- a book
- a chapter
- optionally a specific passage

---

## Content Model

Use stable IDs.

Expected hierarchy:

Book
→ Chapter
→ Paragraph
→ Sentence

The system must preserve source ordering.

Do not couple progress records to fragile list indexes when a stable ID can
be used instead.

---

## Persistence

Use SQLite.

Database access must be isolated in storage/.

Schema changes should be explicit and migration-friendly.

Store at least enough information to eventually support:

- books
- chapters
- sentences
- quizzes
- study sessions
- sentence attempts
- event attempts
- quiz attempts
- review statistics

Never delete user study history as a side effect of importing or editing a
book unless explicitly requested.

---

## Review Model

Design the data model so that each sentence can eventually have a mastery
or weakness score.

Possible signals include:

- typing accuracy
- typing attempts
- blank-event success rate
- recall success rate
- quiz errors
- last studied time

Do not prematurely implement a complicated spaced-repetition algorithm.

Start simple and keep the scheduler replaceable.

---

## Testing

For every change:

1. add or update relevant tests,
2. run the most targeted tests,
3. run the full test suite when practical,
4. run lint checks,
5. report what was verified.

Core behavior should have unit tests.

Important edge cases include:

- empty strings
- punctuation
- whitespace
- newlines
- Korean text
- mixed Korean/English text
- corrections/backspace
- partially typed text
- exact completion
- event boundaries

Never claim something works unless it was tested or explicitly identify it
as requiring manual verification.

---

## Development Style

Prefer small, cohesive modules.

Prefer dataclasses or similarly simple models when appropriate.

Use type hints.

Avoid premature abstraction except where architecture explicitly requires it.

Do not create giant manager classes.

Do not duplicate domain logic in the UI.

Do not silently change unrelated code.

Keep changes scoped to the current requested task.

---

## UI Principles

This is a focused reading and typing application.

Prefer:

- minimal distraction
- high text readability
- keyboard-first interaction
- comfortable line spacing
- clear current position
- obvious errors without excessive animation

Avoid:

- unnecessary gradients
- excessive cards
- dashboard clutter
- gamification that interferes with reading
- modal dialogs for routine actions

UI language should default to Korean.

---

## Delivery Rule

For every implementation task:

1. inspect the existing repository first,
2. identify relevant existing abstractions,
3. implement the smallest coherent change,
4. add tests,
5. run validation,
6. fix failures caused by the change,
7. summarize changed files and validation results.

Do not merely describe code that should be written.
Actually implement it.

When requirements are ambiguous, prefer the simplest design compatible
with this document and docs/PRODUCT_SPEC.md.

Do not start unrelated future phases unless specifically requested.