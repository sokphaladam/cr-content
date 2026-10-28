"""Packaging: what decides whether a video gets clicked and watched, before anyone judges the content.

- fluff_opening: the stock intros ("welcome back", "in this video") that lose viewers in the first seconds
- review: Gemini scores a finished video's title, thumbnail and opening together and writes stronger ones
- outliers: YouTube videos that got far more views than their channel has subscribers (5:1 or more) but are packaged
  or delivered weakly, so a better-made version of the same idea has a proven audience
- journey: the creator's own progress note, worked honestly into descriptions (never into a video's opening)
"""
import base64
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

from . import llm
import requests

from .config import LLM_MODEL, LANGS, ROOT
from .script import VideoScript, make_client

CHANNEL_FILE = ROOT / "channel.json"
YOUTUBE_API = "https://www.googleapis.com/youtube/v3"

# openings that make a viewer wait for the point; checked in the first ~30 words
FLUFF = [
    (r"\b(hey|hi|hello|what'?s up),? (guys|everyone|everybody|y'?all|friends)\b", "a greeting"),
    (r"\bwelcome (back )?to (my|the|our) (channel|video)\b|\bwelcome back\b", "\"welcome back\""),
    (r"\bin (this|today'?s) (video|episode)\b", "\"in this video\""),
    (r"\btoday,? (we'?re|we are|i'?m|i am) (going to|gonna) (talk|look|show|discuss|be)\b", "\"today we're going to...\""),
    (r"\bbefore we (start|begin|get (started|into it))\b", "\"before we start\""),
    (r"\b(don'?t forget to|make sure (you|to)) (like|subscribe|hit)\b|\bsmash (that|the) like\b", "a subscribe request"),
    (r"\blet'?s (get (started|into it)|dive (right )?in|begin)\b", "\"let's get started\""),
    (r"\bmy name is\b|\bi'?m your host\b", "an introduction"),
    (r"\b(so,? )?without further ado\b", "\"without further ado\""),
    (r"\bhave you ever wondered\b", "\"have you ever wondered\""),
    # Khmer: hello / welcome back / today we will talk about / don't forget to subscribe
    (r"សួស្តី|ជំរាបសួរ", "a greeting"),
    (r"សូមស្វាគមន៍", "\"welcome\""),
    (r"ថ្ងៃនេះ\s*(យើង|ខ្ញុំ)\s*(នឹង|នឹងមក)", "\"today we're going to...\""),
    (r"កុំភ្លេច\s*(subscribe|ចុច)", "a subscribe request"),
]


def fluff_opening(text: str, words: int = 30) -> list[str]:
    """What in the opening of `text` makes the viewer wait (empty = it gets straight to the point)."""
    start = " ".join(text.split()[:words]).lower()
    found = []
    for pattern, what in FLUFF:
        if re.search(pattern, start) and what not in found:
            found.append(what)
    return found


# ---------- the creator's journey ----------

def journey() -> str:
    try:
        return json.loads(CHANNEL_FILE.read_text(encoding="utf-8")).get("journey", "")
    except (OSError, ValueError):
        return ""


