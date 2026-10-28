"""Write an original song (lyrics + structure + sound) with Gemini as validated, structured JSON."""
import json
import re
from pathlib import Path

from . import llm
from pydantic import BaseModel, Field

from .config import LLM_MODEL, LANGS
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
- title: a short, memorable song title (1-5 words), usually taken from the hook.
- caption: the social post caption in the requested language: a first line that hooks on its own (a feeling or a
  story in a phrase), then a question that is easy to answer to drive comments. Short lines, 0-2 emoji.
- hashtags: 4-7 tags without the # sign, mixing broad music tags and niche topic tags; never fyp, viral or trending."""

KHMER_NOTE = """
The language is Khmer. Write natural, singable Khmer lyrics. Put a normal space between phrases every 2-5 words,
because captions are timed per space-separated phrase."""


def generate_song(topic: str, lang: str = "en", seconds: int = 45, style: str = "", vocal: str = "",
                  client: llm.Client | None = None) -> SongScript:
    """Ask Gemini for an original song about `topic`, sized to about `seconds` long."""
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
        model=LLM_MODEL,
        max_tokens=16000,
        output_config={"effort": "medium", "format": {"type": "json_schema", "schema": SCHEMA}},
        system=system,
        messages=[{"role": "user", "content": prompt}],
    )
    if response.stop_reason == "refusal":
        raise RuntimeError(f"Gemini declined this song topic: {response.stop_details}")
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


# ---------- Your own song: lyrics you paste for an mp3 you upload ----------

_HEADER = re.compile(r"^\s*[\[(]\s*([^\])]{1,40}?)\s*[\])]\s*:?\s*$|^\s*([A-Za-z][\w -]{0,30}?(?:\s*\d+)?)\s*:\s*$")
_SECTION_WORDS = ("verse", "chorus", "pre-chorus", "prechorus", "hook", "bridge", "intro", "outro", "refrain",
                  "interlude", "drop", "breakdown", "post-chorus", "instrumental", "solo", "rap")


_SECTION_NAME = re.compile(r"^(?:(?:final|last|first|second|third|double|short|extended|big)\s+)?(?:%s)\b"
                           % "|".join(re.escape(w) for w in _SECTION_WORDS), re.IGNORECASE)
# "Guitar Solo", "Piano Interlude", "Beat Drop 2": a short name that ends with the section word
_NAMED_SECTION = re.compile(r"^[\w\'-]+(?:\s+[\w\'-]+){0,2}?\s+(?:%s)(?:\s*\d+)?$"
                            % "|".join(re.escape(w) for w in _SECTION_WORDS), re.IGNORECASE)
_NOTE = re.compile(r"^\s*\[([^\]]*)\]?\s*$")
_INLINE_NOTE = re.compile(r"\s*\[[^\]]*\]\s*")


def _header_name(line: str) -> str | None:
    """'[Chorus]', '(Verse 2)', 'Bridge:', '[Final Chorus]' -> the section name; None for anything else."""
    m = _HEADER.match(line)
    if not m:
        return None
    name = (m.group(1) or m.group(2) or "").strip()
    # "(oh-oh)", "And she said:" or "[Drums drop out, floating vocals]" aren't headers: a header starts with
    # the section's name
    if not (_SECTION_NAME.match(name) or _NAMED_SECTION.match(name)):
        return None
    return name[:1].upper() + name[1:]


_PAREN_NOTE = re.compile(r"^\s*\(([^()]*)\)\s*$")
# words that make a whole-line (parenthesis) a sound direction rather than a sung backing line like "(oh-oh)"
_SOUND_WORDS = re.compile(
    r"\b(drums?|bass|synths?|guitars?|piano|rhodes|keys|strings|pads?|organ|horns?|brass|beat|loop|kick|snare|"
    r"hi-?hats?|vocals?|harmon(y|ies)|falsetto|choir|ad-?libs?|reverb|echo(es|ing)?|delay|phaser|filter(ed)?|"
    r"fades?|fading|tape|vinyl|instrumental|solo|bars?|build(s|ing)?|drops?|sweep|swell|riser|breakdown|"
    r"tempo|half-?time|key change|outro|intro|spoken|whisper(ed|s)?|hum(s|ming)?|silence|sfx|full band)\b",
    re.IGNORECASE)


