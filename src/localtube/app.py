import sys

from PySide6.QtWidgets import QApplication

from localtube import __version__
from localtube.main_window import MainWindow


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("LocalTube")
    app.setApplicationVersion(__version__)

    window = MainWindow()
    window.show()

    return app.exec()
