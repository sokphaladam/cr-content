"""Asset-rights checklist for a finished video or a Lyric Studio song: what was used, where it came from, under which
licence, and whether you confirmed it. Saved as rights.json in the video's / song's folder.

Pre-filled from what the app knows (stock source, a music track's saved licence and credit, the Suno plan), marked
`auto` until you confirm it. This is your own record: nothing here is verified, and it never replaces YouTube Studio's
copyright (Content ID) and ad-suitability checks.
"""
import json
import re
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from .config import ASSETS_DIR, OUTPUT_DIR, ROOT

router = APIRouter()
FILE = "rights.json"
Perm = Literal["yes", "no", "unknown"]
STOCK = {"pexels": ("Pexels", "Pexels License (free for commercial use, no attribution required)"),
         "pixabay": ("Pixabay", "Pixabay Content License (free for commercial use, no attribution required)")}


class Asset(BaseModel):
    id: str = Field(max_length=120)
    name: str = Field(max_length=200)
    type: Literal["footage", "image", "music", "sound", "voice", "font", "other"] = "other"
    source: str = Field("", max_length=300)
    license: str = Field("", max_length=300)
    attribution_required: Perm = "unknown"
    attribution_text: str = Field("", max_length=500)
    commercial: Perm = "unknown"
    derivatives: Perm = "unknown"
    restrictions: str = Field("", max_length=300)
    confirmed: bool = False
    notes: str = Field("", max_length=1000)
    auto: bool = False  # suggested by the app, not yet looked at by you


def documented(a: Asset) -> bool:
    """Locally documented: a source and a licence written down, and confirmed by you."""
    return bool(a.source.strip() and a.license.strip() and a.confirmed)


def _media_asset(rel: str, n: int) -> Asset:
    name = Path(rel).name
    kind = "image" if Path(rel).suffix.lower() in (".jpg", ".jpeg", ".png", ".webp") else "footage"
    m = re.match(r"(pexels|pixabay)-(?:photo-|video-)?(\d+)", name)  # visuals.py saves videos as pixabay-<id>.mp4
    if m:
        site, licence = STOCK[m[1]]
        return Asset(id=f"media:{rel}", name=f"Scene {n} {kind}: {site} #{m[2]}", type=kind, source=site, license=licence,
                     attribution_required="no", commercial="yes", derivatives="yes", auto=True)
    from . import commons

    if line := commons.credit(ROOT / rel):
        return Asset(id=f"media:{rel}", name=f"Scene {n} {kind}: {name}", type=kind, source=commons.site(ROOT / rel),
                     license=line, attribution_required="yes", attribution_text=line, auto=True)
    own = rel.startswith("uploads/")
    return Asset(id=f"media:{rel}", name=f"Scene {n} {kind}: {name}", type=kind,
                 source="Your upload" if own else "", auto=True,
                 notes="Your own file: add where it came from." if own else "")


