"""Free libraries beyond stock sites, for scenes stock can't get right:
- iNaturalist: research-grade wildlife photos, the species confirmed by naturalists (only CC0 / CC BY / CC BY-SA)
- The Met: public-domain paintings, sculpture, objects and old photographs (Open Access, CC0)
- NASA: space and aviation photos and video (public domain as NASA media)
- Internet Archive: old film and newsreels from collections that are public domain as a whole (Prelinger,
  Universal Newsreels, FedFlix); uploaders elsewhere on the Archive label their own licences, so only these are used

Every item has the shape footage.py works with: {source, id, kind, thumb, page, author, width, height, url, licence,
licence_url, title}. Some urls are only known once a file is chosen (NASA's file list, an Archive film's mp4): those
items carry what fetch() needs to find it.
"""
import hashlib
import json
from pathlib import Path

import requests

from ..config import CACHE_DIR
from ..render import run

CACHE = CACHE_DIR / "archives"
HEADERS = {"User-Agent": "ShortsStudio/0.1 (desktop video app; contact via GitHub sokphaladam)"}
TIMEOUT = 30

INAT = "https://api.inaturalist.org/v1/observations"
INAT_LICENCES = {"cc0": ("CC0", "https://creativecommons.org/publicdomain/zero/1.0/"),
                 "cc-by": ("CC BY 4.0", "https://creativecommons.org/licenses/by/4.0/"),
                 "cc-by-sa": ("CC BY-SA 4.0", "https://creativecommons.org/licenses/by-sa/4.0/")}
MET_SEARCH = "https://collectionapi.metmuseum.org/public/collection/v1.1/search"  # v1 search retired 2026-10-01
MET_OBJECT = "https://collectionapi.metmuseum.org/public/collection/v1/objects/{}"
NASA = "https://images-api.nasa.gov/search"
NASA_LICENCE = ("NASA media (public domain)", "https://www.nasa.gov/nasa-brand-center/images-and-media/")
ARCHIVE_SEARCH = "https://archive.org/advancedsearch.php"
ARCHIVE_META = "https://archive.org/metadata/{}"
ARCHIVE_COLLECTIONS = ("prelinger", "universal_newsreels", "FedFlix")
ARCHIVE_LICENCE = ("Public domain (Internet Archive)", "https://archive.org/details/{}")
ARCHIVE_SPOTS = (0.3, 0.55, 0.8)  # where in a film a clip is taken from (its opening is mostly titles)


