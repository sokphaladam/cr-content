"""Hidden History Files spec, milestone H2: research briefs, sources, claims and the evidence rule. No network:
providers and Gemini are stubbed."""
import json
from types import SimpleNamespace

import pytest
import requests

from crcontent import drafts
from crcontent.history import claims as cl
from crcontent.history import research, sources as src
from crcontent.history.models import Evidence, HistoricalClaim, ResearchBrief, ResearchSource
from tests.test_director_plan import client  # noqa: F401  (fixture)


class FakeClient:
    """Answers each structured call in turn; post() is the grounded call (raw Gemini JSON)."""

    def __init__(self, *answers, grounded=None):
        self.answers, self.grounded, self.calls = list(answers), grounded, []
        outer = self

        class messages:
            @staticmethod
            def create(**kw):
                outer.calls.append(kw)
                return SimpleNamespace(content=[SimpleNamespace(type="text", text=json.dumps(outer.answers.pop(0)))],
                                       stop_reason="end_turn")

        self.beta = SimpleNamespace(messages=messages)

    def post(self, model, body):
        assert body["tools"] == [{"google_search": {}}]
        return self.grounded


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    monkeypatch.setattr(src, "CACHE", tmp_path / "cache")
    monkeypatch.setattr(src, "_resolve", lambda uri: uri)  # grounding redirects: no network


def source(sid, url, *excerpts, error=""):
    return ResearchSource(id=sid, url=url, publisher=url.split("/")[2], excerpts=list(excerpts), retrieval_error=error)


def claim(cid, text, importance="central", *evidence, status="unsupported", locked=False):
    return HistoricalClaim(id=cid, claim_text=text, importance=importance, evidence=list(evidence), status=status, locked=locked)


# ---------- the evidence rule (settle) ----------

def test_supported_needs_attached_evidence_not_a_models_word():
    brief = ResearchBrief(id="b", sources=[source("s1", "https://museum.org/a", "Built in 1113.")], claims=[
        claim("c1", "Built in 1113", "central", Evidence(source_id="s1", excerpt="Built in 1113.")),
        claim("c2", "Hidden for 1000 years", "central", status="supported"),  # a model said so, nothing attached
        claim("c3", "Fake", "central", Evidence(source_id="s-invented", excerpt="made up"), status="supported"),
        claim("c4", "Empty excerpt", "central", Evidence(source_id="s1", excerpt="  "), status="supported"),
    ])
    cl.settle(brief)
    status = {c.id: c.status for c in brief.claims}
    assert status == {"c1": "supported", "c2": "unsupported", "c3": "unsupported", "c4": "unsupported"}
    assert brief.claims[0].source_ids == ["s1"] and brief.claims[2].evidence == []


def test_conflicting_sources_stay_visible():
    brief = ResearchBrief(id="b", sources=[source("s1", "https://uni.edu/a", "800 AD"), source("s2", "https://museum.org/b", "not before 900")],
                          claims=[claim("c1", "Founded in 802", "central", Evidence(source_id="s1", excerpt="800 AD"),
                                        Evidence(source_id="s2", excerpt="not before 900", stance="disputes"))])
    cl.settle(brief)
    assert brief.claims[0].status == "disputed"
    assert brief.contradictions[0].claim_id == "c1" and set(brief.contradictions[0].source_ids) == {"s1", "s2"}
    cl.settle(brief)
    assert len(brief.contradictions) == 1  # settling again doesn't repeat it


def test_wikipedia_alone_cannot_back_a_central_claim():
    wiki = source("w", "https://en.wikipedia.org/wiki/X", "Built in 1113.")
    brief = ResearchBrief(id="b", sources=[wiki], claims=[
        claim("c1", "Built in 1113", "central", Evidence(source_id="w", excerpt="Built in 1113.")),
        claim("c2", "Built in 1113", "supporting", Evidence(source_id="w", excerpt="Built in 1113."))])
    cl.settle(brief)
    assert [c.status for c in brief.claims] == ["uncertain", "supported"]
    assert "Wikipedia only" in brief.claims[0].notes


