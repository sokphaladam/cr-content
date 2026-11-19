"""References in a pasted script: links (YouTube, TikTok, a page, a picture) and named sources ("Reference: BBC Earth,
octopus hunting"). Each is tied to the scene it's written in; a "References" / "Sources" block or a reference before
the first scene counts for every scene. shot_footage.find downloads them and offers them as footage, checked against
the shot like stock, flagged rights_unknown: a reference is someone else's material until you've checked.
"""
import hashlib
import re
from pathlib import Path

import requests

from .config import CACHE_DIR
from .visuals import IMAGE_EXTS, VIDEO_EXTS

CACHE = CACHE_DIR / "references"
PER_SHOT = 3   # references tried per shot (each one is a download and a Gemini look)
URL = re.compile(r"https?://[^\s<>\"')\]]+")
NAMED = re.compile(r"^\W*(?:ref(?:erence)?s?|sources?|footage|inspired by|b-?roll)\s*[:\-–]\s*(.+)$", re.I)
# a heading alone on its line. shortcut: the block runs to the end of the script; if scripts put one mid-way, end it
# at the next scene label instead
BLOCK = re.compile(r"^\W*(?:references?|sources?)\W*$", re.I)


def extract(text: str) -> list[tuple[int, str]]:
    """(character offset, reference) for every link and named reference, in order. -1 = the whole script."""
    out, pos, block = [], 0, False
    for line in text.splitlines(keepends=True):
        bare = line.strip()
        if BLOCK.match(bare):
            block = True
        urls = list(URL.finditer(line))
        out += [(-1 if block else pos + u.start(), u.group().rstrip(".,;")) for u in urls]
        m = NAMED.match(bare)
        if m and not urls and len(m.group(1).strip()) > 2:
            out.append((-1 if block else pos, m.group(1).strip()))
        pos += len(line)
    return out


def attach(plan, text: str) -> None:
    """Each scene's `references`: those written inside it (from where its narration starts to where the next one
    does), plus the script-wide ones."""
    starts = []
    for s in plan.scenes:
        probe = s.narration.strip()[:40]
        i = text.find(probe) if probe else -1
        starts.append(i if i >= 0 else (starts[-1] if starts else 0))
    for at, ref in extract(text):
        inside = [s for s, st in zip(plan.scenes, starts) if at >= 0 and st <= at]
        for s in inside[-1:] or plan.scenes:  # before the first scene or in a References block: every scene
            if ref not in s.references:
                s.references.append(ref)


def strip(text: str) -> str:
    """The script without its references, for the importer: a reference is a note, never voiceover."""
    out, block = [], False
    for line in text.splitlines():
        bare = line.strip()
        block = block or bool(BLOCK.match(bare))
        if block or NAMED.match(bare):
            continue
        out.append(URL.sub("", line).rstrip())
    return "\n".join(out)


def fetch(ref: str, log=print) -> Path | None:
    """A reference as a local file (cached): a direct picture or video link, a video page (yt-dlp), a page's main
    picture (og:image), or for a named reference the first YouTube result. None when nothing could be downloaded."""
    CACHE.mkdir(parents=True, exist_ok=True)
    key = hashlib.sha1(ref.encode()).hexdigest()[:16]
    done = [p for p in CACHE.glob(f"{key}.*") if p.suffix.lower() in (*VIDEO_EXTS, *IMAGE_EXTS)]
    if done:
        return done[0]
    url = ref if URL.fullmatch(ref) else f"ytsearch1:{ref}"
    ext = Path(ref.split("?")[0]).suffix.lower()
    try:
        if ext in (*VIDEO_EXTS, *IMAGE_EXTS):
            return _save(url, CACHE / f"{key}{ext}")
        got = _video(url, key)
        if got or not url.startswith("http"):
            return got
        image = _page_image(url)
        if image:
            return _save(image, CACHE / f"{key}{Path(image.split('?')[0]).suffix.lower() or '.jpg'}")
    except (requests.RequestException, OSError) as e:
        log(f"      ! reference {ref[:60]}: couldn't download it ({type(e).__name__})")
    return None


def _save(url: str, dest: Path) -> Path:
    with requests.get(url, stream=True, timeout=60, headers={"User-Agent": "Mozilla/5.0"}) as r:
        r.raise_for_status()
        part = dest.with_name(dest.name + ".part")
        with part.open("wb") as f:
            for chunk in r.iter_content(1 << 20):
                f.write(chunk)
    part.replace(dest)
    return dest


class _Silent:
    def debug(self, msg): pass
    def info(self, msg): pass
    def warning(self, msg): pass
    def error(self, msg): pass


def _video(url: str, key: str) -> Path | None:
    try:
        import yt_dlp
    except ImportError:
        return None
    opts = {"outtmpl": str(CACHE / f"{key}.%(ext)s"), "noplaylist": True, "quiet": True, "no_warnings": True,
            "format": "bv*[height<=1080]+ba/b[height<=1080]/b", "merge_output_format": "mp4",
            "max_filesize": 300 << 20, "match_filter": yt_dlp.utils.match_filter_func("duration < 1200"),
            "logger": _Silent()}  # a page that isn't a video is expected: the og:image fallback handles it
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.extract_info(url, download=True)
    except Exception:  # not a video page (an article...), private, removed, or yt-dlp can't read that site
        return None
    found = [p for p in CACHE.glob(f"{key}.*") if p.suffix.lower() in VIDEO_EXTS]
    return found[0] if found else None


def _page_image(url: str) -> str | None:
    """A page's main picture: its og:image / twitter:image."""
    r = requests.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
    r.raise_for_status()
    m = re.search(r"<meta[^>]+(?:property|name)=[\"'](?:og:image|twitter:image)[\"'][^>]*content=[\"']([^\"']+)",
                  r.text, re.I) or re.search(
        r"<meta[^>]+content=[\"']([^\"']+)[\"'][^>]*(?:property|name)=[\"'](?:og:image|twitter:image)[\"']", r.text, re.I)
    return requests.compat.urljoin(url, m.group(1)) if m else None
