"""Background music library (assets/music): tracks found on Jamendo, and the credit each track needs.

Jamendo tracks are Creative Commons; most licences require naming the artist, so every downloaded track gets a
<track>.json next to it with its credit, and the video's description carries that credit (see credit()).
"""
import json
import os
import re
from pathlib import Path

import requests

from .config import ASSETS_DIR

MUSIC_DIR = ASSETS_DIR / "music"
JAMENDO_API = "https://api.jamendo.com/v3.0"


class MusicError(RuntimeError):
    pass


def jamendo_key() -> str:
    return os.getenv("JAMENDO_CLIENT_ID", "").strip()


def tracks() -> list[str]:
    return sorted(p.name for p in MUSIC_DIR.glob("*.mp3")) if MUSIC_DIR.exists() else []


def licence_use(url: str) -> str:
    """What a Creative Commons licence (its URL) lets you do with music in a video you may earn from:
    "ok" (CC0, CC BY, CC BY-SA; public domain), "nc" (non-commercial: not for monetized videos), "nd" (no
    derivatives: Creative Commons counts putting music to video as an adaptation, so it can't be used in one at all),
    or "unknown"."""
    u = (url or "").lower()
    if not u:
        return "unknown"
    if "-nc" in u or "/nc" in u:
        return "nc"
    if "-nd" in u or "/nd" in u:
        return "nd"
    if "creativecommons.org" in u or "publicdomain" in u:
        return "ok"
    return "unknown"


def track_use(track: Path | str) -> str:
    """licence_use() of a library track, from the licence saved next to it ("unknown" without one)."""
    meta = MUSIC_DIR / f"{Path(track).stem}.json"
    try:
        return licence_use(json.loads(meta.read_text(encoding="utf-8")).get("license", ""))
    except (OSError, ValueError):
        return "unknown"


def credit(track: Path | str | None) -> str:
    """The credit line a track needs in the video's description ("" when it needs none or isn't known)."""
    if not track:
        return ""
    meta = MUSIC_DIR / f"{Path(track).stem}.json"
    try:
        return json.loads(meta.read_text(encoding="utf-8")).get("credit", "")
    except (OSError, ValueError):
        return ""


def _words(text: str) -> list[str]:
    return [w for w in re.findall(r"[a-z]{3,}", text.lower()) if w not in {"and", "with", "the", "sfx", "only"}]


def best_matches(mood: str, names: list[str]) -> list[str]:
    """The track names that share the most words with `mood` (none when no name shares any)."""
    want = set(_words(mood))
    scores = {n: len(want & set(_words(Path(n).stem))) for n in names}
    top = max(scores.values(), default=0)
    return [n for n, score in scores.items() if score == top] if top else []


def local_match(mood: str) -> str:
    """The library track whose file name best fits `mood` ("" when none shares a word with it)."""
    return next(iter(best_matches(mood, tracks())), "")


def search(query: str, limit: int = 20) -> list[dict]:
    """Instrumental Jamendo tracks for `query` (mood or style words), most popular first. Tracks whose artist doesn't
    allow downloads are left out."""
    key = jamendo_key()
    if not key:
        raise MusicError("Add a free Jamendo client ID in Settings first.")
    params = {"client_id": key, "format": "json", "limit": limit, "vocalinstrumental": "instrumental",
              "include": "musicinfo", "audioformat": "mp32", "audiodlformat": "mp32", "order": "popularity_total"}
    words = _words(query)
    results: list[dict] = []
    # mood words as tags find the best fits; plain text search is the fallback
    for extra in ([{"fuzzytags": "+".join(words[:4])}] if words else []) + [{"search": query.strip()}]:
        try:
            r = requests.get(f"{JAMENDO_API}/tracks/", params={**params, **extra}, timeout=20)
            data = r.json()
        except (requests.RequestException, ValueError) as e:
            raise MusicError(f"Couldn't reach Jamendo ({e.__class__.__name__}). Check your internet connection.")
        head = data.get("headers", {})
        if head.get("status") != "success":
            raise MusicError(f"Jamendo: {head.get('error_message') or 'the search failed'}. Check the client ID in Settings.")
        results = [t for t in data.get("results", []) if t.get("audiodownload_allowed") and t.get("audiodownload")]
        if results:
            break
    return [{
        "id": str(t["id"]),
        "name": t.get("name", ""),
        "artist": t.get("artist_name", ""),
        "duration": t.get("duration", 0),
        "preview": t.get("audio", ""),
        "image": t.get("image") or t.get("album_image", ""),
        "license": t.get("license_ccurl", ""),
        # NC licences don't allow commercial use (a monetized channel may count)
        "commercial": "-nc" not in t.get("license_ccurl", "").lower(),
        "use": licence_use(t.get("license_ccurl", "")),  # "ok" = fine in a monetized video (see licence_use)
        "tags": ((t.get("musicinfo") or {}).get("tags") or {}).get("vartags", [])[:4],
    } for t in results]


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:40] or "track"


def download(track_id: str) -> str:
    """Save a Jamendo track into assets/music (with its credit next to it). Returns the file name."""
    key = jamendo_key()
    if not key:
        raise MusicError("Add a free Jamendo client ID in Settings first.")
    if not re.fullmatch(r"\d{1,12}", track_id):
        raise MusicError("Unknown track.")
    existing = list(MUSIC_DIR.glob(f"jamendo-{track_id}-*.mp3")) if MUSIC_DIR.exists() else []
    if existing:
        return existing[0].name
    try:
        r = requests.get(f"{JAMENDO_API}/tracks/", timeout=20, params={
            "client_id": key, "format": "json", "id": track_id, "include": "musicinfo", "audiodlformat": "mp32"})
        t = (r.json().get("results") or [None])[0]
    except (requests.RequestException, ValueError) as e:
        raise MusicError(f"Couldn't reach Jamendo ({e.__class__.__name__}).")
    if not t or not t.get("audiodownload_allowed") or not t.get("audiodownload"):
        raise MusicError("This track can't be downloaded. Pick another one.")
    tags = ((t.get("musicinfo") or {}).get("tags") or {}).get("vartags", [])[:3]
    name = f"jamendo-{track_id}-{_slug(' '.join(tags + [t.get('name', '')]))}.mp3"
    MUSIC_DIR.mkdir(parents=True, exist_ok=True)
    dest = MUSIC_DIR / name
    tmp = dest.with_suffix(".part")
    try:
        with requests.get(t["audiodownload"], stream=True, timeout=60) as resp:
            resp.raise_for_status()
            with open(tmp, "wb") as f:
                for chunk in resp.iter_content(1 << 16):
                    f.write(chunk)
    except requests.RequestException as e:
        tmp.unlink(missing_ok=True)
        raise MusicError(f"The download failed ({e.__class__.__name__}). Try again.")
    tmp.replace(dest)
    license_url = t.get("license_ccurl", "")
    meta = {"title": t.get("name", ""), "artist": t.get("artist_name", ""), "source": t.get("shareurl", ""),
            "license": license_url,
            "credit": f"Music: \"{t.get('name', '')}\" by {t.get('artist_name', '')} (Jamendo), {license_url}".strip(", ")}
    dest.with_suffix(".json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    return name


def for_mood(mood: str) -> str:
    """Download the most popular instrumental Jamendo track for a mood ("" when there's no key or nothing fits)."""
    if not jamendo_key() or not mood.strip():
        return ""
    try:
        found = [t for t in search(mood, limit=10) if t["use"] == "ok"]  # only what a monetized video may use
        return download(found[0]["id"]) if found else ""
    except MusicError:
        return ""
