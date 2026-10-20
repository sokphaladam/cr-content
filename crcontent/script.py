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
    # words of the narration that land with a hit (zoom punch, shake, flash, sound); pacing.py also finds punchy
    # words by itself
    impacts: list[str] = []
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
    # the real subject the pictures must get right ("peacock mantis shrimp: green and orange body, eyes on stalks..."),
    # checked by Claude on every picture that shows it; and what the image model must not draw instead
    art_subject: str = ""
    art_avoid: str = ""

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
                    "impacts": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["narration", "visual_query", "on_screen_text", "impacts"],
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
- In the feed nobody sees the title: they see the first frame for less than a second. So scene 1 opens with the
  PAYOFF, not the setup. State the claim itself in the first sentence, while the picture shows it, so within one
  second the viewer knows what the video claims and wants the reason. Good: "If your cat sleeps like THIS, it trusts
  you completely." Bad: "Here's why your cat sleeps like this..." Never open with "Hey guys", "In this video", "Did
  you know", a greeting or background.
- Then explain: every later scene delivers one concrete, specific reason or detail. Numbers, names, vivid details.
- Short spoken sentences. It is heard, not read. No filler: every line earns its second.
- Make it loop. The last scene ends with a line that leads straight back into the opening, so the end runs into the
  start without a seam: e.g. the last line asks the question that the first line answers, or is a half sentence the
  first line completes ("...and that's exactly why" -> "If your cat sleeps like THIS..."). No sign-off, no "follow
  for more", no "thanks for watching" at the end; it would break the loop (the call to action goes in the caption).
- Only state facts you are confident are true.

Field rules:
- narration: the exact words spoken, written in the requested language.
- visual_query: always ENGLISH, 2-4 concrete nouns that a stock video site would have (e.g. "octopus underwater", "city night traffic"). No abstract concepts.
  Scene 1's query must find a BRIGHT, CLOSE-UP, MOVING shot of the subject doing the thing the claim is about,
  ideally something funny or strange (e.g. "cat sleeping belly up", "cat close up funny"), never a dark, wide or
  empty shot.
- on_screen_text: scene 1 always gets one: the hook as a short, bold line of 2-6 words in the requested language that
  states the claim (e.g. "IT TRUSTS YOU" or "This means LOVE"); no emoji (the video's fonts can't draw them; they
  belong in the caption). Later scenes: "" unless a number or a
  name really helps; less text on screen reads better.
- impacts: 0-2 single words copied exactly from this scene's narration that should land with a HIT on screen (a zoom
  punch, a flash and a sound): the action or the payoff word ("punches", "boils", "smashes", "faster"). Scene 1
  always gets one, early in its first sentence: the hook's promised action must be SHOWN hitting in the first two
  seconds, not just described.
- title: 30-60 characters (Khmer: under about 40), specific and front-loaded: a number, a name, a vivid detail or a
  clear promise. Title Case for English, no hashtags, no clickbait the video doesn't deliver.
- caption: the social post caption in the requested language: a first line that hooks on its own with the most
  surprising fact (never a repeat or rewording of the title, which shows right above it), one line that teases the
  payoff, then a question that is easy to answer to drive comments. When the hook simplifies something for effect
  ("the water boils"), name the precise term once in passing, e.g. "(technically called cavitation)". Short lines,
  0-2 emoji.
- hashtags: 4-7 tags without the # sign, mixing broad, topic and niche tags; never fyp, viral, foryou or trending."""

def make_client() -> anthropic.Anthropic:
    """Claude client; adds the workspace header for org-level keys that aren't scoped to a workspace."""
    workspace = os.getenv("ANTHROPIC_WORKSPACE_ID", "").strip()
    headers = {"anthropic-workspace-id": workspace} if workspace else None
    return anthropic.Anthropic(default_headers=headers)


