"""Central settings: video format, voices, caption styling per language."""
import os
import sys
from dataclasses import dataclass
from pathlib import Path

from . import locations

CODE_DIR = Path(__file__).resolve().parent.parent
# Everything the app writes (drafts, uploads, cache, assets, .env...) lives under ROOT, the data folder chosen in
# Settings (Documents/Shorts Studio by default). Scripts store media paths relative to it. Finished videos go to
# OUTPUT_DIR, which is ROOT/output unless another folder was chosen. See locations.py.
locations.first_run(CODE_DIR)
ROOT, OUTPUT_DIR, _ = locations.current()
DRAFTS_DIR = ROOT / "drafts"
CACHE_DIR = ROOT / "cache"
ASSETS_DIR = ROOT / "assets"
# where installed fonts are looked up (after assets/fonts): Windows, or macOS system / user fonts
if sys.platform == "win32":
    SYSTEM_FONT_DIRS = (Path("C:/Windows/Fonts"), Path(os.getenv("LOCALAPPDATA", "")) / "Microsoft" / "Windows" / "Fonts")
elif sys.platform == "darwin":
    SYSTEM_FONT_DIRS = (Path.home() / "Library" / "Fonts", Path("/Library/Fonts"), Path("/System/Library/Fonts"),
                        Path("/System/Library/Fonts/Supplemental"))
else:
    SYSTEM_FONT_DIRS = (Path.home() / ".local" / "share" / "fonts", Path.home() / ".fonts", Path("/usr/share/fonts"))

WIDTH, HEIGHT, FPS = 1080, 1920, 30
# Frame sizes by aspect ratio: shorts are vertical; full-length music videos can also be landscape (YouTube).
ASPECTS: dict[str, tuple[int, int]] = {"9:16": (WIDTH, HEIGHT), "16:9": (1920, 1080)}


def frame_size(aspect: str | None) -> tuple[int, int]:
    return ASPECTS.get(aspect or "", ASPECTS["9:16"])


def orientation(size: tuple[int, int]) -> str:
    """'portrait' or 'landscape': which way stock footage should face to crop well into `size`."""
    return "landscape" if size[0] > size[1] else "portrait"
SCENE_PAD_SEC = 0.25  # breath of silence after each scene's narration
LLM_MODEL = ""  # "" = the LLM_MODEL setting in .env, else the default in crcontent/llm.py


@dataclass(frozen=True)
class LangProfile:
    code: str
    name: str
    voices: tuple[str, ...]          # first one is the default
    font_file: str                   # file in assets/fonts or the system fonts
    font_name: str                   # family name libass should look up
    font_size: int
    words_per_caption: int           # tokens shown together on screen
    words_per_second: float          # speaking speed, used to size the script


LANGS: dict[str, LangProfile] = {
    "en": LangProfile(
        code="en",
        name="English",
        voices=("en-US-AndrewNeural", "en-US-AvaNeural", "en-US-BrianNeural", "en-US-EmmaNeural"),
        font_file="arialbd.ttf",
        font_name="Arial",
        font_size=92,
        words_per_caption=3,
        words_per_second=2.6,
    ),
    # Edge TTS reports Khmer timings per space-separated phrase, so one phrase = one caption.
    "km": LangProfile(
        code="km",
        name="Khmer",
        voices=("km-KH-PisethNeural", "km-KH-SreymomNeural"),
        # Khmer OS comes with Windows; macOS has Khmer Sangam MN instead
        font_file="Khmer Sangam MN.ttf" if sys.platform == "darwin" else "KhmerOSbattambang.ttf",
        font_name="Khmer Sangam MN" if sys.platform == "darwin" else "Khmer OS Battambang",
        font_size=100,
        words_per_caption=1,
        words_per_second=0.9,  # phrases per second
    ),
}
