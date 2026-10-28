import cv2
import numpy as np
from PIL import Image


def _song(tmp_path, monkeypatch):
    from crcontent import lyricvideo
    from neonmekong import pictures

    song = tmp_path / "s"
    (song / "out").mkdir(parents=True)
    (song / "song.json").write_text('{"title": "T", "mood_phrase": "rainy night", '
                                    '"sections": [{"tag": "Verse", "kind": "verse", "start": 1, "end": 9}]}')
    (song / "lyrics.lrc").write_text("[00:02.00]hello\n")
    (song / "suno.txt").write_text("x")
    monkeypatch.setattr(lyricvideo, "SONGS_DIR", tmp_path)
    monkeypatch.setattr(pictures, "ai_prompts", lambda *a, **k: None)   # no Gemini in tests
    return song


def _clip(path, level):
    out = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), 10, (64, 36))
    for _ in range(10):
        out.write(np.full((36, 64, 3), level, np.uint8))
    out.release()


def test_the_cover_switches_between_picture_and_animated(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient

    from crcontent import web
    from neonmekong import songjson, thumbnail

    song = _song(tmp_path, monkeypatch)
    c = TestClient(web.app)
    p = c.get("/api/lyricvideo/s/pictures").json()
    assert p["cover_mode"] == "picture" and p["loop"] == "" and "rainy night" in p["loop_prompt"]

    Image.new("RGB", (64, 36), (10, 10, 10)).save(tmp_path / "dark.png")
    with open(tmp_path / "dark.png", "rb") as f:
        assert c.post("/api/lyricvideo/s/pictures/cover/upload", files={"image": ("dark.png", f)}).json()["cover_mode"] == "picture"

    _clip(tmp_path / "bright.mp4", 240)
    with open(tmp_path / "bright.mp4", "rb") as f:
        p = c.post("/api/lyricvideo/s/loop/upload", files={"video": ("bright.mp4", f)}).json()
    assert p["cover_mode"] == "animated" and p["loop"] == "loop.mp4"
    # the thumbnail and the still behind the video follow the animated cover...
    data = songjson.load(song / "song.json")
    assert np.asarray(thumbnail.custom_background(data, 32, 18)).mean() > 200
    r = c.get("/api/lyricvideo/s/thumbnail/preview")
    assert r.status_code == 200 and r.headers["content-type"] == "image/jpeg"

    # ...and the picture again once it is switched back, though the loop is kept
    p = c.put("/api/lyricvideo/s/pictures", json={"cover_mode": "picture", "loop_prompt": "  a quiet beach  "}).json()
    assert p["cover_mode"] == "picture" and p["loop"] == "loop.mp4" and p["loop_prompt"] == "a quiet beach"
    assert np.asarray(thumbnail.custom_background(data, 32, 18)).mean() < 30
    assert thumbnail.active_loop(song) is None

    assert c.put("/api/lyricvideo/s/pictures", json={"cover_mode": "video"}).status_code == 400
    assert c.post("/api/lyricvideo/s/loop/upload", files={"video": ("x.gif", b"GIF89a")}).status_code == 400
    p = c.delete("/api/lyricvideo/s/loop").json()
    assert p["loop"] == "" and p["cover_mode"] == "picture"


def test_a_library_song_shares_the_animated_cover(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient

    from crcontent import config, coverloop, web

    lyric = _song(tmp_path, monkeypatch)
    out = tmp_path / "output"
    (out / "my-song").mkdir(parents=True)
    (out / "my-song" / "song.json").write_text('{"title": "Mine", "mood": "sleepy", "sections": []}')
    monkeypatch.setattr(web, "OUTPUT_DIR", out)
    monkeypatch.setattr(config, "OUTPUT_DIR", out)
    c = TestClient(web.app)

    v = c.get("/api/videos/my-song/cover-loop").json()
    assert v["cover_mode"] == "picture" and v["loop"] == "" and "sleepy" in v["loop_prompt"]
    # picking Animated before any loop exists sticks (the page then shows Draw / Upload clip); renders keep the picture
    assert c.put("/api/videos/my-song/cover-loop", json={"cover_mode": "animated"}).json()["cover_mode"] == "animated"
    assert coverloop.active(out / "my-song") is None
    assert c.put("/api/lyricvideo/s/pictures", json={"cover_mode": "animated"}).json()["cover_mode"] == "animated"
    _clip(tmp_path / "room.mp4", 200)
    with open(tmp_path / "room.mp4", "rb") as f:
        assert c.post("/api/videos/my-song/cover-loop/upload", files={"video": ("room.mp4", f)}).json()["cover_mode"] == "animated"
    assert coverloop.active(out / "my-song")

    # the Lyrics page sees the Library song's loop and can reuse it, with no Gemini request
    p = c.get("/api/lyricvideo/s/pictures").json()
    assert {"slug": "video:my-song", "title": "Mine"} in p["other_loops"]
    assert c.post("/api/lyricvideo/s/loop/from/video:my-song").json()["cover_mode"] == "animated"
    assert (lyric / "loop.mp4").exists()
    # and the other way round
    assert {"slug": "lyric:s", "title": "T"} in c.get("/api/videos/my-song/cover-loop").json()["other_loops"]

    assert c.put("/api/videos/my-song/cover-loop", json={"cover_mode": "picture"}).json()["cover_mode"] == "picture"
    assert coverloop.active(out / "my-song") is None
    assert c.delete("/api/videos/my-song/cover-loop").json()["loop"] == ""


def _ramp(path, seconds, fps=10):
    """A clip whose grey level is its own time: 10 levels per second."""
    out = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), fps, (64, 36))
    for i in range(int(seconds * fps)):
        out.write(np.full((36, 64, 3), min(255, i * 2), np.uint8))
    out.release()


