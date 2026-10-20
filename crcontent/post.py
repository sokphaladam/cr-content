"""Post text ideas: several polished title + description + hashtag packages for a finished video, from Claude."""
import json
from pathlib import Path

import anthropic

from .config import CLAUDE_MODEL, LANGS
from .script import VideoScript, make_client

AI_CREDIT = "Music and vocals are AI-generated."

POSTS_SCHEMA = {
    "type": "object",
    "properties": {
        "options": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "angle": {"type": "string"},
                    "title": {"type": "string"},
                    "description": {"type": "string"},
                    "hashtags": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["angle", "title", "description", "hashtags"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["options"],
    "additionalProperties": False,
}

SYSTEM = """You are the copywriter behind top-performing short-form channels (TikTok, Instagram Reels, YouTube Shorts).
You write the title and description a viewer sees next to a finished video. They must look like a professional
creator wrote them: confident, specific and clean, never generic or spammy.

Titles:
- 30-60 characters (Khmer: under about 40 characters). Front-load the strongest words; they are often cut off.
- Specific beats vague: a number, a name, a vivid detail or a clear promise ("The 3-Second Rule Pilots Swear By",
  not "Interesting Pilot Facts").
- Proven patterns, used honestly: curiosity gap, bold claim, surprising number, direct challenge, contrast,
  "how/why" question, emotional hook (for songs: the hook line, a feeling, a story in a phrase).
- Title Case for English. At most one emoji, and only when it adds meaning. No ALL CAPS sentences, no "!!!",
  no clickbait the video doesn't deliver, no hashtags in the title.

Descriptions:
- Line 1 is a hook that works on its own; only about the first 125 characters show before "more". It never repeats
  or rewords the title (both are shown together): start with the most surprising fact instead.
- When the title or the video simplifies something for effect ("the water boils", "it's immortal"), name the precise
  term once, in passing, e.g. "(technically called cavitation)", so the creator is covered when someone comments
  "that's not really boiling".
- Then 1-3 short lines that add value or intrigue: a key detail, the payoff teased (not spoiled), context.
- End with one easy-to-answer question or call to action that drives comments, saves or shares.
- Short lines separated by line breaks. Emoji sparingly as visual bullets (0-3 total). No hashtags inside it.
- 150-400 characters in total.

Hashtags: 4-7, without the # sign, no spaces. Mix 1-2 broad discovery tags, 2-3 topic tags and 1-2 niche or
long-tail tags. Never use dead tags like fyp, viral, foryou, foryoupage, trending.

Each option takes a clearly different `angle` (2-4 words naming it, e.g. "Curiosity gap", "Bold claim",
"Emotional story", "Listicle", "Relatable"), so the user has real choices, not rewordings.
Everything must be true to the video. Write titles and descriptions in the requested language; `angle` in English."""

KHMER_NOTE = """
The language is Khmer. Write natural, modern Khmer the way popular Cambodian creators post, with a normal space
between phrases. Hashtags may mix Khmer and English (English for broad discovery tags)."""


def _context(job: Path) -> dict:
    """What the video is about: everything the copywriter needs, from the job's script.json or song.json."""
    if (job / "script.json").exists():
        script = VideoScript.load(job / "script.json")
        return {"kind": "faceless short video", "current_title": script.title,
                "narration_by_scene": [s.narration for s in script.scenes],
                "on_screen_headlines": [s.on_screen_text for s in script.scenes if s.on_screen_text],
                "current_caption": script.caption}
    if (job / "song.json").exists():
        from .lyrics import SongScript

        song = SongScript.load(job / "song.json")
        return {"kind": "music video", "song_title": song.title, "genre": song.genre, "mood": song.mood,
                "lyrics": [l.strip() for s in song.sections for l in s.lyrics if l.strip()][:40],
                "current_caption": song.caption}
    try:
        meta = json.loads((job / "meta.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        meta = {}
    if meta.get("kind") == "clip":  # a campaign clip: what's said in it, and the campaign's caption rules
        from .campaigns import load

        ctx = {"kind": "clip for a sponsored Content Rewards campaign", "current_title": meta.get("title", ""),
               "on_screen_hook": meta.get("hook", ""), "spoken_words": meta.get("transcript", "")}
        try:
            c = load(meta["campaign"])
            ctx.update(campaign_brief=c.brief, campaign_rules=c.requirements.rules,
                       caption_must_include=c.requirements.must_include,
                       required_hashtags=c.requirements.hashtags, required_mentions=c.requirements.mentions,
                       required_disclosure=c.requirements.disclosure)
        except (KeyError, ValueError):
            pass
        return ctx
    return {"kind": "video", "current_title": meta.get("title") or job.name}


def suggest_posts(job: Path, lang: str, count: int = 5, idea: str = "",
                  client: anthropic.Anthropic | None = None) -> list[dict]:
    """`count` post packages (angle, title, description, hashtags) for the video in `job`."""
    profile = LANGS.get(lang, LANGS["en"])
    client = client or make_client()
    prompt = (f"Language: {profile.name}\n"
              f"About the video:\n{json.dumps(_context(job), ensure_ascii=False, indent=2)}\n\n")
    if idea.strip():
        prompt += f"The user's direction for the post:\n<idea>\n{idea.strip()}\n</idea>\nFollow it.\n\n"
    prompt += f"Write {count} options, each with a different angle. Make the first one your strongest pick."
    from .packaging import JOURNEY_RULE, journey

    system = SYSTEM + (KHMER_NOTE if lang == "km" else "")
    if journey():
        system += "\n\n" + JOURNEY_RULE.format(note=journey())
    response = client.beta.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=6000,
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
        output_config={"effort": "medium", "format": {"type": "json_schema", "schema": POSTS_SCHEMA}},
        system=system,
        messages=[{"role": "user", "content": prompt}],
    )
    if response.stop_reason == "refusal":
        raise RuntimeError("Claude declined to write post text for this video.")
    options = json.loads(next(b.text for b in response.content if b.type == "text"))["options"]
    out = []
    for o in options:
        if not o["title"].strip():
            continue
        tags = [h.lstrip("#").replace(" ", "") for h in o["hashtags"] if h.strip("# ")]
        out.append({"angle": o["angle"].strip(), "title": o["title"].strip(),
                    "description": o["description"].strip(), "hashtags": tags})
    return out[:count]


def write_post(job: Path, title: str, description: str, hashtags: list[str]) -> str:
    """Save the chosen post text to post.txt, keeping the AI-music credit a generated song's post must carry, and
    the sources line and music credit a narrated video's post has."""
    old = (job / "post.txt").read_text(encoding="utf-8") if (job / "post.txt").exists() else ""
    tags = " ".join(f"#{h.lstrip('#').replace(' ', '')}" for h in hashtags if h.strip("# "))
    credit = f"\n{AI_CREDIT}\n" if AI_CREDIT in old else ""
    # credits that must stay: the works cited, real photos used (their licence asks for it) and the music
    kept = [line for line in old.splitlines()
            if line.startswith(("Sources: ", "Photo: ", 'Music: "')) and line not in description]
    description = "\n\n".join([description.strip(), *kept])
    text = f"{title.strip()}\n\n{description}\n\n{tags}\n{credit}"
    (job / "post.txt").write_text(text, encoding="utf-8")
    return text


def set_title(job: Path, title: str) -> str:
    """Swap only the title line of post.txt (the description, hashtags and credits stay as they are)."""
    old = (job / "post.txt").read_text(encoding="utf-8") if (job / "post.txt").exists() else ""
    _, _, rest = old.partition("\n")
    text = f"{title.strip()}\n{rest}" if rest else f"{title.strip()}\n"
    (job / "post.txt").write_text(text, encoding="utf-8")
    return text
