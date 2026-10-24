"""Footage for every scene, in this order:
a) your own file: <media_dir>/<script>/scene-XX.mp4 (or .mov / .jpg / .png ...), used as it is
b) what the scene is, as Gemini reads the script (any topic: wildlife, history, science, places...):
   - footage: everyday real-world shots, from the stock libraries (Pexels, Pixabay) and Wikimedia Commons
   - species: one particular living thing, from stock video and iNaturalist / Wikimedia photos of that species
   - archival: history, people, artworks, events, space: Internet Archive film and newsreels, NASA, Wikimedia
     Commons, The Met (all public domain or freely licensed)
   - graphic: a comparison, list, logo sting or end screen, drawn by the app (cards.py): no library has those
   - montage: quick cuts of the video's own footage from other scenes (a cold open, a recap)
   searched with words Gemini writes from the Visual column ("Slow-motion catch" under #10 GREEN HERON becomes
   "green heron catching fish"); each scene keeps a few alternatives for the storyboard to swap to
c) nothing that really shows the scene: a card with its on-screen text, flagged in the storyboard

Searches are loose (a "raven" search shows crows, rooks, any black bird; "logo animation" a glowing heart), so Gemini
looks at every pick: under PASS the next match is tried, and a pick under MIN_SHOW is never used, whatever the
libraries had. Every downloaded file keeps its source page, author and licence (credits.txt).
"""
import hashlib
import json
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import requests

from .. import commons, visuals
from . import archives, cards
from ..config import CACHE_DIR, LLM_MODEL
from ..importer import STOPWORDS
from ..render import duration, run
from ..visuals import IMAGE_EXTS, VIDEO_EXTS
from .parse import Scene, Script

SEARCH_CACHE = CACHE_DIR / "stock-search"
SEARCH_TTL = 7 * 24 * 3600  # stock searches are kept a week (Pexels allows 200 requests an hour)
PASS = 7                    # Gemini's 0-10 score for "this shows the subject"; under it the pick is flagged
MIN_SHOW = 5                # under it a pick is never used (a man on a rock for "brain comparison"): a card instead
CHECK_TRIES = 4             # matches downloaded and checked at most per search before keeping the best
LICENCES = {
    "pexels": ("Pexels License", "https://www.pexels.com/license/"),
    "pixabay": ("Pixabay Content License", "https://pixabay.com/service/license-summary/"),
}
STOCK = (*LICENCES, "commons", *archives.SEARCHES)  # sources a scene's pick can be swapped back to
KINDS = ("footage", "species", "archival", "graphic", "montage")
MONTAGE_CUT = 1.4           # seconds per shot in a montage

PLAN_SCHEMA = {
    "type": "object",
    "properties": {"scenes": {"type": "array", "items": {
        "type": "object",
        "properties": {
            "scene": {"type": "integer"},
            "query": {"type": "string"},
            "alt_query": {"type": "string"},
            "subject": {"type": "string"},
            "kind": {"type": "string", "enum": list(KINDS)},
            "card": {"type": "object", "properties": {
                "style": {"type": "string", "enum": list(cards.STYLES)},
                "title": {"type": "string"},
                "items": {"type": "array", "items": {"type": "string"}},
            }, "required": ["style", "title", "items"], "additionalProperties": False},
        },
        "required": ["scene", "query", "alt_query", "subject", "kind", "card"],
        "additionalProperties": False,
    }}},
    "required": ["scenes"],
    "additionalProperties": False,
}


# ---------- search words ----------

def _subjects(script: Script) -> list[str]:
    """The animal/thing each scene is about: the last "#N NAME" title card at or before it ("" before the first)."""
    out, current = [], ""
    for s in script.scenes:
        current = s.name.title() if s.rank else current
        out.append(current)
    return out


def local_query(scene: Scene, subject: str) -> str:
    """Search words without Gemini: the scene's subject plus the Visual column's first content words."""
    words = [w for w in re.findall(r"[A-Za-z']+", scene.visual.lower())
             if w not in STOPWORDS and len(w) > 2 and w not in ("montage", "graphic", "close", "shot", "footage")]
    head = subject.lower()
    picked = [w for w in dict.fromkeys(words) if w not in head.split()][:3]
    return " ".join(([head] if head else []) + picked) or scene.visual[:40]


