"""The AI Director in Shorts Mode: a plan per episode that steers the beat searches and shows the chosen clips."""
import json

import pytest

from crcontent.longform.parse import Scene, Script
from crcontent.shorts import directed, plan, queries


def _ep(voice=("Octopuses have three hearts.", "And blue blood.")):
    scenes = [Scene(i, 0, f"octopus shot {i}", f"TEXT {i}", v) for i, v in enumerate(voice, 1)]
    return plan.ShortPlan(1, "Octopus", Script("Octopus", "octopus", "en", scenes), animal_search="octopus")


def _directed(p):
    out = p.model_copy(deep=True)
    out.planned_by = "ai"
    first = out.shots[0]
    out.shots.insert(1, first.model_copy(update={"id": "shot-001-2", "shot_type": "close_up",
                                                 "visual_description": "octopus heart close-up"}))
    return out


def test_plan_for_directs_keeps_and_replans(tmp_path):
    ep, calls = _ep(), []
    direct = lambda p: calls.append(1) or _directed(p)
    p = directed.plan_for(ep, tmp_path, log=lambda *_: None, direct=direct)
    assert p.planned_by == "ai" and [s.narration for s in p.scenes] == [s.voiceover for s in ep.script.scenes]
    assert (tmp_path / "plan.json").exists()
    assert directed.plan_for(ep, tmp_path, log=lambda *_: None, direct=direct) == p and len(calls) == 1  # kept
    ep.script.scenes[1].voiceover = "And green blood."
    directed.plan_for(ep, tmp_path, log=lambda *_: None, direct=direct)
    assert len(calls) == 2  # the voiceover changed: planned again

    def broken(_):
        raise RuntimeError("nonsense")

    fallback = directed.plan_for(_ep(("Other words.",)), tmp_path, log=lambda *_: None, direct=broken)
    assert fallback.planned_by == "script" and len(fallback.shots) == 1


def test_shot_notes_and_queries_follow_the_director(monkeypatch):
    ep = _ep()
    p = _directed(directed.seed(ep))
    notes = directed.shot_notes(p)
    assert notes[1].endswith("then close up: octopus heart close-up") and directed.shot_notes(directed.seed(ep)) == {}
    assert directed._plain("cat head centered in vertical frame looking down") == "cat head looking down"
    asked = []

    def ask(prompt, schema, max_tokens=4000):
        asked.append(prompt)
        return {"beats": [{"beat": s.n, "shot": "x", "queries": ["octopus"], "key_objects": [], "reuse_opening": False}
                          for s in ep.script.scenes]}

    monkeypatch.setattr(queries, "_ask", ask)
    queries.plan(ep, lambda *_: None, notes)
    assert "DIRECTOR'S SHOTS: " in asked[0] and "the director's first shot" in asked[0]
    queries.plan(ep, lambda *_: None)
    assert "DIRECTOR" not in asked[1]  # no plan: the prompt is as before


def test_record_puts_each_beats_clip_on_its_first_shot():
    p = _directed(directed.seed(_ep()))
    entries = [{"scene": 1, "query": "octopus", "match": 8, "flags": [],
                "chosen": {"source": "pixabay", "kind": "video", "file": "a.mp4", "page": "p"}},
               {"scene": 2, "query": "octopus", "match": 0, "flags": ["needs your own clip"],
                "chosen": {"source": "card", "kind": "image", "file": "card.png"}}]
    out = directed.record(p, entries, "job1")
    a, b = out.shots[0].footage, out.shots[2].footage
    assert a.match == "good" and a.thumb == "/media/job1/storyboard/scene-01.jpg" and out.shots[1].footage is None
    assert b.match == "weak" and b.kind == "photo" and out.shots[2].warnings == ["needs your own clip"]


@pytest.fixture
def short_job(tmp_path, monkeypatch):
    from crcontent import web

    monkeypatch.setattr(web, "OUTPUT_DIR", tmp_path)
    job = tmp_path / "20261103-en-ep01-octopus"
    job.mkdir()
    (job / "meta.json").write_text(json.dumps({"kind": "short"}), encoding="utf-8")
    ep = _ep()
    ep.save(job / "episode.json")
    ep.script.save(job / "scenes.json")
    return job


def test_plan_endpoints_for_a_shorts_job(short_job, monkeypatch):
    from fastapi.testclient import TestClient

    from crcontent import web

    client = TestClient(web.app)
    url = f"/api/plans/short/{short_job.name}"
    r = client.get(url)  # made before the AI Director: one shot per beat
    assert r.status_code == 200, r.text
    assert len(r.json()["shots"]) == 2 and r.json()["planned_by"] == "script"
    submitted = []
    monkeypatch.setattr(web.renderer, "submit", lambda *a: submitted.append(a))
    r = client.post(f"{url}/footage", json={"shots": []})
    assert r.status_code == 200 and submitted[0][0] is web._run_shorts and submitted[0][3] == short_job.resolve()
    assert web.jobs[r.json()["id"]]["kind"] == "short"
    web.jobs[r.json()["id"]]["status"] = "done"
    assert client.post(f"{url}/assemble", json={}).status_code == 400
    assert client.post(f"{url}/shots/shot-001-1/pick", json={"index": 0}).status_code == 400
