import json
import subprocess

import pytest

import crcontent.shorts as shorts
from crcontent.longform.parse import Scene, Script
from crcontent.longform.timing import Slot, Timeline
from crcontent.shorts import footage, plan, preflight


@pytest.fixture
def job(tmp_path, monkeypatch):
    """A built Short (2 beats, stock picks) with the pre-flight and the media folder stubbed out."""
    job = tmp_path / "job"
    (job / "storyboard").mkdir(parents=True)
    media = tmp_path / "media"
    stock = tmp_path / "stock.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc2=s=640x360:d=4", "-pix_fmt", "yuv420p",
                    str(stock)], check=True)
    ep = plan.ShortPlan(1, "T", Script("T", "t-ep01", "en", [Scene(1, 0, "v", "HOOK", "One."),
                                                               Scene(2, 2, "v", "", "Two—")]))
    ep.save(job / "episode.json")
    (job / "timeline.json").write_text(json.dumps(Timeline([Slot(1, 0, 2.0, 0, "a.mp3", 1.7),
                                                            Slot(2, 2.0, 2.0, 2, "b.mp3", 1.7)], [], 4).to_json()))
    (job / "voice.json").write_text("[]")
    pick = {"source": "pixabay", "kind": "video", "id": 7, "file": str(stock), "start": 0.5}
    (job / "footage.json").write_text(json.dumps([
        {"scene": 1, "chosen": dict(pick), "match": 5, "flags": ["needs your own clip: ..."], "alternatives": []},
        {"scene": 2, "chosen": dict(pick, id=8), "match": 9, "flags": [], "alternatives": []}]))
    (job / "approved.json").write_text("{}")
    monkeypatch.setattr(shorts, "media_folder", lambda slug, cfg: media)
    monkeypatch.setattr(preflight, "write", lambda *a, **k: {"status": {"state": "needs work", "reasons": []}})
    scores = {"next": 8}  # what the (stubbed) shot-match check gives the next clip
    monkeypatch.setattr(footage.match, "check", lambda path, animal, shot, keys, start, length: {
        "score": scores["next"], "missing": [] if scores["next"] >= 7 else ["toy"], "seen": "a cat", "x": 0.5,
        "y": 0.4, "animal": True, "in_motion": True, "logo_or_text": False, "intro_or_title": False})
    return job, media, stock, scores


def test_your_clip_replaces_a_beat_and_can_be_removed(job, tmp_path):
    job, media, stock, scores = job
    mine = tmp_path / "my cat.mp4"
    mine.write_bytes(stock.read_bytes())
    shorts.use_own_clip(job, 1, mine, "my cat.mp4", log=lambda m: None)
    e = json.loads((job / "footage.json").read_text())[0]
    assert e["chosen"]["source"] == "own" and e["chosen"]["file"] == str(media / "scene-01.mp4")
    assert "start" in e["chosen"] and "hook" in e["chosen"]    # the hook rules still look at your clip
    assert e["stock"]["chosen"]["id"] == 7 and e["match"] == 8 and e["flags"] == []  # scored like stock
    assert not (job / "approved.json").exists()                # a changed Short needs approving again

    shorts.use_own_clip(job, 1, mine, "second.mov", log=lambda m: None)   # a new upload sets the old one aside
    assert (media / "scene-01.mov").exists() and not (media / "scene-01.mp4").exists()
    assert len(list((media / "removed").iterdir())) == 1
    assert json.loads((job / "footage.json").read_text())[0]["stock"]["chosen"]["id"] == 7  # still the stock pick

    shorts.remove_own_clip(job, 1, log=lambda m: None)
    e = json.loads((job / "footage.json").read_text())[0]
    assert e["chosen"]["id"] == 7 and e["match"] == 5 and "stock" not in e
    assert not (media / "scene-01.mov").exists() and len(list((media / "removed").iterdir())) == 2  # never deleted


def test_only_videos_and_photos(job, tmp_path):
    job, media, stock, scores = job
    with pytest.raises(ValueError, match="Use a video"):
        shorts.use_own_clip(job, 1, stock, "notes.txt", log=lambda m: None)
    with pytest.raises(ValueError, match="no beat 9"):
        shorts.use_own_clip(job, 9, stock, "a.mp4", log=lambda m: None)
    with pytest.raises(ValueError, match="isn't using your clip"):
        shorts.remove_own_clip(job, 2, log=lambda m: None)


def test_your_clip_is_held_to_the_planned_shot(job, tmp_path):
    job, media, stock, scores = job
    scores["next"] = 4
    shorts.use_own_clip(job, 2, stock, "mine.mp4", log=lambda m: None)
    e = json.loads((job / "footage.json").read_text())[1]
    assert e["match"] == 4 and "your clip: shot match 4/10 (no toy)" in e["flags"][0]
    assert footage.weak(json.loads((job / "footage.json").read_text())) == [1, 2]  # beat 1's stock was 5/10 too
