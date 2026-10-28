"""Ponto de entrada do localtube-ytdlp.exe: roda o yt-dlp embutido ou, se houver, o wheel
mais novo baixado por Configurações › Motor › Atualizar."""

import sys

from localtube.core import tools

wheel = tools.updated_ytdlp_wheel()
if wheel:
    sys.path.insert(0, str(wheel))

try:
    import yt_dlp
except Exception:
    if not wheel:
        raise
    # Wheel com defeito (ou feito para outro Python): volta para o yt-dlp embutido em vez
    # de deixar todos os downloads falhando até alguém apagar a pasta de atualizações.
    sys.path.remove(str(wheel))
    for name in [m for m in sys.modules if m == "yt_dlp" or m.startswith("yt_dlp.")]:
        del sys.modules[name]
    import yt_dlp

yt_dlp.main()
