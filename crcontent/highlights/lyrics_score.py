"""Step 2 — lyrics: how strong each sung line is as a hook, scored per second of the video.

The word timing comes from source.py (lyrics.json, or a forced alignment of the given lyrics). A line is strong when
it's sung again and again (the most repeated lines are what people remember) and when it carries the song's title.
"""
import math
import re
import unicodedata
from dataclasses import dataclass, field

from .settings import blend


def letters(text: str) -> str:
    """Only the letters and digits, lower case: compares lines whatever the punctuation, spacing or script (Khmer is
    written without spaces between words, so titles are found as a run of letters, not as words)."""
    return "".join(c for c in unicodedata.normalize("NFC", text.lower())
                   if unicodedata.category(c)[0] in "LMN")


def _words(text: str) -> list[str]:
    return [w for w in (letters(t) for t in re.split(r"\s+", text)) if w]


def _alike(a: str, b: str) -> bool:
    """Same line, or nearly (one word changed: "I keep watching it again" / "I'm still watching one more time" aren't;
    "Replay, replay" / "Replay... replay..." are)."""
    if letters(a) == letters(b):
        return True
    wa, wb = set(_words(a)), set(_words(b))
    return bool(wa and wb) and len(wa & wb) / len(wa | wb) >= 0.75


@dataclass
class LyricScores:
    strength: list[float]                  # per line (same order as the lines), 0..1
    parts: list[dict]                      # per line: {"repeat", "title"} 0..1, and "count" (times sung)
    per_second: dict[str, list[float]] = field(default_factory=dict)  # repeat / title / density, 0..1


def analyze(lines: list, title: str, total: float, cfg: dict) -> LyricScores:
    n = max(1, math.ceil(total))
    if not lines:
        return LyricScores([], [], {k: [0.0] * n for k in ("repeat", "title", "density")})
    counts = [sum(_alike(l.text, o.text) for o in lines) for l in lines]
    most = max(counts)
    name = letters(title)
    name_words = _words(title)
    parts = []
    for line, count in zip(lines, counts):
        text = letters(line.text)
        if name and name in text:
            has_title = 1.0
        else:  # part of a longer title ("Summer in Phnom Penh"): the share of its words sung in this line
            mine = set(_words(line.text))
            has_title = 0.6 * sum(w in mine for w in name_words) / len(name_words) if name_words else 0.0
        parts.append({"repeat": (count - 1) / (most - 1) if most > 1 else 0.0, "title": has_title, "count": count})
    w = {k: v for k, v in cfg["lyrics"]["parts"].items() if k != "density"}
    strength = [blend(p, w) for p in parts]

    # per second: the line being sung (the stronger one where two overlap), and how much of the second is sung
    repeat, has_title, density = [0.0] * n, [0.0] * n, [0.0] * n
    for line, p in zip(lines, parts):
        for word in line.words:
            for s in range(max(0, int(word.start)), min(n, int(math.ceil(word.end)))):
                density[s] += max(0.0, min(word.end, s + 1) - max(word.start, s))
        # the line's score covers it from its first word to its last, plus the breath after
        for s in range(max(0, int(line.start)), min(n, int(math.ceil(line.end + 0.5)))):
            repeat[s] = max(repeat[s], p["repeat"])
            has_title[s] = max(has_title[s], p["title"])
    density = [min(1.0, d / 0.6) for d in density]  # ~60% of a second sung counts as fully sung
    return LyricScores(strength, parts, {"repeat": repeat, "title": has_title, "density": density})


def score(ls: LyricScores, cfg: dict) -> list[float]:
    w = cfg["lyrics"]["parts"]
    n = len(ls.per_second["repeat"])
    return [blend({k: ls.per_second[k][t] for k in w}, w) for t in range(n)]
