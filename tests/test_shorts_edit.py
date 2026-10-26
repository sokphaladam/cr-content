import pytest

from crcontent.shorts import captions, edit, match, preflight
from test_shorts_output import _short


def test_edit_defaults_and_validation(tmp_path):
    assert edit.load(tmp_path) == {"look": "", "caption": "classic", "transition": "cut", "graphics": []}
    assert edit.save(tmp_path, {"look": "moody", "transition": "dip"}) == {"look": "moody", "caption": "classic",
                                                                          "transition": "dip", "graphics": []}
    assert edit.load(tmp_path)["look"] == "moody"
    with pytest.raises(ValueError):
        edit.save(tmp_path, {"caption": "comic-sans"})
    (tmp_path / "edit.json").write_text('{"look": "nope"}')  # an unknown saved name falls back to the default
    assert edit.load(tmp_path)["look"] == ""


def test_cut_filter_only_for_effects():
    assert edit.cut_filter([1.0], "cut") == ""
    assert edit.cut_filter([1.0, 2.0], "flash").count("eq=") == 2
    assert "between(t,0.900,1.100)" in edit.cut_filter([1.0], "dip")


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
