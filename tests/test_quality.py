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


# ---------- Milestone 3: sampled-frame visual checks and audio checks ----------

def test_clean_short_passes_visual_and_audio_checks(tmp_path):
    rep = quality.inspect_file(make(tmp_path / "ok.mp4"), "short", SHORT)
    for d in ("visual.sharpness", "visual.exposure", "visual.colour", "visual.border", "visual.repeat", "audio.jumps"):
        assert status(rep, d) == {"pass"}, d
    assert status(rep, "audio.balance") == {"not_checked"}  # mono sine: nothing to balance, and it says so


@pytest.mark.skipif(not quality.has_filter("blurdetect"), reason="needs ffmpeg 5.1+")
def test_blurry_section_warns_with_timestamp(tmp_path):
    v = "testsrc2=s=180x320:r=30:d=2[a];testsrc2=s=180x320:r=30:d=2,boxblur=12[b];[a][b]concat=n=2:v=1"
    [issue] = by(quality.inspect_file(make(tmp_path / "soft.mp4", video=v), "short", SHORT), "visual.sharpness")
    assert issue["status"] == "warning" and issue["start"] == pytest.approx(2.0, abs=0.6) and issue["evidence"]


def test_sharpness_not_checked_without_blurdetect(tmp_path, monkeypatch):
    path = make(tmp_path / "ok.mp4")
    monkeypatch.setattr(quality, "has_filter", lambda name: False)
    assert status(quality.inspect_file(path, "short", SHORT), "visual.sharpness") == {"not_checked"}


def test_dark_picture_warns(tmp_path):
    rep = quality.inspect_file(make(tmp_path / "dark.mp4", video="testsrc2=s=180x320:r=30:d=4,format=yuv420p,lutyuv=y='val*0.22'"), "short", SHORT)
    assert status(rep, "visual.exposure") == {"warning"}
    assert status(rep, "visual.black") == {"pass"}  # dark is not black


def test_letterbox_warns(tmp_path):
    rep = quality.inspect_file(make(tmp_path / "bars.mp4", video="testsrc2=s=180x200:r=30:d=4,pad=180:320:0:60"), "short", SHORT)
    [issue] = by(rep, "visual.border")
    assert issue["status"] == "warning" and "top and bottom" in issue["title"]


def test_colour_cast_warns(tmp_path):
    v = "testsrc2=s=180x320:r=30:d=4,colorchannelmixer=rr=0.2:gg=0.2:bb=1"
    assert status(quality.inspect_file(make(tmp_path / "blue.mp4", video=v), "short", SHORT), "visual.colour") == {"warning"}


def test_repeated_shot_found_for_shorts_not_lyric(tmp_path):
    v = ("smptebars=s=180x320:r=30:d=1[a];rgbtestsrc=s=180x320:r=30:d=1[b];testsrc2=s=180x320:r=30:d=1[c];"
         "smptebars=s=180x320:r=30:d=1[d];[a][b][c][d]concat=n=4:v=1")
    path = make(tmp_path / "rep.mp4", video=v)
    [issue] = by(quality.inspect_file(path, "short", SHORT), "visual.repeat")
    assert issue["status"] == "warning" and issue["start"] == pytest.approx(3.0, abs=0.6)
    assert status(quality.inspect_file(path, "lyric", SHORT), "visual.repeat") == {"not_checked"}


def test_stereo_imbalance_and_phase(tmp_path):
    lopsided = make(tmp_path / "lr.mp4", audio="sine=f=440:d=4,pan=stereo|c0=c0|c1=0.3*c0")
    rep = quality.inspect_file(lopsided, "short", SHORT)
    assert status(rep, "audio.balance") == {"warning"} and status(rep, "audio.mono") == {"pass"}
    inverted = make(tmp_path / "phase.mp4", audio="sine=f=440:d=4,pan=stereo|c0=c0|c1=-1*c0")
    rep = quality.inspect_file(inverted, "short", SHORT)
    assert status(rep, "audio.balance") == {"pass"} and status(rep, "audio.mono") == {"warning"}


def test_sudden_loudness_jump_warns(tmp_path):
    a = "sine=f=440:d=4,volume='if(lt(t,2),0.03,0.9)':eval=frame"
    [issue] = by(quality.inspect_file(make(tmp_path / "jump.mp4", audio=a), "short", SHORT), "audio.jumps")
    assert issue["status"] == "warning" and "jump" in issue["title"] and 1 <= issue["start"] <= 2


def test_pauses_and_the_ending_are_not_loudness_jumps(tmp_path):
    # loud, a pause (very quiet), loud again at the same level, then the ending fades to near silence
    a = "sine=f=440:d=7,volume='if(between(t,2,3),0.01,if(gt(t,5.5),0.005,0.5))':eval=frame"
    assert status(quality.inspect_file(make(tmp_path / "pause.mp4", audio=a), "short", SHORT), "audio.jumps") == {"pass"}


def test_stretches_and_repeats_helpers():
    assert quality.stretches([0, 0.5, 1.0, 3.0], 0.5, 1.0) == [(0, 1.5)]
    a, b = bytes(range(0, 256)), bytes(255 - x for x in range(256))
    sigs = [(0, a), (0.5, a), (1, b), (1.5, b), (2, a)]
    assert quality.repeated_shots(sigs) == [(2, 0)]
    assert quality.repeated_shots([(0, a), (0.5, a), (1, a)]) == []  # one long shot is not a repeat
