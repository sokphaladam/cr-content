"""Generate a short-video script with Claude as validated, structured JSON."""
import json
import os
from pathlib import Path

import anthropic
from pydantic import BaseModel, Field

from .config import CLAUDE_MODEL, LANGS
from .styles import CaptionStyle

LAYOUTS = ("fill", "fit", "split")  # footage fills the frame / whole clip over a blurred copy / two clips stacked


class BRoll(BaseModel):
    """A cutaway inside a scene: another clip or photo over the footage for a while (seconds from the scene's start)."""
    media: str
    at: float = 0
    duration: float = 2


class TextOverlay(BaseModel):
    """Extra text on the frame for a while (seconds from the scene's start); x, y = its middle, as fractions."""
    text: str
    at: float = 0
    duration: float = 2
    x: float = 0.5
    y: float = 0.4
    size: str = "m"
    color: str = "#FFFFFF"
    box: bool = False  # on a black box instead of an outline


class Scene(BaseModel):
    narration: str = Field(description="What the voiceover says in this scene")
    visual_query: str = Field(description="2-4 word ENGLISH stock-footage search query")
    on_screen_text: str = Field(default="", description="Optional short headline shown at top")
    # Chosen background (path relative to the project root: uploads/... or cache/pexels/...).
    # Empty = pick footage automatically from visual_query.
    media: str = ""
    # Length of a scene without narration (e.g. a sound-effect beat); ignored when there is narration.
    seconds: float = 0
    # Transcript edits: words shown in the keyword colour in the captions (voiceover.keyword() form), and stretches
    # (seconds) cut out of the voiceover, which only apply to the voiceover they were made on (cuts_key).
    keywords: list[str] = []
    cuts: list[tuple[float, float]] = []
    cuts_key: str = ""
    # Timeline edits: where the footage starts (seconds into the clip), how it fills the frame, the second clip of a
    # split layout ("" = picked automatically like `media`), cutaways and extra text.
    media_start: float = 0
    layout: str = "fill"
    media2: str = ""
    broll: list[BRoll] = []
    texts: list[TextOverlay] = []
    # AI scene art (when the script has an art_style and no `media` is chosen): the picture's prompt (written by
    # director.py, editable), its seed (another seed = another take of the same prompt), the camera move over it
    # (fx.MOTIONS) and atmosphere effects (fx.EFFECTS). Empty prompt = planned at render time.
    art_prompt: str = ""
    art_seed: int = 0
    motion: str = ""
    effects: list[str] = []


class VideoScript(BaseModel):
    title: str
    scenes: list[Scene]
    caption: str
    hashtags: list[str]
    # from a content plan's Music / Mood and Key Visual columns: the background track is picked by the mood, the key
    # visual is the shot the video is built around (scene `key_scene`, 1-based; 0 = none) and the cover is taken from it
    mood: str = ""
    key_visual: str = ""
    key_scene: int = 0
    captions: CaptionStyle = CaptionStyle()
    # from a content plan's Fact Check sheet: the notes, the works they cite (a "Sources:" line in the description)
    # and a comment to pin under the video
    facts: list[str] = []
    sources: str = ""
    pinned_comment: str = ""
    # scene pictures: "" = stock footage (Pexels/Pixabay), else an imagegen.STYLES look drawn on this computer;
    # art_bible: the director's notes (characters, world, palette) that keep every picture in one style
    art_style: str = ""
    art_bible: str = ""

    @property
    def narration(self) -> str:
        return " ".join(s.narration for s in self.scenes)

    def save(self, path: Path) -> None:
        path.write_text(self.model_dump_json(indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> "VideoScript":
        return cls.model_validate_json(Path(path).read_text(encoding="utf-8"))


SCHEMA = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "scenes": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "narration": {"type": "string"},
                    "visual_query": {"type": "string"},
                    "on_screen_text": {"type": "string"},
                },
                "required": ["narration", "visual_query", "on_screen_text"],
                "additionalProperties": False,
            },
        },
        "caption": {"type": "string"},
        "hashtags": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["title", "scenes", "caption", "hashtags"],
    "additionalProperties": False,
}

SYSTEM = """You write scripts for faceless short-form vertical videos (TikTok, Instagram Reels, YouTube Shorts).

What makes these videos perform:
- Scene 1 is the hook. It must stop the scroll within 2 seconds: a surprising claim, a question, or a bold promise. Never open with "Hey guys", "In this video", or a greeting.
- Every scene delivers one concrete, specific idea. Use numbers, names, and vivid details instead of generalities.
- Short spoken sentences. It is heard, not read.
- Build curiosity so viewers keep watching; save a strong payoff for the end.
- The last scene closes with a short call to action (follow for more, comment your answer, etc.).
- Only state facts you are confident are true.

Field rules:
- narration: the exact words spoken, written in the requested language.
- visual_query: always ENGLISH, 2-4 concrete nouns that a stock video site would have (e.g. "octopus underwater", "city night traffic"). No abstract concepts.
- on_screen_text: a 1-5 word headline for the scene in the requested language, or "" if not needed.
- title: 30-60 characters (Khmer: under about 40), specific and front-loaded: a number, a name, a vivid detail or a
  clear promise. Title Case for English, no hashtags, no clickbait the video doesn't deliver.
- caption: the social post caption in the requested language: a first line that hooks on its own, one line that
  teases the payoff, then a question that is easy to answer to drive comments. Short lines, 0-2 emoji.
- hashtags: 4-7 tags without the # sign, mixing broad, topic and niche tags; never fyp, viral, foryou or trending."""