def _get(url: str, **params) -> dict:
    r = requests.get(url, params=params, headers=HEADERS, timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()


# ---------- iNaturalist ----------

def inaturalist(name: str, count: int = 6) -> list[dict]:
    """Research-grade photos of the species `name` (common or scientific), most-liked observations first."""
    data = _get(INAT, taxon_name=name, photo_license="cc0,cc-by,cc-by-sa", quality_grade="research", photos="true",
                order_by="votes", per_page=count * 2)
    out = []
    for o in data.get("results", []):
        photo = next((p for p in o.get("photos", []) if p.get("license_code") in INAT_LICENCES), None)
        dims = (photo or {}).get("original_dimensions") or {}
        if not photo or min(dims.get("width", 0), dims.get("height", 0)) < 900:
            continue
        lic, lic_url = INAT_LICENCES[photo["license_code"]]
        url = photo["url"]
        out.append({"source": "inaturalist", "id": photo["id"], "kind": "photo",
                    "thumb": url.replace("/square.", "/medium."), "url": url.replace("/square.", "/original."),
                    "page": f"https://www.inaturalist.org/observations/{o['id']}",
                    "author": (photo.get("attribution") or "").removeprefix("(c) ").split(",")[0] or "unknown",
                    "title": (o.get("taxon") or {}).get("preferred_common_name") or (o.get("taxon") or {}).get("name", ""),
                    "width": dims.get("width", 0), "height": dims.get("height", 0),
                    "licence": lic, "licence_url": lic_url})
        if len(out) == count:
            break
    return out


# ---------- The Met ----------

def met(query: str, count: int = 5) -> list[dict]:
    """Public-domain works matching `query` (each one needs its own lookup, so few are asked for)."""
    ids = _get(MET_SEARCH, q=query, hasImages="true", limit=count * 2, offset=0).get("objectIDs") or []
    out = []
    for oid in ids[:count * 2]:
        try:
            o = _get(MET_OBJECT.format(oid))
        except (requests.RequestException, ValueError):
            continue
        if not o.get("isPublicDomain") or not o.get("primaryImage"):
            continue
        out.append({"source": "met", "id": oid, "kind": "photo", "thumb": o.get("primaryImageSmall") or o["primaryImage"],
                    "url": o["primaryImage"], "page": o.get("objectURL", ""),
                    "author": o.get("artistDisplayName") or "The Metropolitan Museum of Art",
                    "title": " ".join(filter(None, [o.get("title", ""), o.get("objectDate", "")])),
                    "width": 0, "height": 0, "licence": "CC0 (Met Open Access)",
                    "licence_url": "https://www.metmuseum.org/policies/image-resources"})
        if len(out) == count:
            break
    return out


# ---------- NASA ----------

def nasa(query: str, kind: str, count: int = 6) -> list[dict]:
    """NASA photos or videos for `query`; the file itself is picked from the item's file list when it's fetched."""
    data = _get(NASA, q=query, media_type="video" if kind == "video" else "image")
    out = []
    for it in (data.get("collection") or {}).get("items", [])[:count]:
        d = (it.get("data") or [{}])[0]
        thumb = next((l["href"] for l in it.get("links", []) if l.get("render") == "image" or "href" in l), "")
        lic, lic_url = NASA_LICENCE
        out.append({"source": "nasa", "id": d.get("nasa_id", ""), "kind": kind, "thumb": thumb,
                    "manifest": it.get("href", ""), "url": "", "title": d.get("title", ""),
                    "page": f"https://images.nasa.gov/details/{d.get('nasa_id', '')}",
                    "author": d.get("photographer") or d.get("center") or "NASA", "width": 0, "height": 0,
                    "licence": lic, "licence_url": lic_url})
    return out


def _nasa_file(item: dict) -> str:
    files = _get(item["manifest"]) if item.get("manifest") else []
    if item["kind"] == "video":
        order = ("~medium.mp4", "~large.mp4", "~orig.mp4", "~small.mp4")
    else:
        order = ("~large.jpg", "~orig.jpg", "~medium.jpg", "~large.png", "~orig.png")
    for end in order:
        hit = next((f for f in files if f.endswith(end)), None)
        if hit:
            return hit.replace("http://", "https://")
    raise ValueError(f"NASA item {item['id']} has no usable file")


# ---------- Internet Archive ----------

def archive(query: str, count: int = 3) -> list[dict]:
    """Public-domain films and newsreels about `query`: a few spots in each film, each a candidate clip."""
    words = " ".join(query.replace('"', "").split())
    q = (f"(title:({words}) OR subject:({words}) OR description:({words})) AND mediatype:movies "
         f"AND collection:({' OR '.join(ARCHIVE_COLLECTIONS)})")
    docs = (_get(ARCHIVE_SEARCH, q=q, rows=count, output="json",
                 **{"fl[]": ["identifier", "title", "year"]}).get("response") or {}).get("docs", [])
    out = []
    lic, lic_url = ARCHIVE_LICENCE
    for d in docs:
        ident = d["identifier"]
        for spot in ARCHIVE_SPOTS:
            out.append({"source": "archive", "id": f"{ident}@{round(spot * 100)}", "kind": "video", "film": ident,
                        "spot": spot, "thumb": f"https://archive.org/services/img/{ident}", "url": "",
                        "page": f"https://archive.org/details/{ident}",
                        "title": " ".join(filter(None, [d.get("title", ""), str(d.get("year") or "")])),
                        "author": "Internet Archive", "width": 0, "height": 0,
                        "licence": lic, "licence_url": lic_url.format(ident)})
    return out


def _archive_clip(item: dict, seconds: float, dest: Path) -> Path:
    """`seconds` of the film from its spot, cut straight from the Archive's mp4 (only that part is downloaded)."""
    meta = _get(ARCHIVE_META.format(item["film"]))
    mp4s = [f for f in meta.get("files", []) if f.get("name", "").endswith(".mp4") and f.get("length")]
    if not mp4s:
        raise ValueError(f"{item['film']} has no mp4")
    best = max(mp4s, key=lambda f: int(f.get("width") or 0))
    length = float(best["length"])
    start = max(min(length * item["spot"], length - seconds - 1), 0)
    url = f"https://archive.org/download/{item['film']}/{best['name']}"
    tmp, raw = dest.with_suffix(".part.mp4"), dest.with_suffix(".raw.mp4")
    run(["ffmpeg", "-y", "-v", "error", "-ss", f"{start:.2f}", "-i", url, "-t", f"{seconds:.2f}", "-an",
         "-c:v", "libx264", "-preset", "veryfast", "-crf", "14", "-pix_fmt", "yuv420p", str(raw)])
    crop = black_bars(raw)
    if crop:  # an old 4:3 film stored in a 16:9 file: its black bars cut off (the render frames it properly)
        run(["ffmpeg", "-y", "-v", "error", "-i", str(raw), "-vf", f"crop={crop}", "-c:v", "libx264",
             "-preset", "veryfast", "-crf", "14", "-pix_fmt", "yuv420p", str(tmp)])
        raw.unlink(missing_ok=True)
    else:
        raw.replace(tmp)
    tmp.replace(dest)
    item["width"], item["height"] = int(best.get("width") or 0), int(best.get("height") or 0)
    return dest


def black_bars(path: Path) -> str:
    """FFmpeg's crop (w:h:x:y) that removes black bars baked into a clip, or "" when it has none worth cutting."""
    import re
    import subprocess

    proc = subprocess.run(["ffmpeg", "-v", "info", "-ss", "1", "-i", str(path), "-t", "6", "-vf",
                           "cropdetect=limit=24:round=2:reset=0", "-f", "null", "-"],
                          stdin=subprocess.DEVNULL, capture_output=True, text=True, encoding="utf-8", errors="replace")
    found = re.findall(r"crop=(\d+):(\d+):(\d+):(\d+)", proc.stderr)
    size = re.search(r"Video:.*?(\d{2,5})x(\d{2,5})", proc.stderr)
    if not found or not size:
        return ""
    w, h, x, y = map(int, found[-1])
    W, H = int(size.group(1)), int(size.group(2))
    if w < W * 0.3 or h < H * 0.3 or (w >= W * 0.95 and h >= H * 0.95):
        return ""  # a dark frame, not bars; or nothing to cut
    return f"{w}:{h}:{x}:{y}"


# ---------- download ----------

ARCHIVE_SECONDS = 20.0  # an Archive clip: long enough for most scenes without looping


def fetch(item: dict) -> Path:
    """The file of an item in the cache (downloaded once)."""
    from ..visuals import _download

    CACHE.mkdir(parents=True, exist_ok=True)
    safe = hashlib.sha1(str(item["id"]).encode()).hexdigest()[:16]
    ext = ".mp4" if item["kind"] == "video" else ".jpg"
    dest = CACHE / f"{item['source']}-{item['kind']}-{safe}{ext}"
    if dest.exists():
        return dest
    if item["source"] == "archive":
        return _archive_clip(item, ARCHIVE_SECONDS, dest)
    url = item["url"] or (_nasa_file(item) if item["source"] == "nasa" else "")
    if not url:
        raise ValueError(f"no file for {item['source']} {item['id']}")
    item["url"] = url
    path = _download(url, dest)
    path.with_suffix(".json").write_text(json.dumps({k: v for k, v in item.items() if k != "file"},
                                                    ensure_ascii=False), encoding="utf-8")
    return path


SEARCHES = {
    "inaturalist": lambda q, kind: inaturalist(q) if kind == "photo" else [],
    "met": lambda q, kind: met(q) if kind == "photo" else [],
    "nasa": nasa,
    "archive": lambda q, kind: archive(q) if kind == "video" else [],
}
LICENCES = {"inaturalist": "iNaturalist", "met": "The Metropolitan Museum of Art", "nasa": "NASA",
            "archive": "Internet Archive"}
