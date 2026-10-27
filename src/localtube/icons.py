"""Ícones do mockup (traços SVG de 24x24) renderizados na cor pedida."""

from functools import lru_cache

from PySide6.QtCore import QByteArray, QRectF, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer

SHAPES = {
    "search": '<circle cx="11" cy="11" r="7"/><path d="M21 21l-4.3-4.3"/>',
    "logo": '<path d="M12 4v11M7 10l5 5 5-5M6 20h12"/>',
    "download": '<path d="M12 3v12M7 10l5 5 5-5M5 20h14"/>',
    "convert": '<path d="M17 3l4 4-4 4M3 11V10a3 3 0 0 1 3-3h15M7 21l-4-4 4-4M21 13v1a3 3 0 0 1-3 3H3"/>',
    "list": '<path d="M9 6h12M9 12h12M9 18h12M4 6h.01M4 12h.01M4 18h.01"/>',
    "folder": '<path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>',
    "sliders": '<path d="M4 20v-6M4 10V4M12 20v-8M12 8V4M20 20v-4M20 12V4M2 14h4M10 8h4M18 16h4"/>',
    "link": '<path d="M10 13a5 5 0 0 0 7.5.5l3-3a5 5 0 0 0-7-7l-1.7 1.7M14 11a5 5 0 0 0-7.5-.5l-3 3a5 5 0 0 0 7 7l1.7-1.7"/>',
    "close": '<path d="M6 6l12 12M18 6L6 18"/>',
    "clipboard": '<rect x="8" y="2" width="8" height="4" rx="1"/>'
    '<path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"/>',
    "clock": '<path d="M12 8v4l3 2"/><circle cx="12" cy="12" r="9"/>',
    "check": '<path d="M20 6L9 17l-5-5"/>',
    "copy": '<rect x="9" y="9" width="12" height="12" rx="2"/>'
    '<path d="M5 15H4a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1h10a1 1 0 0 1 1 1v1"/>',
    "external": '<path d="M14 4h6v6M20 4l-9 9M18 14v5a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1h5"/>',
    "terminal": '<path d="M4 17l6-5-6-5M12 19h8"/>',
    "video": '<rect x="3" y="5" width="18" height="14" rx="2"/><path d="M10 9.5v5l4-2.5z"/>',
    "audio": '<path d="M9 18V5l12-2v13"/><circle cx="6" cy="18" r="3"/><circle cx="18" cy="16" r="3"/>',
    "pause": '<path d="M9 5v14M15 5v14"/>',
    "play": '<path d="M7 5l12 7-12 7z"/>',
    "refresh": '<path d="M21 12a9 9 0 1 1-3-6.7L21 8M21 3v5h-5"/>',
    "upload": '<path d="M12 16V4M7 9l5-5 5 5M5 20h14"/>',
    "arrow-right": '<path d="M5 12h14M13 6l6 6-6 6"/>',
    "chevron-down": '<path d="M6 9l6 6 6-6"/>',
    "library": '<path d="M4 4h6v16H4zM14 4l6 2-4 14-4-1"/>',
    "alert": '<circle cx="12" cy="12" r="9"/><path d="M12 8v5M12 16h.01"/>',
}


def _svg(name: str, color: str, stroke: float) -> bytes:
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="{color}" '
        f'stroke-width="{stroke}" stroke-linecap="round" stroke-linejoin="round">{SHAPES[name]}</svg>'
    ).encode()


@lru_cache(maxsize=512)
def pixmap(name: str, color: str, size: int = 16, stroke: float = 1.6, dpr: float = 2.0) -> QPixmap:
    renderer = QSvgRenderer(QByteArray(_svg(name, color, stroke)))
    pm = QPixmap(round(size * dpr), round(size * dpr))
    pm.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pm)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    renderer.render(painter, QRectF(0, 0, pm.width(), pm.height()))
    painter.end()
    pm.setDevicePixelRatio(dpr)
    return pm


def icon(name: str, color: str, size: int = 16, stroke: float = 1.6, hover_color: str | None = None) -> QIcon:
    result = QIcon()
    result.addPixmap(pixmap(name, color, size, stroke), QIcon.Mode.Normal)
    result.addPixmap(pixmap(name, hover_color or color, size, stroke), QIcon.Mode.Active)
    result.addPixmap(pixmap(name, "#44444c", size, stroke), QIcon.Mode.Disabled)
    return result


def app_icon() -> QIcon:
    """Quadrado laranja com a seta de download, como o logo da barra lateral."""
    result = QIcon()
    for size in (16, 24, 32, 48, 64, 128, 256):
        pm = QPixmap(size, size)
        pm.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pm)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#f07152"))
        painter.drawRoundedRect(QRectF(0, 0, size, size), size * 0.27, size * 0.27)
        glyph = QSvgRenderer(QByteArray(_svg("logo", "#1a0e0a", 2.4)))
        inset = size * 0.2
        glyph.render(painter, QRectF(inset, inset, size - 2 * inset, size - 2 * inset))
        painter.end()
        result.addPixmap(pm)
    return result
