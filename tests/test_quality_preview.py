"""Preview inspector: Shorts scripts and Lyric Studio song folders with known faults."""
import json
import shutil
import subprocess

import pytest

from crcontent import quality_preview as qp
from crcontent.script import BRoll, Scene, TextOverlay, VideoScript


def script(*scenes, **kw):
    return VideoScript(title=kw.get("title", "T"), caption="c", hashtags=["#a"],
                       scenes=list(scenes) or [Scene(narration="Octopuses have three hearts.", visual_query="octopus")])


def by(rep, prefix):
    return [c for c in rep["checks"] if c["detector"].startswith(prefix)]


@pytest.fixture
def lib(tmp_path, monkeypatch):
    monkeypatch.setattr(qp, "ROOT", tmp_path)
    monkeypatch.setattr(qp, "ASSETS_DIR", tmp_path / "assets")
    (tmp_path / "uploads").mkdir()
    return tmp_path


def test_clean_script_has_no_failures(lib):
    rep = qp.inspect_short(script(), "en", "none", [4.0], False)
    assert rep["stage"] == "preview" and rep["counts"]["fail"] == 0
    assert all(c["stage"] == "preview" for c in rep["checks"])
    assert by(rep, "timing.total")[0]["status"] == "pass"


def test_unvoiced_scene_leaves_length_not_checked(lib):
    rep = qp.inspect_short(script(), "en", "none", [0], False)
    assert by(rep, "timing.total")[0]["status"] == "not_checked"


def test_missing_media_fails_and_points_at_scene(lib):
    s = Scene(narration="x", visual_query="q", media="uploads/gone.mp4")
    rep = qp.inspect_short(script(Scene(narration="a", visual_query="q"), s), "en", "none", [2, 2], False)
    [miss] = by(rep, "media.missing")
    assert miss["status"] == "fail" and miss["scene"] == 1


def test_media_outside_library_is_refused(lib):
    s = Scene(narration="x", visual_query="q", media="../../etc/hosts")
    rep = qp.inspect_short(script(s), "en", "none", [2], False)
    assert by(rep, "media.missing")[0]["status"] == "fail"


def test_overlay_off_frame_late_and_unsafe(lib):
    s = Scene(narration="x", visual_query="q", texts=[
        TextOverlay(text="A very long overlay line that cannot possibly fit", x=0.9, size="l"),
        TextOverlay(text="hi", y=0.95),
        TextOverlay(text="late", at=9)],
        broll=[BRoll(media="uploads/b.jpg", at=9)])
    (lib / "uploads" / "b.jpg").write_bytes(b"x")
    rep = qp.inspect_short(script(s), "en", "none", [3], False)
    assert by(rep, "captions.clip") and by(rep, "captions.safe") and by(rep, "captions.late") and by(rep, "media.broll_late")


def test_too_long_for_a_short_and_long_shot(lib):
    rep = qp.inspect_short(script(), "en", "none", [200], False)
    assert by(rep, "timing.total")[0]["status"] == "fail" and by(rep, "pacing.long")


def test_missing_music_and_warmup_opener(lib):
    rep = qp.inspect_short(script(Scene(narration="Hey guys, today...", visual_query="q")), "en", "gone.mp3", [3], False)
    assert by(rep, "audio.music")[0]["status"] == "fail"
    assert by(rep, "story.hook")[0]["status"] == "warning"


def test_fingerprint_changes_with_the_project(lib):
    a = qp.inspect_short(script(), "en", "none", [3], False)["fingerprint"]
    b = qp.inspect_short(script(title="Other"), "en", "none", [3], False)["fingerprint"]
    assert a != b


@pytest.mark.skipif(not shutil.which("ffmpeg"), reason="needs ffmpeg")
def test_full_check_probes_media(lib):
    clip = lib / "uploads" / "small.mp4"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", "testsrc2=s=320x240:d=1", str(clip)], check=True)
    s = Scene(narration="x", visual_query="q", media="uploads/small.mp4", media_start=5)
    quick = qp.inspect_short(script(s), "en", "none", [2], False)
    assert not by(quick, "media.lowres")
    full = qp.inspect_short(script(s), "en", "none", [2], True)
    assert by(full, "media.lowres") and by(full, "media.start")[0]["status"] == "fail"


# ---------- lyric ----------

@pytest.fixture
def song(tmp_path):
    folder = tmp_path / "my-song"
    folder.mkdir()
    (folder / "song.json").write_text(json.dumps({"title": "S", "plan": "pro", "generated_on": "2026-01-01",
                                                  "genre": "nu-disco"}), encoding="utf-8")
    return folder


def write_lrc(folder, rows):
    (folder / "lyrics.lrc").write_text("".join(f"[{int(t // 60):02d}:{t % 60:05.2f}]{x}\n" for t, x in rows), encoding="utf-8")


def test_song_without_analysis_fails(tmp_path):
    folder = tmp_path / "s"
    folder.mkdir()
    rep = qp.inspect_song(folder, False)
    assert {c["detector"] for c in rep["checks"] if c["status"] == "fail"} >= {"audio.song", "lyrics.analyzed"}


def test_lyric_timing_faults(song):
    write_lrc(song, [(1, "first line"), (5, "second"), (3, "out of order"), (3.3, "quick"), (3.5, "dup"), (3.6, "dup"),
                     (30, "x" * 60)])
    rep = qp.inspect_song(song, False)
    assert by(rep, "lyrics.order")[0]["status"] == "fail"
    assert by(rep, "lyrics.flash") and by(rep, "lyrics.duplicate") and by(rep, "lyrics.gap") and by(rep, "lyrics.long")
    # word-level sync is never claimed
    assert any(c["status"] == "not_checked" and "sync" in c["title"].lower() for c in rep["checks"])


def test_song_report_outdated_after_lyric_edit(song, monkeypatch):
    from crcontent import lyricvideo

    monkeypatch.setattr(lyricvideo, "SONGS_DIR", song.parent)
    write_lrc(song, [(1, "a line"), (4, "another")])
    qp.preview_song(song.name)
    assert qp.get_preview_song(song.name)["report"]["outdated"] is False
    write_lrc(song, [(1, "a line"), (4, "changed")])
    assert qp.get_preview_song(song.name)["report"]["outdated"] is True
