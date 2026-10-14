"""Claude as director of photography for AI scene art: one look for the whole video, then a picture prompt, camera
move and atmosphere effects for every scene (shorts) or every picture slot (music videos).

The "visual bible" (who the recurring characters are, the world, the palette) is written once and repeated inside
every prompt that shows them, which is what keeps a generated video looking like one film instead of random
pictures. Prompts are written for the model behind each look (imagegen.STYLES): Danbooru-style tags for the anime
model, film-still sentences for the cinematic one, simple visual metaphors for flat 2D.
"""
import json
from dataclasses import dataclass

import anthropic

from .config import CLAUDE_MODEL
from .fx import EFFECTS, MOTIONS

# effects Claude picks per scene; the base ones (glow, grain, vignette...) come with the art style
MOOD_EFFECTS = ["dust", "snow", "embers", "sparkles", "petals", "speed_lines", "light_leak", "light_trails", "flash"]

SCHEMA = {
    "type": "object",
    "properties": {
        "bible": {"type": "string"},
        "shots": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "prompt": {"type": "string"},
                    "motion": {"type": "string", "enum": list(MOTIONS)},
                    "effects": {"type": "array", "items": {"type": "string", "enum": MOOD_EFFECTS}},
                },
                "required": ["prompt", "motion", "effects"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["bible", "shots"],
    "additionalProperties": False,
}

PROMPT_RULES = {
    "anime": """Write every prompt as comma-separated Danbooru tags for the Animagine XL anime model, in this order:
subject count (1girl / 1boy / 2girls / no humans), the recurring character's fixed appearance tags (hair colour and
length, eyes, outfit - copied word for word from the bible every time they appear), pose/action, expression, setting,
time of day and weather, lighting (e.g. backlighting, golden hour, rim light, neon lights), camera framing
(close-up, upper body, cowboy shot, full body, wide shot, from below, from above, dutch angle).
Men: write "1boy, male focus" and, for a grown man, "mature male"; give him short or medium hair (long or
shoulder-length hair makes the model draw a girl). Avoid facial hair tags (mustache, beard, stubble): the model
paints them onto a soft young face and it looks wrong; only use "beard" when the man is clearly older.
Prefer strong, simple compositions with depth: a clear foreground subject and a detailed background.
At most 28 tags (the model reads only ~75 tokens; anything longer is cut off). No quality tags (they are added for you). Never ask for text, signs, letters or logos.""",
    "cinematic": """Write every prompt as one or two plain English sentences describing a film still for a photoreal
model: the subject, what they are doing, the setting, the lighting and lens/framing (close-up, wide establishing
shot, low angle, over the shoulder). Recurring people are described with the same fixed appearance every time
(copied from the bible). Strong composition with depth (foreground subject, background), cinematic light.
At most 40 words (the model reads only ~75 tokens). No quality words (they are added for you). Never ask for readable text, signs or logos.""",
    "flat": """Write every prompt as a short description of a flat 2D illustration in a motion-graphics style: one
clear visual metaphor for the idea of the scene, simple shapes, a named colour palette from the bible (repeat it in
every prompt), centered composition with empty space around the subject. At most 35 words (the model reads only ~75 tokens). No quality words.
Never ask for text, numbers, charts with labels, letters or logos.""",
}

SYSTEM = """You are the director of photography for short-form videos made from AI-generated pictures.
Each picture becomes a moving shot (the camera move you choose is animated over it) and they are cut together, so the
video must look like ONE film: the same characters, world, palette and light logic from the first shot to the last.

First write the visual bible: recurring character(s) with fixed appearance details, the world/setting, era,
palette and lighting style. Keep it under 70 words. Then one shot per requested slot, in order.

Camera moves:
- push_in: emotion, focus, a reveal; pull_out: ending, loneliness, scale
- pan_left / pan_right: wide landscapes, cityscapes, travel; tilt_up / tilt_down: tall subjects, sky, buildings
- orbit_3d / dolly_3d / rise_3d: the "3D" moves (the picture is split into depth layers); use them on shots with a
  clear foreground subject in front of a distant background - they look the most expensive, use them often
- still: rare, only for a held beat
Never use the same move twice in a row. The first shot must hook: a striking composition and a 3D move.

Atmosphere effects (0-2 per shot, only when they fit what is in the picture): dust (floating motes, calm, warm light),
snow, embers (fire, war, intensity), sparkles (magic, dreams), petals (romance, spring), speed_lines (action, impact,
shock - anime only), light_leak (nostalgia, memories, sunsets), light_trails (car light streaks: roads, traffic, night
drives, speed), flash (a hard accent - use for hooks and big moments).
Colour grade, film grain, bloom and vignette are added automatically; do not ask for them."""


@dataclass
class ShotPlan:
    prompt: str
    motion: str
    effects: list[str]


def _client(client: anthropic.Anthropic | None) -> anthropic.Anthropic:
    from .script import make_client

    return client or make_client()


def _ask(task: str, count: int, style: str, client: anthropic.Anthropic | None) -> tuple[str, list[ShotPlan]]:
    response = _client(client).beta.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=16000,
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
        output_config={"effort": "medium", "format": {"type": "json_schema", "schema": SCHEMA}},
        system=SYSTEM + "\n\nPrompt format:\n" + PROMPT_RULES[style],
        messages=[{"role": "user", "content": task + f"\n\nReturn exactly {count} shots, in order."}],
    )
    if response.stop_reason == "refusal":
        raise RuntimeError("Claude declined to plan the pictures for this video.")
    data = json.loads(next(b.text for b in response.content if b.type == "text"))
    shots = [ShotPlan(s["prompt"].strip(), s["motion"] if s["motion"] in MOTIONS else "push_in",
                      [e for e in s["effects"] if e in EFFECTS][:2]) for s in data["shots"]]
    if not shots:
        raise RuntimeError("Claude returned no shots.")
    while len(shots) < count:  # rare: pad by reusing from the start with a different move
        src = shots[len(shots) % max(len(shots), 1)]
        shots.append(ShotPlan(src.prompt, "pull_out" if src.motion != "pull_out" else "push_in", src.effects))
    return data["bible"].strip(), shots[:count]


