"""Script to Video, milestone 1: the Director Plan schema, its storage, and /api/script-video for both formats."""
import pytest
from pydantic import ValidationError

from crcontent import director_plan, drafts
from crcontent.longform.parse import parse

SCENES = [
    {"narration": "Ravens can bend wire into a hook.", "visual_query": "raven wire", "on_screen_text": "SMART"},
    {"narration": "Then they pull the food out of the tube.", "visual_query": "raven tube food", "on_screen_text": ""},
]
TABLE = """# Clever Birds

| Time | Visual | On-screen Text | Voiceover |
| --- | --- | --- | --- |
| 0:00 | raven on branch | #1 RAVEN | Ravens can bend wire into a hook. |
| 0:05 | crow in city | | Crows drop nuts on roads. |
"""


def test_seeded_plan_keeps_narration_and_stable_ids():
    plan = director_plan.from_scenes("Ravens", "short", "en", "cinematic_wildlife", SCENES)
    assert plan.project.aspect_ratio == "9:16" and plan.planned_by == "script"
    assert [s.id for s in plan.scenes] == ["scene-001", "scene-002"]
    assert [(s.id, s.scene_id) for s in plan.shots] == [("shot-001-1", "scene-001"), ("shot-002-1", "scene-002")]
    assert plan.scenes[0].narration == SCENES[0]["narration"]  # word for word
    assert plan.shots[0].footage_queries == ["raven wire"] and plan.shots[0].duration_seconds > 0
    again = director_plan.load(plan.model_dump())  # round trip through JSON-shaped data
    assert again == plan


def test_validation_and_migration():
    plan = director_plan.from_scenes("t", "long", "en", "educational", SCENES).model_dump()
    assert director_plan.load({**plan, "version": 0}).version == director_plan.VERSION
    with pytest.raises(ValidationError, match="newer version"):
        director_plan.load({**plan, "version": director_plan.VERSION + 1})
    with pytest.raises(ValidationError, match="unknown scenes"):
        director_plan.load({**plan, "shots": [{**plan["shots"][0], "scene_id": "scene-999"}]})
    with pytest.raises(ValidationError, match="unique"):
        director_plan.load({**plan, "scenes": [plan["scenes"][0], plan["scenes"][0]], "shots": []})
    stale = {**plan, "project": {**plan["project"], "aspect_ratio": "9:16"}}
    assert director_plan.load(stale).project.aspect_ratio == "16:9"


def test_khmer_duration_counts_letters():
    assert director_plan.spoken_seconds("សួស្តីពិភពលោក") > 0


def test_longform_markdown_reads_back(tmp_path):
    plan = director_plan.from_scenes("Ravens | Crows", "long", "en", "cinematic_wildlife", SCENES)
    md = tmp_path / "s.md"
    md.write_text(director_plan.longform_markdown(plan), encoding="utf-8")
    script = parse(md)
    assert [s.voiceover for s in script.scenes] == [s["narration"] for s in SCENES]
    assert script.scenes[1].planned > script.scenes[0].planned


def test_editor_save_keeps_the_plan(tmp_path, monkeypatch):
    monkeypatch.setattr(drafts, "DRAFTS_DIR", tmp_path)
    from crcontent.script import VideoScript

    script = VideoScript(title="Ravens", scenes=[{"narration": "x", "visual_query": "y"}], caption="", hashtags=[])
    plan = director_plan.from_scenes("Ravens", "short", "en", "storytelling", SCENES)
    draft_id, _ = drafts.create(drafts.Draft(script=script, plan=plan))
    drafts.save(draft_id, drafts.Draft(script=script, topic="edited"))  # what the editor's autosave sends
    loaded = drafts.load(draft_id)
    assert loaded.topic == "edited" and loaded.plan == plan


@pytest.fixture
def client(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient

    from crcontent import web

    monkeypatch.delenv("GEMINI_API_KEY", raising=False)  # the basic reader: no network
    monkeypatch.setattr(drafts, "DRAFTS_DIR", tmp_path / "drafts")
    monkeypatch.setattr(web, "LONG_SCRIPTS", tmp_path / "scripts")
    started = []
    monkeypatch.setattr(web.footage_pool, "submit", lambda fn, job_id, *args: web.jobs[job_id].update(status="done"))
    monkeypatch.setattr(web.renderer, "submit", lambda fn, *args: started.append((fn.__name__, args)))
    c = TestClient(web.app)
    c.started = started
    return c


PASTED = """Clever Ravens

Scene 1
Visual: raven close-up
Voiceover: Ravens can bend wire into a hook.

Scene 2
Visual: raven pulls food from tube
Voiceover: Then they pull the food out of the tube.
"""


def test_script_video_short_makes_a_draft_with_plan(client):
    r = client.post("/api/script-video", json={"text": PASTED, "format": "short", "visual_style": "cinematic_wildlife"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["format"] == "short" and body["scenes"] >= 1
    d = drafts.load(body["id"])
    assert d.plan.project.format == "short" and d.plan.project.visual_style == "cinematic_wildlife"
    assert [s.narration for s in d.plan.scenes] == [s.narration for s in d.script.scenes]


def test_script_video_long_from_prose_and_from_table(client):
    r = client.post("/api/script-video", json={"text": PASTED, "format": "long"})
    assert r.status_code == 200, r.text
    name, (job_id, dest, plan) = client.started[-1]
    assert name == "_run_storyboard" and r.json()["id"] == job_id
    assert plan.project.aspect_ratio == "16:9" and parse(dest).scenes  # the existing long pipeline can read it

    r = client.post("/api/script-video", json={"text": TABLE, "format": "long"})
    assert r.status_code == 200, r.text
    _, (_, dest2, plan2) = client.started[-1]
    assert dest2.read_text(encoding="utf-8") == TABLE  # a table is used as written (title cards, chapters)
    assert plan2.project.title == "Clever Birds" and len(plan2.scenes) == 2


def test_script_video_rejects_bad_input(client):
    assert client.post("/api/script-video", json={"text": PASTED, "format": "tiktok"}).status_code == 400
    assert client.post("/api/script-video", json={"text": PASTED, "format": "short", "visual_style": "8k"}).status_code == 400
