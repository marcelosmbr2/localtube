"""Presets de conversão (tabela do mockup), argumentos do ffmpeg e a fila de conversão."""

from collections.abc import Callable
from dataclasses import dataclass
from itertools import count
from pathlib import Path

from PySide6.QtCore import QObject, Signal

from localtube.core.media import MEDIA_EXTS, ProbeService, describe, kind_from_ext
from localtube.core.process import ProcessRunner

VIDEO_TARGETS = ["mp4", "mkv", "webm", "mov", "gif"]
AUDIO_TARGETS = ["mp3", "m4a", "wav", "flac", "ogg"]
CRF_CODECS = {"libx264", "libx265", "libvpx-vp9", "libsvtav1"}
CRF_MIN, CRF_MAX, CRF_DEFAULT = 15, 35, 23


@dataclass
class Field:
    key: str
    label: str
    options: list[tuple[str, str]]  # (rótulo, valor)


KEEP = ("Manter original", "")
RESOLUTION = Field("height", "Resolução", [KEEP, ("2160p", "2160"), ("1440p", "1440"), ("1080p", "1080"),
                                           ("720p", "720"), ("480p", "480")])
FPS = Field("fps", "Taxa de quadros", [KEEP, ("60 fps", "60"), ("30 fps", "30"), ("24 fps", "24")])
SAMPLE_RATE = Field("ar", "Taxa de amostragem", [KEEP, ("44,1 kHz", "44100"), ("48 kHz", "48000")])
CHANNELS = Field("ac", "Canais", [KEEP, ("Estéreo", "2"), ("Mono", "1")])
X264 = ("H.264 (libx264)", "libx264")
X265 = ("H.265 (libx265)", "libx265")
VP9 = ("VP9 (libvpx-vp9)", "libvpx-vp9")
NO_AUDIO = ("Sem áudio", "none")

FIELDS: dict[str, list[Field]] = {
    "mp4": [Field("vcodec", "Codec de vídeo", [X264, X265]), RESOLUTION, FPS,
            Field("audio", "Áudio", [("AAC · 192 kbps", "aac:192k"), ("AAC · 128 kbps", "aac:128k"),
                                     ("Copiar fluxo", "copy"), NO_AUDIO])],
    "mkv": [Field("vcodec", "Codec de vídeo", [X264, X265, VP9]), RESOLUTION, FPS,
            Field("audio", "Áudio", [("Copiar fluxo", "copy"), ("AAC · 192 kbps", "aac:192k"),
                                     ("Opus · 128 kbps", "libopus:128k"), NO_AUDIO])],
    "webm": [Field("vcodec", "Codec de vídeo", [VP9, ("AV1 (libsvtav1)", "libsvtav1")]), RESOLUTION, FPS,
             Field("audio", "Áudio", [("Opus · 128 kbps", "libopus:128k"), ("Opus · 96 kbps", "libopus:96k"),
                                      NO_AUDIO])],
    "mov": [Field("vcodec", "Codec de vídeo", [("ProRes 422", "prores"), X264]), RESOLUTION, FPS,
            Field("audio", "Áudio", [("PCM 24-bit", "pcm_s24le"), ("AAC · 192 kbps", "aac:192k"), NO_AUDIO])],
    "gif": [Field("colors", "Paleta", [("Otimizada · 256 cores", "256"), ("Otimizada · 128 cores", "128"),
                                       ("Otimizada · 64 cores", "64")]),
            Field("width", "Largura", [("640 px", "640"), ("480 px", "480"), ("320 px", "320"), KEEP]),
            Field("fps", "Taxa de quadros", [("15 fps", "15"), ("10 fps", "10"), ("24 fps", "24")])],
    "mp3": [Field("codec", "Codec", [("MP3 (LAME)", "libmp3lame")]),
            Field("bitrate", "Taxa de bits", [("192 kbps", "192k"), ("128 kbps", "128k"), ("256 kbps", "256k"),
                                              ("320 kbps", "320k")]), SAMPLE_RATE, CHANNELS],
    "m4a": [Field("codec", "Codec", [("AAC", "aac")]),
            Field("bitrate", "Taxa de bits", [("256 kbps", "256k"), ("192 kbps", "192k"), ("128 kbps", "128k")]),
            SAMPLE_RATE, CHANNELS],
    "wav": [Field("codec", "Formato", [("PCM 16-bit", "pcm_s16le"), ("PCM 24-bit", "pcm_s24le")]),
            Field("ar", "Taxa de amostragem", [("44,1 kHz", "44100"), KEEP, ("48 kHz", "48000")]), CHANNELS],
    "flac": [Field("compression", "Compressão", [("Nível 5", "5"), ("Nível 0 · mais rápido", "0"),
                                                 ("Nível 8 · menor", "8")]), SAMPLE_RATE, CHANNELS],
    "ogg": [Field("codec", "Codec", [("Vorbis", "libvorbis")]),
            Field("quality", "Qualidade", [("q6 · ~192 kbps", "6"), ("q4 · ~128 kbps", "4"),
                                           ("q8 · ~256 kbps", "8")]), CHANNELS],
}


