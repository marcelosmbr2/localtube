"""QProcess com saída em linhas UTF-8, usado para o yt-dlp, o ffmpeg e o ffprobe."""

from PySide6.QtCore import QObject, QProcess, QProcessEnvironment, Signal


class ProcessRunner(QObject):
    line = Signal(str)
    error_line = Signal(str)
    finished = Signal(int)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._proc = QProcess(self)
        env = QProcessEnvironment.systemEnvironment()
        env.insert("PYTHONUTF8", "1")
        env.insert("PYTHONIOENCODING", "utf-8")
        self._proc.setProcessEnvironment(env)
        self._out = b""
        self._err = b""
        self._proc.readyReadStandardOutput.connect(self._read_out)
        self._proc.readyReadStandardError.connect(self._read_err)
        self._proc.finished.connect(self._on_finished)
        self._proc.errorOccurred.connect(self._on_error)
        self._done = False

    def start(self, program: str, args: list[str]) -> None:
        self._proc.start(program, args)

    def kill(self) -> None:
        if self._proc.state() != QProcess.ProcessState.NotRunning:
            self._proc.kill()

    def is_running(self) -> bool:
        return self._proc.state() != QProcess.ProcessState.NotRunning

    def _read_out(self) -> None:
        self._out = self._emit_lines(self._out + bytes(self._proc.readAllStandardOutput()), self.line)

    def _read_err(self) -> None:
        self._err = self._emit_lines(self._err + bytes(self._proc.readAllStandardError()), self.error_line)

    @staticmethod
    def _emit_lines(buffer: bytes, signal) -> bytes:
        *lines, rest = buffer.replace(b"\r\n", b"\n").replace(b"\r", b"\n").split(b"\n")
        for raw in lines:
            text = raw.decode("utf-8", errors="replace").strip()
            if text:
                signal.emit(text)
        return rest

    def _flush(self) -> None:
        for buf, signal in ((self._out, self.line), (self._err, self.error_line)):
            text = buf.decode("utf-8", errors="replace").strip()
            if text:
                signal.emit(text)
        self._out = self._err = b""

    def _on_finished(self, code: int, status: QProcess.ExitStatus) -> None:
        if self._done:
            return
        self._done = True
        self._read_out()
        self._read_err()
        self._flush()
        self.finished.emit(code if status == QProcess.ExitStatus.NormalExit else -1)

    def _on_error(self, error: QProcess.ProcessError) -> None:
        if error == QProcess.ProcessError.FailedToStart and not self._done:
            self._done = True
            self.error_line.emit(f"ERROR: não foi possível iniciar {self._proc.program()}")
            self.finished.emit(-1)
