"""Tela Converter: arquivos locais → alvo escolhido, com o ffmpeg."""

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QButtonGroup,
    QComboBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QPushButton,
    QSlider,
    QWidget,
)

from localtube import icons, theme
from localtube.core import convert
from localtube.core.convert import AUDIO_TARGETS, CONVERTING, DONE, FAILED, QUEUED, READY, VIDEO_TARGETS, ConvertItem
from localtube.core.formatting import plural
from localtube.core.media import MEDIA_EXTS
from localtube.services import Services
from localtube.ui.widgets.common import (
    Card,
    ClickableFrame,
    ElidedLabel,
    ThinProgress,
    button,
    card_row,
    clear_layout,
    frame,
    hbox,
    icon_box,
    icon_button,
    icon_label,
    label,
    page_header,
    scroll_area,
    section_label,
    set_color,
    set_prop,
    vbox,
)

FILE_FILTER = "Mídia ({});;Todos os arquivos (*)".format(" ".join(f"*.{e}" for e in sorted(MEDIA_EXTS)))


class DropZone(ClickableFrame):
    files_dropped = Signal(list)

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("DropZone")
        self.setFixedHeight(104)
        self.setAcceptDrops(True)
        text = label("Solte arquivos aqui ou <span style='color:#f5866d'>procure</span>", 13, theme.TEXT_3)
        text.setTextFormat(Qt.TextFormat.RichText)
        hint = label("Vídeo e áudio · MP4, MOV, MKV, WEBM, MP3, WAV, FLAC", 11, theme.TEXT_8)
        layout = vbox(icon_label("upload", theme.TEXT_5, 18), text, hint, spacing=7)
        for i in range(layout.count()):
            layout.setAlignment(layout.itemAt(i).widget(), Qt.AlignmentFlag.AlignHCenter)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setLayout(layout)

    def dragEnterEvent(self, event) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            set_prop(self, "dragging", True)

    def dragLeaveEvent(self, event) -> None:
        set_prop(self, "dragging", False)

    def dropEvent(self, event) -> None:
        set_prop(self, "dragging", False)
        paths = [u.toLocalFile() for u in event.mimeData().urls() if u.isLocalFile()]
        files: list[str] = []
        for path in paths:
            p = Path(path)
            files += [str(c) for c in sorted(p.iterdir()) if c.is_file()] if p.is_dir() else [path]
        self.files_dropped.emit(files)


class FileRow(QFrame):
    def __init__(self, item: ConvertItem, page: "ConvertPage") -> None:
        super().__init__()
        self.item = item
        self.page = page
        self.box = icon_box("video" if item.kind == "video" else "audio")
        self.name = ElidedLabel(item.name, 12, mono=True, weight=QFont.Weight.Medium)
        self.meta = ElidedLabel(item.meta, 11.5, theme.TEXT_6)
        self.target = label("", 11.5, theme.ACCENT_TEXT, QFont.Weight.DemiBold)
        target_box = QWidget()
        target_box.setFixedWidth(64)
        target_box.setLayout(hbox(icon_label("arrow-right", theme.TEXT_7, 12, 1.8), self.target, None, spacing=6))
        self.progress = ThinProgress()
        self.line = ElidedLabel("", 11.5, theme.TEXT_6)
        progress_box = QWidget()
        progress_box.setFixedWidth(150)
        progress_box.setLayout(vbox(self.progress, self.line, spacing=5))
        remove = icon_button("close", "Remover", lambda: page.queue.remove(item.id), size=13, stroke=1.8)
        self.setObjectName("CardRow")
        self.setLayout(hbox(self.box, vbox(self.name, self.meta, spacing=3), target_box, progress_box, remove,
                            spacing=14, margins=(14, 11, 12, 11)))
        self.update_item()

    def update_item(self) -> None:
        item = self.item
        self.box.icon_label.setPixmap(icons.pixmap("video" if item.kind == "video" else "audio", theme.TEXT_4, 15))
        self.meta.set_full_text(item.meta)
        target = item.target if item.status in (QUEUED, CONVERTING, DONE) and item.target else self.page.target
        self.target.setText(target.upper())
        done = item.status == DONE
        self.progress.set_value(item.percent, theme.GREEN if done else (theme.RED if item.status == FAILED
                                                                        else theme.ACCENT))
        if item.status == READY:
            text = "Pronto"
        elif item.status == QUEUED:
            text = "Na fila"
        elif item.status == CONVERTING:
            text = f"{int(item.percent)}% · codificando"
        elif done:
            text = f"Concluído · {Path(item.output).name}"
        else:
            text = item.error or "Falhou"
        self.line.set_full_text(text)
        color = theme.GREEN_TEXT if done else (theme.RED_TEXT if item.status == FAILED else theme.TEXT_6)
        set_color(self.line, color)


