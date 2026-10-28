"""A Short's text layer (ASS, 1080x1920), all of it inside the safe zone: nothing in the bottom 20% (the title,
caption and music line the apps draw) or the right 15% (like / comment / share), nor the top 8% (the app's header);
covers.SAFE holds those edges.

- the hook: beat 1's On-screen Text on a white card (captions._hook_events) from the very first frame
- labels: every other beat's On-screen Text, at the top, white on a dark card
- captions: the voiceover word by word from its real word timings, big and bold, white with a thick black outline,
  the word being spoken in yellow; a few words at a time, broken at sentence ends, shrunk to fit the safe width
English and Khmer both work: each language has its own fonts (longform.video._fonts) and libass shapes Khmer with
HarfBuzz (finalize uses shaping=complex). Emoji in the sheet's text are drawn by finalize (emoji.py).
"""
from ..captions import _balance, _case, _esc, _hook_events, _rounded, _text_width, _ts
from ..config import HEIGHT, LANGS, WIDTH
from ..highlights.covers import SAFE
from ..longform.parse import Script
from ..longform.timing import Timeline
from ..longform.video import _fonts
from ..tts import Word

TOP, BOTTOM = round(HEIGHT * SAFE["top"]), round(HEIGHT * SAFE["bottom"])
# centred on the screen (centring between the safe edges sits ~50 px left and looks off), so the text may reach as
# far left of the centre as the right 15% lets it go right: 756 px wide, the same margin on both sides
CX = WIDTH // 2
TEXT_W = 2 * (round(WIDTH * SAFE["right"]) - CX)
LEFT, RIGHT = CX - TEXT_W // 2, CX + TEXT_W // 2
HOOK_PX, LABEL_PX, CAPTION_PX = 92, 76, 100
CAPTION_Y = round(HEIGHT * 0.64)     # the caption's middle: under the animal, well above the bottom 20%
LABEL_TOP = TOP + 40
YELLOW, WHITE, BLACK = "&H0000D4FF&", "&H00FFFFFF&", "&H00000000&"
SENTENCE_END = (".", "!", "?", "…", "—", ":", ";")


def groups(words: list[Word], n: int) -> list[list[Word]]:
    """The words in caption groups of up to `n`, a new group after each sentence end (or a comma once the group has
    two words), so a caption never runs across two sentences."""
    out: list[list[Word]] = [[]]
    for w in words:
        out[-1].append(w)
        t = w.text.rstrip("\"'”’)")
        if len(out[-1]) >= n or t.endswith(SENTENCE_END) or (t.endswith(",") and len(out[-1]) >= 2):
            out.append([])
    return [g for g in out if g]


def _fit(text: str, family: str, px: int, lang: str, width: float, lines: int = 2) -> tuple[list[str], int]:
    """`text` balanced over at most `lines` rows at the biggest size from `px` down that fits `width`."""
    words = text.split()
    for size in [px, *(round(px * f) for f in (0.9, 0.8, 0.7, 0.6))]:
        for n in range(1, min(lines, len(words)) + 1):
            rows = _balance(words, n, lambda t, s=size: _text_width(t, family, s, lang))
            if max(_text_width(r, family, size, lang) for r in rows) <= width:
                return rows, size
    return _balance(words, min(lines, len(words)), lambda t: _text_width(t, family, px, lang)), round(px * 0.6)


def label_events(text: str, start: float, end: float, family: str, lang: str) -> list[str]:
    """A beat's On-screen Text at the top: white words on a dark rounded card, fading in and out."""
    pad_x, pad_y = round(LABEL_PX * 0.45), round(LABEL_PX * 0.28)
    rows, size = _fit(text, family, LABEL_PX, lang, RIGHT - LEFT - 2 * pad_x)
    w = max(_text_width(r, family, size, lang) for r in rows) + 2 * pad_x
    h = len(rows) * size * 1.12 + 2 * pad_y
    cy = round(LABEL_TOP + h / 2)
    fade = r"\fad(120,120)"
    return [f"Dialogue: 2,{_ts(start)},{_ts(end)},Label,,0,0,0,,{{\\an5\\pos({CX},{cy}){fade}\\bord0\\shad0"
            f"\\1c&H141414&\\1a&H28&\\p1}}{_rounded(w, h, size * 0.25)}",
            f"Dialogue: 3,{_ts(start)},{_ts(end)},Label,,0,0,0,,{{\\an5\\pos({CX},{cy}){fade}\\fs{size}\\q2}}"
            + r"\N".join(_esc(r) for r in rows)]


