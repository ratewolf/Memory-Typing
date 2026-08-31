"""Main application window."""

from pathlib import Path

from PySide6.QtCore import QStandardPaths
from PySide6.QtWidgets import QMainWindow

from memory_typing.core import JsonImporter, JsonImportError
from memory_typing.domain import Book
from memory_typing.storage import BookRepository, Database, StudyRepository
from memory_typing.ui.typing_view import TypingView


class MainWindow(QMainWindow):
    """Top-level window for Memory Typing."""

    def __init__(self, database_path: str | Path | None = None) -> None:
        super().__init__()
        self.setWindowTitle("Memory Typing")
        self._database = Database(database_path or _default_database_path())
        self._book_repository = BookRepository(self._database)
        self._study_repository = StudyRepository(self._database)
        books = self._load_library()
        self.setCentralWidget(
            TypingView(
                books,
                content_store=self._book_repository,
                study_record_store=self._study_repository,
            )
        )
        self.resize(960, 640)

    def _load_library(self) -> tuple[Book, ...]:
        books = self._book_repository.list_all()
        if books:
            return books
        sample_book = _load_sample_book()
        if sample_book is None:
            return ()
        self._book_repository.add(sample_book)
        return (sample_book,)


def _default_database_path() -> Path:
    data_directory = QStandardPaths.writableLocation(
        QStandardPaths.StandardLocation.AppLocalDataLocation
    )
    if not data_directory:
        data_directory = str(Path.home() / ".memory-typing")
    return Path(data_directory) / "memory-typing.sqlite3"


def _load_sample_book() -> Book | None:
    sample_path = Path(__file__).resolve().parents[3] / "sample_data" / "korean_sample.json"
    try:
        return JsonImporter().import_file(sample_path)
    except (OSError, UnicodeError, JsonImportError):
        return None
