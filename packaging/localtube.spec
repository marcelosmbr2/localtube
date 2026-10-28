# PyInstaller (onedir): LocalTube.exe (janela) e localtube-ytdlp.exe (console, que o app abre
# sem janela) dividem a mesma pasta _internal. Use packaging\build.ps1, que também gera o ícone
# e copia o ffmpeg.
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_submodules, copy_metadata

ROOT = Path(SPECPATH).parent
SRC = ROOT / "src"
ICON = ROOT / "build" / "localtube.ico"
EXCLUDES = ["tkinter", "unittest", "pydoc_data", "test"]

app = Analysis(
    [str(SRC / "localtube" / "__main__.py")],
    pathex=[str(SRC)],
    datas=collect_data_files("localtube") + copy_metadata("yt-dlp"),
    excludes=EXCLUDES + ["yt_dlp"],
)
helper = Analysis(
    [str(Path(SPECPATH) / "ytdlp_entry.py")],
    pathex=[str(SRC)],
    hiddenimports=collect_submodules("yt_dlp"),
    excludes=EXCLUDES + ["PySide6", "shiboken6"],
)

app_exe = EXE(
    PYZ(app.pure),
    app.scripts,
    exclude_binaries=True,
    name="LocalTube",
    console=False,
    icon=str(ICON),
    upx=False,
)
helper_exe = EXE(
    PYZ(helper.pure),
    helper.scripts,
    exclude_binaries=True,
    name="localtube-ytdlp",
    console=True,
    icon=str(ICON),
    upx=False,
)

COLLECT(
    app_exe, app.binaries, app.datas,
    helper_exe, helper.binaries, helper.datas,
    name="LocalTube",
    upx=False,
)
