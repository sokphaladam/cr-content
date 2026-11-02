"""Final-render inspector on tiny ffmpeg-generated clips with known faults (made in tmp_path, ~1 s each to render)."""
import shutil
import subprocess
import threading

import pytest

from crcontent import quality

pytestmark = pytest.mark.skipif(not shutil.which("ffmpeg"), reason="needs ffmpeg")
SHORT = {"width": 180, "height": 320, "fps": 30}


def make(path, video="testsrc2=s=180x320:r=30:d=4", audio="sine=f=440:d=4", extra=()):
    cmd = ["ffmpeg", "-y", "-v", "error"]
    if video:
        cmd += ["-f", "lavfi", "-i", video]
    if audio:
        cmd += ["-f", "lavfi", "-i", audio]
    cmd += [*extra, "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", str(path)]
    subprocess.run(cmd, check=True)
    return path


def by(rep, detector):
    return [c for c in rep["checks"] if c["detector"] == detector]


def status(rep, detector):
    return {c["status"] for c in by(rep, detector)}


def test_clean_short_passes(tmp_path):
    rep = quality.inspect_file(make(tmp_path / "ok.mp4"), "short", SHORT)
    for d in ("file.exists", "stream.video", "stream.audio", "format.resolution", "format.fps", "decode.errors",
              "visual.black", "visual.freeze", "audio.silence", "sync.av_duration"):
        assert status(rep, d) == {"pass"}, d
    assert rep["verdict"] in ("pass", "warning")  # colour tag / loudness advice may warn
    assert rep["counts"]["fail"] == 0
    assert rep["counts"]["not_checked"] >= len(quality.NOT_YET)  # unimplemented checks are listed, not passed


def test_no_audio_fails(tmp_path):
    rep = quality.inspect_file(make(tmp_path / "mute.mp4", audio=None), "short", SHORT)
    assert status(rep, "stream.audio") == {"fail"} and rep["verdict"] == "fail"


def test_wrong_orientation_fails(tmp_path):
    rep = quality.inspect_file(make(tmp_path / "wide.mp4", video="testsrc2=s=320x180:r=30:d=4"), "short", SHORT)
    assert status(rep, "format.resolution") == {"fail"}


def test_black_section_found_with_timestamp_and_evidence(tmp_path):
    v = "color=black:s=180x320:r=30:d=2[b];testsrc2=s=180x320:r=30:d=2[t];[t][b]concat=n=2:v=1"
    rep = quality.inspect_file(make(tmp_path / "black.mp4", video=v), "short", SHORT)
    [issue] = by(rep, "visual.black")
    assert issue["status"] == "warning" and 1.8 <= issue["start"] <= 2.2
    assert (tmp_path / issue["evidence"]).is_file()
    assert by(rep, "visual.freeze")[0]["status"] == "pass"  # the black stretch isn't reported twice


def test_frozen_section_found(tmp_path):
    v = "testsrc2=s=180x320:r=30:d=1[a];color=gray:s=180x320:r=30:d=3[g];[a][g]concat=n=2:v=1"
    rep = quality.inspect_file(make(tmp_path / "frozen.mp4", video=v), "short", SHORT)
    [issue] = by(rep, "visual.freeze")
    assert issue["status"] == "warning" and issue["start"] == pytest.approx(1.0, abs=0.2)


def test_silence_and_early_ending(tmp_path):
    rep = quality.inspect_file(make(tmp_path / "quiet.mp4", audio="sine=f=440:d=1,apad=whole_dur=4"), "short", SHORT)
    [issue] = by(rep, "audio.silence")
    assert issue["status"] == "warning" and "before the end" in issue["title"]


def test_clipped_audio_warns(tmp_path):
    rep = quality.inspect_file(make(tmp_path / "loud.mp4", audio="sine=f=440:d=4,volume=12"), "short", SHORT)
    assert status(rep, "audio.peak") == {"warning"}


def test_truncated_file_fails(tmp_path):
    good = make(tmp_path / "ok.mp4").read_bytes()
    bad = tmp_path / "cut.mp4"
    bad.write_bytes(good[: len(good) // 2])
    rep = quality.inspect_file(bad, "short", SHORT)
    assert rep["verdict"] == "fail"


def test_missing_and_empty_files_fail(tmp_path):
    (tmp_path / "empty.mp4").write_bytes(b"")
    for name in ("none.mp4", "empty.mp4"):
        rep = quality.inspect_file(tmp_path / name, "short", SHORT)
        assert status(rep, "file.exists") == {"fail"}


def test_expected_duration_shortfall_warns(tmp_path):
    rep = quality.inspect_file(make(tmp_path / "ok.mp4"), "lyric", {**SHORT, "duration": 10})
    assert status(rep, "duration.length") == {"warning"}


def test_rerender_makes_report_outdated(tmp_path):
    path = make(tmp_path / "ok.mp4")
    rep = quality.inspect_file(path, "short", SHORT)
    assert not quality.outdated(rep, path)
    make(path, video="testsrc2=s=180x320:r=30:d=3", audio="sine=f=330:d=3")
    assert quality.outdated(rep, path)


def test_cancel_gives_partial_report_never_pass(tmp_path):
    stop = threading.Event()
    stop.set()
    rep = quality.inspect_file(make(tmp_path / "ok.mp4"), "short", SHORT, cancel=stop)
    assert rep["cancelled"] and rep["verdict"] == "incomplete"
    assert status(rep, "visual.black") == {"not_checked"}


def test_missing_ffmpeg_is_actionable(tmp_path, monkeypatch):
    monkeypatch.setattr(quality.shutil, "which", lambda _: None)
    with pytest.raises(RuntimeError, match="FFmpeg/FFprobe not found"):
        quality.inspect_file(tmp_path / "x.mp4", "short", SHORT)
