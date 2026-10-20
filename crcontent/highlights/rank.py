"""Step 4 — candidate clips: 15–30 s windows cut on the music and the lyrics, ranked by the weighted scores.

A clip starts on a lyric line: on the bar line just before it (so a pickup into the line is kept), else the beat,
never inside the previous line's last word. It ends after a complete line, on the next beat after a short tail and
before the next line starts. So no clip ever cuts a word in half.
"""
import bisect
from dataclasses import asdict, dataclass, field

import numpy as np

from .lyrics_score import letters
from .settings import blend


@dataclass
class Candidate:
    start: float
    end: float
    first: int                       # index of its first and last lyric line
    last: int
    score: float = 0.0
    parts: dict = field(default_factory=dict)       # structure / lyrics / visual / hook 0..1 (+ details)
    section: str = ""                # the section it's mostly in ("Chorus")
    kind: str = ""                   # its kind ("chorus")
    hook_line: str = ""              # the line it opens on
    lyrics: list[str] = field(default_factory=list)
    starts_on: str = ""              # "bar", "beat" or "breath": what its start is snapped to
    ends_on: str = ""

    @property
    def length(self) -> float:
        return self.end - self.start

    def to_json(self) -> dict:
        d = asdict(self)
        d["length"] = round(self.length, 2)
        return d


def _latest(grid: list[float], lo: float, hi: float) -> float | None:
    i = bisect.bisect_right(grid, hi) - 1
    return grid[i] if i >= 0 and grid[i] >= lo else None


def _earliest(grid: list[float], lo: float, hi: float) -> float | None:
    i = bisect.bisect_left(grid, lo)
    return grid[i] if i < len(grid) and grid[i] <= hi else None


def snap_start(lines: list, i: int, beats: list[float], bars: list[float]) -> tuple[float, str]:
    """Where a clip opening on line i starts: the last bar line within a bar before the line (keeps a pickup),
    else the last beat within a beat before it, else a breath before it; never before the previous line ends."""
    line = lines[i]
    floor = lines[i - 1].end + 0.05 if i > 0 else 0.0
    beat = float(np.median(np.diff(beats))) if len(beats) > 1 else 0.5
    hi = line.start - 0.02
    t = _latest(bars, max(floor, line.start - 4 * beat), hi)
    if t is not None:
        return t, "bar"
    t = _latest(beats, max(floor, line.start - beat), hi)
    if t is not None:
        return t, "beat"
    return max(floor, line.start - 0.15, 0.0), "breath"


def snap_end(lines: list, j: int, beats: list[float], bars: list[float], tail: float, total: float) -> tuple[float, str]:
    """Where a clip ending on line j ends: the first bar line in the music after it (within a bar), else the first
    beat after a short tail, else the tail; always before the next line's first word."""
    line = lines[j]
    ceiling = (lines[j + 1].start - 0.05) if j + 1 < len(lines) else total
    beat = float(np.median(np.diff(beats))) if len(beats) > 1 else 0.5
    lo = line.end + min(tail, 0.25)
    t = _earliest(bars, lo, min(ceiling, line.end + 4 * beat))
    if t is not None:
        return t, "bar"
    t = _earliest(beats, line.end + tail * 0.5, min(ceiling, line.end + tail + beat))
    if t is not None:
        return t, "beat"
    return min(ceiling, line.end + tail, total), "breath"


def _mean(arr: list[float], a: float, b: float) -> float:
    """Mean of a per-second curve over [a, b), each second weighted by how much of it is inside."""
    total, weight = 0.0, 0.0
    for s in range(int(a), min(len(arr), int(np.ceil(b)))):
        w = max(0.0, min(b, s + 1) - max(a, s))
        total += arr[s] * w
        weight += w
    return total / weight if weight else 0.0


def candidates(lines: list, st, scores: dict[str, list[float]], lyric, cfg: dict) -> list[Candidate]:
    """Every clip that fits the length rules, scored (best first)."""
    c = cfg["clip"]
    lo, hi, ideal = c["min_seconds"], c["max_seconds"], c["ideal_seconds"]
    window = cfg["hook"]["window_seconds"]
    out = []
    for i in range(len(lines)):
        start, starts_on = snap_start(lines, i, st.beats, st.bars)
        for j in range(i, len(lines)):
            end, ends_on = snap_end(lines, j, st.beats, st.bars, c["tail_seconds"], st.duration)
            length = end - start
            if length > hi:
                break
            if length < lo:
                continue
            parts = {k: _mean(v, start, end) for k, v in scores.items()}
            # hook: the first seconds open on a strong line, or on a beat drop
            opening = [k for k in range(i, j + 1) if lines[k].start < start + window]
            line_hook = max((lyric.strength[k] for k in opening), default=0.0)
            drop_hook = max(st.per_second["drop"][int(start):int(start + window) + 1] or [0.0])
            parts["hook"] = blend({"line": line_hook, "drop": drop_hook}, cfg["hook"]["parts"])
            fit = 1 - 0.1 * min(1.0, abs(length - ideal) / max(1, hi - lo))
            sec = st.section_at((start + end) / 2) or {"name": "", "kind": ""}
            # the section it's mostly in, by time
            spans = {}
            for s in st.sections:
                spans[s["name"]] = spans.get(s["name"], 0) + max(0.0, min(end, s["end"]) - max(start, s["start"]))
            name = max(spans, key=spans.get) if spans else sec["name"]
            kind = next((s["kind"] for s in st.sections if s["name"] == name), sec["kind"])
            cand = Candidate(round(start, 3), round(end, 3), i, j, 0.0,
                             {**{k: round(v, 4) for k, v in parts.items()}, "fit": round(fit, 3),
                              "hook_line": round(line_hook, 3), "hook_drop": round(drop_hook, 3)},
                             name, kind, lines[i].text, [lines[k].text for k in range(i, j + 1)], starts_on, ends_on)
            cand.score = round(blend(parts, cfg["weights"]) * fit, 4)
            out.append(cand)
    return sorted(out, key=lambda x: -x.score)


def _overlap(a: Candidate, b: Candidate) -> bool:
    return a.start < b.end and b.start < a.end


def _shared(a: Candidate, b: Candidate) -> float:
    """Share of a's lyric lines that b sings too (a chorus and its repeat share nearly all)."""
    mine = [letters(t) for t in a.lyrics]
    theirs = {letters(t) for t in b.lyrics}
    return sum(t in theirs for t in mine) / len(mine) if mine else 0.0


def pick(cands: list[Candidate], count: int, diversity: float = 0.15) -> list[Candidate]:
    """The best `count` clips that don't overlap. A clip singing the same lines as one already picked (the chorus
    again) is marked down by `diversity` x the share of lines it repeats, so the picks differ when they can."""
    chosen: list[Candidate] = []
    pool = list(cands)
    while pool and len(chosen) < count:
        def adjusted(c: Candidate) -> float:
            return c.score * (1 - diversity * max((_shared(c, p) for p in chosen), default=0.0))
        best = max(pool, key=adjusted)
        best.parts["repeat_penalty"] = round(1 - adjusted(best) / best.score, 3) if best.score else 0.0
        chosen.append(best)
        pool = [c for c in pool if not _overlap(c, best)]
    return chosen
