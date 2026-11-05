"""Attention roadmap M8: the final inspector checks the video against the editor's timeline and the story plan."""
import json

from crcontent import director_plan, drafts, quality, timeline
from crcontent.script import Clip, Scene, TrackState, VideoScript

G = Clip(id="g", track="graphics", start=1, duration=2, template="LowerThird", props={"title": "Crow"})
S = Clip(id="s", track="sfx", start=3, duration=1, sound="impact")


def folder(tmp_path, clips, record, draft=""):
    s = VideoScript(title="T", caption="", hashtags=[], scenes=[Scene(narration="a", visual_query="b")], clips=clips)
    (tmp_path / "script.json").write_text(s.model_dump_json(), encoding="utf-8")
    meta = {"draft": draft} if draft else {}
    if record is not None:
        meta["timeline"] = record
    (tmp_path / "meta.json").write_text(json.dumps(meta), encoding="utf-8")
    return tmp_path


def run(path):
    checks = []
    covered = quality.edit_checks(checks, path)
    return {c["detector"].split(".")[0] + "." + c["detector"].split(".")[1]: c for c in checks}, covered, checks


def test_everything_placed_is_in_the_video(tmp_path):
    rec = {"length": 10, "graphics": {"g": [1, 2]}, "sounds": ["s"], "left_out": {}}
    found, _, _ = run(folder(tmp_path, [G, S], rec))
    assert found["edit.timeline"]["status"] == "pass" and "2 timeline clips" in found["edit.timeline"]["title"]


def test_a_missing_or_moved_clip_fails(tmp_path):
    rec = {"length": 10, "graphics": {"g": [1.5, 2]}, "sounds": [], "left_out": {}}
    found, _, _ = run(folder(tmp_path, [G, S], rec))
    c = found["edit.timeline"]
    assert c["status"] == "fail" and "g drawn at 1.50 s" in c["description"] and "s isn't in the video" in c["description"]


def test_left_out_with_a_reason_is_a_warning_not_a_failure(tmp_path):
    rec = {"length": 10, "graphics": {}, "sounds": ["s"], "left_out": {"g": "Remotion couldn't draw it"}}
    _, _, checks = run(folder(tmp_path, [G, S], rec))
    statuses = {c["detector"]: c["status"] for c in checks}
    assert statuses == {"edit.left_out.g": "warning", "edit.timeline": "pass"}
    assert "Remotion couldn't draw it" in next(c for c in checks if c["detector"] == "edit.left_out.g")["description"]


def test_an_old_render_says_not_checked(tmp_path):
    found, _, _ = run(folder(tmp_path, [G], None))
    assert found["edit.timeline"]["status"] == "not_checked"
    assert run(folder(tmp_path, [], None))[2] == []  # no clips, nothing to say


def test_story_checks_come_from_the_draft(tmp_path, monkeypatch):
    monkeypatch.setattr(drafts, "DRAFTS_DIR", tmp_path / "drafts")
    plan = director_plan.from_scenes("t", "short", "en", "educational", [{"narration": "a"}, {"narration": "b"}])
    plan.planned_by = "ai"
    plan.scenes[0].phase, plan.scenes[1].phase = "setup", "tension"  # no payoff
    did, _ = drafts.create(drafts.Draft(script=VideoScript(title="T", caption="", hashtags=[], scenes=[]), plan=plan))
    found, covered, checks = run(folder(tmp_path, [], None, did))
    assert covered == {"storytelling"} and any("No payoff" in c["title"] for c in checks)
    # the not-checked placeholder for storytelling is dropped once the plan was checked
    rep = quality._finish({"stage": "render", "checks": list(checks), "cancelled": False},
                          [n for n in quality.NOT_YET if n[0] not in covered])
    assert not any(c["detector"].startswith("later.storytelling") for c in rep["checks"])


def test_the_render_records_why_clips_were_left_out():
    s = VideoScript(title="T", caption="", hashtags=[], scenes=[], clips=[
        Clip(id="late", track="sfx", start=50, sound="impact"), Clip(id="gone", track="sfx", start=1, sound="user:nope-1"),
        Clip(id="bad", track="graphics", start=1, template="LowerThird", props={"title": ""})])
    left = {}
    timeline.sound_events(s, 10, lambda m: None, left)
    timeline.graphic_clips(s, 10, "", lambda m: None, left_out=left)
    assert left == {"late": "it starts after the video ends", "gone": "the sound isn't in the library", "bad": "Title is empty."}
    hidden = s.model_copy(update={"tracks": {"graphics": TrackState(hidden=True)}})
    left = {}
    timeline.graphic_clips(hidden, 10, "", lambda m: None, left_out=left)
    assert left == {"bad": "the graphics lane is hidden"}