def suggestions_video(folder: Path) -> list[Asset]:
    from . import music

    out: list[Asset] = []
    try:
        meta = json.loads((folder / "meta.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        meta = {}
    try:
        script = json.loads((folder / "script.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        script = {}
    seen = set()
    for n, sc in enumerate(script.get("scenes", []), 1):
        for rel in [sc.get("media"), sc.get("media2"), *(b.get("media") for b in sc.get("broll", []))]:
            if rel and rel not in seen:
                seen.add(rel)
                out.append(_media_asset(rel, n))
    if script.get("art_style"):
        out.append(Asset(id="art", name="AI scene pictures (drawn on this computer)", type="image",
                         source="Stable Diffusion XL, generated locally", auto=True,
                         notes="Check the model licence's terms for commercial use."))
    if track := meta.get("music"):
        use = music.track_use(track)
        credit = music.credit(track)
        licence_file = ASSETS_DIR / "music" / f"{Path(track).stem}.json"
        try:
            lic = json.loads(licence_file.read_text(encoding="utf-8")).get("license", "")
        except (OSError, ValueError):
            lic = ""
        out.append(Asset(id=f"music:{track}", name=f"Music: {track}", type="music", source="Jamendo" if lic else "",
                         license=lic, attribution_required="yes" if credit else "unknown", attribution_text=credit,
                         commercial={"ok": "yes", "nc": "no"}.get(use, "unknown"),
                         derivatives={"ok": "yes", "nd": "no"}.get(use, "unknown"), auto=True))
    if script.get("scenes") and any(s.get("narration") for s in script["scenes"]):
        out.append(Asset(id="voice", name="Voiceover (text to speech)", type="voice", source="Microsoft Edge TTS",
                         auto=True, notes="Check the service's terms for commercial use."))
    return out


def suggestions_song(folder: Path) -> list[Asset]:
    try:
        data = json.loads((folder / "song.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        data = {}
    plan = str(data.get("plan", "")).lower()
    paid = plan in ("pro", "premier")
    out = [Asset(id="song", name=f"Song: {data.get('title') or folder.name}", type="music", source="Suno",
                 license=f"Suno {plan.capitalize()} plan" if plan else "", commercial="yes" if paid else "unknown",
                 derivatives="yes" if paid else "unknown", auto=True,
                 restrictions="" if paid else "Only songs made on a paid Suno plan can be monetized.",
                 notes=f"Made on {data['generated_on']}." if data.get("generated_on") else "Add the date it was made.")]
    try:
        slots = json.loads((folder / "pictures.json").read_text(encoding="utf-8")).get("slots", [])  # neonmekong.pictures
    except (OSError, ValueError, AttributeError):
        slots = []
    if any(s.get("file") for s in slots):
        out.append(Asset(id="pictures", name="Section pictures", type="image", source="Generated or uploaded in Lyric Studio",
                         auto=True, notes="Note where uploaded pictures came from."))
    out.append(Asset(id="font", name="Lyric and title fonts", type="font", auto=True))
    return out


def _folder(scope: str, name: str) -> tuple[Path, list[Asset]]:
    if scope == "video":
        folder = (OUTPUT_DIR / name).resolve()
        if folder.parent != OUTPUT_DIR.resolve() or not folder.is_dir():
            raise HTTPException(404, "Video not found.")
        return folder, suggestions_video(folder)
    if scope == "song":
        from . import lyricvideo

        folder = lyricvideo._folder(name)
        return folder, suggestions_song(folder)
    raise HTTPException(400, "Unknown video type.")


def _saved(folder: Path) -> dict:
    try:
        data = json.loads((folder / FILE).read_text(encoding="utf-8"))
        return {"items": [Asset(**a) for a in data.get("items", [])], "removed": [str(x) for x in data.get("removed", [])]}
    except (OSError, ValueError, TypeError, AttributeError):
        return {"items": [], "removed": []}


def load(folder: Path, suggested: list[Asset]) -> list[Asset]:
    """Your saved records, plus the app's suggestions for assets not in them yet (and not removed by you)."""
    saved = _saved(folder)
    skip = {a.id for a in saved["items"]} | set(saved["removed"])
    return saved["items"] + [a for a in suggested if a.id not in skip]


def summary(items: list[Asset]) -> dict:
    done = sum(documented(a) for a in items)
    return {"total": len(items), "documented": done,
            "blocked": [a.name for a in items if a.commercial == "no" or a.derivatives == "no"]}


def check(scope: str, name: str, checks: list, _check) -> None:
    """The rights rows of a render report: what you documented, and what only YouTube can check."""
    folder, suggested = _folder(scope, name)
    items = load(folder, suggested)
    s = summary(items)
    if s["blocked"]:
        _check(checks, "rights.licence", "rights", "warning", "A licence may not allow this use",
               "Marked no for commercial use or adaptation: " + ", ".join(s["blocked"]), "high",
               "Replace the asset, or confirm the permission in the rights checklist.")
    if not items:
        _check(checks, "rights.documented", "rights", "not_checked", "Asset rights", "Nothing listed in the rights checklist.")
    elif s["documented"] < s["total"]:
        _check(checks, "rights.documented", "rights", "warning", f"{s['total'] - s['documented']} of {s['total']} assets not documented",
               "Add the source and licence and tick Confirmed in the rights checklist.", "medium")
    else:
        _check(checks, "rights.documented", "rights", "pass", f"All {s['total']} assets documented locally",
               "Your own record: not independently verified.")
    _check(checks, "rights.youtube", "rights", "not_checked", "Copyright (Content ID) and ad suitability",
           "Only YouTube Studio can check these: upload privately or unlisted and wait for its checks.")


@router.get("/api/rights/{scope}/{name}")
def get_rights(scope: str, name: str):
    folder, suggested = _folder(scope, name)
    items = load(folder, suggested)
    return {"items": [a.model_dump() for a in items], "summary": summary(items)}


class RightsBody(BaseModel):
    items: list[Asset] = Field(max_length=200)


@router.put("/api/rights/{scope}/{name}")
def put_rights(scope: str, name: str, body: RightsBody):
    folder, suggested = _folder(scope, name)
    if len({a.id for a in body.items}) != len(body.items):
        raise HTTPException(400, "Two assets have the same id.")
    kept = {a.id for a in body.items}
    removed = sorted(({a.id for a in suggested} | set(_saved(folder)["removed"])) - kept)  # suggestions you deleted
    (folder / FILE).write_text(json.dumps({"items": [a.model_dump() for a in body.items], "removed": removed},
                                          ensure_ascii=False, indent=2), encoding="utf-8")
    return get_rights(scope, name)
