"""Remotion graphics: when each one shows, the lengths and places they're made from, and the fallback."""
import json
from types import SimpleNamespace as N

from crcontent.shorts import graphics, motion
from crcontent.tts import Word

TL = N(slots=[N(scene=1, start=0, end=5), N(scene=2, start=5, end=10)], total=10)
WORDS = {1: [Word("lives", 1.0, 1.3), Word("400", 1.4, 1.9), Word("years", 1.9, 2.3), Word("in", 2.3, 2.4),
             Word("Greenland.", 2.4, 3.0)],
         2: [Word("about", 0.2, 0.5), Word("6", 0.6, 0.9), Word("metres", 0.9, 1.4)]}


def test_facts_and_sizes_follow_the_fact_schedule():
    got = motion.plan(TL, WORDS, "", ["facts_remotion", "size_compare"], lambda k: f"photo{k}")
    assert [(c["id"], c["at"]) for c in got] == [("Fact", 1.4), ("SizeCompare", 5.6)]
    size = got[1]["props"]
    assert (size["metres"], size["shown"], size["unit"], size["photo"]) == (6.0, "6", "METRES", "photo1")
    assert got[0]["props"]["y"] == graphics.FACT_Y
    assert graphics.events(["facts_remotion", "size_compare", "map_zoom"], TL, WORDS) == []  # nothing in the ASS layer


def test_lengths():
    assert motion.metres("6", "METRES") == 6 and motion.metres("10", "FEET") == 3.048
    assert motion.metres("400", "YEARS") is None and motion.metres("2 MILLION", "METRES") is None
    assert motion.metres("5000", "KM") is None and motion.metres("900", "METRES") is None  # beyond any comparison


def test_the_map_waits_for_its_word_and_graphics_never_overlap(tmp_path):
    text = " ".join(w.text for s in (1, 2) for w in WORDS[s])
    import hashlib

    (tmp_path / "map.json").write_text(json.dumps({  # what Gemini said, cached
        "key": hashlib.sha1(text.encode()).hexdigest()[:16], "found": True, "place": "Greenland", "lat": 72,
        "lon": -40, "zoom": "country", "words": "Greenland"}))
    where = motion.place(tmp_path, TL, WORDS)
    assert where == {"place": "Greenland", "lat": 72, "lon": -40, "zoom": "country", "at": 2.4}
    got = motion.plan(TL, WORDS, "", ["facts_remotion", "map_zoom"], where=where)
    # the map starts while the 400 pop-up is still up (1.4-3.4 s): left out rather than covering it
    assert [c["id"] for c in got] == ["Fact", "Fact"]
    got = motion.plan(TL, WORDS, "", ["map_zoom", "size_compare"], where=where)
    assert [(c["id"], c["at"]) for c in got] == [("MapZoom", 2.4), ("SizeCompare", 5.6)]


def test_built_in_pop_ups_stay_clear_of_remotion_ones():
    assert graphics.events(["facts"], TL, WORDS, busy=[(5.0, 9.0)])  # 400 YEARS still pops
    assert len(graphics.events(["facts"], TL, WORDS, busy=[(0, 10)])) == 0


def test_no_remotion_falls_back(monkeypatch, tmp_path):
    monkeypatch.setattr(motion, "PROJECT", tmp_path / "missing")
    logged = []
    assert motion.overlay(tmp_path, "picture.mkv", motion.plan(TL, WORDS, "", ["facts_remotion"]), logged.append) is None
    assert "npm install" in logged[0]
