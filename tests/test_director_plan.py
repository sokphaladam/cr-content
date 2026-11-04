"""Script to Video, milestone 1: the Director Plan schema, its storage, and /api/script-video for both formats."""
import json
import pytest
from pydantic import ValidationError

from crcontent import director_plan, drafts
from crcontent.longform.parse import parse

SCENES = [
    {"narration": "Ravens can bend wire into a hook.", "visual_query": "raven wire", "on_screen_text": "SMART"},
    {"narration": "Then they pull the food out of the tube.", "visual_query": "raven tube food", "on_screen_text": ""},
]
TABLE = """# Clever Birds

| Time | Visual | On-screen Text | Voiceover |
| --- | --- | --- | --- |
| 0:00 | raven on branch | #1 RAVEN | Ravens can bend wire into a hook. |
| 0:05 | crow in city | | Crows drop nuts on roads. |
"""


def test_seeded_plan_keeps_narration_and_stable_ids():
    plan = director_plan.from_scenes("Ravens", "short", "en", "cinematic_wildlife", SCENES)
    assert plan.project.aspect_ratio == "9:16" and plan.planned_by == "script"
    assert [s.id for s in plan.scenes] == ["scene-001", "scene-002"]
    assert [(s.id, s.scene_id) for s in plan.shots] == [("shot-001-1", "scene-001"), ("shot-002-1", "scene-002")]
    assert plan.scenes[0].narration == SCENES[0]["narration"]  # word for word
    assert plan.shots[0].footage_queries == ["raven wire"] and plan.shots[0].duration_seconds > 0
    again = director_plan.load(plan.model_dump())  # round trip through JSON-shaped data
    assert again == plan


def test_validation_and_migration():
    plan = director_plan.from_scenes("t", "long", "en", "educational", SCENES).model_dump()
    assert director_plan.load({**plan, "version": 0}).version == director_plan.VERSION
    with pytest.raises(ValidationError, match="newer version"):
        director_plan.load({**plan, "version": director_plan.VERSION + 1})
    with pytest.raises(ValidationError, match="unknown scenes"):
        director_plan.load({**plan, "shots": [{**plan["shots"][0], "scene_id": "scene-999"}]})
    with pytest.raises(ValidationError, match="unique"):
        director_plan.load({**plan, "scenes": [plan["scenes"][0], plan["scenes"][0]], "shots": []})
    stale = {**plan, "project": {**plan["project"], "aspect_ratio": "9:16"}}
    assert director_plan.load(stale).project.aspect_ratio == "16:9"


def test_khmer_duration_counts_letters():
    assert director_plan.spoken_seconds("សួស្តីពិភពលោក") > 0


def test_longform_markdown_reads_back(tmp_path):
    plan = director_plan.from_scenes("Ravens | Crows", "long", "en", "cinematic_wildlife", SCENES)
    md = tmp_path / "s.md"
    md.write_text(director_plan.longform_markdown(plan), encoding="utf-8")
    script = parse(md)
    assert [s.voiceover for s in script.scenes] == [s["narration"] for s in SCENES]
    assert script.scenes[1].planned > script.scenes[0].planned


def test_editor_save_keeps_the_plan(tmp_path, monkeypatch):
    monkeypatch.setattr(drafts, "DRAFTS_DIR", tmp_path)
    from crcontent.script import VideoScript

    script = VideoScript(title="Ravens", scenes=[{"narration": "x", "visual_query": "y"}], caption="", hashtags=[])
    plan = director_plan.from_scenes("Ravens", "short", "en", "storytelling", SCENES)
    draft_id, _ = drafts.create(drafts.Draft(script=script, plan=plan))
    drafts.save(draft_id, drafts.Draft(script=script, topic="edited"))  # what the editor's autosave sends
    loaded = drafts.load(draft_id)
    assert loaded.topic == "edited" and loaded.plan == plan