GRAPHIC_WORDS = re.compile(r"\b(graphics?|logo|sting|end ?screen|split ?screen|diagram|chart|infographic|comparison|"
                           r"versus|subscribe)\b", re.I)
MONTAGE_WORDS = re.compile(r"\b(montage|recap)\b", re.I)


def local_kind(scene: Scene) -> str:
    """The scene's kind from the Visual column's words alone (no Gemini)."""
    if MONTAGE_WORDS.search(scene.visual):
        return "montage"
    return "graphic" if GRAPHIC_WORDS.search(scene.visual) else "footage"


def local_card(scene: Scene) -> dict:
    """A headline card from the scene's on-screen text, else its Visual line (an end screen gets the end layout)."""
    title = scene.text or re.sub(r"^(graphics?|split screen|logo sting)\s*:?\s*", "", scene.visual, flags=re.I)
    style = "end" if re.search(r"end ?screen", scene.visual, re.I) else "headline"
    return {"style": style, "title": title[:80], "items": []}


def plan_queries(script: Script, log=print) -> list[dict]:
    """[{scene, query, alt_query, subject, kind, card}] per scene: Gemini's plan, or a local one without it."""
    subjects = _subjects(script)
    fallback = [{"scene": s.n, "query": local_query(s, subj), "alt_query": subj.lower() or local_query(s, ""),
                 "subject": subj.lower(), "kind": local_kind(s), "card": local_card(s)}
                for s, subj in zip(script.scenes, subjects)]
    listing = "\n".join(f"{s.n}. [section: {subj or 'intro'}] VISUAL: {s.visual} | TEXT: {s.text} | VO: {s.voiceover}"
                        for s, subj in zip(script.scenes, subjects))
    task = (
        f"Video: \"{script.title}\" (any topic: nature, history, science, places...). For each scene below, decide "
        "what kind of picture it needs and how to find it.\n"
        "- kind:\n"
        "  footage: everyday real-world shots a stock library has (a city square, a forest, waves, a person "
        "cooking).\n"
        "  species: one particular animal or plant species that must be right.\n"
        "  archival: the past, or a specific real person, artwork, artefact, historic event or building, war, "
        "expedition, space mission: searched in public-domain archives (old film and newsreels, museum collections, "
        "NASA, Wikimedia Commons).\n"
        "  graphic: anything no camera filmed: a comparison or split screen, a diagram, a chart, a list of "
        "items, numbers, a logo sting, a title, an end screen.\n"
        "  montage: quick cuts of footage from the video's other scenes (a cold open teasing what's coming, a "
        "recap of everything).\n"
        "- query: 2-5 search words. footage/species: the exact subject by its common name (never just \"bird\" or "
        "\"soldier\") and what it does or where it is, as stock sites tag clips (\"green heron fishing\"). "
        "archival: the names, place and period archives catalogue by (\"Apollo 11 launch\", \"Battle of the Somme "
        "trenches\", \"Napoleon portrait\", \"Monet water lilies\"). Take the subject from the scene's section when "
        "the Visual doesn't name it. graphic/montage: the scene's main subject, in case its card needs pictures.\n"
        "- alt_query: a broader 1-3 word fallback that still shows the right subject.\n"
        "- subject: when the scene must show one particular species, person, artwork, place or thing a viewer could "
        "tell apart from look-alikes, \"<name>: <the visible features that tell it apart>\" (e.g. \"common raven: "
        "very large all-black corvid, shaggy throat feathers, thick curved bill, wedge-shaped tail\", \"Napoleon "
        "Bonaparte: short dark hair, bicorne hat, French uniform of the early 1800s\"); \"\" when any matching "
        "shot will do, and for graphic and montage scenes.\n"
        "- card: for graphic scenes, what the app draws. style: headline (one big line; a logo sting is the channel "
        "or video title), versus (two things compared: items = the two names, each searched for a picture), list "
        "(items = up to 6 short entries) or end (the end screen: title = a short sign-off). title: the scene's "
        "On-screen Text when it has one, else a heading of at most 6 words. Other kinds: style headline, title = "
        "the On-screen Text or a 2-5 word heading for the scene (shown if no footage is good enough), items [].\n\n"
        + listing)
    try:
        from ..script import make_client

        response = make_client().beta.messages.create(
            model=LLM_MODEL,
            max_tokens=16000,
            output_config={"effort": "low", "format": {"type": "json_schema", "schema": PLAN_SCHEMA}},
            messages=[{"role": "user", "content": task}],
        )
        if response.stop_reason == "refusal":
            raise RuntimeError("Gemini declined")
        got = {p["scene"]: p for p in json.loads(next(b.text for b in response.content if b.type == "text"))["scenes"]}
        return [{**f, **got[f["scene"]]} if f["scene"] in got else f for f in fallback]
    except Exception as e:  # no key or offline: words from the Visual column
        log(f"      ! couldn't plan search words with Gemini ({type(e).__name__}: {str(e)[:120]}); using the Visual column")
        return fallback


