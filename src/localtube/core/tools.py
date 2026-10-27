"""Localização e versões das ferramentas externas (yt-dlp, ffmpeg, ffprobe)."""

import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


@dataclass
class ToolInfo:
    name: str
    path: str | None
    version: str | None

    @property
    def ok(self) -> bool:
        return self.path is not None


def ytdlp_version() -> str | None:
    try:
        from yt_dlp.version import __version__
    except ImportError:
        return None
    return __version__


def ytdlp_command() -> list[str]:
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
    """Caminho configurado (arquivo ou pasta) → PATH → instalação do winget."""
    if configured:
        path = Path(configured)
        if path.is_dir():
            path = path / _exe(name)
        elif path.name.lower() != _exe(name).lower():
            path = path.with_name(_exe(name))
        if path.is_file():
            return str(path)
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


def is_newer(latest: str, current: str) -> bool:
    def key(v: str) -> tuple[int, ...]:
        return tuple(int(p) for p in re.findall(r"\d+", v))

    return key(latest) > key(current)
