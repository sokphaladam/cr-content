"""Attention roadmap M2: the Story Retention Inspector inside the pre-render check, on representative stories."""
import pytest

from crcontent import director_plan, drafts
from crcontent import quality_preview as qp
from crcontent.script import Scene, VideoScript

LINES = ["This bird solves a puzzle most children can't.", "Scientists hid meat deep inside a narrow tube.",
         "The crow bent a straight wire into a hook.", "It fished the meat out on the first try."]


def plan_for(beats, loops=(("q1", "How does it get the meat?", False),)):
    """beats: per line (phase, role, opens, resolves)."""
    plan = director_plan.from_scenes("Crow", "short", "en", "educational", [{"narration": n} for n in LINES])
    plan.planned_by = "ai"
    plan.story.loops = [director_plan.Loop(id=i, question=q, left_open=o) for i, q, o in loops]
    for scene, (phase, role, opens, resolves) in zip(plan.scenes, beats):
        scene.phase, scene.beat_role, scene.opens, scene.resolves = phase, role, opens, resolves
        scene.viewer_question = "How?" if opens else ""
    return plan


GOOD = [("setup", "curiosity_gap", ["q1"], []), ("tension", "stakes", [], []),
        ("tension", "evidence", [], []), ("payoff", "final_payoff", [], ["q1"])]


def run(plan, lines=LINES):
    s = VideoScript(title="T", caption="c", hashtags=["#a"], scenes=[Scene(narration=n, visual_query="crow") for n in lines])
    return qp.inspect_short(s, "en", "none", [3.0] * len(lines), False, plan)


def story(rep):
    return [c for c in rep["checks"] if c["detector"].startswith("plan.story")]


@pytest.fixture(autouse=True)
def lib(tmp_path, monkeypatch):
    monkeypatch.setattr(qp, "ROOT", tmp_path)
    monkeypatch.setattr(qp, "ASSETS_DIR", tmp_path / "assets")


def test_a_good_story_passes():
    [c] = story(run(plan_for(GOOD)))
    assert c["status"] == "pass" and c["method"] == "inferred"


def test_weak_opening():
    beats = [("setup", "context", [], []), *GOOD[1:]]
    [c] = [c for c in story(run(plan_for(beats, loops=()))) if "opening" in c["detector"]]
    assert c["status"] == "warning" and c["scene"] == 0 and c["start"] == 0
    assert "raises no question" in c["title"] and c["recommendation"]


def test_missing_opening_starts_mid_story():
    beats = [("tension", "evidence", ["q1"], []), *GOOD[1:]]
    assert any("opens in its tension" in c["title"] for c in story(run(plan_for(beats))))


def test_unresolved_promise_points_at_where_it_was_raised():
    beats = [*GOOD[:3], ("payoff", "final_payoff", [], [])]
    found = {c["detector"].split(".")[2]: c for c in story(run(plan_for(beats)))}
    assert found["unresolved"]["scene"] == 0 and "never answered" in found["unresolved"]["title"]
    assert "payoff_mismatch" in found  # the payoff answers nothing the video asked
    assert found["payoff_mismatch"]["scene"] == 3 and found["payoff_mismatch"]["start"] == 9.0


def test_repetitive_escalation_is_flagged_once():
    lines = [LINES[0], "The crow bent a straight wire into a hook.", "The crow bent a straight wire into a hook again.", LINES[3]]
    beats = [GOOD[0], ("tension", "escalation", [], []), ("tension", "escalation", [], []), GOOD[3]]
    rep = run(plan_for(beats), lines)
    repeats = [c for c in rep["checks"] if c["detector"].startswith("story.repeat.")]
    assert repeats and repeats[0]["scene"] == 2 and repeats[0]["method"] == "heuristic"
    assert not any("repeat" in c["detector"] for c in story(rep))  # one finding, not two


def test_no_plan_or_unplanned_is_not_checked():
    for plan in (None, director_plan.from_scenes("t", "short", "en", "educational", [{"narration": n} for n in LINES])):
        [c] = story(run(plan))
        assert c["status"] == "not_checked" and c["method"] == "not_checked"


def test_every_check_is_labelled_and_the_plan_changes_the_fingerprint():
    a, b = run(plan_for(GOOD)), run(plan_for([*GOOD[:3], ("payoff", "final_payoff", [], [])]))
    assert all(c["method"] in ("measured", "heuristic", "inferred", "ai", "not_checked") for c in a["checks"])
    assert a["fingerprint"] != b["fingerprint"]  # a re-directed plan makes the old report outdated
    assert a["counts"]["fail"] == 0  # the technical checks still run alongside


def test_endpoint_reads_the_drafts_plan(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient

    from crcontent import web

    monkeypatch.setattr(drafts, "DRAFTS_DIR", tmp_path / "drafts")
    s = VideoScript(title="T", caption="c", hashtags=["#a"], scenes=[Scene(narration=n, visual_query="crow") for n in LINES])
    draft_id, _ = drafts.create(drafts.Draft(script=s, plan=plan_for([*GOOD[:3], ("payoff", "final_payoff", [], [])])))
    client = TestClient(web.app)
    body = {"script": s.model_dump(), "lengths": [3] * 4, "draft": draft_id}
    rep = client.post("/api/inspect/preview/short", json=body).json()
    assert any("never answered" in c["title"] for c in story(rep))
    for bad in ("../etc", "missing-draft"):  # no plan to read: not checked, never an error
        rep = client.post("/api/inspect/preview/short", json={**body, "draft": bad}).json()
        assert story(rep)[0]["status"] == "not_checked"


def test_a_plan_made_before_story_beats_is_not_checked_not_warned():
    plan = plan_for([("", "", [], [])] * 4, loops=())
    [c] = story(run(plan))
    assert c["status"] == "not_checked" and "AI Director" in c["description"]
