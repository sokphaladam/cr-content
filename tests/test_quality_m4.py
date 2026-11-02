"""Milestone 4: configurable rules, caption speed, lyric sync against the vocal stem, AI story review, rights."""
import json
import shutil
import subprocess
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from crcontent import quality, quality_preview as qp, rights
from crcontent.script import Scene, VideoScript

ffmpeg = pytest.mark.skipif(not shutil.which("ffmpeg"), reason="needs ffmpeg")


def by(rep, prefix):
    return [c for c in rep["checks"] if c["detector"].startswith(prefix)]


@pytest.fixture
def rules_file(tmp_path, monkeypatch):
    monkeypatch.setattr(quality, "RULES_FILE", tmp_path / "quality_rules.json")
    return tmp_path / "quality_rules.json"


def test_rule_overrides_apply_and_are_validated(rules_file):
    quality.put_rules({"short": {"blur": 15, "duplicates": False}, "lyric_preview": {"sync_sec": 1.2}})
    assert quality.rules_for("short")["blur"] == 15 and quality.rules_for("short")["duplicates"] is False
    assert quality.rules_for("lyric")["blur"] == quality.PROFILES["lyric"]["blur"]  # other profile untouched
    assert quality.rules_for("lyric_preview")["sync_sec"] == 1.2
    for bad in ({"nope": {}}, {"short": {"label": "x"}}, {"short": {"blur": "high"}}, {"short": {"blur": -1}},
                {"short": {"duplicates": 3}}):
        with pytest.raises(HTTPException):
            quality.put_rules(bad)
    quality.put_rules({"short": {"blur": None}})  # back to the default
    assert quality.rules_for("short")["blur"] == quality.PROFILES["short"]["blur"]


def test_hand_edited_rules_file_cannot_inject_keys(rules_file):
    rules_file.write_text(json.dumps({"short": {"blur": "9", "evil": 1, "label": 5}}))
    r = quality.rules_for("short")
    assert "evil" not in r and r["label"] == "Shorts" and r["blur"] == quality.PROFILES["short"]["blur"]


def test_caption_speed(tmp_path, monkeypatch, rules_file):
    monkeypatch.setattr(qp, "ROOT", tmp_path)
    fast = VideoScript(title="T", caption="c", hashtags=["a"],
                       scenes=[Scene(narration=" ".join(["word"] * 30), visual_query="q")])
    assert by(qp.inspect_short(fast, "en", "none", [2.0], False), "captions.speed")[0]["status"] == "warning"
    assert by(qp.inspect_short(fast, "en", "none", [12.0], False), "captions.speed")[0]["status"] == "pass"


@pytest.fixture
def sung(tmp_path):
    """A song folder whose vocal stem sings 0-2 s and 5-8 s, silent in between."""
    folder = tmp_path / "s"
    folder.mkdir()
    (folder / "song.json").write_text(json.dumps({"plan": "pro", "generated_on": "x", "genre": "nu-disco"}))
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i",
                    "sine=f=440:d=8,volume='if(between(t,2,5),0,1)':eval=frame", str(folder / "vocals.wav")], check=True)
    return folder


def lrc(folder, rows):
    (folder / "lyrics.lrc").write_text("".join(f"[00:{t:05.2f}]{x}\n" for t, x in rows))


@ffmpeg
def test_lyric_sync_flags_early_and_late_lines(sung):
    lrc(sung, [(0.1, "on time"), (3.0, "too early"), (6.5, "late line")])
    rep = qp.inspect_song(sung, True)
    titles = [c["title"] for c in by(rep, "lyrics.sync")]
    assert any("too early" in t and "before the singing" in t for t in titles)
    assert any("Singing starts at 5" in t for t in titles)


@ffmpeg
def test_lyric_sync_passes_when_aligned_and_is_not_checked_without_stem(sung):
    lrc(sung, [(0.1, "on time"), (5.0, "also on time")])
    assert {c["status"] for c in by(qp.inspect_song(sung, True), "lyrics.sync")} == {"pass"}
    (sung / "vocals.wav").unlink()
    assert {c["status"] for c in by(qp.inspect_song(sung, True), "lyrics.sync")} == {"not_checked"}