# ---------- stock search ----------

def _cached(key: str, fetch) -> list[dict]:
    path = SEARCH_CACHE / f"{hashlib.sha1(key.encode()).hexdigest()[:20]}.json"
    if path.exists() and time.time() - path.stat().st_mtime < SEARCH_TTL:
        return json.loads(path.read_text(encoding="utf-8"))
    items = fetch()
    SEARCH_CACHE.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(items), encoding="utf-8")
    return items


def usable_width(item: dict, portrait: bool = False) -> float:
    """How many of a match's pixels fill the frame's width: its width, or for a 9:16 frame the width left once a wider
    picture is cropped to 9:16 (a 1920x1080 clip keeps 608 px; 4K keeps 1215)."""
    w, h = item.get("width") or 0, item.get("height") or 0
    return min(w, h * 9 / 16) if portrait and h else w


def _pexels_file(files: list[dict], width: int, portrait: bool = False) -> dict | None:
    """The smallest landscape mp4 at least `width` wide, else the widest (a 4K file only slows the render down).
    portrait: any orientation, the smallest that still fills a `width`-wide 9:16 frame."""
    wide = [f for f in files if f.get("file_type") == "video/mp4"
            and (portrait or (f.get("width") or 0) > (f.get("height") or 0))]
    good = [f for f in wide if usable_width(f, portrait) >= width]
    return (min(good, key=lambda f: f["width"]) if good
            else max(wide, key=lambda f: usable_width(f, portrait), default=None))


def _pixabay_file(videos: dict, width: int, portrait: bool = False) -> dict | None:
    files = [f for f in (videos.get(s) or {} for s in ("tiny", "small", "medium", "large")) if f.get("url")]
    good = [f for f in files if usable_width(f, portrait) >= width]
    return good[0] if good else (files[-1] if files else None)


def _pexels(query: str, kind: str, width: int, portrait: bool = False) -> list[dict]:
    lic, lic_url = LICENCES["pexels"]
    facing = "portrait" if portrait else "landscape"
    if kind == "video":
        data = visuals._pexels(visuals.PEXELS_VIDEO_SEARCH, query=query, orientation=facing, size="medium",
                               per_page=15 if portrait else 8)
        out = []
        for v in data.get("videos", []):
            f = _pexels_file(v.get("video_files", []), width, portrait)
            if f:
                mp4 = [x for x in v.get("video_files", []) if x.get("file_type") == "video/mp4" and x.get("width")]
                small = min(mp4, key=lambda x: x["width"], default=f)
                out.append({"source": "pexels", "id": v["id"], "kind": "video", "thumb": v.get("image", ""),
                            "page": v.get("url", ""), "author": (v.get("user") or {}).get("name", ""),
                            "duration": v.get("duration", 0), "width": f.get("width") or 0,
                            "height": f.get("height") or 0, "url": f["link"], "licence": lic, "licence_url": lic_url,
                            # Pexels has no tags: its page name says what's in the clip ("cat-drinking-water")
                            "tags": " ".join(re.findall(r"[a-z]+", (v.get("url") or "").lower().split("/video/")[-1])),
                            "preview": small["link"]})
        return out
    data = visuals._pexels(visuals.PEXELS_PHOTO_SEARCH, query=query, orientation=facing, per_page=6)
    return [{"source": "pexels", "id": p["id"], "kind": "photo", "thumb": p["src"]["medium"], "page": p.get("url", ""),
             "author": p.get("photographer", ""), "width": p.get("width") or 0, "height": p.get("height") or 0,
             # the original, scaled on Pexels' side to what a 1080p frame with a slow zoom needs
             "url": f"{p['src']['original']}?auto=compress&cs=tinysrgb&w={max(width, 1920) + 480}",
             "licence": lic, "licence_url": lic_url} for p in data.get("photos", [])]


