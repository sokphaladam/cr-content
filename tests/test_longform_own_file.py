import json
import subprocess

import pytest

import crcontent.longform as longform
from crcontent.longform import footage as lf_footage
from crcontent.longform import settings
from crcontent.longform.parse import Scene, Script
from crcontent.longform.timing import Slot, Timeline


@pytest.fixture
def job(tmp_path, monkeypatch):
    """A storyboard with 2 scenes on stock footage; the media folder and the page writer are stubbed."""
    job = tmp_path / "job"
    (job / "storyboard").mkdir(parents=True)
    media = tmp_path / "media"
    stock = tmp_path / "stock.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc2=s=640x360:d=2", "-pix_fmt", "yuv420p",
                    str(stock)], check=True)
    Script("T", "t-ep01", "en", [Scene(1, 0, "v", "", "One."), Scene(2, 2, "v", "", "Two.")]).save(job / "scenes.json")
    (job / "timeline.json").write_text(json.dumps(Timeline([Slot(1, 0, 2.0, 0, "a.mp3", 1.7),
                                                            Slot(2, 2.0, 2.0, 2, "b.mp3", 1.7)], [], 4).to_json()))
    pick = {"source": "pixabay", "kind": "video", "id": 7, "file": str(stock)}
    (job / "footage.json").write_text(json.dumps([
        {"scene": 1, "chosen": dict(pick), "flags": [], "alternatives": []},
        {"scene": 2, "chosen": dict(pick, id=8), "flags": [], "alternatives": []}]))
    monkeypatch.setattr(settings, "load", lambda: {})
    monkeypatch.setattr(longform, "media_folder", lambda slug, cfg: media)
    monkeypatch.setattr(lf_footage, "_thumb", lambda *a, **k: None)
    from crcontent.longform import storyboard
    monkeypatch.setattr(storyboard, "write", lambda *a, **k: None)
    return job, media, stock


def test_upload_replaces_one_scene_and_sets_the_old_file_aside(job, tmp_path):
    job, media, stock = job
    longform.use_own_file(job, 1, stock, "my cat.mp4")
    entries = json.loads((job / "footage.json").read_text())
    assert entries[0]["chosen"]["source"] == "own" and entries[0]["chosen"]["file"] == str(media / "scene-01.mp4")
    assert entries[1]["chosen"]["source"] == "pixabay"  # the other scene is untouched

    longform.use_own_file(job, 1, stock, "second.mov")
    assert (media / "scene-01.mov").exists() and not (media / "scene-01.mp4").exists()
    assert len(list((media / "removed").iterdir())) == 1  # set aside, never deleted


def test_only_videos_and_photos(job):
    job, media, stock = job
    with pytest.raises(ValueError, match="Use a video"):
        longform.use_own_file(job, 1, stock, "notes.txt")
    with pytest.raises(KeyError):
        longform.use_own_file(job, 9, stock, "a.mp4")