def caption_events(words: list[Word], at: float, family: str, lang: str, n: int, until: float) -> list[str]:
    """The voiceover's words (times relative to `at`, the beat's start) as captions; the last group stays up to
    `until` at most."""
    out = []
    gs = groups(words, n)
    for gi, g in enumerate(gs):
        g_end = gs[gi + 1][0].start if gi + 1 < len(gs) else min(g[-1].end + 0.3, until - at)
        texts = [_esc(_case(w.text, "upper", lang)) for w in g]
        rows, size = _fit(" ".join(texts), family, CAPTION_PX, lang, RIGHT - LEFT)
        # each row is drawn as its words, so the spoken one can be coloured; rows were balanced on the plain text
        per_row, k = [], 0
        for r in rows:
            per_row.append(list(range(k, k + len(r.split()))))
            k += len(r.split())
        for wi, w in enumerate(g):
            s = at + w.start
            e = at + (g[wi + 1].start if wi + 1 < len(g) else g_end)
            if e <= s:
                continue
            pop = r"\fscx82\fscy82\t(0,80,0.7,\fscx106\fscy106)\t(80,130,\fscx100\fscy100)" if wi == 0 else ""
            body = r"\N".join(" ".join(f"{{\\1c{YELLOW if j == wi else WHITE}}}{texts[j]}" for j in idx)
                              for idx in per_row)
            out.append(f"Dialogue: 1,{_ts(s)},{_ts(e)},Caption,,0,0,0,,{{\\an5\\pos({CX},{CAPTION_Y})\\fs{size}"
                       f"{pop}}}{body}")
    return out


def build(script: Script, tl: Timeline, voices: dict[int, list[Word]]) -> str:
    """The whole text layer: hook, labels and captions for every beat."""
    lang = script.lang
    profile = LANGS.get(lang, LANGS["en"])
    (body, _), (title, _) = _fonts(lang)
    heavy = body if lang == "km" else title  # Khmer's title face (Muol) is decorative: captions use the body face
    n = profile.words_per_caption if lang == "km" else 3
    events: list[str] = []
    for i, (scene, slot) in enumerate(zip(script.scenes, tl.slots)):
        if scene.text and i == 0:
            events += _hook_events(_esc(_case(scene.text, "upper", lang)), 0.0, slot.end, LABEL_TOP, heavy,
                                   HOOK_PX, lang, left=LEFT, right=RIGHT)
        elif scene.text:
            events += label_events(scene.text, slot.start + 0.05, slot.end - 0.05, heavy, lang)
        words = voices.get(scene.n) or []
        if words:
            events += caption_events(words, slot.start, heavy, lang, n, slot.end)
    styles = [
        f"Style: Hook,{heavy},{HOOK_PX},&H00141414&,&H00141414&,&H00FFFFFF&,&H00FFFFFF&,-1,0,0,0,100,100,0,0,1,0,0,"
        "8,0,0,0,1",
        f"Style: Label,{heavy},{LABEL_PX},{WHITE},{WHITE},{BLACK},{BLACK},-1,0,0,0,100,100,0,0,1,0,0,5,0,0,0,1",
        # thick outline + soft shadow: readable on any footage
        f"Style: Caption,{heavy},{CAPTION_PX},{WHITE},{WHITE},{BLACK},&H80000000&,-1,0,0,0,100,100,0,0,1,7,3,5,0,0,0,"
        "1",
    ]
    return "\n".join([
        "[Script Info]", "ScriptType: v4.00+", f"PlayResX: {WIDTH}", f"PlayResY: {HEIGHT}", "WrapStyle: 2",
        "ScaledBorderAndShadow: yes", "", "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, "
        "Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, "
        "MarginR, MarginV, Encoding", *styles, "", "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text", *events, ""])
