"""Real photos from Wikimedia Commons, for real subjects that image models can't draw and stock sites don't have
(a peacock mantis shrimp, a rare bird, a specific engine). Only freely licensed files (public domain, CC0, CC BY,
CC BY-SA); each keeps its author and licence, which go into the post's description as a credit."""
import hashlib
import json
import re
import threading
import time
from pathlib import Path

import requests

from .config import CACHE_DIR

API = "https://commons.wikimedia.org/w/api.php"
CACHE = CACHE_DIR / "commons"
# Wikimedia asks every client to say who it is, with a way to reach its maker (a URL or an email address)
HEADERS = {"User-Agent": "ShortsStudio/0.1 (https://github.com/sokphaladam/cr-content; desktop video app)"}
FREE = re.compile(r"^(public domain|pd\b|cc0|cc by(-sa)?\b)", re.I)
# downloaded size: enough for a 1080x1920 frame with room for camera moves. One of Wikimedia's standard thumbnail
# widths (20 ... 960, 1280, 1920, 3840): any other width is made on request and strictly rate-limited
WIDTH = 1920
GAP_SEC = 1.0        # between downloads: Wikimedia answers bursts with 429 (too many requests)
MAX_WAIT = 90.0      # a 429 asking to wait longer than this fails the download (the caller tries other libraries)
DEFAULT_WAIT = 20.0  # when a 429 doesn't say how long
_lock = threading.Lock()
_next_at = 0.0       # when the next download may start (spacing, or a 429's Retry-After)


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


def _wait_seconds(response: requests.Response) -> float:
    try:
        return max(float(response.headers.get("retry-after") or DEFAULT_WAIT), 1.0)
    except ValueError:  # an HTTP date instead of seconds
        return DEFAULT_WAIT


def download(item: dict) -> Path:
    """The photo in the cache, with its credit saved next to it (credit() reads it back). Downloads go one at a
    time, spaced out; a 429 is waited out (Retry-After) and tried again, unless it asks for more than MAX_WAIT."""
    global _next_at
    name = hashlib.sha1(item["url"].encode()).hexdigest()[:16]
    path = CACHE / f"{name}.jpg"
    if path.exists():
        return path
    CACHE.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".part")
    with _lock:
        for attempt in range(3):
            wait = _next_at - time.time()
            if wait > MAX_WAIT:
                raise ValueError(f"Wikimedia asked to wait {wait:.0f} s (too many requests); try again later")
            if wait > 0:
                time.sleep(wait)
            with requests.get(item["url"], headers=HEADERS, stream=True, timeout=60) as r:
                if r.status_code == 429 and attempt < 2:
                    _next_at = time.time() + _wait_seconds(r) * (attempt + 1)
                    continue
                r.raise_for_status()
                with open(tmp, "wb") as f:
                    for chunk in r.iter_content(1 << 16):
                        f.write(chunk)
            _next_at = time.time() + GAP_SEC
            break
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
