"""Headless integration coverage for UI-to-SQLite persistence wiring."""

import json
import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QFileDialog

from memory_typing.storage import BookRepository, Database, StudyRepository
from memory_typing.ui.main_window import MainWindow


def imported_book_data() -> dict[str, object]:
    return {
        "format_version": 1,
        "book": {
            "id": "persistent-book",
            "title": "영구 저장 책",
            "chapters": [
                {
                    "id": "persistent-chapter",
                    "title": "저장 장",
                    "paragraphs": [
                        {
                            "id": "persistent-paragraph",
                            "sentences": [
                                {"id": "persistent-sentence-1", "text": "영구 저장 문장."},
                                {"id": "persistent-sentence-2", "text": "두 번째 문장."},
                            ],
                        }
                    ],
                }
            ],
        },
    }


def test_imported_book_and_completed_attempt_survive_window_restart(
    tmp_path: Path, monkeypatch
) -> None:
    app = QApplication.instance() or QApplication([])
    database_path = tmp_path / "memory-typing.sqlite3"
    import_path = tmp_path / "persistent.json"
    import_path.write_text(json.dumps(imported_book_data(), ensure_ascii=False), encoding="utf-8")
    monkeypatch.setattr(
        QFileDialog,
        "getOpenFileName",
        lambda *args, **kwargs: (str(import_path), "JSON 파일 (*.json)"),
    )
    window = MainWindow(database_path)
    view = window.centralWidget()

    view._import_json()
    assert view._book_combo.currentText() == "영구 저장 책"
    view._typing_input.setPlainText("영구 저장 문장.")
    app.processEvents()
    app.processEvents()
    view._typing_input.setPlainText("두 번째 문장.")
    app.processEvents()
    app.processEvents()

    database = Database(database_path)
    assert BookRepository(database).get("persistent-book") is not None
    sessions = StudyRepository(database).list_sessions(chapter_id="persistent-chapter")
    assert len(sessions) == 1
    assert sessions[0].completed_at is not None
    attempts = StudyRepository(database).list_sentence_attempts(sessions[0].id)
    assert len(attempts) == 2
    assert attempts[0].sentence_id == "persistent-sentence-1"
    assert attempts[0].typed_text == "영구 저장 문장."
    assert attempts[1].sentence_id == "persistent-sentence-2"

    window.close()
    restored_window = MainWindow(database_path)
    restored_view = restored_window.centralWidget()
    titles = [
        restored_view._book_combo.itemText(index) for index in range(len(restored_view._books))
    ]
    assert "영구 저장 책" in titles
    restored_window.close()
