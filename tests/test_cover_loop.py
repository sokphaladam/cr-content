import math
import shutil

import cv2
import numpy as np
import pytest
from PIL import Image


def _small(monkeypatch, depth=None):
    """A 64x36, 1-second loop (30 frames) so renders take a moment; depth: a fake depth map, or None for no model."""
    from crcontent import coverloop, fx

    monkeypatch.setattr(coverloop, "SIZE", (64, 36))
    monkeypatch.setattr(coverloop, "SECONDS", 1.0)

    def depth_map(image):
        if depth is None:
            raise ImportError("no torch")
        return type("T", (), {"float": lambda s: s, "cpu": lambda s: s, "numpy": lambda s: depth[None, None]})()

    monkeypatch.setattr(fx, "depth_map", depth_map)


def _frames(path):
    cap = cv2.VideoCapture(str(path))
    out = []
    while True:
        ok, f = cap.read()
        if not ok:
            break
        out.append(f.astype(np.int16))
    cap.release()
    return out


def _picture(path, size=(96, 54)):
    w, h = size
    x = np.linspace(60, 220, w, dtype=np.uint8)[None, :, None].repeat(h, 0).repeat(3, 2)
    Image.fromarray(x).save(path)
    return path


def test_the_camera_path_is_periodic_and_subtle():
    from crcontent import coverloop

    T = coverloop.SECONDS
    assert coverloop.camera(0, 40) == pytest.approx(coverloop.camera(T, 40), abs=1e-12)
    eps = 1e-4   # velocity matches across the seam too
    v_end = [(b - a) / eps for a, b in zip(coverloop.camera(T - eps, 40), coverloop.camera(T, 40))]
    v_start = [(b - a) / eps for a, b in zip(coverloop.camera(0, 40), coverloop.camera(eps, 40))]
    assert v_end == pytest.approx(v_start, abs=1e-3)
    for i in range(360):
        dx, dy, z = coverloop.camera(i / 30, 100)
        assert abs(dx) <= 0.02 and abs(dy) <= 0.015 and 1 <= z <= 1.02
    assert coverloop.camera(5, 0) == (0, 0, 1)


@pytest.mark.parametrize("ext", ["png", "jpg", "webp"])
def test_parallax_renders_a_seamless_loop_with_no_gaps(tmp_path, monkeypatch, ext):
    from crcontent import coverloop

    _small(monkeypatch, depth=np.linspace(0, 1, 16, dtype=np.float32)[:, None].repeat(16, 1))
    still = tmp_path / "loop.png"   # animate() copies the song's picture here, whatever its format
    shutil.copy(_picture(tmp_path / f"background.{ext}"), still)
    out = tmp_path / "loop.mp4"
    assert coverloop.parallax(still, out, 100) is True
    f = _frames(out)
    assert len(f) == 30 and f[0].shape == (36, 64, 3)
    assert min(x.min() for x in f) > 30                              # no black wedges at the edges
    assert np.abs(f[-1] - f[0]).mean() < 6                           # the last frame runs into the first
    assert max(np.abs(a - b).mean() for a, b in zip(f, f[1:])) < 6   # and no jumps along the way
    assert np.abs(f[7] - f[0]).mean() > 0.5                          # but it does move
    assert not list(tmp_path.glob("*.tmp.mp4"))

    again = tmp_path / "again.mp4"
    coverloop.parallax(still, again, 100)
    assert all(np.abs(a - b).max() <= 2 for a, b in zip(f, _frames(again)))   # deterministic


def test_parallax_without_a_depth_model_drifts_flat(tmp_path, monkeypatch):
    from crcontent import coverloop

    _small(monkeypatch)
    logs = []
    assert coverloop.parallax(_picture(tmp_path / "p.png"), tmp_path / "loop.mp4", log=logs.append) is False
    assert len(_frames(tmp_path / "loop.mp4")) == 30 and "2D drift" in logs[0]


def test_parallax_rejects_bad_input_and_keeps_the_old_loop_on_failure(tmp_path, monkeypatch):
    from crcontent import coverloop

    _small(monkeypatch)
    out = tmp_path / "loop.mp4"
    out.write_bytes(b"the old loop")
    (tmp_path / "bad.png").write_bytes(b"not a picture")
    with pytest.raises(ValueError, match="can't be read"):
        coverloop.parallax(tmp_path / "bad.png", out)
    with pytest.raises(ValueError, match="0 to 100"):
        coverloop.parallax(_picture(tmp_path / "p.png"), out, 101)

    def boom(*a, **k):
        raise RuntimeError("mid-render failure")

    monkeypatch.setattr(cv2, "remap", boom)
    with pytest.raises(RuntimeError):
        coverloop.parallax(tmp_path / "p.png", out)
    assert out.read_bytes() == b"the old loop" and not list(tmp_path.glob("*.tmp.mp4"))


