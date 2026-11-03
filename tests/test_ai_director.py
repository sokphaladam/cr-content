"""Milestone 2: the AI Director turns a seeded plan into a directed one, checks Gemini's answer, keeps user edits."""
import json
from types import SimpleNamespace

import pytest

from crcontent import ai_director, director_plan, drafts

SCENES = [
    {"narration": "Ravens can bend wire into a hook.", "visual_query": "raven wire"},
    {"narration": "Then they pull the food out of the tube.", "visual_query": "raven tube"},
]


def shot(**kw):
    base = {"purpose": "Show the tool", "shot_type": "close_up", "subject": "Raven", "action": "bends wire",
            "visual_description": "Stunning cinematic raven beak gripping a wire, 8K", "angle": "eye_level",
            "movement": "slow_push_in", "framing": "tight", "lighting": "soft side light", "weight": 1,
            "footage_queries": ["raven bending wire hook", "beautiful raven tool"], "evidence": "exact_action",
            "factual_requirements": ["must be a raven, not a crow"], "visual_priority": "high", "transition_out": "hard_cut"}
    return base | kw


ANSWER = {
    "story": {"hook": "A bird that makes tools", "central_idea": "Ravens plan", "emotional_arc": ["surprise", "awe"],
              "payoff": "Food retrieved", "audience": "curious viewers", "key_facts": ["ravens bend wire"]},
    "continuity": {"subjects": ["common raven"], "locations": ["lab"], "lighting": ["daylight"]},
    "edit_plan": {"music_mood": "curious", "sound_effects": ["wire creak"], "colour_grade": "natural", "pacing": "fast"},
    "suggestions": [],
    "scenes": [
        {"scene_id": "scene-001", "purpose": "Hook", "viewer_objective": "Wonder how", "emotion": "surprise",
         "transition_out": "match_cut", "shots": [shot(weight=1), shot(shot_type="wide", weight=3, movement="warp_speed")]},
        {"scene_id": "scene-002", "purpose": "Payoff", "viewer_objective": "See it work", "emotion": "awe",
         "transition_out": "bogus", "shots": [shot(action="pulls food")]},
        {"scene_id": "scene-999", "purpose": "invented", "viewer_objective": "", "emotion": "", "transition_out": "hard_cut",
         "shots": [shot()]},
    ],
}


class FakeClient:
    def __init__(self, answer):
        self.answer, self.calls = answer, []
        outer = self

        class messages:
            @staticmethod
            def create(**kw):
                outer.calls.append(kw)
                text = outer.answer if isinstance(outer.answer, str) else json.dumps(outer.answer)
                return SimpleNamespace(content=[SimpleNamespace(type="text", text=text)], stop_reason="end_turn")

        self.beta = SimpleNamespace(messages=messages)


@pytest.fixture(autouse=True)
def no_cache(tmp_path, monkeypatch):
    monkeypatch.setattr(ai_director, "CACHE", tmp_path / "director")


def seeded(fmt="short"):
    return director_plan.from_scenes("Ravens", fmt, "en", "cinematic_wildlife", SCENES)


def test_direct_fills_and_normalises_the_plan():
    client = FakeClient(ANSWER)
    plan = ai_director.direct(seeded(), client=client)
    assert plan.planned_by == "ai" and plan.story.hook == "A bird that makes tools"
    assert plan.continuity.subjects == ["common raven"] and plan.continuity.visual_style == "cinematic_wildlife"
    assert [s.id for s in plan.shots] == ["shot-001-1", "shot-001-2", "shot-002-1"]  # scene-999 ignored
    first, second = plan.shots[0], plan.shots[1]
    assert first.visual_description == "raven beak gripping a wire"  # filler words dropped
    assert first.footage_queries == ["raven bending wire hook", "raven tool"]
    assert second.camera.movement == "static"  # unknown move -> safe default
    total = director_plan.spoken_seconds(SCENES[0]["narration"])
    assert abs(first.duration_seconds + second.duration_seconds - total) < 0.05 and second.duration_seconds > first.duration_seconds
    assert plan.scenes[1].transition_out == "hard_cut" and plan.scenes[0].transition_out == "match_cut"
    assert [s.narration for s in plan.scenes] == [s["narration"] for s in SCENES]  # never rewritten
    sent = client.calls[0]
    assert "vertical 9:16" in sent["messages"][0]["content"] and "scene-002" in sent["messages"][0]["content"]


def test_cache_avoids_a_second_call():
    client = FakeClient(ANSWER)
    ai_director.direct(seeded(), client=client)
    ai_director.direct(seeded(), client=client)
    assert len(client.calls) == 1