def _pixabay(query: str, kind: str, width: int, portrait: bool = False) -> list[dict]:
    """portrait: for a 9:16 frame: clips of any orientation (vertical ones fill it whole; a landscape one is cropped,
    so it needs 4K to stay sharp), photos of any orientation."""
    lic, lic_url = LICENCES["pixabay"]
    if kind == "video":
        # the most-liked clips first (Pixabay's own ranking lists a lot of amateur footage), sharp enough for the frame
        data = visuals._pixabay(visuals.PIXABAY_VIDEOS, q=query, video_type="film", order="popular",
                                min_width=round(width * 0.95), per_page=20 if portrait else 8)
        out = []
        for h in data.get("hits", []):
            f = _pixabay_file(h.get("videos", {}), width, portrait)
            if f and (portrait or (f.get("width") or 0) > (f.get("height") or 0)):
                out.append({"source": "pixabay", "id": h["id"], "kind": "video",
                            "thumb": f.get("thumbnail") or (h["videos"].get("medium") or {}).get("thumbnail", ""),
                            "page": h.get("pageURL", ""), "author": h.get("user", ""), "duration": h.get("duration", 0),
                            "width": f.get("width") or 0, "height": f.get("height") or 0, "url": f["url"],
                            "licence": lic, "licence_url": lic_url, "tags": h.get("tags", ""),
                            # a small copy to judge it by before downloading the full file
                            "preview": (h["videos"].get("small") or h["videos"].get("medium") or f).get("url", "")})
        return out
    data = visuals._pixabay(visuals.PIXABAY_PHOTOS, q=query, image_type="photo",
                            orientation="all" if portrait else "horizontal", order="popular", min_width=width,
                            per_page=6)
    return [{"source": "pixabay", "id": p["id"], "kind": "photo", "thumb": p.get("webformatURL", ""),
             "page": p.get("pageURL", ""), "author": p.get("user", ""), "width": p.get("imageWidth") or 0,
             "height": p.get("imageHeight") or 0, "url": p.get("largeImageURL", ""), "licence": lic,
             "licence_url": lic_url, "tags": p.get("tags", "")} for p in data.get("hits", [])]


def _commons(query: str) -> list[dict]:
    return [{"source": "commons", "id": hashlib.sha1(c["url"].encode()).hexdigest()[:16], "kind": "photo",
             "thumb": c["url"], "page": c["page"], "author": c["author"], "url": c["url"], "title": c["title"],
             "licence": c["licence"], "licence_url": c["page"], "width": commons.WIDTH, "height": 0}
            for c in commons.search(query, 6)]


def search(query: str, sources: list[str], width: int, length: float, log=print, portrait: bool = False) -> list[dict]:
    """Matches for `query` from `sources`, best first: videos long enough for the scene and sharp enough for the
    frame, then shorter ones (they loop), then photos (a slow zoom), Wikimedia photos last unless nothing else.
    portrait: for a 9:16 frame (Shorts)."""
    tall = "|portrait2" if portrait else ""  # 2: results carry tags and a preview
    found = []
    for source in sources:
        try:
            if source == "pexels" and visuals.pexels_key():
                for kind in ("video", "photo"):
                    found += _cached(f"pexels|{kind}|{width}{tall}|{query}",
                                     lambda: _pexels(query, kind, width, portrait))
            elif source == "pixabay" and visuals.pixabay_key():
                for kind in ("video", "photo"):
                    found += _cached(f"pixabay-popular|{kind}|{width}{tall}|{query}",
                                     lambda: _pixabay(query, kind, width, portrait))
            elif source == "commons":
                found += _cached(f"commons|{query}", lambda: _commons(query))
            elif source in archives.SEARCHES:
                for kind in ("video", "photo"):
                    found += _cached(f"{source}|{kind}|{query}", lambda: archives.SEARCHES[source](query, kind))
        except (requests.RequestException, ValueError, KeyError) as e:
            log(f"      ! {source} search for {query!r} failed ({type(e).__name__}: {str(e)[:100]})")

    return sorted(found, key=lambda item: rank(item, sources, width, length, portrait))


