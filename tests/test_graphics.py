from crcontent.longform.timing import Slot, Timeline
from crcontent.shorts import captions, edit, graphics as shorts_gfx

PAL = [(255, 79, 163), (57, 213, 224), (255, 181, 71), (120, 80, 255)]


def _tl():
    return Timeline([Slot(1, 0.0, 2.0, 0, "a.mp3", 1.8), Slot(2, 2.0, 3.0, 2, "b.mp3", 2.6)], [], 5.0)


def test_short_graphics_are_ass_events_per_cut():
    ev = shorts_gfx.events(["progress", "burst", "sweep", "brackets", "nope"], _tl())
    text = "\n".join(ev)
    assert text.count("Gfx") == len(ev) and "fscx100" in text      # the bar fills over the whole Short
    assert text.count("3a&HFF&") == 4                               # two rings on each beat
    assert text.count("move(-200") == 1                             # a sweep on every cut but the first frame
    assert shorts_gfx.events([], _tl()) == []


def test_edit_keeps_only_known_graphics(tmp_path):
    assert edit.save(tmp_path, {"graphics": ["burst", "burst", "progress"]})["graphics"] == ["burst", "progress"]
    import pytest
    with pytest.raises(ValueError):
        edit.save(tmp_path, {"graphics": ["confetti"]})
    assert edit.load(tmp_path)["graphics"] == ["burst", "progress"]


def test_captions_carry_the_graphics_layer():
    from test_shorts_output import _short
    script, tl, words = _short()
    ass = captions.build(script, tl, words, "classic", ["burst"])
    assert "Style: Gfx" in ass and "Dialogue: 0," in ass
    assert "Style: Gfx" not in captions.build(script, tl, words)
