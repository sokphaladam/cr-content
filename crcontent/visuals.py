"""Background media: stock videos/photos (Pexels, Pixabay, Mixkit, Unsplash), user uploads, local footage, or gradient fallback."""
import html
import os
import re
import random
import subprocess
from pathlib import Path

import requests

from .config import ASSETS_DIR, CACHE_DIR, HEIGHT, ROOT

PEXELS_VIDEO_SEARCH = "https://api.pexels.com/videos/search"
PEXELS_VIDEO_BY_ID = "https://api.pexels.com/videos/videos/{id}"
PEXELS_PHOTO_SEARCH = "https://api.pexels.com/v1/search"
PEXELS_PHOTO_BY_ID = "https://api.pexels.com/v1/photos/{id}"
PIXABAY_VIDEOS = "https://pixabay.com/api/videos/"
PIXABAY_PHOTOS = "https://pixabay.com/api/"
UNSPLASH_SEARCH = "https://api.unsplash.com/search/photos"
UNSPLASH_BY_ID = "https://api.unsplash.com/photos/{id}"
MIXKIT_SEARCH = "https://mixkit.co/free-stock-video/discover/{slug}/"
MIXKIT_FILE = "https://assets.mixkit.co/videos/{id}/{id}-{size}.mp4"
LOCAL_FOOTAGE = ASSETS_DIR / "footage"
STOCK_CACHE = CACHE_DIR / "stock"

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp"}
VIDEO_EXTS = {".mp4", ".mov", ".webm", ".m4v"}


def is_image(path: Path) -> bool:
    return path.suffix.lower() in IMAGE_EXTS


def pexels_key() -> str:
    return os.getenv("PEXELS_API_KEY", "").strip()


def pixabay_key() -> str:
    return os.getenv("PIXABAY_API_KEY", "").strip()


def unsplash_key() -> str:
    return os.getenv("UNSPLASH_ACCESS_KEY", "").strip()


def stock_source() -> str:
    """The first stock library searched: 'pexels', 'pixabay', else 'mixkit' (it needs no key)."""
    return "pexels" if pexels_key() else "pixabay" if pixabay_key() else "mixkit"


def _get(url: str, headers: dict | None = None, **params) -> dict:
    r = requests.get(url, headers=headers or {}, params=params, timeout=20)
    r.raise_for_status()
    return r.json()


# ---------- Pexels ----------

def _pexels(url: str, **params) -> dict:
    return _get(url, headers={"Authorization": pexels_key()}, **params)


def _pexels_best_file(files: list[dict], orientation: str = "portrait") -> dict | None:
    """Smallest mp4 facing the right way that is still at least full-HD-ish (keeps downloads light)."""
    def long(f: dict) -> int:
        return max(f.get("height") or 0, f.get("width") or 0)

    landscape = orientation == "landscape"
    facing = [f for f in files if f.get("file_type") == "video/mp4"
              and ((f.get("width") or 0) > (f.get("height") or 0)) == landscape]
    good = [f for f in facing if long(f) >= HEIGHT * 0.66]
    if good:
        return min(good, key=long)
    return max(facing, key=long) if facing else None


def _pexels_search(query: str, kind: str, per_page: int, orientation: str) -> list[dict]:
    if kind == "photo":
        data = _pexels(PEXELS_PHOTO_SEARCH, query=query, orientation=orientation, per_page=per_page)
        return [{"source": "pexels", "id": p["id"], "kind": "photo", "thumb": p["src"]["medium"],
                 "author": p.get("photographer", "")} for p in data.get("photos", [])]
    data = _pexels(PEXELS_VIDEO_SEARCH, query=query, orientation=orientation, size="medium", per_page=per_page)
    return [{"source": "pexels", "id": v["id"], "kind": "video", "thumb": v.get("image", ""),
             "duration": v.get("duration", 0), "author": (v.get("user") or {}).get("name", "")}
            for v in data.get("videos", []) if _pexels_best_file(v.get("video_files", []), orientation)]


def _pexels_download(kind: str, item_id: int, orientation: str) -> Path:
    if kind == "photo":
        photo = _pexels(PEXELS_PHOTO_BY_ID.format(id=item_id))
        return _download(photo["src"]["large2x"], STOCK_CACHE / f"pexels-photo-{item_id}.jpg")
    file = _pexels_best_file(_pexels(PEXELS_VIDEO_BY_ID.format(id=item_id)).get("video_files", []), orientation)
    if not file:
        raise ValueError(f"This video has no usable {orientation} file.")
    return _download(file["link"], STOCK_CACHE / f"pexels-{item_id}.mp4")


