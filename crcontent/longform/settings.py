"""Script to Video settings: voice engine, footage sources, render options, kept in <data folder>/longform.json.

The file is written with the defaults the first time it's needed; edit it to switch the voice engine, footage sources
or render options. Keys missing from it fall back to the defaults below, so older files keep working when new
settings are added. Relative folders are inside the data folder.
"""
import copy
import json
from pathlib import Path

from ..config import ROOT

PATH = ROOT / "longform.json"

DEFAULTS: dict = {
    "voice": {
        # edge (free Microsoft voices), elevenlabs (ELEVENLABS_API_KEY), or files: your own recordings,
        # media/<script>/scene-XX.wav (or .mp3 / .m4a / .flac), matched by scene number
        "engine": "edge",
        "edge": {"en": "en-US-AndrewNeural", "km": "km-KH-PisethNeural", "rate": "+0%"},
        "elevenlabs": {"voice_id": "JBFqnCBsd6RMkjVDRZzb", "model": "eleven_multilingual_v2"},
    },
    "timing": {"pad_seconds": 0.4},  # silence after each scene's voiceover
    "footage": {
        "media_dir": "media",        # your own clips and photos: <media_dir>/<script>/scene-XX.*
        # stock libraries searched in this order (keys from PEXELS_API_KEY / PIXABAY_API_KEY); commons = freely
        # licensed Wikimedia photos, which get rare species right where stock sites show "a black bird"
        "sources": ["pexels", "pixabay", "commons"],
        # the libraries for the other kinds of scene (footage.py): one species (iNaturalist: research-grade wildlife
        # photos), and history, people, artworks, events and space (Internet Archive film and newsreels, NASA,
        # Wikimedia Commons, The Met), all public domain or freely licensed; graphics are drawn by the app
        "by_kind": {
            "species": ["pexels", "pixabay", "inaturalist", "commons"],
            "archival": ["archive", "nasa", "commons", "met"],
        },
        "alternatives": 4,           # matches kept per scene for the storyboard to swap between
        "check_subject": True,       # Gemini looks at each pick and flags footage that doesn't show the named animal
    },
    "render": {
        "width": 1920, "height": 1080, "fps": 30,
        "crossfade": 0.4,            # seconds of dissolve between scenes
        # one colour grade over every scene, so clips from different libraries look like one film: natural,
        # cinematic, film, moody, vibrant, mono (styles.LOOKS)
        "look": "natural",
        "encoder": "auto",           # auto (NVENC when the GPU has it) | nvenc | cpu
        "captions": False,           # burn the voiceover in as captions (captions.srt is always written)
        "title_card_seconds": 2.5,   # how long a "#N BIRD NAME" card stays up
        "lower_third_seconds": 4.0,  # how long other on-screen text stays up
    },
    "music": {
        "dir": "assets/music/own",   # tracks you own the rights to (mp3 / wav / m4a / flac); empty folder = no music
        "volume": 0.25,              # around the default level under the voice (it's ducked while the voice speaks)
    },
}


def _merge(base: dict, over: dict) -> dict:
    out = copy.deepcopy(base)
    for k, v in over.items():
        out[k] = _merge(out[k], v) if isinstance(v, dict) and isinstance(out.get(k), dict) else v
    return out


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


def folder(value: str) -> Path:
    """A folder setting: absolute, or relative to the data folder."""
    path = Path(value).expanduser()
    return path if path.is_absolute() else ROOT / path
