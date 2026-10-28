import pytest

from crcontent.shorts import captions, edit, match, preflight
from test_shorts_output import _short


def test_edit_defaults_and_validation(tmp_path):
    assert edit.load(tmp_path) == edit.DEFAULT
    assert edit.save(tmp_path, {"look": "moody", "transition": "dip"}) == {**edit.DEFAULT, "look": "moody",
                                                                          "transition": "dip"}
    assert edit.load(tmp_path)["look"] == "moody"
    with pytest.raises(ValueError):
        edit.save(tmp_path, {"caption": "comic-sans"})
    (tmp_path / "edit.json").write_text('{"look": "nope"}')  # an unknown saved name falls back to the default
    assert edit.load(tmp_path)["look"] == ""


def test_per_beat_edits_and_sliders(tmp_path):
    saved = edit.save(tmp_path, {"look": "teal", "transition": "cut", "caption_size": 1.2, "push": False,
                                 "beats": {"3": {"look": "noir", "transition": "glitch"}, "4": {"look": ""}}})
    assert saved["beats"] == {"3": {"look": "noir", "transition": "glitch"}}   # "" = as the Short: not kept
    assert edit.for_beat(saved, 3, "look") == "noir" and edit.for_beat(saved, 2, "look") == "teal"
    assert edit.load(tmp_path)["caption_size"] == 1.2 and edit.load(tmp_path)["push"] is False
    with pytest.raises(ValueError):
        edit.save(tmp_path, {"beats": {"2": {"transition": "spin"}}})
    with pytest.raises(ValueError):
        edit.save(tmp_path, {"caption_y": 0.95})   # into the bottom 20% the apps draw over
    edit.save(tmp_path, {"voice": "en-US-AvaNeural"})   # the narrator is set by shorts.set_voice (it re-voices)
    assert edit.load(tmp_path)["voice"] == ""


def test_cut_filter_only_for_effects():
    assert edit.cut_filter([1.0], "cut") == ""
    assert edit.cut_filter([1.0, 2.0], "flash").count("eq=") == 2
    assert "between(t,0.900,1.100)" in edit.cut_filter([1.0], "dip")
    each = edit.cut_filter([1.0, 2.0, 3.0], ["cut", "glitch", "blur"])   # one per cut
    assert "rgbashift" in each and "between(t,2.000" in each and "gblur" in each and "1.000" not in each


def test_caption_size_and_height(tmp_path):
    script, tl, words = _short()
    ass = captions.build(script, tl, words, "classic", (), 1.2, 0.5)
    assert f",{round(captions.CAPTION_PX * 1.2)}," in ass and f"\\pos({captions.CX},960)" in ass


@pytest.mark.parametrize("style", sorted(captions.STYLES))
def test_caption_styles_colour_the_spoken_word(style):
    script, tl, words = _short()
    ass = captions.build(script, tl, words, style)
    assert captions.STYLES[style]["hi"] in ass
    assert f",{captions.STYLES[style]['px']}," in ass  # the Caption style line carries the look's size


def test_judge_evidence_and_object_chips():
    m = {"score": 4, "objects_seen": ["water", "sand"], "missing": ["towel"]}
    assert match.evidence(m) == {"objects_seen": ["water", "sand"], "missing": ["towel"]}
    ent = {"match": 4, "chosen": {**match.evidence(m)}, "search": {"plan": {"key_objects": ["water", "towel"]}}}
    html = preflight._objects_html(ent)
    assert "✓ water" in html and "✗ towel" in html and "sand" in html and 'width:40%' in html
    assert preflight._objects_html({"match": None, "chosen": {}}) == ""
