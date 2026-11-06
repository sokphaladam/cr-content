"""Generate a short-video script with Gemini as validated, structured JSON."""
import json
import os
from pathlib import Path

from . import llm
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from .config import LLM_MODEL, LANGS
from .styles import CaptionStyle

LAYOUTS = ("fill", "fit", "split")  # footage fills the frame / whole clip over a blurred copy / two clips stacked


class BRoll(BaseModel):
    """A cutaway inside a scene: another clip or photo over the footage for a while (seconds from the scene's start)."""
    media: str
    at: float = 0
    duration: float = 2
    fade: float = 0     # seconds it dissolves in over (0 = a hard cut)
    speed: float = 1    # playback speed of a video clip (0.5 = slow motion, from a Director Plan)
    sound: str = ""     # a sound effect on the cut (sfx.SOUNDS: whoosh, impact, thunder, or rain/wind/water/birds ambience)
    # >0: `at` and `duration` were planned for a scene this many seconds long (a Director Plan's estimate); the render
    # stretches them to the recorded voice's real length. Moving the cutaway by hand sets it back to 0.
    basis: float = 0


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
    # Not given (a new scene): picked from the narration (the AI script marks them; else pacing.auto_keywords), so the
    # captions colour the numbers, names and subject by themselves; [] = the creator cleared them
    keywords: list[str] | None = None
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
    sound: str = ""  # a sound effect as the scene starts (sfx.SOUNDS), from a Director Plan's shot
    speed: float = 1  # playback speed of the scene's video clip (0.5 = slow motion, from a Director Plan)
    # a calm scene (an explanation, a serious moment, a held reveal): no automatic hits or flash, slower re-framing;
    # the words the script marks still hit. "auto" = set by the Edit Director (it may change it again), "on"/"off" =
    # the creator's choice (it never does), "" = not calm
    calm: Literal["", "auto", "on", "off"] = ""
    calm_note: str = ""  # why (the Edit Director's reason)

    @model_validator(mode="after")
    def _keywords(self) -> "Scene":
        from .pacing import _edge, auto_keywords

        if self.keywords is None:
            self.keywords = auto_keywords(self.narration, self.visual_query, self.impacts)
        else:
            self.keywords = list(dict.fromkeys(k for k in (_edge(p).lower() for w in self.keywords for p in w.split()) if k))
        return self


TIMELINE_VERSION = 1
TRACKS = ("voice", "music", "graphics", "sfx")  # the editor's timeline lanes with their own controls


class Clip(BaseModel):
    """A timeline-global item (attention roadmap M4): a motion graphic or a sound effect, placed in seconds from the
    video's start (B-roll and texts stay scene-relative, on their scenes). Edited on the timeline; the render
    (timeline.py) mixes the sounds with the voice and lays the graphics over the picture, at the same times."""
    id: str
    track: Literal["graphics", "sfx"]
    start: float = Field(default=0, ge=0)
    duration: float = Field(default=1, gt=0)
    source_in: float = Field(default=0, ge=0)  # sfx: seconds into the sound it starts from (trimmed head)
    sound: str = ""                            # sfx: an sfx.SOUNDS name, or "user:<id>" (an imported sound)
    template: str = ""                         # graphics: a Remotion composition (graphic_templates.TEMPLATES)
    template_version: int = 0                  # graphics: the template version its props were made for (0 = current)
    props: dict = {}                           # graphics: its props (seconds and font are filled in at render)
    gain: float = Field(default=1, ge=0, le=2)
    fade_in: float = Field(default=0, ge=0)
    fade_out: float = Field(default=0, ge=0)
    layer: int = 0                             # graphics: higher draws on top
    duck: bool = False                         # sfx: the music dips while it plays
    essential: bool = True                     # sfx: False for a nice-to-have (an AI or rule suggestion marked optional)
    note: str = ""                             # why it's there (a suggestion's reason), shown in the inspector
    # who made it: "" the creator, "director" the Edit Director (replaced when it re-plans), "edited" one of its clips
    # the creator changed (kept from then on, like their own)
    origin: Literal["", "director", "edited"] = ""


