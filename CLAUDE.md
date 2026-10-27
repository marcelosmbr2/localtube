# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

LocalTube: a Python desktop app built with PySide6 (Qt Widgets) that inspects links and downloads media with **yt-dlp**, converts local files with **ffmpeg**, and shows a download queue and a library of the download folder. Packaged with `pyproject.toml` (setuptools, `src/` layout); requires Python >=3.11, and the local `.venv` uses Python 3.14 with PySide6 6.12. UI text is in Portuguese (pt-BR), with decimal commas (`core/formatting.py`).

The visual reference for the UI is `mockup/LocalTube.dc.html` (HTML mockup + `support.js`): its markup holds the exact colors/sizes and its `<script>` block holds the screen behavior. Consult it when building screens.

## Commands (Windows / PowerShell)

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -e ".[dev]"   # app + pytest/pytest-qt; exposes the `localtube` script
.venv\Scripts\python.exe -m localtube                 # run the app
.venv\Scripts\python.exe -m pytest                    # all tests (offscreen, ~2 s)
.venv\Scripts\python.exe -m pytest tests/test_downloads.py::test_pause_kills_without_failing_and_resume_restarts
```

ffmpeg/ffprobe are external (`winget install --id Gyan.FFmpeg -e`). `core/tools.find_tool` looks at the configured path, then PATH, then the winget `Links`/`Packages` folders, so a fresh winget install is found without restarting the shell. yt-dlp is a pip dependency and runs as `sys.executable -m yt_dlp`.

To check the UI without showing a window, use `QT_QPA_PLATFORM=offscreen`, create the `QApplication` first, then the window, then a `QTimer.singleShot(…, app.quit)` — a timer created before the app exists never fires and the process hangs. `window.grab().save("x.png")` gives a screenshot to compare against the mockup. Pass `AppSettings(QSettings(path, IniFormat))` to avoid touching the real settings in `%APPDATA%\LocalTube`.

## Architecture

- `app.py` loads the bundled fonts, applies the global QSS (`theme.build_stylesheet()`), builds `Services` and `ui/main_window.MainWindow`.
- `services.Services` owns the shared state passed to every page: `settings` (`AppSettings` over QSettings, emits `changed(key)`), `downloads` (`DownloadQueue`), `conversions` (`ConvertQueue`), `probes` (`ProbeService`), and the detected ffmpeg (`tools_changed`). Queues live here, not in pages, so the sidebar badge, palette and notifications read the same state.
- `core/` has no widgets. External tools run through `core/process.ProcessRunner` (QProcess → UTF-8 lines on `line`/`error_line`, then `finished(code)`); queues accept a `runner_factory` so tests inject `tests/conftest.FakeRunner`.
  - yt-dlp: `ytdlp.build_args` adds `--progress-template "download:LTPROG %(progress)j"` and `--print "after_move:LTFILE %(filepath)s"`; `parse_line` reads them. `format_args` is the user-visible part shared with "Copiar comando".
  - Pause = kill the process; resume = start again with `--continue` (reuses the `.part`). `DownloadQueue._on_finished` ignores runners that are no longer registered, which is how a kill is told apart from a failure. Progress spans the separate video and audio downloads via `done_bytes` and never goes backwards.
  - `formats.build_options` turns the `-J` info dict into the Vídeo/Somente áudio rows (≤2 codecs per height, HTTPS preferred over m3u8, `-drc`/storyboards dropped, "Recomendado" from the preferred-quality setting).
  - `convert.FIELDS` is the per-target preset table from the mockup; `convert.build_args` maps choices to ffmpeg args and uses `-progress pipe:1`. Outputs go next to the source and are never overwritten (`output_path` also reserves names for parallel jobs).
  - `media.ProbeService` runs ffprobe in a thread pool with a cache keyed by path/mtime/size and emits `probed` back on the UI thread; the library model and the convert queue listen to it.
- `ui/pages/*` are the five screens; `ui/widgets/common.py` holds the building blocks (segmented control, toggle, card with divider rows, elided label, flow layout); `ui/widgets/overlays.py` has the toast and the command palette (Ctrl+K). Pages talk back to the window through `host.go()`, `host.toast()`, `host.copy_text()`, `host.notify()`.

## Qt gotchas found here

- Colors/sizes come from `theme.py` tokens. Do not put `font-family`/`font-size` on the global `QWidget` QSS rule: it overrides `setFont()` (that broke the monospace labels). Fonts are set per widget via `theme.ui_font`/`theme.mono_font`.
- Remove widgets with `common.discard()` (hide + unparent + deleteLater). `deleteLater()` alone leaves them painted until the event loop runs again, which showed old controls overlapping new ones.
- Paths over 260 chars fail `Path.stat()` on Windows; use `media.file_stat()`, which retries with the `\\?\` prefix.
- Dynamic properties used in QSS selectors need `common.set_prop()` (it re-polishes).

The version lives in `pyproject.toml` and `localtube/__init__.py` (`__version__`, shown in the sidebar); keep them in sync.
