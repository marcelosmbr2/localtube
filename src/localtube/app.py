import sys

from PySide6.QtWidgets import QApplication

from localtube import __version__, theme
from localtube.services import Services
from localtube.settings import AppSettings
from localtube.ui.main_window import MainWindow


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("LocalTube")
    app.setOrganizationName("LocalTube")
    app.setApplicationVersion(__version__)
    app.setStyle("Fusion")

    theme.load_fonts()
    app.setFont(theme.ui_font(13))
    app.setStyleSheet(theme.build_stylesheet())

    services = Services(AppSettings())
    window = MainWindow(services)
    window.show()

    return app.exec()
