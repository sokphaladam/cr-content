"""Hidden History Files spec, milestone H3: history direction, the history hook judge, scripts from research, and
backward-compatible plans. Gemini is stubbed."""
import json

import pytest

from crcontent import ai_director, director_plan, drafts
from crcontent.history import hook, script as hscript
from crcontent.history.models import Evidence, HistoricalClaim, ResearchBrief, ResearchSource
from tests.test_ai_director import ANSWER, FakeClient, shot
from tests.test_director_plan import client  # noqa: F401  (fixture)
from tests.test_history_research import FakeClient as JsonClient

HISTORY_SCENES = [
    {"narration": "In 2012, lasers found a lost city under Cambodia's jungle.", "visual_query": "jungle aerial"},
    {"narration": "Mahendraparvata sits on the Phnom Kulen plateau.", "visual_query": "Phnom Kulen"},
]


@pytest.fixture(autouse=True)
def no_cache(tmp_path, monkeypatch):
    from crcontent.shorts import analytics

    monkeypatch.setattr(ai_director, "CACHE", tmp_path / "director")
    row = {"tag": "octopus", "videos": 5, "views": 5000, "stayed": 60.0, "viewed": 70.0}
    data = {"imported": "2026-11-05T10:00:00", "videos": [{}] * 9,
            "summary": {"hook_style": [], "length": [], "animal": [row, {**row, "tag": "raven"}]}}
    path = tmp_path / "analytics.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    monkeypatch.setattr(analytics, "PATH", path)  # the wildlife channel's numbers, with animal subjects


def history_plan(profile="hidden_history_files", style="cinematic_history"):
    plan = director_plan.from_scenes("Lost City", "short", "en", style, HISTORY_SCENES)
    plan.project.channel_profile_id = profile
    return plan


def history_answer(origin="evidence", first_subject="lidar map of Mahendraparvata"):
    a = json.loads(json.dumps(ANSWER))
    a["story"]["payoff"] = "The city was mapped by lidar"
    a["scenes"] = [
        {**ANSWER["scenes"][0], "phase": "setup", "shots": [shot(subject=first_subject, visual_origin=origin,
                                                                 visual_description="lidar map of a city grid",
                                                                 footage_queries=["Mahendraparvata lidar map"])]},
        {**ANSWER["scenes"][1], "scene_id": "scene-002", "phase": "payoff",
         "shots": [shot(visual_origin="nonsense", subject="Phnom Kulen plateau")]}]
    return a


def approved_brief(**claim_kw):
    s = ResearchSource(id="s1", url="https://uni.edu/a", excerpts=["Mapped in 2012."])
    claims = [HistoricalClaim(id="c1", claim_text="Lidar mapped the city in 2012", status="supported", importance="central",
                              evidence=[Evidence(source_id="s1", excerpt="Mapped in 2012.")], script_scene_ids=["scene-001"]),
              HistoricalClaim(id="c2", claim_text="It held 40,000 people", status="disputed", importance="supporting",
                              script_scene_ids=["scene-002"]),
              HistoricalClaim(id="c3", claim_text="Aliens built it", status="unsupported", importance="central",
                              script_scene_ids=["scene-001"])]
    for c in claims:
        for k, v in claim_kw.get(c.id, {}).items():
            setattr(c, k, v)
    return ResearchBrief(id="b", topic="Mahendraparvata", sources=[s], claims=claims, research_status="approved",
                         revision=3, approved_revision=3)


# ---------- routing: history vs every other project ----------

def test_history_profile_gets_history_direction_without_wildlife_numbers():
    client = FakeClient(history_answer())
    plan = ai_director.direct(history_plan(), client=client)
    call = client.calls[0]
    assert "Hidden History Files" in call["system"] and "visual_origin" in call["system"]
    sent = call["messages"][0]["content"]
    assert "octopus" not in sent and "30-50 seconds" in sent  # no wildlife analytics; the history Short format
    shot_schema = call["output_config"]["format"]["schema"]["properties"]["scenes"]["items"]["properties"]["shots"]["items"]
    assert "visual_origin" in shot_schema["required"]
    assert [s.visual_origin for s in plan.shots] == ["evidence", ""]  # an unknown origin is dropped


