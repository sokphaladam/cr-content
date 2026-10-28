import shutil
from datetime import date
from pathlib import Path

import pytest

import make_song
from neonmekong import ai, config, schedule_week

FIX = Path(__file__).parent / "fixtures" / "songs" / "demo-song"


@pytest.fixture
def song(tmp_path):
    dest = tmp_path / "demo-song"
    shutil.copytree(FIX, dest)
    assert make_song.main(["--dry-run", "analyze", str(dest)]) == 0
    return dest


def test_template_text(song):
    assert make_song.main(["--dry-run", "text", str(song)]) == 0
    text = (song / "upload.txt").read_text(encoding="utf-8")
    assert "Nostalgic Disco Love Song – Demo Song (Lyric Video)" in text
    assert "@neonmekong.music" in text and "Neon Nostalgia: Disco Love Songs" in text
    assert "[Chorus]\nReplay, replay the night again" in text and "#NeonMekong" in text
    assert not (song / "ai_cache.json").exists()


def test_checklist(song):
    assert make_song.main(["checklist", str(song)]) == 0
    md = (song / "checklist.md").read_text(encoding="utf-8")
    assert "vocals start at 12s" in md and "Reel posted" in md and "Set plan and generated_on" in md


def test_existing_upload_txt_backed_up(song):
    (song / "upload.txt").write_text("mine", encoding="utf-8")
    assert make_song.main(["text", str(song)]) == 0
    assert any(p.read_text(encoding="utf-8") == "mine" for p in song.glob("upload.txt.bak-*"))


def test_dry_run_ai_makes_no_calls(song, monkeypatch):
    def boom(*a, **k):
        raise AssertionError("AI called in dry-run")
    monkeypatch.setattr(ai, "BACKENDS", {"local": boom, "gemini": boom})
    assert make_song.main(["--dry-run", "text", str(song), "--ai", "gemini"]) == 0
    assert not (song / "ai_cache.json").exists()


def test_ai_cache_and_refresh(song, monkeypatch):
    calls = []

    def fake(text, model=None):
        calls.append(text)
        return '```json\n{"hook": "Hook sentence.", "pinned_comment": "Pinned Q?"}\n```'
    monkeypatch.setattr(ai, "BACKENDS", {"local": fake, "gemini": fake})
    for extra in ([], [], ["--refresh"]):
        assert make_song.main(["text", str(song), "--ai", "gemini", *extra]) == 0
    assert len(calls) == 2  # second run came from ai_cache.json
    text = (song / "upload.txt").read_text(encoding="utf-8")
    assert "Hook sentence." in text and "Pinned Q?" in text and "Nostalgic Disco Love Song" in text  # title stays a template
    assert (song / "ai_cache.json").exists()


def test_ai_failure_falls_back_to_template(song, monkeypatch):
    def broken(text, model=None):
        raise RuntimeError("no key")
    monkeypatch.setattr(ai, "BACKENDS", {"local": broken, "gemini": broken})
    assert make_song.main(["text", str(song), "--ai", "gemini"]) == 0
    assert "Nostalgic Disco Love Song" in (song / "upload.txt").read_text(encoding="utf-8")


def test_weekly_schedule():
    rows = schedule_week.plan(["A", "B"], date(2026, 10, 26))  # a Monday
    assert [(d.strftime("%a"), k[:5], t) for d, k, t in rows] == [
        ("Mon", "Short", "A"), ("Tue", "Lyric", "A"), ("Wed", "Short", "A"), ("Thu", "Short", "A"),
        ("Fri", "Lyric", "B"), ("Sat", "Short", "B")]
    assert schedule_week.next_monday(date(2026, 10, 23)).weekday() == 0
