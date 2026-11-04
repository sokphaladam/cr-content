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



@pytest.mark.skipif(not shutil.which("ffmpeg"), reason="needs ffmpeg")
def test_full_check_samples_footage_quality(lib):
    def clip(name, src):
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", f"{src}:s=1280x720:d=3", str(lib / "uploads" / name)],
                       check=True)
    clip("sharp.mp4", "testsrc2=r=25")
    clip("dark.mp4", "color=c=0x080808:r=25")
    scenes = [Scene(narration="x", visual_query="q", media="uploads/sharp.mp4"),
              Scene(narration="y", visual_query="q", media="uploads/dark.mp4")]
    quick = qp.inspect_short(script(*scenes), "en", "none", [2, 2], False)
    assert by(quick, "visual.footage")[0]["status"] == "not_checked"
    full = qp.inspect_short(script(*scenes), "en", "none", [2, 2], True)
    dark = by(full, "visual.exposure")
    assert len(dark) == 1 and dark[0]["scene"] == 1 and "dark" in dark[0]["title"]
    assert not by(full, "visual.sharpness.0") and not by(full, "visual.colour")
    assert not by(full, "later.visual")  # no longer listed as "not part of this inspector"


@pytest.mark.skipif(not shutil.which("ffmpeg"), reason="needs ffmpeg")
def test_full_check_measures_the_music(lib):
    music = lib / "assets" / "music"
    music.mkdir(parents=True)

    def track(name, expr):
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", f"aevalsrc='{expr}':d=20", str(music / name)],
                       check=True)
    track("steady.wav", "0.2*sin(440*2*PI*t)")
    track("quiet.wav", "0.002*sin(440*2*PI*t)")  # about -57 LUFS
    track("swings.wav", "if(lt(mod(t,10),5),0.5,0.06)*sin(440*2*PI*t)")  # 5 s loud, 5 s 18 dB softer
    by_track = {n: qp.inspect_short(script(), "en", n, [3], True) for n in ("steady.wav", "quiet.wav", "swings.wav")}
    assert by(by_track["steady.wav"], "audio.music_level")[0]["status"] == "pass"
    assert by(by_track["quiet.wav"], "audio.music_quiet")
    assert by(by_track["swings.wav"], "audio.music_range")
    quick = qp.inspect_short(script(), "en", "steady.wav", [3], False)
    assert by(quick, "audio.music_level")[0]["status"] == "not_checked"


@pytest.mark.skipif(not shutil.which("ffmpeg"), reason="needs ffmpeg")
def test_footage_review_flags_a_mismatch(lib, monkeypatch):
    from types import SimpleNamespace

    from crcontent import script as script_mod

    asked = []

    class Client:  # Gemini stub: scores by what the narration talks about
        class beta:
            class messages:
                @staticmethod
                def create(**kw):
                    text = kw["messages"][0]["content"][-1]["text"]
                    asked.append(text)
                    ok = "octopus" in text
                    body = json.dumps({"score": 8 if ok else 2, "seen": "an octopus", "problem": "" if ok else "no car"})
                    return SimpleNamespace(content=[SimpleNamespace(type="text", text=body)])

    monkeypatch.setattr(script_mod, "make_client", lambda: Client)
    clip = lib / "uploads" / "octo.mp4"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", "testsrc2=s=320x240:d=3", str(clip)], check=True)
    scenes = [Scene(narration="An octopus has three hearts.", visual_query="q", media="uploads/octo.mp4"),
              Scene(narration="Faster than a race car.", visual_query="q", media="uploads/octo.mp4"),
              Scene(narration="Picked at render.", visual_query="q")]
    rep = qp.footage_review(qp.FootageRequest(script=script(*scenes), lengths=[2, 2, 2]))
    status = {c["scene"]: c["status"] for c in by(rep, "ai.footage")}
    assert status == {0: "pass", 1: "warning", 2: "not_checked"}
    assert by(rep, "ai.footage.1")[0]["start"] == 2
    qp.footage_review(qp.FootageRequest(script=script(*scenes), lengths=[2, 2, 2]))
    assert len(asked) == 2  # the second run reads the saved answers


def test_rights_flags_unknown_files_and_a_non_commercial_track(lib, monkeypatch):
    from crcontent import music, rights

    monkeypatch.setattr(rights, "ROOT", lib)
    monkeypatch.setattr(music, "MUSIC_DIR", lib / "assets" / "music")
    (lib / "assets" / "music").mkdir(parents=True)
    (lib / "assets" / "music" / "song.mp3").write_bytes(b"x")
    (lib / "assets" / "music" / "song.json").write_text(json.dumps({"license": "https://creativecommons.org/licenses/by-nc/3.0/"}))
    (lib / "cache").mkdir()
    for rel in ("cache/mystery.mp4", "cache/pixabay-6681.mp4", "uploads/mine.mp4"):
        (lib / rel).write_bytes(b"x")
    scenes = [Scene(narration="x", visual_query="q", media=m)
              for m in ("cache/mystery.mp4", "cache/pixabay-6681.mp4", "uploads/mine.mp4")]
    rep = qp.inspect_short(script(*scenes), "en", "song.mp3", [2, 2, 2], False)
    unknown = by(rep, "rights.media")
    assert [c["scene"] for c in unknown] == [0] and "mystery.mp4" in unknown[0]["title"]
    assert by(rep, "rights.music")[0]["status"] == "warning" and by(rep, "rights.youtube")[0]["status"] == "not_checked"
    ok = qp.inspect_short(script(*scenes[1:]), "en", "none", [2, 2], False)
    assert by(ok, "rights.media")[0]["status"] == "pass" and not by(ok, "rights.music")


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


