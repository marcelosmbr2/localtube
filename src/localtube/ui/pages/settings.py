"""Tela Configurações: tudo é salvo assim que muda."""

import json
import sys

from PySide6.QtCore import QProcess, QUrl
from PySide6.QtGui import QFont
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkReply, QNetworkRequest
from PySide6.QtWidgets import QComboBox, QFileDialog, QFrame, QLineEdit, QWidget

from localtube import theme
from localtube.core import tools
from localtube.services import Services
from localtube.settings import BANDWIDTH_OPTIONS, QUALITY_OPTIONS
from localtube.ui.widgets.common import (
    Card,
    ElidedLabel,
    SegmentedControl,
    Toggle,
    button,
    card_row,
    dot,
    hbox,
    label,
    page_header,
    scroll_area,
    section_label,
    set_color,
    vbox,
)

PYPI_URL = "https://pypi.org/pypi/yt-dlp/json"


def setting_row(title: str, description: str, control: QWidget | None, desc_mono: bool = False):
    desc = label(description, 11.5 if desc_mono else 12, theme.TEXT_6, mono=desc_mono)
    left = vbox(label(title, weight=QFont.Weight.Medium), desc, spacing=3)
    layout = hbox(left, None, spacing=24, margins=(16, 13, 16, 13))
    if control is not None:
        layout.addWidget(control)
    row = card_row(layout)
    row.description = desc
    return row


def section(title: str, *rows: QFrame) -> QWidget:
    card = Card()
    for row in rows:
        card.add_row(row)
    head = section_label(title)
    head.setContentsMargins(2, 0, 0, 0)
    box = QWidget()
    box.setLayout(vbox(head, card, spacing=8))
    return box


