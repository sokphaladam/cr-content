"""Attention roadmap M4: the timeline's global graphics / sound clips, their storage and how the render uses them."""
import json
import shutil
import subprocess

import pytest
from pydantic import ValidationError

from crcontent import render, sfx, timeline
from crcontent.script import Clip, Scene, TrackState, VideoScript


def script(*clips, **tracks):
    return VideoScript(title="T", caption="c", hashtags=[], scenes=[Scene(narration="a", visual_query="b")],
                       clips=list(clips), tracks=tracks)


SFX = Clip(id="c1", track="sfx", start=2, duration=1.5, source_in=0.2, sound="impact", gain=0.8, fade_in=0.1, fade_out=2)
GFX = Clip(id="g1", track="graphics", start=1, duration=3, template="Fact", props={"shown": "7"}, layer=1)


def test_old_scripts_load_and_clips_round_trip():
    old = VideoScript.model_validate({"title": "T", "caption": "", "hashtags": [], "scenes": []})
    assert old.clips == [] and old.tracks == {} and old.timeline_version == 1
    s = script(SFX, GFX, music=TrackState(mute=True))
    again = VideoScript.model_validate_json(s.model_dump_json())
    assert again == s and again.track("music").mute and again.track("sfx").volume == 1


def test_bad_timelines_are_refused():
    with pytest.raises(ValidationError, match="unique"):
        script(SFX, SFX)
    with pytest.raises(ValidationError, match="unknown timeline tracks"):
        script(SFX, drums=TrackState())
    with pytest.raises(ValidationError):
        Clip(id="x", track="sfx", duration=0)
    with pytest.raises(ValidationError):
        Clip(id="x", track="video")


def test_sound_events_trim_fade_and_follow_the_track():
    [(path, at, vol, cut)] = timeline.sound_events(script(SFX), 30)
    assert path == sfx.sound("impact") and at == 2 and vol == pytest.approx(0.8)
    assert cut == {"in": 0.2, "dur": 1.5, "fade_in": 0.1, "fade_out": 0.75, "duck": False}  # a fade never longer than half the clip
    assert timeline.sound_events(script(SFX), 2.5)[0][3]["dur"] == 0.5  # cut at the video's end
    assert timeline.sound_events(script(SFX), 1.9) == []  # starts after the end
    assert timeline.sound_events(script(SFX, sfx=TrackState(mute=True)), 30) == []
    assert timeline.sound_events(script(SFX, sfx=TrackState(volume=0.5)), 30)[0][2] == pytest.approx(0.4)
    notes = []
    assert timeline.sound_events(script(SFX.model_copy(update={"sound": "nope"})), 30, notes.append) == []
    assert "isn't in the library, left out" in notes[0]


def test_graphic_clips_become_remotion_jobs():
    under = GFX.model_copy(update={"id": "g0", "layer": 0, "start": 5})
    todo = timeline.graphic_clips(script(GFX, under), 4.5, "data:font")
    assert [c["clip"] for c in todo] == ["g1"]  # g0 starts after the video's end
    [job] = todo
    assert job["id"] == "Fact" and job["at"] == 1
    assert job["props"]["shown"] == "7" and job["props"]["unit"] == "HEARTS"  # the clip's props over the defaults
    assert job["props"]["seconds"] == 3 and job["props"]["font"] == "data:font"
    assert [c["clip"] for c in timeline.graphic_clips(script(GFX, under), 30, "")] == ["g0", "g1"]  # bottom layer first
    notes = []
    assert timeline.graphic_clips(script(GFX, graphics=TrackState(hidden=True)), 30, "", notes.append) == []
    assert "hidden" in notes[0]


def test_lanes_for_the_mix():
    assert timeline.mix(script()) == {"music_on": True, "music_volume": 0.25, "voice_gain": 1, "music_duck": 1}
    lanes = timeline.mix(script(music=TrackState(mute=True), voice=TrackState(volume=0.5)))
    assert not lanes["music_on"] and lanes["voice_gain"] == 0.5


@pytest.mark.skipif(not shutil.which("ffmpeg"), reason="needs ffmpeg")
def test_the_mix_places_a_trimmed_faded_clip(tmp_path):
    """A real mix: silence for a voice, one impact clip at 1.0 s: the sound is there from 1.0 s, not before."""
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo", "-f", "lavfi",
                    "-i", "color=black:s=64x64", "-t", "3", "-shortest", str(tmp_path / "v.mp4")], check=True)
    [event] = timeline.sound_events(script(Clip(id="c", track="sfx", start=1, duration=0.8, sound="impact",
                                                fade_out=0.2)), 3)
    name = render._mix_audio(tmp_path, "v.mp4", None, 0.25, None, [event])
    out = subprocess.run(["ffmpeg", "-v", "error", "-i", str(tmp_path / name), "-ac", "1", "-ar", "1000", "-f", "s16le", "-"],
                         capture_output=True, check=True).stdout
    import array

    samples = array.array("h", out)
    before, during, after = (max(abs(v) for v in samples[a:b]) for a, b in ((0, 950), (1000, 1600), (2000, 2900)))
    assert during > 1000 and before < during / 20 and after < during / 20


def test_endpoints(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient

    from crcontent import web

    monkeypatch.setattr(sfx, "SFX_DIR", tmp_path)
    client = TestClient(web.app)
    cat = client.get("/api/timeline/catalog").json()
    assert {s["name"] for s in cat["sounds"]} == set(sfx.SOUNDS) and all(s["duration"] > 0 for s in cat["sounds"])
    assert {"Fact", "MapZoom", "SizeCompare", "KineticTitle", "Spotlight"} <= set(cat["templates"])
    assert all(t["version"] >= 1 and t["fields"] for t in cat["templates"].values())
    assert client.get("/api/sfx/whoosh.wav").status_code == 200
    peaks = client.get("/api/sfx/whoosh/peaks").json()
    assert peaks["rate"] > 0 and max(peaks["peaks"]) == 1
    assert client.get("/api/sfx/..%2Fsecret.wav").status_code == 404
    assert client.get("/api/sfx/nope/peaks").status_code == 404


def test_preview_check_warns_about_clips_that_wont_render(tmp_path, monkeypatch):
    from crcontent import quality_preview as qp
    from crcontent.shorts import motion

    monkeypatch.setattr(qp, "ROOT", tmp_path)
    monkeypatch.setattr(motion, "PROJECT", tmp_path / "no-remotion")
    s = script(SFX.model_copy(update={"sound": ""}), GFX, Clip(id="late", track="sfx", start=50, sound="impact"))
    rep = qp.inspect_short(s, "en", "none", [4.0], False)
    found = {c["detector"]: c for c in rep["checks"] if c["detector"].startswith("timeline.")}
    assert "no sound picked" in found["timeline.clip.0"]["title"]
    assert "late" in found["timeline.late"]["description"]
    assert found["timeline.remotion"]["severity"] == "high"
    json.dumps(rep)  # still a plain JSON report