def rank(item: dict, sources: list[str], width: int, length: float, portrait: bool = False) -> tuple:
    """Videos long enough for the scene first, then shorter ones (they loop), then photos (a slow zoom); within
    each, sharp enough for the frame first, then by the sources' order."""
    video = item["kind"] == "video"
    # the archives' sizes aren't known yet
    soft = usable_width(item, portrait) < width * 0.95 and item["source"] in LICENCES
    long_enough = item.get("duration", 0) >= length or "duration" not in item  # Archive clips are cut to length
    where = sources.index(item["source"]) if item["source"] in sources else len(sources)
    return (0 if video and long_enough else 1 if video else 2, soft, where)


def spread(matches: list[dict]) -> list[dict]:
    """Matches reordered so each source's best comes first, then each one's second best...: the few that get
    checked aren't all from one loose library (three Pixabay galahs for a Goffin's cockatoo)."""
    by_source: dict[str, list[dict]] = {}
    for m in matches:
        by_source.setdefault(m["source"], []).append(m)
    out, k = [], 0
    while len(out) < len(matches):
        out += [lst[k] for lst in by_source.values() if k < len(lst)]
        k += 1
    return out


def sources_for(kind: str, cfg: dict) -> list[str]:
    """The libraries searched for a scene of `kind`, in order (longform.json: footage.sources and footage.by_kind)."""
    fc = cfg["footage"]
    return list((fc.get("by_kind") or {}).get(kind) or fc["sources"])


def key(item: dict) -> str:
    return f"{item['source']}-{item['kind']}-{item.get('id', '')}"


def fetch(item: dict) -> Path:
    """The file of a stock match in the cache (downloaded once)."""
    if item["source"] == "commons":  # one at a time, spaced out, a 429 waited out: commons.download
        return commons.download({k: item[k] for k in ("title", "url", "page", "licence", "author")})
    if item["source"] in archives.SEARCHES:
        return archives.fetch(item)
    ext = ".mp4" if item["kind"] == "video" else ".jpg"
    return visuals._download(item["url"], visuals.STOCK_CACHE / f"{item['source']}-{item['kind']}-{item['id']}{ext}")


# ---------- per scene ----------

def own_media(media: Path, n: int) -> Path | None:
    """Your clip or photo for scene `n`: <media>/scene-XX.<video or image> (scene-7 works too)."""
    for stem in (f"scene-{n:02d}", f"scene-{n}"):
        for ext in (*VIDEO_EXTS, *IMAGE_EXTS):
            if (path := media / f"{stem}{ext}").is_file():
                return path
    return None


def target(entry: dict, scene: Scene) -> str:
    """What a scene's footage is checked against: its named species, else what the Visual column describes."""
    return entry["subject"] or f"{entry['query']}: {scene.visual}"


def check(path: Path, subject: str, visual: str) -> tuple[int, str]:
    """Gemini's 0-10 verdict on whether `path` shows `subject` (cached next to the file)."""
    from ..pipeline import _verdict

    return _verdict(path, subject, f"stock footage for: {visual}")


def _size(cfg: dict) -> tuple[int, int]:
    return int(cfg["render"]["width"]), int(cfg["render"]["height"])


def plan_card(entry: dict, scene: Scene) -> dict:
    """The card a scene shows: its planned one (older footage.json files have none: made from the scene's text). A
    "#N NAME" scene's card stays empty: the title card is drawn over it anyway."""
    if scene.rank:
        return {"style": "headline", "title": "", "items": []}
    return entry.get("card") or local_card(scene)


def make_card(entry: dict, scene: Scene, out: Path, cfg: dict, lang: str, under: Path | None = None,
              pictures: list[Path | None] = ()) -> dict:
    """Draw the scene's card into out/ and return it as the scene's pick."""
    card = plan_card(entry, scene)
    path = cards.draw(card, out / f"card-{scene.n:02d}.png", _size(cfg), lang, under, pictures)
    return {"source": "card", "kind": "photo", "file": str(path), "page": "", "author": "", "licence": "",
            "licence_url": "", "style": card["style"]}


def _thumb(path: Path, out: Path, at: float | None = None) -> None:
    """A small jpg of `path` (a video's frame from 40% in) for the storyboard."""
    seek = at if at is not None else (duration(path) * 0.4 if path.suffix.lower() not in IMAGE_EXTS else 0)
    run(["ffmpeg", "-y", "-v", "error", *(["-ss", f"{seek:.2f}"] if seek else []), "-i", str(path),
         "-frames:v", "1", "-vf", "scale=480:-2", "-q:v", "4", str(out)])