KHMER_NOTE = """
The language is Khmer. Write natural spoken Khmer. Put a normal space between phrases every 2-5 words,
because the captions are timed per space-separated phrase; never leave a phrase longer than about 25 characters."""


def generate_script(topic: str, lang: str = "en", scenes: int = 4, seconds: int = 20,
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
    from .packaging import fluff_opening

    messages = [{"role": "user", "content": prompt}]
    for attempt in range(2):
        response = client.beta.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=16000,
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
            output_config={"effort": "medium", "format": {"type": "json_schema", "schema": SCHEMA}},
            system=system,
            messages=messages,
        )
        if response.stop_reason == "refusal":
            raise RuntimeError(f"Claude declined this topic: {response.stop_details}")
        if response.stop_reason == "max_tokens":
            raise RuntimeError("Script generation was cut off (max_tokens); try fewer scenes.")

        text = next(b.text for b in response.content if b.type == "text")
        script = VideoScript.model_validate(json.loads(text))
        # an opening that makes the viewer wait loses them in the first second: write it again, once
        fluff = fluff_opening(script.scenes[0].narration) if script.scenes else []
        if not fluff or attempt:
            break
        messages += [{"role": "assistant", "content": text},
                     {"role": "user", "content": f"Scene 1 opens with {' and '.join(fluff)}. Rewrite the whole "
                      "script so the first sentence states the payoff itself, with no intro."}]
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


TOPICS_SCHEMA = {
    "type": "object",
    "properties": {"topics": {"type": "array", "items": {
        "type": "object",
        "properties": {"format": {"type": "string"}, "topic": {"type": "string"}, "hook": {"type": "string"}},
        "required": ["format", "topic", "hook"],
        "additionalProperties": False,
    }}},
    "required": ["topics"],
    "additionalProperties": False,
}

# hook styles worth testing against each other: one channel finds which one breaks out by mixing them
TOPIC_FORMATS = ["payoff-first claim (\"If your X does THIS, it means...\")", "rank these", "which one is...",
                 "surprising ability", "myth vs fact", "this vs that", "POV / what it's really like",
                 "quiz: guess before the end"]


def suggest_topics(niche: str, lang: str, recent: list[str], client: anthropic.Anthropic | None = None) -> list[dict]:
    """Ideas for the next Shorts in a niche, in a mix of formats, none a near-repeat of the channel's recent titles.
    Each: {format, topic (what to give the script writer), hook (the opening line, payoff first)}."""
    client = client or make_client()
    listing = "\n".join(f"- {t}" for t in recent[:60]) or "(none yet)"
    prompt = (
        f"Niche / channel subject: {niche or 'the same subject as the recent videos below'}\n"
        f"Language of the videos: {LANGS[lang].name}\n\n"
        f"Recent video titles on this channel:\n{listing}\n\n"
        "Suggest 8 ideas for the next 15-25 second YouTube Shorts. Rules:\n"
        "- Vary the format: use at least 5 different formats from: " + "; ".join(TOPIC_FORMATS) + ".\n"
        "- Never a near-repeat of a recent title: a different angle, not the same question reworded (\"why your cat"
        " ignores you\" and \"why your cat ignores your dessert\" count as the same).\n"
        "- Each must work as a short: one clear claim or question, visual (stock footage of it exists), and true.\n"
        "- format: the format's short name in English. topic: one line for the script writer, in English, saying"
        " the angle and the format. hook: the video's first spoken line, in the video's language, payoff first"
        " (states the claim immediately, under 12 words)."
    )
    response = client.beta.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=4000,
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
        output_config={"effort": "low", "format": {"type": "json_schema", "schema": TOPICS_SCHEMA}},
        messages=[{"role": "user", "content": prompt}],
    )
    if response.stop_reason == "refusal":
        raise RuntimeError("Claude declined to suggest topics for this niche.")
    text = next(b.text for b in response.content if b.type == "text")
    return [t for t in json.loads(text)["topics"] if t["topic"].strip()][:8]


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
