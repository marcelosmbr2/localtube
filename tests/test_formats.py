from localtube.core.formats import build_options, default_selection, natural_audio_container


def test_video_rows_pair_best_audio_and_keep_two_codecs_per_height(info):
    video, _audio, total = build_options(info)
    assert total == len(info["formats"])
    rows = [(r.quality, r.codec, r.selector) for r in video]
    assert rows == [
        ("2160p", "VP9 + Opus", "315+251"),
        ("1080p", "H.264 + AAC", "299+140"),
        ("1080p", "VP9 + Opus", "303+251"),
        ("480p", "H.264 + AAC", "135+140"),  # HTTPS vence o m3u8 da mesma altura
        ("480p", "VP9 + Opus", "244+251"),
        ("360p", "H.264 + AAC", "134+140"),
    ]
    assert video[1].size == 257_619_653 + 10_271_496


def test_recommended_follows_preferred_quality(info):
    video, _, _ = build_options(info, "1080p · MP4")
    assert default_selection(video).selector == "299+140"
    assert default_selection(video).badge == "Recomendado"
    video, _, _ = build_options(info, "720p · MP4")
    assert default_selection(video).quality == "480p"
    assert default_selection(video).codec.startswith("H.264")


def test_audio_rows_skip_drc_and_add_reencoded_mp3(info):
    _, audio, _ = build_options(info)
    assert [(r.quality, r.codec, r.container) for r in audio] == [
        ("129 kbps", "AAC", "m4a"),
        ("129 kbps", "Opus", "webm"),
        ("49 kbps", "AAC", "m4a"),
        ("320 kbps", "MP3 · recodificado", "mp3"),
        ("192 kbps", "MP3 · recodificado", "mp3"),
    ]
    assert audio[0].badge == "Melhor"
    assert audio[0].detail == "44,1 kHz"
    assert audio[3].audio_quality == "320K"
    assert natural_audio_container(audio[1]) == "opus"
    assert natural_audio_container(audio[0]) == "m4a"


def test_no_formats():
    video, audio, total = build_options({"formats": []})
    assert (video, audio, total) == ([], [], 0)