# ---------- retention checks (deterministic, no AI key) ----------

def test_strong_short_passes_the_retention_checks(lib):
    s = script(Scene(narration="This shark is older than America.", visual_query="q", on_screen_text="400 YEARS OLD",
                     broll=[BRoll(media="", at=1.5)]),
               Scene(narration="It grows one centimeter every year in freezing water.", visual_query="q"),
               Scene(narration="So the one you see today was born before the Mayflower sailed.", visual_query="q"))
    rep = qp.inspect_short(s, "en", "none", [3.0, 4.0, 4.0], False)
    assert [c["status"] for c in by(rep, "pacing.opening")] == ["pass"]
    assert [c["status"] for c in by(rep, "story.repeat")] == ["pass"]
    assert not by(rep, "captions.echo") and not by(rep, "captions.collide") and not by(rep, "visual.stills")
    assert by(rep, "story.loop")[0]["status"] == "pass"


def test_long_first_shot_and_mid_sentence_ending(lib):
    s = script(Scene(narration="Deep in the Arctic there is an animal.", visual_query="q"),
               Scene(narration="And it is still out there", visual_query="q"))
    rep = qp.inspect_short(s, "en", "none", [6.0, 3.0], False)
    (opening,) = by(rep, "pacing.opening")
    assert opening["status"] == "warning" and opening["scene"] == 0 and opening["end"] == 6.0
    (end,) = by(rep, "story.loop")
    assert end["status"] == "warning" and end["scene"] == 1 and end["start"] == 6.0


def test_unvoiced_opening_is_not_checked(lib):
    assert by(qp.inspect_short(script(), "en", "none", [0], False), "pacing.opening")[0]["status"] == "not_checked"


def test_a_fact_said_twice(lib):
    s = script(Scene(narration="Greenland sharks can live for four hundred years.", visual_query="q"),
               Scene(narration="They swim slowly.", visual_query="q"),
               Scene(narration="A Greenland shark can live four hundred years!", visual_query="q"))
    (rep,) = by(qp.inspect_short(s, "en", "none", [3, 3, 3], False), "story.repeat.")
    assert rep["scene"] == 2 and "scene 1" in rep["title"] and rep["start"] == 6


def test_a_run_of_stills_but_not_a_single_still(lib):
    stills = [Scene(narration="x", visual_query="q", media=f"uploads/{k}.jpg") for k in range(3)]
    assert len(by(qp.inspect_short(script(*stills), "en", "none", [3, 3, 3], False), "visual.stills")) == 1
    one = [stills[0], Scene(narration="x", visual_query="q", media="uploads/v.mp4"), stills[1]]
    assert not by(qp.inspect_short(script(*one), "en", "none", [3, 3, 3], False), "visual.stills")


def test_headline_collides_with_raised_captions_and_echoes_the_voice(lib):
    s = script(Scene(narration="Octopuses have three hearts and blue blood.", visual_query="q",
                     on_screen_text="Three hearts, blue blood", texts=[TextOverlay(text="WOW", y=0.2)]))
    s.captions.y = 0.2
    rep = qp.inspect_short(s, "en", "none", [3], False)
    assert {c["detector"] for c in by(rep, "captions.collide")} == {"captions.collide.0", "captions.collide.0.0"}
    assert by(rep, "captions.echo")[0]["severity"] == "info"


def _apply(s, check):
    """What the editor does with a finding's fix (Storyboard's onApply)."""
    fix = check["fix"]
    if "captions" in fix:
        s.captions = s.captions.model_copy(update=fix["captions"])
    if "text" in fix:
        t = s.scenes[check["scene"]].texts[fix["text"]]
        s.scenes[check["scene"]].texts[fix["text"]] = t.model_copy(update=fix["set"])


@pytest.mark.parametrize("prefix", ["captions.collide", "captions.position", "captions.safe", "captions.clip", "captions.late"])
def test_each_fix_clears_its_finding(lib, prefix):
    s = script(Scene(narration="Octopuses have three hearts.", visual_query="q", on_screen_text="3 HEARTS",
                     texts=[TextOverlay(text="WOW", y=0.2), TextOverlay(text="LOW", y=0.95), TextOverlay(text="EDGE", x=0.97, y=0.5),
                            TextOverlay(text="LATE", at=9)]))
    s.captions.y = {"captions.position": 0.9}.get(prefix, 0.2)
    found = [c for c in by(qp.inspect_short(s, "en", "none", [3], False), prefix) if c["status"] == "warning"]
    assert found and all(c["fix"]["label"] for c in found)
    for c in found:
        _apply(s, c)
    assert not [c for c in by(qp.inspect_short(s, "en", "none", [3], False), prefix) if c["status"] == "warning"]


def test_moved_headline_gets_moved_back_instead(lib):
    s = script(Scene(narration="Octopuses have three hearts.", visual_query="q", on_screen_text="3 HEARTS"))
    s.captions.headline_y = 0.58
    (c,) = by(qp.inspect_short(s, "en", "none", [3], False), "captions.collide")
    assert c["fix"]["captions"] == {"headline_y": 0.13}
