"""Motion graphics for a Short: animated shapes in the text layer (ASS vector drawings, burned in with the captions).

Same design language as the lyric video's (neonmekong/graphics.py), so a channel's Shorts and long videos look like
one kit: thin strokes, one accent colour plus soft white at low opacity, eased motion, a touch of blur for glow, and
motion only on the cuts. They sit under the captions (layer 0) and inside the safe zone (captions.TOP / BOTTOM /
RIGHT): nothing in the app's header, the bottom 20% or the right 15%.

- progress   a hairline under the app header that fills over the whole Short, with a small bright head
- burst      two thin rings that ease outward from the picture on every cut
- sweep      a faint soft streak of light that crosses the picture on every cut
- brackets   an inset hairline frame with accent corners that fade in and breathe
"""
from ..captions import _circle, _rounded, _ts
from ..config import HEIGHT, WIDTH
from . import captions

NAMES = {
    "progress": "Progress bar",
    "burst": "Ring burst on each cut",
    "sweep": "Light sweep on each cut",
    "brackets": "Inset frame",
}
ACCENT, SOFT, WHITE = "&H00A34FFF&", "&H00F0E6FF&", "&H00FFFFFF&"   # ASS colours are BGR: the channel pink, a pink white
BAR_Y, BAR_H = captions.TOP + 12, 6
CY = round(HEIGHT * 0.40)   # where a burst starts: over the picture, above the captions


def _ev(start: float, end: float, text: str, layer: int = 0) -> str:
    return f"Dialogue: {layer},{_ts(start)},{_ts(end)},Gfx,,0,0,0,,{text}"


def events(names: list[str] | tuple[str, ...], tl) -> list[str]:
    """The ASS events for the chosen graphics over the Short's timeline `tl` (longform.timing.Timeline)."""
    names = [n for n in names if n in NAMES]
    total = tl.total
    out: list[str] = []
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


STYLE = "Style: Gfx,Arial,20,&H00FFFFFF&,&H00FFFFFF&,&H00000000&,&H00000000&,0,0,0,0,100,100,0,0,1,0,0,7,0,0,0,1"
