"""Biblioteca: arquivos de mídia da pasta de downloads, como modelo de tabela."""

import stat
import time
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QAbstractTableModel, QModelIndex, QObject, QSortFilterProxyModel, Qt

from localtube.core.formatting import fmt_day, fmt_duration, fmt_size
from localtube.core.media import MEDIA_EXTS, ProbeService, file_stat, kind_from_ext, quality_label

PARTIAL_SUFFIXES = (".part", ".ytdl", ".temp")
COLUMNS = ["Nome", "Formato", "Qualidade", "Tamanho", "Duração", "Adicionado", ""]
NAME, FORMAT, QUALITY, SIZE, DURATION, ADDED, ACTIONS = range(len(COLUMNS))
SORT_ROLE = Qt.ItemDataRole.UserRole
ITEM_ROLE = Qt.ItemDataRole.UserRole + 1


@dataclass
class LibraryItem:
    path: str
    size: int
    mtime: float

    @property
    def name(self) -> str:
        return Path(self.path).stem

    @property
    def ext(self) -> str:
        return Path(self.path).suffix.lstrip(".").upper()

    @property
    def kind(self) -> str:
        return kind_from_ext(self.path)


def scan(folder: str) -> list[LibraryItem]:
    root = Path(folder)
    if not root.is_dir():
        return []
    items = []
    for path in root.rglob("*"):
        name = path.name.lower()
        if name.endswith(PARTIAL_SUFFIXES) or path.suffix.lower().lstrip(".") not in MEDIA_EXTS:
            continue
        st = file_stat(path)
        if st and stat.S_ISREG(st.st_mode):
            items.append(LibraryItem(str(path), st.st_size, st.st_mtime))
    return items


class LibraryModel(QAbstractTableModel):
    def __init__(self, probes: ProbeService, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._probes = probes
        self.items: list[LibraryItem] = []
        self._rows: dict[str, int] = {}
        probes.probed.connect(self._on_probed)

    def set_items(self, items: list[LibraryItem]) -> None:
        self.beginResetModel()
        self.items = items
        self._rows = {item.path: i for i, item in enumerate(items)}
        self.endResetModel()
        for item in items:
            self._probes.request(item.path)

    def total_size(self) -> int:
        return sum(i.size for i in self.items)

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:  # noqa: N802
        return 0 if parent.isValid() else len(self.items)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:  # noqa: N802
        return 0 if parent.isValid() else len(COLUMNS)

    def headerData(self, section: int, orientation, role=Qt.ItemDataRole.DisplayRole):  # noqa: N802
        if orientation != Qt.Orientation.Horizontal:
            return None
        if role == Qt.ItemDataRole.DisplayRole:
            return COLUMNS[section].upper()
        if role == Qt.ItemDataRole.TextAlignmentRole:
            right = section in (SIZE, DURATION)
            return int((Qt.AlignmentFlag.AlignRight if right else Qt.AlignmentFlag.AlignLeft)
                       | Qt.AlignmentFlag.AlignVCenter)
        return None

    def data(self, index: QModelIndex, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
        item = self.items[index.row()]
        col = index.column()
        if role == ITEM_ROLE:
            return item
        info = self._probes.get(item.path)
        if role == Qt.ItemDataRole.DisplayRole:
            return {
                NAME: item.name,
                FORMAT: item.ext,
                QUALITY: quality_label(info),
                SIZE: fmt_size(item.size),
                DURATION: fmt_duration(info.duration) if info and info.duration else "—",
                ADDED: fmt_day(item.mtime, time.time()),
            }.get(col, "")
        if role == SORT_ROLE:
            return {
                NAME: item.name.lower(),
                FORMAT: item.ext,
                QUALITY: (info.height or info.bit_rate or 0) if info else 0,
                SIZE: item.size,
                DURATION: (info.duration or 0) if info else 0,
                ADDED: item.mtime,
            }.get(col, 0)
        if role == Qt.ItemDataRole.ToolTipRole and col == NAME:
            return item.path
        return None

    def _on_probed(self, path: str, _info) -> None:
        row = self._rows.get(path)
        if row is not None and row < len(self.items) and self.items[row].path == path:
            self.dataChanged.emit(self.index(row, 0), self.index(row, len(COLUMNS) - 1))


class LibraryFilter(QSortFilterProxyModel):
    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._query = ""
        self.setSortRole(SORT_ROLE)

    def set_query(self, text: str) -> None:
        self._query = text.strip().lower()
        self.invalidateFilter()

    def filterAcceptsRow(self, row: int, parent: QModelIndex) -> bool:  # noqa: N802
        if not self._query:
            return True
        item: LibraryItem = self.sourceModel().items[row]
        return self._query in item.name.lower() or self._query in item.ext.lower()