def test_same_script_under_wildlife_keeps_wildlife_behaviour():
    client = FakeClient(ANSWER)
    plan = history_plan(profile="wildlife_facts", style="cinematic_wildlife")
    ai_director.direct(plan, client=client)
    call = client.calls[0]
    assert call["system"] == ai_director.SYSTEM  # untouched
    assert "octopus" in call["messages"][0]["content"] and "22-30 seconds" in call["messages"][0]["content"]
    assert "visual_origin" not in json.dumps(call["output_config"])
    assert "visual_origin" not in json.dumps(ai_director.SCHEMA)  # the shared schema was not mutated


def test_style_alone_routes_to_history():
    assert ai_director.is_history(history_plan(profile="", style="cinematic_history"))
    assert not ai_director.is_history(history_plan(profile="", style="cinematic_documentary"))
    assert ai_director.is_history(history_plan(profile="hidden_history_files", style="educational"))


# ---------- approved research in the plan ----------

def test_approved_research_reaches_the_director_and_the_plan():
    client = FakeClient(history_answer())
    plan = ai_director.direct(history_plan(), client=client, research=approved_brief())
    sent = client.calls[0]["messages"][0]["content"]
    assert "[disputed] It held 40,000 people" in sent and "Aliens" not in sent  # unsupported never offered
    assert [s.claim_ids for s in plan.scenes] == [["c1"], ["c2"]]
    assert plan.story.key_facts == ["Lidar mapped the city in 2012"] and plan.story.research_revision == 3


def test_unapproved_research_links_nothing():
    brief = approved_brief()
    brief.research_status = "needs_review"  # edited after approval
    plan = ai_director.link_research(history_plan(), brief)
    assert plan.scenes[0].claim_ids == [] and plan.story.research_revision == 0
    assert ai_director._research_block(brief) == ""


def test_old_plans_load_without_history_fields():
    plan = history_plan().model_dump()
    for s in plan["scenes"]:
        del s["claim_ids"]
    for s in plan["shots"]:
        del s["visual_origin"]
    del plan["story"]["research_revision"]
    loaded = director_plan.load(plan)
    assert loaded.shots[0].visual_origin == "" and loaded.scenes[0].claim_ids == [] and loaded.story.research_revision == 0


# ---------- history hook judge ----------

def directed(narration, origin="evidence", subject="lidar map of the lost city", payoff=True, claim_ids=()):
    plan = history_plan()
    plan.scenes[0].narration = narration
    plan.scenes[0].claim_ids = list(claim_ids)
    plan.planned_by = "ai"
    first = plan.shots[0]
    first.visual_origin, first.subject, first.visual_description, first.footage_queries = origin, subject, subject, [subject]
    plan.story.payoff = "Lidar revealed it" if payoff else ""
    plan.scenes[-1].phase = "payoff" if payoff else ""
    return plan


def status(findings):
    return {f["key"]: f["status"] for f in findings}


def test_a_specific_truthful_hook_passes():
    f = hook.judge(directed("In 2012, lasers found a lost city under Cambodia's jungle."))
    assert set(status(f).values()) == {"pass"} and hook.score(f) == 100


def test_hook_problems_are_named():
    s = status(hook.judge(directed("Welcome back! Today we talk about something really old.", origin="reconstruction",
                                   payoff=False)))
    assert s == {"no_intro": "fail", "concrete": "warning", "curiosity": "warning", "clarity": "warning",
                 "truthful": "pass", "first_visual": "warning", "payoff": "warning"}
    s = status(hook.judge(directed("Nobody knows who built the cursed city of Mahendraparvata.")))
    assert s["truthful"] == "warning"


