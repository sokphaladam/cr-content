"""Motion graphics for a Short: animated shapes in the text layer (ASS vector drawings, burned in with the captions).

Same design language as the lyric video's (neonmekong/graphics.py), so a channel's Shorts and long videos look like
one kit: thin strokes, one accent colour plus soft white at low opacity, eased motion, a touch of blur for glow, and
motion only on the cuts. They sit under the captions (layer 0) and inside the safe zone (captions.TOP / BOTTOM /
RIGHT): nothing in the app's header, the bottom 20% or the right 15%.

- progress   a hairline under the app header that fills over the whole Short, with a small bright head
- burst      two thin rings that ease outward from the picture on every cut
- sweep      a faint soft streak of light that crosses the picture on every cut
- brackets   an inset hairline frame with accent corners that fade in and breathe
The attention traps (story devices, not decoration):
- facts      a number the voice says ("400 years") slams on screen, counting up to it
  (facts_remotion: the same moments drawn by Remotion, remotion/src/Fact.tsx, and laid over the picture: motion.py)
Drawn by Remotion only (motion.py): size_compare (a length the voice says, the animal next to a person) and map_zoom
(the place the voice names, on a globe that dives in).
- teaser     an open loop: "wait for the end" over the hook beat, closed by "here it is" when the last beat starts
- chapters   an n/N badge that ticks forward on every cut: a finish line worth reaching
- callout    a lock-on reticle on the subject the footage search found
"""
import re

from ..captions import _circle, _esc, _rounded, _text_width, _ts
from ..config import HEIGHT, WIDTH
from . import captions

NAMES = {
    "progress": "Progress bar",
    "burst": "Ring burst on each cut",
    "sweep": "Light sweep on each cut",
    "brackets": "Inset frame",
    "facts": "Fact pop-ups (numbers count up)",
    "facts_remotion": "Fact pop-ups, Remotion (glow, sparks; needs Node)",
    "size_compare": "Size comparison, Remotion (the animal next to a person)",
    "map_zoom": "Map zoom to the place named, Remotion",
    "teaser": "Open-loop teaser",
    "chapters": "Chapter counter",
    "callout": "Lock-on callout on the subject",
}
YELLOW, DARK = "&H0000D4FF&", "&H00141414&"
FACT_Y = round(HEIGHT * 0.30)        # under the top labels, over the picture
TEASER_Y = round(HEIGHT * 0.735)     # between the captions and the apps' bottom 20%
CHAPTER_Y = captions.BOTTOM - 46
TEASER = {"en": ("WAIT FOR THE END", "HERE IT IS"), "km": ("រង់ចាំមើលដល់ចុង", "នេះហើយ!")}
_ONES = "zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen " \
        "seventeen eighteen nineteen".split()
NUM_WORDS = {w: i for i, w in enumerate(_ONES)} | {
    w: 10 * (i + 2) for i, w in enumerate("twenty thirty forty fifty sixty seventy eighty ninety".split())}
SCALES = {"hundred": 100, "thousand": 1000, "million": 10 ** 6, "billion": 10 ** 9}
SKIP = set("of the a an and to in on at is are was were it its that this for with as by or than about".split())
ACCENT, SOFT, WHITE = "&H00A34FFF&", "&H00F0E6FF&", "&H00FFFFFF&"   # ASS colours are BGR: the channel pink, a pink white
BAR_Y, BAR_H = captions.TOP + 12, 6
CY = round(HEIGHT * 0.40)   # where a burst starts: over the picture, above the captions


def _ev(start: float, end: float, text: str, layer: int = 0) -> str:
    return f"Dialogue: {layer},{_ts(start)},{_ts(end)},Gfx,,0,0,0,,{text}"


def _clean(text: str) -> str:
    return text.strip(".,!?;:\"'()“”‘’…—").lower()