def plan_scenes(title: str, scenes: list[dict], style: str, idea: str = "", bible: str = "",
                client: anthropic.Anthropic | None = None) -> tuple[str, list[ShotPlan]]:
    """One shot per scene of a short. scenes: [{"narration", "visual_query"}]. `bible`: an existing visual bible
    (perhaps edited by hand) to keep instead of writing a new one."""
    listing = "\n".join(f"{i + 1}. narration: {s['narration']!r}" + (f" | idea: {s['visual_query']}" if s.get("visual_query") else "")
                        for i, s in enumerate(scenes))
    task = (f"A vertical 9:16 short video titled {title!r}." + (f"\nThe creator's direction: {idea}" if idea else "")
            + (f"\n\nUse this visual bible exactly as written (return it unchanged as `bible`):\n{bible}" if bible else "")
            + f"\n\nScenes (the narration may be in Khmer; the pictures must illustrate what is being said):\n{listing}")
    return _ask(task, len(scenes), style, client)


def plan_song(title: str, mood: str, genre: str, slots: list[dict], style: str, aspect: str, idea: str = "",
              bible: str = "", client: anthropic.Anthropic | None = None) -> tuple[str, list[ShotPlan]]:
    """Pictures for a music video. slots: [{"section", "lyrics", "seconds", "scene"?}] in song order; several slots can
    belong to the same section (they should progress, not repeat). "scene": the creator's direction for that section
    (from direct_idea), which the pictures must show. `bible`: an existing visual bible to keep."""
    directed = any(s.get("scene") for s in slots)
    listing = "\n".join(f"{i + 1}. [{s['section']}, {s['seconds']:.0f}s] lyrics: {s['lyrics'] or '(instrumental)'}"
                        + (f"\n   DIRECTION: {s['scene']}" if s.get("scene") else "")
                        for i, s in enumerate(slots))
    task = (f"A {aspect} music video for the song {title!r} ({mood} {genre})."
            + (f"\nThe creator's idea for the video: {idea}" if idea else
               "\nTell a simple visual story that follows the lyrics (a character, a place, a change).")
            + ("\nThe creator directed every section (DIRECTION below). Follow it exactly: each picture shows that "
               "section's direction, not your own idea and not a literal reading of the lyrics. When a section has "
               "several pictures, walk through its direction in order (e.g. 'keys dropped into her hand, then the "
               "engine starting' = first picture the keys, the next the ignition and dashboard lights). Keep the "
               "point of view the direction asks for (e.g. from the passenger seat)." if directed else
               "\nChoruses should feel bigger: wider shots, stronger light, flash/sparkles; verses more intimate.")
            + (f"\n\nUse this visual bible exactly as written (return it unchanged as `bible`):\n{bible}" if bible else "")
            + f"\n\nPicture slots (lyrics may be in Khmer; illustrate their meaning):\n{listing}")
    return _ask(task, len(slots), style, client)


