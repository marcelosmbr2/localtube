"""Barra lateral: logo, navegação entre telas e estado das ferramentas."""

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QFrame, QLabel

from localtube import __version__, icons, theme
from localtube.ui.widgets.common import ClickableFrame, dot, hbox, label, set_color, set_prop, vbox

NAV = [
    ("download", "Baixar", "download", "Ctrl+1"),
    ("convert", "Converter", "convert", "Ctrl+2"),
    ("queue", "Fila", "list", "Ctrl+3"),
    ("library", "Biblioteca", "folder", "Ctrl+4"),
]
SETTINGS = ("settings", "Configurações", "sliders", "Ctrl+,")


class NavItem(ClickableFrame):
    def __init__(self, key: str, text: str, icon_name: str, shortcut: str) -> None:
        super().__init__()
        self.setObjectName("NavItem")
        self.setFixedHeight(30)
        self.key = key
        self._icon_name = icon_name
        self._icon = QLabel()
        self._icon.setFixedSize(16, 16)
        self._text = label(text, weight=QFont.Weight.Medium)
        self.count = QLabel()
        self.count.setObjectName("NavCount")
        self.count.setFixedHeight(18)
        self.count.setMinimumWidth(18)
        self.count.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.count.hide()
        shortcut_lbl = label(shortcut, 11, theme.TEXT_9)
        self.setLayout(hbox(self._icon, self._text, None, self.count, shortcut_lbl, spacing=10,
                            margins=(10, 0, 10, 0)))
        self.set_active(False)

    def set_active(self, active: bool) -> None:
        set_prop(self, "active", active)
        set_color(self._text, theme.TEXT if active else theme.TEXT_4)
        self._icon.setPixmap(icons.pixmap(self._icon_name, theme.ACCENT if active else theme.TEXT_6, 16, 1.6))


class ToolStatus(QFrame):
    def __init__(self, name: str) -> None:
        super().__init__()
        self._dot = dot(theme.GREEN)
        self._version = label("", 10.5, theme.TEXT_8, mono=True)
        self.setLayout(hbox(self._dot, label(name, 11.5, theme.TEXT_6), None, self._version))

    def set_state(self, ok: bool, version: str | None) -> None:
        self._dot.setStyleSheet(f"background: {theme.GREEN if ok else theme.RED}; border-radius: 3px;")
        self._version.setText(version if ok and version else ("—" if ok else "ausente"))


class Sidebar(QFrame):
    navigate = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("Sidebar")
        self.setFixedWidth(220)

        logo = QLabel()
        logo.setFixedSize(22, 22)
        logo.setPixmap(icons.app_icon().pixmap(22, 22))
        brand = hbox(logo, label("LocalTube", 13, weight=QFont.Weight.DemiBold), None,
                     label(__version__, 11, theme.TEXT_8), spacing=9, margins=(8, 0, 8, 14))

        self.items: dict[str, NavItem] = {}
        layout = vbox(brand, spacing=2, margins=(10, 14, 10, 12))
        for key, text, icon_name, shortcut in NAV:
            layout.addWidget(self._make_item(key, text, icon_name, shortcut))
        layout.addStretch(1)
        layout.addWidget(self._make_item(*SETTINGS))

        self.ytdlp = ToolStatus("yt-dlp")
        self.ffmpeg = ToolStatus("ffmpeg")
        footer = QFrame()
        footer.setObjectName("SidebarFooter")
        footer.setLayout(vbox(self.ytdlp, self.ffmpeg, spacing=7, margins=(10, 12, 10, 2)))
        layout.addSpacing(10)
        layout.addWidget(footer)
        self.setLayout(layout)

    def _make_item(self, key: str, text: str, icon_name: str, shortcut: str) -> NavItem:
        item = NavItem(key, text, icon_name, shortcut)
        item.clicked.connect(lambda k=key: self.navigate.emit(k))
        self.items[key] = item
        return item

    def set_current(self, key: str) -> None:
        for k, item in self.items.items():
            item.set_active(k == key)

    def set_queue_count(self, count: int) -> None:
        badge = self.items["queue"].count
        badge.setText(str(count))
        badge.setVisible(count > 0)
