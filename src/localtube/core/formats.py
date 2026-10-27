"""Transforma o info dict do yt-dlp (-J) nas linhas das abas Vídeo e Somente áudio."""

import re
from dataclasses import dataclass

CODEC_ORDER = ["H.264", "VP9", "AV1", "H.265"]
VIDEO_CONTAINERS = ["mp4", "mkv", "webm"]
AUDIO_CONTAINERS = ["mp3", "m4a", "opus", "wav"]
REENCODED_MP3 = [320, 192]


@dataclass
class FormatOption:
    id: str
    kind: str  # "video" | "audio"
    quality: str  # "1080p" | "160 kbps"
    codec: str  # "H.264 + AAC" | "Opus"
    detail: str  # FPS (vídeo) ou taxa de amostragem (áudio)
    container: str  # extensão de origem: mp4, webm, m4a…
    size: int | None
    selector: str  # valor de -f
    height: int | None = None
    abr: float | None = None
    video_codec: str = ""
    badge: str = ""
    audio_quality: str | None = None  # --audio-quality ao recodificar


def video_codec_label(vcodec: str | None) -> str:
    v = (vcodec or "").lower()
    if v.startswith(("avc1", "avc", "h264")):
        return "H.264"
    if v.startswith(("vp09", "vp9")):
        return "VP9"
    if v.startswith("vp8"):
        return "VP8"
    if v.startswith(("av01", "av1")):
        return "AV1"
    if v.startswith(("hvc1", "hev1", "h265", "hevc")):
        return "H.265"
    return v.split(".")[0].upper() or "?"


def audio_codec_label(acodec: str | None) -> str:
    a = (acodec or "").lower()
    if a.startswith("mp4a") or a == "aac":
        return "AAC"
    if a.startswith("opus"):
        return "Opus"
    if a.startswith("vorbis"):
        return "Vorbis"
    if a.startswith("mp3"):
        return "MP3"
    if a.startswith(("ac-3", "ac3", "ec-3", "eac3")):
        return "Dolby"
    return a.split(".")[0].upper() or "?"


def _has(codec: str | None) -> bool:
    return codec not in (None, "none")


def _usable(f: dict) -> bool:
    if f.get("ext") == "mhtml" or "storyboard" in (f.get("format_note") or ""):
        return False
    return not str(f.get("format_id", "")).endswith("-drc")


def _size(f: dict, duration: float | None) -> int | None:
    size = f.get("filesize") or f.get("filesize_approx")
    if size:
        return int(size)
    if f.get("tbr") and duration:
        return int(f["tbr"] * 125 * duration)
    return None


def _rank(f: dict) -> tuple:
    """Prefere HTTPS (tamanho conhecido, retomável) e depois a maior taxa."""
    return (
        (f.get("protocol") or "").startswith("http") and "m3u8" not in (f.get("protocol") or ""),
        bool(f.get("filesize") or f.get("filesize_approx")),
        f.get("tbr") or 0,
    )


def _rate_label(asr: float | None) -> str:
    if not asr:
        return "—"
    khz = asr / 1000
    return (f"{khz:g}".replace(".", ",")) + " kHz"


def _best_audio(audios: list[dict], prefer_ext: str | None) -> dict | None:
    if not audios:
        return None
    pool = [a for a in audios if a.get("ext") == prefer_ext] or audios
    return max(pool, key=lambda a: (a.get("abr") or 0, _rank(a)))


def preferred_height(preferred: str) -> int:
    match = re.match(r"(\d+)p", preferred or "")
    return int(match.group(1)) if match else 1080


