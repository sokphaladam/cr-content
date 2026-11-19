"""Post text ideas: several polished title + description + hashtag packages for a finished video, from Gemini."""
import json
import re
from pathlib import Path

from . import llm

from .config import LLM_MODEL, LANGS
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
- Leave the answer for the video. Titles that open a question without answering it score far higher than ones that
  name the payoff. Scored on vidIQ for a hagfish Short (2026-11-19): "What Happens When A Shark Bites This Fish 😱"
  97 and "What This Fish Does When A Shark Bites 😱" 95, against "This Fish Chokes Sharks With Slime 😱" 84 and
  "Why Sharks Spit Out This Fish 🦈" 87. So: a plain "What happens when…" / "What this … does when…" setup, a
  concrete subject ("this fish", "a shark"), the reveal held back, one reaction emoji (😱 😳) at the end.
  History stories score the same way (2026-11-20, Dyatlov Pass Short): "What Happened When 9 Hikers Fled Their Tent
  At Night 😳" 98, against "What Made 9 Hikers Cut Their Way Out Of Their Tent 😱" 89: ask what happened, never
  what caused it ("What made…", "Why did…" score lower). Aim for 90+ on vidIQ: the FIRST option is always this
  "What happens/happened when…" shape, with a number or a named subject in it.

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
                  client: llm.Client | None = None) -> list[dict]:
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
        model=LLM_MODEL,
        max_tokens=6000,
        output_config={"effort": "medium", "format": {"type": "json_schema", "schema": POSTS_SCHEMA}},
        system=system,
        messages=[{"role": "user", "content": prompt}],
    )
    if response.stop_reason == "refusal":
        raise RuntimeError("Gemini declined to write post text for this video.")
    options = json.loads(next(b.text for b in response.content if b.type == "text"))["options"]
    out = []
    for o in options:
        if not o["title"].strip():
            continue
        tags = [h.lstrip("#").replace(" ", "") for h in o["hashtags"] if h.strip("# ")]
        p = {"angle": o["angle"].strip(), "title": o["title"].strip(), "description": o["description"].strip(),
             "hashtags": tags}
        if lang == "en":  # the rules are English patterns
            p["score"], p["issues"] = check_post(p["title"], p["description"], tags)
        out.append(p)
    out.sort(key=lambda p: -p.get("score", 0))  # stable: unscored keeps Gemini's order
    return out[:count]


EMOJI = re.compile("[\U0001F300-\U0001FAFF☀-➿]")
DEAD_TAGS = {"fyp", "viral", "foryou", "foryoupage", "trending"}


def check_post(title: str, description: str, hashtags: list[str]) -> tuple[int, list[str]]:
    """(0-100, what lost points): a local stand-in for vidIQ's title score, from the patterns that scored 90+ there
    (see SYSTEM). shortcut: fixed rules, not vidIQ itself; re-check a few picks on vidIQ when the rules drift."""
    score, issues = 100, []

    def miss(points: int, why: str) -> None:
        nonlocal score
        score -= points
        issues.append(why)

    t = title.strip()
    low = t.lower()
    if not re.match(r"what (happens|happened) when|what (this|these|a|an|the) .+ (does|did|do) when", low):
        miss(20, 'Title: no "What happens/happened when…" setup')
    if re.match(r"(what made|why (did|do|does|is|are))\b", low):
        miss(10, 'Title: asks for the cause ("What made…", "Why…")')
    if not re.search(r"\d|\b(this|these)\b", low):
        miss(10, "Title: no number or concrete subject")
    if not 30 <= len(t) <= 60:
        miss(10, f"Title: {len(t)} characters (30-60 reads best)")
    emojis = EMOJI.findall(t)
    if len(emojis) != 1 or not EMOJI.search(t[-2:]):
        miss(10, "Title: needs exactly one reaction emoji, at the end")

    lines = [line for line in description.strip().splitlines() if line.strip()]
    first = lines[0] if lines else ""
    title_words = set(re.findall(r"[a-z']{4,}", low))
    first_words = set(re.findall(r"[a-z']{4,}", first.lower()))
    if len(first) > 125 or (title_words and len(title_words & first_words) / len(title_words) >= 0.5):
        miss(10, "Description: first line is over 125 characters or repeats the title")
    if not 150 <= len(description.strip()) <= 400:
        miss(10, f"Description: {len(description.strip())} characters (150-400)")
    if not lines or "?" not in lines[-1]:
        miss(10, "Description: doesn't end with a question")
    if "#" in description or DEAD_TAGS & {h.lower() for h in hashtags}:
        miss(10, "Hashtags inside the description, or dead tags (fyp, viral…)")
    return max(score, 0), issues


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
