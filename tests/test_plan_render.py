"""Milestone 4: a Director Plan's shots go into the existing Short and long-video renderers, keeping user choices."""
from pathlib import Path

import pytest

from crcontent import director_plan, plan_render
from crcontent.director_plan import Camera, Footage

NARR = ["Ravens can bend wire into a hook.", "They live almost everywhere."]


def footage(tmp_path, name, kind="video", source="pexels"):
    f = tmp_path / name
    f.write_bytes(b"x")
    return Footage(source=source, kind=kind, file=str(f), page=f"https://p/{name}", author="A", licence="L")


@pytest.fixture
def plan(tmp_path):
    p = director_plan.from_scenes("Ravens", "short", "en", "cinematic_wildlife",
                                  [{"narration": n, "visual_query": "raven"} for n in NARR])
    base = p.shots[0]
    p.shots = [
        base.model_copy(update={"id": "shot-001-1", "duration_seconds": 1.0, "footage": footage(tmp_path, "a.mp4")}),
        base.model_copy(update={"id": "shot-001-2", "duration_seconds": 1.5, "footage": None}),  # covered by the one before
        base.model_copy(update={"id": "shot-001-3", "duration_seconds": 2.0,
                                "footage": footage(tmp_path, "b.jpg", "photo", "commons"), "warnings": ["soft"]}),
        p.shots[1].model_copy(update={"footage": footage(tmp_path, "c.jpg", "photo"),
                                      "camera": Camera(movement="pan_left")}),
    ]
    return p


def test_short_scenes_cut_main_and_cutaways(plan, monkeypatch, tmp_path):
    monkeypatch.setattr(plan_render, "ROOT", tmp_path)
    scenes = [{"narration": n, "visual_query": "x", "media": ""} for n in NARR]
    out, notes = plan_render.short_scenes(plan, scenes)
    first, second = out
    assert first["media"] == "a.mp4" and first["motion"] == ""  # a project path; a video needs no camera move
    # after shot 1 + shot 2 it replaces; timed on the plan's 4.5 s estimate (the render stretches it to the voice)
    assert first["broll"] == [{"media": "b.jpg", "at": 2.5, "duration": 2.5, "fade": 0, "sound": "", "basis": 4.5}]
    assert second["media"] == "c.jpg" and second["motion"] == "pan_left" and second["broll"] == []
    assert notes[0] == "Put the plan's footage in 2 scenes."
    again, _ = plan_render.short_scenes(plan, out)  # applying twice is the same (the plan's files are its own)
    assert again == out


def test_short_scenes_keep_user_choices_and_rewritten_narration(plan, monkeypatch, tmp_path):
    monkeypatch.setattr(plan_render, "ROOT", tmp_path)
    scenes = [{"narration": NARR[0], "media": "uploads/mine.mp4"}, {"narration": "rewritten", "media": ""},
              {"narration": NARR[1], "media": ""}]  # a scene inserted before the second planned one
    out, notes = plan_render.short_scenes(plan, scenes)
    assert out[0]["media"] == "uploads/mine.mp4" and out[1]["media"] == "" and out[2]["media"] == "c.jpg"
    assert any("kept the footage you chose" in n for n in notes) and any("narration changed" in n for n in notes)


def test_long_entries_use_parts_weights_and_credits(plan):
    entries = [{"scene": 1, "kind": "species", "chosen": {"source": "pixabay", "file": "old.mp4"}},
               {"scene": 2, "kind": "footage", "chosen": {"source": "own", "file": "mine.mp4"}}]
    out, notes = plan_render.long_entries(plan, entries, NARR)
    c = out[0]["chosen"]
    assert c["parts"] == [plan.shots[0].footage.file, plan.shots[2].footage.file] and c["weights"] == [2.5, 2.0]
    assert out[0]["credits"][0]["source"] == "commons" and out[0]["flags"] == ["soft"]
    assert out[1]["chosen"]["file"] == "mine.mp4" and notes == ["Put the plan's footage in 1 scene."]
    picked = [{**entries[0], "chosen": {"source": "pexels", "file": "x", "picked": True}}]
    assert plan_render.long_entries(plan, picked, NARR[:1])[0][0]["chosen"]["file"] == "x"


