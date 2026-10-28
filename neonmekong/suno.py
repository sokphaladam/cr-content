"""Parse the text pasted from Suno (suno.txt).

Accepted layout (header lines optional, any order, before the first [Tag]):
    Title: Slow Motion City
    Style: nu-disco, dreamy, female vocal
    Plan: Premier
    Generated: 2026-10-01
    [Verse 1]
    lyric line ...
Without a "Title:" line the first non-empty header line is the title.
"""
import re
from dataclasses import dataclass, field

TAG = re.compile(r"^\[(.+?)\]\s*$")
HEADER = re.compile(r"^(title|style|plan|generated|generated_on)\s*:\s*(.+)$", re.I)
# Words that identify a section tag when they are among its first two words, checked in order ("pre-chorus" before
# "chorus"; "Final Chorus" is a chorus; "[Drums drop out]" is a sound note, not a section).
WORDS = (("pre-chorus", "pre-chorus"), ("prechorus", "pre-chorus"), ("pre chorus", "pre-chorus"), ("chorus", "chorus"),
         ("verse", "verse"), ("bridge", "bridge"), ("intro", "intro"), ("outro", "outro"), ("hook", "hook"),
         ("instrumental", "instrumental"), ("solo", "instrumental"), ("break", "instrumental"),
         ("interlude", "interlude"))


@dataclass
class Section:
    tag: str            # as written, e.g. "Verse 1"
    kind: str           # normalized: verse / chorus / bridge ...
    lines: list[str] = field(default_factory=list)


@dataclass
class Suno:
    title: str = ""
    style: str = ""
    plan: str = ""
    generated_on: str = ""
    sections: list[Section] = field(default_factory=list)

    def lyric_lines(self) -> list[tuple[str, str]]:
        """[(kind, line)] for every sung line, in song order."""
        return [(s.kind, ln) for s in self.sections for ln in s.lines]


def kind_of(tag: str) -> str:
    """Normalize a tag; sound notes like "Soft synth swell" or "Drums get fuller" become "note"."""
    t = tag.lower().strip()
    if len(t.split()) > 3 or "," in t:   # a description, not a section name ("Soaring synth solo, pulsing bass")
        return "note"
    head = " ".join(t.split()[:2])
    return next((kind for word, kind in WORDS if word in head), "note")


def parse(text: str) -> Suno:
    out = Suno()
    loose: list[str] = []
    cur: Section | None = None
    for raw in text.lstrip("﻿").splitlines():
        line = raw.strip()
        if not line:
            continue
        m = TAG.match(line)
        if m:
            kind = kind_of(m.group(1))
            if kind != "note":   # sound notes ([Drums drop out]) never start a section or take lyrics
                cur = Section(m.group(1).strip(), kind)
                out.sections.append(cur)
            continue
        if cur is None:  # still in the header
            h = HEADER.match(line)
            if h:
                key = h.group(1).lower()
                setattr(out, "generated_on" if key.startswith("generated") else key, h.group(2).strip())
            else:
                loose.append(line)
            continue
        cur.lines.append(line)
    if not out.title and loose:
        out.title = loose.pop(0)
    if not out.style and loose:
        out.style = " ".join(loose)
    return out
