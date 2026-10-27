"""Configurações persistidas em QSettings (INI em %APPDATA%\\LocalTube)."""

import json
import time
from pathlib import Path
from typing import Any

from PySide6.QtCore import QObject, QSettings, QStandardPaths, Signal


def default_download_dir() -> str:
    videos = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.MoviesLocation)
    return str(Path(videos or Path.home() / "Videos") / "LocalTube")


QUALITY_OPTIONS = ["2160p · MP4", "1440p · MP4", "1080p · MP4", "720p · MP4", "480p · MP4"]
BANDWIDTH_OPTIONS = [
    ("Ilimitado", ""),
    ("1 MB/s", "1M"),
    ("2 MB/s", "2M"),
    ("5 MB/s", "5M"),
    ("10 MB/s", "10M"),
    ("20 MB/s", "20M"),
]

DEFAULTS: dict[str, Any] = {
    "download_dir": None,  # resolvido em default_download_dir()
    "clipboard_monitor": True,
    "notifications": True,
    "preferred_quality": "1080p · MP4",
    "concurrency": 3,
    "bandwidth_limit": "",
    "filename_template": "%(title)s.%(ext)s",
    "ffmpeg_path": "",
    "proxy": "",
    "embed_thumbnail": True,
    "embed_metadata": True,
    "write_subs": False,
    "split_chapters": False,
}

MAX_RECENT = 5


class AppSettings(QObject):
    changed = Signal(str)

    def __init__(self, store: QSettings | None = None, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._store = store or QSettings(
            QSettings.Format.IniFormat, QSettings.Scope.UserScope, "LocalTube", "LocalTube"
        )

    def get(self, key: str) -> Any:
        default = DEFAULTS[key]
        if key == "download_dir":
            return str(self._store.value(key, default_download_dir()))
        return self._store.value(key, default, type=type(default))

    def set(self, key: str, value: Any) -> None:
        if self.get(key) == value:
            return
        self._store.setValue(key, value)
        self.changed.emit(key)

    def recent(self) -> list[dict]:
        try:
            return json.loads(self._store.value("recent", "[]", type=str))
        except ValueError:
            return []

    def add_recent(self, title: str, domain: str, url: str) -> None:
        items = [r for r in self.recent() if r.get("u") != url]
        items.insert(0, {"t": title, "d": domain, "u": url, "ts": time.time()})
        self._store.setValue("recent", json.dumps(items[:MAX_RECENT], ensure_ascii=False))
        self.changed.emit("recent")