def _spelled(words: list, i: int) -> tuple[int, int]:
    """("four hundred", ...) from words[i]: (its value, the index after it); (0, i) when it isn't a number."""
    j, cur, total = i, 0, 0
    while j < len(words):
        w = _clean(words[j].text)
        parts = w.split("-")
        if all(p in NUM_WORDS for p in parts):
            cur += sum(NUM_WORDS[p] for p in parts)
        elif w == "hundred" and j > i:
            cur = (cur or 1) * 100
        elif w in SCALES and j > i:
            total, cur = total + (cur or 1) * SCALES[w], 0
        elif not (w == "and" and j > i and j + 1 < len(words) and _clean(words[j + 1].text) in NUM_WORDS):
            break
        j += 1
    return total + cur, j


def facts(words: list) -> list[tuple[float, float, str, int | None, str]]:
    """The numbers the voice says in `words` (tts.Word): (start, end, the number as shown, its value when it can
    count up, the word after it as its unit). Spelled-out ones count only from 10 up or with a unit ("two hearts"),
    so "one of the" never pops."""
    out, i = [], 0
    while i < len(words):
        t = _clean(words[i].text)
        if re.fullmatch(r"\d[\d,]*(\.\d+)?%?", t):
            shown, j = t, i + 1
            value = int(t.replace(",", "")) if re.fullmatch(r"\d[\d,]*", t) else None
            if j < len(words) and _clean(words[j].text) in SCALES:
                shown, value, j = f"{t} {_clean(words[j].text)}", None, j + 1
        else:
            value, j = _spelled(words, i)
            shown = f"{value:,}"
        if j == i:
            i += 1
            continue
        unit = _clean(words[j].text) if j < len(words) else ""
        unit = unit if unit.isalpha() and unit not in SKIP else ""
        if t[:1].isdigit() or value >= 10 or unit:
            out.append((words[i].start, words[j if unit else j - 1].end, shown.upper(), value, unit.upper()))
        i = j
    return out


def fact_times(tl, words: dict) -> list[tuple[float, float, str, int | None, str, int]]:
    """When each fact pops over the Short: (start, end, shown, value, unit, beat index) in the Short's seconds."""
    out, last = [], -9.0
    for k, slot in enumerate(tl.slots):
        for s, e, shown, value, unit in facts(words.get(slot.scene) or []):
            at = slot.start + s
            if at - last >= 2.0:   # one at a time: a pile of numbers is noise
                out.append((at, min(slot.start + e + 1.0, slot.end, tl.total), shown, value, unit, k))
                last = at
    return out


def _fact_events(at: float, end: float, shown: str, value: int | None, unit: str, family: str) -> list[str]:
    """A number slamming in at FACT_Y: it counts up over 0.4 s when it's a whole number from 10 up, then holds."""
    def card(s: float, e: float, text: str, pop: str = "") -> str:
        under = rf"\N{{\fs64\1c{captions.WHITE}}}{_esc(unit)}" if unit else ""
        return _ev(s, e, rf"{{\an5\pos({captions.CX},{FACT_Y})\fn{family}\b1\fs150\1c{YELLOW}\3c&H000000&\bord8"
                         rf"\shad4\4a&H60&\q2{pop}}}{_esc(text)}{under}", 5)
    pop = r"\fscx150\fscy150\t(0,160,0.6,\fscx100\fscy100)"
    if value is None or value < 10 or value > 10 ** 9:
        return [card(at, end, shown, pop + r"\fad(0,150)")]
    steps, run = 8, 0.4
    out = [card(at + run * k / steps, at + run * (k + 1) / steps, f"{round(value * (1 - (1 - k / steps) ** 3)):,}",
                pop if k == 0 else "") for k in range(steps)]
    return out + [card(at + run, end, shown, r"\fscx112\fscy112\t(0,120,\fscx100\fscy100)\fad(0,150)")]


def _pill(start: float, end: float, text: str, x: int, y: int, an: int, family: str, lang: str, px: int,
          anim: str = "") -> list[str]:
    """`text` on a small dark rounded pill, anchored at (x, y) by `an` (4 = left middle, 5 = centre)."""
    w, h = _text_width(text, family, px, lang) + px, px * 1.5
    return [_ev(start, end, rf"{{\an{an}\pos({x},{y})\bord0\shad0\1c{DARK}\1a&H30&{anim}\p1}}{_rounded(w, h, h / 2)}", 5),
            _ev(start, end, rf"{{\an{an}\pos({x + (px // 2 if an == 4 else 0)},{y})\fn{family}\b1\fs{px}"
                            rf"\1c{captions.WHITE}\bord0\shad0\q2{anim}}}{_esc(text)}", 6)]