def make_client() -> anthropic.Anthropic:
    """Claude client; adds the workspace header for org-level keys that aren't scoped to a workspace."""
    workspace = os.getenv("ANTHROPIC_WORKSPACE_ID", "").strip()
    headers = {"anthropic-workspace-id": workspace} if workspace else None
    return anthropic.Anthropic(default_headers=headers)


KHMER_NOTE = """
The language is Khmer. Write natural spoken Khmer. Put a normal space between phrases every 2-5 words,
because the captions are timed per space-separated phrase; never leave a phrase longer than about 25 characters."""


def generate_script(topic: str, lang: str = "en", scenes: int = 6, seconds: int = 45,
                    style: str = "", client: anthropic.Anthropic | None = None) -> VideoScript:
    profile = LANGS[lang]
    client = client or make_client()
    unit = "phrases" if lang == "km" else "words"
    budget = round(seconds * profile.words_per_second)

    prompt = (
        f"Topic: {topic}\n"
        f"Language: {profile.name}\n"
        f"Scenes: exactly {scenes}\n"
        f"Target length: about {seconds} seconds spoken, roughly {budget} {unit} of narration in total.\n"
    )
    if style:
        prompt += f"Style / extra instructions: {style}\n"
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
        raise RuntimeError(f"Claude declined this topic: {response.stop_details}")
    if response.stop_reason == "max_tokens":
        raise RuntimeError("Script generation was cut off (max_tokens); try fewer scenes.")

    text = next(b.text for b in response.content if b.type == "text")
    script = VideoScript.model_validate(json.loads(text))
    script.hashtags = [h.lstrip("#").replace(" ", "") for h in script.hashtags]
    return script


IDEAS_SCHEMA = {
    "type": "object",
    "properties": {"queries": {"type": "array", "items": {"type": "string"}}},
    "required": ["queries"],
    "additionalProperties": False,
}


def suggest_queries(narration: str, current: str = "", client: anthropic.Anthropic | None = None) -> list[str]:
    """Ask Claude for stock-footage search ideas that fit one scene's narration."""
    client = client or make_client()
    prompt = (
        f"Scene narration (may be in Khmer or English):\n{narration}\n\n"
        f"Current footage search: {current or '(none)'}\n\n"
        "Suggest 5 different ENGLISH search queries (2-4 concrete words each) for vertical stock video "
        "or photos on Pexels that would look good behind this narration. Mix literal and mood/b-roll ideas. "
        "Only things a stock site realistically has; no text, logos, or specific famous people."
    )
    response = client.beta.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=2000,
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
        output_config={"effort": "low", "format": {"type": "json_schema", "schema": IDEAS_SCHEMA}},
        messages=[{"role": "user", "content": prompt}],
    )
    if response.stop_reason == "refusal":
        raise RuntimeError("Claude declined to suggest footage for this scene.")
    text = next(b.text for b in response.content if b.type == "text")
    return [q.strip() for q in json.loads(text)["queries"] if q.strip()][:6]


TRANSLATE_SCHEMA = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "scenes": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"narration": {"type": "string"}, "on_screen_text": {"type": "string"}},
                "required": ["narration", "on_screen_text"],
                "additionalProperties": False,
            },
        },
        "caption": {"type": "string"},
        "hashtags": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["title", "scenes", "caption", "hashtags"],
    "additionalProperties": False,
}


def translate_script(script: VideoScript, target: str, client: anthropic.Anthropic | None = None) -> VideoScript:
    """Translate the spoken/visible text into another language, keeping scene order, footage and media."""
    profile = LANGS[target]
    client = client or make_client()
    source = {
        "title": script.title,
        "scenes": [{"narration": s.narration, "on_screen_text": s.on_screen_text} for s in script.scenes],
        "caption": script.caption,
        "hashtags": script.hashtags,
    }
    system = (
        "You adapt short-form video scripts (TikTok, Reels, Shorts) into another language. "
        "Write the way a native creator would say it out loud: natural, punchy spoken language, not a literal "
        "word-for-word translation. Keep every fact, the hook's impact, and the call to action. "
        "Return exactly one output scene per input scene, in the same order; keep each scene about the same "
        "spoken length. Keep an empty on_screen_text empty. Hashtags: no # sign; translate or localize the "
        "topic tags and keep widely used English tags (like brand or platform tags) as they are."
        + (KHMER_NOTE if target == "km" else "")
    )
    response = client.beta.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=16000,
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
        output_config={"effort": "medium", "format": {"type": "json_schema", "schema": TRANSLATE_SCHEMA}},
        system=system,
        messages=[{"role": "user", "content":
                   f"Target language: {profile.name}\n\nScript (JSON):\n{json.dumps(source, ensure_ascii=False, indent=2)}"}],
    )
    if response.stop_reason == "refusal":
        raise RuntimeError("Claude declined to translate this script.")
    if response.stop_reason == "max_tokens":
        raise RuntimeError("The translation was cut off; try a shorter script.")
    data = json.loads(next(b.text for b in response.content if b.type == "text"))
    if len(data["scenes"]) != len(script.scenes):
        raise RuntimeError("The translation came back with a different number of scenes; please try again.")
    return VideoScript(
        title=data["title"],
        scenes=[s.model_copy(update={"narration": t["narration"], "on_screen_text": t["on_screen_text"]})
                for s, t in zip(script.scenes, data["scenes"])],
        caption=data["caption"],
        hashtags=[h.lstrip("#").replace(" ", "") for h in data["hashtags"]],
    )