def _note(line: str) -> str | None:
    """'[Warbly Rhodes, tape hiss]' or '(Drums drop out, reverb vocals)' -> the production note inside; None for a sung
    line.

    Song generators (and the people who write for them) put sound directions in square brackets, or in parentheses;
    they're never sung. A line in parentheses only counts when it describes sound, so a sung "(oh-oh)" or
    "(where my love)" stays a lyric.
    """
    m = _NOTE.match(line)
    if m:
        return m.group(1).strip()
    m = _PAREN_NOTE.match(line)
    if m and _SOUND_WORDS.search(m.group(1)):
        return m.group(1).strip()
    return None


def move_notes(song: "SongScript") -> bool:
    """Sound directions that ended up among the sung lines (songs added before they were recognised) become the
    section's styles. Returns True when something moved."""
    moved = False
    for section in song.sections:
        notes = [n for n in (_note(" ".join(l.split())) for l in section.lyrics) if n is not None]
        if notes:
            section.lyrics = [l for l in section.lyrics if _note(" ".join(l.split())) is None]
            section.styles += [n for n in notes if n]
            moved = True
    return moved


def parse_lyrics(text: str) -> list[SongSection]:
    """Pasted lyrics -> sections. [Verse 1] / Chorus: style headers start sections; without headers,
    blank lines separate them. Other [square bracket] lines are production notes: they become the section's
    styles, never lyrics. Times are filled in later from the audio."""
    sections: list[SongSection] = []
    current: SongSection | None = None
    has_headers = any(_header_name(" ".join(l.split())) for l in text.splitlines())

    def start(name: str) -> SongSection:
        section = SongSection(name=name, lyrics=[], seconds=0, visual_query="")
        sections.append(section)
        return section

    for raw in text.splitlines():
        line = " ".join(raw.split())
        name = _header_name(line) if line else None
        note = None if name or not line else _note(line)
        if name:
            current = start(name)
        elif not line:
            if not has_headers:
                current = None  # blank line = next section
        elif note is not None:
            if note:
                current = current or start(f"Part {len(sections) + 1}")
                current.styles.append(note)
        else:
            line = _INLINE_NOTE.sub(" ", line).strip()  # "Hold on [whispered]" -> "Hold on"
            if not line:
                continue
            if current is None:
                current = start(f"Part {len(sections) + 1}")
            current.lyrics.append(line)
    # keep instrumental parts (intro, solo, break): they still get their own footage
    return [s for s in sections if s.lyrics or s.styles or has_headers]


