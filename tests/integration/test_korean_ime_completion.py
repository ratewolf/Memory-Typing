"""Headless checks for completing a sentence from Korean IME preedit text."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtGui import QInputMethodEvent, QTextCursor
from PySide6.QtWidgets import QApplication

from memory_typing.domain import Book, Chapter, Paragraph, Sentence
from memory_typing.ui.typing_input import ImeAwareTextEdit
from memory_typing.ui.typing_view import TypingView


def korean_book() -> Book:
    sentence = Sentence("sentence", "paragraph", 0, "한글")
    paragraph = Paragraph("paragraph", "chapter", 0, sentence.original_text, (sentence,))
    chapter = Chapter("chapter", "book", 0, "한글 장", paragraph.original_text, (paragraph,))
    return Book("book", "한글 책", chapter.original_text, (chapter,))


def test_matching_final_preedit_commits_and_advances_without_space(monkeypatch) -> None:
    app = QApplication.instance() or QApplication([])
    view = TypingView((korean_book(),))

    def commit_synthetic_preedit(editor: ImeAwareTextEdit) -> None:
        committed_text = editor.preedit_text
        event = QInputMethodEvent()
        event.setCommitString(committed_text)
        QApplication.sendEvent(editor, event)

    monkeypatch.setattr(ImeAwareTextEdit, "commit_preedit", commit_synthetic_preedit)
    view._typing_input.setPlainText("한")
    view._typing_input.moveCursor(QTextCursor.MoveOperation.End)
    QApplication.sendEvent(view._typing_input, QInputMethodEvent("글", []))

    for _ in range(4):
        app.processEvents()

    assert view._typing_input.toPlainText() == "한글"
    assert view._typing_input.isEnabled() is False
    assert view._position_label.text() == "완료 · 1개 문장을 모두 입력했습니다."


def test_non_matching_preedit_remains_in_composition(monkeypatch) -> None:
    app = QApplication.instance() or QApplication([])
    view = TypingView((korean_book(),))
    commit_calls = 0

    def count_commit(editor: ImeAwareTextEdit) -> None:
        nonlocal commit_calls
        commit_calls += 1

    monkeypatch.setattr(ImeAwareTextEdit, "commit_preedit", count_commit)
    view._typing_input.setPlainText("한")
    view._typing_input.moveCursor(QTextCursor.MoveOperation.End)
    QApplication.sendEvent(view._typing_input, QInputMethodEvent("국", []))
    app.processEvents()

    assert commit_calls == 0
    assert view._typing_input.has_preedit is True
    assert view._typing_input.toPlainText() == "한"
    assert view._position_label.text() == "현재 문장 1 / 1"
