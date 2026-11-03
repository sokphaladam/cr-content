"""Milestone 3: footage per planned shot, user files first, checked for subject and action, with plain warnings."""
import json
from types import SimpleNamespace

import pytest
from PIL import Image

from crcontent import director_plan, drafts, shot_footage
from crcontent.longform import footage as lf

CFG = {"footage": {"sources": ["pexels"], "by_kind": {"species": ["pexels", "commons"]}, "check_subject": True}}


def make_plan(fmt="short"):
    plan = director_plan.from_scenes("Ravens", fmt, "en", "cinematic_wildlife", [
        {"narration": "Ravens can bend wire into a hook to get food.", "visual_query": "raven wire"},
        {"narration": "They live almost everywhere.", "visual_query": "raven"},
    ])
    plan.shots[0] = plan.shots[0].model_copy(update={
        "subject": "Common raven", "action": "bending a wire into a hook", "evidence": "exact_action",
        "footage_queries": ["raven bending wire hook", "raven close up"], "camera": director_plan.Camera(movement="tracking")})
    plan.shots[1] = plan.shots[1].model_copy(update={"subject": "Common raven", "footage_queries": ["raven perched"]})
    return plan


def item(i, kind="video", duration=10, width=2160, height=3840):
    return {"source": "pexels", "id": i, "kind": kind, "url": f"https://x/{i}", "thumb": f"https://x/{i}.jpg",
            "page": f"https://pexels/{i}", "author": "A", "licence": "Pexels License", "licence_url": "https://l",
            "duration": duration, "width": width, "height": height}


class Vision:
    """Fake Gemini: scores by the clip id, as given in `scores` {id: (subject, action, quality)}."""

    def __init__(self, scores):
        self.scores, self.calls = scores, []
        outer = self

        class messages:
            @staticmethod
            def create(**kw):
                import base64
                import io

                content = kw["messages"][0]["content"]
                outer.calls.append(content[1]["text"])
                cid = Image.open(io.BytesIO(base64.b64decode(content[0]["source"]["data"]))).width - 100
                s, a, q = outer.scores[cid]
                body = json.dumps({"subject": s, "action": a, "quality": q, "problem": "" if s >= 7 else "a crow"})
                return SimpleNamespace(content=[SimpleNamespace(type="text", text=body)])

        self.beta = SimpleNamespace(messages=messages)


@pytest.fixture
def stock(tmp_path, monkeypatch):
    """Searches return `results[query]`; downloads write a tiny picture named after the id."""
    results = {}
    vision = Vision({})

    def fetch(it):
        path = tmp_path / f"clip-{it['id']}.jpg"
        Image.new("RGB", (100 + it["id"], 32), "gray").save(path)  # the width tells the fake Gemini which clip
        return path

    monkeypatch.setattr(lf, "search", lambda q, *a, **k: list(results.get(q, [])))
    monkeypatch.setattr(lf, "fetch", fetch)
    monkeypatch.setenv("GEMINI_API_KEY", "test")
    return SimpleNamespace(results=results, vision=vision)


def test_exact_action_beats_a_pretty_subject_only_clip(stock):
    stock.results["raven bending wire hook"] = [item(1), item(2)]
    stock.results["raven perched"] = [item(3, kind="photo")]
    stock.vision.scores = {1: (9, 3, 10), 2: (8, 8, 6), 3: (8, 0, 7)}
    plan = shot_footage.find(make_plan(), None, CFG, client=stock.vision)
    first, second = plan.shots
    assert first.footage.raw["id"] == 2 and first.footage.match == "exact"  # the action, not the prettier clip
    assert [c.raw["id"] for c in first.candidates] == [1] and first.candidates[0].match == "subject_only"
    assert first.footage.licence == "Pexels License" and first.footage.page and first.footage.file
    asked = [c for c in stock.vision.calls if "Doing exactly this" in c]
    assert len(asked) == 2 and len(stock.vision.calls) == 3  # the action is asked only for the shot that needs it
    assert second.footage.match == "good"
    assert not first.warnings


