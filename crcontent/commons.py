"""Real photos from Wikimedia Commons, for real subjects that image models can't draw and stock sites don't have
(a peacock mantis shrimp, a rare bird, a specific engine). Only freely licensed files (public domain, CC0, CC BY,
CC BY-SA); each keeps its author and licence, which go into the post's description as a credit."""
import hashlib
import json
import re
from pathlib import Path

import requests

from .config import CACHE_DIR

API = "https://commons.wikimedia.org/w/api.php"
CACHE = CACHE_DIR / "commons"
# Wikimedia asks every client to say who it is
HEADERS = {"User-Agent": "ShortsStudio/0.1 (desktop video app; contact via GitHub sokphaladam)"}
FREE = re.compile(r"^(public domain|pd\b|cc0|cc by(-sa)?\b)", re.I)
WIDTH = 1600  # downloaded size: enough for a 1080x1920 frame with room for camera moves


def _plain(html: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", html or "")).strip()


def search(query: str, count: int = 8) -> list[dict]:
    """Freely licensed photos for `query`, best matches first: {title, url, page, author, licence}."""
    data = requests.get(API, params={
        "action": "query", "format": "json", "generator": "search", "gsrsearch": f"filetype:bitmap {query}",
        "gsrnamespace": 6, "gsrlimit": count * 2, "prop": "imageinfo", "iiprop": "url|size|extmetadata",
        "iiurlwidth": WIDTH}, headers=HEADERS, timeout=30).json()
    pages = sorted((data.get("query") or {}).get("pages", {}).values(), key=lambda p: p.get("index", 0))
    out = []
    for p in pages:
        info = (p.get("imageinfo") or [{}])[0]
        meta = info.get("extmetadata") or {}
        licence = _plain((meta.get("LicenseShortName") or {}).get("value", ""))
        if not FREE.match(licence) or min(info.get("width", 0), info.get("height", 0)) < 900:
            continue
        out.append({"title": p["title"].removeprefix("File:"), "url": info.get("thumburl") or info["url"],
                    "page": info.get("descriptionurl", ""), "licence": licence,
                    "author": _plain((meta.get("Artist") or {}).get("value", ""))[:80] or "Unknown author"})
        if len(out) == count:
            break
    return out


def download(item: dict) -> Path:
    """The photo in the cache, with its credit saved next to it (credit() reads it back)."""
    name = hashlib.sha1(item["url"].encode()).hexdigest()[:16]
    path = CACHE / f"{name}.jpg"
    if not path.exists():
        CACHE.mkdir(parents=True, exist_ok=True)
        with requests.get(item["url"], headers=HEADERS, stream=True, timeout=60) as r:
            r.raise_for_status()
            tmp = path.with_suffix(".part")
            with open(tmp, "wb") as f:
                for chunk in r.iter_content(1 << 16):
                    f.write(chunk)
        tmp.replace(path)
        path.with_suffix(".json").write_text(json.dumps(item, ensure_ascii=False), encoding="utf-8")
    return path


def credit(path: Path) -> str:
    """'Photo: <author>, <licence>, via Wikimedia Commons' for a photo from here; "" for anything else."""
    meta = Path(path).with_suffix(".json")
    if Path(path).parent.resolve() != CACHE.resolve() or not meta.exists():
        return ""
    item = json.loads(meta.read_text(encoding="utf-8"))
    return f"Photo: {item['author']}, {item['licence']}, via Wikimedia Commons ({item['page']})"
