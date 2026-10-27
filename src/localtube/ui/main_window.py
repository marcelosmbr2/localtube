"""Janela principal: barra superior, barra lateral, telas e sobreposições."""

from collections.abc import Callable

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QMainWindow,
    QPushButton,
    QStackedWidget,
    QSystemTrayIcon,
    QWidget,
)

from localtube import icons, theme
from localtube.core.ytdlp import domain
from localtube.services import Services
from localtube.ui import desktop
from localtube.ui.widgets.common import hbox, icon_label, kbd, label, vbox
from localtube.ui.widgets.overlays import URL_RE, Command, CommandPalette, Toast
from localtube.ui.widgets.sidebar import Sidebar


class MainWindow(QMainWindow):
    def __init__(self, services: Services) -> None:
        super().__init__()
        self.services = services
        self.setWindowTitle("LocalTube")
        self.setWindowIcon(icons.app_icon())
        self.resize(1280, 820)
        self.setMinimumSize(1080, 640)

        central = QWidget()
        central.setObjectName("Central")
        self.setCentralWidget(central)

        self.sidebar = Sidebar()
        self.sidebar.navigate.connect(self.go)
        self.stack = QStackedWidget()
        self.pages: dict[str, QWidget] = {}
        self._build_pages()

        body = hbox(self.sidebar, self.stack, spacing=0)
        central.setLayout(vbox(self._top_bar(), body, spacing=0))

        self.toast_widget = Toast(central)
        self.palette = CommandPalette(central, self._commands)
        self.palette.inspect_requested.connect(self.inspect)

        self._shortcuts()
        services.tools_changed.connect(self._sync_tools)
        self._sync_tools()

        self._own_clipboard = ""
        QApplication.clipboard().dataChanged.connect(self._on_clipboard)
        self.tray = QSystemTrayIcon(icons.app_icon(), self)
        self.tray.setToolTip("LocalTube")
        downloads = services.downloads
        for signal in (downloads.job_added, downloads.job_changed, downloads.job_removed):
            signal.connect(self._sync_queue_count)
        downloads.job_finished.connect(
            lambda job: self.notify("Download concluído", job.request.title))
        self.go("download")

    # Construção ------------------------------------------------------------
    def _top_bar(self) -> QFrame:
        btn = QPushButton()
        btn.setObjectName("PaletteButton")
        btn.setFixedSize(360, 26)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        parts = (icon_label("search", theme.TEXT_7, 14, 1.7),
                 label("Buscar comandos ou colar um link…", 12, theme.TEXT_7), kbd("Ctrl K"))
        for part in parts:
            part.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        btn.setLayout(hbox(parts[0], parts[1], None, parts[2], spacing=8, margins=(10, 0, 6, 0)))
        btn.clicked.connect(lambda: self.palette.open())
        bar = QFrame()
        bar.setObjectName("TopBar")
        bar.setFixedHeight(40)
        bar.setLayout(hbox(None, btn, None))
        return bar

    def _build_pages(self) -> None:
        from localtube.ui.pages import build_pages

        for key, page in build_pages(self.services, self).items():
            self.pages[key] = page
            self.stack.addWidget(page)

    def _shortcuts(self) -> None:
        def add(seq: str, fn: Callable) -> None:
            sc = QShortcut(QKeySequence(seq), self)
            sc.setContext(Qt.ShortcutContext.WindowShortcut)
            sc.activated.connect(fn)

        for i, key in enumerate(["download", "convert", "queue", "library"], start=1):
            add(f"Ctrl+{i}", lambda k=key: self.go(k))
        add("Ctrl+,", lambda: self.go("settings"))
        add("Ctrl+K", self.palette.toggle)
        add("Ctrl+Return", self._primary_action)
        add("Ctrl+Enter", self._primary_action)

    def _commands(self) -> list[Command]:
        active = self.services.downloads.active_count()
        return [
            Command("Inspecionar link da área de transferência", "link", self.inspect_clipboard, "Ctrl+V"),
            Command("Converter arquivos…", "convert", lambda: self.go("convert"), "Ctrl+2"),
            Command("Mostrar fila", "list", lambda: self.go("queue"), f"{active} ativos"),
            Command("Abrir biblioteca", "library", lambda: self.go("library"), "Ctrl+4"),
            Command("Abrir pasta de downloads", "folder", self.open_download_dir),
            Command("Verificar atualizações do yt-dlp", "refresh", self.check_updates),
            Command("Configurações", "sliders", lambda: self.go("settings"), "Ctrl+,"),
        ]

    # Ações -----------------------------------------------------------------
    def go(self, key: str) -> None:
        self.palette.close_palette()
        self.stack.setCurrentWidget(self.pages[key])
        self.sidebar.set_current(key)
        page = self.pages[key]
        if hasattr(page, "on_shown"):
            page.on_shown()

    def toast(self, text: str, action: str = "", callback: Callable | None = None, error: bool = False) -> None:
        self.toast_widget.show_message(text, action, callback, error)

    def inspect(self, url: str) -> None:
        self.go("download")
        self.pages["download"].inspect(url)

    def inspect_clipboard(self) -> None:
        text = QApplication.clipboard().text().strip()
        if URL_RE.match(text):
            self.inspect(text)
        else:
            self.toast("A área de transferência não tem um link", error=True)

    def copy_text(self, text: str) -> None:
        self._own_clipboard = text
        QApplication.clipboard().setText(text)

    def notify(self, title: str, message: str) -> None:
        if not self.services.settings.get("notifications") or not QSystemTrayIcon.isSystemTrayAvailable():
            return
        self.tray.show()
        self.tray.showMessage(title, message, icons.app_icon(), 5000)

    def open_download_dir(self) -> None:
        desktop.open_folder(self.services.settings.get("download_dir"))
        self.toast("Pasta de downloads aberta")

    def _on_clipboard(self) -> None:
        text = QApplication.clipboard().text().strip()
        if (not self.services.settings.get("clipboard_monitor") or not URL_RE.match(text)
                or text == self._own_clipboard):
            return
        self._own_clipboard = text
        self.toast(f"Link copiado · {domain(text)}", "Inspecionar", lambda: self.inspect(text))

    def _sync_queue_count(self, *_args) -> None:
        self.sidebar.set_queue_count(self.services.downloads.active_count())

    def check_updates(self) -> None:
        self.go("settings")
        page = self.pages["settings"]
        if hasattr(page, "check_updates"):
            page.check_updates()

    def _primary_action(self) -> None:
        page = self.stack.currentWidget()
        if hasattr(page, "primary_action"):
            page.primary_action()

    def _sync_tools(self) -> None:
        self.sidebar.ytdlp.set_state(self.services.ytdlp_version is not None, self.services.ytdlp_version)
        ff = self.services.ffmpeg
        self.sidebar.ffmpeg.set_state(ff.ok, ff.version)

    # Eventos ---------------------------------------------------------------
    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if self.palette.isVisible():
            self.palette.setGeometry(self.centralWidget().rect())
        if self.toast_widget.isVisible():
            self.toast_widget.reposition()

    def closeEvent(self, event) -> None:
        for page in self.pages.values():
            if hasattr(page, "shutdown"):
                page.shutdown()
        self.services.shutdown()
        self.tray.hide()
        super().closeEvent(event)
