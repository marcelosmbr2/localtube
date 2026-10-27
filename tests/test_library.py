from localtube.core.library import scan


def test_scan_lists_media_and_skips_partial_files(tmp_path):
    (tmp_path / "video.mp4").write_bytes(b"x" * 10)
    (tmp_path / "song.MP3").write_bytes(b"x")
    (tmp_path / "video.f135.mp4.part").write_bytes(b"x")
    (tmp_path / "notes.txt").write_text("x")
    sub = tmp_path / "Canal"
    sub.mkdir()
    (sub / "aula.mkv").write_bytes(b"x")

    items = sorted(scan(str(tmp_path)), key=lambda i: i.name)
    assert [(i.name, i.ext, i.kind) for i in items] == [
        ("aula", "MKV", "video"),
        ("song", "MP3", "audio"),
        ("video", "MP4", "video"),
    ]
    assert items[2].size == 10


def test_scan_missing_folder(tmp_path):
    assert scan(str(tmp_path / "nao-existe")) == []
