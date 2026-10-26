import time

import numpy as np
from PIL import Image

from neonmekong import mood, overlays


def test_neon_name_drops_the_post_title_extras():
    assert overlays.neon_name("Signal Lost - Song About Losing Connection (Official Lyric Video)") == "Signal Lost"
    assert overlays.neon_name("Replay") == "Replay"


def test_neon_intro_only_when_the_singing_starts_later():
    assert overlays.intro_span(0.2) is None            # trimmed video / chorus preview: sung at once
    assert overlays.intro_span(34.0) == (0.6, 5.5)     # a long intro: until the default end
    assert overlays.intro_span(4.0) == (0.6, 3.7)      # gone 0.3 s before the first line
    assert overlays.intro_span(2.0) is None            # too short to show
    assert overlays.intro_span(None) == (0.6, 5.5)
    assert overlays.intro_span(2.5) is None            # would run over the first line


def test_neon_sign_flickers_then_holds_then_fades():
    on, off = 0.6, 5.5
    assert overlays.neon_gain(0.3, on, off) == 0 and overlays.neon_gain(6.0, on, off) == 0
    assert overlays.neon_gain(0.62, on, off) > 0.4     # first burst
    assert overlays.neon_gain(0.75, on, off) == 0.1    # dark tube between bursts
    assert overlays.neon_gain(3.0, on, off) > 0.9      # steady
    assert 0 < overlays.neon_gain(5.3, on, off) < 0.5  # fading


def test_suggestion_reads_the_mood_and_genre():
    s = mood.suggest({"mood_phrase": "Melancholic", "genre": "synthwave", "scene_theme": ""})
    assert s["grade"] in mood.GRADES and s["style"] in mood.LYRIC_STYLES and "synthwave" in s["reason"]
    assert mood.suggest({})["grade"] == mood.DEFAULT_GRADE
    assert mood.suggest({"mood_phrase": "hazy trippy", "genre": "psych"})["grade"] == "dream"


def test_every_grade_is_drawn():
    for name in mood.GRADES:
        out = mood.Grader(name, (160, 90)).grade(np.full((90, 160, 3), 128, np.uint8), 0.5, 0.3)
        assert out.shape == (90, 160, 3) and out.dtype == np.uint8


def test_a_picture_draw_reports_its_steps(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient

    from crcontent import imagegen, lyricvideo, pipeline, web

    song = tmp_path / "s"
    (song / "out").mkdir(parents=True)
    (song / "song.json").write_text('{"title": "T", "sections": [{"tag": "Verse", "kind": "verse", "start": 1, "end": 9}]}')
    (song / "lyrics.lrc").write_text("[00:02.00]hello\n")
    (song / "suno.txt").write_text("x")
    monkeypatch.setattr(lyricvideo, "SONGS_DIR", tmp_path)
    monkeypatch.setattr(web, "_art_check", lambda style: None)
    made = tmp_path / "made.png"
    Image.new("RGB", (64, 36), (9, 9, 9)).save(made)

    def fake(prompt, style, size, seed=None, subject="", avoid="", log=print):
        log("loading the cinematic model onto the GPU")
        for phase in ("drawing", "detail"):
            imagegen._phase = phase
            for i in range(3):
                imagegen._report(i + 1, 3)
                time.sleep(0.05)
        return made, 1, None, ""

    monkeypatch.setattr(pipeline, "draw_checked", fake)
    c = TestClient(web.app)
    assert c.post("/api/lyricvideo/s/pictures/cover/draw", json={"prompt": "a sky", "style": "cinematic"}).json() == {"started": "cover"}
    seen = set()
    for _ in range(80):
        st = c.get("/api/lyricvideo/s/pictures/draw-status").json()
        seen.add(st["phase"])
        if st["state"] != "running":
            break
        time.sleep(0.05)
    assert st["state"] == "done" and {"drawing", "detail"} <= seen
    assert (song / "background.png").exists()