def flags(entry: dict, length: float, size: tuple[int, int]) -> list[str]:
    """What to look at in a scene's pick: no footage good enough, the wrong subject, a clip that loops, a picture too
    small for the frame."""
    c, out = entry["chosen"], []
    what = (entry["subject"] or entry["query"]).split(":")[0].strip()
    if c["source"] == "placeholder":
        return [f"no footage found for \"{entry['query']}\": a placeholder card is shown"]
    if c["source"] == "card":
        if entry.get("kind") == "graphic":
            return []
        return [f"nothing found really shows {what}: a card with the scene's text is shown; pick an alternative, "
                "search again or add your own file"]
    if c["source"] == "montage":
        return []
    if c.get("check") is not None and c["check"] < PASS:
        out.append(f"may not show {what} ({c['check']}/10): {c.get('problem', '')}")
    if c["kind"] == "video" and c.get("duration") and c["duration"] < length:
        out.append(f"the clip is {c['duration']} s for a {length:.1f} s scene: it loops")
    portrait = size[1] > size[0]
    if c.get("width") and usable_width(c, portrait) < size[0] * 0.95 and c["source"] in LICENCES:
        out.append(f"only {usable_width(c, portrait):.0f} px wide{' once cropped to 9:16' if portrait else ''}: "
                   f"soft at {size[0]}x{size[1]}")
    return out


