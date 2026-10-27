# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

LocalTube: a Python desktop app built with PySide6 (Qt Widgets). Packaged with `pyproject.toml` (setuptools, `src/` layout); requires Python >=3.11, and the local `.venv` uses Python 3.14 with PySide6 6.12. UI text is in Portuguese (pt-BR).

The visual reference for the UI lives outside this folder, in `../mockup/LocalTube.dc.html` (HTML mockup + `support.js`). Consult it when building screens.

## Commands (Windows / PowerShell)

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -e .   # editable install; exposes the `localtube` script
.venv\Scripts\python.exe -m localtube          # run the app
```

There is no test suite, linter or formatter configured yet.

To check that the UI starts without opening a window (e.g. from a non-interactive shell), use the offscreen platform and quit from a timer created **after** the `QApplication` exists — a `QTimer.singleShot` scheduled before the app is constructed never fires and the process hangs:

```powershell
$env:QT_QPA_PLATFORM = 'offscreen'; .venv\Scripts\python.exe -c "import sys; from PySide6.QtCore import QTimer; from PySide6.QtWidgets import QApplication; from localtube.main_window import MainWindow; app = QApplication(sys.argv); w = MainWindow(); w.show(); QTimer.singleShot(500, app.quit); print(app.exec())"
```

## Architecture

- `localtube/app.py` — `main()` entry point: creates the `QApplication`, sets app name/version, shows `MainWindow`, returns the exit code. Used by both `python -m localtube` (`__main__.py`) and the `localtube` console script.
- `localtube/main_window.py` — `MainWindow(QMainWindow)`: central widget, menu bar (Arquivo/Ajuda) and status bar. New screens/widgets should be composed into this window.
- The version is defined in two places: `pyproject.toml` and `localtube/__init__.py` (`__version__`); the About dialog also hardcodes it. Keep them in sync.
