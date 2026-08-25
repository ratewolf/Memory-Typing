"""Application entry point."""

import sys
from collections.abc import Sequence

from PySide6.QtWidgets import QApplication

from memory_typing.ui.main_window import MainWindow


def main(argv: Sequence[str] | None = None) -> int:
    """Create and run the Qt application."""
    app = QApplication(list(argv) if argv is not None else sys.argv)
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
