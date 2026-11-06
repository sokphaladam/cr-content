"""Hidden History Files spec, milestone H1: channel profiles, their persistence, and the legacy defaults."""
import json

import pytest
from pydantic import ValidationError

from crcontent import director_plan, drafts, profiles
from tests.test_director_plan import PASTED, SCENES, TABLE, client  # noqa: F401  (client is a fixture)


def test_registry_profiles_are_valid_and_use_known_styles():
    assert set(profiles.PROFILES) == {"wildlife_facts", "hidden_history_files"}
    for p in profiles.PROFILES.values():
        assert p.visual_style in director_plan.STYLES and p.version >= 1
        profiles.ChannelProfile.model_validate(p.model_dump())  # round trip through the schema
    history = profiles.PROFILES["hidden_history_files"]
    assert history.visual_style == "cinematic_history" and history.format_defaults.target_seconds == 40
    assert history.palette["accent"] == "#B99A60"
    with pytest.raises(ValidationError):
        profiles.ChannelProfile(id="x", display_name="X", version=0, visual_style="educational")


def test_resolve_falls_back_safely():
    assert profiles.resolve("") == (None, "")
    p, note = profiles.resolve("hidden_history_files")
    assert p.id == "hidden_history_files" and note == ""
    p, note = profiles.resolve("no_such_channel")
    assert p is None and "general defaults" in note
    newer = profiles.PROFILES["wildlife_facts"].model_copy(update={"schema_version": profiles.SCHEMA + 1})
    profiles.PROFILES["future"] = newer
    try:
        assert profiles.resolve("future")[0] is None
    finally:
        del profiles.PROFILES["future"]


def test_legacy_plans_load_without_a_profile():
    plan = director_plan.from_scenes("Ravens", "short", "en", "cinematic_wildlife", SCENES).model_dump()
    del plan["project"]["channel_profile_id"], plan["project"]["channel_profile_version"]  # a pre-profile draft.json
    loaded = director_plan.load(plan)
    assert loaded.project.channel_profile_id == "" and loaded.project.visual_style == "cinematic_wildlife"
    assert profiles.stamp({"kind": "video"}, loaded) == {"kind": "video"}  # nothing added to its meta.json


def test_history_short_records_its_profile(client):  # noqa: F811
    r = client.post("/api/script-video", json={"text": PASTED, "format": "short", "visual_style": "cinematic_history",
                                               "channel_profile_id": "hidden_history_files"})
    assert r.status_code == 200, r.text
    assert r.json()["profile_note"] == ""
    project = drafts.load(r.json()["id"]).plan.project
    assert (project.channel_profile_id, project.channel_profile_version, project.visual_style) == \
        ("hidden_history_files", 1, "cinematic_history")
    meta = profiles.stamp({}, drafts.load(r.json()["id"]).plan)
    assert meta == {"channel_profile_id": "hidden_history_files", "channel_profile_version": 1,
                    "channel_profile_name": "Hidden History Files"}


def test_no_profile_and_unknown_profile_keep_general_defaults(client):  # noqa: F811
    r = client.post("/api/script-video", json={"text": PASTED, "format": "short"})
    assert r.status_code == 200 and drafts.load(r.json()["id"]).plan.project.channel_profile_id == ""
    r = client.post("/api/script-video", json={"text": PASTED, "format": "short", "channel_profile_id": "nope"})
    assert r.status_code == 200, r.text
    assert "isn't known" in r.json()["profile_note"]
    project = drafts.load(r.json()["id"]).plan.project
    assert project.channel_profile_id == "" and project.visual_style == "cinematic_documentary"


def test_long_video_plan_carries_the_profile(client):  # noqa: F811
    for text in (PASTED, TABLE):  # prose (imported) and a ready table both tag the plan
        r = client.post("/api/script-video", json={"text": text, "format": "long", "channel_profile_id": "wildlife_facts"})
        assert r.status_code == 200, r.text
        _, (_, _, plan, _) = client.started[-1]
        assert plan.project.channel_profile_id == "wildlife_facts"


def test_profiles_endpoint_lists_both(client):  # noqa: F811
    ids = [p["id"] for p in client.get("/api/profiles").json()]
    assert ids == ["wildlife_facts", "hidden_history_files"]


def test_storyboard_job_writes_profile_to_meta(tmp_path, monkeypatch):
    from crcontent import longform, web

    folder = tmp_path / "out"
    folder.mkdir()
    (folder / "meta.json").write_text(json.dumps({"kind": "long_video"}), encoding="utf-8")
    monkeypatch.setattr(longform, "make_storyboard", lambda *a, **k: folder)
    monkeypatch.setattr(web, "_direct_or_keep", lambda plan, log: plan)
    plan = director_plan.from_scenes("T", "long", "en", "cinematic_history", SCENES)
    plan.project.channel_profile_id, plan.project.channel_profile_version = "hidden_history_files", 1
    web.jobs["t1"] = {"id": "t1", "status": "queued", "step": 0, "log": []}
    web._run_storyboard("t1", tmp_path / "s.md", plan)
    assert web.jobs["t1"]["status"] == "done", web.jobs["t1"]
    meta = json.loads((folder / "meta.json").read_text(encoding="utf-8"))
    assert meta["kind"] == "long_video" and meta["channel_profile_id"] == "hidden_history_files"


def test_preflight_report_names_the_profile():
    from crcontent import quality_preview as qp
    from crcontent.script import VideoScript

    script = VideoScript(title="T", scenes=[{"narration": "x y z", "visual_query": "q"}], caption="", hashtags=[])
    plan = director_plan.from_scenes("T", "short", "en", "cinematic_history", SCENES)
    assert qp.inspect_short(script, "en", "none", [2.0], False, plan)["channel_profile"] == ""  # General
    plan.project.channel_profile_id, plan.project.channel_profile_version = "hidden_history_files", 1
    assert qp.inspect_short(script, "en", "none", [2.0], False, plan)["channel_profile"] == "Hidden History Files"
    assert qp.inspect_short(script, "en", "none", [2.0], False)["channel_profile"] == ""  # no plan