class ConvertPage(QWidget):
    def __init__(self, services: Services, host) -> None:
        super().__init__()
        self.services = services
        self.queue = services.conversions
        self.host = host
        self.target = "mp4"
        self.choices: dict[str, dict[str, str]] = {}
        self.rows: dict[int, FileRow] = {}

        header, _, _ = page_header("Converter", "Converta mídias locais com o ffmpeg. Os arquivos nunca saem "
                                                "deste computador.")
        drop = DropZone()
        drop.clicked.connect(self._browse)
        drop.files_dropped.connect(self.add_files)
        self.files_label = section_label("Arquivos (0)")
        clear = button("Limpar", "link", on_click=self.queue.clear)
        self.card = Card()
        self.empty = card_row(hbox(label("Nenhum arquivo adicionado.", 12, theme.TEXT_7), margins=(0, 36, 0, 36)))
        self.empty.layout().setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.card.add_row(self.empty)
        left = QWidget()
        left.setLayout(vbox(drop, vbox(hbox(self.files_label, None, clear), self.card, spacing=8), None,
                            spacing=18, margins=(24, 20, 24, 20)))

        side_content = QWidget()
        side_content.setLayout(self._side_panel())
        side = frame(vbox(scroll_area(side_content)), "SidePanel")
        side.setFixedWidth(300)

        self.summary = label("", 12.5, theme.TEXT_2, QFont.Weight.Medium)
        note = label("A saída é salva ao lado de cada arquivo original.", 11.5, theme.TEXT_7)
        self.convert_btn = button("Converter", "primary", on_click=self._convert)
        self.convert_btn.setMinimumWidth(120)
        footer_layout = hbox(vbox(None, self.summary, note, None, spacing=3), self.convert_btn,
                             margins=(24, 0, 20, 0), spacing=16)
        footer_layout.setStretch(0, 1)
        footer = frame(footer_layout, "Footer")
        footer.setFixedHeight(58)

        self.setLayout(vbox(header, hbox(scroll_area(left), side, spacing=0), footer, spacing=0))
        self.queue.item_added.connect(self._on_added)
        self.queue.item_changed.connect(self._on_changed)
        self.queue.item_removed.connect(self._on_removed)
        self.queue.batch_finished.connect(self._on_batch_finished)
        self._set_target("mp4")

    # Painel lateral ------------------------------------------------------------------
    def _side_panel(self):
        self.target_group = QButtonGroup(self)
        self.target_buttons: dict[str, QPushButton] = {}

        def grid(targets: list[str]) -> QGridLayout:
            layout = QGridLayout()
            layout.setSpacing(6)
            for i, target in enumerate(targets):
                btn = QPushButton(target.upper())
                btn.setProperty("variant", "target")
                btn.setCheckable(True)
                btn.setCursor(Qt.CursorShape.PointingHandCursor)
                btn.clicked.connect(lambda _=False, t=target: self._set_target(t))
                self.target_group.addButton(btn)
                self.target_buttons[target] = btn
                layout.addWidget(btn, i // 3, i % 3)
            return layout

        self.fields_layout = vbox(spacing=12)
        self.crf_value = label("", 11, theme.TEXT_3, mono=True)
        self.crf = QSlider(Qt.Orientation.Horizontal)
        self.crf.setRange(0, convert.CRF_MAX - convert.CRF_MIN)
        self.crf.setValue(convert.CRF_MAX - convert.CRF_DEFAULT)
        self.crf.setCursor(Qt.CursorShape.PointingHandCursor)
        self.crf.valueChanged.connect(self._sync_crf)
        self.crf_box = QWidget()
        self.crf_box.setLayout(vbox(hbox(label("Qualidade", 12, theme.TEXT_5), None, self.crf_value),
                                    self.crf,
                                    hbox(label("Menor", 11, theme.TEXT_8), None, label("Melhor", 11, theme.TEXT_8)),
                                    spacing=8))
        self._sync_crf()
        settings_box = QFrame()
        settings_box.setStyleSheet(f"QFrame#ConvSettings {{ border-top: 1px solid {theme.BORDER_ROW}; }}")
        settings_box.setObjectName("ConvSettings")
        settings_box.setLayout(vbox(self.fields_layout, self.crf_box, spacing=12, margins=(0, 16, 0, 0)))
        return vbox(vbox(section_label("Vídeo"), grid(VIDEO_TARGETS)),
                    vbox(section_label("Áudio"), grid(AUDIO_TARGETS)),
                    settings_box, None, spacing=20, margins=(20, 20, 20, 20))

    def _set_target(self, target: str) -> None:
        self.target = target
        self.target_buttons[target].setChecked(True)
        choices = self.choices.setdefault(target, convert.default_choices(target))
        clear_layout(self.fields_layout)
        for field in convert.FIELDS[target]:
            combo = QComboBox()
            for text, value in field.options:
                combo.addItem(text, value)
            combo.setCurrentIndex(max(0, combo.findData(choices[field.key])))
            combo.currentIndexChanged.connect(
                lambda _i, c=combo, k=field.key: self._set_choice(k, c.currentData()))
            box = QWidget()
            box.setLayout(vbox(label(field.label, 12, theme.TEXT_5), combo, spacing=6))
            self.fields_layout.addWidget(box)
        self._refresh()

    def _set_choice(self, key: str, value: str) -> None:
        self.choices[self.target][key] = value
        self._refresh()

    def _crf(self) -> int:
        return convert.CRF_MAX - self.crf.value()

    def _sync_crf(self) -> None:
        self.crf_value.setText(f"CRF {self._crf()}")

    # Arquivos ---------------------------------------------------------------------
    def _browse(self) -> None:
        paths, _ = QFileDialog.getOpenFileNames(self, "Escolher arquivos", "", FILE_FILTER)
        if paths:
            self.add_files(paths)

    def add_files(self, paths: list[str]) -> None:
        if not self.services.ffmpeg.ok:
            self.host.toast("Instale o ffmpeg ou indique o caminho em Configurações", "Configurações",
                            lambda: self.host.go("settings"), error=True)
        added = self.queue.add_files(paths)
        if paths and not added:
            self.host.toast("Nenhum arquivo de mídia novo", error=True)

    def _on_added(self, item: ConvertItem) -> None:
        row = FileRow(item, self)
        self.rows[item.id] = row
        self.card.add_row(row, len(self.rows) - 1)
        self._refresh()

    def _on_changed(self, item: ConvertItem) -> None:
        if item.id in self.rows:
            self.rows[item.id].update_item()
        self._refresh()

    def _on_removed(self, item_id: int) -> None:
        row = self.rows.pop(item_id, None)
        if row:
            self.card.remove_row(row)
        self._refresh()

    def _convert(self) -> None:
        if not self.services.ffmpeg.ok:
            self.host.toast("O ffmpeg não foi encontrado", "Configurações", lambda: self.host.go("settings"),
                            error=True)
            return
        self.queue.convert(self.target, self.choices[self.target], self._crf())

    def _on_batch_finished(self, done: int, failed: int) -> None:
        if failed:
            self.host.toast(f"{plural(done, 'arquivo convertido', 'arquivos convertidos')} · {failed} com falha",
                            error=True)
        else:
            self.host.toast(f"{plural(done, 'arquivo convertido', 'arquivos convertidos')}")
        self.host.notify("Conversão concluída", f"{done} de {done + failed} arquivos convertidos")

    def _refresh(self) -> None:
        n = len(self.queue.items)
        self.files_label.setText(f"Arquivos ({n})")
        self.empty.setVisible(n == 0)
        self.card.refresh()
        self.summary.setText(f"{plural(n, 'arquivo')} → {self.target.upper()}")
        ready = self.queue.ready_count()
        busy = self.queue.busy()
        self.convert_btn.setText("Convertendo…" if busy else (f"Converter {plural(ready, 'arquivo')}" if ready
                                                              else "Converter"))
        self.convert_btn.setEnabled(bool(ready) and not busy)
        self.crf_box.setVisible(convert.uses_crf(self.target, self.choices.get(self.target, {})))
        for row in self.rows.values():
            row.update_item()
