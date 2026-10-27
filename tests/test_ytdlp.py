from localtube.core import ytdlp
from localtube.core.ytdlp import DownloadRequest


def request(**kw) -> DownloadRequest:
    base = dict(url="https://www.youtube.com/watch?v=x", title="T", kind="video", selector="299+140",
                container="mp4", out_dir=r"C:\Videos\LocalTube", video_codec="H.264")
    return DownloadRequest(**{**base, **kw})


def test_video_args_merge_and_embed():
    args = ytdlp.format_args(request())
    assert args[:2] == ["-f", "299+140"]
    assert "--merge-output-format" in args and "--embed-thumbnail" in args and "--embed-metadata" in args


def test_webm_with_h264_is_recoded():
    args = ytdlp.format_args(request(container="webm"))
    assert args[args.index("--recode-video") + 1] == "webm"
    assert "--embed-thumbnail" not in args  # webm não aceita miniatura embutida


def test_audio_args_and_options():
    args = ytdlp.format_args(request(kind="audio", selector="ba/b", container="mp3", audio_quality="320K",
                                     subtitles=["en"], split_chapters=True, section=(10, 70)))
    assert args[args.index("--audio-format") + 1] == "mp3"
    assert args[args.index("--audio-quality") + 1] == "320K"
    assert args[args.index("--sub-langs") + 1] == "en"
    assert "--split-chapters" in args
    assert args[args.index("--download-sections") + 1] == "*10-70"


def test_build_args_adds_progress_and_tools():
    args = ytdlp.build_args(request(), ffmpeg=r"C:\ffmpeg\ffmpeg.exe", proxy="socks5://p:1080", rate_limit="500000")
    assert args[-2:] == ["--", "https://www.youtube.com/watch?v=x"]
    assert "download:LTPROG %(progress)j" in args
    assert args[args.index("--ffmpeg-location") + 1] == r"C:\ffmpeg\ffmpeg.exe"
    assert args[args.index("--limit-rate") + 1] == "500000"
    assert "--continue" in args


def test_command_string_is_pasteable():
    cmd = ytdlp.command_string(request(template="%(title)s.%(ext)s"))
    assert cmd.startswith("yt-dlp -f 299+140 ")
    assert cmd.endswith("https://www.youtube.com/watch?v=x")
    assert "LTPROG" not in cmd


def test_parse_lines():
    kind, value = ytdlp.parse_line('LTPROG {"status": "downloading", "downloaded_bytes": 10}')
    assert kind == "progress" and value["downloaded_bytes"] == 10
    assert ytdlp.parse_line(r"LTFILE C:\a\b.mp4") == ("file", r"C:\a\b.mp4")
    assert ytdlp.parse_line("[youtube] qualquer coisa") is None
    assert ytdlp.error_message("ERROR: [youtube] abc: Video unavailable") == "Video unavailable"
    assert ytdlp.error_message("WARNING: x") is None


def test_rate_per_job_and_domain():
    assert ytdlp.rate_per_job("5M", 2) == "2500000"
    assert ytdlp.rate_per_job("", 3) == ""
    assert ytdlp.domain("https://www.youtube.com/watch?v=x") == "youtube.com"
