"""Main application window."""

from pathlib import Path

from PySide6.QtWidgets import QMainWindow

from memory_typing.core import JsonImporter, JsonImportError
from memory_typing.domain import Book
from memory_typing.ui.typing_view import TypingView


class MainWindow(QMainWindow):
    """Top-level window for Memory Typing."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Memory Typing")
        sample_book = _load_sample_book()
        self.setCentralWidget(TypingView((sample_book,) if sample_book is not None else ()))
        self.resize(960, 640)


def _load_sample_book() -> Book | None:
    sample_path = Path(__file__).resolve().parents[3] / "sample_data" / "korean_sample.json"
    try:
        return JsonImporter().import_file(sample_path)
    except (OSError, UnicodeError, JsonImportError):
        return None
