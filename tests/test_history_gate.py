"""Hidden History Files spec, milestone H7 core: the history gate (ready / review_required / blocked), approvals with
a note, rights that can't be waved through, render and publishing refusing an unchecked history video, and the
research sources in post.txt."""
import json

import pytest

from crcontent import director_plan, drafts
from crcontent.director_plan import Footage
from crcontent.history import gate, research
from crcontent.history.models import Evidence, HistoricalClaim, ResearchBrief, ResearchSource
from tests.test_director_plan import client  # noqa: F401  (fixture)

SCENES = [{"narration": "In 2012, lasers found a lost city under Cambodia's jungle.", "visual_query": "jungle"},
          {"narration": "Some say 40,000 people lived there.", "visual_query": "plateau"}]


def plan(**footage):
    p = director_plan.from_scenes("Lost City", "short", "en", "cinematic_history", SCENES)
    p.project.channel_profile_id = "hidden_history_files"
    p.scenes[0].claim_ids, p.scenes[1].claim_ids = ["c1"], ["c2"]
    p.shots[0].visual_origin, p.shots[1].visual_origin = "evidence", "context"
    for s in p.shots:
        s.footage = Footage(**{"source": "commons", "kind": "photo", "page": f"https://c/{s.id}", "licence": "CC BY-SA 4.0",
                               "asset_type": "photograph", "depicts": "actual", "rights": "licensed", **footage.get(s.id, {})})
    return p


def brief(status="approved"):
    s = ResearchSource(id="s1", url="https://uni.edu/lidar", title="Lidar at Phnom Kulen", publisher="uni.edu",
                       excerpts=["Mapped in 2012."])
    return ResearchBrief(id="b", sources=[s], research_status=status, revision=2, approved_revision=2, claims=[
        HistoricalClaim(id="c1", claim_text="Lidar found the city in 2012", status="supported", importance="central",
                        evidence=[Evidence(source_id="s1", excerpt="Mapped in 2012.")], source_ids=["s1"]),
        HistoricalClaim(id="c2", claim_text="40,000 people lived there", status="disputed", importance="supporting")])


def levels(verdict):
    return {it["key"].split(":")[0]: (it["level"], it["overridable"]) for it in verdict["items"]}


def test_unapproved_research_blocks():
    v = gate.evaluate(plan(), None, None)
    assert v["status"] == "blocked" and levels(v)["research"] == ("blocked", False)
    assert gate.evaluate(plan(), brief("needs_review"), None)["status"] == "blocked"  # edited after approval


def test_review_items_and_what_can_be_approved():
    p = plan(**{"shot-001-1": {"rights": "rights_unknown", "licence": "Rights not stated (Internet Archive item)",
                               "depicts": "illustrative"}})
    v = gate.evaluate(p, brief(), None)
    assert v["status"] == "review_required"
    assert levels(v) == {"claim": ("review", True), "rights": ("review", False), "standin": ("review", True)}


def test_wrong_period_blocks_evidence_but_only_reviews_context():
    p = plan(**{"shot-001-1": {"period_score": 2}, "shot-002-1": {"period_score": 2}})
    keys = {it["key"].split(":")[1]: it["level"] for it in gate.evaluate(p, brief(), None)["items"] if it["key"].startswith("period")}
    assert keys == {"shot-001-1": "blocked", "shot-002-1": "review"}


def test_hook_failure_and_missing_picture_need_review():
    p = plan()
    p.scenes[0].narration = "Welcome back! In 2012 lasers found a lost city."
    p.shots[1].footage = None
    keys = {it["key"] for it in gate.evaluate(p, brief(), None)["items"]}
    assert "hook:no_intro" in keys and "nofootage:shot-002-1" in keys


def test_approvals_need_a_reason_and_never_cover_rights_or_blockers(tmp_path):
    p = plan(**{"shot-001-1": {"rights": "rights_unknown", "depicts": "illustrative"}})
    b = brief()
    with pytest.raises(ValueError, match="Say why"):
        gate.approve(tmp_path, p, b, "claim:c2", "ok")
    with pytest.raises(ValueError, match="can't be approved"):
        gate.approve(tmp_path, p, b, "rights:shot-001-1:https://c/shot-001-1", "I checked it, it's fine")
    with pytest.raises(KeyError):
        gate.approve(tmp_path, p, b, "claim:nope", "a good reason here")
    gate.approve(tmp_path, p, b, "claim:c2", "Narration says 'some say': qualified")
    v = gate.approve(tmp_path, p, b, "standin:shot-001-1:https://c/shot-001-1", "Labelled 'illustration' on screen")
    assert v["status"] == "review_required"  # the rights item is still open
    p.shots[0].footage.rights, p.shots[0].footage.rights_note = "licensed", "Item page: public domain mark"
    v = gate.evaluate(p, b, tmp_path)
    assert v["status"] == "ready" and {a["key"].split(":")[0] for a in v["approved"]} == {"claim", "standin"}
    p.shots[0].footage.page = "https://c/another-picture"  # a new picture: its stand-in approval doesn't carry over
    assert gate.evaluate(p, b, tmp_path)["status"] == "review_required"


def test_sources_text_lists_what_the_claims_rest_on():
    assert gate.sources_text(plan(), brief()) == "- Lidar at Phnom Kulen (uni.edu): https://uni.edu/lidar"
    assert gate.sources_text(plan(), brief("needs_review")) == ""


# ---------- render and publishing ----------

