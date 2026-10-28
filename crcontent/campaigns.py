"""Content Rewards campaigns (Whop): turn a campaign's brief, content requirements and reference materials into
ready-to-post clips.

1. read_campaign: Gemini reads the pasted campaign page into a Campaign (brief, requirements, reference links).
2. prepare_references: download the reference videos (yt-dlp) and transcribe their speech (Whisper).
3. plan_clips: Gemini picks the strongest moments that fit the brief and writes post text that meets the rules.
4. render_clip: cut each moment to 9:16 with captions and an on-screen hook, as a normal output video (so it can
   get a thumbnail, be uploaded or scheduled like any other).

Campaigns live in <ROOT>/campaigns/<id>/campaign.json, their downloaded references in .../refs/.
"""
import html
import json
import re
import shutil
import uuid
from datetime import datetime
from pathlib import Path
from typing import Callable, Literal

import requests
from pydantic import BaseModel, Field

from .config import LLM_MODEL, LANGS, OUTPUT_DIR, ROOT
from .tts import Word

CAMPAIGNS_DIR = ROOT / "campaigns"
VIDEO_EXTS = {".mp4", ".mov", ".mkv", ".webm", ".m4v", ".avi"}
AUDIO_EXTS = {".mp3", ".wav", ".m4a", ".aac", ".ogg", ".flac"}
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp"}
HOOK_SEC = 3.0  # the on-screen hook shows for the first seconds of a clip
MAX_TRANSCRIPT_CHARS = 250_000


class Reference(BaseModel):
    id: str = Field(default_factory=lambda: uuid.uuid4().hex[:8])
    title: str = ""
    url: str = ""
    file: str = ""  # project path (campaigns/<id>/refs/...) once downloaded or uploaded
    kind: Literal["video", "audio", "image", "document", "link"] = "link"
    # new: not fetched yet; ready: usable; manual: can't be downloaded automatically (add the files yourself)
    status: Literal["new", "ready", "manual", "error"] = "new"
    note: str = ""
    duration: float = 0.0
    transcribed: bool = False


class Requirements(BaseModel):
    min_seconds: int = 15
    max_seconds: int = 60
    hashtags: list[str] = []  # without '#'
    mentions: list[str] = []  # accounts to tag, without '@'
    must_include: list[str] = []  # words or calls to action the caption must contain ("link in bio")
    disclosure: str = ""  # e.g. "#ad" or "Paid partnership"
    captions: bool = True  # burn in captions
    rules: list[str] = []  # every content requirement, as the campaign states it
    avoid: list[str] = []  # what the campaign forbids


class Campaign(BaseModel):
    id: str = ""
    name: str
    brand: str = ""
    url: str = ""
    kind: Literal["clipping", "ugc", "other"] = "clipping"
    platforms: list[str] = []  # tiktok, youtube, instagram, x
    rate: str = ""  # "$2 per 1,000 views"
    budget: str = ""
    brief: str = ""
    lang: str = "en"  # caption language (en or km)
    requirements: Requirements = Requirements()
    references: list[Reference] = []
    created: str = ""
    updated: str = ""
    source_text: str = ""  # what the campaign was read from


class ClipPlan(BaseModel):
    ref_id: str
    start: float
    end: float
    hook: str  # on-screen text for the first seconds
    title: str
    description: str
    hashtags: list[str]
    why: str = ""


# ---------- Storage ----------

def _dir(campaign_id: str) -> Path:
    folder = (CAMPAIGNS_DIR / campaign_id).resolve()
    if folder.parent != CAMPAIGNS_DIR.resolve():
        raise KeyError(campaign_id)
    return folder


def load(campaign_id: str) -> Campaign:
    path = _dir(campaign_id) / "campaign.json"
    if not path.exists():
        raise KeyError(campaign_id)
    return Campaign.model_validate_json(path.read_text(encoding="utf-8"))


