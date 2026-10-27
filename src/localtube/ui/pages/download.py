"""Tela Baixar: inspeciona um link com o yt-dlp e monta o pedido de download."""

from PySide6.QtCore import QPointF, QRectF, Qt, QUrl
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen, QPixmap
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkReply, QNetworkRequest
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QFrame,
    QLabel,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QStackedWidget,
    QWidget,
)

from localtube import theme
from localtube.core import formats, ytdlp
from localtube.core.formats import FormatOption
from localtube.core.formatting import fmt_clock, fmt_duration, fmt_relative, fmt_size, fmt_upload_date, parse_clock
from localtube.services import Services
from localtube.ui import desktop
from localtube.ui.widgets.common import (
    Card,
    ClickableFrame,
    ElidedLabel,
    FlowLayout,
    FocusHighlighter,
    SegmentedControl,
    ToggleRow,
    badge,
    button,
    card_row,
    chip,
    dot,
    frame,
    hbox,
    icon_button,
    icon_label,
    label,
    page_header,
    paint_stripes,
    scroll_area,
    section_label,
    set_prop,
    skeleton,
    vbox,
)

SUB_LANG_PREFERENCE = ["pt-BR", "pt", "en"]
COLUMNS = [13, 12, 7, 7, 8]  # proporções das colunas da tabela de formatos (como no mockup)


class Thumbnail(QWidget):
    """Miniatura 192x108 com cantos arredondados e duração no canto."""

    def __init__(self) -> None:
        super().__init__()
        self.setFixedSize(192, 108)
        self._pixmap: QPixmap | None = None
        self._duration = ""

    def set_content(self, pixmap: QPixmap | None, duration: str) -> None:
        self._pixmap, self._duration = pixmap, duration
        self.update()

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        rect = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        path = QPainterPath()
        path.addRoundedRect(rect, 8, 8)
        p.setClipPath(path)
        if self._pixmap and not self._pixmap.isNull():
            scaled = self._pixmap.scaled(self.size() * 2, Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                                         Qt.TransformationMode.SmoothTransformation)
            scaled.setDevicePixelRatio(2)
            x = (self.width() - scaled.width() / 2) / 2
            y = (self.height() - scaled.height() / 2) / 2
            p.drawPixmap(QPointF(x, y), scaled)
        else:
            paint_stripes(p, rect)
            p.setPen(QColor(theme.TEXT_9))
            p.setFont(theme.mono_font(10))
            p.drawText(rect, Qt.AlignmentFlag.AlignCenter, "miniatura")
        p.setClipping(False)
        p.setPen(QPen(QColor(theme.BORDER_SEGMENT), 1))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPath(path)
        if self._duration:
            p.setFont(theme.mono_font(10.5))
            w = p.fontMetrics().horizontalAdvance(self._duration) + 10
            box = QRectF(self.width() - w - 6, self.height() - 18 - 6, w, 18)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(0, 0, 0, 190))
            p.drawRoundedRect(box, 4, 4)
            p.setPen(QColor(theme.TEXT))
            p.drawText(box, Qt.AlignmentFlag.AlignCenter, self._duration)


class Radio(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setFixedSize(14, 14)
        self.checked = False
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(QPen(QColor(theme.ACCENT if self.checked else theme.RING), 1.5))
        p.drawEllipse(QRectF(0.75, 0.75, 12.5, 12.5))
        if self.checked:
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(theme.ACCENT))
            p.drawEllipse(QRectF(4, 4, 6, 6))


def table_columns(cells: list[QWidget], first: QWidget) -> object:
    layout = hbox(spacing=0, margins=(0, 0, 14, 0))
    first.setFixedWidth(40)
    layout.addWidget(first)
    for cell, stretch in zip(cells, COLUMNS, strict=True):
        cell.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        layout.addWidget(cell, stretch)
    return layout


