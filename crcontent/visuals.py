"""Background media: stock videos/photos (Pexels or Pixabay), user uploads, local footage, or gradient fallback."""
import os
import random
from pathlib import Path

import requests

from .config import ASSETS_DIR, CACHE_DIR, HEIGHT, ROOT

PEXELS_VIDEO_SEARCH = "https://api.pexels.com/videos/search"
PEXELS_VIDEO_BY_ID = "https://api.pexels.com/videos/videos/{id}"
PEXELS_PHOTO_SEARCH = "https://api.pexels.com/v1/search"
PEXELS_PHOTO_BY_ID = "https://api.pexels.com/v1/photos/{id}"
PIXABAY_VIDEOS = "https://pixabay.com/api/videos/"
PIXABAY_PHOTOS = "https://pixabay.com/api/"
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


def stock_source() -> str:
    """Which stock library is configured: 'pexels', 'pixabay', or '' for none."""
    return "pexels" if pexels_key() else "pixabay" if pixabay_key() else ""


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


# ---------- Public API ----------

def search(query: str, kind: str = "video", per_page: int = 15, orientation: str = "portrait") -> list[dict]:
    """Stock search results for the scene picker UI, from whichever library is configured."""
    source = stock_source()
    if source == "pexels":
        return _pexels_search(query, kind, per_page, orientation)
    if source == "pixabay":
        return _pixabay_search(query, kind, per_page, orientation)
    return []


def download_stock(source: str, kind: str, item_id: int, orientation: str = "portrait") -> Path:
    """Fetch one item by id (never by a client-supplied URL) into the cache."""
    kind = "photo" if kind == "photo" else "video"
    if source == "pexels" and pexels_key():
        return _pexels_download(kind, int(item_id), orientation)
    if source == "pixabay" and pixabay_key():
        return _pixabay_download(kind, int(item_id))
    raise ValueError(f"No API key configured for {source or 'stock footage'}.")


class FootagePicker:
    """Finds one clip per scene automatically and avoids repeating a clip within a video."""

    def __init__(self, orientation: str = "portrait") -> None:
        self.orientation = orientation
        self.source = stock_source()
        self.used: set[str] = set()
        self.local = sorted(LOCAL_FOOTAGE.glob("*.mp4")) if LOCAL_FOOTAGE.exists() else []

    def pick(self, query: str) -> Path | None:
        """Return a local media path, or None to signal the gradient fallback."""
        if self.source:
            try:
                clip = self._stock(query) or self._stock(query.split()[0])
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

    def _stock(self, query: str) -> Path | None:
        for item in search(query, "video", per_page=10, orientation=self.orientation):
            key = f"{item['source']}-{item['id']}"
            if key in self.used:
                continue
            self.used.add(key)
            return download_stock(item["source"], "video", item["id"], self.orientation)
        return None


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
