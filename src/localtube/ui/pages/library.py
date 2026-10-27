"""Tela Biblioteca: o que já está na pasta de downloads."""

from PySide6.QtCore import QEvent, QFileSystemWatcher, QModelIndex, QRect, QRectF, QSize, Qt, QTimer
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QHeaderView,
    QLineEdit,
    QStackedWidget,
    QStyle,
    QStyledItemDelegate,
    QStyleOptionViewItem,
    QTableView,
    QWidget,
)

from localtube import icons, theme
from localtube.core.formatting import fmt_size
from localtube.core.library import (
    ACTIONS,
    ADDED,
    DURATION,
    FORMAT,
    ITEM_ROLE,
    NAME,
    SIZE,
    LibraryFilter,
    LibraryItem,
    LibraryModel,
    scan,
)
from localtube.services import Services
from localtube.ui import desktop
from localtube.ui.widgets.common import (
    FocusHighlighter,
    frame,
    hbox,
    icon_label,
    label,
    page_header_row,
    paint_stripes,
    vbox,
)

GAP, PAD = 16, 24
WIDTHS = {FORMAT: 72, 2: 110, SIZE: 84, DURATION: 80, ADDED: 110, ACTIONS: 64}
SORTS = [("Adicionados recentemente", ADDED, Qt.SortOrder.DescendingOrder),
         ("Nome (A–Z)", NAME, Qt.SortOrder.AscendingOrder),
         ("Maiores primeiro", SIZE, Qt.SortOrder.DescendingOrder),
         ("Mais longos primeiro", DURATION, Qt.SortOrder.DescendingOrder)]
ACTION_ICONS = [("convert", "Converter"), ("folder", "Mostrar na pasta")]


class LibraryDelegate(QStyledItemDelegate):
    def __init__(self, view: "LibraryView") -> None:
        super().__init__(view)
        self.view = view

    @staticmethod
    def content_rect(rect: QRect, column: int) -> QRect:
        left = PAD if column == NAME else GAP
        right = PAD if column == ACTIONS else 0
        return rect.adjusted(left, 0, -right, 0)

    @staticmethod
    def action_rects(rect: QRect) -> list[QRect]:
        inner = LibraryDelegate.content_rect(rect, ACTIONS)
        y = inner.center().y() - 14
        right = inner.right() + 1
        return [QRect(right - 58, y, 28, 28), QRect(right - 28, y, 28, 28)]

    def paint(self, p: QPainter, option: QStyleOptionViewItem, index: QModelIndex) -> None:
        p.save()
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = option.rect
        if index.row() == self.view.hover_row:
            p.fillRect(rect, QColor("#131316"))
        p.setPen(QPen(QColor("#17171b"), 1))
        p.drawLine(rect.bottomLeft(), rect.bottomRight())
        col = index.column()
        inner = self.content_rect(rect, col)
        item: LibraryItem = index.data(ITEM_ROLE)
        text = index.data() or ""
        if col == NAME:
            thumb = QRectF(inner.left(), inner.center().y() - 13.5, 48, 27)
            path = QPainterPath()
            path.addRoundedRect(thumb, 4, 4)
            p.setClipPath(path)
            paint_stripes(p, thumb, 5)
            p.setClipping(False)
            p.setPen(QPen(QColor(theme.BORDER_SEGMENT), 1))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawPath(path)
            if item.kind == "audio":
                pm = icons.pixmap("audio", theme.TEXT_9, 11, 2)
                p.drawPixmap(int(thumb.center().x() - 5.5), int(thumb.center().y() - 5.5), pm)
            text_rect = inner.adjusted(48 + 12, 0, 0, 0)
            self._text(p, text_rect, text, theme.ui_font(13, QFont.Weight.Medium), theme.TEXT)
        elif col == FORMAT:
            self._text(p, inner, text, theme.mono_font(11), theme.TEXT_4)
        elif col in (SIZE, DURATION):
            color = theme.TEXT_3 if col == SIZE else theme.TEXT_4
            self._text(p, inner, text, theme.ui_font(13), color, Qt.AlignmentFlag.AlignRight)
        elif col == ADDED:
            self._text(p, inner, text, theme.ui_font(13), theme.TEXT_6)
        elif col == ACTIONS:
            if index.row() == self.view.hover_row:
                for i, (rect_i, (name, _)) in enumerate(zip(self.action_rects(rect), ACTION_ICONS, strict=True)):
                    hovered = self.view.hover_action == i
                    if hovered:
                        p.setPen(Qt.PenStyle.NoPen)
                        p.setBrush(QColor("#1e1e23"))
                        p.drawRoundedRect(QRectF(rect_i), 6, 6)
                    pm = icons.pixmap(name, theme.TEXT if hovered else theme.TEXT_5, 14)
                    p.drawPixmap(rect_i.center().x() - 7 + 1, rect_i.center().y() - 7 + 1, pm)
        else:
            self._text(p, inner, text, theme.ui_font(13), theme.TEXT_4)
        p.restore()

    @staticmethod
    def _text(p: QPainter, rect: QRect, text: str, font: QFont, color: str,
              align=Qt.AlignmentFlag.AlignLeft) -> None:
        p.setFont(font)
        p.setPen(QColor(color))
        elided = p.fontMetrics().elidedText(text, Qt.TextElideMode.ElideRight, rect.width())
        p.drawText(rect, int(align | Qt.AlignmentFlag.AlignVCenter), elided)

    def sizeHint(self, option, index) -> QSize:  # noqa: N802
        return QSize(0, 48)


