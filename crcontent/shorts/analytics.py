"""The feedback loop: which hooks keep viewers, from YouTube Studio's own numbers.

Import the Studio "Content" export (Analytics -> Advanced mode -> Export -> CSV; the "Table data.csv" inside the zip,
or the CSV itself): one row per video with Video title, Duration, Views, Average percentage viewed (%) and Stayed to
watch (%). Columns are found by their names, the "Total" row is skipped.

Each video is matched to an episode of a content plan by title (the plan's new and old titles; emoji, hashtags and
punctuation ignored) and tagged:
- hook style (HOOK_STYLES): Claude reads the title (and the matched episode's first line), with keyword rules as
  the fallback ("your cat" -> "your cat + hidden meaning", ...)
- length: a bucket from Duration
- animal / topic
The summary averages Stayed to watch % and % viewed per tag (weighted by views, so one tiny video can't top the
table) and is saved to <data folder>/shorts-analytics.json, where the pre-flight judge reads it to rank its hook
suggestions.
"""
import csv
import difflib
import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path

from ..config import CLAUDE_MODEL, ROOT
from ..importer import strip_emoji

PATH = ROOT / "shorts-analytics.json"
HOOK_STYLES = ("your cat + hidden meaning", "shock fact", "science explainer", "question", "myth bust",
               "pov / situation", "list / ranking", "other")
LENGTHS = ((20, "under 20s"), (30, "20-30s"), (45, "30-45s"), (60, "45-60s"), (10 ** 9, "over 60s"))
MATCH_MIN = 0.72  # title similarity (0-1) needed to call a video an episode

TAG_SCHEMA = {
    "type": "object",
    "properties": {"videos": {"type": "array", "items": {
        "type": "object",
        "properties": {"n": {"type": "integer"}, "hook_style": {"type": "string", "enum": list(HOOK_STYLES)},
                       "animal": {"type": "string"}},
        "required": ["n", "hook_style", "animal"],
        "additionalProperties": False,
    }}},
    "required": ["videos"],
    "additionalProperties": False,
}


@dataclass
class Video:
    title: str
    seconds: float
    views: int
    viewed: float | None      # Average percentage viewed (%)
    stayed: float | None      # Stayed to watch (%)
    ep: int | None = None
    match: float = 0.0
    hook_style: str = ""
    length: str = ""
    animal: str = ""
    first_line: str = ""      # the matched episode's first voiceover line (helps tag the hook)
    extra: dict = field(default_factory=dict)


def norm_title(title: str) -> str:
    """A title as words only: no emoji, hashtags, punctuation or case."""
    t = re.sub(r"#\w+", " ", strip_emoji(title or "")).lower()
    return " ".join(re.findall(r"[\w']+", t)).replace("'", "")


def _num(value: str) -> float | None:
    v = (value or "").strip().replace(",", "").rstrip("%")
    try:
        return float(v)
    except ValueError:
        return None


def _seconds(value: str) -> float:
    """Duration as Studio writes it: seconds ("28"), or m:ss / h:mm:ss."""
    v = (value or "").strip()
    if ":" in v:
        secs = 0.0
        for part in v.split(":"):
            secs = secs * 60 + float(part or 0)
        return secs
    return _num(v) or 0.0


def _column(heads: list[str], *names: str) -> str | None:
    low = {h: re.sub(r"[^a-z%]", "", h.lower()) for h in heads}
    for n in names:
        key = re.sub(r"[^a-z%]", "", n.lower())
        for h, k in low.items():
            if k.startswith(key):
                return h
    return None


