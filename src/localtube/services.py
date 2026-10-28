"""Serviços compartilhados entre as telas, criados uma vez em app.main()."""

from PySide6.QtCore import QObject, QUrl, Signal
from PySide6.QtNetwork import QNetworkProxy

from localtube.core import tools
from localtube.core.convert import ConvertQueue
from localtube.core.downloads import DownloadQueue
from localtube.core.media import ProbeService
from localtube.settings import AppSettings


def network_proxy(text: str) -> QNetworkProxy:
    """O proxy de Configurações (no formato do --proxy do yt-dlp) para as requisições do Qt."""
    text = text.strip()
    url = QUrl(text if "://" in text else f"http://{text}")
    if not text or not url.isValid() or not url.host():
        return QNetworkProxy(QNetworkProxy.ProxyType.NoProxy)
    socks = url.scheme().lower().startswith("socks")
    kind = QNetworkProxy.ProxyType.Socks5Proxy if socks else QNetworkProxy.ProxyType.HttpProxy
    return QNetworkProxy(kind, url.host(), url.port(1080 if socks else 8080), url.userName(), url.password())


class Services(QObject):
    tools_changed = Signal()

    def __init__(self, settings: AppSettings) -> None:
        super().__init__()
        self.settings = settings
        self.ffmpeg = tools.ToolInfo("ffmpeg", None, None)
        self.ytdlp_version = tools.ytdlp_version()
        self.refresh_tools()
        self._apply_proxy()
        settings.changed.connect(self._on_setting)
        self.downloads = DownloadQueue(settings, lambda: self.ffmpeg.path, parent=self)
        self.probes = ProbeService(lambda: self.ffprobe, parent=self)
        self.conversions = ConvertQueue(lambda: self.ffmpeg.path, self.probes, parent=self)

    def shutdown(self) -> None:
        self.downloads.shutdown()
        self.conversions.shutdown()
        self.probes.shutdown()

    def refresh_tools(self) -> None:
        self.ffmpeg = tools.ffmpeg_info(self.settings.get("ffmpeg_path"))
        self.tools_changed.emit()

    @property
    def ffprobe(self) -> str | None:
        return tools.ffprobe_path(self.ffmpeg.path)

    def _apply_proxy(self) -> None:
        # O yt-dlp recebe --proxy; a miniatura e a atualização (QNetworkAccessManager) usam este.
        QNetworkProxy.setApplicationProxy(network_proxy(self.settings.get("proxy")))

    def _on_setting(self, key: str) -> None:
        if key == "ffmpeg_path":
            self.refresh_tools()
        elif key == "proxy":
            self._apply_proxy()