def choose(script: Script, plans: list[dict], slots: list, media: Path, out: Path, cfg: dict, log=print) -> list[dict]:
    """One entry per scene: {scene, query, subject, kind, card, chosen, alternatives, flags}; chosen = {source, kind,
    file, page, author, licence, ...}. Thumbnails and cards go in out/ (the job's storyboard/ folder)."""
    fc = cfg["footage"]
    width, size = _size(cfg)[0], _size(cfg)
    portrait = size[1] > size[0]  # a Short: footage of any orientation, sharp once cropped to 9:16
    out.mkdir(parents=True, exist_ok=True)
    used: set[str] = set()
    lock = threading.Lock()
    do_check = bool(fc["check_subject"])
    keep = max(int(fc["alternatives"]), 1)

    def claim(item: dict) -> bool:
        with lock:
            if key(item) in used:
                return False
            used.add(key(item))
            return True

    def release(item: dict) -> None:
        with lock:
            used.discard(key(item))

    def best_of(tries: list[dict], scene: Scene, entry: dict, best=None):
        """Download and check `tries` in order until one passes; returns the best (score, item, path, problem)."""
        for item in tries:
            if not claim(item):
                continue
            try:
                path = fetch(item)
            except (requests.RequestException, OSError, ValueError, RuntimeError) as e:
                log(f"      ! scene {scene.n}: couldn't download {key(item)} ({type(e).__name__}: "
                    f"{str(e).strip().splitlines()[-1][:120] if str(e).strip() else ''})")
                release(item)
                continue
            score, problem = None, ""
            if do_check:
                try:
                    score, problem = check(path, target(entry, scene), scene.visual)
                    item["check"], item["problem"] = score, problem  # shown with the alternative in the storyboard
                except Exception as e:
                    log(f"      ! scene {scene.n}: couldn't check the pick ({type(e).__name__}: {str(e)[:100]})")
            if best is None or (score or 0) > (best[0] or 0):
                if best:
                    release(best[1])
                best = (score, item, path, problem)
            else:
                release(item)
            if score is None or score >= PASS:
                break
        return best

    def candidates(query: str, entry: dict, sources: list[str], length: float) -> list[dict]:
        """Matches for `query`, plus (when the scene names one particular subject) searches for just its name in the
        precise libraries (iNaturalist, Wikimedia, archives), spread across sources, unused ones only."""
        found = search(query, sources, width, length, log, portrait)
        name = entry["subject"].split(":")[0].strip()
        precise = [s for s in sources if s not in LICENCES]
        if name and precise and name.lower() != query.lower():
            found += search(name, precise, width, length, log, portrait)
        with lock:
            fresh = list({key(m): m for m in found if key(m) not in used}.values())
        return spread(sorted(fresh, key=lambda m: rank(m, sources, width, length, portrait)))

    def pictures_for(card: dict, kind_sources: list[str]) -> list[Path | None]:
        """A checked photo for each side of a versus card."""
        if card.get("style") != "versus":
            return []
        pics = []
        for label in card.get("items", [])[:2]:
            photos = [m for m in search(label, kind_sources, width, 1, log, portrait) if m["kind"] == "photo"]
            got = None
            for item in photos[:2]:
                try:
                    path = fetch(item)
                    if do_check and check(path, label, f"a picture of {label}")[0] < MIN_SHOW:
                        continue
                    got = path
                    break
                except Exception as e:
                    log(f"      ! card picture for {label!r} failed ({type(e).__name__})")
            pics.append(got)
        return pics

    def one(i: int) -> dict:
        scene, plan, slot = script.scenes[i], plans[i], slots[i]
        kind = plan.get("kind") if plan.get("kind") in KINDS else local_kind(scene)
        entry = {"scene": scene.n, "query": plan["query"], "alt_query": plan["alt_query"], "subject": plan["subject"],
                 "kind": kind, "card": plan.get("card") or local_card(scene), "length": slot.length,
                 "chosen": None, "alternatives": [], "flags": []}
        own = own_media(media, scene.n)
        if own:
            entry["chosen"] = {"source": "own", "kind": "photo" if own.suffix.lower() in IMAGE_EXTS else "video",
                               "file": str(own), "page": "", "author": "you", "licence": "your own media",
                               "licence_url": ""}
            _thumb(own, out / f"scene-{scene.n:02d}.jpg")
            return entry
        if kind == "montage":
            return entry  # made from the other scenes' picks once they're all chosen
        sources = sources_for("footage" if kind == "graphic" else kind, cfg)
        if kind == "graphic":
            entry["chosen"] = make_card(entry, scene, out, cfg, script.lang,
                                        pictures=pictures_for(entry["card"], sources_for("archival", cfg)
                                                              if entry["card"].get("style") == "versus" else sources))
            entry["alternatives"] = search(plan["query"], sources, width, slot.length, log, portrait)[:keep]
            _thumb(Path(entry["chosen"]["file"]), out / f"scene-{scene.n:02d}.jpg")
            return entry

        tried = candidates(plan["query"], entry, sources, slot.length)
        best = best_of(tried[:CHECK_TRIES if do_check else 1], scene, entry)
        if do_check and (best is None or (best[0] or 0) < PASS) and plan["alt_query"]:
            more = candidates(plan["alt_query"], entry, sources, slot.length)
            tried += more
            best = best_of(more[:CHECK_TRIES], scene, entry, best)
        if best is not None and do_check and best[0] is not None and best[0] < MIN_SHOW:
            release(best[1])  # wrong footage is worse than none
            best = None
        if best is None:
            entry["chosen"] = make_card(entry, scene, out, cfg, script.lang)
        else:
            score, item, path, problem = best
            entry["chosen"] = {**item, "file": str(path), "check": score, "problem": problem}
        entry["flags"] = flags(entry, slot.length, size)
        pool = {key(a): a for a in tried}  # the checked ones first, with their scores
        entry["alternatives"] = [a for k, a in pool.items() if k != key(entry["chosen"])
                                 and not (a.get("check") is not None and a["check"] < MIN_SHOW)][:keep]
        _thumb(Path(entry["chosen"]["file"]), out / f"scene-{scene.n:02d}.jpg")
        return entry

    with ThreadPoolExecutor(4) as pool:
        entries = list(pool.map(one, range(len(script.scenes))))
    for entry, scene in zip(entries, script.scenes):
        if entry["chosen"] is None:  # a montage
            montage(entry, entries, scene, out, cfg, script.lang)
    for e in entries:
        c = e["chosen"]
        log(f"      scene {e['scene']:02d} [{e['kind']}]: {e['query']!r} -> {c['source']} {c['kind']}"
            + (f" ({c['check']}/10)" if c.get("check") is not None else "")
            + (f"  ! {'; '.join(e['flags'])}" if e["flags"] else ""))
    return entries


