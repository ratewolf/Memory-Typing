"""Main application window."""

from PySide6.QtWidgets import QLabel, QMainWindow


class MainWindow(QMainWindow):
    """Top-level window for Memory Typing."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Memory Typing")
        self.setCentralWidget(QLabel("Memory Typing"))
        self.resize(800, 600)