def test_disputed_claim_in_hook_needs_qualifying_words():
    brief = approved_brief()
    bare = directed("Mahendraparvata held 40,000 people in 802.", claim_ids=["c2"])
    assert status(hook.judge(bare, brief))["truthful"] == "fail"
    hedged = directed("Mahendraparvata may have held 40,000 people in 802.", claim_ids=["c2"])
    assert status(hook.judge(hedged, brief))["truthful"] == "pass"


def test_first_visual_must_match_the_hook():
    s = status(hook.judge(directed("In 2012, lasers found a lost city under Cambodia's jungle.", subject="sunset beach")))
    assert s["first_visual"] == "warning"
    seeded = history_plan()  # not directed yet: the picture and payoff aren't judged
    assert {k: v for k, v in status(hook.judge(seeded)).items() if k in ("first_visual", "payoff")} == \
        {"first_visual": "not_checked", "payoff": "not_checked"}


def test_preflight_uses_history_hook_only_for_history():
    from crcontent import quality_preview as qp
    from crcontent.script import VideoScript

    script = VideoScript(title="T", scenes=[{"narration": s["narration"], "visual_query": "q"} for s in HISTORY_SCENES],
                         caption="", hashtags=[])
    ids = {c["detector"] for c in qp.inspect_short(script, "en", "none", [4, 4], False, history_plan())["checks"]}
    assert {"history.hook.no_intro", "history.hook.concrete"} <= ids
    wildlife = history_plan(profile="wildlife_facts", style="cinematic_wildlife")
    ids = {c["detector"] for c in qp.inspect_short(script, "en", "none", [4, 4], False, wildlife)["checks"]}
    assert not any(i.startswith("history.") for i in ids)


# ---------- the script from research ----------

def test_script_written_only_from_approved_claims():
    brief = approved_brief()
    with pytest.raises(ValueError, match="Approve"):
        hscript.write(brief.model_copy(update={"research_status": "needs_review"}))
    fake = JsonClient({"title": "The City Under the Jungle", "scenes": [
        {"stage": "hook", "narration": "In 2012, lasers found a city.", "visual": "lidar map", "claim_ids": ["c1", "c-made-up"]},
        {"stage": "context", "narration": "Aliens built it.", "visual": "temple", "claim_ids": ["c3"]},
        {"stage": "revelation", "narration": "  ", "visual": "", "claim_ids": []}]})
    out = hscript.write(brief, 40, fake)
    sent = fake.calls[0]["messages"][0]["content"]
    assert "c1 [supported, central]" in sent and "c2 [disputed" in sent and "c3" not in sent and "104 words" in sent
    assert [s["claim_ids"] for s in out["scenes"]] == [["c1"], ["c3"]]  # invented id dropped, empty scene skipped
    assert any("without a source" in w for w in out["warnings"])
    assert out["text"].startswith("The City Under the Jungle\n\nScene 1\nVisual: lidar map\nVoiceover: In 2012")


def test_attach_links_claims_to_resplit_scenes():
    brief = approved_brief()
    written = [{"narration": "In 2012, lasers found a city. It sits on Phnom Kulen.", "claim_ids": ["c1"]},
               {"narration": "Some say 40,000 lived there.", "claim_ids": ["c2"]}]
    out = hscript.attach(brief, written, ["scene-001", "scene-002", "scene-003"],
                         ["In 2012, lasers found a city.", "It sits on Phnom Kulen.", "Some say 40,000 lived there."])
    assert {c.id: c.script_scene_ids for c in out.claims} == {"c1": ["scene-001", "scene-002"], "c2": ["scene-003"], "c3": []}


# ---------- the API: topic brief -> script -> Short keeps the research ----------

TOPIC_SCRIPT = """The City Under the Jungle

Scene 1
Visual: lidar map
Voiceover: In 2012, lasers found a lost city under Cambodia's jungle.

Scene 2
Visual: plateau
Voiceover: Some say 40,000 people lived there.
"""