class SettingsPage(QWidget):
    def __init__(self, services: Services, host) -> None:
        super().__init__()
        self.services = services
        self.settings = services.settings
        self.host = host
        self._net = QNetworkAccessManager(self)
        self._latest: str | None = None
        self._wheel: dict | None = None
        self._pip: QProcess | None = None

        header, _, _ = page_header("Configurações", "As alterações são salvas automaticamente.")
        content = QWidget()
        column = vbox(self._general(), self._downloads(), self._engine(), self._appearance(), None, spacing=24)
        inner = QWidget()
        inner.setMaximumWidth(700)
        inner.setLayout(column)
        content.setLayout(hbox(inner, None, margins=(24, 20, 24, 32)))
        self.setLayout(vbox(header, scroll_area(content), spacing=0))

        self.settings.changed.connect(self._on_setting)
        services.tools_changed.connect(self._sync_ffmpeg)
        self._sync_ffmpeg()

    # Seções ----------------------------------------------------------------
    def _general(self) -> QWidget:
        self.dir_label = ElidedLabel(self.settings.get("download_dir"), 11.5, theme.TEXT_3, mono=True)
        self.dir_label.setMinimumWidth(200)
        path_box = QFrame()
        path_box.setObjectName("PathField")
        path_box.setProperty("tone", "dark")
        path_box.setFixedHeight(28)
        path_box.setLayout(hbox(self.dir_label, margins=(10, 0, 10, 0)))
        change = button("Alterar", size="sm", on_click=self._choose_dir)
        control = QWidget()
        control.setLayout(hbox(path_box, change, spacing=6))

        return section(
            "Geral",
            setting_row("Pasta de downloads", "Onde os novos downloads são salvos.", control),
            setting_row("Monitorar área de transferência", "Oferece inspecionar um link quando ele é copiado.",
                        self._toggle("clipboard_monitor")),
            setting_row("Notificações", "Avisa quando um download ou conversão termina.",
                        self._toggle("notifications")),
        )

    def _downloads(self) -> QWidget:
        quality = self._combo([(q, q) for q in QUALITY_OPTIONS], "preferred_quality")
        bandwidth = self._combo(BANDWIDTH_OPTIONS, "bandwidth_limit")
        conc = SegmentedControl([(str(n), str(n)) for n in range(1, 5)], str(self.settings.get("concurrency")),
                                tone="dark", button_width=32)
        conc.changed.connect(lambda v: self.settings.set("concurrency", int(v)))
        template = self._line_edit("filename_template", 220, mono=True)
        return section(
            "Downloads",
            setting_row("Qualidade preferida", "Pré-selecionada ao inspecionar um link.", quality),
            setting_row("Downloads simultâneos", "Itens extras aguardam na fila.", conc),
            setting_row("Limite de banda", "Vale para todos os downloads ativos somados.", bandwidth),
            setting_row("Modelo de nome", "Usa os campos de modelo de saída do yt-dlp.", template),
        )

    def _engine(self) -> QWidget:
        self.ytdlp_status_dot = dot(theme.GREEN)
        self.ytdlp_status = label("", 12, theme.GREEN_TEXT)
        self.update_btn = button("Verificar agora", size="sm", on_click=self.check_updates)
        status = QWidget()
        status.setLayout(hbox(hbox(self.ytdlp_status_dot, self.ytdlp_status, spacing=6), self.update_btn, spacing=10))
        self.ytdlp_status.setText("")
        self.ytdlp_status_dot.hide()
        version = self.services.ytdlp_version or "não instalado"
        self.ytdlp_row = setting_row("yt-dlp", f"{version} · incluído", status, desc_mono=True)

        ffmpeg_btn = button("Alterar caminho", size="sm", on_click=self._choose_ffmpeg)
        self.ffmpeg_row = setting_row("ffmpeg", "", ffmpeg_btn, desc_mono=True)

        proxy = self._line_edit("proxy", 220, placeholder="Nenhum")
        return section(
            "Motor",
            self.ytdlp_row,
            self.ffmpeg_row,
            setting_row("Proxy", "Encaminha as requisições por um proxy HTTP ou SOCKS.", proxy),
        )

    def _appearance(self) -> QWidget:
        theme_ctl = SegmentedControl([("dark", "Escuro"), ("light", "Claro"), ("system", "Sistema")], "dark",
                                     tone="dark")
        theme_ctl.set_enabled_option("light", False, "Em breve")
        theme_ctl.set_enabled_option("system", False, "Em breve")
        return section(
            "Aparência",
            setting_row("Tema", "Por enquanto o LocalTube tem só o tema escuro.", theme_ctl),
        )

    # Controles -------------------------------------------------------------
    def _toggle(self, key: str) -> Toggle:
        toggle = Toggle(self.settings.get(key))
        toggle.toggled.connect(lambda on: self.settings.set(key, on))
        return toggle

    def _combo(self, options: list[tuple[str, str]], key: str) -> QComboBox:
        combo = QComboBox()
        combo.setProperty("tone", "dark")
        combo.setFixedWidth(160)
        for text, value in options:
            combo.addItem(text, value)
        index = combo.findData(self.settings.get(key))
        combo.setCurrentIndex(max(0, index))
        combo.currentIndexChanged.connect(lambda _: self.settings.set(key, combo.currentData()))
        return combo

    def _line_edit(self, key: str, width: int, mono: bool = False, placeholder: str = "") -> QLineEdit:
        edit = QLineEdit(self.settings.get(key))
        edit.setProperty("tone", "dark")
        edit.setProperty("mono", mono)
        edit.setFixedWidth(width)
        edit.setPlaceholderText(placeholder)
        edit.editingFinished.connect(lambda: self.settings.set(key, edit.text().strip()))
        return edit

    def _choose_dir(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "Pasta de downloads", self.settings.get("download_dir"))
        if path:
            self.settings.set("download_dir", path)

    def _choose_ffmpeg(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Localizar ffmpeg", self.services.ffmpeg.path or "",
                                              "ffmpeg (ffmpeg.exe ffmpeg);;Todos os arquivos (*)")
        if not path:
            return
        self.settings.set("ffmpeg_path", path)
        if self.services.ffmpeg.ok:
            self.host.toast(f"ffmpeg {self.services.ffmpeg.version or ''} encontrado")
        else:
            self.host.toast("Não foi possível usar esse ffmpeg", error=True)

    def _on_setting(self, key: str) -> None:
        if key == "download_dir":
            self.dir_label.set_full_text(self.settings.get("download_dir"))

    def _sync_ffmpeg(self) -> None:
        ff = self.services.ffmpeg
        text = f"{ff.version or '?'} · {ff.path}" if ff.ok else "Não encontrado · instale o ffmpeg ou indique o caminho"
        self.ffmpeg_row.description.setText(text)
        set_color(self.ffmpeg_row.description, theme.TEXT_6 if ff.ok else theme.RED_TEXT)

    # Atualização do yt-dlp -------------------------------------------------
    def check_updates(self) -> None:
        if self._latest and self.services.ytdlp_version and tools.is_newer(self._latest, self.services.ytdlp_version):
            self._run_upgrade()
            return
        self.update_btn.setEnabled(False)
        self.update_btn.setText("Verificando…")
        reply = self._net.get(QNetworkRequest(QUrl(PYPI_URL)))
        reply.finished.connect(lambda: self._on_pypi(reply))

    def _on_pypi(self, reply: QNetworkReply) -> None:
        reply.deleteLater()
        self.update_btn.setEnabled(True)
        self.update_btn.setText("Verificar agora")
        if reply.error() != QNetworkReply.NetworkError.NoError:
            self.host.toast("Não foi possível consultar o PyPI", error=True)
            return
        try:
            data = json.loads(bytes(reply.readAll()).decode())
            self._latest = data["info"]["version"]
        except (ValueError, KeyError):
            self.host.toast("Resposta inesperada do PyPI", error=True)
            return
        self._wheel = next((f for f in data.get("urls", []) if f.get("packagetype") == "bdist_wheel"), None)
        current = self.services.ytdlp_version or "0"
        self.ytdlp_status_dot.show()
        if tools.is_newer(self._latest, current):
            self._set_status(f"Nova versão {self._latest}", theme.AMBER)
            self.update_btn.setText("Atualizar")
            self.host.toast(f"yt-dlp {self._latest} disponível")
        else:
            self._set_status("Atualizado", theme.GREEN)
            self.host.toast(f"yt-dlp {current} está atualizado")

    def _set_status(self, text: str, color: str) -> None:
        self.ytdlp_status.setText(text)
        set_color(self.ytdlp_status, theme.GREEN_TEXT if color == theme.GREEN else color)
        self.ytdlp_status_dot.setStyleSheet(f"background: {color}; border-radius: 3px;")

    def _run_upgrade(self) -> None:
        self.update_btn.setEnabled(False)
        self.update_btn.setText("Atualizando…")
        if tools.FROZEN:
            # A versão empacotada não tem pip: o wheel (um zip importável) fica na pasta do
            # usuário e o localtube-ytdlp.exe o usa no lugar do yt-dlp embutido.
            if not self._wheel:
                self._on_upgrade_done(1, None)
                return
            reply = self._net.get(QNetworkRequest(QUrl(self._wheel["url"])))
            reply.finished.connect(lambda: self._on_wheel(reply))
            return
        self._pip = QProcess(self)
        self._pip.finished.connect(self._on_upgrade_done)
        self._pip.start(sys.executable, ["-m", "pip", "install", "--upgrade", "--disable-pip-version-check", "yt-dlp"])

    def _on_wheel(self, reply: QNetworkReply) -> None:
        reply.deleteLater()
        ok = (reply.error() == QNetworkReply.NetworkError.NoError
              and tools.install_ytdlp_wheel(bytes(reply.readAll()), self._wheel["filename"],
                                            self._wheel["digests"]["sha256"]))
        self._on_upgrade_done(0 if ok else 1, None)

    def _on_upgrade_done(self, code: int, _status) -> None:
        self.update_btn.setEnabled(True)
        self.update_btn.setText("Verificar agora")
        if code == 0:
            # Cada download roda o yt-dlp num processo novo, então a versão nova já vale.
            self.services.ytdlp_version = self._latest
            self.services.tools_changed.emit()
            self.ytdlp_row.description.setText(f"{self._latest} · incluído")
            self._set_status("Atualizado", theme.GREEN)
            self.host.toast(f"yt-dlp {self._latest} instalado · vale para os próximos downloads")
        else:
            self.host.toast("A atualização do yt-dlp falhou", error=True)