# ---------- Pixabay ----------

def _pixabay(url: str, **params) -> dict:
    return _get(url, key=pixabay_key(), safesearch="true", **params)


def _pixabay_best_file(videos: dict) -> dict | None:
    """Pixabay sizes: large (often 4K), medium (~1080p), small (~720p), tiny. The smallest that is still full HD:
    4K files are hundreds of MB and only slow the render down, since videos are 1080p."""
    files = [f for f in (videos.get(s) or {} for s in ("small", "medium", "large")) if f.get("url")]
    for f in files:
        if max(f.get("width") or 0, f.get("height") or 0) >= 1900:
            return f
    return files[-1] if files else None


def _pixabay_search(query: str, kind: str, per_page: int, orientation: str) -> list[dict]:
    landscape = orientation == "landscape"
    if kind == "photo":
        data = _pixabay(PIXABAY_PHOTOS, q=query, image_type="photo",
                        orientation="horizontal" if landscape else "vertical", per_page=per_page)
        return [{"source": "pixabay", "id": p["id"], "kind": "photo", "thumb": p.get("webformatURL", ""),
                 "author": p.get("user", "")} for p in data.get("hits", [])]
    data = _pixabay(PIXABAY_VIDEOS, q=query, video_type="film", per_page=max(per_page, 20))
    hits = [h for h in data.get("hits", []) if _pixabay_best_file(h.get("videos", {}))]
    # Pixabay has no orientation filter for video: list clips facing the frame's way first (they crop best)
    hits.sort(key=lambda h: (lambda f: (f.get("width", 0) > f.get("height", 0)) != landscape)(_pixabay_best_file(h["videos"])))
    return [{"source": "pixabay", "id": h["id"], "kind": "video",
             "thumb": h["videos"].get("tiny", {}).get("thumbnail") or h["videos"].get("medium", {}).get("thumbnail", ""),
             "duration": h.get("duration", 0), "author": h.get("user", "")} for h in hits[:per_page]]


def _pixabay_download(kind: str, item_id: int) -> Path:
    if kind == "photo":
        hits = _pixabay(PIXABAY_PHOTOS, id=item_id).get("hits", [])
        if not hits:
            raise ValueError("Photo not found on Pixabay.")
        return _download(hits[0]["largeImageURL"], STOCK_CACHE / f"pixabay-photo-{item_id}.jpg")
    hits = _pixabay(PIXABAY_VIDEOS, id=item_id).get("hits", [])
    file = _pixabay_best_file(hits[0].get("videos", {})) if hits else None
    if not file:
        raise ValueError("Video not found on Pixabay.")
    return _download(file["url"], STOCK_CACHE / f"pixabay-{item_id}.mp4")


# ---------- Mixkit (free videos, no API: its tag pages are read) ----------

def _mixkit_page(slug: str) -> list[dict]:
    r = requests.get(MIXKIT_SEARCH.format(slug=slug), headers={"User-Agent": "Mozilla/5.0 (compatible; ShortStudio)"},
                     timeout=20)
    r.raise_for_status()
    out = []
    for card in r.text.split('data-item-grid--video-player-item-id-value="')[1:]:
        item_id = re.match(r"(\d+)\"", card)
        img = re.search(r'alt="([^"]*)" width="(\d+)" height="(\d+)"', card)
        if not (item_id and img):
            continue
        title = re.search(r'overlay-video-title">\s*([^<]*?)\s*<', card)
        href = re.search(r'href="(/free-stock-video/[^"]+)"', card)
        out.append({"id": int(item_id[1]), "alt": html.unescape(img[1]), "title": html.unescape(title[1]) if title else "",
                    "aspect": int(img[2]) / max(int(img[3]), 1), "page": f"https://mixkit.co{href[1]}" if href else ""})
    return out


