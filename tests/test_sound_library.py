"""Attention roadmap M6: the sound library (synthesized and imported), the mix's ducking and safety, sound suggestions."""
import array
import json
import shutil
import subprocess
from types import SimpleNamespace

import pytest

from crcontent import director_plan, render, sfx, sound_director, timeline
from crcontent.script import Clip, Scene, TrackState, VideoScript

FFMPEG = pytest.mark.skipif(not shutil.which("ffmpeg"), reason="needs ffmpeg")


@pytest.fixture(autouse=True)
def lib(tmp_path, monkeypatch):
    monkeypatch.setattr(sfx, "SFX_DIR", tmp_path / "sfx-cache")
    monkeypatch.setattr(sfx, "USER_DIR", tmp_path / "assets" / "sfx")
    return tmp_path


def wav(path, seconds=1.0, freq=440, level=0.5):
    """A tone at `level` of full scale (ffmpeg's sine source is 1/8 of it)."""
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", f"sine=f={freq}:d={seconds}", "-af", f"volume={level * 8}",
                    "-ac", "2", str(path)], check=True)
    return path


def test_every_synthesized_sound_is_catalogued():
    cat = {s["name"]: s for s in sfx.catalog(render.duration)}
    assert set(cat) == set(sfx.SOUNDS) and {s["category"] for s in cat.values()} == set(sfx.CATEGORIES)
    assert all(s["duration"] > 0 and s["description"] and s["licence"] == sfx.SYNTH_LICENCE for s in cat.values())
    assert cat["drone"]["category"] == "suspense" and cat["chime"]["category"] == "reveal"


@FFMPEG
def test_import_needs_a_licence_and_a_credit_when_it_asks(lib):
    from fastapi.testclient import TestClient

    from crcontent import web

    client = TestClient(web.app)
    good = wav(lib / "owl.wav")
    form = {"label": "Owl hoot", "category": "action", "licence": "CC BY", "credit": "Jane Doe", "source": "https://example.org/owl"}

    def post(path, **over):
        with open(path, "rb") as f:
            return client.post("/api/sfx/import", data={**form, **over}, files={"file": (path.name, f)})

    assert "licence" in post(good, licence="I found it").json()["detail"]
    assert "asks for a credit" in post(good, credit="").json()["detail"]
    assert post(good, source="ftp://x").status_code == 400
    (lib / "junk.wav").write_bytes(b"not audio")
    assert "can read" in post(lib / "junk.wav").json()["detail"]
    assert not list(sfx.USER_DIR.glob("junk*"))  # a refused file isn't kept
    made = post(good).json()
    name = made["name"]
    assert name.startswith("user:owl-hoot-") and made["licence"] == "CC BY"
    listed = {s["name"]: s for s in client.get("/api/timeline/catalog").json()["sounds"]}
    assert listed[name]["credit"] == "Jane Doe" and listed[name]["category"] == "action"
    assert client.get(f"/api/sfx/{name}.wav").status_code == 200
    assert client.get(f"/api/sfx/{name}/peaks").json()["rate"] > 0
    assert client.get("/api/sfx/user:..%2F..%2Fsecret.wav").status_code == 404
    # its credit goes into the description; synthesized sounds and own recordings need none
    assert sfx.credits([name, "impact", name]) == ["Sound: Jane Doe (CC BY) https://example.org/owl"]


def test_a_missing_imported_sound_is_left_out_not_fatal():
    s = VideoScript(title="T", caption="", hashtags=[], scenes=[Scene(narration="a", visual_query="b")],
                    clips=[Clip(id="c", track="sfx", start=1, sound="user:gone-123456")])
    notes = []
    assert timeline.sound_events(s, 10, notes.append) == [] and "isn't in the library" in notes[0]
    assert "isn't in the sound library any more" in timeline.check(s.clips)[0]


# ---------- the mix ----------

def _levels(path, windows, rate=4000):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-ac", "1", "-ar", str(rate), "-f", "s16le", "-"],
                         capture_output=True, check=True).stdout
    a = array.array("h", raw)
    return [max(1, (sum(v * v for v in a[int(x * rate):int(y * rate)]) / max(1, int((y - x) * rate))) ** 0.5) for x, y in windows]