def test_wrong_subject_is_never_used_and_missing_is_explained(stock):
    stock.results["raven bending wire hook"] = [item(1)]
    stock.results["raven close up"] = [item(2)]
    stock.vision.scores = {1: (2, 0, 9), 2: (8, 2, 8)}  # a crow; then a raven not using a tool
    plan = shot_footage.find(make_plan(), None, CFG, ["shot-001-1"], client=stock.vision)
    shot = plan.shots[0]
    assert shot.footage.raw["id"] == 2 and shot.footage.match == "subject_only"
    assert any("not the stated action" in w for w in shot.warnings)
    assert all(c.raw["id"] != 1 for c in shot.candidates)  # the crow isn't even offered
    assert plan.shots[1].footage is None  # not asked for

    stock.results.clear()
    plan = shot_footage.find(make_plan(), None, CFG, client=stock.vision)
    assert plan.shots[0].footage is None and "add your own file named shot-001-1.mp4" in plan.shots[0].warnings[0]
    assert any("have no footage" in w for w in plan.warnings)


def test_own_files_come_first(stock, tmp_path):
    media = tmp_path / "media"
    media.mkdir()
    (media / "shot-001-1.mp4").write_bytes(b"x")
    (media / "scene-02.jpg").write_bytes(b"x")  # the long-video convention, for a scene's first shot
    stock.results["raven perched"] = [item(3)]
    plan = shot_footage.find(make_plan(), media, CFG, client=stock.vision)
    assert [s.footage.source for s in plan.shots] == ["own", "own"] and not stock.vision.calls
    assert plan.shots[1].footage.kind == "photo"


def test_quality_warnings_and_no_reuse(stock):
    stock.results["raven bending wire hook"] = [item(1, kind="photo")]
    stock.results["raven perched"] = [item(1, kind="photo"), item(4, duration=1, width=1920, height=1080)]
    stock.vision.scores = {1: (9, 9, 8), 4: (9, 0, 8)}
    plan = shot_footage.find(make_plan(), None, CFG, client=stock.vision)
    first, second = plan.shots
    assert first.footage.raw["id"] == 1 and any("still photo can't be a tracking" in w for w in first.warnings)
    assert second.footage.raw["id"] == 4  # the same photo isn't used twice
    assert any("loops" in w for w in second.warnings) and any("soft" in w for w in second.warnings)