def set_journey(text: str) -> str:
    try:
        data = json.loads(CHANNEL_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        data = {}
    data["journey"] = text.strip()[:400]
    CHANNEL_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return data["journey"]


JOURNEY_RULE = """The creator shares their journey with viewers, so viewers feel they grow with the channel. Their note:
<journey>
{note}
</journey>
Work it into the description as ONE short, honest, first-person line near the end (before the closing question),
e.g. "Video 23 of posting every day. Thanks for being here this early." Never invent numbers the note doesn't give,
never brag or beg for subscribers, and never put it in the title or the first line."""


# ---------- packaging review of a finished video ----------

def _opening(job: Path) -> str:
    """The first thing the viewer hears or reads."""
    if (job / "script.json").exists():
        scenes = VideoScript.load(job / "script.json").scenes
        return " ".join(s.narration for s in scenes[:1])
    if (job / "song.json").exists():
        from .lyrics import SongScript

        lines = [l.strip() for s in SongScript.load(job / "song.json").sections for l in s.lyrics if l.strip()]
        return " / ".join(lines[:2])
    if (job / "scenes.json").exists():  # a long video
        from .longform.parse import Script

        scenes = Script.load(job / "scenes.json").scenes
        return " ".join(s.voiceover for s in scenes[:2])
    return ""


def _post(job: Path) -> tuple[str, str]:
    post = (job / "post.txt").read_text(encoding="utf-8") if (job / "post.txt").exists() else ""
    title, _, rest = post.partition("\n")
    return title.strip(), rest.strip()


REVIEW_SCHEMA = {
    "type": "object",
    "properties": {
        "title": {"type": "object", "properties": {"score": {"type": "integer"}, "verdict": {"type": "string"}},
                  "required": ["score", "verdict"], "additionalProperties": False},
        "thumbnail": {"type": "object", "properties": {"score": {"type": "integer"}, "verdict": {"type": "string"}},
                      "required": ["score", "verdict"], "additionalProperties": False},
        "opening": {"type": "object", "properties": {"score": {"type": "integer"}, "verdict": {"type": "string"}},
                    "required": ["score", "verdict"], "additionalProperties": False},
        "titles": {"type": "array", "items": {"type": "string"}},
        "thumbnail_texts": {"type": "array", "items": {
            "type": "object", "properties": {"text": {"type": "string"}, "emphasis": {"type": "string"}},
            "required": ["text", "emphasis"], "additionalProperties": False}},
        "opening_line": {"type": "string"},
        "fixes": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["title", "thumbnail", "opening", "titles", "thumbnail_texts", "opening_line", "fixes"],
    "additionalProperties": False,
}

REVIEW_SYSTEM = """You are a YouTube packaging strategist. You review a finished video the way a viewer meets it:
the thumbnail and title together in the feed, then the first seconds. A good idea dies with weak packaging; the same
idea with a better title, a stronger thumbnail and a tighter delivery wins.

Score each 1-10, honestly (most videos are 4-7; 9-10 is rare), with a one-sentence verdict naming the main problem:
- title: clear in a glance, specific (a number, a name, a vivid detail), a curiosity gap or a promise, front-loaded,
  true to the video. Boring, vague or keyword-stuffed titles score low.
- thumbnail: you see the actual image. One clear subject, high contrast, readable at phone size (2-5 words at most),
  an emotion or a tension, says something the title doesn't (title and thumbnail work as a team, never repeat).
  Clutter, small text, a dull frame or a repeat of the title score low.
- opening: the first words must deliver value at once: the claim, the payoff, the most surprising fact. Any fluff
  (greeting, "in this video", "welcome back", background before the point, a slow build, rambling) scores 3 or less.
  For a song: the first line must be the hook.

Then make it better: `titles`: 3 stronger titles, each a different angle; `thumbnail_texts`: 2 thumbnail headlines
(2-5 words, `emphasis` = the 1-2 punch words copied exactly from the text); `opening_line`: a rewritten first line
that gets straight to the value (for a song: the hook line to open on, from its lyrics); `fixes`: 2-4 short concrete
fixes, most important first (e.g. "Crop tighter on the face", "Cut the first 6 seconds", "Lead with the 40% fact").
Never suggest clickbait the video doesn't deliver. Write titles, headlines and the opening line in the video's
language; verdicts and fixes in English."""


def review(job: Path, lang: str, client: llm.Client | None = None) -> dict:
    """Scores and stronger alternatives for the video's title, thumbnail and opening, plus the stock intros found in
    the opening by fluff_opening (`fluff`)."""
    from .post import _context

    client = client or make_client()
    title, description = _post(job)
    opening = _opening(job)
    info = {**_context(job), "title_shown": title, "description_start": description[:300],
            "opening_words": opening}
    meta = {}
    try:
        meta = json.loads((job / "meta.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        pass
    if meta.get("kind") == "long_video":
        info["kind"] = "long YouTube video (16:9)"
    content: list[dict] = []
    if (job / "thumbnail.jpg").exists():
        content += [{"type": "text", "text": "The thumbnail:"},
                    {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg",
                                                 "data": base64.b64encode((job / "thumbnail.jpg").read_bytes()).decode()}}]
    else:
        info["thumbnail"] = "none made yet: score it 1 and say so"
    content.append({"type": "text", "text": f"Language: {LANGS.get(lang, LANGS['en']).name}\n"
                                            f"The video:\n{json.dumps(info, ensure_ascii=False, indent=2)}"})
    response = client.beta.messages.create(
        model=LLM_MODEL,
        max_tokens=4000,
        output_config={"effort": "medium", "format": {"type": "json_schema", "schema": REVIEW_SCHEMA}},
        system=REVIEW_SYSTEM,
        messages=[{"role": "user", "content": content}],
    )
    if response.stop_reason == "refusal":
        raise RuntimeError("Gemini declined to review this video.")
    out = json.loads(next(b.text for b in response.content if b.type == "text"))
    for k in ("title", "thumbnail", "opening"):
        out[k]["score"] = max(1, min(10, out[k]["score"]))
    out["titles"] = [t.strip() for t in out["titles"] if t.strip()][:3]
    out["thumbnail_texts"] = [t for t in out["thumbnail_texts"] if t["text"].strip()][:2]
    out["fluff"] = fluff_opening(opening)
    out["current_title"] = title
    return out


# ---------- outliers: proven ideas, weakly packaged ----------

class OutlierError(RuntimeError):
    pass


def _youtube_get(path: str, params: dict) -> dict:
    """A YouTube Data API read, with YOUTUBE_API_KEY when it's set, else the connected channel's sign-in."""
    import os

    key = os.getenv("YOUTUBE_API_KEY", "").strip()
    headers = {}
    if key:
        params = {**params, "key": key}
    else:
        from . import publish

        if not publish.connected("youtube"):
            raise OutlierError("Connect a YouTube channel in Settings → Channels, or add a YouTube Data API key in "
                               "Settings → Services, to search YouTube.")
        try:
            headers["Authorization"] = f"Bearer {publish._token('youtube')}"
        except publish.PublishError as e:
            raise OutlierError(f"YouTube sign-in: {e}")
    r = requests.get(f"{YOUTUBE_API}/{path}", params=params, headers=headers, timeout=30)
    if r.status_code != 200:
        try:
            msg = r.json()["error"]["message"]
        except (ValueError, KeyError, TypeError):
            msg = r.text[:200]
        raise OutlierError(f"YouTube search failed ({r.status_code}): {re.sub('<[^>]+>', '', msg)}")
    return r.json()


def _seconds(iso: str) -> int:
    m = re.fullmatch(r"P(?:(\d+)D)?T?(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", iso or "")
    if not m:
        return 0
    d, h, mi, s = (int(x or 0) for x in m.groups())
    return ((d * 24 + h) * 60 + mi) * 60 + s


def find_outliers(query: str, months: int = 12, min_ratio: float = 5.0, length: str = "any") -> list[dict]:
    """Videos about `query` from the last `months` with at least `min_ratio` views per channel subscriber, best
    ratio first. `length`: "short" (under 4 min), "long" (over 4 min) or "any"."""
    after = (datetime.now(timezone.utc) - timedelta(days=30 * months)).strftime("%Y-%m-%dT%H:%M:%SZ")
    params = {"part": "snippet", "q": query, "type": "video", "order": "viewCount", "maxResults": 50,
              "publishedAfter": after, "safeSearch": "moderate"}
    if length == "long":
        params["videoDuration"] = "medium"  # 4-20 min; long-form outliers are mostly here
    elif length == "short":
        params["videoDuration"] = "short"
    found = _youtube_get("search", params).get("items", [])
    ids = [i["id"]["videoId"] for i in found if i.get("id", {}).get("videoId")]
    if not ids:
        return []
    videos = _youtube_get("videos", {"part": "snippet,statistics,contentDetails", "id": ",".join(ids)}).get("items", [])
    channel_ids = list({v["snippet"]["channelId"] for v in videos})
    subs: dict[str, int] = {}
    for k in range(0, len(channel_ids), 50):
        for c in _youtube_get("channels", {"part": "statistics", "id": ",".join(channel_ids[k:k + 50])}).get("items", []):
            st = c.get("statistics", {})
            if not st.get("hiddenSubscriberCount"):
                subs[c["id"]] = int(st.get("subscriberCount", 0))
    out = []
    for v in videos:
        sn, st = v["snippet"], v.get("statistics", {})
        views, sub = int(st.get("viewCount", 0)), subs.get(sn["channelId"], 0)
        if sub < 100 or views < 10_000:  # too small to tell a pattern from luck
            continue
        ratio = views / sub
        if ratio < min_ratio:
            continue
        thumbs = sn.get("thumbnails", {})
        thumb = (thumbs.get("high") or thumbs.get("medium") or thumbs.get("default") or {}).get("url", "")
        out.append({"id": v["id"], "url": f"https://www.youtube.com/watch?v={v['id']}", "title": sn["title"],
                    "channel": sn["channelTitle"], "views": views, "subs": sub, "ratio": round(ratio, 1),
                    "published": sn["publishedAt"][:10], "seconds": _seconds(v.get("contentDetails", {}).get("duration")),
                    "thumbnail": thumb, "description": sn.get("description", "")[:300]})
    out.sort(key=lambda o: o["ratio"], reverse=True)
    return out


JUDGE_SCHEMA = {
    "type": "object",
    "properties": {"videos": {"type": "array", "items": {
        "type": "object",
        "properties": {
            "n": {"type": "integer"},
            "weak": {"type": "array", "items": {"type": "string", "enum": ["title", "thumbnail", "execution"]}},
            "verdict": {"type": "string"},
            "target": {"type": "boolean"},
            "better_title": {"type": "string"},
            "better_thumbnail": {"type": "string"},
            "hook": {"type": "string"},
            "plan": {"type": "string"},
            "topic": {"type": "string"},
        },
        "required": ["n", "weak", "verdict", "target", "better_title", "better_thumbnail", "hook", "plan", "topic"],
        "additionalProperties": False,
    }}},
    "required": ["videos"],
    "additionalProperties": False,
}

JUDGE_SYSTEM = """You find remake opportunities for a creator. Each video below got far more views than its channel
has subscribers, so the IDEA is proven: the algorithm pushed it to people who don't follow the channel. You see its
thumbnail, title and stats.

For each video:
- weak: which of title / thumbnail / execution look weak (boring, unclear, low effort; for execution judge what the
  title, description and length suggest: rambling, no editing, text-only, a slow start). Empty if all are strong.
- target: true when the idea is strong but under-delivered, so a better-made version could beat it. False when it's
  already well made, when it only works because of who made it (a celebrity, a news moment), or when it can't be
  made as a faceless video with stock footage, AI pictures or an AI song.
- verdict: one sentence on why it worked and what's weak.
- better_title: a clearer, stronger title for the remake (specific, front-loaded, honest). better_thumbnail: the
  remake's thumbnail in one line: the picture and its 2-5 words. hook: the remake's first spoken line, straight to
  the value, no intro. plan: 1-2 sentences on the tighter structure and better delivery.
- topic: one line for the script writer, in English: the angle, the format and what to do better. Never copy the
  original's script, only build on the idea.
Write better_title, better_thumbnail and hook in the creator's language; the rest in English."""


def judge_outliers(items: list[dict], lang: str, kind: str = "short", client: llm.Client | None = None) -> list[dict]:
    """Gemini's packaging verdict and a remake plan for each outlier (up to 10), remake targets first."""
    if not items:
        return []
    client = client or make_client()
    items = items[:10]
    content: list[dict] = []
    for n, o in enumerate(items, 1):
        content.append({"type": "text", "text": json.dumps(
            {"n": n, "title": o["title"], "channel": o["channel"], "views": o["views"], "subscribers": o["subs"],
             "views_per_subscriber": o["ratio"], "length_seconds": o["seconds"], "published": o["published"],
             "description_start": o["description"]}, ensure_ascii=False)})
        if o["thumbnail"]:
            content.append({"type": "image", "source": {"type": "url", "url": o["thumbnail"]}})
    content.append({"type": "text", "text": f"The creator's language: {LANGS.get(lang, LANGS['en']).name}. "
                                            f"They will make it as a {kind}. Judge every video."})
    response = client.beta.messages.create(
        model=LLM_MODEL,
        max_tokens=8000,
        output_config={"effort": "medium", "format": {"type": "json_schema", "schema": JUDGE_SCHEMA}},
        system=JUDGE_SYSTEM,
        messages=[{"role": "user", "content": content}],
    )
    if response.stop_reason == "refusal":
        raise RuntimeError("Gemini declined to judge these videos.")
    verdicts = {v["n"]: v for v in json.loads(next(b.text for b in response.content if b.type == "text"))["videos"]}
    out = []
    for n, o in enumerate(items, 1):
        v = verdicts.get(n)
        if v:
            out.append({**o, **{k: v[k] for k in ("weak", "verdict", "target", "better_title", "better_thumbnail",
                                                  "hook", "plan", "topic")}})
        else:
            out.append(o)
    out.sort(key=lambda o: (not o.get("target", False), -o["ratio"]))
    return out
