"""Read a Shorts content plan (.xlsx) into one ShortPlan per episode.

The workbook (sheets are found by their header row, as in sheet.py; extra columns are ignored):
- Scripts: Ep | Time | Visual | On-screen Text | Voiceover, one row per beat. A row whose Time is "TITLE" holds the
  episode's title in its Visual (or On-screen Text) cell and is not a beat.
- Plan (optional): Ep | ... | Old title | New title | Hook (first 2s) | Description + hashtags | Pinned comment

The title is the Plan's New title, else its Old title, else the TITLE row. Hashtags never stay in the title (they hurt
Shorts titles): they move to the description's hashtags. The voiceover is spoken word for word, without "(sound
cues)" and the "[loops]" / "[loops to start]" marker; the marker records that the last line is meant to run back into
the first one (rule 3), which preflight checks.
"""
import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path

import openpyxl

from ..importer import detect_lang
from ..longform.parse import Scene, Script, unquote
from ..sheet import CUE, SPAN, _get, _table

LOOP_MARK = re.compile(r"\[\s*loops?\b[^\]]*\]", re.I)  # "[loops]", "[loops to start]"
HASHTAG = re.compile(r"(?<![\w&])#(\w+)")


@dataclass
class ShortPlan:
    ep: int
    title: str                  # what goes up as the title: no hashtags (emoji kept)
    script: Script              # the beats, as Script to Video's scenes (scene 1 = the hook beat)
    description: str = ""       # the description without its hashtags
    hashtags: list[str] = field(default_factory=list)  # without "#", in order, no repeats
    pinned_comment: str = ""
    hook_idea: str = ""         # the Plan's "Hook (first 2s)": what the opening is meant to show
    old_title: str = ""         # the title it was posted under before (matched against the Studio export)
    loop_marked: bool = False   # the last line carries a [loops] marker
    planned_ends: list[float] = field(default_factory=list)  # each beat's planned end (the sheet's Time span)
    status: str = ""            # for sheet.pick_episodes ("Posted" rows are skipped by default)
    animal: str = ""            # the episode's animal, as footage is judged ("domestic house cat"); footage.py
    animal_search: str = ""     # ... and as stock libraries tag it ("cat")
    animal_tags: list[str] = field(default_factory=list)  # every tag word it goes by ("cat", "cats", "kitten")
    notes: list[str] = field(default_factory=list)  # what the parser fixed or had to guess

    def to_json(self) -> dict:
        return {**asdict(self), "script": self.script.to_json()}

    def save(self, path: Path) -> None:
        path.write_text(json.dumps(self.to_json(), ensure_ascii=False, indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> "ShortPlan":
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        scenes = [Scene(**s) for s in data["script"].pop("scenes")]
        data["script"] = Script(**{**data["script"], "scenes": scenes, "chapters": []})
        return cls(**data)


def split_hashtags(text: str) -> tuple[str, list[str]]:
    """`text` without its #hashtags (lines left empty dropped), and the tags in order without repeats."""
    tags = list(dict.fromkeys(HASHTAG.findall(text or "")))
    rest = "\n".join(re.sub(r"\s{2,}", " ", HASHTAG.sub("", line)).strip() for line in (text or "").splitlines())
    return re.sub(r"\n{3,}", "\n\n", rest).strip(), tags


def spoken(voiceover: str) -> tuple[str, bool]:
    """What the voice says (no sound cues, no loop marker), and whether the line carried a loop marker."""
    looped = bool(LOOP_MARK.search(voiceover))
    text = CUE.sub("", LOOP_MARK.sub("", voiceover))
    return re.sub(r"\s{2,}", " ", text).strip(), looped


def _span(time: str) -> tuple[float, float] | None:
    m = SPAN.search(time or "")
    return (float(m.group(1)), float(m.group(2))) if m else None


def read(path: Path) -> list[ShortPlan]:
    path = Path(path)
    wb = openpyxl.load_workbook(path, data_only=True, read_only=True)
    tables = [_table(ws) for ws in wb.worksheets]
    wb.close()

    def find(*cols: str) -> list[dict]:
        for rows in tables:
            if rows and all(any(k.startswith(c) for k in rows[0]) for c in cols):
                return rows
        return []

    scripts = find("voiceover") or find("narration")
    if not scripts:
        raise ValueError(f"{path.name}: no sheet with a header row 'Ep | Time | Visual | On-screen Text | Voiceover'.")
    plan = find("newtitle") or find("oldtitle") or find("title", "description") or find("hook")
    stem = re.sub(r"[^a-z0-9]+", "-", path.stem.lower()).strip("-") or "shorts"

    out: list[ShortPlan] = []
    for ep in dict.fromkeys(int(r["ep"]) for r in scripts):
        rows = [r for r in scripts if int(r["ep"]) == ep]
        info = next((r for r in plan if int(r["ep"]) == ep), {})
        notes: list[str] = []
        title_row = ""
        scenes: list[Scene] = []
        ends: list[float] = []
        marked_at: list[int] = []
        for r in rows:
            time = _get(r, "time")
            if time.strip().upper() == "TITLE":
                title_row = _get(r, "visual") or _get(r, "onscreen") or _get(r, "voiceover")
                continue
            vo, marked = spoken(_get(r, "voiceover", "narration"))
            visual, text = _get(r, "visual"), unquote(_get(r, "onscreen", "text"))
            if not (vo or visual or text):
                continue
            if marked:
                marked_at.append(len(scenes) + 1)
            span = _span(time)
            if span is None:
                start = ends[-1] if ends else 0.0
                span = (start, start + 3.0)
                notes.append(f"beat {len(scenes) + 1}: no time span in \"{time}\"; planned as 3 s after the one before")
            scenes.append(Scene(len(scenes) + 1, span[0], visual, text, vo))
            ends.append(span[1])
        if not scenes:
            continue
        early = [n for n in marked_at if n != len(scenes)]
        if early:
            notes.append(f"beat {', '.join(map(str, early))} has a loop marker but isn't the last beat")

        title = _get(info, "newtitle") or _get(info, "oldtitle") or _get(info, "title") or title_row
        if not title:
            title = f"Episode {ep}"
            notes.append("no title in the Plan sheet or a TITLE row")
        clean_title, title_tags = split_hashtags(title)
        if title_tags:
            notes.append(f"moved {' '.join('#' + t for t in title_tags)} from the title to the description")
        description, tags = split_hashtags(_get(info, "description"))
        hashtags = list(dict.fromkeys([*tags, *title_tags]))
        lang = detect_lang(" ".join(s.voiceover for s in scenes))
        out.append(ShortPlan(
            ep=ep, title=clean_title, description=description, hashtags=hashtags,
            pinned_comment=_get(info, "pinnedcomment", "comment"), hook_idea=_get(info, "hook"),
            old_title=split_hashtags(_get(info, "oldtitle"))[0], loop_marked=len(scenes) in marked_at, planned_ends=ends,
            status=_get(info, "status"), notes=notes,
            script=Script(title=clean_title, slug=f"{stem}-ep{ep:02d}", lang=lang, scenes=scenes),
        ))
    return out
