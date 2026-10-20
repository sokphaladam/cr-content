"""Read a long-form video script (.md) into the scene list the rest of Script to Video works from.

The script:
- the title on the first "# " line
- one or more markdown tables headed Time | Visual | On-screen Text | Voiceover (an Ep column is allowed, so the
  Excel Scripts sheet maps to the same rows): every such table, in order, is the script; other tables (an Overview
  ranking) are skipped by their header
- a packaging section, optional: **Thumbnail:**, **Title options** (a list), **Description ...** (paragraphs, with a
  "Chapters: 0:00 Intro · 0:45 Green heron" line) and **Shorts ...** (a list)

On-screen Text is shown without its quotes. A line like "#10 GREEN HERON" makes that scene a title card.
"""
import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path

from ..importer import detect_lang

COLUMNS = ("time", "visual", "onscreentext", "voiceover")
CLOCK = re.compile(r"(?<![\d:])(\d{1,2}(?::\d{2}){1,2})(?![\d:])")
RANK = re.compile(r"^#\s*(\d{1,3})\s*[:.\-–—]?\s+(.+)$")
QUOTES = "\"'“”‘’«»„"


@dataclass
class Scene:
    n: int              # 1-based, in script order (media/<script>/scene-XX.* goes by it)
    planned: float      # seconds, from the Time column
    visual: str
    text: str           # on-screen text, quotes stripped
    voiceover: str
    part: str = ""      # the "## ..." heading the scene's table sits under
    rank: int | None = None   # "#10 GREEN HERON": a title card
    name: str = ""            # ... and its name ("GREEN HERON")


@dataclass
class Chapter:
    planned: float
    title: str


