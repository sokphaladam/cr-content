"""The four agreed cuts in Gemini calls: Shorts footage checks, picture checks, highlights judge, analytics tags."""
import pytest

from crcontent import pipeline
from crcontent.highlights import settings as highlights_settings
from crcontent.shorts import analytics, footage, match
from crcontent.shorts import settings as shorts_settings


def picker(mode):
    p = object.__new__(footage.Picker)
    p.cfg = {"footage": {"check": mode}} if mode else {}
    return p


@pytest.mark.parametrize("mode,hook,other", [("hook", True, False), ("all", True, True), ("off", False, False)])
def test_footage_check_modes(mode, hook, other):
    p = picker(mode)
    assert p.checks(True) is hook and p.checks(False) is other


def test_footage_check_defaults_to_every_beat():
    """Hook-only let a praying mantis stand in for a mantis shrimp on beats 2-4, so every beat is checked."""
    assert shorts_settings.DEFAULTS["footage"]["check"] == "all"
    assert picker(None).checks(True) and picker(None).checks(False)


def test_unchecked_clip_passes_centred_and_never_trips_the_hook_rules():
    m = match.unchecked()
    assert m["score"] == match.PASS and (m["x"], m["y"]) == (0.5, 0.5) and not m["missing"]
    from crcontent.shorts import hook
    s = hook.Scan.__new__(hook.Scan)
    s.reject = ""
    assert hook.judged(s, m).reject == ""   # no animal / logo / intro / motion verdict against it


def test_own_clip_not_checked_returns_without_calling_gemini(tmp_path, monkeypatch):
    clip = tmp_path / "scene-01.jpg"
    clip.write_bytes(b"x")
    monkeypatch.setattr(match, "check", lambda *a, **k: pytest.fail("Gemini called"))
    chosen, flags, score = footage.own_pick(clip, 2.0, False, "cat", {"shot": "s", "key_objects": []}, check=False)
    assert chosen["source"] == "own" and score is None


def test_picture_check_is_off_unless_asked(monkeypatch):
    monkeypatch.delenv("PICTURE_CHECK", raising=False)
    assert pipeline.picture_check_on() is False
    for value in ("1", "true", "YES", "on"):
        monkeypatch.setenv("PICTURE_CHECK", value)
        assert pipeline.picture_check_on() is True
    monkeypatch.setenv("PICTURE_CHECK", "0")
    assert pipeline.picture_check_on() is False


def test_highlights_judge_defaults_off():
    assert highlights_settings.DEFAULTS["ai_judge"]["enabled"] is False


def videos():
    return [analytics.Video(**{**{f: "" for f in analytics.Video.__dataclass_fields__}, "title": "Why cats purr, explained",
                               "seconds": 20, "views": 5})]


def test_analytics_uses_keyword_rules_without_calling_gemini(monkeypatch):
    monkeypatch.setattr("crcontent.script.make_client", lambda: pytest.fail("Gemini called"))
    monkeypatch.setattr(shorts_settings, "load", lambda: shorts_settings.DEFAULTS)
    vs = videos()
    analytics.tag(vs, log=lambda *_: None)
    assert vs[0].hook_style == "science explainer"


def test_analytics_asks_gemini_when_switched_on(monkeypatch):
    called = []

    def fake_client():
        called.append(1)
        raise RuntimeError("stop here")   # falls back to the keyword rules, as when Gemini is unavailable
    monkeypatch.setattr("crcontent.script.make_client", fake_client)
    vs = videos()
    analytics.tag(vs, log=lambda *_: None, ai=True)
    assert called and vs[0].hook_style == "science explainer"
