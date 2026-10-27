import json

from localtube.core.downloads import DONE, DOWNLOADING, FAILED, PAUSED, QUEUED, DownloadQueue
from localtube.core.ytdlp import DownloadRequest


def make_queue(settings, fake_runner) -> DownloadQueue:
    return DownloadQueue(settings, lambda: r"C:\ffmpeg\ffmpeg.exe", runner_factory=fake_runner)


def request(title="T", size=1000) -> DownloadRequest:
    return DownloadRequest(url="https://example.com/v", title=title, kind="video", selector="1+2",
                           container="mp4", out_dir="out", size=size)


def progress(runner, **data) -> None:
    runner.line.emit("LTPROG " + json.dumps(data))


def test_concurrency_limit_and_scheduling(settings, fake_runner):
    settings.set("concurrency", 2)
    queue = make_queue(settings, fake_runner)
    jobs = [queue.add(request(f"v{i}")) for i in range(3)]
    assert [j.status for j in jobs] == [DOWNLOADING, DOWNLOADING, QUEUED]
    assert len(fake_runner.instances) == 2
    assert "--ffmpeg-location" in fake_runner.instances[0].args

    fake_runner.instances[0].finished.emit(0)
    assert jobs[0].status == DONE and jobs[0].percent == 100
    assert jobs[2].status == DOWNLOADING
    assert queue.counts() == {"all": 3, "active": 2, "done": 1, "failed": 0}


def test_progress_spans_video_and_audio_parts(settings, fake_runner):
    queue = make_queue(settings, fake_runner)
    job = queue.add(request(size=1000))
    runner = fake_runner.instances[0]
    progress(runner, status="downloading", downloaded_bytes=400, total_bytes=800, speed=100.0, eta=4)
    assert round(job.percent) == 40 and job.speed == 100.0
    progress(runner, status="finished", downloaded_bytes=800, total_bytes=800)
    progress(runner, status="downloading", downloaded_bytes=100, total_bytes=200, speed=50.0, eta=2)
    assert round(job.percent) == 90
    runner.line.emit(r"LTFILE out\T.mp4")
    runner.finished.emit(0)
    assert job.status == DONE and job.filepath == r"out\T.mp4"


def test_failure_keeps_yt_dlp_error(settings, fake_runner):
    queue = make_queue(settings, fake_runner)
    job = queue.add(request())
    runner = fake_runner.instances[0]
    runner.error_line.emit("ERROR: [generic] x: HTTP Error 403: Forbidden")
    runner.finished.emit(1)
    assert job.status == FAILED and job.error == "HTTP Error 403: Forbidden"

    queue.retry(job.id)
    assert job.status == DOWNLOADING and job.error == ""
    assert len(fake_runner.instances) == 2


def test_pause_kills_without_failing_and_resume_restarts(settings, fake_runner):
    queue = make_queue(settings, fake_runner)
    job = queue.add(request())
    first = fake_runner.instances[0]
    progress(first, status="downloading", downloaded_bytes=300, total_bytes=1000, speed=10.0, eta=70)
    queue.pause(job.id)
    assert first.killed and job.status == PAUSED and round(job.percent) == 30

    queue.resume(job.id)
    assert job.status == DOWNLOADING and len(fake_runner.instances) == 2
    second = fake_runner.instances[1]
    progress(second, status="downloading", downloaded_bytes=200, total_bytes=1000, speed=10.0, eta=80)
    assert round(job.percent) == 30  # nunca regride ao retomar
    second.finished.emit(0)
    assert job.status == DONE


def test_pause_all_resume_all_and_clear_done(settings, fake_runner):
    queue = make_queue(settings, fake_runner)
    a, b = queue.add(request("a")), queue.add(request("b"))
    queue.pause_all()
    assert {a.status, b.status} == {PAUSED}
    assert not queue.any_running()
    queue.resume_all()
    assert {a.status, b.status} == {DOWNLOADING}
    fake_runner.instances[-1].finished.emit(0)
    fake_runner.instances[-2].finished.emit(0)
    queue.clear_done()
    assert queue.jobs == []


def test_bandwidth_is_split_between_slots(settings, fake_runner):
    settings.set("bandwidth_limit", "6M")
    settings.set("concurrency", 3)
    make_queue(settings, fake_runner).add(request())
    args = fake_runner.instances[0].args
    assert args[args.index("--limit-rate") + 1] == "2000000"
