"""Central settings: video format, voices, caption styling per language."""
import os
from dataclasses import dataclass
from pathlib import Path

CODE_DIR = Path(__file__).resolve().parent.parent
# Everything the app writes (drafts, output, uploads, cache, assets, .env) lives under ROOT. Scripts store media
# paths relative to it. The desktop app points it at the user's app-data folder; otherwise it's the project folder.
ROOT = Path(os.getenv("CRCONTENT_DATA_DIR") or CODE_DIR).resolve()
OUTPUT_DIR = ROOT / "output"
DRAFTS_DIR = ROOT / "drafts"
CACHE_DIR = ROOT / "cache"
ASSETS_DIR = ROOT / "assets"
WINDOWS_FONTS = Path("C:/Windows/Fonts")

WIDTH, HEIGHT, FPS = 1080, 1920, 30
# Frame sizes by aspect ratio: shorts are vertical; full-length music videos can also be landscape (YouTube).
ASPECTS: dict[str, tuple[int, int]] = {"9:16": (WIDTH, HEIGHT), "16:9": (1920, 1080)}


def frame_size(aspect: str | None) -> tuple[int, int]:
    return ASPECTS.get(aspect or "", ASPECTS["9:16"])


def orientation(size: tuple[int, int]) -> str:
    """'portrait' or 'landscape': which way stock footage should face to crop well into `size`."""
    return "landscape" if size[0] > size[1] else "portrait"
SCENE_PAD_SEC = 0.25  # breath of silence after each scene's narration
CLAUDE_MODEL = "claude-opus-5-5"


@dataclass(frozen=True)
class LangProfile:
    code: str
    name: str
    voices: tuple[str, ...]          # first one is the default
    font_file: str                   # file in assets/fonts or C:/Windows/Fonts
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
        font_file="KhmerOSbattambang.ttf",
        font_name="Khmer OS Battambang",
        font_size=100,
        words_per_caption=1,
        words_per_second=0.9,  # phrases per second
    ),
}
