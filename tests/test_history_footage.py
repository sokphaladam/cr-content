"""Hidden History Files spec, milestone H4: archive-first footage for history Shorts, provenance and rights on every
pick, a visual check that rejects the wrong period or a lookalike, and wildlife searches unchanged."""
import io
import json
from types import SimpleNamespace

import pytest
from PIL import Image

from crcontent import director_plan, shot_footage
from crcontent.longform import archives, footage as lf

CFG = {"footage": {"sources": ["pexels", "commons"], "check_subject": True,
                   "by_kind": {"species": ["pexels", "inaturalist"], "archival": ["archive", "met", "commons"]}}}


def history_plan():
    plan = director_plan.from_scenes("The Voynich Manuscript", "short", "en", "cinematic_history", [
        {"narration": "Why has the Voynich Manuscript never been deciphered?", "visual_query": "manuscript"},
        {"narration": "Its vellum was made between 1404 and 1438.", "visual_query": "lab"}])
    plan.project.channel_profile_id = "hidden_history_files"
    plan.shots[0] = plan.shots[0].model_copy(update={
        "subject": "Voynich Manuscript pages", "visual_origin": "evidence",
        "footage_queries": ["ancient manuscript pages botanical"]})
    plan.shots[1] = plan.shots[1].model_copy(update={
        "subject": "laboratory vellum testing", "visual_origin": "context", "footage_queries": ["laboratory vellum testing"]})
    return plan


def item(i, source, kind="photo", licence="", page=""):
    return {"source": source, "id": i, "kind": kind, "url": f"https://x/{i}", "thumb": "", "page": page or f"https://{source}/{i}",
            "author": "A", "licence": licence, "licence_url": "", "width": 3000, "height": 4000}


class Vision:
    """Fake Gemini: answers by the clip id (picture width - 100): {id: dict of scores}."""

    def __init__(self):
        self.scores, self.calls = {}, []
        outer = self

        class messages:
            @staticmethod
            def create(**kw):
                import base64

                content = kw["messages"][0]["content"]
                outer.calls.append((content[1]["text"], kw["output_config"]["format"]["schema"]))
                cid = Image.open(io.BytesIO(base64.b64decode(content[0]["source"]["data"]))).width - 100
                body = {"subject": 8, "action": 0, "quality": 7, "problem": "", "period": 8, "specific": 8} | outer.scores.get(cid, {})
                return SimpleNamespace(content=[SimpleNamespace(type="text", text=json.dumps(body))])

        self.beta = SimpleNamespace(messages=messages)


@pytest.fixture
def lib(tmp_path, monkeypatch):
    results, searched = {}, []

    def search(q, sources, *a, **k):
        searched.append((q, list(sources)))
        return list(results.get(q, []))

    def fetch(it):
        path = tmp_path / f"clip-{it['id']}.jpg"
        Image.new("RGB", (100 + it["id"], 32), "gray").save(path)
        return path

    monkeypatch.setattr(lf, "search", search)
    monkeypatch.setattr(lf, "fetch", fetch)
    monkeypatch.setenv("GEMINI_API_KEY", "test")
    return SimpleNamespace(results=results, searched=searched, vision=Vision())


def test_history_searches_archives_first_and_names_the_entity(lib):
    shot_footage.find(history_plan(), None, CFG, client=lib.vision)
    first_q, libs = lib.searched[0]
    assert libs == ["archive", "met", "commons", "pexels"]  # archives and museums, then stock
    assert first_q == "Voynich Manuscript ancient pages botanical"  # the entity comes first
    assert [q for q, _ in lib.searched][:3] == ["Voynich Manuscript ancient pages botanical", "Voynich Manuscript",
                                                "ancient manuscript pages botanical"]
    assert "laboratory vellum testing" in [q for q, _ in lib.searched]  # a context shot keeps its own search


def test_wildlife_routing_and_queries_unchanged(lib):
    plan = director_plan.from_scenes("Ravens", "short", "en", "cinematic_wildlife",
                                     [{"narration": "Ravens bend wire.", "visual_query": "raven wire"}])
    shot_footage.find(plan, None, CFG, client=lib.vision)
    assert lib.searched[0] == ("raven wire", ["pexels", "inaturalist"])
    plain = director_plan.from_scenes("Ravens", "short", "en", "cinematic_documentary",
                                      [{"narration": "Ravens bend wire.", "visual_query": "raven wire"}])
    assert shot_footage.sources(plain, CFG) == ["pexels", "commons"]


