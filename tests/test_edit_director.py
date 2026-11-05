"""Attention roadmap M7: the Edit Director's story-aware decisions, restraint, evidence gaps and calm scenes."""
from types import SimpleNamespace

from crcontent import director_plan, edit_director, pacing
from crcontent.director_plan import Footage
from crcontent.script import Clip, Scene, VideoScript

LINES = ["This bird solves a puzzle most children can't.",          # setup, pattern interrupt (the hook)
         "Scientists hid meat 30 centimetres down a narrow tube.",   # tension, evidence (a number)
         "First it finds a wire, then it bends the tip, then it hooks.",  # tension, explanation (a sequence)
         "The crow bent a straight wire into a hook.",               # tension, escalation: must show the action
         "It pulled the meat out on the first try."]                 # payoff, final payoff
BEATS = [("setup", "pattern_interrupt"), ("tension", "evidence"), ("tension", "explanation"),
         ("tension", "escalation"), ("payoff", "final_payoff")]


def plan(weak_action=True):
    p = director_plan.from_scenes("Crow", "short", "en", "educational", [{"narration": n} for n in LINES])
    p.planned_by = "ai"
    p.continuity.subjects = ["new caledonian crow"]
    for sc, (phase, role) in zip(p.scenes, BEATS):
        sc.phase, sc.beat_role = phase, role
    shot = p.shots[3]
    shot.evidence, shot.action = "exact_action", "the crow bending wire into a hook"
    shot.footage = Footage(source="pexels", kind="video", match="subject_only" if weak_action else "exact")
    return p


def script(*clips, **scene_over):
    scenes = [Scene(narration=n, visual_query="crow") for n in LINES]
    for k, v in scene_over.items():
        i, field = k.split("_", 1)
        setattr(scenes[int(i[1:])], field, v)
    return VideoScript(title="Crow", caption="", hashtags=[], scenes=scenes, clips=list(clips))


L = [4.0, 4.0, 4.5, 4.0, 4.0]


def by(out, kind):
    return [d for d in out["decisions"] if d["kind"] == kind]


def test_calm_follows_the_story_and_respects_the_creator():
    out = edit_director.propose(script(), plan(), L)
    calm = {d["scene"]: d for d in by(out, "calm")}
    assert set(calm) == {2, 4}  # the explanation, and the payoff held; never the hook
    assert "explanation" in calm[2]["reason"] and calm[4]["essential"] and "hold the reveal" in calm[4]["reason"]
    # the creator turned scene 3 (index 2) calm off: it stays off
    assert 2 not in {d["scene"] for d in by(edit_director.propose(script(s2_calm="off"), plan(), L), "calm")}


def test_graphics_only_where_they_clarify():
    out = edit_director.propose(script(), plan(), L)
    g = {d["clip"]["template"]: d for d in by(out, "graphic")}
    assert g["LowerThird"]["clip"]["props"]["title"] == "New caledonian crow" and g["LowerThird"]["scene"] == 1
    fact = g.get("Fact")
    assert fact is None or (fact["clip"]["props"]["shown"] == "30" and fact["clip"]["props"]["unit"] == "CENTIMETRES")
    assert len(by(out, "graphic")) <= sum(L) // edit_director.GRAPHIC_EVERY  # restraint
    assert all(d["reason"] and d["clip"]["note"] == d["reason"] for d in out["decisions"] if "clip" in d)
    starts = sorted((d["clip"]["start"], d["clip"]["start"] + d["clip"]["duration"]) for d in by(out, "graphic"))
    assert all(a[1] <= b[0] for a, b in zip(starts, starts[1:]))  # never on top of each other


def test_a_creators_graphic_is_kept_and_not_doubled():
    mine = Clip(id="mine", track="graphics", start=4.0, duration=3, template="LowerThird", props={"title": "Crow"})
    old = Clip(id="old", track="graphics", start=8.0, duration=3, template="Fact", origin="director")
    out = edit_director.propose(script(mine, old), plan(), L)
    templates = [d["clip"]["template"] for d in by(out, "graphic")]
    assert "LowerThird" not in templates  # the subject is already named by the creator
    for d in by(out, "graphic"):  # nothing proposed over the creator's graphic (4-7 s)
        assert d["clip"]["start"] >= 7 or d["clip"]["start"] + d["clip"]["duration"] <= 4
    # the director's own earlier clip doesn't block anything: it's about to be replaced