def test_regenerate_one_scene_keeps_the_rest_and_locked_shots():
    plan = ai_director.direct(seeded(), client=FakeClient(ANSWER))
    plan.shots[0].visual_description = "my own idea"
    plan.shots[0].locked = True
    redo = {**ANSWER, "scenes": [{**ANSWER["scenes"][1], "shots": [shot(action="new take"), shot(action="result")]}]}
    client = FakeClient(redo)
    again = ai_director.direct(plan, ["scene-002"], "more detail", client=client)
    assert "[PLAN THIS]" in client.calls[0]["messages"][0]["content"] and "more detail" in client.calls[0]["messages"][0]["content"]
    assert again.story == plan.story  # project analysis untouched by a scene re-plan
    assert again.shots[0].visual_description == "my own idea" and again.shots[0].locked
    assert [s.action for s in again.shots if s.scene_id == "scene-002"] == ["new take", "result"]
    # a whole-video pass skips the scene with a locked shot
    whole = ai_director.direct(again, note="x", client=FakeClient(ANSWER))
    kept = [s for s in whole.shots if s.scene_id == "scene-001"]
    assert [(s.id, s.visual_description) for s in kept][0] == ("shot-001-1", "my own idea") and len(kept) == 2


def test_bad_answers_raise_and_leave_the_plan_alone():
    plan = seeded()
    with pytest.raises(RuntimeError, match="didn't match"):
        ai_director.direct(plan, client=FakeClient({**ANSWER, "scenes": []}))
    with pytest.raises(RuntimeError, match="wasn't usable"):
        ai_director.direct(plan, client=FakeClient({**ANSWER, "story": {"emotional_arc": 5}}))
    with pytest.raises(ValueError, match="Unknown scenes"):
        ai_director.direct(plan, ["scene-404"], client=FakeClient(ANSWER))
    assert plan.planned_by == "script"


@pytest.fixture
def client(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient

    from crcontent import web

    monkeypatch.setattr(drafts, "DRAFTS_DIR", tmp_path / "drafts")
    monkeypatch.setattr(web, "LONG_SCRIPTS", tmp_path / "scripts")
    monkeypatch.setattr(web.footage_pool, "submit", lambda fn, job_id, *args: web.jobs[job_id].update(status="done"))
    monkeypatch.setattr(web.renderer, "submit", lambda fn, *args: None)
    return TestClient(web.app)


def make_draft():
    from crcontent.script import VideoScript

    script = VideoScript(title="Ravens", scenes=SCENES, caption="", hashtags=[])
    return drafts.create(drafts.Draft(script=script, plan=seeded()))[0]


def test_plan_endpoints(client, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test")
    draft_id = make_draft()
    plan = client.get(f"/api/plans/draft/{draft_id}").json()
    assert plan["planned_by"] == "script"

    plan["shots"][0]["visual_description"], plan["shots"][0]["locked"] = "edited", True
    assert client.put(f"/api/plans/draft/{draft_id}", json=plan).status_code == 200
    bad = {**plan, "shots": [{**plan["shots"][0], "scene_id": "nope"}]}
    assert client.put(f"/api/plans/draft/{draft_id}", json=bad).status_code == 422

    fake = FakeClient(ANSWER)
    import crcontent.script as script_mod

    monkeypatch.setattr(script_mod, "make_client", lambda: fake)
    r = client.post(f"/api/plans/draft/{draft_id}/direct", json={})
    assert r.status_code == 200, r.text
    saved = drafts.load(draft_id).plan
    assert saved.planned_by == "ai" and saved.shots[0].visual_description == "edited"  # locked scene kept
    assert client.post(f"/api/plans/draft/{draft_id}/direct", json={"scenes": ["x"]}).status_code == 400
    assert client.get("/api/plans/draft/missing").status_code == 404


def test_direct_without_gemini_is_a_clear_error(client, monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    assert client.post(f"/api/plans/draft/{make_draft()}/direct", json={}).status_code == 400


def test_script_video_directs_the_short_or_says_why_not(client, monkeypatch):
    import crcontent.script as script_mod
    from crcontent import web

    pasted = "Ravens\n\nScene 1\nVoiceover: Ravens can bend wire into a hook.\n\nScene 2\nVoiceover: Then they pull the food out of the tube.\n"
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    body = client.post("/api/script-video", json={"text": pasted, "format": "short"}).json()
    assert body["planned_by"] == "script" and "Gemini isn't set up" in body["director_note"]

    # Gemini set up but failing: the draft is still made, with the seeded plan and the reason
    monkeypatch.setenv("GEMINI_API_KEY", "test")
    monkeypatch.setattr(web, "import_script", lambda text, lang, use_claude: (drafts.load(body["id"]).script, "en", "claude"))
    monkeypatch.setattr(script_mod, "make_client", lambda: FakeClient("not json"))
    body = client.post("/api/script-video", json={"text": pasted, "format": "short"}).json()
    assert body["planned_by"] == "script" and "couldn't plan" in body["director_note"]
