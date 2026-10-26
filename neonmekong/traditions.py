"""Art traditions for the lyric video's pictures: how the anime model is asked to draw, in the manner of a well-known
animation tradition. They are prompt presets over the one anime model (no extra download), written as visual traits
(hand-painted backgrounds, luminous skies...) rather than studio names, which a tag-trained model follows far better.
The tags go first in the prompt, because the model reads only the first ~75 tokens.

A song keeps one tradition for all its pictures (pictures.json "tradition") so they look like one film.
"""
import re

DEFAULT = ""   # plain anime
TRADITIONS = {
    "": {"label": "Anime (default)", "hint": "Clean modern anime illustration", "front": "", "avoid": ""},
    "ghibli": {
        "label": "Ghibli-like, hand-painted",
        "hint": "Watercolor-painted backgrounds, lush nature, big cumulus clouds, warm natural light",
        "front": "hand-painted background, watercolor, lush greenery, fluffy cumulus clouds, warm natural light, "
                 "nostalgic, 1990s anime film",
        "avoid": "neon, glowing, 3d, cgi, sharp digital shading, lens flare",
        "moods": ("dream", "hopeful", "nostalgi", "tender", "gentle", "folk", "acoustic", "warm", "summer"),
    },
    "shinkai": {
        "label": "Luminous skies (Shinkai-like)",
        "hint": "Hyper-detailed twilight skies, glowing city lights, lens flare, emotional distance",
        "front": "luminous sky, twilight gradient, highly detailed clouds, glowing city lights, lens flare, "
                 "light rays, anime film background",
        "avoid": "flat colors, simple background, sketch",
        "moods": ("longing", "yearning", "romantic", "love", "lonely", "bittersweet", "night", "city", "hopeful"),
    },
    "lofi": {
        "label": "Lofi cozy room",
        "hint": "A cozy room at night: lamp glow, window, plants, books, a cat; calm and warm",
        "front": "cozy room, warm lamp light, window at night, indoor plants, books, a cat, lo-fi aesthetic, "
                 "soft shadows, limited warm palette",
        "avoid": "crowd, harsh light, neon, outdoors",
        "moods": ("lofi", "lo-fi", "chill", "study", "ambient", "soft", "sleep", "calm", "acoustic"),
    },
    "cel90s": {
        "label": "90s cel anime",
        "hint": "Hand-drawn cel look: muted palette, film grain, soft retro colour, VHS-era anime",
        "front": "1990s anime, cel shading, retro anime screencap, muted colors, film grain, hand-drawn, "
                 "slightly faded colors",
        "avoid": "3d, cgi, glossy, hyper detailed, modern digital",
        "moods": ("retro", "vintage", "90s", "nostalgic", "disco", "funk", "oldies", "vhs", "memory", "psych"),
    },
    "citypop": {
        "label": "City pop (80s poster)",
        "hint": "Airbrushed 80s Japanese poster art: neon pastels, palm trees, sunsets, convertibles",
        "front": "1980s city pop illustration, airbrushed, pastel neon colors, sunset gradient, palm trees, "
                 "retro poster art, shiny highlights",
        "avoid": "dark, gritty, muted colors, realistic",
        "moods": ("city pop", "synthwave", "neon", "nu-disco", "disco", "funk", "dance", "summer", "night drive"),
    },
    "storybook": {
        "label": "Storybook watercolor",
        "hint": "Soft picture-book painting: gouache and watercolor, gentle shapes, paper texture",
        "front": "storybook illustration, soft watercolor and gouache, painterly, gentle rounded shapes, paper "
                 "texture, traditional media, pastel palette",
        "avoid": "sharp lines, 3d, neon, photorealistic, glossy",
        "moods": ("lullaby", "children", "folk", "whimsical", "tender", "sleep", "gentle", "innocent"),
    },
}


CUSTOM = "custom"   # the user's own: their words for the look, kept with the song
MAX_CUSTOM = 240


def pick(key: str | None) -> str:
    """A known tradition key (or "custom"), else the default."""
    return key if key in TRADITIONS or key == CUSTOM else DEFAULT


def clean(text: str | None) -> str:
    """The user's words as one short line of tags."""
    parts = [re.sub(r"\s+", " ", x).strip() for x in re.split(r"[,\n]+", text or "")]
    return ", ".join(x for x in parts if x)[:MAX_CUSTOM].strip(" ,")


def suggest(data: dict) -> str:
    """The tradition whose mood words match the song's mood, genre and scene idea the most; plain anime when none do."""
    text = f"{data.get('mood_phrase') or ''} {data.get('genre') or ''} {data.get('scene_theme') or ''}".lower()
    best, top = DEFAULT, 0
    for key, t in TRADITIONS.items():
        score = sum(1 for w in t.get("moods", ()) if re.search(rf"(?<!\w){re.escape(w)}", text))
        if score > top:
            best, top = key, score
    return best


def apply(prompt: str, key: str | None, custom: str = "") -> str:
    """`prompt` with the tradition's traits in front (a tag prompt stays a tag prompt). `custom`: the user's own
    description, used for the "custom" tradition."""
    front = clean(custom) if pick(key) == CUSTOM else TRADITIONS[pick(key)]["front"]
    return f"{front}, {prompt}" if front else prompt


def avoid(key: str | None, custom: str = "") -> str:
    return clean(custom) if pick(key) == CUSTOM else TRADITIONS[pick(key)]["avoid"]


def catalog() -> dict:
    out = {k: {"label": t["label"], "hint": t["hint"]} for k, t in TRADITIONS.items()}
    out[CUSTOM] = {"label": "My own style…",
                   "hint": "Describe the look in your own words, as short tags (for example: oil painting, thick brush "
                           "strokes, moody blue light)"}
    return out
