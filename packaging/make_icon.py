"""Gera o .ico do executável a partir de icons.app_icon() (PNG em cada tamanho)."""

import struct
import sys

from PySide6.QtCore import QBuffer, QByteArray, QIODevice
from PySide6.QtGui import QGuiApplication

from localtube import icons

SIZES = (16, 24, 32, 48, 64, 128, 256)


def png_bytes(size: int) -> bytes:
    data = QByteArray()
    buffer = QBuffer(data)
    buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    icons.app_icon().pixmap(size, size).save(buffer, "PNG")
    return bytes(data)


def main(target: str) -> None:
    images = [png_bytes(size) for size in SIZES]
    offset = 6 + 16 * len(images)
    header = struct.pack("<HHH", 0, 1, len(images))
    entries = b""
    for size, image in zip(SIZES, images):
        side = 0 if size == 256 else size  # 0 significa 256 no formato ICO
        entries += struct.pack("<BBBBHHII", side, side, 0, 0, 1, 32, len(image), offset)
        offset += len(image)
    with open(target, "wb") as out:
        out.write(header + entries + b"".join(images))


if __name__ == "__main__":
    app = QGuiApplication(sys.argv[:1])  # QPixmap precisa da aplicação
    main(sys.argv[1])
