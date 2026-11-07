"""Hidden History Files spec, milestone H6: AI reconstructions (brief from approved research only, stored distinctly,
labelled on the picture, reviewable / rejectable), the gate's reconstruction items, and the evidence graphics."""
import time

import pytest
from PIL import Image

from crcontent import graphic_templates as gt
from crcontent import imagegen, shot_footage
from crcontent.director_plan import Footage
from crcontent.history import gate, reconstruct
from tests.test_director_plan import client  # noqa: F401  (fixture)
from tests.test_history_footage import CFG, lib  # noqa: F401  (fixture)
from tests.test_history_gate import brief, make_history_draft, plan


def rebuilt_plan():
    p = plan()
    p.shots[1].visual_origin, p.shots[1].footage = "reconstruction", None
    p.shots[1].visual_description = "crowded market street below stone temple towers"
    return p


def test_brief_uses_only_approved_research():
    p, b = rebuilt_plan(), brief()
    b.period, b.places = "9th century", ["Phnom Kulen, Cambodia"]
    p.scenes[1].claim_ids = ["c1", "c2"]
    out = reconstruct.brief(p, p.shots[1], b)
    assert out["verified"] == ["Lidar found the city in 2012"]
    assert out["uncertain"] == ["40,000 people lived there (disputed)"]  # listed, never drawn as fact
    assert "40,000" not in out["prompt"]
    assert out["prompt"].startswith("crowded market street below stone temple towers, Phnom Kulen, Cambodia, 9th century")
    assert out["kind"] == "proposed reconstruction" and out["aspect"] == "9:16" and "text" in out["negative"]
    with pytest.raises(ValueError, match="Approve the research"):
        reconstruct.brief(p, p.shots[1], brief("needs_review"))


def test_label_is_burnt_in(tmp_path):
    src = tmp_path / "a.png"
    Image.new("RGB", (1080, 1920), (0, 120, 0)).save(src)
    out = reconstruct.label(src, tmp_path / "b.jpg")
    img = Image.open(out)
    assert img.size == (1080, 1920)
    region = img.crop((150, 200, 600, 300)).getcolors(1 << 20)
    assert len(region) > 10  # text and pill drawn, not a flat green


def test_draw_stores_a_distinct_labelled_asset(tmp_path, monkeypatch):
    raw = tmp_path / "gen.png"
    Image.new("RGB", (64, 112), "gray").save(raw)
    monkeypatch.setattr(imagegen, "installed", lambda: True)
    monkeypatch.setattr(imagegen, "generate", lambda *a, **k: raw)
    monkeypatch.setattr(reconstruct, "OUT", tmp_path / "out")
    p = rebuilt_plan()
    f = reconstruct.draw(reconstruct.brief(p, p.shots[1], brief()), (1080, 1920), 7)
    assert (f.asset_type, f.depicts, f.source, f.rights) == ("reconstruction", "illustrative", "reconstruction", "licensed")
    assert f.raw["label"] == "AI RECONSTRUCTION" and f.raw["brief"]["research_revision"] == 2 and f.raw["seed"] == 7
    monkeypatch.setattr(imagegen, "installed", lambda: False)
    with pytest.raises(RuntimeError, match="your own picture"):
        reconstruct.draw(f.raw["brief"], (1080, 1920))


def test_footage_search_never_fills_a_reconstruction_shot(lib, tmp_path):  # noqa: F811
    from tests.test_history_footage import history_plan, item

    p = history_plan()
    p.shots[1].visual_origin = "reconstruction"
    lib.results["laboratory vellum testing"] = [item(1, "pexels")]
    out = shot_footage.find(p, None, CFG, client=lib.vision)
    assert out.shots[1].footage is None and not out.shots[1].candidates
    assert "draw it from the research" in out.shots[1].warnings[0]
    assert all("laboratory" not in q for q, _ in lib.searched)
    own = tmp_path / "shot-002-1.jpg"  # your own picture: used, and labelled
    Image.new("RGB", (200, 300), "gray").save(own)
    out = shot_footage.find(p, tmp_path, CFG, client=lib.vision)
    f = out.shots[1].footage
    assert f.source == "own" and f.asset_type == "reconstruction" and f.raw["original"] == str(own) and f.file != str(own)


def test_gate_flags_unlabelled_or_found_footage_on_reconstruction_shots():
    p = rebuilt_plan()
    p.shots[1].footage = Footage(source="pexels", kind="video", page="https://p/1", licence="Pexels License",
                                 asset_type="stock", depicts="illustrative", rights="licensed")
    keys = {it["key"].split(":")[0] for it in gate.evaluate(p, brief(), None)["items"]}
    assert "notrebuilt" in keys
    p.shots[1].footage = Footage(source="own", kind="video", file="x.mp4", asset_type="reconstruction", rights="licensed")
    assert "label" in {it["key"].split(":")[0] for it in gate.evaluate(p, brief(), None)["items"]}
    p.shots[1].footage = Footage(source="reconstruction", kind="photo", file="x.jpg", asset_type="reconstruction",
                                 depicts="illustrative", rights="licensed", match="drawn")
    keys = {it["key"].split(":")[0] for it in gate.evaluate(p, brief(), None)["items"]}
    assert not keys & {"notrebuilt", "label", "standin", "rights"}


def test_draw_review_and_reject_through_the_api(client, tmp_path, monkeypatch):  # noqa: F811
    raw = tmp_path / "gen.png"
    Image.new("RGB", (64, 112), "gray").save(raw)
    monkeypatch.setattr(imagegen, "installed", lambda: True)
    monkeypatch.setattr(imagegen, "generate", lambda prompt, *a, **k: raw)
    monkeypatch.setattr(reconstruct, "OUT", tmp_path / "out")
    from crcontent import web

    monkeypatch.setattr(web.footage_pool, "submit", lambda fn, *args: fn(*args))  # the drawing job, run right here
    draft_id, _ = make_history_draft(client, rebuilt_plan(), brief())
    base = f"/api/history/draft/{draft_id}/shots/shot-002-1/reconstruction"
    r = client.get(base)
    assert r.status_code == 200 and r.json()["installed"] and r.json()["brief"]["prompt"]
    for prompt in ("stone towers above a market", "stone towers at dawn"):
        job = client.post(base, json={"prompt": prompt}).json()["id"]
        for _ in range(100):
            if client.get(f"/api/jobs/{job}").json()["status"] in ("done", "error"):
                break
            time.sleep(0.05)
        assert client.get(f"/api/jobs/{job}").json()["status"] == "done"
    shot = client.get(f"/api/plans/draft/{draft_id}").json()["shots"][1]
    assert shot["footage"]["query"] == "stone towers at dawn" and shot["locked"]
    assert shot["candidates"][0]["query"] == "stone towers above a market"  # the earlier drawing, to pick back
    shot = client.delete(base).json()["shots"][1]
    assert shot["footage"] is None and shot["candidates"][0]["asset_type"] == "reconstruction"
    other, _ = make_history_draft(client, rebuilt_plan(), brief("needs_review"))
    assert client.get(f"/api/history/draft/{other}/shots/shot-002-1/reconstruction").status_code == 409


def test_evidence_graphics_validate():
    assert gt.validate("Timeline", {})[1] == [] and gt.validate("DocumentExcerpt", {})[1] == []
    assert "Source (author, title) is empty." in gt.validate("DocumentExcerpt", {"source": ""})[1]
    assert gt.validate("Timeline", {"events": ""})[1] == ["Events (date: what; ...) is empty."]