def test_authentic_archive_beats_sharper_stock_and_keeps_provenance(lib):
    q = "Voynich Manuscript ancient pages botanical"
    lib.results[q] = [item(1, "pexels", licence="Pexels License"),
                      item(2, "commons", licence="Public domain", page="https://commons.wikimedia.org/wiki/File:Voynich_manuscript_page.jpg")]
    lib.vision.scores = {1: {"subject": 8, "quality": 10, "specific": 2}, 2: {"subject": 9, "quality": 6, "specific": 9}}
    plan = shot_footage.find(history_plan(), None, CFG, client=lib.vision)
    f = plan.shots[0].footage
    assert (f.source, f.asset_type, f.depicts, f.rights) == ("commons", "photograph", "actual", "licensed")
    assert f.page.endswith("Voynich_manuscript_page.jpg") and f.licence == "Public domain" and f.author == "A"
    _, schema = lib.vision.calls[0]
    assert "period" in schema["required"] and "specific" in schema["required"]  # the history check
    assert "HISTORY documentary" in lib.vision.calls[0][0]
    alt = plan.shots[0].candidates[0]
    assert (alt.source, alt.asset_type, alt.depicts, alt.rights) == ("pexels", "stock", "illustrative", "licensed")


def test_wrong_period_or_lookalike_is_not_used(lib):
    q = "Voynich Manuscript ancient pages botanical"
    lib.results[q] = [item(1, "commons", licence="CC BY-SA 4.0"), item(2, "commons", licence="CC0")]
    lib.vision.scores = {1: {"subject": 9, "period": 2, "problem": "a modern printed book"},
                         2: {"subject": 8, "period": 8, "specific": 3}}
    plan = shot_footage.find(history_plan(), None, CFG, client=lib.vision)
    f = plan.shots[0].footage
    assert f.raw["id"] == 2 and f.depicts == "illustrative"  # the wrong-period scan lost; a lookalike is not the real one
    assert next(c for c in plan.shots[0].candidates if c.raw["id"] == 1).match == "weak"
    assert any("stands in for Voynich Manuscript pages" in w for w in plan.shots[0].warnings)


def test_stock_fallback_is_never_presented_as_authentic(lib):
    lib.results["ancient manuscript pages botanical"] = [item(5, "pexels", licence="Pexels License")]
    plan = shot_footage.find(history_plan(), None, CFG, client=lib.vision)
    f = plan.shots[0].footage
    assert (f.asset_type, f.depicts) == ("stock", "illustrative")
    assert any(w.startswith("Stock footage stands in for") for w in plan.shots[0].warnings)


def test_rights_unknown_is_flagged(lib):
    q = "Voynich Manuscript ancient pages botanical"
    lib.results[q] = [item(3, "archive", kind="video", licence=archives.UNSTATED, page="https://archive.org/details/x")]
    plan = shot_footage.find(history_plan(), None, CFG, client=lib.vision)
    f = plan.shots[0].footage
    assert f.rights == "rights_unknown" and f.asset_type == "archival"
    assert any("doesn't state a licence" in w and "archive.org/details/x" in w for w in plan.shots[0].warnings)

    from crcontent import quality_preview as qp

    checks = []
    qp.history_footage_checks(checks, plan)
    assert any(c["detector"] == "history.rights.shot-001-1" and c["status"] == "warning" for c in checks)


def test_internet_archive_licence_comes_from_the_item():
    assert archives.archive_licence("https://creativecommons.org/publicdomain/mark/1.0/", "x")[0].startswith("Public domain")
    assert archives.archive_licence("http://creativecommons.org/licenses/by-sa/3.0/", "x")[0] == "CC BY-SA 3.0 (Internet Archive)"
    lic, url = archives.archive_licence("", "film1")
    assert lic == archives.UNSTATED and url == "https://archive.org/details/film1"
    assert shot_footage.provenance(director_plan.Footage(source="archive", kind="video", licence=lic)).rights == "rights_unknown"


def test_old_footage_loads_without_provenance():
    plan = history_plan()
    plan.shots[0].footage = director_plan.Footage(source="pexels", kind="video")
    data = plan.model_dump()
    for k in ("asset_type", "depicts", "rights", "period_score"):
        del data["shots"][0]["footage"][k]
    f = director_plan.load(data).shots[0].footage
    assert (f.asset_type, f.depicts, f.rights, f.period_score) == ("", "", "", None)


def test_a_lookalike_is_not_the_real_thing_unless_its_record_says_so(lib):
    # live run: Gemini scored a facsimile of the Epistles of Clement as "the actual Voynich Manuscript"
    q = "Voynich Manuscript ancient pages botanical"
    lib.results[q] = [dict(item(7, "met", licence="CC0 (Met Open Access)"),
                           title="Photographic Facsimiles of the Remains of the Epistles of Clement of Rome")]
    lib.vision.scores = {7: {"subject": 10, "period": 10, "specific": 9}}
    f = shot_footage.find(history_plan(), None, CFG, client=lib.vision).shots[0].footage
    assert f.raw["id"] == 7 and f.depicts == "illustrative"