def _mixkit_file(item_id: int, aspect: float, width: int, portrait: bool) -> tuple[str, int, int] | None:
    """The smallest of Mixkit's 720/1080/2160 files that fills a `width`-wide frame (a 9:16 one once cropped), else
    the biggest it has: not every clip has every size, so each is asked for."""
    best = None
    for size in (720, 1080, 2160):
        w, h = (round(size * aspect), size) if aspect >= 1 else (size, round(size / aspect))
        url = MIXKIT_FILE.format(id=item_id, size=size)
        try:
            if requests.head(url, timeout=10).status_code != 200:
                continue
        except requests.RequestException:
            continue
        best = (url, w, h)
        if (min(w, h * 9 / 16) if portrait else w) >= width:
            break
    return best


def mixkit_search(query: str, width: int = 1080, portrait: bool = True, limit: int = 12) -> list[dict]:
    """Mixkit clips for `query`. Its pages exist only for tags ("cat", not "cat drinking water"), so the words are
    dropped from the end until a page has clips."""
    # shortcut: "green heron fishing" can end at the "green" page (junk the subject check then rejects); try word
    # windows other than prefixes if that wastes too many checks
    words = re.findall(r"[a-z0-9]+", query.lower())
    hits = []
    for n in range(len(words), 0, -1):
        if hits := _mixkit_page("-".join(words[:n])):
            break
    hits = hits[:limit]
    from concurrent.futures import ThreadPoolExecutor

    with ThreadPoolExecutor(8) as pool:
        files = list(pool.map(lambda h: _mixkit_file(h["id"], h["aspect"], width, portrait), hits))
    return [{"source": "mixkit", "id": h["id"], "kind": "video", "thumb": f"https://assets.mixkit.co/videos/{h['id']}/{h['id']}-thumb-360-0.jpg",
             "page": h["page"], "author": "Mixkit", "width": f[1], "height": f[2], "url": f[0],
             "tags": f"{h['title']} {h['alt']}".lower(), "preview": MIXKIT_FILE.format(id=h["id"], size=360)}
            for h, f in zip(hits, files) if f]


def _mixkit_download(item_id: int) -> Path:
    for size in (1080, 720, 2160):  # the size isn't known from the id alone
        try:
            return _download(MIXKIT_FILE.format(id=item_id, size=size), STOCK_CACHE / f"mixkit-{item_id}.mp4")
        except requests.HTTPError:
            continue
    raise ValueError("Video not found on Mixkit.")


# ---------- Unsplash (photos only) ----------

def _unsplash(url: str, **params) -> dict:
    return _get(url, headers={"Authorization": f"Client-ID {unsplash_key()}", "Accept-Version": "v1"}, **params)


def unsplash_track(download_location: str) -> None:
    """Unsplash's API terms: tell it when a photo is downloaded (a failed ping never stops the download)."""
    try:
        _unsplash(download_location)
    except requests.RequestException:
        pass


def _unsplash_url(p: dict) -> str:
    return f"{p['urls']['raw']}&fm=jpg&q=85&w=2400"  # big enough for a 1080p frame with a slow zoom


def unsplash_search(query: str, orientation: str | None = None, per_page: int = 10) -> list[dict]:
    """orientation: landscape / portrait, or None for any."""
    data = _unsplash(UNSPLASH_SEARCH, query=query, orientation=orientation, per_page=per_page, content_filter="high")
    return [{"source": "unsplash", "id": p["id"], "kind": "photo", "thumb": p["urls"]["small"],
             "page": (p.get("links") or {}).get("html", ""), "author": (p.get("user") or {}).get("name", ""),
             "width": p.get("width") or 0, "height": p.get("height") or 0, "url": _unsplash_url(p),
             "download_location": p["links"]["download_location"],
             "tags": " ".join(filter(None, [p.get("alt_description"), p.get("description"),
                                            *[t.get("title", "") for t in p.get("tags") or []]])).lower()}
            for p in data.get("results", [])]


def _unsplash_download(item_id: str) -> Path:
    if not re.fullmatch(r"[\w-]+", item_id):
        raise ValueError("Not an Unsplash photo id.")
    p = _unsplash(UNSPLASH_BY_ID.format(id=item_id))
    unsplash_track(p["links"]["download_location"])
    return _download(_unsplash_url(p), STOCK_CACHE / f"unsplash-photo-{item_id}.jpg")


# ---------- Public API ----------