class TrackState(BaseModel):
    mute: bool = False
    solo: bool = False    # monitoring only: the preview plays just the soloed tracks; the render ignores it
    volume: float = Field(default=1, ge=0, le=2)
    locked: bool = False  # its clips can't be moved, trimmed or deleted
    hidden: bool = False  # graphics: left out of the preview and the render
    duck: float = Field(default=1, ge=0, le=1)  # music: how far it dips under the voice (0 = not at all)


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
    # checked by Gemini on every picture that shows it; and what the image model must not draw instead
    art_subject: str = ""
    art_avoid: str = ""
    # the timeline's global clips and lane controls (M4); older scripts have none
    timeline_version: int = TIMELINE_VERSION
    clips: list[Clip] = []
    tracks: dict[str, TrackState] = {}

    @field_validator("clips")
    @classmethod
    def _unique_clips(cls, clips: list[Clip]) -> list[Clip]:
        ids = [c.id for c in clips]
        if len(set(ids)) != len(ids):
            raise ValueError("timeline clip ids must be unique")
        return clips

    @field_validator("tracks")
    @classmethod
    def _known_tracks(cls, tracks: dict) -> dict:
        if unknown := set(tracks) - set(TRACKS):
            raise ValueError(f"unknown timeline tracks: {', '.join(sorted(unknown))}")
        return tracks

    def track(self, name: str) -> TrackState:
        return self.tracks.get(name) or TrackState()

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
                    "keywords": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["narration", "visual_query", "on_screen_text", "impacts", "keywords"],
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
- keywords: 1-2 single words copied exactly from this scene's narration that the captions show in a highlight colour:
  the word the viewer must catch (the subject's name, a number and its unit, the surprising detail, the payoff word),
  never a filler word like "the", "is" or "this".
- title: 30-60 characters (Khmer: under about 40), specific and front-loaded: a number, a name, a vivid detail or a
  clear promise. Title Case for English, no hashtags, no clickbait the video doesn't deliver.
- caption: the social post caption in the requested language: a first line that hooks on its own with the most
  surprising fact (never a repeat or rewording of the title, which shows right above it), one line that teases the
  payoff, then a question that is easy to answer to drive comments. When the hook simplifies something for effect
  ("the water boils"), name the precise term once in passing, e.g. "(technically called cavitation)". Short lines,
  0-2 emoji.
- hashtags: 4-7 tags without the # sign, mixing broad, topic and niche tags; never fyp, viral, foryou or trending."""

def make_client() -> llm.Client:
    """Gemini client (key: GEMINI_API_KEY, model: LLM_MODEL; see llm.py)."""
    return llm.make_client()


KHMER_NOTE = """
The language is Khmer. Write natural spoken Khmer. Put a normal space between phrases every 2-5 words,
because the captions are timed per space-separated phrase; never leave a phrase longer than about 25 characters."""


def generate_script(topic: str, lang: str = "en", scenes: int = 4, seconds: int = 20,
                    style: str = "", client: llm.Client | None = None) -> VideoScript:
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
            model=LLM_MODEL,
            max_tokens=16000,
            output_config={"effort": "medium", "format": {"type": "json_schema", "schema": SCHEMA}},
            system=system,
            messages=messages,
        )
        if response.stop_reason == "refusal":
            raise RuntimeError(f"Gemini declined this topic: {response.stop_details}")
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


def suggest_queries(narration: str, current: str = "", client: llm.Client | None = None) -> list[str]:
    """Ask Gemini for stock-footage search ideas that fit one scene's narration."""
    client = client or make_client()
    prompt = (
        f"Scene narration (may be in Khmer or English):\n{narration}\n\n"
        f"Current footage search: {current or '(none)'}\n\n"
        "Suggest 5 different ENGLISH search queries (2-4 concrete words each) for vertical stock video "
        "or photos on Pexels that would look good behind this narration. Mix literal and mood/b-roll ideas. "
        "Only things a stock site realistically has; no text, logos, or specific famous people."
    )
    response = client.beta.messages.create(
        model=LLM_MODEL,
        max_tokens=2000,
        output_config={"effort": "low", "format": {"type": "json_schema", "schema": IDEAS_SCHEMA}},
        messages=[{"role": "user", "content": prompt}],
    )
    if response.stop_reason == "refusal":
        raise RuntimeError("Gemini declined to suggest footage for this scene.")
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


def suggest_topics(niche: str, lang: str, recent: list[str], client: llm.Client | None = None) -> list[dict]:
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
        model=LLM_MODEL,
        max_tokens=4000,
        output_config={"effort": "low", "format": {"type": "json_schema", "schema": TOPICS_SCHEMA}},
        messages=[{"role": "user", "content": prompt}],
    )
    if response.stop_reason == "refusal":
        raise RuntimeError("Gemini declined to suggest topics for this niche.")
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


def translate_script(script: VideoScript, target: str, client: llm.Client | None = None) -> VideoScript:
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
        model=LLM_MODEL,
        max_tokens=16000,
        output_config={"effort": "medium", "format": {"type": "json_schema", "schema": TRANSLATE_SCHEMA}},
        system=system,
        messages=[{"role": "user", "content":
                   f"Target language: {profile.name}\n\nScript (JSON):\n{json.dumps(source, ensure_ascii=False, indent=2)}"}],
    )
    if response.stop_reason == "refusal":
        raise RuntimeError("Gemini declined to translate this script.")
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
