"""Milestone 5: partial reports, report history, evidence cleanup, issue dispositions, disk errors, a horizontal video."""
import json
import shutil
import subprocess
import threading

import pytest
from fastapi import HTTPException

from crcontent import quality, rights

pytestmark = pytest.mark.skipif(not shutil.which("ffmpeg"), reason="needs ffmpeg")
BLACK = "color=black:s=180x320:r=30:d=2[b];testsrc2=s=180x320:r=30:d=2[t];[t][b]concat=n=2:v=1"


def make(path, video="testsrc2=s=180x320:r=30:d=4"):
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", video, "-f", "lavfi", "-i", "sine=f=440:d=4",
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", str(path)], check=True)
    return path


@pytest.fixture
def lib(tmp_path, monkeypatch):
    out = tmp_path / "output"
    (out / "v").mkdir(parents=True)
    (out / "v" / "meta.json").write_text(json.dumps({"kind": "video", "aspect": "9:16"}))
    for mod in (quality, rights):
        monkeypatch.setattr(mod, "OUTPUT_DIR", out)
    monkeypatch.setattr(quality, "frame_size", lambda aspect: (180, 320))
    jobs, lock = {}, threading.Lock()
    quality.bind(jobs, lock)

    def run():
        """One inspection, run in this thread (the API queues it)."""
        path, profile, expect, _ = quality._target("video", "v")
        jobs["j"] = {"id": "j", "status": "queued", "log": []}
        quality._run("j", path, profile, expect, ("video", "v"))
        return jobs["j"], quality.get_inspection("video", "v")["report"]

    return out / "v", run


def issue(rep, detector):
    return next(c for c in rep["checks"] if c["detector"] == detector and c["status"] == "warning")


def test_analyzer_crash_keeps_a_partial_report(tmp_path, monkeypatch):
    def broken(*a, **k):
        raise OSError("disk read error")
    monkeypatch.setattr(quality, "analyze", broken)
    rep = quality.inspect_file(make(tmp_path / "ok.mp4"), "short", {"width": 180, "height": 320, "fps": 30})
    st = {c["detector"]: c["status"] for c in rep["checks"]}
    assert rep["verdict"] == "incomplete" and "disk read error" in rep["error"]
    assert st["stream.video"] == "pass" and st["visual.black"] == "not_checked"  # what ran is kept


def test_horizontal_video_passes_its_own_profile(tmp_path):
    path = make(tmp_path / "wide.mp4", "testsrc2=s=320x180:r=30:d=4")
    rep = quality.inspect_file(path, "lyric", {"width": 320, "height": 180, "fps": 30})
    assert {c["status"] for c in rep["checks"] if c["detector"] == "format.resolution"} == {"pass"}


def test_history_and_evidence_cleanup(lib):
    folder, run = lib
    make(folder / "video.mp4", BLACK)
    _, first = run()
    assert list((folder / "quality").glob("video-*.jpg"))
    make(folder / "video.mp4")  # re-render: clean now
    _, second = run()
    assert not list((folder / "quality").glob("video-*.jpg"))  # the old run's frames are gone
    hist = quality.inspection_history("video", "v")["history"]
    assert len(hist) == 1 and hist[0]["created"] == first["created"]
    old = quality.inspection_history_entry("video", "v", hist[0]["id"])["report"]
    assert old["archived"] and old["outdated"] and not any("evidence" in c for c in old["checks"])
    with pytest.raises(HTTPException):
        quality.inspection_history_entry("video", "v", "../../x")


def test_history_is_capped(lib, monkeypatch):
    folder, run = lib
    monkeypatch.setattr(quality, "HISTORY", 2)
    make(folder / "video.mp4")
    for k in range(4):
        rp = quality._report_path(folder / "video.mp4")
        rp.parent.mkdir(exist_ok=True)
        rp.write_text(json.dumps({"created": f"2026-01-0{k + 1}T00:00:00", "checks": []}))
        quality.archive(rp)
    assert [h["created"][:10] for h in quality.inspection_history("video", "v")["history"]] == ["2026-01-04", "2026-01-03"]


def test_fixed_is_confirmed_only_by_a_later_check(lib, monkeypatch):
    folder, run = lib
    make(folder / "video.mp4", BLACK)
    _, rep = run()
    black = issue(rep, "visual.black")
    rep = quality.review_issue("video", "v", black["id"], quality.Review(disposition="fixed"))["report"]
    assert issue(rep, "visual.black")["disposition"] == "fixed"  # awaiting a re-check
    times = iter(["2099-01-01T00:00:00", "2099-01-02T00:00:00"])
    monkeypatch.setattr(quality, "datetime", type("D", (), {"now": staticmethod(lambda: type("T", (), {
        "isoformat": lambda self, timespec=None: next(times)})())}))
    _, rep = run()  # same file, issue still there
    again = issue(rep, "visual.black")
    assert again["disposition"] == "unreviewed" and again["reopened"]
    make(folder / "video.mp4")
    _, rep = run()  # fixed for real
    assert [r["id"] for r in rep["resolved"]] == [black["id"]]


def test_dismissed_carries_over_and_bad_input_is_refused(lib):
    folder, run = lib
    make(folder / "video.mp4", BLACK)
    _, rep = run()
    black = issue(rep, "visual.black")
    quality.review_issue("video", "v", black["id"], quality.Review(disposition="dismissed"))
    _, rep = run()
    assert issue(rep, "visual.black")["disposition"] == "dismissed"
    assert rep["verdict"] == "warning"  # dismissing never turns a report into a pass
    with pytest.raises(HTTPException) as e:
        quality.review_issue("video", "v", black["id"], quality.Review(disposition="gone"))
    assert e.value.status_code == 400
    with pytest.raises(HTTPException) as e:
        quality.review_issue("video", "v", "nope", quality.Review(disposition="reviewed"))
    assert e.value.status_code == 404


def test_unwritable_report_folder_gives_an_actionable_error(lib):
    folder, run = lib
    make(folder / "video.mp4")
    (folder / "quality").write_text("not a folder")
    job, _ = run()
    assert job["status"] == "error" and "disk full" in job["error"]