def test_creator_can_lower_but_not_raise_a_status():
    s = source("s1", "https://museum.org/a", "x")
    brief = ResearchBrief(id="b", sources=[s], claims=[
        claim("c1", "a", "central", Evidence(source_id="s1", excerpt="x"), status="uncertain", locked=True),
        claim("c2", "b", "central", status="supported", locked=True),
        claim("c3", "c", "central", status="uncertain", locked=True)])
    cl.settle(brief)
    assert [c.status for c in brief.claims] == ["uncertain", "unsupported", "uncertain"]


# ---------- sources ----------

def test_duplicate_sources_merge_however_linked():
    a = ResearchSource(id=src.source_id("https://www.Museum.org/page/"), url="https://www.Museum.org/page/", excerpts=["one"])
    b = ResearchSource(id=src.source_id("http://museum.org/page?utm_source=x#top"), url="http://museum.org/page?utm_source=x#top",
                       excerpts=["one", "two"])
    assert a.id == b.id
    merged = src.merge([a], [b])
    assert len(merged) == 1 and merged[0].excerpts == ["one", "two"]


def test_inaccessible_url_is_kept_but_is_not_evidence(monkeypatch):
    def down(*a, **k):
        raise requests.ConnectionError()
    monkeypatch.setattr(src.requests, "get", down)
    s = src.add_url("https://gone.example.org/paper", note="from a book")
    assert s.retrieval_error and s.excerpts == [] and s.title == "gone.example.org"
    assert cl.segments([s]) == {}  # nothing to cite until the creator adds the passage
    with pytest.raises(ValueError):
        src.add_url("javascript:alert(1)")
    s2 = src.add_url("https://gone.example.org/paper", excerpt="The passage.", title="Paper")
    assert list(cl.segments([s2]).values()) == [(s2.id, "The passage.")]


GROUNDED = {"candidates": [{"content": {"parts": [{"text": "Mahendraparvata is on Phnom Kulen. LiDAR mapped it in 2012."}]},
                            "groundingMetadata": {
                                "groundingChunks": [{"web": {"uri": "https://g/redirect1", "title": "nature.com"}},
                                                    {"web": {"uri": "https://g/redirect2", "title": "unused.com"}}],
                                "groundingSupports": [{"segment": {"text": "LiDAR mapped it in 2012."}, "groundingChunkIndices": [0, 7]}]}}]}


def test_grounding_keeps_only_pages_the_answer_rests_on():
    text, found = src.parse_grounding(GROUNDED)
    assert text.startswith("Mahendraparvata")
    assert [(s.publisher, s.excerpts, s.provider) for s in found] == [("nature.com", ["LiDAR mapped it in 2012."], "google_search")]
    assert src.parse_grounding({"candidates": []}) == ("", [])


