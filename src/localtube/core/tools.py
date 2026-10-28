"""Localização e versões das ferramentas externas (yt-dlp, ffmpeg, ffprobe)."""

import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from importlib import metadata
from pathlib import Path

NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)

# Empacotado pelo PyInstaller (packaging/): o yt-dlp roda pelo executável auxiliar e o
# ffmpeg vem na pasta ffmpeg/ ao lado do LocalTube.exe.
FROZEN = bool(getattr(sys, "frozen", False))
APP_DIR = Path(sys.executable).parent
YTDLP_HELPER = "localtube-ytdlp.exe"


@dataclass
class ToolInfo:
    name: str
    path: str | None
    version: str | None

    @property
    def ok(self) -> bool:
        return self.path is not None


def bundled_ytdlp_version() -> str | None:
    # Pelos metadados, sem importar o yt_dlp: o localtube-ytdlp.exe ainda vai escolher
    # entre o embutido e o wheel atualizado.
    try:
        return metadata.version("yt-dlp")
    except metadata.PackageNotFoundError:
        return None


def ytdlp_updates_dir() -> Path:
    """Onde a versão empacotada guarda o wheel do yt-dlp baixado por "Atualizar"."""
    base = os.environ.get("LOCALAPPDATA") or str(Path.home())
    return Path(base) / "LocalTube" / "yt-dlp"


def _wheel_version(path: Path) -> str:
    # yt_dlp-2026.10.26-py3-none-any.whl -> 2026.10.26
    return path.name.split("-")[1]


def updated_ytdlp_wheel(bundled: str | None = None) -> Path | None:
    """O wheel baixado mais novo, se for mais novo que o yt-dlp embutido."""
    bundled = bundled or bundled_ytdlp_version() or "0"
    folder = ytdlp_updates_dir()
    wheels = sorted(folder.glob("yt_dlp-*.whl"), key=lambda p: _version_key(_wheel_version(p)))
    if wheels and is_newer(_wheel_version(wheels[-1]), bundled):
        return wheels[-1]
    return None


def ytdlp_version() -> str | None:
    if FROZEN:
        wheel = updated_ytdlp_wheel()
        if wheel:
            return _wheel_version(wheel)
    return bundled_ytdlp_version()


def ytdlp_command() -> list[str]:
    if FROZEN:
        return [str(APP_DIR / YTDLP_HELPER)]
    return [sys.executable, "-m", "yt_dlp"]


def _exe(name: str) -> str:
    return f"{name}.exe" if os.name == "nt" else name


def _winget_candidates(name: str) -> list[Path]:
    local = os.environ.get("LOCALAPPDATA")
    if not local:
        return []
    winget = Path(local) / "Microsoft" / "WinGet"
    found = [winget / "Links" / _exe(name)]
    packages = winget / "Packages"
    if packages.is_dir():
        found += sorted(packages.glob(f"*FFmpeg*/**/bin/{_exe(name)}"), reverse=True)
    return found


def find_tool(name: str, configured: str = "") -> str | None:
    """Caminho configurado (arquivo ou pasta) → ffmpeg embutido → PATH → instalação do winget."""
    if configured:
        path = Path(configured)
        if path.is_dir():
            path = path / _exe(name)
        elif path.name.lower() != _exe(name).lower():
            path = path.with_name(_exe(name))
        if path.is_file():
            return str(path)
    if FROZEN and (APP_DIR / "ffmpeg" / _exe(name)).is_file():
        return str(APP_DIR / "ffmpeg" / _exe(name))
    on_path = shutil.which(name)
    if on_path:
        return on_path
    for candidate in _winget_candidates(name):
        if candidate.is_file():
            return str(candidate)
    return None


def tool_version(path: str) -> str | None:
    try:
        out = subprocess.run([path, "-version"], capture_output=True, text=True, timeout=10,
                             creationflags=NO_WINDOW).stdout
    except (OSError, subprocess.SubprocessError):
        return None
    match = re.search(r"version\s+(?:n|N-)?([0-9][\w.\-]*)", out)
    if not match:
        return None
    version = match.group(1)
    # "7.1-full_build-www.gyan.dev" -> "7.1"
    return re.split(r"[-_]", version)[0] if re.match(r"\d+\.\d+", version) else version[:12]


def ffmpeg_info(configured: str = "") -> ToolInfo:
    path = find_tool("ffmpeg", configured)
    return ToolInfo("ffmpeg", path, tool_version(path) if path else None)


def ffprobe_path(ffmpeg: str | None) -> str | None:
    if ffmpeg:
        sibling = Path(ffmpeg).with_name(_exe("ffprobe"))
        if sibling.is_file():
            return str(sibling)
    return find_tool("ffprobe")


def _version_key(version: str) -> tuple[int, ...]:
    return tuple(int(p) for p in re.findall(r"\d+", version))


def is_newer(latest: str, current: str) -> bool:
    return _version_key(latest) > _version_key(current)
