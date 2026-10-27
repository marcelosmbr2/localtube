"""Telas do LocalTube. build_pages() cria uma instância de cada, na ordem da barra lateral."""

from PySide6.QtWidgets import QWidget

from localtube.ui.widgets.common import label, page_header, vbox


def _placeholder(title: str) -> QWidget:
    page = QWidget()
    header, _, _ = page_header(title, "Em construção.")
    page.setLayout(vbox(header, label(""), None, spacing=0))
    return page


def build_pages(services, host) -> dict[str, QWidget]:
    from localtube.ui.pages.convert import ConvertPage
    from localtube.ui.pages.download import DownloadPage
    from localtube.ui.pages.queue import QueuePage
    from localtube.ui.pages.settings import SettingsPage

    return {
        "download": DownloadPage(services, host),
        "convert": ConvertPage(services, host),
        "queue": QueuePage(services, host),
        "library": _placeholder("Biblioteca"),
        "settings": SettingsPage(services, host),
    }