def test_the_gpu_endpoint_animates_the_cover_with_parallax(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient

    from crcontent import pipeline, web
    from test_lyric_cover_mode import _song, _wait

    song = _song(tmp_path, monkeypatch)
    _small(monkeypatch)
    monkeypatch.setattr(pipeline, "release_gpu", lambda: None)
    _picture(song / "background.png")
    (song / "thumbnail.jpg").write_bytes(b"thumb")
    c = TestClient(web.app)

    assert c.post("/api/lyricvideo/s/loop/gpu", json={"motion": "parallax", "use_cover": True, "intensity": 101}).status_code == 422
    r = c.post("/api/lyricvideo/s/loop/gpu", json={"motion": "parallax", "use_cover": True, "intensity": 70, "again": True})
    assert r.status_code == 200, r.text
    _wait(c, "/api/lyricvideo/s/loop/status")
    p = c.get("/api/lyricvideo/s/pictures").json()
    assert p["loop"] == "loop.mp4" and p["loop_motion"] == "parallax" and p["loop_intensity"] == 70
    assert p["loop_depth"] is False and len(_frames(song / "loop.mp4")) == 30
    assert (song / "thumbnail.jpg").read_bytes() == b"thumb"
    assert c.delete("/api/lyricvideo/s/loop").status_code == 200 and not (song / "loop.mp4").exists()


def _levels(path, levels, fps=30):
    out = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), fps, (64, 36))
    for v in levels:
        out.write(np.full((36, 64, 3), int(v), np.uint8))
    out.release()
    return path


def test_seam_check_passes_a_loop_and_catches_a_jump(tmp_path):
    from crcontent import coverloop

    round_trip = [100 + 60 * math.sin(2 * math.pi * i / 60) for i in range(60)]   # ends where it starts
    assert coverloop.seam(_levels(tmp_path / "ok.mp4", round_trip))["ok"]
    ramp = np.linspace(40, 200, 60)                                              # ends far from where it starts
    bad = coverloop.seam(_levels(tmp_path / "bad.mp4", ramp))
    assert not bad["ok"] and bad["jump"] > 100


def test_a_take_repeats_into_exactly_twelve_seconds(tmp_path):
    from crcontent import coverloop

    take = _levels(tmp_path / "take.mp4", np.linspace(40, 200, 97), fps=24)   # a 4 s take that ends somewhere else
    out = tmp_path / "loop.mp4"
    out.write_bytes(b"the old loop")
    coverloop.repeat(take, out, 12.0)
    cap = cv2.VideoCapture(str(out))
    assert (cap.get(cv2.CAP_PROP_FRAME_COUNT), cap.get(cv2.CAP_PROP_FPS), cap.get(cv2.CAP_PROP_FRAME_WIDTH)) == (360, 30, 1920)
    cap.release()
    assert coverloop.seam(out)["ok"] and not list(tmp_path.glob("*.once.mp4")) and not list(tmp_path.glob("*.tmp.mp4"))


def test_stabilize_undoes_the_camera_push_but_keeps_the_subject_moving(tmp_path):
    from crcontent import coverloop

    rng = np.random.default_rng(0)
    scene = cv2.GaussianBlur(rng.integers(0, 255, (180, 320, 3), dtype=np.uint8), (5, 5), 0)
    out = cv2.VideoWriter(str(tmp_path / "take.mp4"), cv2.VideoWriter_fourcc(*"mp4v"), 24, (320, 180))
    for i in range(24):   # the camera pushes in 15% while a white square slides along the bottom
        f = scene.copy()
        cv2.rectangle(f, (40 + 4 * i, 130), (60 + 4 * i, 150), (255, 255, 255), -1)
        out.write(cv2.warpAffine(f, cv2.getRotationMatrix2D((160, 90), 0, 1 + 0.15 * i / 23), (320, 180)))
    out.release()
    coverloop.stabilize(tmp_path / "take.mp4")
    f = _frames(tmp_path / "take.mp4")
    assert len(f) == 24 and not list(tmp_path.glob("*.still.mp4"))
    top = slice(10, 110)   # the background, away from the square
    assert np.abs(f[-1][top] - f[0][top]).mean() < 12                    # held still (unstabilised: ~60)
    assert f[-1][140, 40 + 4 * 23 + 10].min() > 180 and f[0][140, 50].min() > 180   # the square still moved


