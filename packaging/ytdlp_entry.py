"""Ponto de entrada do localtube-ytdlp.exe: roda o yt-dlp embutido ou, se houver, o wheel
mais novo baixado por Configurações › Motor › Atualizar."""

import sys

from localtube.core import tools

wheel = tools.updated_ytdlp_wheel()
if wheel:
    sys.path.insert(0, str(wheel))

import yt_dlp  # noqa: E402

yt_dlp.main()
