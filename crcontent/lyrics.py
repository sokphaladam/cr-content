"""Write an original song (lyrics + structure + sound) with Claude as validated, structured JSON."""
import json
from pathlib import Path

import anthropic
from pydantic import BaseModel, Field

from .config import CLAUDE_MODEL, LANGS
from .script import make_client

# ElevenLabs music_v1 limits per section
MIN_SECTION_SEC, MAX_SECTION_SEC = 3, 120


class SongSection(BaseModel):
    name: str = Field(description="Section label, e.g. 'Intro', 'Verse 1', 'Chorus'")
    lyrics: list[str] = Field(default_factory=list, description="Sung lines; empty for an instrumental section")
    styles: list[str] = Field(default_factory=list, description="Sound/arrangement directions for this section only")
    seconds: int
    visual_query: str = Field(description="2-4 word ENGLISH stock-footage search query")


class SongScript(BaseModel):
    title: str
    genre: str
    mood: str
    bpm: int
    vocal: str = Field(description="Description of the singing voice, e.g. 'breathy female pop vocal'")
    styles: list[str] = Field(description="Global positive styles for the whole song")
    avoid: list[str] = Field(default_factory=list, description="Global negative styles")
    sections: list[SongSection]
    caption: str
    hashtags: list[str]

    @property
    def lyrics(self) -> str:
        return "\n\n".join(f"[{s.name}]\n" + "\n".join(s.lyrics) for s in self.sections)

    @property
    def seconds(self) -> int:
        return sum(s.seconds for s in self.sections)

    def save(self, path: Path) -> None:
        path.write_text(self.model_dump_json(indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> "SongScript":
        return cls.model_validate_json(Path(path).read_text(encoding="utf-8"))


_SECTION = {
    "type": "object",
    "properties": {
        "name": {"type": "string"},
        "lyrics": {"type": "array", "items": {"type": "string"}},
        "styles": {"type": "array", "items": {"type": "string"}},
        "seconds": {"type": "integer"},
        "visual_query": {"type": "string"},
    },
    "required": ["name", "lyrics", "styles", "seconds", "visual_query"],
    "additionalProperties": False,
}

SCHEMA = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "genre": {"type": "string"},
        "mood": {"type": "string"},
        "bpm": {"type": "integer"},
        "vocal": {"type": "string"},
        "styles": {"type": "array", "items": {"type": "string"}},
        "avoid": {"type": "array", "items": {"type": "string"}},
        "sections": {"type": "array", "items": _SECTION},
        "caption": {"type": "string"},
        "hashtags": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["title", "genre", "mood", "bpm", "vocal", "styles", "avoid", "sections", "caption", "hashtags"],
    "additionalProperties": False,
}

SYSTEM = """You are a hit songwriter writing ORIGINAL songs for short-form vertical videos (TikTok, Reels, Shorts).

What makes these songs perform:
- The hook comes first. The first section (within ~3 seconds) must contain the catchiest line of the song, usually the chorus hook.
- A chorus people can sing back after one listen: short lines, repetition, one clear idea, an easy rhyme.
- Lines of about 6-10 syllables, with a steady rhythm that fits the bpm. Consistent rhyme scheme per section.
- Concrete, vivid images instead of generic words. No cliches like "fire in my soul".
- Fully original lyrics. Never quote or closely paraphrase existing songs.

Sound rules:
- Never name real artists, bands, songs, or albums anywhere (styles, vocal, avoid). If the request references one,
  translate it into neutral musical traits instead: genre, era, tempo, instruments, production, vocal timbre and delivery.
- vocal: one phrase describing the singing voice (gender/range, timbre, delivery), e.g. "warm raspy male baritone, laid-back".
- styles: 5-8 short global sound tags (genre, era, key instruments, production, energy).
- avoid: 0-4 things to keep out of the sound.
- section styles: 1-4 tags for how that part differs (e.g. "stripped back", "full drums", "big harmonies").
- seconds: whole seconds per section, each between 3 and 120; the total must match the requested length.

Other fields:
- lyrics: the sung lines in the requested language; [] for an instrumental section.
- visual_query: always ENGLISH, 2-4 concrete nouns a stock video site would have, matching the section's imagery.
- caption: the social post caption in the requested language, 1-2 sentences, ends with a question to drive comments.
- hashtags: 5-8 tags without the # sign, mixing broad music tags and niche topic tags."""

KHMER_NOTE = """
The language is Khmer. Write natural, singable Khmer lyrics. Put a normal space between phrases every 2-5 words,
because captions are timed per space-separated phrase."""


def generate_song(topic: str, lang: str = "en", seconds: int = 45, style: str = "", vocal: str = "",
                  client: anthropic.Anthropic | None = None) -> SongScript:
    """Ask Claude for an original song about `topic`, sized to about `seconds` long."""
    profile = LANGS[lang]
    client = client or make_client()
    prompt = (
        f"Song topic: {topic}\n"
        f"Language: {profile.name}\n"
        f"Total length: {seconds} seconds (sum of section seconds).\n"
        f"Suggested structure for this length: {_structure_hint(seconds)}\n"
    )
    if style:
        prompt += f"Genre / style direction: {style}\n"
    if vocal:
        prompt += f"Singer voice: {vocal}\n"
    system = SYSTEM + (KHMER_NOTE if lang == "km" else "")

    response = client.beta.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=16000,
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
        output_config={"effort": "medium", "format": {"type": "json_schema", "schema": SCHEMA}},
        system=system,
        messages=[{"role": "user", "content": prompt}],
    )
    if response.stop_reason == "refusal":
        raise RuntimeError(f"Claude declined this song topic: {response.stop_details}")
    if response.stop_reason == "max_tokens":
        raise RuntimeError("Song writing was cut off (max_tokens); try a shorter length.")

    song = SongScript.model_validate(json.loads(next(b.text for b in response.content if b.type == "text")))
    song.hashtags = [h.lstrip("#").replace(" ", "") for h in song.hashtags]
    fit_length(song, seconds)
    return song


def _structure_hint(seconds: int) -> str:
    if seconds <= 35:
        return "Chorus (hook) -> Verse -> Chorus"
    if seconds <= 70:
        return "Chorus (hook) -> Verse -> Pre-chorus -> Chorus"
    return "Intro hook -> Verse 1 -> Chorus -> Verse 2 -> Chorus -> Bridge -> Final chorus"


def fit_length(song: SongScript, seconds: int) -> None:
    """Scale sections so the total matches `seconds`, clamp each to the API limits, then fix rounding on the last."""
    total = sum(max(1, s.seconds) for s in song.sections)
    for s in song.sections:
        s.seconds = max(MIN_SECTION_SEC, min(MAX_SECTION_SEC, round(max(1, s.seconds) * seconds / total)))
    if song.sections:
        last = song.sections[-1]
        last.seconds = max(MIN_SECTION_SEC, min(MAX_SECTION_SEC, last.seconds + seconds - song.seconds))