def test_api_topic_script_to_short(client, monkeypatch, tmp_path):  # noqa: F811
    from crcontent import web
    from crcontent.history import research

    monkeypatch.setattr(web, "ROOT", tmp_path)
    brief = approved_brief()
    brief.id, brief.project_kind, brief.project_ref = "abcdef0123", "topic", "abcdef0123"
    research.write(tmp_path / "research" / "abcdef0123.json", brief)
    monkeypatch.setenv("GEMINI_API_KEY", "x")
    monkeypatch.setattr(hscript, "write", lambda b, t: {"title": "T", "text": TOPIC_SCRIPT, "warnings": [], "scenes": [
        {"stage": "hook", "narration": "In 2012, lasers found a lost city under Cambodia's jungle.", "visual": "", "claim_ids": ["c1"]},
        {"stage": "context", "narration": "Some say 40,000 people lived there.", "visual": "", "claim_ids": ["c2"]}]})
    r = client.post("/api/research/topic/abcdef0123/script", json={"target_seconds": 40})
    assert r.status_code == 200, r.text
    assert research.load(tmp_path / "research" / "abcdef0123.json").research_status == "approved"  # still approved

    monkeypatch.delenv("GEMINI_API_KEY")  # the basic reader, no Director: the claims are still linked
    r = client.post("/api/script-video", json={"text": TOPIC_SCRIPT, "format": "short", "channel_profile_id": "hidden_history_files",
                                               "research_brief_id": "abcdef0123"})
    assert r.status_code == 200, r.text
    draft_id = r.json()["id"]
    plan = drafts.load(draft_id).plan
    assert [s.claim_ids for s in plan.scenes] == [["c1"], ["c2"]] and plan.story.research_revision == 3
    copied = research.load(drafts.DRAFTS_DIR / draft_id / "research.json")
    assert copied.project_kind == "draft" and copied.project_ref == draft_id and copied.research_status == "approved"
    assert client.post("/api/script-video", json={"text": TOPIC_SCRIPT, "format": "long",
                                                  "research_brief_id": "abcdef0123"}).status_code == 400


def test_api_approve_links_research_into_the_draft_plan(client, monkeypatch):  # noqa: F811
    from crcontent.history import research

    draft_id = client.post("/api/script-video", json={"text": TOPIC_SCRIPT, "format": "short",
                                                      "channel_profile_id": "hidden_history_files"}).json()["id"]
    brief = approved_brief()
    brief.research_status, brief.approved_revision = "needs_review", 0
    research.write(drafts.DRAFTS_DIR / draft_id / "research.json", brief)
    assert client.post(f"/api/research/draft/{draft_id}/approve").status_code == 409  # c3: central, unsupported
    brief.claims = brief.claims[:2]
    research.write(drafts.DRAFTS_DIR / draft_id / "research.json", brief)
    assert client.post(f"/api/research/draft/{draft_id}/approve").status_code == 200
    plan = drafts.load(draft_id).plan
    assert plan.scenes[0].claim_ids == ["c1"] and plan.story.key_facts == ["Lidar mapped the city in 2012"]


def test_script_infers_missing_claim_ids_and_flags_a_flat_hook():
    brief = approved_brief()  # c1 "Lidar mapped the city in 2012", c2 disputed "It held 40,000 people"
    fake = JsonClient({"title": "T", "scenes": [
        {"stage": "hook", "narration": "This city is very large.", "visual": "", "claim_ids": []},
        {"stage": "context", "narration": "In 2012 lidar mapped the whole city.", "visual": "", "claim_ids": []},
        {"stage": "revelation", "narration": "Some say 40,000 people lived there.", "visual": "", "claim_ids": []}]})
    out = hscript.write(brief, 40, fake)
    assert [s["claim_ids"] for s in out["scenes"]] == [[], ["c1"], ["c2"]]  # matched by repeated words and numbers
    assert any("without raising a question" in w for w in out["warnings"])
