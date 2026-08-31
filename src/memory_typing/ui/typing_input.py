"""Standard Qt text editor with observable IME composition state."""

from PySide6.QtCore import Signal
from PySide6.QtGui import QGuiApplication, QInputMethodEvent
from PySide6.QtWidgets import QPlainTextEdit


class ImeAwareTextEdit(QPlainTextEdit):
    """Preserve normal Qt editing while exposing whether preedit is active."""

    composition_state_changed = Signal(bool)
    preedit_text_changed = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self._has_preedit = False
        self._preedit_text = ""

    @property
    def has_preedit(self) -> bool:
        """Return whether the input method currently has unstable preedit text."""
        return self._has_preedit

    @property
    def preedit_text(self) -> str:
        """Return the current input-method composition without committing it."""
        return self._preedit_text

    def text_with_preedit(self) -> str:
        """Return a read-only candidate with preedit inserted at the Qt cursor."""
        committed_text = self.toPlainText()
        cursor = self.textCursor()
        if cursor.hasSelection():
            start = cursor.selectionStart()
            end = cursor.selectionEnd()
            return committed_text[:start] + self._preedit_text + committed_text[end:]
        position = cursor.position()
        return committed_text[:position] + self._preedit_text + committed_text[position:]

    def commit_preedit(self) -> None:
        """Ask the active Qt input method to commit its current composition."""
        if self._has_preedit:
            QGuiApplication.inputMethod().commit()

    def inputMethodEvent(self, event: QInputMethodEvent) -> None:  # noqa: N802
        """Let Qt process IME input and only observe its preedit state."""
        preedit_text = event.preeditString()
        has_preedit = bool(preedit_text)
        preedit_changed = preedit_text != self._preedit_text
        state_changed = has_preedit != self._has_preedit
        self._has_preedit = has_preedit
        self._preedit_text = preedit_text
        super().inputMethodEvent(event)
        if preedit_changed:
            self.preedit_text_changed.emit(preedit_text)
        if state_changed:
            self.composition_state_changed.emit(has_preedit)
