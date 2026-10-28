"""Fila de downloads: cada item roda `python -m yt_dlp` num ProcessRunner próprio.

Pausar encerra o processo; retomar relança com --continue, que reaproveita o .part.
"""

import time
from collections.abc import Callable
from dataclasses import dataclass, field
from itertools import count

from PySide6.QtCore import QObject, Signal

from localtube.core import tools, ytdlp
from localtube.core.process import ProcessRunner
from localtube.core.ytdlp import DownloadRequest
from localtube.settings import AppSettings

DOWNLOADING, QUEUED, PAUSED, DONE, FAILED = "downloading", "queued", "paused", "done", "failed"
ACTIVE = (DOWNLOADING, QUEUED, PAUSED)


@dataclass(eq=False)
class DownloadJob:
    id: int
    request: DownloadRequest
    status: str = QUEUED
    percent: float = 0.0
    speed: float = 0.0
    eta: float | None = None
    downloaded: int = 0
    total: int | None = None
    error: str = ""
    filepath: str = ""
    finished_at: float | None = None
    postprocessing: bool = False
    # bytes das partes (vídeo, áudio) já concluídas na execução atual
    done_bytes: int = field(default=0, repr=False)
    last_error: str = field(default="", repr=False)

    @property
    def expected_size(self) -> int | None:
        return self.request.size


