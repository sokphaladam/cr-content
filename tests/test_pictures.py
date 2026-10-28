from pathlib import Path

from neonmekong import pictures
from neonmekong.lyricvideo import Variant

DATA = {"title": "Replay", "mood_phrase": "nostalgic disco", "genre": "nu-disco", "scene_theme": "",
        "sections": [{"tag": "Intro", "kind": "intro"},
                     {"tag": "Verse 1", "kind": "verse", "start": 10.0, "end": 20.0},
                     {"tag": "Chorus", "kind": "chorus", "start": 24.0, "end": 40.0}]}


def _song(tmp_path: Path) -> Path:
    (tmp_path / "lyrics.lrc").write_text("[00:11.00]first line\n[00:25.00]chorus line\n", encoding="utf-8")
    return tmp_path


def test_suggest_makes_a_slot_per_sung_section(tmp_path):
    plan = pictures.suggest(_song(tmp_path), DATA)
    assert [s["tag"] for s in plan["slots"]] == ["Verse 1", "Chorus"]
    assert plan["slots"][1]["lyrics"] == "chorus line" and "camera" not in plan["slots"][1]["prompt"]
    assert "brightest" in plan["slots"][1]["prompt"]


def test_suggest_keeps_edited_prompts_and_pictures(tmp_path):
    folder = _song(tmp_path)
    old = pictures.suggest(folder, DATA)
    old["slots"][0].update(prompt="my prompt", edited=True, file="s2-1.png")
    old["slots"][1].update(file="s3-1.png")
    again = pictures.suggest(folder, DATA, keep=old)
    assert again["slots"][0]["prompt"] == "my prompt" and again["slots"][0]["file"] == "s2-1.png"
    assert again["slots"][1]["prompt"] != "my prompt" and again["slots"][1]["file"] == "s3-1.png"


def test_gemini_prompts_replace_the_keyword_ones_but_not_yours(tmp_path, monkeypatch):
    folder = _song(tmp_path)
    monkeypatch.setattr(pictures, "ai_prompts", lambda data, slots, lyrics, log=print: {
        "meaning": "about X", "cover": "a cassette", "sections": {"s2": "a doorway", "s3": "a spinning reel"}})
    old = {"slots": [{"id": "s2", "tag": "Verse 1", "prompt": "mine", "edited": True}]}
    plan = pictures.suggest(folder, DATA, keep=old, ai=True)
    assert plan["cover_prompt"] == "a cassette" and plan["meaning"] == "about X"
    assert [s["prompt"] for s in plan["slots"]] == ["mine", "a spinning reel"]
    monkeypatch.setattr(pictures, "ai_prompts", lambda *a, **k: None)   # no Gemini: the keyword prompts stand
    assert "Cinematic still" in pictures.suggest(folder, DATA, ai=True)["cover_prompt"]


def test_timeline_holds_a_picture_until_the_next_section(tmp_path):
    folder = _song(tmp_path)
    plan = pictures.suggest(folder, DATA)
    (folder / pictures.DIR).mkdir()
    (folder / pictures.DIR / "a.png").write_bytes(b"x")
    plan["slots"][0]["file"] = "a.png"
    pictures.save(folder, plan)
    assert pictures.timeline(folder, 60.0) == [(10.0, 24.0, folder / pictures.DIR / "a.png")]


def test_variant_maps_video_time_to_song_time():
    full = Variant("full", None, [], [], None, 100.0)
    trim = Variant("trim", None, [], [], None, 90.0, cut=12.0)
    prev = Variant("preview", None, [], [], None, 110.0, preview=(8.0, 60.0, 10.0))
    assert (full.song_time(5), trim.song_time(5), prev.song_time(3), prev.song_time(30)) == (5, 17, 63.0, 20.0)


def test_every_picture_prompt_carries_the_house_look():
    from neonmekong import pictures
    out = pictures.prompt_for({"title": "Night Walk", "mood_phrase": "Dreamy"}, "verse", "walking home")
    assert pictures.LOOK in out and "camera" not in out
    assert "ONE clear focal subject" in pictures.SYSTEM


def test_each_section_gets_a_suggested_camera_move_and_yours_stays(tmp_path):
    from neonmekong import pictures
    assert pictures.suggest_motion("chorus") == "pull_out" and pictures.suggest_motion("verse") == "push_in"
    assert pictures.suggest_motion("verse", 1) != pictures.suggest_motion("verse", 0)   # neighbours differ
    folder = tmp_path
    (folder / "lyrics.lrc").write_text("[00:01.00]a\n[00:20.00]b\n", encoding="utf-8")
    data = {"title": "T", "sections": [{"tag": "Verse 1", "kind": "verse", "start": 0, "end": 10},
                                      {"tag": "Chorus", "kind": "chorus", "start": 10, "end": 30}]}
    plan = pictures.suggest(folder, data)
    assert [s["motion"] for s in plan["slots"]] == ["push_in", "pull_out"]
    plan["slots"][0].update(motion="pan_left", motion_edited=True)
    again = pictures.suggest(folder, data, keep=plan)
    assert again["slots"][0]["motion"] == "pan_left" and again["slots"][1]["motion"] == "pull_out"
    assert pictures.with_motions({"slots": [{"start": 0, "kind": "bridge"}]})["slots"][0]["motion"] == "pan_left"