def test_providers_without_key_or_network_report_instead_of_inventing(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    assert src.google("Angkor")[1] == [] and "Gemini key" in src.google("Angkor")[2]

    def down(*a, **k):
        raise requests.ConnectionError()
    monkeypatch.setattr(src.requests, "get", down)
    found, note = src.wikipedia("Angkor")
    assert found == [] and "couldn't be searched" in note


# ---------- claims ----------

def test_script_splits_into_atomic_claims_with_scene_ids():
    fake = FakeClient({"claims": [
        {"text": "Mahendraparvata lies on Phnom Kulen", "type": "location", "importance": "central", "scene_ids": ["scene-001", "scene-999"]},
        {"text": "mahendraparvata lies on Phnom Kulen.", "type": "location", "importance": "central"},  # duplicate
        {"text": "LiDAR mapped it in 2012", "type": "nonsense", "importance": "huge"}]})
    out = cl.extract([("scene-001", "Mahendraparvata lies on Phnom Kulen. LiDAR mapped it in 2012.")], fake)
    assert [c.claim_text for c in out] == ["Mahendraparvata lies on Phnom Kulen", "LiDAR mapped it in 2012"]
    assert out[0].script_scene_ids == ["scene-001"]  # the invented scene id is dropped
    assert (out[1].claim_type, out[1].importance) == ("event", "supporting")


def test_basic_split_without_gemini():
    out = cl.basic_split([("scene-001", "It was huge. In 2012 lasers found it. Wow!")])
    assert [c.claim_text for c in out] == ["In 2012 lasers found it."]


def test_hallucinated_mapping_is_dropped():
    brief = ResearchBrief(id="b", sources=[source("s1", "https://uni.edu/a", "Mapped by LiDAR in 2012.")],
                          claims=[claim("c1", "LiDAR mapped it in 2012"), claim("c2", "It held a million people")])
    fake = FakeClient({"claims": [
        {"id": "c1", "evidence": [{"excerpt_id": "s1#0", "stance": "supports"}, {"excerpt_id": "s1#0", "stance": "supports"}]},
        {"id": "c2", "evidence": [{"excerpt_id": "s9#0", "stance": "supports"}]},       # no such excerpt
        {"id": "c-new", "evidence": [{"excerpt_id": "s1#0", "stance": "supports"}]}],   # no such claim
        "summary": "Mapped in 2012.", "contradictions": [{"claim_id": "c-ghost", "note": "x"}]})
    cl.settle(cl.map_evidence(brief, fake))
    assert [(c.id, c.status, len(c.evidence)) for c in brief.claims] == [("c1", "supported", 1), ("c2", "unsupported", 0)]
    assert brief.contradictions == [] and brief.summary == "Mapped in 2012."


# ---------- the whole run, storage and approval ----------

def test_topic_run_end_to_end(tmp_path):
    path = tmp_path / "research" / "t.json"
    brief = research.new("topic", "t", "The lost city under Cambodia's jungle")
    wiki = source("w", "https://en.wikipedia.org/wiki/Mahendraparvata", "Mahendraparvata is an Angkorian-era city.")
    fake = FakeClient(
        {"claims": [{"text": "LiDAR mapped Mahendraparvata in 2012", "type": "event", "importance": "central"},
                    {"text": "It was the first capital", "type": "interpretation", "importance": "central"}]},
        {"claims": [{"id": cl.claim_id("LiDAR mapped Mahendraparvata in 2012"), "evidence": [{"excerpt_id": None, "stance": "supports"}]}],
         "period": "9th century"},
        grounded=GROUNDED)
    # the second answer's excerpt id is filled in once the grounded source's id is known
    _, found = src.parse_grounding(GROUNDED)
    fake.answers[1]["claims"][0]["evidence"][0]["excerpt_id"] = f"{found[0].id}#0"
    out = research.run(path, brief, [], log=lambda *_: None, client=fake, wikipedia=lambda q, *a: ([wiki], ""))
    assert out.research_status == "needs_review" and out.revision == 1 and out.period == "9th century"
    assert sorted(s.publisher for s in out.sources) == ["en.wikipedia.org", "nature.com"]
    status = {c.claim_text: c.status for c in out.claims}
    assert status == {"LiDAR mapped Mahendraparvata in 2012": "supported", "It was the first capital": "unsupported"}
    assert research.load(path) == out
    with pytest.raises(ValueError, match="first capital"):
        research.approve(path)  # a central claim without a source blocks approval


def test_edit_locks_claims_and_approval_is_versioned(tmp_path):
    path = tmp_path / "research.json"
    s = source("s1", "https://museum.org/a", "Built in 1113.")
    research.write(path, ResearchBrief(id="d", sources=[s], claims=[
        claim("c1", "Built in 1113", "central", Evidence(source_id="s1", excerpt="Built in 1113.")),
        claim("c2", "Hidden for 1000 years", "central")]))
    edited = research.load(path)
    edited.claims[1].importance = "supporting"  # the creator downgrades it instead of finding a source
    saved = research.save_edit(path, edited)
    assert saved.claims[1].locked and not saved.claims[0].locked and saved.revision == 1
    approved = research.approve(path)
    assert approved.research_status == "approved" and approved.approved_revision == 1
    again = research.save_edit(path, research.load(path))  # any later save needs approving again
    assert again.research_status == "needs_review" and again.revision == 2 and again.approved_revision == 1


def test_run_without_gemini_keeps_brief_editable(tmp_path, monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    out = research.run(tmp_path / "r.json", research.new("draft", "d"), [("scene-001", "In 2012 lasers found the city of Angkor.")],
                       log=lambda *_: None, wikipedia=lambda q, *a: ([], "Wikipedia couldn't be searched (ConnectionError)."))
    assert [c.status for c in out.claims] == ["unsupported"]
    assert any("Gemini key" in n for n in out.provider_notes) and any("Wikipedia" in n for n in out.provider_notes)


# ---------- the API ----------

PASTED = """Lost City

Scene 1
Visual: jungle
Voiceover: In 2012 lasers revealed Mahendraparvata under the jungle.
"""


def test_api_draft_research_flow(client, monkeypatch, tmp_path):  # noqa: F811
    from crcontent import web

    ran = []
    monkeypatch.setattr(web.footage_pool, "submit", lambda fn, job_id, *args: ran.append((fn, job_id, args)))
    draft_id = client.post("/api/script-video", json={"text": PASTED, "format": "short",
                                                      "channel_profile_id": "hidden_history_files"}).json()["id"]
    assert client.get(f"/api/research/draft/{draft_id}").json() == {"brief": None, "job": None, "blockers": []}
    job = client.post(f"/api/research/draft/{draft_id}/run").json()["id"]
    assert client.post(f"/api/research/draft/{draft_id}/run").json()["id"] == job  # a second click: the same job
    monkeypatch.setattr(research.src, "wikipedia", lambda q, *a: ([], "Wikipedia had no article."))
    fn, job_id, args = next(r for r in ran if r[1] == job)
    fn(job_id, *args)  # run it here (no Gemini key: sentence split, no mapping)
    assert web.jobs[job_id]["status"] == "done", web.jobs[job_id]
    body = client.get(f"/api/research/draft/{draft_id}").json()
    assert body["brief"]["claims"][0]["status"] == "unsupported" and body["blockers"] == []  # supporting by default
    assert (drafts.DRAFTS_DIR / draft_id / "research.json").exists()

    monkeypatch.setattr(src.requests, "get", lambda *a, **k: SimpleNamespace(
        raise_for_status=lambda: None, text="<html><title>EFEO report</title></html>"))
    r = client.post(f"/api/research/draft/{draft_id}/sources", json={
        "url": "https://efeo.fr/report", "excerpt": "In 2012 airborne laser scanning revealed Mahendraparvata."})
    brief = r.json()
    assert brief["sources"][0]["title"] == "EFEO report"
    brief["claims"][0]["importance"] = "central"
    brief["claims"][0]["evidence"] = [{"source_id": brief["sources"][0]["id"],
                                       "excerpt": brief["sources"][0]["excerpts"][0], "stance": "supports"}]
    saved = client.put(f"/api/research/draft/{draft_id}", json=brief).json()
    assert saved["claims"][0]["status"] == "supported" and saved["claims"][0]["locked"]
    assert client.post(f"/api/research/draft/{draft_id}/approve").json()["research_status"] == "approved"
    assert client.post("/api/research/draft/nope/run").status_code == 404
    assert client.get("/api/research/topic/..%2Fx").status_code == 404


def test_api_topic_brief(client, monkeypatch, tmp_path):  # noqa: F811
    from crcontent import web

    monkeypatch.setattr(web, "ROOT", tmp_path)
    monkeypatch.setattr(web.footage_pool, "submit", lambda *a: None)
    r = client.post("/api/research/topic", json={"topic": "Mary Celeste"})
    assert r.status_code == 200, r.text
    body = client.get(f"/api/research/topic/{r.json()['id']}").json()
    assert body["brief"]["topic"] == "Mary Celeste" and body["brief"]["project_kind"] == "topic"
    assert client.post("/api/research/topic", json={"topic": "x"}).status_code == 400


def test_script_names_for_wikipedia():
    text = ("Under Cambodia's jungle lies a city. It is Mahendraparvata, on the Phnom Kulen plateau, linked to King "
            "Jayavarman the Second. Mahendraparvata was mapped in 2012.")
    assert src.names(text) == ["Mahendraparvata", "Cambodia", "Phnom Kulen"]


def test_topic_claims_are_capped_and_merged_titles_kept():
    fake = FakeClient({"claims": [{"text": f"Fact {i}", "type": "event", "importance": "central"} for i in range(20)]})
    assert len(cl.extract([("", "long answer")], fake, most=15)) == 15
    assert "at most 15" in fake.calls[0]["system"]
    grounded = ResearchSource(id=src.source_id("https://en.wikipedia.org/wiki/X"), url="https://en.wikipedia.org/wiki/X", title="wikipedia.org")
    api = grounded.model_copy(update={"title": "Mary Celeste"})
    assert src.merge([grounded], [api])[0].title == "Mary Celeste"
    assert src.role_of("https://www.rmg.co.uk/stories/x") == "museum_or_archive"
