"""Toast e paleta de comandos, desenhados por cima do conteúdo da janela."""

import re
from collections.abc import Callable
from dataclasses import dataclass

from PySide6.QtCore import QEvent, QObject, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QFrame, QGraphicsDropShadowEffect, QLabel, QLineEdit, QWidget

from localtube import icons, theme
from localtube.ui.widgets.common import (
    ClickableFrame,
    button,
    discard,
    hbox,
    icon_label,
    kbd,
    label,
    section_label,
    set_color,
    set_prop,
    vbox,
)

URL_RE = re.compile(r"^https?://\S+$", re.IGNORECASE)


def _shadow(widget: QWidget, blur: int, dy: int, alpha: int) -> None:
    effect = QGraphicsDropShadowEffect(widget)
    effect.setBlurRadius(blur)
    effect.setOffset(0, dy)
    effect.setColor(QColor(0, 0, 0, alpha))
    widget.setGraphicsEffect(effect)


class Toast(QFrame):
    DURATION_MS = 3200

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.setObjectName("Toast")
        check = QLabel()
        check.setFixedSize(18, 18)
        check.setPixmap(icons.pixmap("check", theme.GREEN_TEXT, 11, 2.6))
        check.setAlignment(Qt.AlignmentFlag.AlignCenter)
        check.setStyleSheet("background: rgba(79,191,135,.15); border-radius: 9px;")
        self._icon = check
        self._text = label("", 12.5, theme.TEXT_2)
        self._action = button("", "ghost")
        self._action.setFixedHeight(24)
        self._action.setStyleSheet(f"color: {theme.ACCENT_TEXT}; font-weight: 500;")
        self._action.clicked.connect(self._run_action)
        self._callback: Callable | None = None
        self.setLayout(hbox(check, self._text, self._action, spacing=12, margins=(12, 10, 10, 10)))
        _shadow(self, 32, 12, 128)
        self._timer = QTimer(self, singleShot=True, interval=self.DURATION_MS, timeout=self.hide)
        self.hide()

    def show_message(self, text: str, action: str = "", callback: Callable | None = None,
                     error: bool = False) -> None:
        self._text.setText(text)
        self._callback = callback
        self._action.setText(action)
        self._action.setVisible(bool(action))
        if error:
            self._icon.setPixmap(icons.pixmap("alert", theme.RED_TEXT, 12, 2.2))
            self._icon.setStyleSheet("background: rgba(229,72,77,.15); border-radius: 9px;")
        else:
            self._icon.setPixmap(icons.pixmap("check", theme.GREEN_TEXT, 11, 2.6))
            self._icon.setStyleSheet("background: rgba(79,191,135,.15); border-radius: 9px;")
        self.adjustSize()
        self.reposition()
        self.show()
        self.raise_()
        self._timer.start(self.DURATION_MS * (2 if action else 1))

    def reposition(self) -> None:
        parent = self.parentWidget()
        self.move(parent.width() - self.width() - 20, parent.height() - self.height() - 74)

    def _run_action(self) -> None:
        self.hide()
        if self._callback:
            self._callback()


@dataclass
class Command:
    label: str
    icon: str
    run: Callable[[], None]
    hint: str = ""


class PaletteItem(ClickableFrame):
    def __init__(self, command: Command) -> None:
        super().__init__()
        self.setObjectName("PaletteItem")
        self.setFixedHeight(36)
        self.command = command
        box = QFrame()
        box.setObjectName("PaletteIcon")
        box.setFixedSize(24, 24)
        self._icon = icon_label(command.icon, theme.TEXT_4, 13, 1.8)
        box.setLayout(hbox(self._icon))
        box.layout().setAlignment(Qt.AlignmentFlag.AlignCenter)
        text = label(command.label, color=theme.TEXT_2)
        hint = label(command.hint, 11.5, theme.TEXT_7)
        self.setLayout(hbox(box, text, None, hint, spacing=12, margins=(10, 0, 10, 0)))

    def set_active(self, active: bool) -> None:
        set_prop(self, "active", active)
        self._icon.setPixmap(icons.pixmap(self.command.icon, theme.ACCENT if active else theme.TEXT_4, 13, 1.8))