def test_long_scene_clip_cuts_by_weight(monkeypatch, tmp_path):
    from crcontent.longform import video

    calls = []
    monkeypatch.setattr(video, "render_scene", lambda *a, **k: calls.append(k))
    monkeypatch.setattr(video, "duration", lambda p: 10.0)
    chosen = {"source": "pexels", "file": str(tmp_path / "a.mp4"),
              "parts": [str(tmp_path / n) for n in ("a.mp4", "b.mp4", "c.mp4")], "weights": [1, 1, 2]}
    video.scene_clip(chosen, 8.0, tmp_path / "o.mp4", (1920, 1080))
    (_, at1, d1), (_, at2, d2) = calls[0]["broll"]
    assert (at1, at2) == (2.0, 4.0) and round(d1, 2) == 2.05 and d2 == 4.5
    video.scene_clip({**chosen, "weights": None}, 9.0, tmp_path / "o.mp4", (1920, 1080))  # a montage: even cuts
    assert [b[1] for b in calls[1]["broll"]] == [3.0, 6.0]


def test_credits_list_every_shot():
    from crcontent.longform import extras
    from crcontent.longform.parse import Script

    script = Script(title="T", slug="t", lang="en", scenes=[])
    entries = [{"scene": 1, "chosen": {"source": "pexels", "kind": "video", "file": "a", "author": "A",
                                       "licence": "Pexels License", "page": "p1"},
                "credits": [{"source": "commons", "kind": "photo", "author": "B", "licence": "CC BY 4.0",
                             "licence_url": "", "page": "p2"}]}]
    text = extras.credits(script, entries, [])
    assert "Scene 01 (shot 2): photo by B" in text
    assert any("B, CC BY 4.0" in line for line in extras._attributions(entries))


def test_assemble_endpoint(tmp_path, monkeypatch, plan):
    from fastapi.testclient import TestClient

    from crcontent import drafts, web
    from crcontent.script import VideoScript

    monkeypatch.setattr(drafts, "DRAFTS_DIR", tmp_path / "drafts")
    monkeypatch.setattr(plan_render, "ROOT", tmp_path)
    plan.edit_plan.music_mood = "curious"
    script = VideoScript(title="Ravens", scenes=[{"narration": n, "visual_query": "x"} for n in NARR],
                         caption="", hashtags=[])
    draft_id = drafts.create(drafts.Draft(script=script, plan=plan))[0]
    r = TestClient(web.app).post(f"/api/plans/draft/{draft_id}/assemble",
                                 json={"scenes": [s.model_dump() for s in script.scenes]})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["scenes"][0]["media"] == "a.mp4" and body["mood"] == "curious"
    assert Path(tmp_path / "a.mp4").exists()


def test_cutaway_transitions_and_sounds(plan, monkeypatch, tmp_path):
    monkeypatch.setattr(plan_render, "ROOT", tmp_path)
    plan.shots[1] = plan.shots[1].model_copy(update={"transition_out": "cross_dissolve"})
    plan.shots[2] = plan.shots[2].model_copy(update={"sound_design": ["a heavy thud as it lands"]})
    out, _ = plan_render.short_scenes(plan, [{"narration": n, "media": ""} for n in NARR])
    b = out[0]["broll"][0]
    assert b["fade"] == plan_render.DISSOLVE and b["sound"] == "impact"
    whip = plan.shots[0].model_copy(update={"transition_out": "whip"})
    assert plan_render.cut_sound(whip, plan.shots[3]) == "whoosh"
    assert plan_render.cut_sound(plan.shots[0], plan.shots[3]) == ""  # nothing asked: no sound invented


