from localtube.core import convert
from localtube.core.media import describe, parse_probe


def test_every_target_has_defaults():
    for target in convert.VIDEO_TARGETS + convert.AUDIO_TARGETS:
        args = convert.build_args("in.mov", f"out.{target}", target, convert.default_choices(target))
        assert args[-1] == f"out.{target}"
        assert "-progress" in args


def test_mp4_args():
    args = convert.build_args("in.mov", "out.mp4", "mp4", {"height": "720", "fps": "30"}, crf=20)
    assert args[args.index("-c:v") + 1] == "libx264"
    assert args[args.index("-crf") + 1] == "20"
    assert args[args.index("-vf") + 1] == "scale=-2:720,fps=30"
    assert args[args.index("-b:a") + 1] == "192k"
    assert ["-map", "0:V:0"] == args[args.index("-map"):args.index("-map") + 2]


def test_gif_uses_labeled_palette_graph():
    args = convert.build_args("in.mp4", "out.gif", "gif", {})
    graph = args[args.index("-filter_complex") + 1]
    assert graph.startswith("[0:V:0]fps=15,scale=640:-1") and graph.endswith("[gif]")
    assert args[args.index("-map") + 1] == "[gif]"


def test_audio_targets():
    mp3 = convert.build_args("in.mp4", "o.mp3", "mp3", {"bitrate": "320k", "ac": "1"})
    assert mp3[mp3.index("-c:a") + 1] == "libmp3lame" and "-vn" in mp3
    assert mp3[mp3.index("-ac") + 1] == "1"
    flac = convert.build_args("in.wav", "o.flac", "flac", {})
    assert flac[flac.index("-compression_level") + 1] == "5"


def test_uses_crf():
    assert convert.uses_crf("mp4", {"vcodec": "libx264"})
    assert not convert.uses_crf("mov", {"vcodec": "prores"})
    assert not convert.uses_crf("mp3", {})


def test_output_path_never_overwrites(tmp_path):
    src = tmp_path / "clip.mp4"
    src.write_bytes(b"x")
    assert convert.output_path(str(src), "mp3") == str(tmp_path / "clip.mp3")
    assert convert.output_path(str(src), "mp4") == str(tmp_path / "clip (convertido).mp4")
    reserved = {str(tmp_path / "clip.mp3")}
    assert convert.output_path(str(src), "mp3", reserved) == str(tmp_path / "clip (convertido).mp3")
    (tmp_path / "clip (convertido).mp4").write_bytes(b"x")
    assert convert.output_path(str(src), "mp4") == str(tmp_path / "clip (convertido) (2).mp4")


def test_parse_progress():
    assert convert.parse_progress("out_time_us=2500000") == 2.5
    assert convert.parse_progress("progress=end") == "end"
    assert convert.parse_progress("frame=10") is None


def test_probe_parsing_ignores_attached_pictures():
    data = {
        "format": {"duration": "634.6", "bit_rate": "500000"},
        "streams": [
            {"codec_type": "video", "width": 1280, "height": 720, "disposition": {"attached_pic": 1}},
            {"codec_type": "audio", "sample_rate": "44100", "bit_rate": "192000"},
        ],
    }
    info = parse_probe(data)
    assert info.kind == "audio" and info.sample_rate == 44100 and info.bit_rate == 192000
    assert describe("song.m4a", info, 6_200_000) == "M4A · 44,1 kHz · 10:35 · 6,2 MB"
