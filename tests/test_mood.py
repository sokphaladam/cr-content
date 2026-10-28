import numpy as np

from neonmekong import mood


def test_pick_falls_back():
    assert mood.pick("karaoke", mood.LYRIC_STYLES, "classic") == "karaoke"
    assert mood.pick("nope", mood.LYRIC_STYLES, "classic") == "classic"


def test_every_grade_keeps_the_frame_shape():
    for name in mood.GRADES:
        f = np.full((90, 160, 3), 120, np.uint8)
        out = mood.Grader(name, (160, 90)).grade(f.copy(), 1.0, 0.5)
        assert out.shape == f.shape and out.dtype == np.uint8
    assert (mood.Grader("neon", (160, 90)).grade(f.copy(), 0, 0) == f).all()
    assert mood.Grader("cinema", (160, 90)).grade(f.copy(), 0, 0)[0].sum() == 0  # letterbox bar


def test_karaoke_fill_runs_row_by_row():
    sp = {"pm": np.zeros((20, 10, 3), np.float32), "a": np.zeros((20, 10, 1), np.float32),
          "glow": np.zeros((20, 10, 3), np.float32), "w": 10, "h": 20}
    rows = [(0, 10, 0, 10), (10, 20, 0, 10)]
    assert mood.cut(sp, rows, 0.0) == []
    parts = mood.cut(sp, rows, 0.75)
    assert [p["w"] for p, _, _ in parts] == [10, 5]
    assert abs(mood.fill_fraction(5, 0, 10) - 0.505) < 1e-9 and mood.fill_fraction(0, 0, 0) == 1.0


def test_kinetic_pop_lands_then_settles():
    assert mood.pop_scale(9.9, 10.0, 0.0, False) > 1.2
    assert mood.pop_scale(12.0, 10.0, 0.0, False) == 1.0


def test_beat_effect_levels_parts_and_suggestion():
    assert mood.pulse_settings({}) == (0.035, 0.006, frozenset({"light", "zoom", "glow"}), "always")
    assert mood.pulse_settings({"beat_pulse": "off"})[2] == frozenset()
    light, zoom, parts, when = mood.pulse_settings({"beat_pulse": "strong", "pulse_parts": "zoom, bogus", "pulse_when": "chorus"})
    assert (light, zoom, parts, when) == (0.12, 0.02, frozenset({"zoom"}), "chorus")
    assert mood.pulse_settings({"beat_pulse": "x", "pulse_parts": "none"})[2] == frozenset()
    assert mood.suggest({"mood_phrase": "ambient piano"})["pulse"] == "off"
    assert mood.suggest({"mood_phrase": "club edm dance"})["pulse"] == "strong"
    assert mood.suggest({"mood_phrase": "dreamy"})["pulse"] == "subtle"


def test_the_scene_beats_only_where_the_song_says():
    from neonmekong import lyricvideo as lv
    base = {"title": "T", "sections": [{"kind": "verse", "start": 0, "end": 10}, {"kind": "chorus", "start": 10, "end": 20}]}
    v = lv.Variant("full", None, [], [1.0, 11.0], None, 30.0)
    def beat(over, t):
        return lv.Scene({**base, **over}, v, [], (320, 180), 15)._beat(t)
    assert beat({}, 1.0)[0] > 0 and beat({"beat_pulse": "off"}, 1.0) == (0.0, 0.0, 0.0, 0.0)
    assert beat({"pulse_when": "chorus"}, 1.0) == (0.0, 0.0, 0.0, 0.0) and beat({"pulse_when": "chorus"}, 11.0)[0] > 0
    light, push, glow, _ = beat({"pulse_parts": "zoom"}, 1.0)
    assert light == 0.0 and push > 0 and glow == 0.0