def save(c: Campaign) -> Campaign:
    if not c.id:
        c.id = datetime.now().strftime("%Y%m%d") + "-" + uuid.uuid4().hex[:6]
        c.created = datetime.now().isoformat(timespec="seconds")
    c.updated = datetime.now().isoformat(timespec="seconds")
    folder = _dir(c.id)
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "campaign.json").write_text(c.model_dump_json(indent=2), encoding="utf-8")
    return c


def list_all() -> list[Campaign]:
    out = []
    if CAMPAIGNS_DIR.exists():
        for f in CAMPAIGNS_DIR.glob("*/campaign.json"):
            try:
                out.append(Campaign.model_validate_json(f.read_text(encoding="utf-8")))
            except ValueError:
                continue
    return sorted(out, key=lambda c: c.updated, reverse=True)


def delete(campaign_id: str) -> None:
    shutil.rmtree(_dir(campaign_id))


def clips(campaign_id: str) -> list[Path]:
    """Output folders of the clips made for this campaign, newest first."""
    found = []
    for folder in OUTPUT_DIR.iterdir():
        try:
            meta = json.loads((folder / "meta.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if meta.get("campaign") == campaign_id:
            found.append((meta.get("created", ""), folder))
    return [f for _, f in sorted(found, reverse=True)]


# ---------- 1. Read the campaign ----------

CAMPAIGN_SCHEMA = {
    "type": "object",
    "properties": {
        "name": {"type": "string"},
        "brand": {"type": "string"},
        "kind": {"type": "string", "enum": ["clipping", "ugc", "other"]},
        "platforms": {"type": "array", "items": {"type": "string", "enum": ["tiktok", "youtube", "instagram", "x"]}},
        "rate": {"type": "string"},
        "budget": {"type": "string"},
        "brief": {"type": "string"},
        "lang": {"type": "string", "enum": ["en", "km"]},
        "min_seconds": {"type": "integer"},
        "max_seconds": {"type": "integer"},
        "hashtags": {"type": "array", "items": {"type": "string"}},
        "mentions": {"type": "array", "items": {"type": "string"}},
        "must_include": {"type": "array", "items": {"type": "string"}},
        "disclosure": {"type": "string"},
        "captions": {"type": "boolean"},
        "rules": {"type": "array", "items": {"type": "string"}},
        "avoid": {"type": "array", "items": {"type": "string"}},
        "references": {"type": "array", "items": {
            "type": "object",
            "properties": {"title": {"type": "string"}, "url": {"type": "string"}},
            "required": ["title", "url"], "additionalProperties": False}},
    },
    "required": ["name", "brand", "kind", "platforms", "rate", "budget", "brief", "lang", "min_seconds",
                 "max_seconds", "hashtags", "mentions", "must_include", "disclosure", "captions", "rules", "avoid",
                 "references"],
    "additionalProperties": False,
}

READ_SYSTEM = """You read Content Rewards campaigns from Whop (brands pay creators per 1,000 views for clips or
short videos that follow their rules) and turn them into structured data for a clip editor.

- brief: what the brand wants, in 2-6 plain sentences: the product or person, the message, the tone and the
  audience. Keep the brand's own key phrases.
- rules: every content requirement as a short imperative line, exactly as strict as the campaign
  ("Mention the app name in the first 3 seconds", "Only use footage from the provided videos").
- avoid: everything the campaign forbids (other brands, reuploads without edits, swearing...).
- hashtags (no #), mentions (no @) and must_include (phrases or calls to action the caption must contain):
  only what the campaign actually requires.
- disclosure: a required ad label such as "#ad" or "Paid partnership", or "".
- min_seconds / max_seconds: the allowed clip length; when unstated use 15 and 60.
- captions: false only if the campaign says not to add captions.
- references: every link to source material, footage, brand assets or examples (YouTube, Google Drive,
  Dropbox, websites). Never invent links. Title each in a few words.
- platforms: where clips may be posted; when unstated, the platforms the campaign mentions.
- rate and budget: as written ("$3 per 1K views", "$10,000"), or "".
- lang: "km" only for a Khmer-language campaign, otherwise "en"."""


def _page_text(url: str) -> str:
    """The readable text of a public page (best effort: Whop pages often need a sign-in, then this is empty)."""
    try:
        r = requests.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
        r.raise_for_status()
    except requests.RequestException:
        return ""
    page = r.text
    metas = re.findall(r'<meta[^>]+(?:property|name)="(?:og:title|og:description|description)"[^>]+content="([^"]*)"', page)
    body = re.sub(r"(?is)<(script|style|noscript)[^>]*>.*?</\1>", " ", page)
    links = re.findall(r'href="(https?://[^"]+)"', body)
    text = re.sub(r"(?s)<[^>]+>", " ", body)
    text = re.sub(r"\s+", " ", html.unescape(text)).strip()
    return "\n".join([*map(html.unescape, metas), text[:30_000], *sorted(set(links))[:80]])


def _claude(system: str, prompt: str, schema: dict, max_tokens: int = 8000) -> dict:
    from .script import make_client

    client = make_client()
    response = client.beta.messages.create(
        model=LLM_MODEL,
        max_tokens=max_tokens,
        output_config={"effort": "medium", "format": {"type": "json_schema", "schema": schema}},
        system=system,
        messages=[{"role": "user", "content": prompt}],
    )
    if response.stop_reason == "refusal":
        raise RuntimeError("Gemini declined this request.")
    return json.loads(next(b.text for b in response.content if b.type == "text"))


def read_campaign(text: str, url: str = "") -> Campaign:
    """A new campaign from the pasted campaign page (and its link, which is read too when it's public)."""
    page = _page_text(url) if url else ""
    if not text.strip() and not page.strip():
        raise ValueError("Couldn't read that page (it may need a sign-in). Copy the campaign text from Whop and paste it.")
    prompt = ""
    if url:
        prompt += f"Campaign link: {url}\n\n"
    if page:
        prompt += f"<page>\n{page}\n</page>\n\n"
    if text.strip():
        prompt += f"<pasted>\n{text.strip()[:60_000]}\n</pasted>\n\n"
    prompt += "Read this campaign."
    d = _claude(READ_SYSTEM, prompt, CAMPAIGN_SCHEMA)
    lo, hi = sorted((max(5, d["min_seconds"]), max(5, d["max_seconds"])))
    req = Requirements(min_seconds=lo, max_seconds=max(hi, lo + 5),
                       hashtags=[h.lstrip("#").replace(" ", "") for h in d["hashtags"] if h.strip("# ")],
                       mentions=[m.lstrip("@").strip() for m in d["mentions"] if m.strip("@ ")],
                       must_include=d["must_include"], disclosure=d["disclosure"].strip(), captions=d["captions"],
                       rules=d["rules"], avoid=d["avoid"])
    seen, refs = set(), []
    for r in d["references"]:
        link = r["url"].strip()
        if link.startswith("http") and link not in seen and link != url:
            seen.add(link)
            refs.append(Reference(title=r["title"].strip(), url=link))
    return save(Campaign(name=d["name"].strip() or "Untitled campaign", brand=d["brand"].strip(), url=url, kind=d["kind"],
                         platforms=d["platforms"], rate=d["rate"], budget=d["budget"], brief=d["brief"].strip(),
                         lang=d["lang"], requirements=req, references=refs, source_text=text.strip()[:60_000]))


# ---------- 2. Reference materials ----------

def _kind(path: Path) -> str:
    ext = path.suffix.lower()
    return ("video" if ext in VIDEO_EXTS else "audio" if ext in AUDIO_EXTS
            else "image" if ext in IMAGE_EXTS else "document")


def ref_path(c: Campaign, ref: Reference) -> Path | None:
    return (ROOT / ref.file) if ref.file and (ROOT / ref.file).exists() else None


def add_file(c: Campaign, src: Path, title: str) -> Reference:
    """A reference file you uploaded (moved into the campaign's refs folder)."""
    refs = _dir(c.id) / "refs"
    refs.mkdir(parents=True, exist_ok=True)
    ref = Reference(title=title or src.stem)
    dest = refs / f"{ref.id}{src.suffix.lower()}"
    shutil.move(str(src), dest)
    ref.file = dest.relative_to(ROOT).as_posix()
    ref.kind = _kind(dest)
    ref.status = "ready"
    c.references.append(ref)
    save(c)
    return ref


def _download(c: Campaign, ref: Reference, log) -> None:
    refs = _dir(c.id) / "refs"
    refs.mkdir(parents=True, exist_ok=True)
    clean = ref.url.split("?")[0].lower()
    if any(clean.endswith(e) for e in (*VIDEO_EXTS, *AUDIO_EXTS, *IMAGE_EXTS)):  # a direct file link
        dest = refs / f"{ref.id}{Path(clean).suffix}"
        with requests.get(ref.url, stream=True, timeout=60) as r:
            r.raise_for_status()
            with open(dest, "wb") as f:
                for chunk in r.iter_content(1 << 20):
                    f.write(chunk)
    else:
        if re.search(r"drive\.google\.com/drive/(u/\d+/)?folders|dropbox\.com/(sh|scl/fo)/|notion\.(so|site)", ref.url):
            ref.status, ref.kind = "manual", "link"
            ref.note = "This is a folder or page, not a single video. Download the files you need and add them here."
            return
        try:
            import yt_dlp
        except ImportError:
            ref.status = "manual"
            ref.note = "Downloading links needs yt-dlp (pip install yt-dlp). Or download the file and add it here."
            return
        opts = {"outtmpl": str(refs / f"{ref.id}.%(ext)s"), "noplaylist": True, "quiet": True, "no_warnings": True,
                "format": "bv*[height<=1080]+ba/b[height<=1080]/b", "merge_output_format": "mp4",
                "restrictfilenames": True}
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(ref.url, download=True)
                if info and not ref.title:
                    ref.title = info.get("title", "")
        except Exception as e:
            ref.status = "manual"
            ref.note = f"Couldn't download it ({str(e).strip().splitlines()[-1][:160]}). Download it yourself and add the file here."
            return
        found = sorted(refs.glob(f"{ref.id}.*"), key=lambda p: p.stat().st_size, reverse=True)
        found = [p for p in found if p.suffix.lower() not in (".part", ".ytdl", ".json")]
        if not found:
            ref.status, ref.note = "error", "The download finished without a file."
            return
        dest = found[0]
    ref.file = dest.relative_to(ROOT).as_posix()
    ref.kind = _kind(dest)
    ref.status = "ready"
    ref.note = ""
    log(f"  downloaded {ref.title or ref.url}")


def _words_file(c: Campaign, ref: Reference) -> Path:
    return _dir(c.id) / "refs" / f"{ref.id}.words.json"


def load_words(c: Campaign, ref: Reference) -> list[Word]:
    try:
        return [Word(**w) for w in json.loads(_words_file(c, ref).read_text(encoding="utf-8"))]
    except (OSError, ValueError):
        return []


def _transcribe(c: Campaign, ref: Reference, log) -> None:
    from .align import transcribe_words
    from .render import duration, run

    src = ref_path(c, ref)
    ref.duration = round(duration(src), 2)
    wav = _dir(c.id) / "refs" / f"{ref.id}.speech.wav"
    run(["ffmpeg", "-y", "-hide_banner", "-i", str(src), "-vn", "-ac", "1", "-ar", "16000", str(wav)])
    try:
        log(f"  transcribing {ref.title or ref.id} ({ref.duration / 60:.0f} min)…")
        words = transcribe_words(wav, "km" if c.lang == "km" else None, {}, ref.duration)
    finally:
        wav.unlink(missing_ok=True)
    _words_file(c, ref).write_text(json.dumps([w.__dict__ for w in words], ensure_ascii=False), encoding="utf-8")
    ref.transcribed = True
    if not words:
        ref.note = "No speech found, so clips can't be picked from what's said."


def prepare_references(campaign_id: str, log: Callable[[str], None] = print) -> Campaign:
    """Download every reference link not fetched yet, then transcribe each video and audio file once."""
    c = load(campaign_id)
    todo = [r for r in c.references if r.status == "new" and r.url]
    for i, ref in enumerate(todo, 1):
        log(f"[1/2] Downloading {i} of {len(todo)}: {ref.title or ref.url}")
        try:
            _download(c, ref, log)
        except Exception as e:
            ref.status, ref.note = "error", str(e).strip().splitlines()[-1][:200]
        save(c)
    media = [r for r in c.references if r.status == "ready" and r.kind in ("video", "audio") and not r.transcribed]
    for i, ref in enumerate(media, 1):
        log(f"[2/2] Listening {i} of {len(media)}: {ref.title or ref.id}")
        try:
            _transcribe(c, ref, log)
        except ImportError:
            raise RuntimeError("Transcribing needs Whisper: install the AI add-on in Settings → AI features.")
        except Exception as e:
            ref.note = f"Couldn't transcribe: {str(e).strip().splitlines()[-1][:160]}"
        save(c)
    return c


# ---------- 3. Plan clips ----------

PLAN_SCHEMA = {
    "type": "object",
    "properties": {"clips": {"type": "array", "items": {
        "type": "object",
        "properties": {
            "ref_id": {"type": "string"}, "start": {"type": "number"}, "end": {"type": "number"},
            "hook": {"type": "string"}, "title": {"type": "string"}, "description": {"type": "string"},
            "hashtags": {"type": "array", "items": {"type": "string"}}, "why": {"type": "string"},
        },
        "required": ["ref_id", "start", "end", "hook", "title", "description", "hashtags", "why"],
        "additionalProperties": False}}},
    "required": ["clips"],
    "additionalProperties": False,
}

PLAN_SYSTEM = """You are a top short-form clipper working on a paid Content Rewards campaign: you get paid per view,
but only for clips that follow the campaign's brief and requirements exactly. From the timestamped transcripts of
the reference videos, pick the moments that will hold attention on TikTok, Reels and Shorts.

Picking moments:
- Each clip stands on its own: a clear hook in the first 2 seconds (a bold claim, a question, a surprising line,
  conflict or emotion), one idea, and a satisfying end. Never start or stop mid-sentence.
- Use the transcript's timestamps: start at the first word of the hook line, end just after the last word of
  the payoff. Stay within the allowed length.
- Spread clips across different moments and topics; no two clips may overlap much.
- Prefer moments that serve the brief (the product, the message the brand wants seen).

For each clip write:
- hook: on-screen text for the first seconds, 3-8 words, that makes people stay (no hashtags, no emoji).
- title: 30-60 characters, specific and honest.
- description: 1-3 short lines that tease the payoff, then a light call to action. Work in every phrase the
  campaign requires the caption to include. Don't put hashtags or @mentions in it (they're added for you).
- hashtags: 2-4 topic hashtags (no #) on top of the required ones; never fyp, viral or foryou.
- why: one line on why this moment works for the brief.
Follow every rule and avoid everything the campaign forbids."""


def _transcript(c: Campaign) -> tuple[str, dict[str, Reference]]:
    """Timestamped lines per reference ("[12.4] words…"), broken at pauses and sentence ends."""
    parts, usable = [], {}
    for ref in c.references:
        words = load_words(c, ref) if ref.kind == "video" and ref.transcribed else []
        if not words:
            continue
        usable[ref.id] = ref
        lines, cur, start = [], [], words[0].start
        for i, w in enumerate(words):
            if not cur:
                start = w.start
            cur.append(w.text)
            gap = words[i + 1].start - w.end if i + 1 < len(words) else 9
            if gap > 0.7 or (w.text.endswith((".", "?", "!")) and len(cur) >= 6) or len(cur) >= 24:
                lines.append(f"[{start:.1f}] {' '.join(cur)}")
                cur = []
        parts.append(f'<reference id="{ref.id}" title="{ref.title}" seconds="{ref.duration:.0f}">\n'
                     + "\n".join(lines) + "\n</reference>")
    return "\n\n".join(parts)[:MAX_TRANSCRIPT_CHARS], usable


def plan_clips(c: Campaign, count: int, idea: str = "") -> list[ClipPlan]:
    text, usable = _transcript(c)
    if not usable:
        raise RuntimeError("No transcribed reference videos yet. Add the campaign's videos and press Prepare.")
    r = c.requirements
    rules = {"brief": c.brief, "kind": c.kind, "platforms": c.platforms, "length_seconds": [r.min_seconds, r.max_seconds],
             "rules": r.rules, "avoid": r.avoid, "caption_must_include": r.must_include}
    prompt = (f"<campaign>\n{json.dumps(rules, ensure_ascii=False, indent=2)}\n</campaign>\n\n{text}\n\n")
    if idea.strip():
        prompt += f"<direction>\n{idea.strip()[:1000]}\n</direction>\nFollow this direction.\n\n"
    if c.lang == "km":
        prompt += "Write hook, title and description in natural Khmer.\n"
    prompt += f"Pick the {count} best clips, strongest first."
    plans = []
    for p in _claude(PLAN_SYSTEM, prompt, PLAN_SCHEMA, max_tokens=12000)["clips"]:
        ref = usable.get(p["ref_id"])
        if not ref:
            continue
        plan = ClipPlan(**p)
        plan.start, plan.end = _fit(load_words(c, ref), plan.start, plan.end, r.min_seconds, r.max_seconds, ref.duration)
        if plan.end - plan.start >= 3:
            plans.append(plan)
    return plans[:count]


def _fit(words: list[Word], start: float, end: float, lo: float, hi: float, total: float) -> tuple[float, float]:
    """Snap a moment to word boundaries (a breath before the first word, after the last) and the allowed length."""
    inside = [w for w in words if w.end > start and w.start < end]
    if inside:
        start, end = inside[0].start, inside[-1].end
    start = max(0.0, start - 0.15)
    end = min(total or end + 0.4, end + 0.4)
    if end - start > hi:  # too long: end on the last word that fits
        fits = [w for w in inside if w.end + 0.4 - start <= hi]
        end = (fits[-1].end + 0.4) if fits else start + hi
    if end - start < lo:  # too short: let it run on to the end of the next words
        later = [w for w in words if w.end > end and w.end + 0.4 - start <= lo + 4]
        end = min(total or 1e9, (later[-1].end + 0.4) if later else start + lo)
    return round(start, 2), round(end, 2)


# ---------- 4. Render a clip ----------

def _post_text(c: Campaign, plan: ClipPlan) -> str:
    r = c.requirements
    desc = plan.description.strip()
    lower = desc.lower()
    for phrase in r.must_include:  # Gemini was asked to work them in; make sure
        if phrase.strip() and phrase.lower() not in lower:
            desc += f"\n{phrase.strip()}"
    if r.mentions:
        desc += "\n" + " ".join(f"@{m}" for m in r.mentions)
    tags, seen = [], set()
    disclosure = r.disclosure.strip()
    if disclosure and not disclosure.startswith("#"):
        desc = f"{disclosure}\n{desc}"
    for t in ([disclosure] if disclosure.startswith("#") else []) + r.hashtags + plan.hashtags:
        t = t.lstrip("#").replace(" ", "")
        if t and t.lower() not in seen and t.lower() not in ("fyp", "viral", "foryou", "foryoupage"):
            seen.add(t.lower())
            tags.append(f"#{t}")
    return f"{plan.title.strip()}\n\n{desc.strip()}\n\n{' '.join(tags)}\n"


def render_clip(c: Campaign, plan: ClipPlan, layout: str = "fill", log: Callable[[str], None] = print) -> Path:
    """One clip as an output video folder (video.mp4, thumbnail.jpg, post.txt, meta.json)."""
    from .captions import build_ass
    from .config import FPS, HEIGHT, WIDTH
    from .pipeline import _install_font, make_thumbnail, slugify
    from .render import finalize, run

    ref = next(r for r in c.references if r.id == plan.ref_id)
    src = ref_path(c, ref)
    lang = c.lang if c.lang in LANGS else "en"
    profile = LANGS[lang]
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    job = OUTPUT_DIR / f"{stamp}-{lang}-clip-{slugify(plan.title, 30)}"
    work = job / "work"
    work.mkdir(parents=True)
    length = plan.end - plan.start

    # vertical frame: "fill" keeps the whole picture over a blurred copy of itself; "crop" fills the frame
    if layout == "crop":
        vf = f"scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=increase,crop={WIDTH}:{HEIGHT},setsar=1,fps={FPS}"
    else:
        vf = (f"split[a][b];[a]scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=increase,crop={WIDTH}:{HEIGHT},"
              f"boxblur=24:2,eq=brightness=-0.12[bg];[b]scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=decrease[fg];"
              f"[bg][fg]overlay=(W-w)/2:(H-h)/2,setsar=1,fps={FPS}")
    run(["ffmpeg", "-y", "-hide_banner", "-ss", f"{plan.start:.2f}", "-t", f"{length:.2f}", "-i", str(src),
         "-filter_complex", f"[0:v]{vf}[v]", "-map", "[v]", "-map", "0:a?", "-c:v", "libx264", "-preset", "veryfast",
         "-crf", "18", "-c:a", "aac", "-b:a", "192k", "-ar", "44100", "cut.mp4"], cwd=work)

    # captions: the spoken words (times relative to the clip), with the hook on screen for the first seconds
    words = [Word(w.text, max(0.0, w.start - plan.start), max(0.0, w.end - plan.start))
             for w in load_words(c, ref) if w.start >= plan.start - 0.05 and w.end <= plan.end + 0.05]
    if not c.requirements.captions:
        words = []
    hook_end = min(HOOK_SEC, length)
    first = [w for w in words if w.start < hook_end]
    rest = [Word(w.text, w.start - hook_end, w.end - hook_end) for w in words if w.start >= hook_end]
    scenes = [(0.0, hook_end, first, plan.hook.strip()), (hook_end, length, rest, "")]
    (work / "captions.ass").write_text(build_ass(scenes, profile), encoding="utf-8")
    _install_font(profile, work / "fonts")
    finalize(work, "cut.mp4", "captions.ass", job / "video.mp4", None)

    (job / "meta.json").write_text(json.dumps({
        "lang": lang, "kind": "clip", "title": plan.title.strip(), "campaign": c.id, "reference": ref.id,
        "start": plan.start, "end": plan.end, "hook": plan.hook, "why": plan.why, "aspect": "9:16",
        "transcript": " ".join(w.text for w in words)[:4000],
        "created": datetime.now().isoformat(timespec="seconds"),
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    (job / "post.txt").write_text(_post_text(c, plan), encoding="utf-8")
    try:
        make_thumbnail(job, plan.hook or plan.title, min(1.0, length / 2), lang)
    except Exception as e:  # a missing cover never fails the clip
        log(f"  ! thumbnail: {e}")
    log(f"  made: {plan.title} ({length:.0f}s)")
    return job