def test_composite_keeps_the_picture_sharp_and_only_the_moving_part_from_the_take(tmp_path, monkeypatch):
    from crcontent import coverloop

    monkeypatch.setattr(coverloop, "SIZE", (320, 180))
    still = tmp_path / "loop.png"
    y, x = np.mgrid[:180, :320]
    Image.fromarray((((x // 6 + y // 6) % 2) * 200 + 30).astype(np.uint8)).convert("RGB").save(still)   # detail a take blurs
    blurry = cv2.resize(cv2.resize(np.asarray(Image.open(still))[..., ::-1], (80, 45)), (128, 72))
    out = cv2.VideoWriter(str(tmp_path / "take.mp4"), cv2.VideoWriter_fourcc(*"mp4v"), 24, (128, 72))
    for i in range(24):   # the model's low-res redraw, with a white square moving in the bottom-left
        f = blurry.copy()
        cv2.rectangle(f, (8 + i, 50), (20 + i, 62), (255, 255, 255), -1)
        out.write(f)
    out.release()
    coverloop.composite(tmp_path / "take.mp4", still)
    f = _frames(tmp_path / "take.mp4")
    pic = np.asarray(Image.open(still))[..., ::-1].astype(np.int16)
    assert len(f) == 24 and f[0].shape == (180, 320, 3) and not list(tmp_path.glob("*.sharp.mp4"))
    up = cv2.resize(blurry, (320, 187))[3:183].astype(np.int16)        # what the take alone would give
    sharp, soft = np.abs(f[5][:60, 160:] - pic[:60, 160:]).mean(), np.abs(up[:60, 160:] - pic[:60, 160:]).mean()
    assert sharp < 15 and sharp < soft / 3                             # still part: the sharp original
    assert f[0][140, 40].min() > 180 and f[-1][140, 90].min() > 180   # the square still moves


def test_a_video_take_runs_in_its_own_process_and_reports_its_failure(tmp_path):
    from crcontent import videogen

    (tmp_path / "bad.png").write_bytes(b"not a picture")
    with pytest.raises(RuntimeError, match="cannot identify image"):   # the child's error, not a dead engine
        videogen.take(tmp_path / "bad.png", "she blinks", tmp_path / "raw.mp4")
    assert not (tmp_path / "raw.mp4").exists()


def _scene_take(path, morph):
    """A 4 s take of a still scene: a small square moving, or (morph) the whole picture dissolving into another."""
    rng = np.random.default_rng(3)
    a = cv2.resize(rng.integers(0, 255, (9, 16, 3), dtype=np.uint8), (128, 72), interpolation=cv2.INTER_CUBIC)
    b = 255 - a   # every pixel ends somewhere else
    out = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), 24, (128, 72))
    for i in range(24):
        f = cv2.addWeighted(a, 1 - i / 23, b, i / 23, 0) if morph else a.copy()
        if not morph:
            cv2.rectangle(f, (10 + i, 40), (22 + i, 52), (255, 255, 255), -1)
        out.write(f)
    out.release()


def test_a_take_that_redraws_the_scene_is_retried_and_the_best_kept(tmp_path, monkeypatch):
    from crcontent import coverloop, videogen

    seeds = []

    def take(still, prompt, out, seed=0, log=print, progress=None):
        seeds.append(seed)
        _scene_take(out, morph=len(seeds) < 3)   # the first two takes morph the whole scene

    monkeypatch.setattr(videogen, "take", take)
    seed, share = coverloop.best_take(tmp_path / "loop.png", "she blinks", tmp_path / "raw.mp4", 5, log=lambda t: None)
    assert len(seeds) == 3 and seeds[0] == 5 and seed == seeds[2]
    assert share <= coverloop.MAX_CHANGE and coverloop.changed(tmp_path / "raw.mp4") == share
    assert not list(tmp_path.glob("*.best.mp4"))

    seeds.clear()
    monkeypatch.setattr(videogen, "take", lambda still, prompt, out, seed=0, **k: seeds.append(seed) or _scene_take(out, True))
    seed, share = coverloop.best_take(tmp_path / "loop.png", "she blinks", tmp_path / "raw.mp4", 5, log=lambda t: None)
    assert len(seeds) == coverloop.TAKES and share > coverloop.MAX_CHANGE   # all bad: the least bad, reported


REGIONS = [{"kind": "rain", "box": [0.1, 0.05, 0.4, 0.4], "intensity": 60},
           {"kind": "sway", "box": [0.55, 0.1, 0.3, 0.4], "intensity": 80, "anchor": "top"},
           {"kind": "breathe", "box": [0.55, 0.5, 0.3, 0.45], "intensity": 60},
           {"kind": "blink", "box": [0.2, 0.6, 0.1, 0.05], "intensity": 100},
           {"kind": "flicker", "box": [0.35, 0.6, 0.1, 0.2], "intensity": 70},
           {"kind": "leaves", "box": [0.0, 0.0, 1.0, 1.0], "intensity": 50},
           {"kind": "steam", "box": [0.8, 0.6, 0.15, 0.3], "intensity": 50},
           {"kind": "protect", "box": [0.0, 0.8, 0.15, 0.2], "intensity": 0}]


def _textured(size=(320, 180)):
    w, h = size
    y, x = np.mgrid[:h, :w]
    return Image.fromarray(np.dstack([(x * 255 // w), (y * 255 // h), ((x // 8 + y // 8) % 2) * 160 + 40]).astype(np.uint8))


def test_living_regions_move_only_inside_their_box_and_loop_exactly():
    from crcontent import living

    f = living.frames(_textured(), REGIONS[:3], (320, 180), 12.0)
    base = np.asarray(_textured()).astype(int)
    assert np.abs(f(0).astype(int) - f(12.0).astype(int)).max() == 0          # the loop joins itself exactly
    mid = f(1.3).astype(int)
    assert np.abs(mid[10:60, 190:260] - base[10:60, 190:260]).mean() > 1     # swaying hair moved
    assert np.abs(mid[150:180, 0:20] - base[150:180, 0:20]).max() <= 1       # outside every box: untouched
    assert np.abs(f(0.4).astype(int)[12:70, 35:155] - f(0.9).astype(int)[12:70, 35:155]).mean() > 0.2   # rain falls


def test_protected_regions_never_change_and_bad_regions_are_refused():
    from crcontent import living

    f = living.frames(_textured(), REGIONS, (320, 180), 12.0)
    base = np.asarray(_textured()).astype(int)
    for t in (0.0, 3.6, 7.2):
        assert np.abs(f(t).astype(int)[150:176, 4:44] - base[150:176, 4:44]).max() <= 1   # the core of "protect"
    with pytest.raises(ValueError, match="Unknown kind"):
        living.clean([{"kind": "explode", "box": [0, 0, 1, 1]}])
    with pytest.raises(ValueError, match="too small"):
        living.clean([{"kind": "sway", "box": [0.5, 0.5, 0.001, 0.2]}])
    assert living.clean([{"kind": "sway", "box": [0.9, 0.9, 0.5, 0.5], "intensity": 400}])[0] == {
        "kind": "sway", "box": [0.9, 0.9, 0.1, 0.1], "intensity": 100, "anchor": "top"}


def test_the_living_loop_is_previewed_and_made_from_the_cover(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient

    from crcontent import coverloop, pipeline, web
    from test_lyric_cover_mode import _song, _wait

    song = _song(tmp_path, monkeypatch)
    monkeypatch.setattr(coverloop, "SIZE", (320, 180))
    monkeypatch.setattr(coverloop, "SECONDS", 2.0)
    monkeypatch.setattr(pipeline, "release_gpu", lambda: None)
    c = TestClient(web.app)
    assert c.post("/api/lyricvideo/s/loop/preview", json={"regions": REGIONS}).status_code == 400   # no cover yet
    _textured((640, 360)).save(song / "background.png")
    cover = (song / "background.png").read_bytes()
    assert c.post("/api/lyricvideo/s/loop/preview", json={"regions": [{"kind": "nope", "box": [0, 0, 1, 1]}]}).status_code == 400
    r = c.post("/api/lyricvideo/s/loop/preview", json={"regions": REGIONS})
    assert r.status_code == 200, r.text
    assert r.json()["preview"] == "loop.preview.mp4" and len(_frames(song / "loop.preview.mp4")) == 30
    assert len(c.get("/api/lyricvideo/s/pictures").json()["loop_regions"]) == len(REGIONS)

    assert c.post("/api/lyricvideo/s/loop/gpu", json={"motion": "living", "use_cover": True}).status_code == 200
    _wait(c, "/api/lyricvideo/s/loop/status")
    p = c.get("/api/lyricvideo/s/pictures").json()
    assert p["loop"] == "loop.mp4" and p["loop_motion"] == "living" and p["loop_seam"]["ok"]
    assert len(_frames(song / "loop.mp4")) == 60 and (song / "background.png").read_bytes() == cover


def test_nod_turns_the_head_about_the_neck_and_write_moves_the_hand():
    from crcontent import living

    base = np.asarray(_textured()).astype(int)
    nod = living.frames(_textured(), [{"kind": "nod", "box": [0.3, 0.1, 0.4, 0.6], "intensity": 100}], (320, 180), 12.0)
    f = nod(0.5).astype(int)   # a quarter of a nod: tilted most
    top, neck = (slice(32, 50), slice(130, 190)), (slice(110, 117), slice(150, 170))
    assert np.abs(f[top] - base[top]).mean() > 2 * np.abs(f[neck] - base[neck]).mean()   # the crown moves, the neck holds
    write = living.frames(_textured(), [{"kind": "write", "box": [0.4, 0.5, 0.2, 0.3], "intensity": 100}], (320, 180), 12.0)
    hand = (slice(100, 140), slice(140, 180))
    assert np.abs(write(0.25).astype(int)[hand] - base[hand]).mean() > 1
    assert np.abs(write(0).astype(int) - write(12.0).astype(int)).max() == 0