class LibraryView(QTableView):
    def __init__(self, page: "LibraryPage") -> None:
        super().__init__()
        self.page = page
        self.hover_row = -1
        self.hover_action = -1
        self.setMouseTracking(True)
        self.setShowGrid(False)
        self.setWordWrap(False)
        self.setFrameShape(QTableView.Shape.NoFrame)
        self.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.verticalHeader().hide()
        self.verticalHeader().setDefaultSectionSize(48)
        self.setItemDelegate(LibraryDelegate(self))

    def setup_header(self) -> None:
        header = self.horizontalHeader()
        header.setHighlightSections(False)
        header.setSectionsClickable(False)
        header.setFixedHeight(34)
        header.setFont(theme.section_font())
        header.setSectionResizeMode(NAME, QHeaderView.ResizeMode.Stretch)
        for col, width in WIDTHS.items():
            header.setSectionResizeMode(col, QHeaderView.ResizeMode.Fixed)
            header.resizeSection(col, width + GAP + (PAD if col == ACTIONS else 0))

    def mouseMoveEvent(self, event) -> None:
        index = self.indexAt(event.position().toPoint())
        row = index.row() if index.isValid() else -1
        action = -1
        if index.isValid():
            rect = self.visualRect(self.model().index(row, ACTIONS))
            for i, r in enumerate(LibraryDelegate.action_rects(rect)):
                if r.contains(event.position().toPoint()):
                    action = i
        if (row, action) != (self.hover_row, self.hover_action):
            self.hover_row, self.hover_action = row, action
            self.setCursor(Qt.CursorShape.PointingHandCursor if action >= 0 else Qt.CursorShape.ArrowCursor)
            self.setToolTip(ACTION_ICONS[action][1] if action >= 0 else "")
            self.viewport().update()
        super().mouseMoveEvent(event)

    def leaveEvent(self, event: QEvent) -> None:
        self.hover_row = self.hover_action = -1
        self.viewport().update()
        super().leaveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        index = self.indexAt(event.position().toPoint())
        if index.isValid() and event.button() == Qt.MouseButton.LeftButton and self.hover_action >= 0:
            item: LibraryItem = index.data(ITEM_ROLE)
            self.page.run_action(self.hover_action, item)
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event) -> None:
        index = self.indexAt(event.position().toPoint())
        if index.isValid() and self.hover_action < 0:
            desktop.open_file(index.data(ITEM_ROLE).path)


class LibraryPage(QWidget):
    def __init__(self, services: Services, host) -> None:
        super().__init__()
        self.services = services
        self.settings = services.settings
        self.host = host

        self.search = QLineEdit()
        self.search.setProperty("bare", True)
        self.search.setFont(theme.ui_font(12.5))
        self.search.setPlaceholderText("Filtrar arquivos")
        search_box = frame(hbox(icon_label("search", theme.TEXT_7, 13, 1.8), self.search, spacing=8,
                                margins=(10, 0, 10, 0)), "SearchField")
        search_box.setFixedSize(240, 30)
        FocusHighlighter(self.search, search_box)
        self.sort = QComboBox()
        for text, _col, _order in SORTS:
            self.sort.addItem(text)
        self.sort.setStyleSheet(f"QComboBox {{ background: {theme.BG_BUTTON}; border-color: {theme.BORDER_STRONG}; "
                                f"font-size: 12.5px; padding-right: 4px; }}")
        self.sort.setFixedHeight(30)
        self.sort.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToContents)
        header, self.subtitle = page_header_row("Biblioteca", "", search_box, self.sort)

        self.model = LibraryModel(services.probes, self)
        self.proxy = LibraryFilter(self)
        self.proxy.setSourceModel(self.model)
        self.view = LibraryView(self)
        self.view.setModel(self.proxy)
        self.view.setup_header()
        empty = label("Nenhum arquivo encontrado.", 12, theme.TEXT_7)
        empty.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)
        empty.setContentsMargins(0, 48, 0, 0)
        self.body = QStackedWidget()
        self.body.addWidget(self.view)
        self.body.addWidget(empty)
        self.setLayout(vbox(header, self.body, spacing=0))

        self.search.textChanged.connect(self._on_query)
        self.sort.currentIndexChanged.connect(self._apply_sort)
        self._refresh_timer = QTimer(self, singleShot=True, interval=400, timeout=self.refresh)
        self.watcher = QFileSystemWatcher(self)
        self.watcher.directoryChanged.connect(lambda _: self._refresh_timer.start())
        services.downloads.job_finished.connect(lambda _: self._refresh_timer.start())
        services.conversions.batch_finished.connect(lambda *_: self._refresh_timer.start())
        self.settings.changed.connect(self._on_setting)
        services.tools_changed.connect(self.refresh)
        self.refresh()

    def refresh(self) -> None:
        folder = self.settings.get("download_dir")
        if self.watcher.directories():
            self.watcher.removePaths(self.watcher.directories())
        try:
            self.watcher.addPath(folder)
        except RuntimeError:
            pass
        self.model.set_items(scan(folder))
        self._apply_sort()
        self.subtitle.set_full_text(f"{len(self.model.items)} arquivos · {fmt_size(self.model.total_size())} em {folder}")
        self._sync_empty()

    def on_shown(self) -> None:
        self._refresh_timer.start(0)

    def run_action(self, action: int, item: LibraryItem) -> None:
        if action == 0:
            self.services.conversions.add_files([item.path])
            self.host.go("convert")
        else:
            desktop.reveal(item.path)

    def _on_query(self, text: str) -> None:
        self.proxy.set_query(text)
        self._sync_empty()

    def _apply_sort(self) -> None:
        _text, col, order = SORTS[self.sort.currentIndex()]
        self.proxy.sort(col, order)

    def _sync_empty(self) -> None:
        self.body.setCurrentIndex(0 if self.proxy.rowCount() else 1)

    def _on_setting(self, key: str) -> None:
        if key == "download_dir":
            self.refresh()

