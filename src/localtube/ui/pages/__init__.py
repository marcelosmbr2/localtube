"""Telas do LocalTube. build_pages() cria uma instância de cada, na ordem da barra lateral."""

from PySide6.QtWidgets import QWidget


def build_pages(services, host) -> dict[str, QWidget]:
    from localtube.ui.pages.convert import ConvertPage
    from localtube.ui.pages.download import DownloadPage
    from localtube.ui.pages.library import LibraryPage
    from localtube.ui.pages.queue import QueuePage
    from localtube.ui.pages.settings import SettingsPage

    return {
        "download": DownloadPage(services, host),
        "convert": ConvertPage(services, host),
        "queue": QueuePage(services, host),
        "library": LibraryPage(services, host),
        "settings": SettingsPage(services, host),
    }
