"""Generate a short-video script with Claude as validated, structured JSON."""
import json
import os
from pathlib import Path

import anthropic
from pydantic import BaseModel, Field

from .config import CLAUDE_MODEL, LANGS


class Scene(BaseModel):
    narration: str = Field(description="What the voiceover says in this scene")
    visual_query: str = Field(description="2-4 word ENGLISH stock-footage search query")
    on_screen_text: str = Field(default="", description="Optional short headline shown at top")
    # Chosen background (path relative to the project root: uploads/... or cache/pexels/...).
    # Empty = pick footage automatically from visual_query.
    media: str = ""


class VideoScript(BaseModel):
    title: str
    scenes: list[Scene]
    caption: str
    hashtags: list[str]

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
- caption: the social post caption in the requested language, 1-2 sentences, ends with a question to drive comments.
- hashtags: 5-8 tags without the # sign, mixing broad and niche tags."""

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