def default_choices(target: str) -> dict[str, str]:
    return {f.key: f.options[0][1] for f in FIELDS[target]}


def uses_crf(target: str, choices: dict[str, str]) -> bool:
    return target in VIDEO_TARGETS and target != "gif" and choices.get("vcodec") in CRF_CODECS


def output_path(src: str, target: str, reserved: set[str] = frozenset()) -> str:
    """Ao lado do original; nunca sobrescreve um arquivo existente nem uma saída já reservada."""
    source = Path(src)

    def taken(p: Path) -> bool:
        return p == source or p.exists() or str(p) in reserved

    candidate = source.with_suffix(f".{target}")
    if taken(candidate):
        stem = f"{source.stem} (convertido)"
        candidate = source.with_name(f"{stem}.{target}")
        n = 2
        while taken(candidate):
            candidate = source.with_name(f"{stem} ({n}).{target}")
            n += 1
    return str(candidate)


def _audio_codec_args(value: str) -> list[str]:
    if value == "none":
        return ["-an"]
    if value == "copy":
        return ["-c:a", "copy"]
    codec, _, bitrate = value.partition(":")
    return ["-c:a", codec] + (["-b:a", bitrate] if bitrate else [])


def build_args(src: str, dst: str, target: str, choices: dict[str, str], crf: int = CRF_DEFAULT) -> list[str]:
    c = {**default_choices(target), **choices}
    args = ["-hide_banner", "-nostdin", "-y", "-i", src]
    if target == "gif":
        scale = f",scale={c['width']}:-1:flags=lanczos" if c["width"] else ""
        graph = (f"[0:V:0]fps={c['fps']}{scale},split[s0][s1];[s0]palettegen=max_colors={c['colors']}[p];"
                 "[s1][p]paletteuse[gif]")
        args += ["-filter_complex", graph, "-map", "[gif]", "-loop", "0", "-an"]
    elif target in VIDEO_TARGETS:
        vcodec = c["vcodec"]
        args += ["-map", "0:V:0", "-map", "0:a:0?", "-c:v", vcodec]
        filters = []
        if c.get("height"):
            filters.append(f"scale=-2:{c['height']}")
        if c.get("fps"):
            filters.append(f"fps={c['fps']}")
        if filters:
            args += ["-vf", ",".join(filters)]
        if vcodec in CRF_CODECS:
            args += ["-crf", str(crf)]
        if vcodec in ("libx264", "libx265"):
            args += ["-preset", "medium", "-pix_fmt", "yuv420p"]
        if vcodec == "libx265" and target in ("mp4", "mov"):
            args += ["-tag:v", "hvc1"]
        if vcodec == "libvpx-vp9":
            args += ["-b:v", "0", "-row-mt", "1"]
        if vcodec == "prores":
            args += ["-profile:v", "2", "-pix_fmt", "yuv422p10le"]
        args += _audio_codec_args(c["audio"])
        if target in ("mp4", "mov"):
            args += ["-movflags", "+faststart"]
    else:
        args += ["-map", "0:a:0", "-vn"]
        if target == "flac":
            args += ["-c:a", "flac", "-compression_level", c["compression"]]
        elif target == "ogg":
            args += ["-c:a", c["codec"], "-q:a", c["quality"]]
        elif target == "wav":
            args += ["-c:a", c["codec"]]
        else:
            args += ["-c:a", c["codec"], "-b:a", c["bitrate"]]
        if c.get("ar"):
            args += ["-ar", c["ar"]]
        if c.get("ac"):
            args += ["-ac", c["ac"]]
    return args + ["-progress", "pipe:1", "-nostats", dst]


def parse_progress(line: str) -> float | None | str:
    """Segundos já codificados, 'end' no fim, ou None para outras linhas."""
    key, _, value = line.partition("=")
    if key in ("out_time_us", "out_time_ms") and value.strip().lstrip("-").isdigit():
        return max(0, int(value)) / 1_000_000
    if key == "progress" and value.strip() == "end":
        return "end"
    return None


READY, QUEUED, CONVERTING, DONE, FAILED = "ready", "queued", "converting", "done", "failed"


@dataclass(eq=False)
class ConvertItem:
    id: int
    path: str
    kind: str
    meta: str
    duration: float | None = None
    status: str = READY
    percent: float = 0.0
    output: str = ""
    error: str = ""
    target: str = ""

    @property
    def name(self) -> str:
        return Path(self.path).name


