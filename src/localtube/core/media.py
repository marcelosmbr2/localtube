"""Metadados de arquivos de mídia via ffprobe, com cache e execução em segundo plano."""

import json
import subprocess
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QObject, Signal

from localtube.core.formatting import fmt_duration, fmt_size
from localtube.core.tools import NO_WINDOW

VIDEO_EXTS = {"mp4", "mkv", "webm", "mov", "avi", "m4v", "wmv", "flv", "gif"}
AUDIO_EXTS = {"mp3", "m4a", "wav", "flac", "ogg", "opus", "aac", "wma"}
MEDIA_EXTS = VIDEO_EXTS | AUDIO_EXTS


@dataclass
class MediaInfo:
    kind: str  # "video" | "audio"
    duration: float | None = None
    width: int | None = None
    height: int | None = None
    sample_rate: int | None = None
    bit_rate: int | None = None


def kind_from_ext(path: str) -> str:
    return "audio" if Path(path).suffix.lower().lstrip(".") in AUDIO_EXTS else "video"


def probe(ffprobe: str, path: str) -> MediaInfo | None:
    try:
        out = subprocess.run(
            [ffprobe, "-v", "error", "-print_format", "json", "-show_format", "-show_streams", path],
            capture_output=True, timeout=30, creationflags=NO_WINDOW,
        ).stdout
        data = json.loads(out.decode("utf-8", errors="replace") or "{}")
    except (OSError, subprocess.SubprocessError, ValueError):
        return None
    return parse_probe(data)


def parse_probe(data: dict) -> MediaInfo | None:
    streams = data.get("streams") or []
    if not streams:
        return None
    fmt = data.get("format") or {}
    video = next((s for s in streams if s.get("codec_type") == "video"
                  and not (s.get("disposition") or {}).get("attached_pic")), None)
    audio = next((s for s in streams if s.get("codec_type") == "audio"), None)
    duration = fmt.get("duration") or (video or audio or {}).get("duration")
    bit_rate = (audio or {}).get("bit_rate") if not video else None
    return MediaInfo(
        kind="video" if video else "audio",
        duration=float(duration) if duration else None,
        width=int(video["width"]) if video and video.get("width") else None,
        height=int(video["height"]) if video and video.get("height") else None,
        sample_rate=int(audio["sample_rate"]) if audio and audio.get("sample_rate") else None,
        bit_rate=int(bit_rate or fmt.get("bit_rate") or 0) or None,
    )


def describe(path: str, info: MediaInfo | None, size: int | None = None) -> str:
    """MOV · 2560×1440 · 4:12 · 1,2 GB  |  M4A · 44,1 kHz · 6:31 · 6,2 MB"""
    parts = [Path(path).suffix.lstrip(".").upper()]
    if info:
        if info.kind == "video" and info.width:
            parts.append(f"{info.width}×{info.height}")
        elif info.sample_rate:
            parts.append((f"{info.sample_rate / 1000:g}".replace(".", ",")) + " kHz")
        if info.duration:
            parts.append(fmt_duration(info.duration))
    if size:
        parts.append(fmt_size(size))
    return " · ".join(parts)


def quality_label(info: MediaInfo | None) -> str:
    if not info:
        return "—"
    if info.kind == "video" and info.width:
        return f"{info.width}×{info.height}"
    if info.bit_rate:
        return f"{round(info.bit_rate / 1000)} kbps"
    if info.sample_rate:
        return (f"{info.sample_rate / 1000:g}".replace(".", ",")) + " kHz"
    return "—"


class ProbeService(QObject):
    """Roda o ffprobe em threads e avisa no thread da interface."""

    probed = Signal(str, object)  # caminho, MediaInfo | None

    def __init__(self, ffprobe, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._ffprobe = ffprobe  # callable que devolve o caminho atual do ffprobe
        self._pool = ThreadPoolExecutor(max_workers=4, thread_name_prefix="ffprobe")
        self._cache: dict[tuple[str, float, int], MediaInfo | None] = {}
        self._pending: set[str] = set()

    def get(self, path: str) -> MediaInfo | None:
        key = self._key(path)
        return self._cache.get(key) if key else None

    def request(self, path: str) -> None:
        key = self._key(path)
        if not key or key in self._cache or path in self._pending:
            return
        ffprobe = self._ffprobe()
        if not ffprobe:
            return
        self._pending.add(path)
        self._pool.submit(self._work, ffprobe, path, key)

    def _work(self, ffprobe: str, path: str, key) -> None:
        info = probe(ffprobe, path)
        self._cache[key] = info
        self._pending.discard(path)
        self.probed.emit(path, info)

    @staticmethod
    def _key(path: str):
        try:
            st = Path(path).stat()
        except OSError:
            return None
        return (path, st.st_mtime, st.st_size)

    def shutdown(self) -> None:
        self._pool.shutdown(wait=False, cancel_futures=True)
