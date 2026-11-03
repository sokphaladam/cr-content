"""Stopping a job: POST /api/jobs/<id>/cancel, the job's log raising JobStopped, and the queue ending it as stopped."""
import sys
import threading

import pytest
from fastapi.testclient import TestClient

from crcontent import render, web


def _job(kind="long_video", status="running"):
    job_id = f"t{threading.get_ident()}{len(web.jobs)}"
    web.jobs[job_id] = {"id": job_id, "kind": kind, "status": status, "step": 0, "log": [], "title": "t"}
    return job_id


def test_cancel_stops_a_running_job_at_its_next_log_line():
    job_id = _job()
    started, release = threading.Event(), threading.Event()

    def runner(jid):
        log = web._job_logger(web.jobs[jid], 2)
        log("[1/2] working")
        started.set()
        release.wait(5)
        try:
            log("[2/2] next step")  # raises: the job was stopped
        except Exception as e:  # how runners end: _fail
            web._fail(web.jobs[jid], e)
            return
        web.jobs[jid]["status"] = "done"

    fut = web.renderer.submit(runner, job_id)
    assert started.wait(5)
    r = TestClient(web.app).post(f"/api/jobs/{job_id}/cancel")
    assert r.status_code == 200
    release.set()
    fut.result(5)
    job = web.jobs[job_id]
    assert job["status"] == "error" and job["cancelled"] and job["error"] == web.STOPPED
    assert job["log"] == ["[1/2] working"]


def test_a_job_stopped_while_queued_never_starts_and_an_escaping_stop_still_ends_it():
    queued = _job(status="queued")
    web.jobs[queued]["cancel"] = True
    ran = []
    web.renderer.submit(lambda jid: ran.append(jid), queued).result(5)
    assert not ran and web.jobs[queued]["status"] == "error" and web.jobs[queued]["cancelled"]

    escaping = _job()
    web.jobs[escaping]["cancel"] = True
    web.renderer.submit(lambda jid: web._job_logger(web.jobs[jid], 1)("x"), escaping).result(5)  # no try/except
    assert web.jobs[escaping]["status"] == "error" and web.jobs[escaping]["error"] == web.STOPPED


def test_cancel_refuses_unknown_and_unstoppable_jobs():
    client = TestClient(web.app)
    assert client.post("/api/jobs/nope/cancel").status_code == 404
    assert client.post(f"/api/jobs/{_job(kind='publish')}/cancel").status_code == 400
    done = _job(status="done")
    assert client.post(f"/api/jobs/{done}/cancel").json()["status"] == "done"
    assert "cancel" not in web.jobs[done]


def test_run_progress_kills_ffmpeg_when_progress_raises(monkeypatch):
    # a stand-in for ffmpeg that keeps writing progress for a minute
    script = "import time\nfor i in range(600):\n print('out_time_us=%d' % (i * 100000), flush=True); time.sleep(0.1)"
    killed = []
    real = render.subprocess.Popen

    def popen(cmd, **kw):
        proc = real([sys.executable, "-c", script], **kw)
        orig = proc.kill
        proc.kill = lambda: (killed.append(True), orig())
        return proc

    monkeypatch.setattr(render.subprocess, "Popen", popen)

    def progress(_):
        raise web.JobStopped("stop")

    with pytest.raises(web.JobStopped):
        render.run_progress(["ffmpeg"], 60, progress)
    assert killed


def test_a_stalled_ffmpeg_is_killed_and_tried_once_more(tmp_path):
    marker = tmp_path / "ran-once"
    # freezes on the first run only, like FFmpeg 8.1's rare stall before closing a scene
    script = (f"import pathlib, sys, time\np = pathlib.Path(r'{marker}')\n"
              "if not p.exists():\n    p.touch(); time.sleep(60)\n")
    t = __import__("time").time()
    render.run([sys.executable, "-c", script, str(tmp_path / "scene.mp4")], timeout=2)
    assert marker.exists() and __import__("time").time() - t < 20


def test_ffmpeg_that_stalls_twice_fails_the_render(tmp_path):
    with pytest.raises(RuntimeError, match="stalled twice"):
        render.run([sys.executable, "-c", "import time; time.sleep(60)", str(tmp_path / "scene.mp4")], timeout=1)