def build_options(info: dict, preferred: str = "1080p · MP4") -> tuple[list[FormatOption], list[FormatOption], int]:
    """Devolve (linhas de vídeo, linhas de áudio, total de formatos do yt-dlp)."""
    raw = info.get("formats") or []
    duration = info.get("duration")
    formats = [f for f in raw if _usable(f)]
    audios = [f for f in formats if not _has(f.get("vcodec")) and _has(f.get("acodec"))]
    videos = [f for f in formats if _has(f.get("vcodec")) and f.get("height")]

    # Vídeo: uma linha por (altura, codec, fps), no máximo dois codecs por altura.
    groups: dict[tuple, dict] = {}
    for f in videos:
        key = (f["height"], video_codec_label(f.get("vcodec")), round(f.get("fps") or 0))
        if key not in groups or _rank(f) > _rank(groups[key]):
            groups[key] = f
    by_height: dict[int, list[tuple]] = {}
    for key in groups:
        by_height.setdefault(key[0], []).append(key)

    video_rows: list[FormatOption] = []
    for height in sorted(by_height, reverse=True):
        keys = sorted(by_height[height], key=lambda k: (CODEC_ORDER.index(k[1]) if k[1] in CODEC_ORDER else 9, -k[2]))
        for key in keys[:2]:
            f = groups[key]
            vlabel = key[1]
            if _has(f.get("acodec")):
                selector = f["format_id"]
                alabel = audio_codec_label(f.get("acodec"))
                size = _size(f, duration)
            else:
                audio = _best_audio(audios, "m4a" if f.get("ext") == "mp4" else "webm")
                selector = f"{f['format_id']}+{audio['format_id']}" if audio else f["format_id"]
                alabel = audio_codec_label(audio.get("acodec")) if audio else ""
                vs, as_ = _size(f, duration), (_size(audio, duration) if audio else 0)
                size = (vs or 0) + (as_ or 0) or None
            video_rows.append(FormatOption(
                id=f"v{f['format_id']}", kind="video", quality=f"{height}p",
                codec=f"{vlabel} + {alabel}" if alabel else vlabel,
                detail=str(key[2]) if key[2] else "—", container=f.get("ext") or "?", size=size,
                selector=selector, height=height, video_codec=vlabel,
            ))

    # Áudio: formatos nativos sem repetição + MP3 recodificado.
    audio_groups: dict[tuple, dict] = {}
    for f in audios:
        key = (audio_codec_label(f.get("acodec")), round(f.get("abr") or 0))
        if key not in audio_groups or _rank(f) > _rank(audio_groups[key]):
            audio_groups[key] = f
    audio_rows = [
        FormatOption(
            id=f"a{f['format_id']}", kind="audio", quality=f"{round(f.get('abr') or 0)} kbps",
            codec=audio_codec_label(f.get("acodec")), detail=_rate_label(f.get("asr")),
            container="m4a" if f.get("ext") == "mp4" else (f.get("ext") or "?"),
            size=_size(f, duration), selector=f["format_id"], abr=f.get("abr"),
        )
        for f in sorted(audio_groups.values(), key=lambda a: -(a.get("abr") or 0))
    ]
    if audio_rows:
        audio_rows[0].badge = "Melhor"
    if audios or videos:
        for kbps in REENCODED_MP3:
            audio_rows.append(FormatOption(
                id=f"mp3-{kbps}", kind="audio", quality=f"{kbps} kbps", codec="MP3 · recodificado",
                detail="44,1 kHz", container="mp3", size=int(kbps * 125 * duration) if duration else None,
                selector="ba/b", abr=kbps, audio_quality=f"{kbps}K",
            ))

    recommended = pick_recommended(video_rows, preferred_height(preferred))
    if recommended:
        recommended.badge = "Recomendado"
    return video_rows, audio_rows, len(raw)


def pick_recommended(rows: list[FormatOption], height: int) -> FormatOption | None:
    if not rows:
        return None
    fitting = [r for r in rows if (r.height or 0) <= height] or rows[-1:]
    best_height = max(r.height or 0 for r in fitting)
    same = [r for r in fitting if r.height == best_height]
    return next((r for r in same if r.video_codec == "H.264"), same[0])


def default_selection(rows: list[FormatOption]) -> FormatOption | None:
    return next((r for r in rows if r.badge), rows[0] if rows else None)


def natural_audio_container(option: FormatOption) -> str:
    if option.container in AUDIO_CONTAINERS:
        return option.container
    if option.codec == "Opus":
        return "opus"
    return "m4a" if option.codec == "AAC" else "mp3"
