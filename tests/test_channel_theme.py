"""Channel-branded visual system: profile caption themes, headline/hook colours in the ASS render, legacy drafts."""
from crcontent import captions, drafts, profiles, styles
from crcontent.config import LANGS
from crcontent.styles import CaptionStyle, ass_color
from tests.test_director_plan import PASTED, client  # noqa: F401  (client is a fixture)

HISTORY, WILDLIFE = profiles.PROFILES["hidden_history_files"], profiles.PROFILES["wildlife_facts"]


def test_profile_themes():
    w = profiles.theme_captions(WILDLIFE, "en")
    assert (w.color, w.highlight, w.keyword, w.size) == ("#F8FAFC", "#FFC857", "#42C7D9", "l")
    h = profiles.theme_captions(HISTORY, "en")
    assert (h.color, h.highlight, h.keyword, h.headline_color, h.hook_fill) == \
        ("#D6C9AC", "#B99A60", "#76AFA7", "#F0E8D8", "#B99A60")
    assert HISTORY.headline_font_preferences[0] == "Bebas Neue" and WILDLIFE.headline_font_preferences[0] == "Anton"
    assert profiles.theme_captions(None, "en") == CaptionStyle()


def test_fonts_fall_back_safely(monkeypatch):
    monkeypatch.setattr(profiles, "available_fonts", lambda lang: ["Montserrat", "Bebas Neue"])
    monkeypatch.setattr(styles, "available_fonts", lambda lang: ["Montserrat", "Bebas Neue"])
    h = profiles.theme_captions(HISTORY, "en")
    assert (h.font, h.headline_font) == ("Montserrat", "Bebas Neue")  # Inter / missing: next installed one
    monkeypatch.setattr(profiles, "available_fonts", lambda lang: ["Khmer OS Battambang"])
    monkeypatch.setattr(styles, "available_fonts", lambda lang: ["Khmer OS Battambang"])
    k = profiles.theme_captions(HISTORY, "km")
    assert (k.font, k.headline_font) == ("", "")  # the language's own font, never a Latin brand face


def test_bad_profile_values_never_crash():
    odd = WILDLIFE.model_copy(update={"caption_defaults": {"size": "huge", "bogus": 1, "headline_color": "red"}})
    s = profiles.theme_captions(odd, "en")
    assert s.size == "m" and s.headline_color == "#FFFFFF"


def test_old_caption_json_loads_with_general_headlines():
    old = {"preset": "classic", "color": "#F8FAFC", "highlight": "#FACC15", "keyword": "#38BDF8"}
    s = CaptionStyle.model_validate(old)
    assert (s.headline_font, s.headline_color, s.headline_background, s.hook_fill) == ("", "#FFFFFF", "#000000", "#FFFFFF")


def test_general_ass_is_unchanged():
    ass = captions.caption_styles(LANGS["en"], CaptionStyle().clean("en"))
    assert ",&H00FFFFFF&,&H00FFFFFF&,&HFF000000&,&H1A000000&," in ass.splitlines()[1]  # white on ~90% black


def test_theme_reaches_ass_headline_and_hook():
    style = profiles.theme_captions(HISTORY, "en")
    ass = captions.caption_styles(LANGS["en"], style)
    head = ass.splitlines()[1]
    assert ass_color("#F0E8D8") in head and ass_color("#101419", 0x1A) in head
    hook = captions._hook_events("A HOOK", 0, 2, 200, "Arial", 90, "en", fill=style.hook_fill)
    assert f"\\1c&H{ass_color('#B99A60')[4:]}" in hook[1]  # the card in the accent
    words = [type("W", (), {"text": t, "start": i * 0.3, "end": i * 0.3 + 0.3})() for i, t in enumerate(["old", "map"])]
    full = captions.build_ass([(0, 1, words, "Hook", {"map"})], LANGS["en"], style)
    assert "Style: Hook," in full and ass_color("#141414") in full.split("Style: Hook,")[1].splitlines()[0]  # dark ink
    assert ass_color("#B99A60") in full and ass_color("#76AFA7") in full  # spoken word + keyword


def test_new_projects_take_their_channel_theme(client):  # noqa: F811
    for pid, highlight in (("hidden_history_files", "#B99A60"), ("wildlife_facts", "#FFC857"), ("", "#FACC15")):
        r = client.post("/api/script-video", json={"text": PASTED, "format": "short", "channel_profile_id": pid})
        assert r.status_code == 200, r.text
        assert drafts.load(r.json()["id"]).script.captions.highlight == highlight