# ---------- turning a creator's concept into a shot list ----------

PACES = ("slow", "normal", "fast")

DIRECTION_SCHEMA = {
    "type": "object",
    "properties": {
        "bible": {"type": "string"},
        "sections": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"scene": {"type": "string"}, "pace": {"type": "string", "enum": list(PACES)}},
                "required": ["scene", "pace"],
                "additionalProperties": False,
            },
        },
        "look": {"type": "string"},
        "lyric_preset": {"type": "string"},
        "lyric_font": {"type": "string"},
        "notes": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["bible", "sections", "look", "lyric_preset", "lyric_font", "notes"],
    "additionalProperties": False,
}


def direct_idea(title: str, mood: str, genre: str, sections: list[dict], idea: str, looks: dict[str, str],
                presets: dict[str, str], fonts: list[str], client: anthropic.Anthropic | None = None) -> dict:
    """A creator's music video concept as a shot list for this song: what each section shows and how fast it cuts,
    the recurring characters and world, a colour grade, a lyric style, and notes on what can't be done literally.
    sections: [{"name", "lyrics"}] in song order. looks / presets: key -> label of what the app can do."""
    listing = "\n".join(f"{i + 1}. {s['name']}: {' / '.join(s['lyrics'][:6]) or '(instrumental)'}"
                        for i, s in enumerate(sections))
    task = f"""You are a music video director turning a creator's concept into a shot list for this song.

Song: {title!r} ({mood} {genre})
Sections, in order:
{listing}

The creator's concept:
{idea}

How the video is made: AI-drawn still pictures, each moved by a camera move (push in, pan, 3D parallax), cut on the
beat, with effects (light trails, light leaks, particles, flashes), a colour grade over everything and the lyrics as
captions. There is no real filming and nothing moves inside a picture.

Return:
- sections: exactly {len(sections)}, one per song section in the order above. `scene`: what the viewer sees during
  that section, 1-3 concrete visual sentences taken from the concept (the concept may name sections loosely: "Verses"
  covers every verse, "Final chorus" the last chorus). A section the concept doesn't mention gets a scene that fits
  the story between its neighbours. Repeated sections (a second chorus) may share a scene or progress it. `pace`:
  how fast it cuts: fast for energy or "faster cuts", slow for "everything slows down", stillness, intros/outros
  that linger; normal otherwise.
- bible: the recurring characters (fixed appearance: hair, clothes, age), the car/place/world, era and palette, under
  70 words, so every picture shows the same people and world.
- look: the colour grade that best matches the concept, one of: {", ".join(f"{k} ({v})" for k, v in looks.items())}.
- lyric_preset: one of: {", ".join(f"{k} ({v})" for k, v in presets.items())}.
- lyric_font: a font the concept asks for, from: {", ".join(fonts)}; "" when it doesn't ask for one.
- notes: short plain sentences for the creator about anything in the concept the app can't do literally and what
  it does instead (e.g. lyrics can't sit on the windshield inside the picture; they are shown over the middle of the
  frame). Empty when everything fits."""
    response = _client(client).beta.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=8000,
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
        output_config={"effort": "medium", "format": {"type": "json_schema", "schema": DIRECTION_SCHEMA}},
        messages=[{"role": "user", "content": task}],
    )
    if response.stop_reason == "refusal":
        raise RuntimeError("Claude declined to direct this idea.")
    data = json.loads(next(b.text for b in response.content if b.type == "text"))
    rows = data["sections"][:len(sections)]
    while len(rows) < len(sections):  # rare: repeat the last direction
        rows.append(rows[-1] if rows else {"scene": "", "pace": "normal"})
    return {
        "bible": data["bible"].strip(),
        "sections": [{"scene": r["scene"].strip(), "pace": r["pace"] if r["pace"] in PACES else "normal"} for r in rows],
        "look": data["look"] if data["look"] in looks else "",
        "lyric_preset": data["lyric_preset"] if data["lyric_preset"] in presets else "",
        "lyric_font": data["lyric_font"] if data["lyric_font"] in fonts else "",
        "notes": [n.strip() for n in data["notes"] if n.strip()][:6],
    }