def test_without_gemini_it_picks_and_says_unchecked(stock, monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY")
    stock.results["raven bending wire hook"] = [item(1)]
    stock.results["raven perched"] = [item(2)]
    plan = shot_footage.find(make_plan(), None, CFG)
    assert [s.footage.match for s in plan.shots] == ["unchecked", "unchecked"]
    assert "Not checked" in plan.shots[0].warnings[0]


def test_locked_shots_keep_their_footage_and_pick_swaps(stock):
    stock.results["raven bending wire hook"] = [item(1), item(2)]
    stock.results["raven perched"] = [item(3)]
    stock.vision.scores = {1: (9, 9, 9), 2: (8, 6, 6), 3: (8, 0, 8)}
    plan = shot_footage.find(make_plan(), None, CFG, client=stock.vision)
    assert plan.shots[0].footage.raw["id"] == 1
    swapped = shot_footage.pick(plan, "shot-001-1", 0)
    assert swapped.shots[0].footage.raw["id"] == 2 and swapped.shots[0].locked
    assert swapped.shots[0].candidates[0].raw["id"] == 1
    again = shot_footage.find(swapped, None, CFG, client=stock.vision)
    assert again.shots[0].footage.raw["id"] == 2
    with pytest.raises(IndexError):
        shot_footage.pick(plan, "shot-001-1", 9)


def test_variety_warnings():
    plan = make_plan()
    plan.shots = [plan.shots[0].model_copy(update={"id": f"shot-001-{k}", "shot_type": "close_up"}) for k in range(1, 4)]
    assert any("Three close up shots in a row" in w for w in shot_footage.plan_warnings(plan))


def test_cancel_stops_between_shots(stock):
    stock.results["raven bending wire hook"] = [item(1)]
    stock.vision.scores = {1: (9, 9, 9)}
    plan = shot_footage.find(make_plan(), None, CFG, cancelled=lambda: True, client=stock.vision)
    assert all(s.footage is None for s in plan.shots) and not stock.vision.calls


# ---------- API ----------

@pytest.fixture
def client(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient

    from crcontent import web

    monkeypatch.setattr(drafts, "DRAFTS_DIR", tmp_path / "drafts")
    monkeypatch.setattr(web, "_plan_media", lambda kind, ref: tmp_path / "media" / ref)
    ran = []

    def run_now(fn, *args):  # run the job inline, so the test sees its result
        ran.append(args)
        fn(*args)

    monkeypatch.setattr(web.footage_pool, "submit", run_now)
    monkeypatch.setattr(web.renderer, "submit", lambda fn, *a: None)
    c = TestClient(web.app)
    c.ran = ran
    return c


def test_footage_api(client, stock, monkeypatch):
    from crcontent.longform import settings as lsettings
    from crcontent.script import VideoScript
    from crcontent import web

    monkeypatch.setattr(lsettings, "load", lambda: CFG)
    import crcontent.script as script_mod

    monkeypatch.setattr(script_mod, "make_client", lambda: stock.vision)
    stock.results["raven bending wire hook"] = [item(1), item(2)]
    stock.results["raven perched"] = [item(3)]
    stock.vision.scores = {1: (9, 9, 9), 2: (8, 8, 7), 3: (8, 0, 8)}
    script = VideoScript(title="Ravens", scenes=[{"narration": "a", "visual_query": "b"}], caption="", hashtags=[])
    draft_id = drafts.create(drafts.Draft(script=script, plan=make_plan()))[0]

    r = client.post(f"/api/plans/draft/{draft_id}/footage", json={})
    assert r.status_code == 200, r.text
    assert web.jobs[r.json()["id"]]["status"] == "done"
    plan = client.get(f"/api/plans/draft/{draft_id}").json()
    assert plan["shots"][0]["footage"]["match"] == "exact" and plan["media_folder"].endswith(draft_id)

    # an edit from the editor can't wipe the footage
    edited = {**plan, "shots": [{**plan["shots"][0], "footage": None, "visual_description": "mine", "locked": True},
                                plan["shots"][1]]}
    saved = client.put(f"/api/plans/draft/{draft_id}", json=edited).json()
    assert saved["shots"][0]["footage"]["match"] == "exact" and saved["shots"][0]["visual_description"] == "mine"

    r = client.post(f"/api/plans/draft/{draft_id}/shots/shot-001-1/pick", json={"index": 0})
    assert r.status_code == 200 and r.json()["shots"][0]["footage"]["raw"]["id"] == 2
    assert client.post(f"/api/plans/draft/{draft_id}/shots/shot-001-1/pick", json={"index": 7}).status_code == 400
    assert client.post(f"/api/plans/draft/{draft_id}/shots/nope/pick", json={"index": 0}).status_code == 404
    assert client.post(f"/api/plans/draft/{draft_id}/footage", json={"shots": ["nope"]}).status_code == 400


def test_searches_drop_format_words_and_end_with_the_subject():
    shot = director_plan.Shot(id="shot-001-1", scene_id="scene-001", subject="Common octopus (Octopus vulgaris)",
                              footage_queries=["octopus swimming coral reef vertical", "octopus 4K close up"])
    assert shot_footage.queries(shot) == ["octopus swimming coral reef", "octopus close up", "Common octopus"]


def test_junk_searches_offer_no_unchecked_alternatives(stock):
    stock.results["raven perched"] = [item(5), item(6), item(7), item(8), item(9)]
    stock.vision.scores = {5: (0, 0, 8), 6: (1, 0, 8), 7: (0, 0, 2)}  # a burger, bacon, a beach
    plan = shot_footage.find(make_plan(), None, CFG, ["shot-002-1"], client=stock.vision)
    assert plan.shots[1].footage is None and plan.shots[1].candidates == []
