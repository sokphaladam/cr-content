"""Hidden History Files spec, milestone H7 (completion): claim/source/shot traceability, unsupported claims blocking,
credits for reconstructions and maps, and the history rows and three-state status in the render Quality Inspector."""
import json

from crcontent import quality
from crcontent.director_plan import Footage
from crcontent.history import gate
from crcontent.script import Clip
from tests.test_director_plan import client  # noqa: F401  (fixture)
from tests.test_history_gate import brief, make_history_draft, plan


def test_a_stated_unsupported_claim_blocks_and_cant_be_approved(tmp_path):
    b = brief()
    b.claims[1].status = "unsupported"
    v = gate.evaluate(plan(), b, None)
    it = next(i for i in v["items"] if i["key"] == "unsupported:c2")
    assert v["status"] == "blocked" and it["level"] == "blocked" and not it["overridable"]
    p = plan()
    p.scenes[1].claim_ids = ["gone"]
    assert "noclaim:gone" in {i["key"] for i in gate.evaluate(p, brief(), None)["items"]}


def test_a_doubtful_evidence_picture_needs_review():
    p = plan(**{"shot-001-1": {"match": "weak", "subject_score": 5, "problem": "a different manuscript"}})
    it = next(i for i in gate.evaluate(p, brief(), None)["items"] if i["key"].startswith("mismatch:"))
    assert it["level"] == "review" and "a different manuscript" in it["detail"]


def test_trace_points_claims_to_sources_and_names_the_material():
    p = plan(**{"shot-002-1": {"source": "reconstruction", "asset_type": "reconstruction", "depicts": "illustrative"}})
    t = gate.trace(p, brief())
    c1, c2 = t["claims"]
    assert c1["scenes"] == [1] and c1["sources"] == [{"title": "Lidar at Phnom Kulen", "url": "https://uni.edu/lidar"}]
    assert c2["status"] == "disputed" and c2["sources"] == []
    assert [s["material"] for s in t["shots"]] == ["photograph", "AI reconstruction"]


def test_credits_name_reconstructions_and_map_sources():
    p = plan(**{"shot-002-1": {"asset_type": "reconstruction"}})
    clips = [Clip(id="g1", track="graphics", template="HistoryMap", props={
        "map_source": "Natural Earth", "region_geojson": "{}", "region_source": "https://maps.example/khmer", "region_dates": "1150-1220"})]
    text = gate.credits_text(p, clips)
    assert "AI reconstruction (illustrative, not archival footage): shot-002-1" in text
    assert "- Map: Natural Earth" in text and "Historical region (1150-1220): https://maps.example/khmer" in text
    assert gate.credits_text(plan()) == ""


def checks_for(tmp_path, meta):
    (tmp_path / "meta.json").write_text(json.dumps(meta), encoding="utf-8")
    checks, result = [], {"checks": []}
    quality.history_checks(checks, tmp_path, result)
    result["checks"] = checks
    return checks, result


def test_inspector_rows_and_three_states(tmp_path):
    p = plan(**{"shot-001-1": {"rights": "rights_unknown", "rights_note": "Item page: Public Domain Mark"},
                "shot-002-1": {"asset_type": "stock", "depicts": "illustrative"}})
    p.shots[1].visual_origin = "evidence"
    g = {"status": "ready", "checked_at": "t", "approved": [{"key": "claim:c2", "title": "Scene 2 states a disputed claim",
                                                             "note": "Qualified: some say", "at": "t"}],
         "open": [], "trace": gate.trace(p, brief())}
    checks, result = checks_for(tmp_path, {"channel_profile_id": "hidden_history_files", "history_gate": g})
    by = {c["id"]: c for c in checks}
    assert by["history.gate"]["status"] == "pass"
    assert by["history.approved.claim:c2"]["status"] == "pass" and "Qualified" in by["history.approved.claim:c2"]["description"]
    assert by["history.claim.c1"]["status"] == "pass" and "Lidar at Phnom Kulen" in by["history.claim.c1"]["description"]
    assert by["history.claim.c2"]["status"] == "warning"
    assert "rights confirmed" in by["history.shot.shot-001-1"]["title"]
    assert by["history.shot.shot-002-1"]["status"] == "warning" and "modern stock" in by["history.shot.shot-002-1"]["title"]
    assert quality.history_status(result) == "review_required"
    for c in checks:
        if c["status"] == "warning":
            c["disposition"] = "reviewed"
    assert quality.history_status(result) == "ready"


def test_source_and_rights_failures_cant_be_dismissed(tmp_path):
    b = brief()
    b.claims[0].source_ids, b.claims[0].status = [], "unsupported"
    p = plan(**{"shot-001-1": {"rights": "rights_unknown"}})
    checks, result = checks_for(tmp_path, {"channel_profile_id": "hidden_history_files",
                                           "history_gate": {"status": "ready", "trace": gate.trace(p, b)}})
    fails = {c["id"] for c in checks if c["status"] == "fail"}
    assert fails == {"history.claim.c1", "history.rights.shot-001-1"}
    for c in checks:
        c["disposition"] = "dismissed"
    assert quality.history_status(result) == "blocked"
    checks, result = checks_for(tmp_path, {"channel_profile_id": "hidden_history_files"})  # rendered before H7
    assert checks[0]["id"] == "history.gate" and quality.history_status(result) == "blocked"


def test_other_videos_get_no_history_rows(tmp_path):
    checks, result = checks_for(tmp_path, {"channel_profile_id": "wildlife_facts"})
    assert checks == [] and "history" not in result


def test_gate_api_returns_the_trace(client):  # noqa: F811
    draft_id, _ = make_history_draft(client, plan(), brief())
    t = client.get(f"/api/history/draft/{draft_id}/gate").json()["trace"]
    assert [c["id"] for c in t["claims"]] == ["c1", "c2"] and len(t["shots"]) == 2