def montage(entry: dict, entries: list[dict], scene: Scene, out: Path, cfg: dict, lang: str) -> dict:
    """Quick cuts of the good footage picked for the other scenes, spread across the whole video (a cold open
    teases what's coming, a recap goes over all of it); a card when there is none yet."""
    from .video import aspect

    good = [e["chosen"]["file"] for e in entries
            if e is not entry and e["chosen"] and e["chosen"]["source"] not in ("card", "placeholder", "montage")
            and (e["chosen"].get("check") is None or e["chosen"]["check"] >= PASS)
            and aspect(Path(e["chosen"]["file"])) >= 1.3]  # a quick cut crops to the frame: no portraits
    count = min(max(round(entry["length"] / MONTAGE_CUT), 3), 8, len(good))
    if count < 2:
        entry["chosen"] = make_card(entry, scene, out, cfg, lang)
    else:
        step = len(good) / count
        parts = [good[int(k * step)] for k in range(count)]
        entry["chosen"] = {"source": "montage", "kind": "video", "file": parts[0], "parts": parts, "page": "",
                           "author": "", "licence": "", "licence_url": ""}
    entry["flags"] = flags(entry, entry["length"], _size(cfg))
    _thumb(Path(entry["chosen"]["file"]), out / f"scene-{scene.n:02d}.jpg")
    return entry


# ---------- storyboard edits ----------

def use(entry: dict, item: dict, scene: Scene, length: float, cfg: dict, out: Path, log=print) -> dict:
    """Swap a scene's footage for `item` (one of its alternatives): download, check, new thumbnail. The footage it
    had goes back into the alternatives."""
    path = fetch(item)
    score, problem = None, ""
    if cfg["footage"]["check_subject"] and item.get("check") is None:
        try:
            score, problem = check(path, target(entry, scene), scene.visual)
        except Exception as e:
            log(f"      ! scene {scene.n}: couldn't check the pick ({type(e).__name__})")
    elif item.get("check") is not None:
        score, problem = item["check"], item.get("problem", "")
    old = entry["chosen"]
    entry["chosen"] = {**item, "file": str(path), "check": score, "problem": problem}
    if entry.get("kind") in ("graphic", "montage"):
        entry["kind"] = "footage"  # real footage now: checked and flagged like any other
    rest = [a for a in entry["alternatives"] if key(a) != key(item)]
    if old and old["source"] in STOCK:  # stock it had: still there to swap back to
        rest.insert(0, {k: v for k, v in old.items() if k != "file"})
    entry["alternatives"] = rest
    entry["flags"] = flags(entry, length, _size(cfg))
    _thumb(path, out / f"scene-{scene.n:02d}.jpg")
    return entry


def research(entry: dict, query: str, length: float, cfg: dict, taken: set[str], log=print) -> dict:
    """New alternatives for a scene from other search words (nothing is downloaded until one is used)."""
    query = " ".join(query.split())[:80]
    if not query:
        raise ValueError("Type some search words first.")
    kind = entry.get("kind", "footage")
    size = _size(cfg)
    found = spread(search(query, sources_for("footage" if kind in ("graphic", "montage") else kind, cfg),
                          size[0], length, log, size[1] > size[0]))
    entry["query"] = query
    entry["alternatives"] = [m for m in found if key(m) not in taken][:max(int(cfg["footage"]["alternatives"]) * 2, 4)]
    return entry


def reload_own(entries: list[dict], script: Script, media: Path, slots: list, cfg: dict, out: Path) -> int:
    """Use the files you put in the media folder since (scene-XX.*); returns how many scenes use one of yours."""
    found = 0
    for entry, scene, slot in zip(entries, script.scenes, slots):
        own = own_media(media, scene.n)
        if own:
            found += 1
            if entry["chosen"]["file"] != str(own):
                entry["chosen"] = {"source": "own", "kind": "photo" if own.suffix.lower() in IMAGE_EXTS else "video",
                                   "file": str(own), "page": "", "author": "you", "licence": "your own media",
                                   "licence_url": ""}
                entry["flags"] = []
                _thumb(own, out / f"scene-{scene.n:02d}.jpg")
        elif entry["chosen"]["source"] == "own":  # your file was taken away: back to the best alternative or a card
            entry["chosen"] = None
            if entry["alternatives"]:
                use(entry, entry["alternatives"][0], scene, slot.length, cfg, out)
            else:
                entry["chosen"] = make_card(entry, scene, out, cfg, script.lang)
                entry["flags"] = flags(entry, slot.length, _size(cfg))
                _thumb(Path(entry["chosen"]["file"]), out / f"scene-{scene.n:02d}.jpg")
    return found
