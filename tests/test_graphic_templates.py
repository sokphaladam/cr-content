"""Attention roadmap M5: typed, versioned graphics templates, their validation, render use and preview frames."""
import shutil

import pytest

from crcontent import graphic_templates as gt
from crcontent import timeline
from crcontent.script import Clip, Scene, VideoScript
from crcontent.shorts import motion


def script(*clips):
    return VideoScript(title="T", caption="c", hashtags=[], scenes=[Scene(narration="a", visual_query="b")], clips=list(clips))


def test_every_template_validates_with_its_defaults():
    for name, t in gt.TEMPLATES.items():
        props, errors = gt.validate(name, {})
        assert errors == [], name
        assert t["version"] >= 1 and t["label"] and t["description"]
        keys = {f["key"] for f in t["fields"]}
        assert {"enter", "exit"} <= keys  # every graphic can come in and go out
        assert "x" not in keys and "y" not in keys  # placement is at_x / at_y: Fact has its own y (px)


def test_validation_reports_problems_in_plain_words():
    props, errors = gt.validate("KineticTitle", {"text": "", "style": "wavy", "accent": "yellow", "scale": 9,
                                                 "at_x": "left", "junk": 1})
    found = " | ".join(errors)
    for bit in ("Text is empty", "Style: 'wavy'", "isn't a colour", "Scale: 9 is outside", "Across: not a number"):
        assert bit in found, bit
    assert "junk" not in props
    assert gt.validate("KineticTitle", {"text": "x" * 61})[1] == ["Text: 61 characters, at most 60."]
    assert gt.validate("Nope", {})[1] == ["Unknown template 'Nope'."]
    assert "newer version" in gt.validate("Fact", {}, version=99)[1][0]


def test_fact_keeps_its_old_position_and_counts_whole_numbers():
    props, _ = gt.validate("Fact", {"shown": "1,200", "unit": "years", "y": 300})
    assert props["y"] == 960 and props["at_y"] == 0.3  # drawn centred, moved up to 30 % (576 px, where it was)
    assert props["value"] == 1200 and props["unit"] == "YEARS"
    assert gt.validate("Fact", {"shown": "2.5 MILLION"})[0]["value"] is None


def test_render_leaves_invalid_graphics_out_and_says_why():
    ok = Clip(id="a", track="graphics", start=1, duration=2, template="LowerThird", props={"title": "Raven"})
    bad = Clip(id="b", track="graphics", start=1, duration=2, template="LowerThird", props={"title": ""})
    notes = []
    todo = timeline.graphic_clips(script(ok, bad), 10, "", notes.append)
    assert [c["clip"] for c in todo] == ["a"] and todo[0]["props"]["title"] == "Raven"
    assert "graphic b (LowerThird) left out: Title is empty." in notes[0]
    assert timeline.check([bad]) == ["Graphic b (LowerThird): Title is empty."]


def test_a_freeze_frame_spotlight_holds_the_picture_at_its_start():
    spot = Clip(id="s", track="graphics", start=2.5, duration=2, template="Spotlight", props={})
    live = Clip(id="l", track="graphics", start=6, duration=2, template="Spotlight", props={"freeze": "no"})
    asked = []
    todo = timeline.graphic_clips(script(spot, live), 10, "", frame_at=lambda t: asked.append(t) or "data:image/jpeg;x")
    assert asked == [2.5]
    assert todo[0]["props"]["photo"] == "data:image/jpeg;x" and todo[1]["props"]["photo"] == ""


def test_preview_frame_is_settled_before_the_exit():
    assert gt.preview_frame("Process", 3.5) == 96
    assert gt.preview_frame("Fact", 0.2) == 0


def test_stills_endpoint(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient

    from crcontent import web

    monkeypatch.setattr(gt, "STILLS", tmp_path)

    def fake(jobs, font=""):
        made = {}
        for j in jobs:
            key = gt.still_key(j["template"], j["props"], j["seconds"])
            if j["props"].get("title") == "boom":
                made[key] = "renderer crashed"
            else:
                (tmp_path / f"{key}.png").write_bytes(b"png")
                made[key] = ""
        return made

    monkeypatch.setattr(gt, "render_stills", fake)
    client = TestClient(web.app)
    items = [{"template": "LowerThird", "props": {"title": "Raven"}, "seconds": 3},
             {"template": "LowerThird", "props": {"title": ""}, "seconds": 3},
             {"template": "LowerThird", "props": {"title": "boom"}, "seconds": 3}]
    made, invalid, failed = client.post("/api/graphics/stills", json={"items": items}).json()["items"]
    assert client.get(made["url"]).content == b"png"
    assert invalid == {"errors": ["Title is empty."]}
    assert failed == {"failed": "renderer crashed"}
    assert client.get("/api/graphics/stills/..%2Fx.png").status_code == 404
    # a change to any prop is another preview: the old one isn't shown for the new props
    other = client.post("/api/graphics/stills", json={"items": [{**items[0], "props": {"title": "Crow"}}]}).json()["items"][0]
    assert other["key"] != made["key"]


def test_without_remotion_previews_say_so(tmp_path, monkeypatch):
    monkeypatch.setattr(motion, "PROJECT", tmp_path)
    jobs = [{"template": "Fact", "props": gt.validate("Fact", {})[0], "seconds": 2}]
    assert list(gt.render_stills(jobs).values()) == ["Remotion isn't installed (Node and `npm install`)"]


@pytest.mark.skipif(not ((motion.PROJECT / "node_modules").is_dir() and shutil.which("node")), reason="needs Remotion")
def test_a_real_preview_frame(tmp_path, monkeypatch):
    """Remotion draws a template on a transparent frame (slow: starts headless Chrome)."""
    import subprocess

    monkeypatch.setattr(gt, "STILLS", tmp_path)
    props = gt.validate("LowerThird", {"title": "Raven"})[0]
    [why] = gt.render_stills([{"template": "LowerThird", "props": props, "seconds": 2}]).values()
    assert why == ""
    png = tmp_path / f"{gt.still_key('LowerThird', props, 2)}.png"
    alpha = subprocess.run(["ffmpeg", "-v", "error", "-i", str(png), "-vf", "alphaextract,format=gray", "-f", "rawvideo", "-"],
                           capture_output=True, check=True).stdout
    covered = sum(1 for b in alpha if b > 200) / len(alpha)
    assert 0.005 < covered < 0.2  # a lower third, not an empty or a filled frame
