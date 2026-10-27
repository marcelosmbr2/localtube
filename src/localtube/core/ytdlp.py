"""Argumentos do yt-dlp, leitura do progresso e inspeção de links (-J)."""

import json
import subprocess
import sys
from dataclasses import dataclass, field
from urllib.parse import urlparse

from PySide6.QtCore import QObject, Signal

from localtube.core.process import ProcessRunner

PROGRESS_PREFIX = "LTPROG "
FILE_PREFIX = "LTFILE "
# Contêineres em que o yt-dlp consegue embutir a miniatura só com o ffmpeg.
THUMBNAIL_CONTAINERS = {"mp4", "mkv", "m4a", "mp3"}
WEBM_CODECS = {"VP9", "VP8", "AV1"}


@dataclass
class DownloadRequest:
    url: str
    title: str
    kind: str  # "video" | "audio"
    selector: str
    container: str
    out_dir: str
    template: str = "%(title)s.%(ext)s"
    fmt_label: str = ""
    source: str = ""
    size: int | None = None
    video_codec: str = ""
    audio_quality: str | None = None
    embed_thumbnail: bool = True
    embed_metadata: bool = True
    subtitles: list[str] = field(default_factory=list)
    split_chapters: bool = False
    section: tuple[int, int] | None = None


def domain(url: str) -> str:
    host = urlparse(url).netloc.lower()
    return host[4:] if host.startswith("www.") else host


def format_args(req: DownloadRequest) -> list[str]:
    """Argumentos que definem o resultado (os mesmos do comando copiado)."""
    args = ["-f", req.selector]
    if req.kind == "video":
        if req.container == "webm" and req.video_codec not in WEBM_CODECS:
            args += ["--recode-video", "webm"]
        else:
            args += ["--merge-output-format", req.container, "--remux-video", req.container]
    else:
        args += ["-x", "--audio-format", req.container]
        if req.audio_quality:
            args += ["--audio-quality", req.audio_quality]
    if req.embed_thumbnail and req.container in THUMBNAIL_CONTAINERS:
        args.append("--embed-thumbnail")
    if req.embed_metadata:
        args.append("--embed-metadata")
    if req.subtitles:
        args += ["--write-subs", "--sub-langs", ",".join(req.subtitles)]
    if req.split_chapters:
        args.append("--split-chapters")
    if req.section:
        start, end = req.section
        args += ["--download-sections", f"*{start}-{end}"]
    return args


def build_args(
    req: DownloadRequest, ffmpeg: str | None = None, proxy: str = "", rate_limit: str = ""
) -> list[str]:
    """Argumentos completos para rodar com `python -m yt_dlp`."""
    args = [
        "--no-playlist", "--newline", "--progress", "--quiet", "--no-simulate", "--continue",
        "--progress-template", f"download:{PROGRESS_PREFIX}%(progress)j",
        "--print", f"after_move:{FILE_PREFIX}%(filepath)s",
        "-P", req.out_dir, "-o", req.template,
    ]
    args += format_args(req)
    if ffmpeg:
        args += ["--ffmpeg-location", ffmpeg]
    if proxy:
        args += ["--proxy", proxy]
    if rate_limit:
        args += ["--limit-rate", rate_limit]
    return args + ["--", req.url]


def command_string(req: DownloadRequest, proxy: str = "") -> str:
    """Comando equivalente para colar num terminal."""
    args = ["yt-dlp", *format_args(req)]
    if proxy:
        args += ["--proxy", proxy]
    args += ["-P", req.out_dir, "-o", req.template, req.url]
    return subprocess.list2cmdline(args)


def parse_line(line: str) -> tuple[str, object] | None:
    if line.startswith(PROGRESS_PREFIX):
        try:
            return "progress", json.loads(line[len(PROGRESS_PREFIX):])
        except ValueError:
            return None
    if line.startswith(FILE_PREFIX):
        return "file", line[len(FILE_PREFIX):].strip()
    return None


def error_message(line: str) -> str | None:
    if line.startswith("ERROR:"):
        message = line[len("ERROR:"):].strip()
        # "[youtube] abc123: Video unavailable" -> "Video unavailable"
        if message.startswith("[") and ": " in message:
            message = message.split(": ", 1)[1]
        return message
    return None


def rate_per_job(total: str, jobs: int) -> str:
    """Divide um limite como '5M' entre os downloads simultâneos, em bytes/s."""
    if not total:
        return ""
    units = {"K": 1_000, "M": 1_000_000, "G": 1_000_000_000}
    try:
        value = float(total[:-1]) * units[total[-1].upper()] if total[-1].isalpha() else float(total)
    except (ValueError, KeyError):
        return ""
    return str(int(value / max(1, jobs)))


class Inspector(QObject):
    """Roda `yt-dlp -J` para um link e devolve o info dict."""

    finished = Signal(dict)
    failed = Signal(str)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._runner: ProcessRunner | None = None
        self._out: list[str] = []
        self._error = ""

    def inspect(self, url: str, proxy: str = "") -> None:
        self.cancel()
        self._out, self._error = [], ""
        runner = ProcessRunner(self)
        runner.line.connect(self._out.append)
        runner.error_line.connect(self._on_error_line)
        runner.finished.connect(lambda code, r=runner: self._on_finished(r, code))
        args = ["-m", "yt_dlp", "-J", "--no-playlist", "--no-warnings"]
        if proxy:
            args += ["--proxy", proxy]
        self._runner = runner
        runner.start(sys.executable, args + ["--", url])

    def cancel(self) -> None:
        if self._runner:
            runner, self._runner = self._runner, None
            runner.kill()
            runner.deleteLater()

    def _on_error_line(self, line: str) -> None:
        self._error = error_message(line) or self._error

    def _on_finished(self, runner: ProcessRunner, code: int) -> None:
        if runner is not self._runner:
            return
        self._runner = None
        runner.deleteLater()
        if code == 0:
            try:
                info = json.loads("".join(self._out))
            except ValueError:
                self.failed.emit("O yt-dlp devolveu uma resposta ilegível.")
                return
            if info.get("_type") == "playlist" and info.get("entries"):
                info = next((e for e in info["entries"] if e), info)
            self.finished.emit(info)
        else:
            self.failed.emit(self._error or "O yt-dlp não conseguiu ler este link.")
