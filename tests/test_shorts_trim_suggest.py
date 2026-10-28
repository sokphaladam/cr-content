import json
from pathlib import Path

import pytest

from crcontent.shorts import edit, trim_window


def test_a_trim_without_an_end_shows_the_beat_length_at_normal_speed():
    assert trim_window(10, 2, 1, None) == (1.0, 3.0, 1.0)


def test_a_trim_fits_the_stretch_to_the_beat_between_half_and_twice():
    assert trim_window(10, 2, 1, 2.2) == (1.0, 2.2, 0.6)        # 1.2 s in a 2 s beat: slow motion
    assert trim_window(10, 2, 1, 9) == (1.0, 5.0, 2.0)          # too long: held at 2x
    assert trim_window(10, 2, 1, 1.2) == (1.0, 2.0, 0.5)        # too short: held at 0.5x
    assert trim_window(10, 2, 1, 3.01) == (1.0, 3.0, 1.0)       # near real time: no retiming


def test_a_trim_stays_inside_the_clip():
    assert trim_window(3, 2, 2.5, None) == (2.0, 3.0, 0.5)      # a short clip is slowed to fill the beat
    assert trim_window(10, 2, 99, None)[0] <= 9.0


def _job(tmp_path: Path, lengths: list[float], title: str, voice: str, animal: str = "") -> Path:
    from crcontent.longform.parse import Scene, Script
    from crcontent.longform.timing import Slot, Timeline
    from crcontent.shorts import plan

    scenes = [Scene(i + 1, 0, "v", "T", voice) for i in range(len(lengths))]
    slots, t = [], 0.0
    for i, n in enumerate(lengths):
        slots.append(Slot(i + 1, t, n, 0, "a.mp3", n))
        t += n
    ep = plan.ShortPlan(ep=1, title=title, script=Script("T", "t", "en", scenes), animal=animal)
    ep.save(tmp_path / "episode.json")
    (tmp_path / "timeline.json").write_text(json.dumps(Timeline(slots, [], t).to_json()))
    (tmp_path / "voice.json").write_text("[]")
    (tmp_path / "footage.json").write_text("[]")
    return tmp_path


@pytest.fixture(autouse=True)
def _settings(monkeypatch):
    from crcontent.shorts import settings

    monkeypatch.setattr(settings, "load", lambda: json.loads(json.dumps(settings.DEFAULTS)))


def test_suggestion_for_a_fast_sea_short(tmp_path):
    s = edit.suggest(_job(tmp_path, [2.0] * 8, "Octopus facts", "An octopus has three hearts! Wow!", "octopus"))
    assert s["look"] == "teal" and s["caption"] == "pop" and s["transition"] == "flash"
    assert s["graphics"] == ["progress", "burst", "sweep"] and set(s["reasons"]) == {"look", "caption", "transition", "graphics"}


def test_suggestion_for_a_calm_short_is_restrained(tmp_path):
    s = edit.suggest(_job(tmp_path, [5.0] * 5, "Why sloths sleep", "A sloth sleeps slowly in the trees.", "sloth"))
    assert s["caption"] == "minimal" and s["transition"] == "cut" and s["graphics"] == ["progress"]


def test_suggestion_only_names_options_the_panel_has(tmp_path):
    s = edit.suggest(_job(tmp_path, [3.0] * 6, "Owl at night", "The owl hunts in the dark.", "owl"))
    assert s["look"] in edit.options()["look"] and s["caption"] in edit.options()["caption"]
    assert s["transition"] in edit.options()["transition"] and all(g in edit.graphics_names() for g in s["graphics"])