def _voice_video(path, seconds=6, speech=()):
    """A silent picture with a 'voice': a 200 Hz tone in the `speech` windows, silence elsewhere."""
    expr = "+".join(f"between(t,{a},{b})" for a, b in speech) or "0"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", f"aevalsrc='0.3*sin(2*PI*200*t)*({expr})':s=44100:d={seconds}",
                    "-f", "lavfi", "-i", "color=black:s=64x64", "-t", str(seconds), "-shortest", "-ac", "2", str(path)], check=True)


@FFMPEG
def test_a_ducking_sound_dips_the_music(lib):
    _voice_video(lib / "v.mp4", speech=[(0.2, 0.6)])
    music = wav(lib / "music.wav", seconds=6, freq=110, level=0.6)
    hit = wav(lib / "hit.wav", seconds=1.5, freq=3000, level=0.6)
    opts = {"in": 0, "dur": 1.5, "fade_in": 0, "fade_out": 0}
    levels = {}
    for duck in (False, True):
        name = render._mix_audio(lib, "v.mp4", music, 0.25, None, [(hit, 3.0, 1.0, {**opts, "duck": duck})])
        (lib / f"mix-{duck}.wav").write_bytes((lib / name).read_bytes())
        # music alone (low band) during the hit, against before it
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(lib / f"mix-{duck}.wav"), "-af", "lowpass=f=300", str(lib / f"low-{duck}.wav")], check=True)
        before, during = _levels(lib / f"low-{duck}.wav", [(1.5, 2.8), (3.3, 4.3)])
        levels[duck] = during / before
    assert levels[True] < levels[False] * 0.75  # the music dips under the ducking sound
    assert levels[False] > 0.8  # and doesn't when it isn't marked


