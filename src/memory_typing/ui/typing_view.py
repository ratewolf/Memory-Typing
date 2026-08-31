"""First usable book, chapter, and sentence typing screen."""

from html import escape
from pathlib import Path
from time import monotonic

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from memory_typing.core import JsonImporter, JsonImportError, SessionEvaluation, TypingSession
from memory_typing.domain import Book, Chapter
from memory_typing.ui.typing_input import ImeAwareTextEdit
from memory_typing.ui.typing_presentation import TextSegment, TextStatus, build_text_segments

_SEGMENT_STYLES = {
    TextStatus.CORRECT: "color: #16713a; font-weight: 600;",
    TextStatus.INCORRECT: "color: #b42318; text-decoration: underline;",
    TextStatus.REMAINING: "color: #667085;",
}


class TypingView(QWidget):
    """Select content and type the current sentence using standard Qt editing."""

    def __init__(self, books: tuple[Book, ...] = ()) -> None:
        super().__init__()
        self._books = list(books)
        self._session: TypingSession | None = None
        self._last_evaluation: SessionEvaluation | None = None
        self._started_at: float | None = None
        self._changing_sentence = False

        self._book_combo = QComboBox()
        self._book_combo.setAccessibleName("책 선택")
        self._chapter_combo = QComboBox()
        self._chapter_combo.setAccessibleName("장 선택")
        self._import_button = QPushButton("JSON 가져오기")
        self._position_label = QLabel("학습할 책과 장을 선택하세요.")
        self._target_label = QLabel()
        self._target_label.setTextFormat(Qt.TextFormat.RichText)
        self._target_label.setWordWrap(True)
        self._target_label.setMinimumHeight(120)
        self._typing_input = ImeAwareTextEdit()
        self._typing_input.setAccessibleName("문장 입력")
        self._typing_input.setPlaceholderText("현재 문장을 그대로 입력하세요.")
        self._typing_input.setFixedHeight(100)
        self._progress = QProgressBar()
        self._progress.setRange(0, 100)
        self._status_label = QLabel("정확 0 · 오류 0 · 정확도 100.0%")

        selectors = QHBoxLayout()
        selectors.addWidget(QLabel("책"))
        selectors.addWidget(self._book_combo, 2)
        selectors.addWidget(QLabel("장"))
        selectors.addWidget(self._chapter_combo, 2)
        selectors.addWidget(self._import_button)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 24, 32, 24)
        layout.setSpacing(16)
        layout.addLayout(selectors)
        layout.addWidget(self._position_label)
        layout.addWidget(self._target_label)
        layout.addWidget(self._typing_input)
        layout.addWidget(self._progress)
        layout.addWidget(self._status_label)

        self._book_combo.currentIndexChanged.connect(self._select_book)
        self._chapter_combo.currentIndexChanged.connect(self._select_chapter)
        self._import_button.clicked.connect(self._import_json)
        self._typing_input.textChanged.connect(self._on_text_changed)
        self._typing_input.composition_state_changed.connect(self._on_composition_changed)

        self._populate_books()

    def _populate_books(self) -> None:
        self._book_combo.blockSignals(True)
        self._book_combo.clear()
        for book in self._books:
            self._book_combo.addItem(book.title)
        self._book_combo.blockSignals(False)
        self._select_book(self._book_combo.currentIndex())

    def _select_book(self, index: int) -> None:
        self._chapter_combo.blockSignals(True)
        self._chapter_combo.clear()
        if 0 <= index < len(self._books):
            for chapter in self._books[index].chapters:
                self._chapter_combo.addItem(chapter.title)
        self._chapter_combo.blockSignals(False)
        self._select_chapter(self._chapter_combo.currentIndex())

    def _select_chapter(self, index: int) -> None:
        book_index = self._book_combo.currentIndex()
        if not (0 <= book_index < len(self._books)):
            self._set_unavailable("학습할 책을 선택하세요.")
            return
        chapters = self._books[book_index].chapters
        if not (0 <= index < len(chapters)):
            self._set_unavailable("학습할 장을 선택하세요.")
            return
        self._start_chapter(chapters[index])

    def _start_chapter(self, chapter: Chapter) -> None:
        sentences = tuple(
            sentence for paragraph in chapter.paragraphs for sentence in paragraph.sentences
        )
        if not sentences:
            self._set_unavailable("이 장에는 입력할 문장이 없습니다.")
            return
        self._session = TypingSession(sentences)
        self._show_current_sentence()

    def _show_current_sentence(self) -> None:
        if self._session is None:
            return
        self._changing_sentence = True
        self._typing_input.clear()
        self._changing_sentence = False
        self._typing_input.setEnabled(True)
        self._started_at = None
        evaluation = self._session.evaluate("")
        self._last_evaluation = evaluation
        self._render(evaluation)
        self._typing_input.setFocus()

    def _set_unavailable(self, message: str) -> None:
        self._session = None
        self._last_evaluation = None
        self._position_label.setText(message)
        self._target_label.clear()
        self._typing_input.clear()
        self._typing_input.setEnabled(False)
        self._progress.setValue(0)

    def _on_text_changed(self) -> None:
        if self._changing_sentence or self._session is None or self._session.is_complete:
            return
        typed_text = self._typing_input.toPlainText()
        if typed_text and self._started_at is None:
            self._started_at = monotonic()
        elapsed_seconds = 0.0 if self._started_at is None else monotonic() - self._started_at
        evaluation = self._session.evaluate(typed_text, elapsed_seconds=elapsed_seconds)
        self._last_evaluation = evaluation
        self._render(evaluation)
        if evaluation.typing_state.is_complete:
            QTimer.singleShot(0, lambda: self._advance_after_commit(evaluation))

    def _on_composition_changed(self, has_preedit: bool) -> None:
        if not has_preedit:
            self._on_text_changed()

    def _advance_after_commit(self, evaluation: SessionEvaluation) -> None:
        if (
            self._session is None
            or self._typing_input.has_preedit
            or self._last_evaluation is not evaluation
            or self._typing_input.toPlainText() != evaluation.typing_state.typed_text
        ):
            return
        if not self._session.advance_if_complete(evaluation):
            return
        if self._session.is_complete:
            self._typing_input.setEnabled(False)
            self._position_label.setText(
                f"완료 · {evaluation.sentence_count}개 문장을 모두 입력했습니다."
            )
            return
        self._show_current_sentence()

    def _render(self, evaluation: SessionEvaluation) -> None:
        state = evaluation.typing_state
        self._position_label.setText(
            f"현재 문장 {evaluation.sentence_number} / {evaluation.sentence_count}"
        )
        self._target_label.setText(_segments_to_html(build_text_segments(state)))
        self._progress.setValue(round(state.progress * 100))
        self._status_label.setText(
            f"정확 {state.correct_character_count} · 오류 {state.incorrect_character_count} "
            f"· 정확도 {state.accuracy * 100:.1f}%"
        )

    def _import_json(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "학습할 JSON 파일 선택", "", "JSON 파일 (*.json)"
        )
        if not path:
            return
        try:
            book = JsonImporter().import_file(Path(path))
        except (OSError, UnicodeError, JsonImportError) as error:
            QMessageBox.warning(self, "가져오기 실패", f"JSON 파일을 읽을 수 없습니다.\n{error}")
            return
        self._books.append(book)
        self._book_combo.addItem(book.title)
        self._book_combo.setCurrentIndex(len(self._books) - 1)


def _segments_to_html(segments: tuple[TextSegment, ...]) -> str:
    spans = "".join(
        f'<span style="{_SEGMENT_STYLES[segment.status]}">'
        f"{_preserve_whitespace(segment.text)}</span>"
        for segment in segments
    )
    return f'<div style="font-size: 22px; line-height: 1.6;">{spans}</div>'


def _preserve_whitespace(text: str) -> str:
    return escape(text).replace(" ", "&nbsp;").replace("\t", "&nbsp;" * 4).replace("\n", "<br>")
