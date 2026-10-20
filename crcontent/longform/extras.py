"""What goes with the video: captions.srt, description.txt with chapters at their real times, credits.txt listing
every stock clip/photo and music track with its licence, plus the app's own post.txt, thumbnail and meta.json."""
import json
import re
from pathlib import Path

from ..music import credit as music_credit
from .parse import Script, stamp

SOURCES = {"pexels": "Pexels", "pixabay": "Pixabay", "commons": "Wikimedia Commons", "inaturalist": "iNaturalist",
           "met": "The Metropolitan Museum of Art", "nasa": "NASA", "archive": "the Internet Archive"}
MADE = {"own": "your own media", "placeholder": "placeholder card (made by the app)",
        "card": "graphic card (made by the app)", "montage": "montage of the video's other scenes"}
from .timing import Timeline


def credits(script: Script, entries: list[dict], music: list[str]) -> str:
    """Every downloaded file by scene: source page, author, licence. Your own files and placeholders are listed too,
    so nothing in the video is unaccounted for."""
    lines = [f"Credits: {script.title}", "", "FOOTAGE AND PHOTOS (by scene)"]
    for e in entries:
        c = e["chosen"]
        what = MADE.get(c["source"])
        if what:
            lines.append(f"Scene {e['scene']:02d}: {what} ({Path(c['file']).name})")
            continue
        name = SOURCES.get(c["source"], c["source"])
        lines.append(f"Scene {e['scene']:02d}: {c['kind']} by {c.get('author') or 'unknown'} on {name}, {c['licence']}"
                     + (f" ({c['licence_url']})" if c.get("licence_url") and c["licence_url"] != c.get("page") else "")
                     + f"\n          {c.get('page') or c.get('url', '')}")
    lines += ["", "MUSIC"]
    for t in music:
        lines.append(f"{Path(t).name}: {music_credit(t) or 'your own track (you hold the rights)'}")
    if not music:
        lines.append("none")
    lines += ["", "Voiceover: synthesized per scene (see longform.json, voice.engine).", ""]
    return "\n".join(lines)


def _attributions(entries: list[dict]) -> list[str]:
    """Credit lines the description must carry: Wikimedia and iNaturalist photos (CC BY / BY-SA need the author and
    licence named), and a line for the public-domain archives (not required, but it's how they ask to be cited).
    Pexels and Pixabay don't require credit; they're thanked in one line."""
    out = []
    for e in entries:
        c = e["chosen"]
        if c["source"] in ("commons", "inaturalist"):
            line = (f"Photo: {c.get('author') or 'unknown'}, {c['licence']}, via {SOURCES[c['source']]} "
                    f"({c.get('page', '')})")
            if line not in out:
                out.append(line)
    archive = [SOURCES[s] for s in ("archive", "nasa", "met") if any(e["chosen"]["source"] == s for e in entries)]
    if archive:
        out.append(f"Archive footage and images: {', '.join(archive)} (public domain).")
    stock = sorted({ {"pexels": "Pexels", "pixabay": "Pixabay"}[e["chosen"]["source"]]
                     for e in entries if e["chosen"]["source"] in ("pexels", "pixabay")})
    if stock:
        out.append(f"Stock footage: {' and '.join(stock)}.")
    return out


def description(script: Script, tl: Timeline, entries: list[dict], music: list[str]) -> str:
    chapters = "\n".join(f"{stamp(c['at'])} {c['title']}" for c in tl.chapters)
    parts = [script.description or script.title, "Chapters:\n" + chapters]
    music_lines = [c for c in (music_credit(t) for t in music) if c]
    credit_lines = _attributions(entries) + music_lines
    if credit_lines:
        parts.append("Credits:\n" + "\n".join(credit_lines))
    return "\n\n".join(parts) + "\n"


def thumbnail_text(script: Script) -> str:
    """The cover's words: the last short quoted phrase in the script's Thumbnail note ("SMARTER THAN APES?"), else
    the title."""
    quoted = [q for q in re.findall(r"[\"“]([^\"”]{2,40})[\"”]", script.thumbnail) if len(q.split()) <= 4]
    return quoted[-1] if quoted else script.title


def write(job: Path, script: Script, tl: Timeline, entries: list[dict], made: dict, log=print) -> None:
    from ..pipeline import make_thumbnail
    from .video import srt

    (job / "captions.srt").write_text(srt(made["cues"]), encoding="utf-8")
    desc = description(script, tl, entries, made["music"])
    (job / "description.txt").write_text(desc, encoding="utf-8")
    (job / "credits.txt").write_text(credits(script, entries, made["music"]), encoding="utf-8")
    title = script.title_options[0] if script.title_options else script.title
    (job / "post.txt").write_text(f"{title}\n\n{desc.strip()}\n", encoding="utf-8")
    log(f"      captions.srt ({len(made['cues'])} cues), description.txt ({len(tl.chapters)} chapters), credits.txt")

    meta_path = job / "meta.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    meta.update(aspect="16:9", title=title, duration=round(tl.total, 2), encoder=made["encoder"],
                music=", ".join(Path(t).name for t in made["music"]))
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    # the cover: the frame a moment into the #1 title card's scene (the payoff), with the Thumbnail note's words
    top = next((s for s, sc in zip(tl.slots, script.scenes) if sc.rank == 1), None)
    at = (top.start + min(top.length * 0.6, 3.0)) if top else tl.total * 0.1
    try:
        make_thumbnail(job, thumbnail_text(script), at, script.lang)
        log(f"      thumbnail.jpg: \"{thumbnail_text(script)}\" at {stamp(at)}")
    except Exception as e:  # the video is done either way; the cover can be redone in the app
        log(f"      ! couldn't draw the thumbnail ({type(e).__name__}: {str(e)[:120]})")