@FFMPEG
def test_timeline_sounds_stay_under_the_voice_and_never_click(lib):
    _voice_video(lib / "v.mp4", speech=[(1.0, 3.0)])
    loud = wav(lib / "loud.wav", seconds=4, freq=1000, level=0.9)
    # the same sound under speech (1-3 s) and in silence (4-5 s), cut mid-wave with no fades
    events = [(loud, 1.0, 1.6, {"in": 0.0123, "dur": 2.0, "fade_in": 0, "fade_out": 0}),
              (loud, 4.0, 1.6, {"in": 0.0123, "dur": 1.0, "fade_in": 0, "fade_out": 0})]
    name = render._mix_audio(lib, "v.mp4", None, 0.25, None, events)
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(lib / name), "-af", "highpass=f=600", str(lib / "hi.wav")], check=True)
    under_voice, alone = _levels(lib / "hi.wav", [(1.5, 2.8), (4.2, 4.8)])
    assert under_voice < alone * 0.8  # the voice comes first
    # no click: the first and last 2 ms of the cut sound rise and fall instead of jumping to full level
    start, settled = _levels(lib / "hi.wav", [(4.0, 4.002), (4.2, 4.3)], rate=44100)
    assert start < settled * 0.5
    # the finished mix holds its peaks under the limit (render.TRUE_PEAK) however loud the sounds
    out = subprocess.run(["ffmpeg", "-v", "info", "-i", str(lib / name), "-af", "ebur128=peak=true", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    peak = float(out.rsplit("Peak:", 1)[1].split("dBFS")[0])
    assert peak <= render.TRUE_PEAK + 0.5


def test_lanes_include_the_music_ducking():
    s = VideoScript(title="T", caption="", hashtags=[], scenes=[], tracks={"music": TrackState(duck=0.3)})
    assert timeline.mix(s)["music_duck"] == 0.3
    with pytest.raises(ValueError):
        TrackState(duck=2)


# ---------- suggestions ----------

LINES = ["This bird solves a puzzle in the rain.", "Scientists hid meat in a tube.", "It bends the wire into a hook.",
         "It pulls the meat out on the first try."]


def plan_for():
    plan = director_plan.from_scenes("Crow", "short", "en", "educational", [{"narration": n} for n in LINES])
    plan.planned_by = "ai"
    for sc, (phase, role) in zip(plan.scenes, [("setup", "curiosity_gap"), ("tension", "stakes"), ("tension", "evidence"),
                                               ("payoff", "final_payoff")]):
        sc.phase, sc.beat_role = phase, role
    return plan


def script():
    return VideoScript(title="Crow", caption="", hashtags=[], scenes=[Scene(narration=n, visual_query="crow") for n in LINES])


def test_rules_follow_the_story_and_hold_back():
    out = sound_director.suggest(script(), plan_for(), [4, 4, 4, 4], use_ai=False)
    got = {(e["sound"], e["scene"]) for e in out["events"]}
    assert out["source"] == "rules" and "story beats" in out["note"]
    assert ("rain", 0) in got  # the scene names rain: its bed
    assert ("chime", 3) in got  # the payoff
    assert ("riser", 2) in got or ("impact", 2) in got  # and one accent before it: 16 s of video holds only two
    chime = next(e for e in out["events"] if e["sound"] == "chime")
    assert chime["essential"] and chime["duck"] and chime["reason"]
    accents = [e for e in out["events"] if e["sound"] not in sfx.AMBIENT]
    assert len(accents) <= 16 // sound_director.PER_SECONDS  # restraint
    assert all(abs(a["start"] - b["start"]) >= sound_director.GAP for a, b in zip(accents, accents[1:]))
    # a sound already on the timeline near the payoff blocks a second accent there
    crowded = sound_director.suggest(script(), plan_for(), [4, 4, 4, 4], existing=[12.2], use_ai=False)
    assert not any(e["sound"] == "chime" for e in crowded["events"])
    # no plan: only what the words say
    bare = sound_director.suggest(script(), None, [4, 4, 4, 4], use_ai=False)
    assert [e["sound"] for e in bare["events"]] == ["rain"]
    assert sound_director.suggest(script(), None, [0, 0, 0, 0], use_ai=False)["events"] == []


class Fake:
    def __init__(self, answer):
        self.answer = answer
        outer = self

        class messages:
            @staticmethod
            def create(**kw):
                outer.sent = kw
                if isinstance(outer.answer, Exception):
                    raise outer.answer
                return SimpleNamespace(content=[SimpleNamespace(type="text", text=json.dumps(outer.answer))])

        self.beta = SimpleNamespace(messages=messages)


def test_ai_suggestions_are_checked_and_fall_back_to_rules():
    answer = {"events": [
        {"scene": 4, "offset": 0.2, "sound": "chime", "duration": 9, "gain": 3, "fade_in": 0, "fade_out": 0.3, "duck": True,
         "essential": True, "reason": "The hook pays off."},
        {"scene": 9, "offset": 0, "sound": "impact", "duration": 1, "gain": 1, "fade_in": 0, "fade_out": 0, "duck": False,
         "essential": False, "reason": "invented scene"},
        {"scene": 2, "offset": 0, "sound": "dragon_roar", "duration": 1, "gain": 1, "fade_in": 0, "fade_out": 0,
         "duck": False, "essential": False, "reason": "invented sound"}]}
    out = sound_director.suggest(script(), plan_for(), [4, 4, 4, 4], client=Fake(answer))
    [e] = out["events"]
    assert out["source"] == "ai" and e["sound"] == "chime" and e["start"] == 12.2
    assert e["duration"] == round(sound_director.sfx_length("chime"), 2) and e["gain"] == 1.2  # clamped to the library
    failed = sound_director.suggest(script(), plan_for(), [4, 4, 4, 4], client=Fake(RuntimeError("down")))
    assert failed["source"] == "rules" and "couldn't suggest" in failed["note"] and failed["events"]


def test_suggest_endpoint_without_a_key_uses_the_rules(monkeypatch):
    from fastapi.testclient import TestClient

    from crcontent import web

    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    out = TestClient(web.app).post("/api/sounds/suggest", json={"script": script().model_dump(), "lengths": [4, 4, 4, 4]}).json()
    assert out["source"] == "rules" and [e["sound"] for e in out["events"]] == ["rain"]