class FormatRow(ClickableFrame):
    def __init__(self, option: FormatOption) -> None:
        super().__init__()
        self.option = option
        self.setObjectName("CardRow")
        self.setProperty("clickable", True)
        self.setFixedHeight(40)
        self.radio = Radio()
        radio_cell = QWidget()
        radio_cell.setLayout(hbox(self.radio))
        radio_cell.layout().setAlignment(Qt.AlignmentFlag.AlignCenter)
        quality = QWidget()
        q_layout = hbox(label(option.quality, weight=QFont.Weight.Medium), spacing=8)
        if option.badge:
            q_layout.addWidget(badge(option.badge))
        q_layout.addStretch(1)
        quality.setLayout(q_layout)
        size = label(fmt_size(option.size), color=theme.TEXT_3)
        size.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        cells = [
            quality,
            ElidedLabel(option.codec, color=theme.TEXT_4),
            label(option.detail, color=theme.TEXT_4),
            label(option.container, 11.5, theme.TEXT_4, mono=True),
            size,
        ]
        self.setLayout(table_columns(cells, radio_cell))

    def set_selected(self, selected: bool) -> None:
        self.radio.checked = selected
        self.radio.update()
        set_prop(self, "selected", selected)


class DownloadPage(QWidget):
    def __init__(self, services: Services, host) -> None:
        super().__init__()
        self.services = services
        self.settings = services.settings
        self.host = host
        self.info: dict | None = None
        self.url = ""
        self.video_rows: list[FormatOption] = []
        self.audio_rows: list[FormatOption] = []
        self.total_formats = 0
        self.tab = "video"
        self.selected: FormatOption | None = None
        self.container = "mp4"
        self.out_dir = self.settings.get("download_dir")
        self.thumb_pixmap: QPixmap | None = None
        self._format_rows: list[FormatRow] = []
        self._net = QNetworkAccessManager(self)
        self._thumb_reply: QNetworkReply | None = None
        self.inspector = ytdlp.Inspector(self)
        self.inspector.finished.connect(self._on_info)
        self.inspector.failed.connect(self._on_failed)

        header, _, outer = page_header("Baixar", "Cole um link para ver os formatos disponíveis antes de salvar "
                                                 "qualquer coisa.")
        outer.addLayout(self._url_bar())
        self.body = QStackedWidget()
        self.empty_view = self._empty_view()
        self.loading_view = self._loading_view()
        self.error_view = self._error_view()
        self.ready_view = self._ready_view()
        for view in (self.empty_view, self.loading_view, self.error_view, self.ready_view):
            self.body.addWidget(view)
        self.setLayout(vbox(header, self.body, spacing=0))

        self.settings.changed.connect(self._on_setting)
        self._refresh_recent()
        self._set_phase("empty")

    # Barra de URL ---------------------------------------------------------------
    def _url_bar(self):
        self.url_edit = QLineEdit()
        self.url_edit.setProperty("bare", True)
        self.url_edit.setFont(theme.ui_font(13))
        self.url_edit.setPlaceholderText("https://")
        self.url_edit.returnPressed.connect(lambda: self.inspect(self.url_edit.text()))
        self.url_edit.textChanged.connect(lambda t: self.clear_btn.setVisible(bool(t)))
        self.clear_btn = icon_button("close", "Limpar", self.clear, size=13, stroke=1.8)
        self.clear_btn.setFixedSize(24, 24)
        self.clear_btn.hide()
        field = frame(hbox(icon_label("link", theme.TEXT_7, 15, 1.7), self.url_edit, self.clear_btn, spacing=10,
                           margins=(12, 0, 6, 0)), "UrlField")
        field.setFixedHeight(36)
        FocusHighlighter(self.url_edit, field)
        paste = button("Colar", size="lg", icon_name="clipboard", on_click=self.paste)
        self.inspect_btn = button("Inspecionar", "primary", "lg", on_click=lambda: self.inspect(self.url_edit.text()))
        self.inspect_btn.setMinimumWidth(96)
        return hbox(field, paste, self.inspect_btn, spacing=8)

    # Estados --------------------------------------------------------------------
    def _empty_view(self) -> QWidget:
        box = QFrame()
        box.setFixedSize(40, 40)
        box.setStyleSheet(f"background: #151518; border: 1px solid {theme.BORDER_INPUT}; border-radius: 10px;")
        box.setLayout(hbox(icon_label("link", theme.TEXT_4, 18)))
        box.layout().setAlignment(Qt.AlignmentFlag.AlignCenter)
        text = label("O LocalTube lista primeiro todos os formatos disponíveis. Nada é baixado até você "
                     "escolher um.", 12, theme.TEXT_6)
        text.setWordWrap(True)
        text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title = label("Cole um link de vídeo", 14, weight=QFont.Weight.DemiBold)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.recent_card = Card(radius=9)
        recent_head = section_label("Recentes")
        recent_head.setContentsMargins(10, 0, 0, 0)
        self.recent_box = QWidget()
        self.recent_box.setLayout(vbox(recent_head, self.recent_card, spacing=6))

        column = QWidget()
        column.setFixedWidth(440)
        layout = vbox(box, vbox(title, text, spacing=5), 18, self.recent_box, spacing=14)
        layout.setAlignment(box, Qt.AlignmentFlag.AlignHCenter)
        column.setLayout(layout)
        content = QWidget()
        content.setLayout(vbox(hbox(None, column, None), None, margins=(24, 72, 24, 24)))
        return scroll_area(content)

    def _loading_view(self) -> QWidget:
        lines = vbox(skeleton(None, 14, theme.BG_SKELETON_2), skeleton(None, 10), skeleton(None, 10), None,
                     spacing=10, margins=(0, 4, 0, 0))
        for i, ratio in enumerate((0.7, 0.4, 0.55)):
            lines.itemAt(i).widget().setMaximumWidth(int(520 * ratio))
        media = hbox(skeleton(192, 108, radius=8), lines, spacing=16)
        rows = vbox(*[skeleton(None, 36, "#141417", 6) for _ in range(4)], spacing=8)
        status = hbox(dot(theme.ACCENT), label("Lendo formatos com o yt-dlp…", 12, theme.TEXT_6), None)
        left = QWidget()
        left.setLayout(vbox(media, rows, status, None, spacing=22, margins=(24, 20, 24, 20)))
        side = frame(vbox(), "SidePanel")
        side.setFixedWidth(300)
        view = QWidget()
        view.setLayout(hbox(left, side, spacing=0))
        return view

    def _error_view(self) -> QWidget:
        self.error_text = label("", 12, theme.TEXT_6)
        self.error_text.setWordWrap(True)
        self.error_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.error_text.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        title = label("Não foi possível ler este link", 14, weight=QFont.Weight.DemiBold)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        retry = button("Tentar novamente", on_click=lambda: self.inspect(self.url))
        alert = icon_label("alert", theme.RED_TEXT, 22, 1.7)
        column = QWidget()
        column.setFixedWidth(440)
        layout = vbox(alert, title, self.error_text, 6, retry, spacing=8)
        for w in (alert, retry):
            layout.setAlignment(w, Qt.AlignmentFlag.AlignHCenter)
        column.setLayout(layout)
        view = QWidget()
        view.setLayout(vbox(hbox(None, column, None), None, margins=(24, 72, 24, 24)))
        return view

    def _ready_view(self) -> QWidget:
        left = QWidget()
        left.setLayout(vbox(self._media_header(), self._formats_section(), None, spacing=22,
                            margins=(24, 20, 24, 24)))
        side = frame(vbox(), "SidePanel")
        side.setFixedWidth(300)
        side_content = QWidget()
        side_content.setLayout(self._side_panel())
        side_scroll = scroll_area(side_content)
        side.layout().addWidget(side_scroll)
        main = hbox(scroll_area(left), side, spacing=0)
        view = QWidget()
        view.setLayout(vbox(main, self._footer(), spacing=0))
        return view

    def _media_header(self):
        self.thumb = Thumbnail()
        self.title_label = label("", 14, weight=QFont.Weight.DemiBold)
        self.title_label.setWordWrap(True)
        self.title_label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self.meta_label = label("", 12, theme.TEXT_5)
        self.chips = FlowLayout(6)
        chips_box = QWidget()
        chips_box.setLayout(self.chips)
        info = vbox(self.title_label, self.meta_label, 2, chips_box, None, spacing=8, margins=(0, 2, 0, 0))
        actions = vbox(hbox(icon_button("copy", "Copiar link", self._copy_link, outline=True),
                            icon_button("external", "Abrir no navegador", lambda: desktop.open_url(self.url),
                                        outline=True), spacing=4), None)
        layout = hbox(self.thumb, info, actions, spacing=16)
        layout.setAlignment(self.thumb, Qt.AlignmentFlag.AlignTop)
        return layout

    def _formats_section(self):
        self.tabs = SegmentedControl([("video", "Vídeo"), ("audio", "Somente áudio")], "video")
        self.tabs.changed.connect(self._set_tab)
        self.count_label = label("", 12, theme.TEXT_7)
        self.table = Card(radius=9, plain=True)
        self.col3_label = QLabel("FPS")
        header_cells = [QLabel("Qualidade"), QLabel("Codec"), self.col3_label, QLabel("Contêiner"), QLabel("Tamanho")]
        header_cells[-1].setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        for cell in header_cells:
            cell.setFont(theme.section_font())
            cell.setStyleSheet(f"color: {theme.TEXT_7}; background: transparent;")
        header = frame(table_columns(header_cells, QWidget()), "TableHeader")
        header.setFixedHeight(32)
        self.table.add_row(header)
        return vbox(hbox(self.tabs, None, self.count_label), self.table, spacing=10)

    def _side_panel(self):
        self.containers = SegmentedControl([], expand=True, size="lg")
        self.containers.changed.connect(self._set_container)

        self.dir_label = ElidedLabel(self.out_dir, 11.5, theme.TEXT_3, mono=True)
        change = button("Alterar", "ghost", on_click=self._choose_dir)
        change.setFixedHeight(24)
        path_layout = hbox(icon_label("folder", theme.TEXT_5, 14), self.dir_label, change, spacing=8,
                           margins=(10, 0, 4, 0))
        path_layout.setStretch(1, 1)
        path_field = frame(path_layout, "PathField")
        path_field.setFixedHeight(32)

        self.template_edit = QLineEdit(self.settings.get("filename_template"))
        self.template_edit.setProperty("mono", True)
        self.template_edit.setFixedHeight(32)
        self.template_edit.textChanged.connect(self._refresh_summary)
        self.preview_label = ElidedLabel("", 11.5, theme.TEXT_7)

        self.opt_thumb = ToggleRow("Incorporar miniatura", self.settings.get("embed_thumbnail"))
        self.opt_meta = ToggleRow("Incorporar metadados", self.settings.get("embed_metadata"))
        self.opt_subs = ToggleRow("Legendas", self.settings.get("write_subs"))
        self.opt_chapters = ToggleRow("Dividir por capítulos", self.settings.get("split_chapters"))
        for row, key in ((self.opt_thumb, "embed_thumbnail"), (self.opt_meta, "embed_metadata"),
                         (self.opt_subs, "write_subs"), (self.opt_chapters, "split_chapters")):
            row.toggled.connect(lambda on, k=key: (self.settings.set(k, on), self._refresh_summary()))
        options_head = section_label("Opções")
        options_head.setContentsMargins(0, 0, 0, 4)

        self.range_start = self._clock_edit()
        self.range_end = self._clock_edit()
        dash = label("–", color=theme.TEXT_9)
        range_row = hbox(self.range_start, dash, self.range_end, spacing=6)

        return vbox(
            vbox(section_label("Salvar como"), self.containers),
            vbox(section_label("Pasta"), path_field),
            vbox(section_label("Nome do arquivo"), self.template_edit, self.preview_label),
            vbox(options_head, self.opt_thumb, self.opt_meta, self.opt_subs, self.opt_chapters, spacing=4),
            vbox(section_label("Intervalo"), range_row),
            None,
            spacing=20, margins=(20, 20, 20, 20),
        )

    def _clock_edit(self) -> QLineEdit:
        edit = QLineEdit("00:00:00")
        edit.setProperty("mono", True)
        edit.setAlignment(Qt.AlignmentFlag.AlignCenter)
        edit.setInputMask("99:99:99")
        edit.setFixedHeight(30)
        edit.editingFinished.connect(self._refresh_summary)
        return edit

    def _footer(self) -> QFrame:
        self.summary_label = ElidedLabel("", 12.5, theme.TEXT_2, QFont.Weight.Medium)
        note = label("Salve apenas conteúdo que seja seu ou que você tenha permissão para baixar.", 11.5,
                     theme.TEXT_7)
        copy_cmd = button("Copiar comando", icon_name="terminal", on_click=self._copy_command)
        self.download_btn = QPushButton()
        self.download_btn.setProperty("variant", "primary")
        self.download_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        text = label("Baixar", 12.5, theme.ON_ACCENT, QFont.Weight.DemiBold)
        hint = label("Ctrl ↵", 10.5, theme.ON_ACCENT, QFont.Weight.Medium)
        hint.setStyleSheet(f"color: {theme.ON_ACCENT}; background: rgba(26,14,10,.14); border-radius: 4px; "
                           "padding: 1px 5px;")
        for w in (text, hint):
            w.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        btn_layout = hbox(text, hint, spacing=10, margins=(14, 0, 10, 0))
        self.download_btn.setLayout(btn_layout)
        self.download_btn.setFixedWidth(btn_layout.sizeHint().width())
        self.download_btn.clicked.connect(self.download)
        layout = hbox(vbox(None, self.summary_label, note, None, spacing=3), 8, copy_cmd, self.download_btn,
                      spacing=8, margins=(24, 0, 20, 0))
        layout.setStretch(0, 1)
        footer = frame(layout, "Footer")
        footer.setFixedHeight(58)
        return footer

    # Fluxo ----------------------------------------------------------------------
    def inspect(self, url: str) -> None:
        url = url.strip()
        if not url:
            self.url_edit.setFocus()
            return
        if not url.lower().startswith(("http://", "https://")):
            url = "https://" + url
        self.url = url
        self.url_edit.setText(url)
        self._set_phase("loading")
        self.inspector.inspect(url, self.settings.get("proxy"))

    def paste(self) -> None:
        text = QApplication.clipboard().text().strip()
        if text:
            self.url_edit.setText(text)
            self.inspect(text)
        else:
            self.host.toast("A área de transferência está vazia", error=True)

    def clear(self) -> None:
        self.inspector.cancel()
        self.url_edit.clear()
        self.url = ""
        self.info = None
        self._set_phase("empty")
        self.url_edit.setFocus()

    def primary_action(self) -> None:
        if self.body.currentWidget() is self.ready_view:
            self.download()

    def on_shown(self) -> None:
        if not self.url_edit.text():
            self.url_edit.setFocus()

    def _set_phase(self, phase: str) -> None:
        view = {"empty": self.empty_view, "loading": self.loading_view, "error": self.error_view,
                "ready": self.ready_view}[phase]
        self.body.setCurrentWidget(view)
        loading = phase == "loading"
        self.inspect_btn.setText("Inspecionando…" if loading else "Inspecionar")
        self.inspect_btn.setEnabled(not loading)

    def _on_failed(self, message: str) -> None:
        self.error_text.setText(message)
        self._set_phase("error")

    def _on_info(self, info: dict) -> None:
        self.info = info
        self.url = info.get("webpage_url") or self.url
        self.video_rows, self.audio_rows, self.total_formats = formats.build_options(
            info, self.settings.get("preferred_quality"))
        title = info.get("title") or "Sem título"
        self.settings.add_recent(title, ytdlp.domain(self.url), self.url)
        self._fill_media(info)
        tab = "video" if self.video_rows else "audio"
        self.tabs.set_value(tab)
        self._set_tab(tab)
        self._load_thumbnail(info)
        self._set_phase("ready")

    def _fill_media(self, info: dict) -> None:
        self.title_label.setText(info.get("title") or "Sem título")
        duration = info.get("duration")
        parts = [info.get("channel") or info.get("uploader") or "", fmt_upload_date(info.get("upload_date")),
                 fmt_duration(duration) if duration else ""]
        self.meta_label.setText("  ·  ".join(p for p in parts if p))
        self.thumb.set_content(None, fmt_duration(duration) if duration else "")

        self.chips.clear()
        license_text = info.get("license") or ""
        if license_text:
            short = "Creative Commons" if "creative commons" in license_text.lower() else license_text[:32]
            self.chips.addWidget(chip(short, "green", "check"))
        chapters = info.get("chapters") or []
        if chapters:
            self.chips.addWidget(chip(f"{len(chapters)} capítulos"))
        subs = [k for k in (info.get("subtitles") or {}) if k != "live_chat"]
        if subs:
            shown = ", ".join(s.upper() for s in subs[:3]) + (f" +{len(subs) - 3}" if len(subs) > 3 else "")
            self.chips.addWidget(chip(f"Legendas · {shown}"))
        self.chips.addWidget(chip(ytdlp.domain(self.url)))

        self.sub_lang = next((lang for lang in SUB_LANG_PREFERENCE if lang in subs), subs[0] if subs else None)
        self.opt_subs.text_label.setText(f"Legendas ({self.sub_lang.upper()})" if self.sub_lang
                                         else "Legendas (indisponíveis)")
        self.opt_subs.setEnabled(bool(self.sub_lang))
        self.opt_chapters.setEnabled(bool(chapters))
        self.range_start.setText("00:00:00")
        self.range_end.setText(fmt_clock(duration))
        for edit in (self.range_start, self.range_end):
            edit.setEnabled(bool(duration))

    def _load_thumbnail(self, info: dict) -> None:
        thumbs = [t.get("url") for t in info.get("thumbnails") or [] if t.get("url")]
        jpgs = [u for u in thumbs if u.split("?")[0].lower().endswith((".jpg", ".jpeg", ".png"))]
        url = (jpgs or thumbs or [info.get("thumbnail")])[-1]
        if self._thumb_reply:
            self._thumb_reply.abort()
        if not url:
            return
        reply = self._net.get(QNetworkRequest(QUrl(url)))
        self._thumb_reply = reply
        reply.finished.connect(lambda: self._on_thumbnail(reply))

    def _on_thumbnail(self, reply: QNetworkReply) -> None:
        reply.deleteLater()
        if reply is not self._thumb_reply or reply.error() != QNetworkReply.NetworkError.NoError:
            return
        self._thumb_reply = None
        pixmap = QPixmap()
        if pixmap.loadFromData(bytes(reply.readAll())):
            duration = self.info.get("duration") if self.info else None
            self.thumb.set_content(pixmap, fmt_duration(duration) if duration else "")

    # Seleção --------------------------------------------------------------------
    def _rows(self) -> list[FormatOption]:
        return self.video_rows if self.tab == "video" else self.audio_rows

    def _set_tab(self, tab: str) -> None:
        self.tab = tab
        rows = self._rows()
        self.col3_label.setText("FPS" if tab == "video" else "Taxa")
        for row in self._format_rows:
            self.table.remove_row(row)
        self._format_rows = []
        for option in rows:
            row = FormatRow(option)
            row.clicked.connect(lambda o=option: self._select(o))
            self.table.add_row(row)
            self._format_rows.append(row)
        self.count_label.setText(f"{len(rows)} de {self.total_formats} formatos")
        options = formats.VIDEO_CONTAINERS if tab == "video" else formats.AUDIO_CONTAINERS
        self.containers.set_options([(c, c.upper()) for c in options])
        self.container = options[0]
        self._select(formats.default_selection(rows))

    def _select(self, option: FormatOption | None) -> None:
        self.selected = option
        for row in self._format_rows:
            row.set_selected(row.option is option)
        if option and option.kind == "audio":
            self.container = formats.natural_audio_container(option)
            self.containers.set_value(self.container)
        self._refresh_summary()

    def _set_container(self, container: str) -> None:
        self.container = container
        self._refresh_summary()

    def _refresh_summary(self) -> None:
        option = self.selected
        if not option:
            self.summary_label.set_full_text("Nenhum formato disponível")
            self.download_btn.setEnabled(False)
            return
        self.download_btn.setEnabled(True)
        size = f"≈ {fmt_size(option.size)}" if option.size else "tamanho desconhecido"
        if option.kind == "video":
            text = f"{option.quality} · {self.container.upper()} · {option.codec} · {size}"
        else:
            text = f"Áudio · {self.container.upper()} · {option.quality} · {size}"
        self.summary_label.set_full_text(text)
        title = (self.info or {}).get("title") or "video"
        template = self.template_edit.text() or "%(title)s.%(ext)s"
        preview = template.replace("%(title)s", title).replace("%(ext)s", self.container)
        self.preview_label.set_full_text(f"→ {preview}")

    def _section(self) -> tuple[int, int] | None:
        duration = (self.info or {}).get("duration")
        start, end = parse_clock(self.range_start.text()), parse_clock(self.range_end.text())
        if not duration or start is None or end is None:
            return None
        end = min(end, int(duration))
        if start <= 0 and end >= int(duration):
            return None
        return (start, end) if end > start else None

    def build_request(self) -> ytdlp.DownloadRequest | None:
        option = self.selected
        if not option or not self.info:
            return None
        fmt_label = (f"{option.quality} · {self.container.upper()}" if option.kind == "video"
                     else f"{self.container.upper()} · {option.quality}")
        return ytdlp.DownloadRequest(
            url=self.url, title=self.info.get("title") or self.url, kind=option.kind, selector=option.selector,
            container=self.container, out_dir=self.out_dir,
            template=self.template_edit.text().strip() or "%(title)s.%(ext)s", fmt_label=fmt_label,
            source=ytdlp.domain(self.url), size=option.size, video_codec=option.video_codec,
            audio_quality=option.audio_quality, embed_thumbnail=self.opt_thumb.is_checked(),
            embed_metadata=self.opt_meta.is_checked(),
            subtitles=[self.sub_lang] if self.sub_lang and self.opt_subs.is_checked() else [],
            split_chapters=self.opt_chapters.isEnabled() and self.opt_chapters.is_checked(),
            section=self._section(),
        )

    def download(self) -> None:
        request = self.build_request()
        if not request:
            return
        if not self.services.ffmpeg.ok:
            self.host.toast("O ffmpeg é necessário para juntar e converter os arquivos", "Configurações",
                            lambda: self.host.go("settings"), error=True)
            return
        self.services.downloads.add(request)
        self.host.toast(f"Adicionado à fila · {request.fmt_label}", "Ver fila", lambda: self.host.go("queue"))

    def _copy_link(self) -> None:
        self.host.copy_text(self.url)
        self.host.toast("Link copiado")

    def _copy_command(self) -> None:
        request = self.build_request()
        if request:
            self.host.copy_text(ytdlp.command_string(request, self.settings.get("proxy")))
            self.host.toast("Comando do yt-dlp copiado")

    def _choose_dir(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "Salvar em", self.out_dir)
        if path:
            self.out_dir = path
            self.dir_label.set_full_text(path)

    # Recentes e configurações ------------------------------------------------------
    def _refresh_recent(self) -> None:
        self.recent_card.clear_rows()
        recent = self.settings.recent()
        self.recent_box.setVisible(bool(recent))
        for item in recent:
            texts = vbox(ElidedLabel(item.get("t", "")), label(item.get("d", ""), 11.5, theme.TEXT_7), spacing=2)
            row = card_row(hbox(icon_label("clock", theme.TEXT_7, 14), texts,
                                label(fmt_relative(item.get("ts", 0)), 11.5, theme.TEXT_7), spacing=12,
                                margins=(12, 10, 12, 10)), clickable=True)
            row.clicked.connect(lambda u=item.get("u", ""): self.inspect(u))
            self.recent_card.add_row(row)

    def _on_setting(self, key: str) -> None:
        if key == "recent":
            self._refresh_recent()
        elif key == "download_dir":
            self.out_dir = self.settings.get("download_dir")
            self.dir_label.set_full_text(self.out_dir)
        elif key == "filename_template":
            self.template_edit.setText(self.settings.get("filename_template"))

    def shutdown(self) -> None:
        self.inspector.cancel()
