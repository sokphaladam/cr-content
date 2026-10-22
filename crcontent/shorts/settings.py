"""Shorts Mode settings, kept in <data folder>/shorts.json: Script to Video's settings (longform.json's keys) with the
Shorts values over them, plus the channel's rules under "rules".

Written with the defaults the first time it's needed; keys missing from the file fall back to the defaults below.
"""
import copy
import json

from ..config import ROOT
from ..longform.settings import DEFAULTS as LONGFORM, _merge

PATH = ROOT / "shorts.json"

DEFAULTS: dict = _merge(LONGFORM, {
    "voice": {"edge": {"rate": "+5%"}},
    "timing": {"pad_seconds": 0.25},  # a Short keeps moving: a short breath between beats
    "footage": {
        # your own clips first (<media_dir>/<plan>-epNN/scene-XX.*), then each search in Pixabay, then Pexels (when
        # PEXELS_API_KEY is set), then a placeholder card
        "sources": ["pixabay", "pexels"],
        "by_kind": {"species": ["pixabay", "pexels"], "archival": ["pixabay", "pexels"]},
    },
    "render": {
        "width": 1080, "height": 1920, "fps": 30,
        "crossfade": 0.0,     # hard cuts: dissolves read as slow in a Short
        "captions": True,
    },
    "music": {"dir": "assets/music/own", "volume": 0.25},
    "rules": {
        "hook_max": 2.0,                 # the opening beat (animal in motion + hook text) lasts at most this
        "length": {"min": 22.0, "max": 30.0},
        "loop_tail": 0.5,                # the last seconds show the opening shot again, so the loop is seamless
    },
})


def load() -> dict:
    """The settings: the user's file over the defaults (the file is created with the defaults if missing)."""
    if not PATH.exists():
        PATH.write_text(json.dumps(DEFAULTS, indent=2), encoding="utf-8")
        return copy.deepcopy(DEFAULTS)
    try:
        return _merge(DEFAULTS, json.loads(PATH.read_text(encoding="utf-8")))
    except (ValueError, OSError) as e:
        print(f"  ! {PATH.name} couldn't be read ({e}); using the defaults")
        return copy.deepcopy(DEFAULTS)
