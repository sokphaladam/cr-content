import shutil
from pathlib import Path

import pytest

import make_song
from neonmekong import ai, config

FIX = Path(__file__).parent / "fixtures" / "songs" / "demo-song"


@pytest.fixture
def song(tmp_path):
    dest = tmp_path / "demo-song"
    shutil.copytree(FIX, dest)
    assert make_song.main(["--dry-run", "analyze", str(dest)]) == 0
    return dest


class FakeResponse:
    def __init__(self, body=None):
        self.body = body or {"candidates": [{"content": {"parts": [{"text": '{"hook": "H.", "pinned_comment": "Q?"}'}]},
                                             "finishReason": "STOP"}]}

    def raise_for_status(self):
        pass

    def json(self):
        return self.body


def test_gemini_reads_key_from_project_env_only(song, tmp_path, monkeypatch):
    (tmp_path / ".env").write_text("GEMINI_API_KEY=from-dotenv\nGEMINI_MODEL=my-model\n", encoding="utf-8")
    monkeypatch.setattr(config, "ROOT", tmp_path)
    monkeypatch.setenv("GEMINI_API_KEY", "from-system")          # must be ignored
    monkeypatch.setenv("ANTHROPIC_API_KEY", "never-used")
    seen = {}

    def fake_post(url, **kw):
        seen.update(url=url, **kw)
        return FakeResponse()
    monkeypatch.setattr("requests.post", fake_post)

    assert make_song.main(["text", str(song), "--ai", "gemini"]) == 0
    assert seen["url"] == "https://generativelanguage.googleapis.com/v1beta/models/my-model:generateContent"
    assert seen["headers"]["x-goog-api-key"] == "from-dotenv"
    assert seen["json"]["generationConfig"]["maxOutputTokens"] == 500
    assert seen["json"]["contents"][0]["parts"][0]["text"]
    text = (song / "upload.txt").read_text(encoding="utf-8")
    assert "H." in text and "Q?" in text and "Nostalgic Disco Love Song" in text
    assert (song / "ai_cache.json").exists()

    seen.clear()                                                 # second run: cached, no call
    assert make_song.main(["text", str(song), "--ai", "gemini"]) == 0
    assert not seen


def test_gemini_default_model_blocked_reply_and_missing_key(song, tmp_path, monkeypatch):
    (tmp_path / ".env").write_text("GEMINI_API_KEY=k\n", encoding="utf-8")
    monkeypatch.setattr(config, "ROOT", tmp_path)
    seen = {}
    monkeypatch.setattr("requests.post", lambda url, **kw: seen.update(url=url) or FakeResponse())
    ai._call_gemini("hi")
    assert ai.GEMINI_MODEL in seen["url"]

    blocked = FakeResponse({"promptFeedback": {"blockReason": "SAFETY"}})
    monkeypatch.setattr("requests.post", lambda url, **kw: blocked)
    with pytest.raises(RuntimeError, match="SAFETY"):
        ai._call_gemini("hi")

    (tmp_path / ".env").write_text("", encoding="utf-8")       # no key: warn, use the free template
    assert make_song.main(["text", str(song), "--ai", "gemini", "--refresh"]) == 0
    assert "Nostalgic Disco Love Song" in (song / "upload.txt").read_text(encoding="utf-8")


def test_gemini_dry_run_makes_no_request(song, monkeypatch):
    monkeypatch.setattr("requests.post", lambda *a, **k: pytest.fail("network call in dry-run"))
    assert make_song.main(["--dry-run", "text", str(song), "--ai", "gemini"]) == 0
    assert not (song / "ai_cache.json").exists()


def test_claude_mode_is_gone(song):
    with pytest.raises(SystemExit):
        make_song.main(["text", str(song), "--ai", "claude"])
