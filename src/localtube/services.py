"""Serviços compartilhados entre as telas, criados uma vez em app.main()."""

from PySide6.QtCore import QObject, Signal

from localtube.core import tools
from localtube.core.convert import ConvertQueue
from localtube.core.downloads import DownloadQueue
from localtube.core.media import ProbeService
from localtube.settings import AppSettings


class Services(QObject):
    tools_changed = Signal()

    def __init__(self, settings: AppSettings) -> None:
        super().__init__()
        self.settings = settings
        self.ffmpeg = tools.ToolInfo("ffmpeg", None, None)
        self.ytdlp_version = tools.ytdlp_version()
        self.refresh_tools()
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

    def _on_setting(self, key: str) -> None:
        if key == "ffmpeg_path":
            self.refresh_tools()
