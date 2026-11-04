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


def _words(text):
    from crcontent.tts import Word
    return [Word(w, i * 0.3, i * 0.3 + 0.25) for i, w in enumerate(text.split())]


def test_facts_finds_the_numbers_the_voice_says():
    found = [(shown, value, unit) for _, _, shown, value, unit in
             shorts_gfx.facts(_words("They live four hundred years, grow 1 centimeter a year and one of the 2 million"))]
    assert found == [("400", 400, "YEARS"), ("1", 1, "CENTIMETER"), ("2 MILLION", None, "")]


def test_attention_traps():
    tl = Timeline([Slot(1, 0.0, 2.0, 0, "a", 1.8), Slot(2, 2.0, 3.0, 2, "b", 2.6), Slot(3, 5.0, 3.0, 2, "c", 2.6)],
                  [], 8.0)
    ev = "\n".join(shorts_gfx.events(["facts", "teaser", "chapters", "callout"], tl,
                                     {2: _words("it lives 400 years")}, focus=[None, (0.5, 0.4), None]))
    assert "400 YEARS" not in ev and "400\\N" in ev and "{\\fs64" in ev   # the number counts up, then its unit
    assert "WAIT FOR THE END" in ev and "HERE IT IS" in ev
    assert all(f"{k}/3" in ev for k in (1, 2, 3))
    assert ev.count("fscx170") == 1                                      # the one beat with a subject, not the hook


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