def test_long_scene_transitions(plan):
    from crcontent.longform import video

    plan.scenes[0].transition_out = "dip_to_black"
    entries = [{"scene": 1, "kind": "species", "chosen": {"source": "pixabay", "file": "x"}}]
    out, _ = plan_render.long_entries(plan, entries, NARR[:1])
    assert out[0]["transition"] == "dip_to_black"
    assert video.transition(out[0], 0.6) == ("fadeblack", 0.6)
    assert video.transition({"transition": "hard_cut"}, 0.6) == ("fade", video.CUT)
    assert video.transition({"transition": "cross_dissolve"}, 0.6) == ("fade", 0.6)
    assert video.transition({"scene": 2}, 0.6) == ("fade", 0.6)  # no plan: the crossfade setting, as before


def test_long_join_uses_each_transition(monkeypatch, tmp_path):
    from crcontent.longform import video

    cmds = []
    monkeypatch.setattr(video, "run", lambda cmd, cwd=None: cmds.append(cmd))
    video._dissolve(["a.mp4", "b.mp4", "c.mp4"], [0, 5, 9], 0.6, tmp_path, "o.mp4",
                    [("fadeblack", 0.6), ("fade", video.CUT)])
    graph = cmds[0][cmds[0].index("-filter_complex") + 1]
    assert "transition=fadeblack:duration=0.600:offset=5.000" in graph
    assert "transition=fade:duration=0.033:offset=9.000" in graph


def test_render_scene_dissolves_a_cutaway_in(monkeypatch, tmp_path):
    from crcontent import render

    cmds = []
    monkeypatch.setattr(render, "run", lambda cmd, cwd=None, timeout=None: cmds.append(cmd))
    clip = tmp_path / "a.mp4"
    render.render_scene(clip, None, 6.0, tmp_path / "o.mp4", broll=[(clip, 2.0, 3.0, 0.4), (clip, 4.0, 1.0)])
    graph = cmds[0][cmds[0].index("-filter_complex") + 1]
    assert "fade=t=in:st=2.000:d=0.400:alpha=1" in graph and graph.count("fade=t=in") == 1


def test_graphic_shots_are_drawn(tmp_path, monkeypatch):
    from crcontent import shot_footage

    monkeypatch.setattr(shot_footage, "CARDS", tmp_path / "cards")
    plan = director_plan.from_scenes("Octopus", "short", "en", "educational",
                                     [{"narration": "Three hearts, blue blood, nine brains.", "on_screen_text": "ALIEN BODY"}])
    plan.shots[0] = plan.shots[0].model_copy(update={"shot_type": "graphic",
                                                     "visual_description": "Hearts: 3; Blood: blue; Brains: 9"})
    out = shot_footage.find(plan, None, {"footage": {"sources": [], "check_subject": False}})
    f = out.shots[0].footage
    assert f.source == "card" and f.match == "drawn" and Path(f.file).is_file() and out.shots[0].warnings == []
    from PIL import Image

    assert Image.open(f.file).size == (1080, 1920)


def test_a_drawn_scene_also_cuts_to_its_planned_footage(plan, tmp_path):
    graphic = plan.shots[0].model_copy(update={"id": "shot-001-0", "shot_type": "graphic", "duration_seconds": 2.0,
                                                "footage": None})
    plan.shots = [graphic, plan.shots[2], plan.shots[3].model_copy(update={"shot_type": "graphic"})]
    (tmp_path / "card-01.png").write_bytes(b"x")
    card = {"source": "card", "kind": "photo", "file": str(tmp_path / "card-01.png")}
    entries = [{"scene": 1, "kind": "graphic", "chosen": card}, {"scene": 2, "kind": "graphic", "chosen": card}]
    out, _ = plan_render.long_entries(plan, entries, NARR)
    c = out[0]["chosen"]
    assert c["source"] == "card" and c["parts"] == [card["file"], plan.shots[1].footage.file]
    assert c["weights"] == [2.0, 2.0] and [x["source"] for x in out[0]["credits"]] == ["commons"]
    assert out[1] == entries[1]  # only graphic shots: the card stays as it was

    from crcontent.longform import extras
    from crcontent.longform.parse import Script
    text = extras.credits(Script(title="T", slug="t", lang="en", scenes=[]), out, [])
    assert "graphic card (made by the app)" in text and "Scene 01: photo by A on Wikimedia Commons" in text
