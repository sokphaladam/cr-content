"""song.json: filled in by the analyzer, then edited by you before rendering. Existing files are never overwritten."""
import json
import re
import shutil
import time
from pathlib import Path

from . import config
from .suno import Suno

FIELDS = {
    "title": "", "slug": "", "genre": "", "mood_phrase": "", "scene_theme": "", "style_prompt": "",
    "bpm": None, "beat_times": [], "chorus": {"start": None, "end": None}, "sections": [],
    "palette": [], "subscribe_line": "", "plan": "", "generated_on": "", "playlist": "",
    "vocal_start": None, "audio": "", "lyric_style": "", "mood_grade": "", "beat_pulse": "", "pulse_parts": "", "pulse_when": "", "neon_intro": "", "now_playing": "",
}


def slugify(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")


def genre_of(style: str) -> str:
    s = style.lower()
    for key in ("nu-disco", "psych-pop", "psych-rock"):
        if key in s or key.replace("-", " ") in s:
            return key
    if "psychedelic" in s or "psych" in s:   # "Psychedelic synth-pop" -> psych-pop, "psychedelic rock" -> psych-rock
        return "psych-rock" if "rock" in s else "psych-pop"
    if "nu disco" in s or "nudisco" in s:
        return "nu-disco"
    return "late-night" if any(w in s for w in ("late night", "late-night", "3am")) else ""


def from_suno(s: Suno, slug: str = "") -> dict:
    data = json.loads(json.dumps(FIELDS))  # deep copy
    genre = genre_of(s.style)
    data.update(title=s.title, slug=slug or slugify(s.title), style_prompt=s.style, genre=genre,
                playlist=config.PLAYLISTS.get(genre, ""), plan=s.plan, generated_on=s.generated_on,
                sections=[{"tag": x.tag, "kind": x.kind, "lines": len(x.lines)} for x in s.sections])
    return data


def warnings(data: dict) -> list[str]:
    out = []
    if data.get("plan") not in config.PLANS:
        out.append("plan is missing or not Pro/Premier: only songs made on a paid Suno plan can be monetized")
    if not data.get("generated_on"):
        out.append("generated_on is missing: add the date the song was made on Suno")
    if not data.get("genre"):
        out.append("genre not recognised from the style prompt: set it in song.json "
                   "(nu-disco, psych-pop, psych-rock, late-night)")
    return out


def backup(path: Path) -> Path | None:
    if not path.exists():
        return None
    dest = path.with_name(f"{path.name}.bak-{time.strftime('%Y%m%d-%H%M%S')}")
    shutil.copy2(path, dest)
    return dest


def move_aside(path: Path) -> Path | None:
    """Rename a finished file to <name>.bak-<time> (large videos: no copy). On Windows the rename fails while a player
    or the browser still has the file open, so retry for a few seconds, then say what to close."""
    if not path.exists():
        return None
    dest = path.with_name(f"{path.name}.bak-{time.strftime('%Y%m%d-%H%M%S')}")
    for attempt in range(10):
        try:
            path.rename(dest)
            return dest
        except PermissionError:
            if attempt == 9:
                raise PermissionError(f"{path.name} is open in another program (a video player, or the preview in "
                                      "the browser). Close it and render again.") from None
            time.sleep(0.5)


def save(path: Path, data: dict, force: bool = False) -> Path | None:
    """Write song.json. Refuses to touch an existing file unless force; then the old one is backed up first."""
    if path.exists() and not force:
        raise FileExistsError(f"{path} exists (use --force to replace it; a backup is kept)")
    kept = backup(path)
    data = {k: v for k, v in data.items() if not k.startswith("_")}  # "_dir" is only for this run
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return kept


def load(path: Path) -> dict:
    return {**FIELDS, **json.loads(path.read_text(encoding="utf-8")), "_dir": str(path.parent)}
