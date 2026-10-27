"""Tela Fila: progresso, pausa, retomada e falhas dos downloads."""

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QFrame, QWidget

from localtube import theme
from localtube.core.downloads import ACTIVE, DONE, DOWNLOADING, FAILED, PAUSED, QUEUED, DownloadJob
from localtube.core.formatting import fmt_day, fmt_duration, fmt_size, fmt_speed
from localtube.services import Services
from localtube.ui import desktop
from localtube.ui.widgets.common import (
    Card,
    ElidedLabel,
    SegmentedControl,
    ThinProgress,
    button,
    card_row,
    frame,
    hbox,
    icon_box,
    icon_button,
    label,
    page_header_row,
    scroll_area,
    set_color,
    status_pill,
    style_pill,
    vbox,
)

# rótulo, cor do texto, fundo do selo, cor da barra
STATUS = {
    DOWNLOADING: ("Baixando", theme.ACCENT_TEXT, "rgba(240,113,82,.12)", theme.ACCENT),
    QUEUED: ("Na fila", theme.TEXT_4, "#1c1c21", theme.BORDER_STRONG),
    PAUSED: ("Pausado", theme.AMBER, "rgba(224,168,74,.12)", "#6b6b74"),
    DONE: ("Concluído", theme.GREEN_TEXT, "rgba(79,191,135,.12)", theme.GREEN),
    FAILED: ("Falhou", theme.RED_TEXT, "rgba(229,72,77,.12)", theme.RED),
}
FILTERS = {
    "all": lambda j: True,
    "active": lambda j: j.status in ACTIVE,
    "done": lambda j: j.status == DONE,
    "failed": lambda j: j.status == FAILED,
}


def status_line(job: DownloadJob) -> str:
    if job.status == DOWNLOADING:
        if job.postprocessing:
            return "Processando com o ffmpeg…"
        if not job.speed:
            return f"{int(job.percent)}% · iniciando…"
        eta = f" · {fmt_duration(job.eta)} restante" if job.eta is not None else ""
        return f"{int(job.percent)}% · {fmt_speed(job.speed)}{eta}"
    if job.status == QUEUED:
        return "Aguardando vaga livre"
    if job.status == PAUSED:
        if job.total:
            return f"{int(job.percent)}% · {fmt_size(job.downloaded)} de {fmt_size(job.total)}"
        return f"{int(job.percent)}%"
    if job.status == DONE:
        return f"Salvo · {fmt_day(job.finished_at or 0)}"
    return job.error


class JobRow(QFrame):
    def __init__(self, job: DownloadJob, page: "QueuePage") -> None:
        super().__init__()
        self.job = job
        queue = page.services.downloads
        self.box = icon_box("video" if job.request.kind == "video" else "audio")
        self.title = ElidedLabel(job.request.title, weight=QFont.Weight.Medium)
        self.sub = ElidedLabel("", 11.5, theme.TEXT_6)
        self.progress = ThinProgress()
        self.line = ElidedLabel("", 11.5, theme.TEXT_6)
        progress_box = QWidget()
        progress_box.setFixedWidth(250)
        progress_box.setLayout(vbox(self.progress, self.line, spacing=6))
        self.pill = status_pill("", theme.TEXT_4, "#1c1c21")
        pill_box = QWidget()
        pill_box.setFixedWidth(96)
        pill_box.setLayout(hbox(self.pill, None))

        self.pause_btn = icon_button("pause", "Pausar", lambda: queue.pause(job.id), stroke=1.8)
        self.resume_btn = icon_button("play", "Retomar", lambda: queue.resume(job.id))
        self.reveal_btn = icon_button("folder", "Mostrar na pasta", self._reveal, stroke=1.6)
        self.retry_btn = icon_button("refresh", "Tentar novamente", lambda: queue.retry(job.id))
        remove = icon_button("close", "Remover", lambda: queue.remove(job.id), size=13, stroke=1.8)
        actions = QWidget()
        actions.setFixedWidth(76)
        actions.setLayout(hbox(None, self.pause_btn, self.resume_btn, self.reveal_btn, self.retry_btn, remove,
                               spacing=2))

        self.setObjectName("CardRow")
        self.setLayout(hbox(self.box, vbox(self.title, self.sub, spacing=3), progress_box, pill_box, actions,
                            spacing=16, margins=(14, 12, 14, 12)))
        self.update_job()

    def update_job(self) -> None:
        job = self.job
        text, fg, bg, bar = STATUS[job.status]
        req = job.request
        self.sub.set_full_text(" · ".join(p for p in (req.fmt_label, fmt_size(req.size) if req.size else "",
                                                      req.source) if p))
        shown = max(job.percent, 3) if job.status == FAILED else job.percent
        self.progress.set_value(shown, bar)
        self.line.set_full_text(status_line(job))
        set_color(self.line, theme.RED_TEXT if job.status == FAILED else theme.TEXT_6)
        self.pill.setText(text)
        style_pill(self.pill, fg, bg)
        self.pause_btn.setVisible(job.status in (DOWNLOADING, QUEUED))
        self.resume_btn.setVisible(job.status == PAUSED)
        self.reveal_btn.setVisible(job.status == DONE)
        self.retry_btn.setVisible(job.status == FAILED)

    def _reveal(self) -> None:
        desktop.reveal(self.job.filepath or self.job.request.out_dir)


