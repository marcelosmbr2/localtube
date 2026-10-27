from PySide6.QtCore import Qt
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QLabel, QMainWindow, QMessageBox


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("LocalTube")
        self.resize(1280, 800)

        label = QLabel("LocalTube")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setCentralWidget(label)

        self._create_menu()
        self.statusBar().showMessage("Pronto")

    def _create_menu(self) -> None:
        file_menu = self.menuBar().addMenu("&Arquivo")
        quit_action = QAction("&Sair", self)
        quit_action.setShortcut("Ctrl+Q")
        quit_action.triggered.connect(self.close)
        file_menu.addAction(quit_action)

        help_menu = self.menuBar().addMenu("A&juda")
        about_action = QAction("&Sobre", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)

    def _show_about(self) -> None:
        QMessageBox.about(self, "Sobre o LocalTube", "LocalTube 0.1.0")
