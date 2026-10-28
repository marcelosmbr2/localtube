"""Comportamento da versão empacotada (tools.FROZEN): ffmpeg embutido e yt-dlp atualizado."""

import hashlib

import pytest

from localtube.core import tools


@pytest.fixture
def frozen(tmp_path, monkeypatch):
    app_dir = tmp_path / "LocalTube"
    (app_dir / "ffmpeg").mkdir(parents=True)
    monkeypatch.setattr(tools, "FROZEN", True)
    monkeypatch.setattr(tools, "APP_DIR", app_dir)
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "local"))
    return app_dir


def test_bundled_ffmpeg_comes_before_path(frozen):
    bundled = frozen / "ffmpeg" / "ffmpeg.exe"
    bundled.write_bytes(b"")
    assert tools.find_tool("ffmpeg") == str(bundled)


def test_configured_ffmpeg_still_wins(frozen, tmp_path):
    (frozen / "ffmpeg" / "ffmpeg.exe").write_bytes(b"")
    custom = tmp_path / "custom" / "ffmpeg.exe"
    custom.parent.mkdir()
    custom.write_bytes(b"")
    assert tools.find_tool("ffmpeg", str(custom.parent)) == str(custom)


def test_ytdlp_runs_through_helper_when_frozen(frozen):
    assert tools.ytdlp_command() == [str(frozen / tools.YTDLP_HELPER)]


def test_newest_downloaded_wheel_overrides_bundled(frozen, monkeypatch):
    monkeypatch.setattr(tools, "bundled_ytdlp_version", lambda: "2026.10.26")
    folder = tools.ytdlp_updates_dir()
    folder.mkdir(parents=True)
    assert tools.updated_ytdlp_wheel() is None

    (folder / "yt_dlp-2026.9.1-py3-none-any.whl").write_bytes(b"")
    assert tools.updated_ytdlp_wheel() is None  # mais velho que o embutido
    assert tools.ytdlp_version() == "2026.10.26"

    (folder / "yt_dlp-2026.11.2-py3-none-any.whl").write_bytes(b"")
    (folder / "yt_dlp-2026.11.10-py3-none-any.whl").write_bytes(b"")
    assert tools.updated_ytdlp_wheel().name == "yt_dlp-2026.11.10-py3-none-any.whl"
    assert tools.ytdlp_version() == "2026.11.10"


def test_install_wheel_checks_hash_and_replaces_older(frozen):
    data = b"wheel"
    digest = hashlib.sha256(data).hexdigest()
    folder = tools.ytdlp_updates_dir()

    assert not tools.install_ytdlp_wheel(data, "yt_dlp-2026.11.2-py3-none-any.whl", "0" * 64)
    assert not folder.exists()
    assert not tools.install_ytdlp_wheel(data, "../yt_dlp-2026.11.2-py3-none-any.whl", digest)

    assert tools.install_ytdlp_wheel(data, "yt_dlp-2026.11.2-py3-none-any.whl", digest)
    assert tools.install_ytdlp_wheel(data, "yt_dlp-2026.11.10-py3-none-any.whl", digest.upper())
    assert [p.name for p in folder.iterdir()] == ["yt_dlp-2026.11.10-py3-none-any.whl"]
    assert (folder / "yt_dlp-2026.11.10-py3-none-any.whl").read_bytes() == data