def make_history_draft(client, p=None, b=None):  # noqa: F811
    from crcontent.script import VideoScript

    script = VideoScript(title="Lost City", scenes=[{"narration": s["narration"], "visual_query": "q"} for s in SCENES],
                         caption="", hashtags=[])
    draft_id, _ = drafts.create(drafts.Draft(script=script, plan=p or plan()))
    if b is not None:
        research.write(drafts.DRAFTS_DIR / draft_id / "research.json", b)
    return draft_id, script


def render_body(draft_id, script):
    return {"script": script.model_dump(), "topic": "Lost City", "lang": "en", "voice": "", "rate": "+5%",
            "music": "none", "draft_id": draft_id}


def test_render_refuses_an_unchecked_history_draft_and_records_the_verdict(client, monkeypatch, tmp_path):  # noqa: F811
    from crcontent import web

    draft_id, script = make_history_draft(client)
    r = client.post("/api/render", json=render_body(draft_id, script))
    assert r.status_code == 409 and "research isn't approved" in r.json()["detail"]

    research.write(drafts.DRAFTS_DIR / draft_id / "research.json", brief())
    r = client.post("/api/render", json=render_body(draft_id, script))
    assert r.status_code == 409 and "waiting for your review" in r.json()["detail"]
    r = client.post(f"/api/history/draft/{draft_id}/gate/approve", json={"key": "claim:c2", "note": "Qualified: 'some say'"})
    assert r.json()["status"] == "ready"
    assert client.post("/api/render", json=render_body(draft_id, script)).status_code == 200
    name, args = client.started[-1]
    assert name == "_run_render"

    # the render itself: post.txt gets the research sources, meta.json the verdict
    out = tmp_path / "video"
    out.mkdir()
    seen = {}

    def fake_make_video(topic, script, **kw):
        seen["sources"] = script.sources
        (out / "meta.json").write_text(json.dumps({"kind": "video"}), encoding="utf-8")
        return out / "video.mp4"

    monkeypatch.setattr(web, "make_video", fake_make_video)
    published = []
    monkeypatch.setattr(web, "_auto_publish", lambda folder, log: published.append(folder))
    web.jobs[args[0]]["status"] = "queued"
    web._run_render(*args)
    assert web.jobs[args[0]]["status"] == "done", web.jobs[args[0]]
    assert "https://uni.edu/lidar" in seen["sources"]
    meta = json.loads((out / "meta.json").read_text(encoding="utf-8"))
    assert meta["history_gate"]["status"] == "ready" and meta["history_gate"]["approved"][0]["key"] == "claim:c2"
    assert meta["channel_profile_id"] == "hidden_history_files" and web._history_publish_block(out) == ""


def test_ordinary_drafts_render_as_before(client):  # noqa: F811
    from crcontent.script import VideoScript

    script = VideoScript(title="Ravens", scenes=[{"narration": "Ravens bend wire.", "visual_query": "raven"}], caption="", hashtags=[])
    plain_id, _ = drafts.create(drafts.Draft(script=script))  # no plan at all
    assert client.post("/api/render", json=render_body(plain_id, script)).status_code == 200
    wild = director_plan.from_scenes("Ravens", "short", "en", "cinematic_wildlife", [{"narration": "Ravens bend wire."}])
    wild_id, _ = drafts.create(drafts.Draft(script=script, plan=wild))
    assert client.post("/api/render", json=render_body(wild_id, script)).status_code == 200


def test_rights_are_confirmed_with_a_note(client):  # noqa: F811
    p = plan(**{"shot-001-1": {"rights": "rights_unknown"}})
    draft_id, _ = make_history_draft(client, p, brief())
    assert client.post(f"/api/history/draft/{draft_id}/rights", json={"shot_id": "shot-001-1", "note": "ok"}).status_code == 400
    r = client.post(f"/api/history/draft/{draft_id}/rights", json={"shot_id": "shot-001-1", "note": "Item page: Public Domain Mark"})
    assert r.status_code == 200 and not any(it["key"].startswith("rights") for it in r.json()["items"])
    f = drafts.load(draft_id).plan.shots[0].footage
    assert (f.rights, f.rights_note) == ("licensed", "Item page: Public Domain Mark")


def test_publishing_needs_a_passing_verdict(client, monkeypatch, tmp_path):  # noqa: F811
    from crcontent import web

    folder = tmp_path / "20261107-120000-en-lost-city"
    folder.mkdir()
    (folder / "video.mp4").write_bytes(b"x")
    meta = {"kind": "video", "channel_profile_id": "hidden_history_files"}
    (folder / "meta.json").write_text(json.dumps(meta), encoding="utf-8")
    monkeypatch.setattr(web, "_video_dir", lambda name: folder)
    assert "history check" in web._history_publish_block(folder)
    assert client.post(f"/api/videos/{folder.name}/publish", json={"platforms": ["youtube"]}).status_code == 409
    assert client.post(f"/api/videos/{folder.name}/schedule", json={"platforms": ["youtube"], "at": "2099-01-01T09:00"}).status_code == 409
    logged = []
    monkeypatch.setattr(web.publish, "settings", lambda: pytest.fail("auto-publish must stop before reading settings"))
    web._auto_publish(folder, logged.append)
    assert logged and logged[0].startswith("Auto-upload skipped")
    (folder / "meta.json").write_text(json.dumps({**meta, "history_gate": {"status": "ready"}}), encoding="utf-8")
    assert web._history_publish_block(folder) == ""
    (folder / "meta.json").write_text(json.dumps({"kind": "video"}), encoding="utf-8")  # not history: as before
    assert web._history_publish_block(folder) == ""
