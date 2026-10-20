from pathlib import Path
from types import SimpleNamespace

import pytest

from crcontent.highlights import clip
from crcontent.highlights.clip import TITLE_MAX, upload_text

AI = {"title": "When she only wants a trial run 🚗💔", "line": "Some people only want a trial run.",
      "question": "Have you ever been someone's test drive?", "hashtags": ["synthpop", "retrowave", "newmusic"],
      "comment": "Be honest: have you been someone's test drive? 🚗"}


@pytest.fixture
def src(monkeypatch):
    monkeypatch.setattr(clip, "full_song", lambda s: ("Neon Mekong", "https://youtu.be/4-2-IssEJKE"))
    return SimpleNamespace(title="She Test Drive", artist="", video=Path("x/video.mp4"))


CAND = SimpleNamespace(lyrics=["She test drive my heart tonight", "and never stays"])


def test_hook_first_title_with_the_song_name(src):
    up = upload_text(src, CAND, AI, ai_credit=True)
    assert up["title"] == "When she only wants a trial run 🚗💔 | She Test Drive"
    assert len(up["title"]) <= TITLE_MAX


def test_song_name_dropped_when_too_long(src):
    long = {**AI, "title": "When she only wants a trial run and never the whole ride"}
    assert upload_text(src, CAND, long, False)["title"] == long["title"]


def test_description_layout(src):
    up = upload_text(src, CAND, AI, ai_credit=True)
    assert up["description"] == (
        "Some people only want a trial run.\nHave you ever been someone's test drive?\n\n"
        "🎧 Full song: https://youtu.be/4-2-IssEJKE\n\nMusic and vocals are AI-generated.")
    assert up["hashtags"][:2] == ["NeonMekong", "SheTestDrive"]  # song and artist always tagged
    assert up["comment"] == AI["comment"]


def test_no_ai_credit_when_the_song_has_none(src):
    assert "AI-generated" not in upload_text(src, CAND, AI, ai_credit=False)["description"]


def test_without_the_judge(src, monkeypatch):
    monkeypatch.setattr(clip, "full_song", lambda s: ("", ""))
    up = upload_text(src, CAND, None, False)
    assert up["title"] == "She Test Drive"
    assert up["description"].startswith("♪ She test drive my heart tonight")
    assert '🎧 Full song: "She Test Drive", on the channel' in up["description"]
    assert up["comment"] == ""
