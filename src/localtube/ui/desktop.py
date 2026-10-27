"""Integração com o Explorer e o navegador."""

import os
import subprocess
from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices


def open_folder(path: str) -> None:
    folder = Path(path)
    folder.mkdir(parents=True, exist_ok=True)
    QDesktopServices.openUrl(QUrl.fromLocalFile(str(folder)))


def reveal(path: str) -> None:
    """Abre o Explorer com o arquivo selecionado (ou a pasta, se o arquivo sumiu)."""
    target = Path(path)
    if os.name == "nt" and target.exists():
        subprocess.Popen(["explorer", "/select,", str(target)])
    else:
        open_folder(str(target.parent if target.suffix else target))


def open_file(path: str) -> None:
    QDesktopServices.openUrl(QUrl.fromLocalFile(path))


def open_url(url: str) -> None:
    QDesktopServices.openUrl(QUrl(url))