def read_csv(path: Path) -> list[Video]:
    with open(path, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        return []
    heads = list(rows[0])
    title = _column(heads, "Video title", "Title")
    if not title:
        raise ValueError(f"{Path(path).name}: no 'Video title' column (columns: {', '.join(heads)})")
    dur, views = _column(heads, "Duration"), _column(heads, "Views")
    viewed = _column(heads, "Average percentage viewed")
    stayed = _column(heads, "Stayed to watch")
    out = []
    for r in rows:
        name = (r.get(title) or "").strip()
        if not name or name.lower() == "total" or (r.get(heads[0]) or "").strip().lower() == "total":
            continue
        out.append(Video(name, _seconds(r.get(dur, "")) if dur else 0.0, int(_num(r.get(views, "")) or 0)
                         if views else 0, _num(r.get(viewed, "")) if viewed else None,
                         _num(r.get(stayed, "")) if stayed else None))
    return out


def match(videos: list[Video], episodes: list) -> None:
    """Each video's episode: the plan title (new or old) closest to its title, when close enough."""
    titles = [(e, norm_title(t)) for e in episodes for t in (e.title, e.old_title) if t]
    for v in videos:
        name = norm_title(v.title)
        best = max(((difflib.SequenceMatcher(None, name, t).ratio(), e) for e, t in titles),
                   key=lambda p: p[0], default=(0.0, None))
        if best[1] is not None and best[0] >= MATCH_MIN:
            v.ep, v.match = best[1].ep, round(best[0], 3)
            v.first_line = best[1].script.scenes[0].voiceover if best[1].script.scenes else ""
            v.animal = v.animal or best[1].animal


def length_bucket(seconds: float) -> str:
    return next(label for top, label in LENGTHS if seconds < top) if seconds else ""


def rule_style(title: str, first_line: str = "") -> str:
    """The hook style from keywords alone (no Claude)."""
    t = f"{title} {first_line}".lower()
    if re.search(r"\byour (cat|kitten)\b", t):
        return "your cat + hidden meaning"
    if re.search(r"\b(myth|actually|not what you think|wrong)\b", t):
        return "myth bust"
    if re.search(r"\b(pov|when you|when your)\b", t):
        return "pov / situation"
    if re.search(r"\b(top \d+|\d+ (animals|things|facts))\b", t):
        return "list / ranking"
    if re.search(r"\b(why|how|science|scientists?|explained)\b", t):
        return "science explainer"
    if re.search(r"\b(dies|boils|survived|poops|regrows|deadly|fastest|never|only)\b", t) or \
            re.search(r"\b[A-Z]{4,}\b", f"{title}"):
        return "shock fact"
    return "question" if "?" in title else "other"


def tag(videos: list[Video], log=print) -> None:
    """hook_style, length and animal for every video: Claude in one call, keyword rules without it."""
    for v in videos:
        v.length = length_bucket(v.seconds)
    try:
        from ..script import make_client

        listing = "\n".join(f"{k}. {v.title}" + (f"  (first line: {v.first_line})" if v.first_line else "")
                            for k, v in enumerate(videos, 1))
        response = make_client().beta.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=8000,
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
            output_config={"effort": "low", "format": {"type": "json_schema", "schema": TAG_SCHEMA}},
            messages=[{"role": "user", "content": (
                "These are YouTube Shorts from an animal-facts channel. Tag each one's hook style (how the title and "
                "first line grab a viewer) and its animal or topic (a short common name, e.g. \"cat\", "
                "\"hummingbird\").\nHook styles:\n- your cat + hidden meaning: talks to the viewer about their own "
                "pet and what its behaviour secretly means (\"Your cat brought you a dead mouse?\")\n- shock fact: "
                "one surprising claim up front (\"This bird almost dies every night\")\n- science explainer: explains "
                "how or why something works (\"Why cats purr, explained\")\n- question: a plain question\n- myth "
                "bust: corrects a common belief\n- pov / situation: puts the viewer in a scene\n- list / ranking: "
                "a numbered list\n- other\n\n" + listing)}],
        )
        got = {t["n"]: t for t in json.loads(next(b.text for b in response.content if b.type == "text"))["videos"]}
        for k, v in enumerate(videos, 1):
            if k in got:
                v.hook_style = got[k]["hook_style"]
                v.animal = v.animal or got[k]["animal"].strip().lower()
    except Exception as e:
        log(f"  ! couldn't tag with Claude ({type(e).__name__}); hook styles from keywords")
    for v in videos:
        v.hook_style = v.hook_style or rule_style(v.title, v.first_line)
        v.animal = (v.animal or "").split(":")[0].strip().lower()


def _avg(vals: list[tuple[float | None, int]]) -> float | None:
    """Views-weighted mean of the known values (plain mean when no video has views)."""
    known = [(x, w) for x, w in vals if x is not None]
    if not known:
        return None
    total = sum(w for _, w in known)
    return round(sum(x * w for x, w in known) / total if total else sum(x for x, _ in known) / len(known), 1)


def summary(videos: list[Video]) -> dict:
    """{dimension: [{tag, videos, views, stayed, viewed}] best Stayed to watch first} for hook_style, length,
    animal."""
    out = {}
    for dim in ("hook_style", "length", "animal"):
        groups: dict[str, list[Video]] = {}
        for v in videos:
            if getattr(v, dim):
                groups.setdefault(getattr(v, dim), []).append(v)
        rows = [{"tag": t, "videos": len(vs), "views": sum(v.views for v in vs),
                 "stayed": _avg([(v.stayed, v.views) for v in vs]),
                 "viewed": _avg([(v.viewed, v.views) for v in vs])} for t, vs in groups.items()]
        out[dim] = sorted(rows, key=lambda r: (r["stayed"] is None, -(r["stayed"] or 0), -(r["viewed"] or 0)))
    return out


def import_csv(path: Path, episodes: list = (), log=print) -> dict:
    """Read, match, tag and summarise a Studio export; saved to PATH for the judge. Returns what was saved."""
    videos = read_csv(Path(path))
    if not videos:
        raise ValueError(f"{Path(path).name}: no videos in it")
    match(videos, list(episodes))
    tag(videos, log)
    data = {"source": str(path), "videos": [asdict(v) for v in videos], "summary": summary(videos)}
    PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return data


def load() -> dict | None:
    try:
        return json.loads(PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def style_stats(data: dict | None = None) -> dict[str, dict]:
    """{hook style: {stayed, viewed, videos}} from the last import (empty without one)."""
    data = data if data is not None else load()
    return {r["tag"]: r for r in (data or {}).get("summary", {}).get("hook_style", [])}


def report(data: dict) -> str:
    """The summary as text tables."""
    lines = []
    matched = sum(1 for v in data["videos"] if v["ep"] is not None)
    lines.append(f"{len(data['videos'])} videos, {matched} matched to an episode")
    for dim, label in (("hook_style", "Hook style"), ("length", "Length"), ("animal", "Animal / topic")):
        lines.append(f"\n{label:<28} {'videos':>6} {'views':>8} {'stayed %':>9} {'viewed %':>9}")
        for r in data["summary"][dim]:
            f = lambda x: "-" if x is None else f"{x:.1f}"
            lines.append(f"{r['tag'][:28]:<28} {r['videos']:>6} {r['views']:>8} {f(r['stayed']):>9} "
                         f"{f(r['viewed']):>9}")
    return "\n".join(lines)