class CommandPalette(QWidget):
    """Sobreposição com busca de comandos; um link colado vira 'Inspecionar …'."""

    inspect_requested = Signal(str)

    def __init__(self, parent: QWidget, commands: Callable[[], list[Command]]) -> None:
        super().__init__(parent)
        self._commands = commands
        self._items: list[PaletteItem] = []
        self._selected = 0

        self.panel = QFrame(self)
        self.panel.setObjectName("PalettePanel")
        self.panel.setFixedWidth(600)
        _shadow(self.panel, 80, 30, 150)

        self.input = QLineEdit()
        self.input.setProperty("bare", True)
        self.input.setFont(theme.ui_font(14))
        self.input.setPlaceholderText("Buscar comandos ou colar um link…")
        self.input.textChanged.connect(self._rebuild)
        self.input.installEventFilter(self)
        header = QFrame()
        header.setObjectName("PaletteHeader")
        header.setFixedHeight(50)
        header.setLayout(hbox(icon_label("search", theme.TEXT_7, 16, 1.7), self.input, kbd("esc"),
                              spacing=12, margins=(16, 0, 16, 0)))

        self.group = section_label("Sugestões")
        set_color(self.group, theme.TEXT_8)
        self.list_layout = vbox(spacing=1)
        body = QFrame()
        body.setLayout(vbox(self.group, self.list_layout, spacing=0, margins=(6, 6, 6, 6)))
        self.group.setContentsMargins(10, 8, 10, 6)

        footer = QFrame()
        footer.setObjectName("PaletteFooter")
        footer.setFixedHeight(36)
        hints = hbox(label("Abrir ", 11.5, theme.TEXT_7), label("↵", 11.5, theme.TEXT_4), 14,
                     label("Navegar ", 11.5, theme.TEXT_7), label("↑↓", 11.5, theme.TEXT_4), spacing=0)
        footer.setLayout(hbox(label("LocalTube", 11.5, theme.TEXT_7), None, hints, margins=(14, 0, 14, 0)))

        self.panel.setLayout(vbox(header, body, footer, spacing=0))
        self.hide()

    # API -----------------------------------------------------------------
    def open(self) -> None:
        self.setGeometry(self.parentWidget().rect())
        self.input.clear()
        self._rebuild()
        self.show()
        self.raise_()
        self.input.setFocus()

    def close_palette(self) -> None:
        self.hide()

    def toggle(self) -> None:
        self.close_palette() if self.isVisible() else self.open()

    # Internos ------------------------------------------------------------
    def _rebuild(self) -> None:
        query = self.input.text().strip()
        commands = self._commands()
        if URL_RE.match(query):
            short = re.sub(r"^https?://(www\.)?", "", query)[:48]
            commands = [Command(f"Inspecionar {short}", "link", lambda q=query: self.inspect_requested.emit(q), "↵")]
            group = "Link"
        elif query:
            commands = [c for c in commands if query.lower() in c.label.lower()]
            group = "Resultados"
        else:
            group = "Sugestões"
        self.group.setText(group)
        for item in self._items:
            discard(item)
        self._items = []
        for command in commands:
            item = PaletteItem(command)
            item.clicked.connect(lambda c=command: self._run(c))
            self.list_layout.addWidget(item)
            self._items.append(item)
        self._select(0)
        self.panel.adjustSize()
        self._place_panel()

    def _select(self, index: int) -> None:
        if not self._items:
            self._selected = 0
            return
        self._selected = index % len(self._items)
        for i, item in enumerate(self._items):
            item.set_active(i == self._selected)

    def _run(self, command: Command) -> None:
        self.close_palette()
        command.run()

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:  # noqa: N802
        if obj is self.input and event.type() == QEvent.Type.KeyPress:
            key = event.key()
            if key == Qt.Key.Key_Down:
                self._select(self._selected + 1)
                return True
            if key == Qt.Key.Key_Up:
                self._select(self._selected - 1)
                return True
            if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                if self._items:
                    self._run(self._items[self._selected].command)
                return True
            if key == Qt.Key.Key_Escape:
                self.close_palette()
                return True
        return super().eventFilter(obj, event)

    def _place_panel(self) -> None:
        self.panel.move((self.width() - self.panel.width()) // 2, 86)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._place_panel()

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.fillRect(self.rect(), QColor(4, 4, 5, 140))

    def mousePressEvent(self, event) -> None:
        if not self.panel.geometry().contains(event.position().toPoint()):
            self.close_palette()

