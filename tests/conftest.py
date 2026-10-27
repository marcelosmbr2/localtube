import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QObject, QSettings, Signal  # noqa: E402

from localtube.settings import AppSettings  # noqa: E402


@pytest.fixture
def settings(tmp_path, qapp) -> AppSettings:
    store = QSettings(str(tmp_path / "settings.ini"), QSettings.Format.IniFormat)
    app_settings = AppSettings(store)
    app_settings.set("download_dir", str(tmp_path / "downloads"))
    return app_settings


class FakeRunner(QObject):
    """Substitui o ProcessRunner: guarda os argumentos e deixa o teste emitir a saída."""

    line = Signal(str)
    error_line = Signal(str)
    finished = Signal(int)
    instances: list["FakeRunner"] = []

    def __init__(self) -> None:
        super().__init__()
        self.program = ""
        self.args: list[str] = []
        self.killed = False
        FakeRunner.instances.append(self)

    def start(self, program: str, args: list[str]) -> None:
        self.program, self.args = program, args

    def kill(self) -> None:
        self.killed = True
        self.finished.emit(-1)


@pytest.fixture
def fake_runner():
    FakeRunner.instances = []
    return FakeRunner


def _video(fid, height, vcodec, ext, fps, size, protocol="https"):
    return {"format_id": fid, "ext": ext, "vcodec": vcodec, "acodec": "none", "height": height, "fps": fps,
            "filesize": size, "protocol": protocol, "tbr": size / 100_000}


def _audio(fid, acodec, ext, abr, asr, size):
    return {"format_id": fid, "ext": ext, "vcodec": "none", "acodec": acodec, "abr": abr, "asr": asr,
            "filesize": size, "protocol": "https", "tbr": abr}


@pytest.fixture
def info() -> dict:
    """Recorte do info dict do yt-dlp para um vídeo do YouTube."""
    return {
        "title": "Big Buck Bunny",
        "webpage_url": "https://www.youtube.com/watch?v=aqz-KE-bpKQ",
        "duration": 635,
        "formats": [
            {"format_id": "sb0", "ext": "mhtml", "vcodec": "none", "acodec": "none", "format_note": "storyboard"},
            _audio("139", "mp4a.40.5", "m4a", 48.8, 22050, 3_871_021),
            _audio("140", "mp4a.40.2", "m4a", 129.481, 44100, 10_271_496),
            _audio("140-drc", "mp4a.40.2", "m4a", 129.481, 44100, 10_271_496),
            _audio("251", "opus", "webm", 128.612, 48000, 10_202_210),
            _video("134", 360, "avc1.4D401E", "mp4", 30, 18_294_110),
            _video("135", 480, "avc1.4D401F", "mp4", 30, 28_207_144),
            _video("244", 480, "vp9", "webm", 30, 33_138_062),
            _video("397", 480, "av01.0.04M.08", "mp4", 30, 25_998_574),
            _video("231", 480, "avc1.4D401F", "mp4", 30, 0, protocol="m3u8_native"),
            _video("299", 1080, "avc1.64002A", "mp4", 60, 257_619_653),
            _video("303", 1080, "vp9", "webm", 60, 168_736_189),
            _video("315", 2160, "vp9", "webm", 60, 1_362_269_481),
        ],
    }