@pytest.fixture
def client(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient

    from crcontent import web

    monkeypatch.delenv("GEMINI_API_KEY", raising=False)  # the basic reader: no network
    monkeypatch.setattr(drafts, "DRAFTS_DIR", tmp_path / "drafts")
    monkeypatch.setattr(web, "LONG_SCRIPTS", tmp_path / "scripts")
    started = []
    monkeypatch.setattr(web.footage_pool, "submit", lambda fn, job_id, *args: web.jobs[job_id].update(status="done"))
    monkeypatch.setattr(web.renderer, "submit", lambda fn, *args: started.append((fn.__name__, args)))
    c = TestClient(web.app)
    c.started = started
    return c


PASTED = """Clever Ravens

Scene 1
Visual: raven close-up
Voiceover: Ravens can bend wire into a hook.

Scene 2
Visual: raven pulls food from tube
Voiceover: Then they pull the food out of the tube.
"""


def test_script_video_short_makes_a_draft_with_plan(client):
    r = client.post("/api/script-video", json={"text": PASTED, "format": "short", "visual_style": "cinematic_wildlife"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["format"] == "short" and body["scenes"] >= 1
    d = drafts.load(body["id"])
    assert d.plan.project.format == "short" and d.plan.project.visual_style == "cinematic_wildlife"
    assert [s.narration for s in d.plan.scenes] == [s.narration for s in d.script.scenes]


def test_script_video_long_from_prose_and_from_table(client):
    r = client.post("/api/script-video", json={"text": PASTED, "format": "long"})
    assert r.status_code == 200, r.text
    name, (job_id, dest, plan, choice) = client.started[-1]
    assert name == "_run_storyboard" and r.json()["id"] == job_id
    assert plan.project.aspect_ratio == "16:9" and parse(dest).scenes  # the existing long pipeline can read it
    assert choice is None  # nothing chosen: the Script Video settings as they are

    r = client.post("/api/script-video", json={"text": TABLE, "format": "long"})
    assert r.status_code == 200, r.text
    _, (_, dest2, plan2, _) = client.started[-1]
    assert dest2.read_text(encoding="utf-8") == TABLE  # a table is used as written (title cards, chapters)
    assert plan2.project.title == "Clever Birds" and len(plan2.scenes) == 2


def test_script_video_rejects_bad_input(client):
    assert client.post("/api/script-video", json={"text": PASTED, "format": "tiktok"}).status_code == 400
    assert client.post("/api/script-video", json={"text": PASTED, "format": "short", "visual_style": "8k"}).status_code == 400


def test_script_video_short_keeps_voice_music_and_target(client, tmp_path, monkeypatch):
    from crcontent import web

    monkeypatch.setattr(web, "_voices", lambda lang: {"en": ["en-US-AndrewNeural", "en-US-AvaNeural"],
                                                       "km": ["km-KH-PisethNeural"]}[lang])
    monkeypatch.setattr(web, "ASSETS_DIR", tmp_path / "assets")
    (tmp_path / "assets" / "music").mkdir(parents=True)
    (tmp_path / "assets" / "music" / "calm.mp3").write_bytes(b"x")
    body = {"text": PASTED, "format": "short", "lang": "en", "voice": "en-US-AvaNeural", "rate": "+15%",
            "music": "calm.mp3", "target_seconds": 30}
    r = client.post("/api/script-video", json=body)
    assert r.status_code == 200, r.text
    d = drafts.load(r.json()["id"])
    assert (d.voice, d.rate, d.music, d.plan.project.target_seconds) == ("en-US-AvaNeural", "+15%", "calm.mp3", 30)
    # a Khmer voice on an English script: the default voice, and a note saying so
    r = client.post("/api/script-video", json={**body, "voice": "km-KH-PisethNeural"})
    assert drafts.load(r.json()["id"]).voice == "" and "default voice" in r.json()["voice_note"]
    for bad in ({"voice": "en-US-Nobody"}, {"rate": "+99%"}, {"music": "gone.mp3"}, {"target_seconds": -5}):
        assert client.post("/api/script-video", json={**body, **bad}).status_code == 400, bad


def test_director_gets_the_target_length():
    from crcontent import ai_director

    plan = director_plan.from_scenes("T", "short", "en", director_plan.STYLES[0], [{"narration": "Ravens bend wire.", "visual_query": "raven"}])
    assert "aims for about" not in ai_director._task(plan, None, "")
    plan.project.target_seconds = 45
    assert "aims for about 45 seconds" in ai_director._task(plan, None, "")


def test_script_video_long_passes_its_voice_and_music(client, tmp_path, monkeypatch):
    from crcontent import web

    monkeypatch.setattr(web, "_voices", lambda lang: {"en": ["en-US-AvaNeural"], "km": ["km-KH-PisethNeural"]}[lang])
    monkeypatch.setattr(web, "ASSETS_DIR", tmp_path / "assets")
    (tmp_path / "assets" / "music").mkdir(parents=True)
    (tmp_path / "assets" / "music" / "calm.mp3").write_bytes(b"x")
    r = client.post("/api/script-video", json={"text": PASTED, "format": "long", "voice": "en-US-AvaNeural",
                                               "rate": "-10%", "music": "calm.mp3"})
    assert r.status_code == 200, r.text
    _, (_, _, _, choice) = client.started[-1]
    assert choice == {"voice": "en-US-AvaNeural", "rate": "-10%", "music": "calm.mp3"}


def test_long_video_choice_over_the_settings(tmp_path, monkeypatch):
    from crcontent.longform import settings, video

    monkeypatch.setattr(settings, "PATH", tmp_path / "longform.json")
    monkeypatch.setattr(settings, "ROOT", tmp_path)
    own = tmp_path / "assets" / "music" / "own"
    own.mkdir(parents=True)
    (own / "a.mp3").write_bytes(b"x")
    (tmp_path / "assets" / "music" / "calm.mp3").write_bytes(b"x")
    monkeypatch.setattr("crcontent.config.ASSETS_DIR", tmp_path / "assets")
    job = tmp_path / "job"
    job.mkdir()
    plain = settings.for_job(job)  # no choice.json: the settings as they are (an older video)
    assert plain == settings.load() and [p.name for p in video.playlist(plain, "t")] == ["a.mp3"]
    settings.save_choice(job, "en-US-AvaNeural", "-10%", "calm.mp3")
    cfg = settings.for_job(job)
    assert cfg["voice"]["edge"]["en"] == "en-US-AvaNeural" and cfg["voice"]["edge"]["rate"] == "-10%"
    assert [p.name for p in video.playlist(cfg, "t")] == ["calm.mp3"]
    settings.save_choice(job, music="none")
    assert video.playlist(settings.for_job(job), "t") == []


def test_make_storyboard_saves_the_choice_and_voices_with_it(tmp_path, monkeypatch):
    from crcontent import longform
    from crcontent.longform import settings, voice

    monkeypatch.setattr(settings, "PATH", tmp_path / "longform.json")
    monkeypatch.setattr("crcontent.config.OUTPUT_DIR", tmp_path / "out")
    seen = {}

    class Stop(Exception):
        pass

    def fake_voices(script, media, out, cfg, log=print):
        seen["edge"] = dict(cfg["voice"]["edge"])
        raise Stop  # far enough: the rest needs the network

    monkeypatch.setattr(voice, "make_voices", fake_voices)
    md = tmp_path / "s.md"
    md.write_text(TABLE, encoding="utf-8")
    logged = []
    with pytest.raises(Stop):
        longform.make_storyboard(md, log=logged.append, choice={"voice": "en-US-AvaNeural", "rate": "-10%", "music": "none"})
    assert seen["edge"]["en"] == "en-US-AvaNeural" and seen["edge"]["rate"] == "-10%"
    [job] = (tmp_path / "out").iterdir()
    assert json.loads((job / settings.CHOICE).read_text())["music"] == "none"
    # a Khmer voice on an English script is dropped, with a note
    with pytest.raises(Stop):
        longform.make_storyboard(md, log=logged.append, job=job, choice={"voice": "km-KH-PisethNeural"})
    assert "en-US-AvaNeural" not in seen["edge"].values() and any("doesn't speak" in m for m in logged)
