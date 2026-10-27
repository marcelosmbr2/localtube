"""Telas do LocalTube. build_pages() cria uma instância de cada, na ordem da barra lateral."""

from PySide6.QtWidgets import QWidget

from localtube.ui.widgets.common import label, page_header, vbox


def _placeholder(title: str) -> QWidget:
    page = QWidget()
    header, _, _ = page_header(title, "Em construção.")
    page.setLayout(vbox(header, label(""), None, spacing=0))
    return page


def build_pages(services, host) -> dict[str, QWidget]:
    from localtube.ui.pages.settings import SettingsPage

    return {
        "download": _placeholder("Baixar"),
        "convert": _placeholder("Converter"),
        "queue": _placeholder("Fila"),
        "library": _placeholder("Biblioteca"),
        "settings": SettingsPage(services, host),
    }
