"""Widgets pequenos reutilizados pelas telas: rótulos, botões, cartões, toggles."""

from collections.abc import Callable, Sequence

from PySide6.QtCore import QPoint, QRect, QRectF, QSize, Qt, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPaintEvent
from PySide6.QtWidgets import (
    QAbstractButton,
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLayout,
    QLayoutItem,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from localtube import icons, theme


def repolish(widget: QWidget) -> None:
    widget.style().unpolish(widget)
    widget.style().polish(widget)
    widget.update()


def set_prop(widget: QWidget, name: str, value) -> None:
    if widget.property(name) != value:
        widget.setProperty(name, value)
        repolish(widget)


def label(
    text: str = "",
    px: float = 13,
    color: str = theme.TEXT,
    weight: QFont.Weight = QFont.Weight.Normal,
    mono: bool = False,
    shrink: bool = False,
) -> QLabel:
    lbl = QLabel(text)
    lbl.setFont(theme.mono_font(px, weight) if mono else theme.ui_font(px, weight))
    set_color(lbl, color)
    if shrink:
        lbl.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        lbl.setMinimumWidth(0)
    return lbl


def set_color(lbl: QLabel, color: str) -> None:
    lbl.setStyleSheet(f"color: {color}; background: transparent;")


def section_label(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setFont(theme.section_font())
    set_color(lbl, theme.TEXT_7)
    return lbl


def icon_label(name: str, color: str, size: int = 16, stroke: float = 1.6) -> QLabel:
    lbl = QLabel()
    lbl.setFixedSize(size, size)
    lbl.setPixmap(icons.pixmap(name, color, size, stroke))
    lbl.setStyleSheet("background: transparent;")
    return lbl


def dot(color: str, size: int = 6) -> QLabel:
    lbl = QLabel()
    lbl.setFixedSize(size, size)
    lbl.setStyleSheet(f"background: {color}; border-radius: {size // 2}px;")
    return lbl


def hbox(*items, spacing: int = 8, margins=(0, 0, 0, 0)) -> QHBoxLayout:
    layout = QHBoxLayout()
    layout.setSpacing(spacing)
    layout.setContentsMargins(*margins)
    for item in items:
        _add(layout, item)
    return layout


def vbox(*items, spacing: int = 8, margins=(0, 0, 0, 0)) -> QVBoxLayout:
    layout = QVBoxLayout()
    layout.setSpacing(spacing)
    layout.setContentsMargins(*margins)
    for item in items:
        _add(layout, item)
    return layout


def _add(layout, item) -> None:
    if item is None:
        layout.addStretch(1)
    elif isinstance(item, QLayout):
        layout.addLayout(item)
    elif isinstance(item, int):
        layout.addSpacing(item)
    else:
        layout.addWidget(item)


def frame(layout: QLayout | None = None, name: str = "", **props) -> QFrame:
    f = QFrame()
    if name:
        f.setObjectName(name)
    for key, value in props.items():
        f.setProperty(key, value)
    if layout is not None:
        f.setLayout(layout)
    return f


def button(
    text: str,
    variant: str | None = None,
    size: str | None = None,
    icon_name: str | None = None,
    on_click: Callable | None = None,
) -> QPushButton:
    btn = QPushButton(text)
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    if variant:
        btn.setProperty("variant", variant)
    if size:
        btn.setProperty("size", size)
    if icon_name:
        color = theme.ON_ACCENT if variant == "primary" else theme.TEXT
        btn.setIcon(icons.icon(icon_name, color, 14, 1.7))
        btn.setIconSize(QSize(14, 14))
    if on_click:
        btn.clicked.connect(on_click)
    return btn


def icon_button(
    name: str,
    tooltip: str,
    on_click: Callable | None = None,
    size: int = 14,
    outline: bool = False,
    stroke: float = 1.7,
) -> QToolButton:
    btn = QToolButton()
    btn.setProperty("variant", "iconOutline" if outline else "icon")
    btn.setIcon(icons.icon(name, theme.TEXT_5, size, stroke, hover_color=theme.TEXT))
    btn.setIconSize(QSize(size, size))
    btn.setFixedSize(28, 28)
    btn.setAutoRaise(True)
    btn.setToolTip(tooltip)
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    if on_click:
        btn.clicked.connect(on_click)
    return btn


def kbd(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setObjectName("Kbd")
    lbl.setFixedHeight(17)
    return lbl


def scroll_area(content: QWidget) -> QScrollArea:
    area = QScrollArea()
    area.setWidgetResizable(True)
    area.setFrameShape(QFrame.Shape.NoFrame)
    area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    area.setWidget(content)
    return area


def page_header(title: str, subtitle: str, margins=(24, 20, 24, 18)) -> tuple[QFrame, QLabel, QVBoxLayout]:
    """Cabeçalho de página: título, subtítulo e o layout externo para acrescentar controles."""
    title_lbl = QLabel(title)
    title_lbl.setObjectName("PageTitle")
    sub = QLabel(subtitle)
    sub.setObjectName("PageSubtitle")
    outer = vbox(vbox(title_lbl, sub, spacing=3), spacing=14, margins=margins)
    return frame(outer, "PageHeader"), sub, outer


class ClickableFrame(QFrame):
    clicked = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton and self.rect().contains(event.position().toPoint()):
            self.clicked.emit()
        super().mouseReleaseEvent(event)


class ElidedLabel(QLabel):
    """QLabel de uma linha que corta o texto com reticências em vez de crescer."""

    def __init__(self, text: str = "", px: float = 13, color: str = theme.TEXT,
                 weight: QFont.Weight = QFont.Weight.Normal, mono: bool = False) -> None:
        super().__init__()
        self._full = text
        self.setFont(theme.mono_font(px, weight) if mono else theme.ui_font(px, weight))
        set_color(self, color)
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self.setMinimumWidth(0)
        self._refresh()

    def set_full_text(self, text: str) -> None:
        if text != self._full:
            self._full = text
            self._refresh()

    def full_text(self) -> str:
        return self._full

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._refresh()

    def _refresh(self) -> None:
        width = self.width() if self.width() > 10 else 10_000
        elided = self.fontMetrics().elidedText(self._full, Qt.TextElideMode.ElideRight, width)
        super().setText(elided)
        self.setToolTip(self._full if elided != self._full else "")


class Toggle(QAbstractButton):
    """Interruptor 28x16 do mockup."""

    def __init__(self, checked: bool = False, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setCheckable(True)
        self.setChecked(checked)
        self.setFixedSize(28, 16)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def sizeHint(self) -> QSize:
        return QSize(28, 16)

    def paintEvent(self, event: QPaintEvent) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(Qt.PenStyle.NoPen)
        on = self.isChecked()
        enabled = self.isEnabled()
        p.setOpacity(1.0 if enabled else 0.4)
        p.setBrush(QColor(theme.ACCENT if on else theme.TOGGLE_OFF))
        p.drawRoundedRect(QRectF(0, 0, 28, 16), 8, 8)
        p.setBrush(QColor(theme.ON_ACCENT if on else theme.TEXT_5))
        p.drawEllipse(QRectF(14 if on else 2, 2, 12, 12))


class ToggleRow(ClickableFrame):
    """Linha clicável com texto à esquerda e Toggle à direita."""

    toggled = Signal(bool)

    def __init__(self, text: str, checked: bool, height: int = 32) -> None:
        super().__init__()
        self.setFixedHeight(height)
        self.text_label = label(text, color=theme.TEXT_3)
        self.toggle = Toggle(checked)
        self.setLayout(hbox(self.text_label, None, self.toggle))
        self.toggle.toggled.connect(self.toggled)
        self.clicked.connect(self.toggle.click)

    def is_checked(self) -> bool:
        return self.toggle.isChecked()

    def set_checked(self, value: bool) -> None:
        self.toggle.blockSignals(True)
        self.toggle.setChecked(value)
        self.toggle.blockSignals(False)
        self.toggle.update()

    def setEnabled(self, enabled: bool) -> None:  # noqa: N802 (API do Qt)
        super().setEnabled(enabled)
        set_color(self.text_label, theme.TEXT_3 if enabled else theme.TEXT_8)


class ThinProgress(QWidget):
    """Barra de progresso de 4 px."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._value = 0.0
        self._color = theme.ACCENT
        self.setFixedHeight(4)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def set_value(self, value: float, color: str | None = None) -> None:
        self._value = max(0.0, min(100.0, value))
        if color:
            self._color = color
        self.update()

    def paintEvent(self, event: QPaintEvent) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(theme.BG_TRACK))
        p.drawRoundedRect(QRectF(self.rect()), 2, 2)
        if self._value > 0:
            p.setBrush(QColor(self._color))
            p.drawRoundedRect(QRectF(0, 0, self.width() * self._value / 100, self.height()), 2, 2)


class SegButton(QPushButton):
    """Botão de controle segmentado, com contador opcional em cor apagada."""

    def __init__(self, text: str, count: str | None = None) -> None:
        super().__init__()
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._text = QLabel(text)
        self._count = QLabel(count or "")
        for lbl in (self._text, self._count):
            lbl.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self._text.setFont(theme.ui_font(12, QFont.Weight.Medium))
        self._count.setFont(theme.ui_font(11))
        set_color(self._count, theme.TEXT_7)
        self._count.setVisible(count is not None)
        layout = hbox(None, self._text, self._count, None, spacing=6, margins=(10, 0, 10, 0))
        self.setLayout(layout)
        self.toggled.connect(self._sync)
        self._sync()

    def set_count(self, count: str) -> None:
        self._count.setText(count)
        self._count.setVisible(True)

    def sizeHint(self) -> QSize:
        return QSize(self.layout().sizeHint().width(), 24)

    def minimumSizeHint(self) -> QSize:
        return self.sizeHint()

    def _sync(self) -> None:
        if not self.isEnabled():
            color = theme.TEXT_8
        else:
            color = theme.TEXT if self.isChecked() else theme.TEXT_5
        set_color(self._text, color)

    def changeEvent(self, event) -> None:
        super().changeEvent(event)
        self._sync()


class SegmentedControl(QFrame):
    changed = Signal(str)

    def __init__(
        self,
        options: Sequence[tuple[str, str]],
        value: str | None = None,
        expand: bool = False,
        size: str | None = None,
        tone: str | None = None,
        button_width: int | None = None,
        counts: bool = False,
    ) -> None:
        super().__init__()
        self.setObjectName("Segmented")
        if size:
            self.setProperty("size", size)
        if tone:
            self.setProperty("tone", tone)
        self._group = QButtonGroup(self)
        self._group.setExclusive(True)
        self._buttons: dict[str, SegButton] = {}
        self._expand = expand
        self._button_width = button_width
        self._counts = counts
        layout = hbox(spacing=2, margins=(2, 2, 2, 2))
        self.setLayout(layout)
        self.set_options(options, value)
        self._group.buttonClicked.connect(self._on_click)

    def set_options(self, options: Sequence[tuple[str, str]], value: str | None = None) -> None:
        for btn in self._buttons.values():
            self._group.removeButton(btn)
            btn.deleteLater()
        self._buttons.clear()
        layout = self.layout()
        for key, text in options:
            btn = SegButton(text, "0" if self._counts else None)
            btn.setProperty("value", key)
            if self._button_width:
                btn.setFixedWidth(self._button_width)
            if self._expand:
                btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            self._group.addButton(btn)
            layout.addWidget(btn, 1 if self._expand else 0)
            self._buttons[key] = btn
        if options:
            self.set_value(value if value in self._buttons else options[0][0])

    def value(self) -> str:
        btn = self._group.checkedButton()
        return btn.property("value") if btn else ""

    def set_value(self, value: str) -> None:
        if value in self._buttons:
            self._buttons[value].setChecked(True)

    def set_count(self, key: str, count: int) -> None:
        self._buttons[key].set_count(str(count))

    def set_enabled_option(self, key: str, enabled: bool, tooltip: str = "") -> None:
        self._buttons[key].setEnabled(enabled)
        self._buttons[key].setToolTip(tooltip)

    def _on_click(self, btn) -> None:
        self.changed.emit(btn.property("value"))


class Card(QFrame):
    """Cartão com borda arredondada e linhas separadas por divisórias."""

    def __init__(self, radius: int = 10, plain: bool = False) -> None:
        super().__init__()
        self.setObjectName("Card")
        if radius != 10:
            self.setProperty("radius", str(radius))
        if plain:
            self.setProperty("plain", True)
        self._rows: list[QWidget] = []
        self._layout = vbox(spacing=0, margins=(1, 1, 1, 1))
        self.setLayout(self._layout)

    def add_row(self, row: QWidget, index: int | None = None) -> None:
        row.setObjectName(row.objectName() or "CardRow")
        if index is None:
            self._rows.append(row)
            self._layout.addWidget(row)
        else:
            self._rows.insert(index, row)
            self._layout.insertWidget(index, row)
        self._refresh_dividers()

    def remove_row(self, row: QWidget) -> None:
        if row in self._rows:
            self._rows.remove(row)
            self._layout.removeWidget(row)
            row.deleteLater()
            self._refresh_dividers()

    def clear_rows(self) -> None:
        for row in list(self._rows):
            self.remove_row(row)

    def rows(self) -> list[QWidget]:
        return list(self._rows)

    def set_row_order(self, rows: list[QWidget]) -> None:
        for row in rows:
            self._layout.removeWidget(row)
        for row in rows:
            self._layout.addWidget(row)
        self._rows = rows + [r for r in self._rows if r not in rows]
        self._refresh_dividers()

    def _refresh_dividers(self) -> None:
        visible = [r for r in self._rows if not r.isHidden()]
        for row in self._rows:
            set_prop(row, "divider", bool(visible) and row is not visible[0])
            set_prop(row, "first", bool(visible) and row is visible[0])
            set_prop(row, "last", bool(visible) and row is visible[-1])

    def refresh(self) -> None:
        self._refresh_dividers()


def card_row(layout: QLayout, clickable: bool = False) -> QFrame:
    row = ClickableFrame() if clickable else QFrame()
    row.setObjectName("CardRow")
    if clickable:
        row.setProperty("clickable", True)
    else:
        row.setCursor(Qt.CursorShape.ArrowCursor)
    row.setLayout(layout)
    return row


def chip(text: str, tone: str | None = None, icon_name: str | None = None) -> QLabel | QFrame:
    lbl = QLabel(text)
    lbl.setFont(theme.ui_font(11))
    if icon_name:
        color = theme.GREEN_TEXT if tone == "green" else theme.TEXT_4
        box = frame(hbox(icon_label(icon_name, color, 11, 2.2), lbl, spacing=5, margins=(8, 0, 8, 0)), "Chip")
        set_color(lbl, color)
        if tone:
            box.setProperty("tone", tone)
        box.setFixedHeight(22)
        return box
    lbl.setObjectName("Chip")
    if tone:
        lbl.setProperty("tone", tone)
    lbl.setFixedHeight(22)
    return lbl


def badge(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setObjectName("Badge")
    lbl.setFont(theme.ui_font(10.5, QFont.Weight.Medium))
    lbl.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
    return lbl


def status_pill(text: str, fg: str, bg: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setFont(theme.ui_font(11, QFont.Weight.Medium))
    lbl.setFixedHeight(22)
    lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
    style_pill(lbl, fg, bg)
    return lbl


def style_pill(lbl: QLabel, fg: str, bg: str) -> None:
    lbl.setStyleSheet(f"color: {fg}; background: {bg}; border-radius: 5px; padding: 0 8px;")


def icon_box(name: str, size: int = 32, icon_size: int = 15) -> QFrame:
    box = QFrame()
    box.setObjectName("IconBox")
    box.setFixedSize(size, size)
    lbl = icon_label(name, theme.TEXT_4, icon_size)
    box.setLayout(hbox(lbl, margins=(0, 0, 0, 0)))
    box.layout().setAlignment(Qt.AlignmentFlag.AlignCenter)
    box.icon_label = lbl
    return box


def skeleton(width: int | None, height: int, color: str = theme.BG_SKELETON, radius: int = 4) -> QFrame:
    f = QFrame()
    f.setStyleSheet(f"background: {color}; border-radius: {radius}px;")
    f.setFixedHeight(height)
    if width:
        f.setFixedWidth(width)
    return f


class FlowLayout(QLayout):
    """Layout que quebra linha quando falta espaço (exemplo clássico do Qt)."""

    def __init__(self, spacing: int = 6) -> None:
        super().__init__()
        self._items: list[QLayoutItem] = []
        self._spacing = spacing
        self.setContentsMargins(0, 0, 0, 0)

    def addItem(self, item: QLayoutItem) -> None:  # noqa: N802
        self._items.append(item)

    def count(self) -> int:
        return len(self._items)

    def itemAt(self, index: int) -> QLayoutItem | None:  # noqa: N802
        return self._items[index] if 0 <= index < len(self._items) else None

    def takeAt(self, index: int) -> QLayoutItem | None:  # noqa: N802
        return self._items.pop(index) if 0 <= index < len(self._items) else None

    def expandingDirections(self) -> Qt.Orientation:  # noqa: N802
        return Qt.Orientation(0)

    def hasHeightForWidth(self) -> bool:  # noqa: N802
        return True

    def heightForWidth(self, width: int) -> int:  # noqa: N802
        return self._do_layout(QRect(0, 0, width, 0), test=True)

    def setGeometry(self, rect: QRect) -> None:  # noqa: N802
        super().setGeometry(rect)
        self._do_layout(rect, test=False)

    def sizeHint(self) -> QSize:  # noqa: N802
        return self.minimumSize()

    def minimumSize(self) -> QSize:  # noqa: N802
        size = QSize()
        for item in self._items:
            size = size.expandedTo(item.minimumSize())
        return size

    def clear(self) -> None:
        while self._items:
            item = self._items.pop()
            if item.widget():
                item.widget().deleteLater()

    def _do_layout(self, rect: QRect, test: bool) -> int:
        x, y, line_height = rect.x(), rect.y(), 0
        for item in self._items:
            hint = item.sizeHint()
            if x + hint.width() > rect.right() + 1 and line_height > 0:
                x = rect.x()
                y += line_height + self._spacing
                line_height = 0
            if not test:
                item.setGeometry(QRect(QPoint(x, y), hint))
            x += hint.width() + self._spacing
            line_height = max(line_height, hint.height())
        return y + line_height - rect.y()