def test_an_evidence_gap_is_reported_not_covered():
    out = edit_director.propose(script(), plan(weak_action=True), L)
    [gap] = out["gaps"]
    assert gap["scene"] == 3 and "only shows the subject" in gap["text"] and "wouldn't prove it" in gap["text"]
    assert not any(d["scene"] == 3 and d["kind"] == "graphic" for d in out["decisions"])
    assert not any(d["scene"] == 3 and d["kind"] == "sound" and d["clip"]["sound"] not in ("rain", "wind", "water", "birds")
                   for d in out["decisions"])
    # once the footage shows the action, there's no gap
    assert edit_director.propose(script(), plan(weak_action=False), L)["gaps"] == []


def test_sounds_tie_to_beats_and_do_not_repeat(monkeypatch):
    from crcontent import sound_director

    events = [{"start": t, "sound": "impact", "duration": 0.9, "gain": 0.8, "fade_in": 0, "fade_out": 0.1, "duck": True,
               "essential": False, "scene": s, "reason": "hit"} for t, s in ((4.2, 1), (9.0, 2), (17.0, 4))]
    monkeypatch.setattr(sound_director, "suggest", lambda *a, **k: {"source": "rules", "note": "", "events": events})
    out = edit_director.propose(script(), plan(), L)
    starts = [d["clip"]["start"] for d in by(out, "sound")]
    assert starts == [4.2, 17.0]  # the second impact within 8 s is dropped


def test_without_a_plan_it_says_what_it_needs():
    out = edit_director.propose(script(), None, L)
    assert not by(out, "calm") and not by(out, "graphic") and "AI Director" in out["notes"][0]
    assert edit_director.propose(script(), None, [0] * 5)["decisions"] == []


def test_calm_scenes_keep_only_the_marked_hits():
    words = [SimpleNamespace(text=t, start=s) for t, s in (("Boom", 0.5), ("it", 1.0), ("snaps", 1.8))]
    assert pacing.impacts(words, ["snaps"], 4, hook=True) != pacing.impacts(words, ["snaps"], 4, hook=True, auto=False)
    assert pacing.impacts(words, ["snaps"], 4, hook=True, auto=False) == [1.8]  # no punchy-word or hook hits
    held = pacing.cuts(6, [], pacing.CUT_EVERY * 1.8)
    assert len(held) < len(pacing.cuts(6, [], pacing.CUT_EVERY))  # slower re-framing


def test_endpoint(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient

    from crcontent import drafts, web

    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setattr(drafts, "DRAFTS_DIR", tmp_path)
    draft_id, _ = drafts.create(drafts.Draft(script=script(), plan=plan()))
    out = TestClient(web.app).post("/api/edit/direct", json={"script": script().model_dump(), "lengths": L, "draft": draft_id}).json()
    assert out["gaps"] and by(out, "calm") and all(d["id"] for d in out["decisions"])


def test_a_number_in_an_evidence_beat_gets_a_fact_and_a_sequence_gets_steps():
    p = plan()
    p.continuity.subjects = []  # nothing to name: the moments go to the number and the steps
    out = edit_director.propose(script(), p, L)
    g = {d["clip"]["template"]: d for d in by(out, "graphic")}
    assert g["Fact"]["scene"] == 1 and g["Fact"]["clip"]["props"] == {**g["Fact"]["clip"]["props"], "shown": "30", "unit": "CENTIMETRES"}
    assert g["Process"]["scene"] == 2 and g["Process"]["clip"]["props"]["steps"].count(";") >= 2
    # the headline already shows the number: no second copy of it
    assert "Fact" not in {d["clip"]["template"] for d in by(edit_director.propose(script(s1_on_screen_text="30 CM"), p, L), "graphic")}


def test_a_line_edited_since_the_plan_still_matches_its_beat():
    s = script(s4_narration="It pulled the meat out.")  # the payoff line edited after planning
    calm = {d["scene"] for d in by(edit_director.propose(s, plan(), L), "calm")}
    assert 4 in calm  # still the held payoff
    moved = script()
    moved.scenes = moved.scenes[:4]  # a scene removed: positions no longer line up, so no guessing
    assert 3 not in {d["scene"] for d in by(edit_director.propose(moved, plan(), L[:4]), "calm")}


def test_a_sound_the_creator_already_placed_is_not_proposed_again(monkeypatch):
    from crcontent import sound_director

    events = [{"start": 16.5, "sound": "water", "duration": 3, "gain": 0.6, "fade_in": 0.4, "fade_out": 1, "duck": False,
               "essential": False, "scene": 4, "reason": "ambience"}]
    monkeypatch.setattr(sound_director, "suggest", lambda *a, **k: {"source": "rules", "note": "", "events": events})
    mine = Clip(id="w", track="sfx", start=16, duration=3, sound="water")
    assert by(edit_director.propose(script(mine), plan(), L), "sound") == []
    assert len(by(edit_director.propose(script(), plan(), L), "sound")) == 1