def test_story_review_maps_ai_answer_to_advisory_checks(monkeypatch):
    answer = {"items": [{"aspect": "hook", "ok": False, "title": "Slow start", "note": "Consider...", "scene": 1},
                        {"aspect": "ending", "ok": True, "title": "Loops back", "note": "Good.", "scene": 0},
                        {"aspect": "hook", "ok": True, "title": "dup", "note": "", "scene": 0}]}
    reply = SimpleNamespace(content=[SimpleNamespace(type="text", text=json.dumps(answer))])
    client = SimpleNamespace(beta=SimpleNamespace(messages=SimpleNamespace(create=lambda **kw: reply)))
    monkeypatch.setattr("crcontent.script.make_client", lambda: client)
    s = VideoScript(title="T", caption="c", hashtags=[], scenes=[Scene(narration="Hi", visual_query="q")])
    rep = qp.story_review(qp.StoryRequest(script=s))
    hook = by(rep, "ai.story.hook")
    assert len(hook) == 1 and hook[0]["status"] == "warning" and hook[0]["scene"] == 0
    assert by(rep, "ai.story.ending")[0]["status"] == "pass"
    assert by(rep, "ai.story.purpose")[0]["status"] == "not_checked"  # unanswered: never a pass
    assert rep["counts"]["fail"] == 0 and "AI-assisted" in hook[0]["description"]


def test_story_review_failure_is_a_clear_error(monkeypatch):
    def boom():
        raise RuntimeError("no key")
    monkeypatch.setattr("crcontent.script.make_client", boom)
    s = VideoScript(title="T", caption="c", hashtags=[], scenes=[Scene(narration="Hi", visual_query="q")])
    with pytest.raises(HTTPException) as e:
        qp.story_review(qp.StoryRequest(script=s))
    assert e.value.status_code == 502 and "other checks" in e.value.detail


# ---------- rights ----------

@pytest.fixture
def video(tmp_path, monkeypatch):
    out = tmp_path / "output"
    folder = out / "v1"
    folder.mkdir(parents=True)
    monkeypatch.setattr(rights, "OUTPUT_DIR", out)
    monkeypatch.setattr(rights, "ROOT", tmp_path)
    monkeypatch.setattr(rights, "ASSETS_DIR", tmp_path / "assets")
    (folder / "meta.json").write_text(json.dumps({"kind": "video", "music": "song.mp3"}))
    (folder / "script.json").write_text(json.dumps({"scenes": [
        {"narration": "a", "media": "cache/pexels/pexels-video-123.mp4"}, {"narration": "b", "media": "uploads/me.mp4"}]}))
    return folder


def test_rights_suggestions_and_documented_status(video):
    got = rights.get_rights("video", "v1")
    names = {a["id"]: a for a in got["items"]}
    stock = names["media:cache/pexels/pexels-video-123.mp4"]
    assert stock["source"] == "Pexels" and stock["commercial"] == "yes" and stock["auto"] and not stock["confirmed"]
    assert names["media:uploads/me.mp4"]["source"] == "Your upload" and "voice" in names and "music:song.mp3" in names
    assert got["summary"]["documented"] == 0  # suggestions aren't documentation until you confirm them


def test_rights_save_confirm_remove_and_report_rows(video):
    items = [rights.Asset(**a) for a in rights.get_rights("video", "v1")["items"] if a["id"] != "voice"]
    for a in items:
        a.source, a.license, a.confirmed, a.auto = a.source or "Me", a.license or "Own work", True, False
    got = rights.put_rights("video", "v1", rights.RightsBody(items=items))
    assert got["summary"]["documented"] == got["summary"]["total"] == len(items)
    assert all(a["id"] != "voice" for a in got["items"])  # a removed suggestion stays removed
    checks = []
    rights.check("video", "v1", checks, quality._check)
    st = {c["detector"]: c["status"] for c in checks}
    assert st["rights.documented"] == "pass" and st["rights.youtube"] == "not_checked"


def test_rights_flags_a_licence_that_forbids_the_use(video):
    items = [rights.Asset(id="x", name="NC track", type="music", commercial="no")]
    rights.put_rights("video", "v1", rights.RightsBody(items=items))
    checks = []
    rights.check("video", "v1", checks, quality._check)
    assert any(c["detector"] == "rights.licence" and c["status"] == "warning" for c in checks)


def test_rights_rejects_bad_targets(video):
    for scope, name in (("video", "../../etc"), ("video", "nope"), ("other", "v1")):
        with pytest.raises(HTTPException):
            rights.get_rights(scope, name)
