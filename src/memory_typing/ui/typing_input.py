"""Standard Qt text editor with observable IME composition state."""

from PySide6.QtCore import Signal
from PySide6.QtGui import QInputMethodEvent
from PySide6.QtWidgets import QPlainTextEdit


class ImeAwareTextEdit(QPlainTextEdit):
    """Preserve normal Qt editing while exposing whether preedit is active."""

    composition_state_changed = Signal(bool)

    def __init__(self) -> None:
        super().__init__()
        self._has_preedit = False

    @property
    def has_preedit(self) -> bool:
        """Return whether the input method currently has unstable preedit text."""
        return self._has_preedit

    def inputMethodEvent(self, event: QInputMethodEvent) -> None:  # noqa: N802
        """Let Qt process IME input and only observe its preedit state."""
        has_preedit = bool(event.preeditString())
        if has_preedit != self._has_preedit:
            self._has_preedit = has_preedit
            self.composition_state_changed.emit(has_preedit)
        super().inputMethodEvent(event)