def _reticle(start: float, end: float, x: int, y: int, size: int = 320) -> list[str]:
    """Four accent corners that snap in onto (x, y) from wide, hold, and fade: the eye goes where they point."""
    a, th = size // 4, 7
    path = " ".join(f"m {cx} {cy + dy * a} l {cx} {cy} l {cx + dx * a} {cy} l {cx + dx * a} {cy + dy * th} "
                    f"l {cx + dx * th} {cy + dy * th} l {cx + dx * th} {cy + dy * a}"
                    for cx, cy, dx, dy in ((0, 0, 1, 1), (size, 0, -1, 1), (0, size, 1, -1), (size, size, -1, -1)))
    return [_ev(start, end, rf"{{\an5\pos({x},{y})\bord0\shad0\1c{ACCENT}\blur0.8\fscx170\fscy170\1a&HFF&"
                            rf"\t(0,260,0.5,\fscx100\fscy100\1a&H00&)\fad(0,250)\p1}}{path}", 4)]


def events(names: list[str] | tuple[str, ...], tl, words: dict | None = None, script=None,
           focus: list | None = None, family: str = "Arial", lang: str = "en", busy=()) -> list[str]:
    """The ASS events for the chosen graphics over the Short's timeline `tl` (longform.timing.Timeline). The attention
    traps also use the voice's `words` ({scene: [tts.Word]}, times from each beat's start), the `script` (a beat's
    name labels its callout) and `focus` (each beat's subject point, None where none was found)."""
    names = [n for n in names if n in NAMES]
    out = _trap_events(names, tl, words or {}, script, focus or [], family, lang, busy)
    total = tl.total
    cuts = [s.start for s in tl.slots]   # the first beat's start is the Short's first frame
    if "progress" in names:
        w, ms = captions.RIGHT - captions.LEFT, round(total * 1000)
        track = _rounded(w, BAR_H, BAR_H / 2)
        out.append(_ev(0, total, f"{{\\an7\\pos({captions.LEFT},{BAR_Y})\\bord0\\shad0\\1c{WHITE}\\1a&HE0&\\p1}}{track}"))
        out.append(_ev(0, total, f"{{\\an7\\pos({captions.LEFT},{BAR_Y})\\bord0\\shad0\\1c{ACCENT}\\1a&H10&\\fscx0.5"
                                 f"\\t(0,{ms},\\fscx100)\\p1}}{track}", 1))
        # the head rides the end of the fill: a small bright dot with a soft halo
        mid = BAR_Y + BAR_H // 2
        for r, blur, alpha, layer in ((9, 5, "&H90&", 1), (4, 0.8, "&H00&", 2)):
            out.append(_ev(0, total, f"{{\\an5\\move({captions.LEFT},{mid},{captions.RIGHT},{mid},0,{ms})\\bord0\\shad0"
                                     f"\\1c{SOFT if r == 4 else ACCENT}\\1a{alpha}\\blur{blur}\\p1}}{_circle(r, r, r)}", layer))
    for i, t in enumerate(cuts):
        end = min(t + 0.9, total)
        if "burst" in names:
            for delay, bord, col, alpha, span in ((0, 3, ACCENT, "&H40&", 700), (0.09, 2, SOFT, "&H80&", 640)):
                if t + delay >= total:
                    continue
                out.append(_ev(t + delay, min(t + delay + 0.8, total),
                               f"{{\\an5\\pos({captions.CX},{CY})\\1a&HFF&\\3c{col}\\3a{alpha}\\bord{bord}\\blur1.2"
                               f"\\fscx22\\fscy22\\t(0,{span},0.45,\\fscx400\\fscy400\\3a&HFF&)\\p1}}{_circle(100, 100, 100)}"))
        if "sweep" in names and i > 0:
            out.append(_ev(t, min(t + 0.55, total), f"{{\\an5\\move(-200,{HEIGHT // 2},{WIDTH + 200},{HEIGHT // 2},0,520)"
                                                    f"\\1c{SOFT}\\1a&HE4&\\bord0\\blur34\\frz-16\\p1}}"
                                                    f"{_rounded(120, HEIGHT * 1.3, 60)}"))
    if "brackets" in names:
        x0, x1, y0, y1, a, th = 72, captions.RIGHT + 36, captions.TOP + 74, round(HEIGHT * 0.78), 70, 5
        out.append(_ev(0, total, f"{{\\an7\\pos(0,0)\\1a&HFF&\\3c{WHITE}\\3a&HC8&\\bord2\\fad(600,400)\\p1}}"
                                 f"m {x0} {y0} l {x1} {y0} l {x1} {y1} l {x0} {y1}"))
        for (x, y, dx, dy) in ((x0, y0, 1, 1), (x1, y0, -1, 1), (x0, y1, 1, -1), (x1, y1, -1, -1)):
            pts = (f"m {x} {y + dy * a} l {x} {y} l {x + dx * a} {y} l {x + dx * a} {y + dy * th} "
                   f"l {x + dx * th} {y + dy * th} l {x + dx * th} {y + dy * a}")
            out.append(_ev(0, total, f"{{\\an7\\pos(0,0)\\bord0\\shad0\\1c{ACCENT}\\blur0.8\\fad(700,400)"
                                     f"\\t(0,1600,\\1a&H50&)\\t(1600,3200,\\1a&H10&)\\p1}}{pts}"))
    return out