class ConvertQueue(QObject):
    item_added = Signal(object)
    item_changed = Signal(object)
    item_removed = Signal(int)
    batch_finished = Signal(int, int)  # concluídos, falhas

    CONCURRENCY = 2

    def __init__(self, ffmpeg: Callable[[], str | None], probes: ProbeService,
                 runner_factory: Callable[[], ProcessRunner] = ProcessRunner,
                 parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._ffmpeg = ffmpeg
        self._probes = probes
        self._runner_factory = runner_factory
        self._ids = count(1)
        self.items: list[ConvertItem] = []
        self._runners: dict[int, ProcessRunner] = {}
        self._errors: dict[int, str] = {}
        self._job: tuple[str, dict, int] | None = None
        self._batch = [0, 0]
        probes.probed.connect(self._on_probed)

    def add_files(self, paths: list[str]) -> int:
        known = {i.path for i in self.items}
        added = 0
        for path in paths:
            p = Path(path)
            if path in known or not p.is_file() or p.suffix.lower().lstrip(".") not in MEDIA_EXTS:
                continue
            item = ConvertItem(next(self._ids), str(p), kind_from_ext(path), describe(path, None, p.stat().st_size))
            self.items.append(item)
            self.item_added.emit(item)
            self._probes.request(item.path)
            self._apply_probe(item)
            added += 1
        return added

    def remove(self, item_id: int) -> None:
        item = next((i for i in self.items if i.id == item_id), None)
        if item:
            self._kill(item)
            self.items.remove(item)
            self.item_removed.emit(item_id)
            self._pump()

    def clear(self) -> None:
        for item in list(self.items):
            self.remove(item.id)

    def ready_count(self) -> int:
        return sum(i.status in (READY, FAILED) for i in self.items)

    def busy(self) -> bool:
        return any(i.status in (QUEUED, CONVERTING) for i in self.items)

    def convert(self, target: str, choices: dict[str, str], crf: int) -> None:
        self._job = (target, dict(choices), crf)
        self._batch = [0, 0]
        for item in self.items:
            if item.status in (READY, FAILED):
                item.status, item.percent, item.error, item.target = QUEUED, 0.0, "", target
                self.item_changed.emit(item)
        self._pump()

    def shutdown(self) -> None:
        for item in self.items:
            self._kill(item)

    # Internos ---------------------------------------------------------------
    def _pump(self) -> None:
        if not self._job:
            return
        running = sum(i.status == CONVERTING for i in self.items)
        for item in self.items:
            if running >= self.CONCURRENCY:
                break
            if item.status == QUEUED:
                self._start(item)
                running += 1
        if not self.busy() and sum(self._batch):
            done, failed = self._batch
            self._batch = [0, 0]
            self.batch_finished.emit(done, failed)

    def _start(self, item: ConvertItem) -> None:
        ffmpeg = self._ffmpeg()
        target, choices, crf = self._job
        if not ffmpeg:
            item.status, item.error = FAILED, "ffmpeg não encontrado"
            self.item_changed.emit(item)
            return
        reserved = {i.output for i in self.items if i.status == CONVERTING and i.output}
        item.status, item.output = CONVERTING, output_path(item.path, target, reserved)
        runner = self._runner_factory()
        runner.setParent(self)
        runner.line.connect(lambda line, i=item: self._on_line(i, line))
        runner.error_line.connect(lambda line, i=item: self._on_error_line(i, line))
        runner.finished.connect(lambda code, i=item, r=runner: self._on_finished(i, r, code))
        self._runners[item.id] = runner
        self.item_changed.emit(item)
        runner.start(ffmpeg, build_args(item.path, item.output, target, choices, crf))

    def _on_line(self, item: ConvertItem, line: str) -> None:
        value = parse_progress(line)
        if isinstance(value, float) and item.duration:
            item.percent = min(99.0, value * 100 / item.duration)
            self.item_changed.emit(item)

    def _on_error_line(self, item: ConvertItem, line: str) -> None:
        # "Conversion failed!" é genérico; a causa vem na linha anterior.
        if not line.startswith("Conversion failed"):
            self._errors[item.id] = line

    def _on_finished(self, item: ConvertItem, runner: ProcessRunner, code: int) -> None:
        if self._runners.get(item.id) is not runner:
            return
        del self._runners[item.id]
        runner.deleteLater()
        if code == 0:
            item.status, item.percent = DONE, 100.0
            self._batch[0] += 1
        else:
            item.status = FAILED
            item.error = self._errors.pop(item.id, "") or f"O ffmpeg terminou com código {code}"
            Path(item.output).unlink(missing_ok=True)
            self._batch[1] += 1
        self.item_changed.emit(item)
        self._pump()

    def _kill(self, item: ConvertItem) -> None:
        runner = self._runners.pop(item.id, None)
        if runner:
            runner.kill()
            runner.deleteLater()
            if item.output:
                Path(item.output).unlink(missing_ok=True)

    def _apply_probe(self, item: ConvertItem) -> None:
        info = self._probes.get(item.path)
        if info:
            item.kind, item.duration = info.kind, info.duration
            item.meta = describe(item.path, info, Path(item.path).stat().st_size)
            self.item_changed.emit(item)

    def _on_probed(self, path: str, _info) -> None:
        for item in self.items:
            if item.path == path:
                self._apply_probe(item)