@dataclass
class Script:
    title: str
    slug: str                     # the script's file name, for media/<slug>/
    lang: str
    scenes: list[Scene]
    title_options: list[str] = field(default_factory=list)
    description: str = ""
    chapters: list[Chapter] = field(default_factory=list)
    shorts: list[str] = field(default_factory=list)
    thumbnail: str = ""
    notes: list[str] = field(default_factory=list)  # what the parser had to guess or skip

    def to_json(self) -> dict:
        return asdict(self)

    def save(self, path: Path) -> None:
        path.write_text(json.dumps(self.to_json(), ensure_ascii=False, indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> "Script":
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        data["scenes"] = [Scene(**s) for s in data["scenes"]]
        data["chapters"] = [Chapter(**c) for c in data["chapters"]]
        return cls(**data)


def clock(text: str) -> float | None:
    """Seconds of the first m:ss or h:mm:ss in `text` (a range like "0:00–0:12" gives its start)."""
    m = CLOCK.search(text or "")
    if not m:
        return None
    secs = 0.0
    for part in m.group(1).split(":"):
        secs = secs * 60 + int(part)
    return secs


def stamp(seconds: float) -> str:
    """m:ss, or h:mm:ss from an hour: how YouTube reads chapter times."""
    s = int(round(seconds))
    h, m, s = s // 3600, s % 3600 // 60, s % 60
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def unquote(text: str) -> str:
    """On-screen text without the quotes around it (or around each of its parts)."""
    text = text.strip()
    while len(text) >= 2 and text[0] in QUOTES and text[-1] in QUOTES:
        text = text[1:-1].strip()
    return text


def _cells(line: str) -> list[str]:
    """A markdown table row's cells (a \\| inside a cell is a literal bar)."""
    row = line.strip().removeprefix("|").removesuffix("|")
    return [c.replace("\\|", "|").strip() for c in re.split(r"(?<!\\)\|", row)]


def _norm(header: str) -> str:
    return re.sub(r"[^a-z]", "", header.lower())


def _plain(text: str) -> str:
    """Markdown inline formatting removed (**bold**, *italic*, `code`, <br>)."""
    text = re.sub(r"<br\s*/?>", " ", text, flags=re.I)
    text = re.sub(r"(\*\*|__|\*|`)(.+?)\1", r"\2", text)
    return re.sub(r"\s{2,}", " ", text).strip()


def _tables(lines: list[str]) -> list[tuple[str, list[str], list[list[str]]]]:
    """Every table as (heading above it, header cells, rows)."""
    out, heading, i = [], "", 0
    while i < len(lines):
        line = lines[i].strip()
        if line.startswith("#"):
            heading = line.lstrip("#").strip()
        if line.startswith("|") and i + 1 < len(lines) and re.match(r"^\|?\s*:?-{2,}", lines[i + 1].strip()):
            head, rows = _cells(line), []
            i += 2
            while i < len(lines) and lines[i].strip().startswith("|"):
                rows.append(_cells(lines[i]))
                i += 1
            out.append((heading, head, rows))
            continue
        i += 1
    return out


def _script_columns(head: list[str]) -> dict[str, int] | None:
    """Where Time / Visual / On-screen Text / Voiceover are, if this is a script table."""
    names = [_norm(h) for h in head]
    found = {}
    for col in COLUMNS:
        hits = [k for k, n in enumerate(names) if n == col or (col == "voiceover" and n in ("vo", "narration"))]
        if not hits:
            return None
        found[col] = hits[0]
    return found


def _section(lines: list[str], label: str) -> list[str]:
    """The lines after a bold "**<label>...**" line, up to the next bold label or heading."""
    for i, line in enumerate(lines):
        if re.match(rf"^\*\*{label}", line.strip(), re.I):
            out = []
            for nxt in lines[i + 1:]:
                s = nxt.strip()
                if s.startswith("#") or re.match(r"^\*\*[^*]+\*\*\s*$", s):
                    break
                out.append(s)
            return out
    return []


def _items(block: list[str]) -> list[str]:
    """The entries of a markdown list."""
    return [_plain(re.sub(r"^(?:[-*+]|\d+[.)])\s+", "", s)) for s in block if re.match(r"^(?:[-*+]|\d+[.)])\s+", s)]


def chapters_from(line: str) -> list[Chapter]:
    """'Chapters: 0:00 Intro · 0:45 Green heron · ...' (or one per line) as planned chapters."""
    out = []
    for m in re.finditer(r"(\d{1,2}(?::\d{2}){1,2})\s+([^·•|\n]+?)(?=\s*(?:[·•|]|$|\d{1,2}:\d{2}\s))", line):
        out.append(Chapter(clock(m.group(1)), m.group(2).strip(" -–—,;")))
    return out


def parse(path: Path) -> Script:
    md = Path(path).read_text(encoding="utf-8-sig")
    lines = md.splitlines()
    notes: list[str] = []
    title = next((_plain(l[2:]) for l in lines if l.startswith("# ")), "") or Path(path).stem
    # "<Title> — Video Script": the document's name, not the video's
    title = re.sub(r"\s*[—–-]\s*(video\s+)?script\s*$", "", title, flags=re.I)

    scenes: list[Scene] = []
    for heading, head, rows in _tables(lines):
        cols = _script_columns(head)
        if cols is None:
            notes.append(f"skipped the table under \"{heading}\" (columns: {', '.join(head)})")
            continue
        for row in rows:
            cell = lambda c: row[cols[c]] if cols[c] < len(row) else ""
            planned = clock(cell("time"))
            vo, visual, text = _plain(cell("voiceover")), _plain(cell("visual")), unquote(_plain(cell("onscreentext")))
            if not (vo or visual or text):
                continue
            if planned is None:
                planned = scenes[-1].planned if scenes else 0.0
                notes.append(f"scene {len(scenes) + 1}: no time in \"{cell('time')}\"; placed after the one before")
            scene = Scene(len(scenes) + 1, planned, visual, text, vo, heading)
            if m := RANK.match(text):
                scene.rank, scene.name = int(m.group(1)), m.group(2).strip()
            scenes.append(scene)
    if not scenes:
        raise ValueError("No script table found: it needs the columns Time | Visual | On-screen Text | Voiceover.")
    for a, b in zip(scenes, scenes[1:]):
        if b.planned < a.planned:
            notes.append(f"scene {b.n} is timed {stamp(b.planned)}, before scene {a.n} ({stamp(a.planned)})")

    thumb = next((_plain(re.sub(r"^\*\*Thumbnail:?\*\*:?", "", l.strip(), flags=re.I))
                  for l in lines if re.match(r"^\*\*Thumbnail", l.strip(), re.I)), "")
    desc_block = _section(lines, "Description")
    chapter_lines = [s for s in desc_block if re.match(r"^chapters\s*:", s, re.I)]
    chapters = chapters_from(" ".join(re.sub(r"^chapters\s*:", "", s, flags=re.I) for s in chapter_lines))
    if not chapters:  # a "**Chapters**" block of its own, one per line
        chapters = chapters_from(" · ".join(_section(lines, "Chapters")))
    paragraphs = [s for s in desc_block if s and s not in chapter_lines]
    description = "\n\n".join(_plain(p) for p in paragraphs)

    return Script(title=title, slug=Path(path).stem, lang=detect_lang(" ".join(s.voiceover for s in scenes)),
                  scenes=scenes, title_options=_items(_section(lines, "Title options")), description=description,
                  chapters=chapters, shorts=_items(_section(lines, "Shorts")), thumbnail=thumb, notes=notes)
