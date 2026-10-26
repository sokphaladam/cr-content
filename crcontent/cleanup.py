"""Settings > Storage > Clean up: find files nothing needs any more, and delete the ones you pick.

Everything here can be made again, but some of it takes time or a download, so each group says what deleting costs:

- work       the half-made pieces a render leaves in <video>/work (when it was stopped or failed)
- old        the .bak-<time> copies kept when a video, audio or text file was made or edited again
- removed    your clips you took off a Short (moved to <media>/removed, not deleted at the time)
- pictures   drawn pictures (cache/gen, cache/art) no video, draft or song refers to
- footage    downloaded stock clips and photos (cache/stock, commons, archives) no video, draft or song refers to
- temp       previews, filmstrips and depth maps that are drawn again when needed

"Refers to" = the file's name appears in a .json / .txt file of a video, draft, song or the schedule. Files changed in
the last day are left alone (something may be downloading them), and nothing is deleted while a video is being made.
Voiceover and speech caches are never touched: making them again can cost credits.
"""
import os
import re
import time
from pathlib import Path

DAY = 86_400
BAK = re.compile(r"\.bak-\d{8}-\d{6}$")
NAME = re.compile(r"[\w][\w.\-]*\.(?:mp4|mov|webm|mkv|jpe?g|png|webp|gif|npy|mp3|wav|m4a|json)", re.I)
CATEGORIES = {
    "work": ("Leftover render files",
             "The pieces a render builds a video from (clips, joined picture, caption files). Music videos keep theirs; a stopped or failed render leaves them too.",
             "Making a new thumbnail for those videos later uses the finished video (captions may show in it)."),
    "old": ("Older versions of files",
            "The .bak copies kept when a video, audio file or text was made or edited again.",
            "You can no longer go back to the version before."),
    "removed": ("Clips you removed from Shorts",
                "Your own clips set aside when you removed them from a beat.",
                "They're gone for good: keep any you may want back."),
    "pictures": ("Drawn pictures no video uses",
                 "AI pictures that no video, draft or song refers to.",
                 "Drawing them again takes a few seconds each on your GPU."),
    "footage": ("Downloaded footage no video uses",
                "Stock clips and photos that no video, draft or song refers to.",
                "They download again if a search picks them."),
    "temp": ("Previews and temporary caches",
             "Preview clips, filmstrips and depth maps.",
             "They are drawn again the next time you need them."),
}


def _files(folder: Path):
    for base, _, names in os.walk(folder):
        for n in names:
            yield Path(base) / n


def _references(root: Path, output: Path) -> set[str]:
    """The names (before the first dot) of every media file the library's json / txt files mention."""
    texts: list[Path] = [*root.glob("*.json")]
    for pattern in ("*/*.json", "*/*.txt"):
        texts += output.glob(pattern)
    for folder in ("drafts", "songs", "scripts"):
        texts += (root / folder).glob("**/*.json") if folder == "drafts" else (root / folder).glob("*/*.json")
    found: set[str] = set()
    for f in texts:
        try:
            if f.stat().st_size > 8_000_000:
                continue
            found.update(m.split(".")[0] for m in NAME.findall(f.read_text(encoding="utf-8", errors="ignore")))
        except OSError:
            continue
    return found


def collect(root: Path, output: Path, now: float | None = None) -> dict[str, list[Path]]:
    """The files in each group, as they are now."""
    now = time.time() if now is None else now
    old_enough = lambda p: now - p.stat().st_mtime > DAY   # noqa: E731
    out: dict[str, list[Path]] = {k: [] for k in CATEGORIES}

    if output.is_dir():
        for job in output.iterdir():
            for work in job.glob("work*"):
                if work.is_dir():
                    out["work"] += list(_files(work))
    for top in (root / "songs", output):
        if top.is_dir():
            for base, dirs, names in os.walk(top):
                dirs[:] = [d for d in dirs if not d.startswith("work")]
                out["old"] += [Path(base) / n for n in names if BAK.search(n)]
    media = root / "media"
    if media.is_dir():
        for removed in media.glob("**/removed"):
            out["removed"] += list(_files(removed))

    cache = root / "cache"
    refs = _references(root, output)
    for key, folders in (("pictures", ("gen", "art")), ("footage", ("stock", "commons", "archives"))):
        for name in folders:
            if (cache / name).is_dir():
                out[key] += [f for f in _files(cache / name) if f.name.split(".")[0] not in refs and old_enough(f)]
    for name in ("preview", "filmstrip", "depth"):
        if (cache / name).is_dir():
            out["temp"] += [f for f in _files(cache / name) if old_enough(f)]
    return out


def _size(p: Path) -> int:
    try:
        return p.stat().st_size
    except OSError:
        return 0


def scan(root: Path, output: Path) -> list[dict]:
    """[{id, label, hint, cost, files, bytes, examples}] for every group that has something in it."""
    rows = []
    for key, files in collect(root, output).items():
        if not files:
            continue
        label, hint, cost = CATEGORIES[key]
        rows.append({"id": key, "label": label, "hint": hint, "cost": cost, "files": len(files),
                     "bytes": sum(_size(f) for f in files), "examples": [f.name for f in files[:3]]})
    return sorted(rows, key=lambda r: -r["bytes"])


def run(root: Path, output: Path, ids: list[str]) -> dict:
    """Delete the files of the groups in `ids` (found again now, so only these groups' files can go).
    Returns {freed, files, failed}; a file that is open elsewhere is skipped and counted in failed."""
    chosen = [i for i in ids if i in CATEGORIES]
    freed = files = failed = 0
    for key, found in collect(root, output).items():
        if key not in chosen:
            continue
        for f in found:
            size = _size(f)
            try:
                f.unlink()
                freed, files = freed + size, files + 1
            except OSError:
                failed += 1
    _prune(root, output, chosen)
    return {"freed": freed, "files": files, "failed": failed}


def _prune(root: Path, output: Path, chosen: list[str]) -> None:
    """Remove the empty folders a clean-up leaves (a job's work/, a media removed/)."""
    tops = []
    if "work" in chosen and output.is_dir():
        tops += [w for job in output.iterdir() for w in job.glob("work*") if w.is_dir()]
    if "removed" in chosen and (root / "media").is_dir():
        tops += list((root / "media").glob("**/removed"))
    for top in tops:
        for base, _, _ in os.walk(top, topdown=False):
            try:
                os.rmdir(base)   # only when empty
            except OSError:
                pass
