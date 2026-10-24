"""Shared constants. Dry-run is a process-wide switch: no network, no AI, mock data from tests/fixtures/."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BRAND_DIR = ROOT / "brand"
FIXTURES = ROOT / "tests" / "fixtures" / "songs"

CHANNEL = "Neon Mekong"
INSTAGRAM = "@neonmekong.music"
PLANS = ("Pro", "Premier")  # Suno plans that allow monetization

PLAYLISTS = {
    "nu-disco": "Neon Nostalgia: Disco Love Songs",
    "psych-pop": "Dreamy Psych-Pop",
    "psych-rock": "Trippy Night Rock",
    "late-night": "3AM Night Walk",
}

# Template defaults per genre, filled into song.json when empty (you edit them there)
GENRE_DEFAULTS = {
    "nu-disco": {"mood_phrase": "Nostalgic Disco Love", "scene_theme": "retro disco city lights on a river",
                 "palette": ["#ff2e93", "#00e5ff", "#1a0b3b", "#ffd166"]},
    "psych-pop": {"mood_phrase": "Dreamy Psych Pop", "scene_theme": "hazy pastel river at dusk",
                  "palette": ["#b388ff", "#ff9ecd", "#1b1040", "#7ef9d8"]},
    "psych-rock": {"mood_phrase": "Trippy Night Rock", "scene_theme": "rainy neon city, swirling light",
                   "palette": ["#ff5a1f", "#7a00ff", "#0c0820", "#f7e733"]},
    "late-night": {"mood_phrase": "3AM Night Walk", "scene_theme": "empty river road at night",
                   "palette": ["#4dd0e1", "#ff6f91", "#0a1022", "#c9b6ff"]},
}
SUBSCRIBE_LINE = "Like this song? Subscribe to Neon Mekong"

_dry_run = False


def set_dry_run(on: bool) -> None:
    global _dry_run
    _dry_run = on


def dry_run() -> bool:
    return _dry_run