class DownloadQueue(QObject):
    job_added = Signal(object)
    job_changed = Signal(object)
    job_removed = Signal(int)
    job_finished = Signal(object)

    def __init__(
        self,
        settings: AppSettings,
        ffmpeg: Callable[[], str | None],
        runner_factory: Callable[[], ProcessRunner] = ProcessRunner,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self.settings = settings
        self._ffmpeg = ffmpeg
        self._runner_factory = runner_factory
        self._ids = count(1)
        self.jobs: list[DownloadJob] = []  # mais recente primeiro
        self._runners: dict[int, ProcessRunner] = {}
        settings.changed.connect(self._on_setting)

    # Consultas ----------------------------------------------------------------
    def get(self, job_id: int) -> DownloadJob | None:
        return next((j for j in self.jobs if j.id == job_id), None)

    def active_count(self) -> int:
        return sum(j.status in (DOWNLOADING, QUEUED) for j in self.jobs)

    def counts(self) -> dict[str, int]:
        return {
            "all": len(self.jobs),
            "active": sum(j.status in ACTIVE for j in self.jobs),
            "done": sum(j.status == DONE for j in self.jobs),
            "failed": sum(j.status == FAILED for j in self.jobs),
        }

    def downloading(self) -> list[DownloadJob]:
        return [j for j in self.jobs if j.status == DOWNLOADING]

    def any_running(self) -> bool:
        return any(j.status in (DOWNLOADING, QUEUED) for j in self.jobs)

    # Ações --------------------------------------------------------------------
    def add(self, request: DownloadRequest) -> DownloadJob:
        job = DownloadJob(next(self._ids), request)
        self.jobs.insert(0, job)
        self.job_added.emit(job)
        self._schedule()
        return job

    def pause(self, job_id: int) -> None:
        job = self.get(job_id)
        if job and job.status in (DOWNLOADING, QUEUED):
            self._kill(job)
            job.status, job.speed, job.postprocessing = PAUSED, 0.0, False
            self.job_changed.emit(job)
            self._schedule()

    def resume(self, job_id: int) -> None:
        job = self.get(job_id)
        if job and job.status == PAUSED:
            job.status = QUEUED
            self.job_changed.emit(job)
            self._schedule()

    def retry(self, job_id: int) -> None:
        job = self.get(job_id)
        if job and job.status == FAILED:
            job.status, job.error, job.percent = QUEUED, "", 0.0
            self.job_changed.emit(job)
            self._schedule()

    def remove(self, job_id: int) -> None:
        job = self.get(job_id)
        if not job:
            return
        self._kill(job)
        self.jobs.remove(job)
        self.job_removed.emit(job_id)
        self._schedule()

    def pause_all(self) -> None:
        for job in list(self.jobs):
            if job.status in (DOWNLOADING, QUEUED):
                self.pause(job.id)

    def resume_all(self) -> None:
        for job in self.jobs:
            if job.status == PAUSED:
                job.status = QUEUED
                self.job_changed.emit(job)
        self._schedule()

    def clear_done(self) -> None:
        for job in [j for j in self.jobs if j.status == DONE]:
            self.jobs.remove(job)
            self.job_removed.emit(job.id)

    def shutdown(self) -> None:
        for job in self.jobs:
            self._kill(job)

    # Execução -----------------------------------------------------------------
    def _schedule(self) -> None:
        limit = int(self.settings.get("concurrency"))
        active = len(self.downloading())
        for job in reversed(self.jobs):  # mais antigo primeiro
            if active >= limit:
                break
            if job.status == QUEUED:
                self._start(job)
                active += 1

    def _start(self, job: DownloadJob) -> None:
        job.status, job.speed, job.eta = DOWNLOADING, 0.0, None
        job.done_bytes, job.last_error, job.postprocessing = 0, "", False
        rate = ytdlp.rate_per_job(self.settings.get("bandwidth_limit"), int(self.settings.get("concurrency")))
        args = ytdlp.build_args(job.request, self._ffmpeg(), self.settings.get("proxy"), rate)
        runner = self._runner_factory()
        runner.setParent(self)
        runner.line.connect(lambda line, j=job: self._on_line(j, line))
        runner.error_line.connect(lambda line, j=job: self._on_error_line(j, line))
        runner.finished.connect(lambda code, j=job, r=runner: self._on_finished(j, r, code))
        self._runners[job.id] = runner
        self.job_changed.emit(job)
        program, *base = tools.ytdlp_command()
        runner.start(program, [*base, *args])

    def _kill(self, job: DownloadJob) -> None:
        runner = self._runners.pop(job.id, None)
        if runner:
            runner.kill()
            runner.deleteLater()

    def _on_line(self, job: DownloadJob, line: str) -> None:
        parsed = ytdlp.parse_line(line)
        if not parsed or self._runners.get(job.id) is None:
            return
        kind, value = parsed
        if kind == "file":
            job.filepath = value
            return
        progress: dict = value
        downloaded = int(progress.get("downloaded_bytes") or 0)
        total = progress.get("total_bytes") or progress.get("total_bytes_estimate")
        if progress.get("status") == "finished":
            job.done_bytes += int(total or downloaded)
            job.speed, job.eta, job.postprocessing = 0.0, None, True
        else:
            job.speed = float(progress.get("speed") or 0.0)
            job.eta = progress.get("eta")
            job.postprocessing = False
        current_total = int(total or 0) if progress.get("status") != "finished" else 0
        overall = job.done_bytes + (downloaded if progress.get("status") != "finished" else 0)
        expected = max(job.expected_size or 0, job.done_bytes + current_total)
        job.downloaded, job.total = overall, expected or None
        if expected:
            job.percent = max(job.percent, min(99.5, overall * 100 / expected))
        self.job_changed.emit(job)

    def _on_error_line(self, job: DownloadJob, line: str) -> None:
        message = ytdlp.error_message(line)
        if message:
            job.last_error = message

    def _on_finished(self, job: DownloadJob, runner: ProcessRunner, code: int) -> None:
        if self._runners.get(job.id) is not runner:
            return  # pausado ou removido: o processo foi encerrado de propósito
        del self._runners[job.id]
        runner.deleteLater()
        job.speed, job.eta, job.postprocessing = 0.0, None, False
        if code == 0:
            job.status, job.percent, job.finished_at = DONE, 100.0, time.time()
        else:
            job.status = FAILED
            job.error = job.last_error or f"O yt-dlp terminou com código {code}"
        self.job_changed.emit(job)
        if job.status == DONE:
            self.job_finished.emit(job)
        self._schedule()

    def _on_setting(self, key: str) -> None:
        if key == "concurrency":
            self._schedule()