DESCRIBE_SCHEMA = {
    "type": "object",
    "properties": {
        "genre": {"type": "string"},
        "mood": {"type": "string"},
        "visual_queries": {"type": "array", "items": {"type": "string"}},
        "caption": {"type": "string"},
        "hashtags": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["genre", "mood", "visual_queries", "caption", "hashtags"],
    "additionalProperties": False,
}


def _sections_text(song: SongScript) -> str:
    """The lyrics by section, with any sound notes, as Gemini reads them."""
    return "\n\n".join(f"[{i + 1}. {s.name}]\n" + (f"(sound: {'; '.join(s.styles)})\n" if s.styles else "")
                       + ("\n".join(s.lyrics) or "(instrumental)")
                       for i, s in enumerate(song.sections))


# What makes stock footage look like a real music video rather than a slideshow
SHOT_GUIDE = (
    "Write each search like a cinematographer's shot, using words stock sites tag their best clips with: a concrete "
    "subject plus one shot word such as aerial, silhouette, slow motion, close up, golden hour, neon, bokeh, "
    "timelapse, drone, rain, backlit. Prefer moody, atmospheric, well-lit scenery and anonymous people seen from "
    "behind or far away; avoid talking heads, text, logos, screens and office scenes.")


def describe_song(song: SongScript, lang: str, client: llm.Client | None = None) -> None:
    """Fill in footage searches per section, plus mood, caption and hashtags, by having Gemini read the lyrics."""
    client = client or make_client()
    prompt = (
        f"Song title: {song.title}\nLanguage: {LANGS[lang].name}\n\nLyrics by section:\n{_sections_text(song)}\n\n"
        f"This is the user's own finished song; we are making a music video for it from stock footage.\n"
        f"- visual_queries: exactly {len(song.sections)} items, one per section in order. Each is an ENGLISH stock "
        f"video search of 2-4 concrete words that a site like Pexels really has, matching that section's imagery "
        f"and mood. Keep a consistent look across the song (same setting/colour palette), vary the shots.\n"
        f"  {SHOT_GUIDE}\n"
        f"- genre and mood: a few words each, guessed from the lyrics.\n"
        f"- caption: a social post caption in {LANGS[lang].name} for the music video: a first line that hooks on its "
        f"own, then a question that is easy to answer. Short lines, 0-2 emoji.\n"
        f"- hashtags: 4-7 without the # sign, broad music tags plus niche ones; never fyp, viral or trending."
    )
    response = client.beta.messages.create(
        model=LLM_MODEL,
        max_tokens=4000,
        output_config={"effort": "low", "format": {"type": "json_schema", "schema": DESCRIBE_SCHEMA}},
        messages=[{"role": "user", "content": prompt}],
    )
    if response.stop_reason == "refusal":
        raise RuntimeError("Gemini declined to describe these lyrics.")
    data = json.loads(next(b.text for b in response.content if b.type == "text"))
    queries = [q.strip() for q in data["visual_queries"] if q.strip()]
    for i, s in enumerate(song.sections):
        s.visual_query = queries[i] if i < len(queries) else (queries[-1] if queries else "")
    song.genre, song.mood = data["genre"], data["mood"]
    song.caption = data["caption"]
    song.hashtags = [h.lstrip("#").replace(" ", "") for h in data["hashtags"]]


IDEA_SCHEMA = {
    "type": "object",
    "properties": {"visual_queries": {"type": "array", "items": {"type": "string"}}},
    "required": ["visual_queries"],
    "additionalProperties": False,
}


def plan_footage(song: SongScript, lang: str, idea: str, client: llm.Client | None = None) -> list[str]:
    """One stock-footage search per section that carries out the user's own idea for the video (setting, story,
    look), fitted to what each section sings about."""
    client = client or make_client()
    prompt = (
        f"Song title: {song.title}\nLanguage: {LANGS[lang].name}\n\nLyrics by section:\n{_sections_text(song)}\n\n"
        f"We are making a music video for this song from stock footage. The user's idea for the video:\n"
        f"<idea>\n{idea.strip()}\n</idea>\n\n"
        f"- visual_queries: exactly {len(song.sections)} items, one per section in order. Each is an ENGLISH stock "
        f"video search of 2-4 concrete words that a site like Pexels really has. Follow the user's idea (its setting, "
        f"characters, story and look) through the whole song, and let each section's lyrics and energy pick the "
        f"moment: quieter shots for verses and instrumental parts, the most striking shots for choruses. Vary the "
        f"shots; never repeat a search.\n{SHOT_GUIDE}"
    )
    response = client.beta.messages.create(
        model=LLM_MODEL,
        max_tokens=4000,
        output_config={"effort": "low", "format": {"type": "json_schema", "schema": IDEA_SCHEMA}},
        messages=[{"role": "user", "content": prompt}],
    )
    if response.stop_reason == "refusal":
        raise RuntimeError("Gemini declined this video idea.")
    queries = [q.strip() for q in json.loads(next(b.text for b in response.content if b.type == "text"))["visual_queries"]
               if q.strip()]
    if not queries:
        raise RuntimeError("no footage searches came back")
    return [queries[i] if i < len(queries) else queries[-1] for i in range(len(song.sections))]


IDEAS_SCHEMA = {
    "type": "object",
    "properties": {
        "ideas": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "idea": {"type": "string"},
                    "look": {"type": "string", "enum": ["natural", "cinematic", "film", "moody", "vibrant", "mono"]},
                    "lyric_style": {"type": "string",
                                    "enum": ["classic", "neon", "bold_pop", "cinematic", "minimal", "boxed"]},
                },
                "required": ["title", "idea", "look", "lyric_style"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["ideas"],
    "additionalProperties": False,
}


def suggest_video_ideas(song: SongScript, lang: str, count: int = 4,
                        client: llm.Client | None = None) -> list[dict]:
    """Music video concepts for this song, each with a matching colour grade and lyric style, to pick from."""
    client = client or make_client()
    prompt = (
        f"Song title: {song.title}\nLanguage: {LANGS[lang].name}\n"
        + (f"Genre: {song.genre}\nMood: {song.mood}\n" if song.genre or song.mood else "")
        + f"\nLyrics by section:\n{_sections_text(song)}\n\n"
        f"Suggest {count} different music video concepts for this song, the way a music video director would pitch "
        f"them. The video is cut from stock footage (Pexels / Pixabay), so every concept must be filmable with "
        f"stock clips: real places, nature, cities, weather, light, anonymous people seen from behind or far away. "
        f"No specific actors, faces, story beats that need one recurring character, animation or text on screen.\n"
        f"- title: 2-4 words naming the concept.\n"
        f"- idea: 1-2 sentences in English describing the setting, the light and the feeling, specific enough to "
        f"plan shots from (e.g. 'Empty city streets at blue hour, rain on neon signs and car windows, a lone "
        f"figure walking under an umbrella').\n"
        f"- look: the colour grade that suits it (cinematic = teal and orange, film = warm grainy, moody = dark and "
        f"muted, vibrant = punchy colour, mono = black and white, natural = clean).\n"
        f"- lyric_style: how the lyrics should look (classic karaoke, neon glow, bold_pop for upbeat TikTok-style "
        f"word pops, cinematic serif fades for ballads, minimal, boxed).\n"
        f"Make the concepts clearly different from each other: one close to the lyrics' literal imagery, one more "
        f"abstract or atmospheric, and at least one bold, striking choice."
    )
    response = client.beta.messages.create(
        model=LLM_MODEL,
        max_tokens=4000,
        output_config={"effort": "low", "format": {"type": "json_schema", "schema": IDEAS_SCHEMA}},
        messages=[{"role": "user", "content": prompt}],
    )
    if response.stop_reason == "refusal":
        raise RuntimeError("Gemini declined to suggest ideas for these lyrics.")
    ideas = json.loads(next(b.text for b in response.content if b.type == "text"))["ideas"]
    return [i for i in ideas if i["idea"].strip()][:count]


def idea_queries(song: SongScript, lang: str, idea: str, log=print) -> list[str]:
    """Footage searches for the idea: Gemini's plan, or without Gemini the idea's own words for every section."""
    try:
        return plan_footage(song, lang, idea)
    except Exception as e:  # no key, no credits, offline
        log(f"      ! Gemini couldn't plan footage for your idea ({e.__class__.__name__}); searching for the idea itself")
        words = " ".join(idea.split()[:6])
        return [words] * len(song.sections)


# when Gemini isn't available: calm, broadly fitting footage that rotates per section
FALLBACK_QUERIES = ("city lights night", "ocean waves sunset", "clouds sky timelapse", "forest sunlight",
                    "rain window", "road trip drive", "stars night sky", "flowers field")


def own_song(title: str, lyrics: str, lang: str, log=print) -> SongScript:
    """SongScript for an uploaded song: sections from the pasted lyrics, footage ideas from Gemini when possible."""
    sections = parse_lyrics(lyrics)
    if not sections:
        raise ValueError("Paste the song's lyrics first.")
    song = SongScript(title=title.strip() or "Untitled song", genre="", mood="", bpm=0, vocal="", styles=[], avoid=[],
                      sections=sections, caption="", hashtags=[])
    try:
        describe_song(song, lang)
        log(f"      -> {len(sections)} sections; footage: " + ", ".join(s.visual_query for s in sections))
    except Exception as e:  # no key, no credits, offline: generic footage is still a usable video
        log(f"      ! Gemini couldn't suggest footage ({e.__class__.__name__}); using general scenery")
        for i, s in enumerate(song.sections):
            s.visual_query = FALLBACK_QUERIES[i % len(FALLBACK_QUERIES)]
    return song