def _trap_events(names: list[str], tl, words: dict, script, focus: list, family: str, lang: str,
                 busy=()) -> list[str]:
    out: list[str] = []
    slots = tl.slots
    if "facts" in names:
        for at, end, shown, value, unit, _ in fact_times(tl, words):
            if not any(s <= at < e for s, e in busy):  # a Remotion graphic is on screen then
                out += _fact_events(at, end, shown, value, unit, family)
    if "teaser" in names and len(slots) >= 3:
        open_, close = TEASER.get(lang, TEASER["en"])
        pulse = r"\t(0,300,\fscx106\fscy106)\t(300,600,\fscx100\fscy100)"
        if slots[0].end - 0.8 > 0.5:
            out += _pill(0.8, slots[0].end, open_, captions.CX, TEASER_Y, 5, family, lang, 46, r"\fad(200,150)" + pulse)
        payoff = slots[-1].start
        out += _pill(payoff, min(payoff + 1.4, tl.total), close, captions.CX, TEASER_Y, 5, family, lang, 52,
                     r"\fscx60\fscy60\t(0,180,0.6,\fscx100\fscy100)\fad(0,200)")
    if "chapters" in names and len(slots) >= 3:
        for k, slot in enumerate(slots, 1):
            tick = r"\fscx130\fscy130\t(0,200,\fscx100\fscy100)" if k > 1 else ""
            out += _pill(slot.start, slot.end, f"{k}/{len(slots)}", captions.LEFT, CHAPTER_Y, 4, family, lang, 40, tick)
    if "callout" in names:
        for k, slot in enumerate(slots):
            # the hook beat has its own card; every other beat at most, so it stays a surprise
            if k == 0 or k % 2 == 0 or k >= len(focus) or not focus[k] or slot.length < 1.2:
                continue
            # the render crops on the focus point, so the subject sits at the frame's centre (unless the crop hit an
            # edge: shortcut: no clamping maths, upgrade if callouts drift off wide shots)
            at = slot.start + 0.25
            out += _reticle(at, min(at + 1.3, slot.end), captions.CX, HEIGHT // 2)
            scene = script.scenes[k] if script and k < len(script.scenes) else None
            if scene and scene.name:
                out += _pill(at + 0.2, min(at + 1.3, slot.end), scene.name.upper(), captions.CX, HEIGHT // 2 + 220, 5,
                             family, lang, 40, r"\fad(150,250)")
    return out


STYLE = "Style: Gfx,Arial,20,&H00FFFFFF&,&H00FFFFFF&,&H00000000&,&H00000000&,0,0,0,0,100,100,0,0,1,0,0,7,0,0,0,1"