def _frames(path):
    cap, out = cv2.VideoCapture(str(path)), []
    while True:
        ok, img = cap.read()
        if not ok:
            return out
        out.append(float(img.mean()))


def test_the_gpu_loop_has_no_seam(tmp_path):
    from crcontent import coverloop

    _ramp(tmp_path / "raw.mp4", 14)
    coverloop.seamless(tmp_path / "raw.mp4", tmp_path / "loop.mp4", 12.0, 2.0)
    f = _frames(tmp_path / "loop.mp4")
    assert abs(len(f) - 120) <= 2                      # 12 s at 10 fps
    assert abs(f[0] - 240) < 12                        # it starts where it ends (the raw clip at 12 s)...
    assert abs(f[-1] - 238) < 12                       # ...so pass after pass joins with no jump
    assert max(abs(a - b) for a, b in zip(f, f[1:])) < 20


def test_the_gpu_endpoint_draws_and_animates(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient

    from crcontent import coverloop, fx, imagegen, pipeline, web

    song = _song(tmp_path, monkeypatch)
    drawn = tmp_path / "drawn.png"
    Image.new("RGB", (64, 36), (90, 90, 90)).save(drawn)
    seen = {}
    monkeypatch.setattr(coverloop, "gpu_check", lambda: None)
    monkeypatch.setattr(imagegen, "generate", lambda prompt, style, size, **k: seen.update(prompt=prompt, style=style) or drawn)
    monkeypatch.setattr(fx, "render_shot", lambda image, length, out, **k: seen.update(length=length, **k) or _ramp(out, length))
    monkeypatch.setattr(pipeline, "release_gpu", lambda: seen.update(released=True))
    c = TestClient(web.app)

    assert c.post("/api/lyricvideo/s/loop/gpu", json={"effects": ["rain", "dust", "nonsense"]}).json()["job"]["state"] == "running"
    _wait(c, "/api/lyricvideo/s/loop/status")
    p = c.get("/api/lyricvideo/s/pictures").json()
    assert p["cover_mode"] == "animated" and p["loop"] == "loop.mp4" and p["loop_effects"] == ["rain", "dust"]
    assert seen["style"] == "anime" and seen["prompt"].startswith("cozy room") and seen["released"]
    assert seen["length"] == 14.0 and seen["motion"] == "breathe" and seen["effects"] == ["rain", "dust"]
    assert (song / "loop.png").exists() and "Rain" in p["effect_choices"].values()

    # bringing the song's own cover picture to life needs one
    assert c.post("/api/lyricvideo/s/loop/gpu", json={"use_cover": True}).status_code == 400



def _wait(c, url):
    import time

    for _ in range(1200):   # a character loop is rebuilt at 1080p: several seconds
        st = c.get(url).json()
        if st["state"] != "running":
            assert st["state"] == "done", st
            return st
        time.sleep(0.05)
    raise AssertionError("the GPU loop never finished")


def test_character_motion_repeats_one_take_into_the_loop(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient

    from crcontent import coverloop, pipeline, videogen, web

    song = _song(tmp_path, monkeypatch)
    Image.new("RGB", (64, 36), (90, 90, 90)).save(song / "background.png")
    seen = {}

    def take(picture, prompt, out, seed=0, log=print, progress=None):
        seen.update(picture=picture, prompt=prompt)
        progress(40, 40)
        _ramp(out, 4.0, fps=24)          # 96 frames: a 4 s take
        return out

    monkeypatch.setattr(videogen, "check", lambda: None)
    monkeypatch.setattr(videogen, "take", take)
    monkeypatch.setattr(pipeline, "release_gpu", lambda: None)
    c = TestClient(web.app)
    c.put("/api/lyricvideo/s/pictures", json={"loop_prompt": "1girl, desk, notebook",   # the drawing's tags...
                                              "loop_movement": "she nods slowly while writing, steam rises"})
    r = c.post("/api/lyricvideo/s/loop/gpu", json={"motion": "character", "use_cover": True})
    assert r.status_code == 200, r.text
    _wait(c, "/api/lyricvideo/s/loop/status")
    # ...stay out of the video model's prompt: it gets only the movement
    assert seen["prompt"] == "she nods slowly while writing, steam rises" and seen["picture"] == song / "loop.png"
    cap = cv2.VideoCapture(str(song / "loop.mp4"))
    frames, w, fps = cap.get(cv2.CAP_PROP_FRAME_COUNT), cap.get(cv2.CAP_PROP_FRAME_WIDTH), cap.get(cv2.CAP_PROP_FPS)
    cap.release()
    assert w == 1920 and frames == 360 and fps == 30          # exactly 12 s: whole passes of the take, retimed to fit
    p = c.get("/api/lyricvideo/s/pictures").json()
    assert p["loop_motion"] == "character" and p["loop_seam"]["ok"]
    assert p["loop_settings"]["model"] == videogen.REPO and p["loop_settings"]["seed"] == 0
    assert p["loop_movement"].startswith("she nods") and p["loop_settings"]["changed"] == p["loop_changed"]
    assert not list(song.glob("loop.*.mp4"))                  # no leftovers

    # one GPU loop at a time
    monkeypatch.setattr(coverloop, "_gpu", type("Busy", (), {"acquire": lambda self, blocking=True: False})())
    assert c.post("/api/lyricvideo/s/loop/gpu", json={"motion": "character", "use_cover": True}).status_code == 409