class QueuePage(QWidget):
    def __init__(self, services: Services, host) -> None:
        super().__init__()
        self.services = services
        self.queue = services.downloads
        self.host = host
        self.filter = "all"
        self.rows: dict[int, JobRow] = {}

        self.filters = SegmentedControl([("all", "Todos"), ("active", "Ativos"), ("done", "Concluídos"),
                                         ("failed", "Com falha")], "all", counts=True)
        self.filters.changed.connect(self._set_filter)
        self.pause_all_btn = button("Pausar tudo", size="sm", on_click=self._toggle_all)
        self.pause_all_btn.setFixedHeight(30)
        clear = button("Limpar concluídos", "outline", "sm", on_click=self.queue.clear_done)
        clear.setFixedHeight(30)
        header, self.subtitle = page_header_row("Fila", "", self.filters, self.pause_all_btn, clear)

        self.card = Card()
        self.empty = card_row(hbox(label("Nada nesta visualização.", 12, theme.TEXT_7), margins=(0, 48, 0, 48)))
        self.empty.layout().setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.card.add_row(self.empty)
        content = QWidget()
        content.setLayout(vbox(self.card, None, margins=(24, 16, 24, 16)))

        self.dir_label = ElidedLabel(services.settings.get("download_dir"), 11, theme.TEXT_4, mono=True)
        self.dir_label.setMaximumWidth(self.dir_label.fontMetrics().horizontalAdvance(self.dir_label.full_text()))
        open_link = button("Abrir", "accentLink", on_click=lambda: desktop.open_folder(
            services.settings.get("download_dir")))
        self.throughput = label("Ocioso", 11.5, theme.TEXT_6)
        footer_layout = hbox(label("Salvando em", 11.5, theme.TEXT_6), self.dir_label, open_link, None,
                             self.throughput, spacing=8, margins=(24, 0, 24, 0))
        footer_layout.setStretch(1, 1)
        footer = frame(footer_layout, "Footer")
        footer.setFixedHeight(44)

        self.setLayout(vbox(header, scroll_area(content), footer, spacing=0))
        self.queue.job_added.connect(self._on_added)
        self.queue.job_changed.connect(self._on_changed)
        self.queue.job_removed.connect(self._on_removed)
        services.settings.changed.connect(self._on_setting)
        for job in reversed(self.queue.jobs):
            self._on_added(job)
        self._refresh()

    def _on_added(self, job: DownloadJob) -> None:
        row = JobRow(job, self)
        self.rows[job.id] = row
        self.card.add_row(row, 0)
        self._refresh()

    def _on_changed(self, job: DownloadJob) -> None:
        row = self.rows.get(job.id)
        if row:
            row.update_job()
        self._refresh()

    def _on_removed(self, job_id: int) -> None:
        row = self.rows.pop(job_id, None)
        if row:
            self.card.remove_row(row)
        self._refresh()

    def _set_filter(self, key: str) -> None:
        self.filter = key
        self._refresh()

    def _toggle_all(self) -> None:
        if self.queue.any_running():
            self.queue.pause_all()
        else:
            self.queue.resume_all()

    def _refresh(self) -> None:
        counts = self.queue.counts()
        for key in FILTERS:
            self.filters.set_count(key, counts[key])
        self.subtitle.set_full_text(f"{counts['active']} ativos · {counts['done']} concluídos")
        visible = 0
        for row in self.rows.values():
            show = FILTERS[self.filter](row.job)
            row.setVisible(show)
            visible += show
        self.empty.setVisible(visible == 0)
        self.card.refresh()
        running = self.queue.any_running()
        self.pause_all_btn.setText("Pausar tudo" if running else "Retomar tudo")
        self.pause_all_btn.setEnabled(running or any(j.status == PAUSED for j in self.queue.jobs))
        downloading = self.queue.downloading()
        if downloading:
            total = sum(j.speed for j in downloading)
            self.throughput.setText(f"{len(downloading)} baixando · {fmt_speed(total)} no total")
        else:
            self.throughput.setText("Ocioso")

    def _on_setting(self, key: str) -> None:
        if key == "download_dir":
            path = self.services.settings.get("download_dir")
            self.dir_label.set_full_text(path)
            self.dir_label.setMaximumWidth(self.dir_label.fontMetrics().horizontalAdvance(path))