def search(query: str, kind: str = "video", per_page: int = 15, orientation: str = "portrait") -> list[dict]:
    """Stock search results for the scene picker UI from every library that's set up, taking turns (Pexels' 1st,
    Pixabay's 1st, Mixkit's 1st..., then each one's 2nd), so they can be compared side by side. A library that fails
    is skipped; the error is raised only when every one failed."""
    runs = []
    if pexels_key():
        runs.append(lambda: _pexels_search(query, kind, per_page, orientation))
    if pixabay_key():
        runs.append(lambda: _pixabay_search(query, kind, per_page, orientation))
    if kind == "video":  # Mixkit needs no key
        runs.append(lambda: mixkit_search(query, 1080, orientation == "portrait", per_page))
    elif unsplash_key():
        runs.append(lambda: unsplash_search(query, orientation, per_page))
    lists, error = [], None
    for run_one in runs:
        try:
            lists.append(run_one())
        except (requests.RequestException, ValueError, KeyError) as e:
            error = e
    if error and not lists:
        raise error
    return [x for k in range(max(map(len, lists), default=0)) for lst in lists if k < len(lst) for x in [lst[k]]]


def download_stock(source: str, kind: str, item_id: int | str, orientation: str = "portrait") -> Path:
    """Fetch one item by id (never by a client-supplied URL) into the cache."""
    kind = "photo" if kind == "photo" else "video"
    if source == "unsplash" and unsplash_key():
        return _unsplash_download(str(item_id))
    if source == "mixkit":
        return _mixkit_download(int(item_id))
    if source == "pexels" and pexels_key():
        return _pexels_download(kind, int(item_id), orientation)
    if source == "pixabay" and pixabay_key():
        return _pixabay_download(kind, int(item_id))
    raise ValueError(f"No API key configured for {source or 'stock footage'}.")


HOOK_TRIES = 4  # stock results compared for a video's opening shot


class FootagePicker:
    """Finds one clip per scene automatically and avoids repeating a clip within a video."""

    def __init__(self, orientation: str = "portrait") -> None:
        self.orientation = orientation
        self.source = stock_source()
        self.used: set[str] = set()
        self.local = sorted(LOCAL_FOOTAGE.glob("*.mp4")) if LOCAL_FOOTAGE.exists() else []

    def pick(self, query: str, hook: bool = False) -> Path | None:
        """Return a local media path, or None to signal the gradient fallback. `hook`: this is the video's first
        scene, the frame people see in the feed: of the top few results, take the one with the brightest, most
        moving opening instead of simply the first."""
        if self.source:
            try:
                clip = self._stock(query, hook) or self._stock(query.split()[0], hook)
                if clip:
                    return clip
            except (requests.RequestException, ValueError, KeyError) as e:
                print(f"  ! {self.source} error for '{query}': {e}")
        unused = [p for p in self.local if str(p) not in self.used]
        if unused:
            clip = random.choice(unused)
            self.used.add(str(clip))
            return clip
        return None

    def _stock(self, query: str, hook: bool = False) -> Path | None:
        fresh = [(f"{item['source']}-{item['id']}", item)
                 for item in search(query, "video", per_page=10, orientation=self.orientation)]
        fresh = [(key, item) for key, item in fresh if key not in self.used]
        if not hook:
            for key, item in fresh[:1]:
                self.used.add(key)
                return download_stock(item["source"], "video", item["id"], self.orientation)
            return None
        from .thumbs import opening_score

        best: tuple[float, str, Path] | None = None
        for key, item in fresh[:HOOK_TRIES]:
            try:
                path = download_stock(item["source"], "video", item["id"], self.orientation)
                score = opening_score(path)
            except (requests.RequestException, ValueError, OSError, subprocess.CalledProcessError):
                continue
            if best is None or score > best[0]:
                best = (score, key, path)
        if best is None:
            return None
        self.used.add(best[1])
        return best[2]


def project_path(path: Path) -> str:
    """Path stored in script.json: relative to the project root, forward slashes."""
    return path.resolve().relative_to(ROOT).as_posix()


def _download(url: str, dest: Path) -> Path:
    if dest.exists() and dest.stat().st_size > 0:
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(".part")
    with requests.get(url, stream=True, timeout=60) as r:
        r.raise_for_status()
        with open(tmp, "wb") as f:
            for chunk in r.iter_content(1 << 16):
                f.write(chunk)
    tmp.replace(dest)
    return dest
