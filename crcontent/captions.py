"""Build an .ass subtitle file: big centered captions with the spoken word highlighted."""
import re
from typing import TYPE_CHECKING

from .config import HEIGHT, WIDTH, LangProfile
from .tts import Word

if TYPE_CHECKING:
    from .styles import CaptionStyle

HIGHLIGHT = "&H0000E5FF&"  # ASS colours are &HAABBGGRR -> yellow
WHITE = "&H00FFFFFF&"


def _ts(sec: float) -> str:
    sec = max(sec, 0)
    h, rem = divmod(sec, 3600)
    m, s = divmod(rem, 60)
    return f"{int(h)}:{int(m):02d}:{s:05.2f}"


def _esc(text: str) -> str:
    # emoji are kept: render.finalize() draws them in colour (emoji.py)
    text = text.strip()
    return text.replace("\\", "/").replace("{", "(").replace("}", ")").replace("\n", " ")


def _text_width(text: str, family: str, px: float, lang: str = "en", spacing: float = 0.0) -> float:
    """About how wide libass draws `text` in `family` at font size `px` (ASS sizes are the font's ascent+descent,
    not its em, so PIL's width is scaled by em/(ascent+descent)). Falls back to an average glyph width when the font
    file isn't found. Khmer is measured without shaping (subscripts counted as glyphs): a little wide, never short."""
    from .styles import FONTS, font_path

    n = len(text)
    try:
        from PIL import ImageFont

        file = FONTS.get(lang, FONTS["en"]).get(family) or FONTS["en"].get(family, "")
        path = font_path(file) if file else None
        if path:
            f = ImageFont.truetype(str(path), 200)
            asc, desc = f.getmetrics()
            return f.getlength(text) * px / (asc + desc) + spacing * n
    except Exception:
        pass
    return px * 0.56 * n + spacing * n


def _balance(words: list[str], lines: int, width) -> list[str]:
    """`words` split into `lines` lines (in order) so the widest line is as narrow as possible; `width(str)`."""
    if lines <= 1 or len(words) <= 1:
        return [" ".join(words)]
    best, best_w = [" ".join(words)], float("inf")
    n = len(words)
    cuts = [(i,) for i in range(1, n)] if lines == 2 or n < 3 else \
        [(i, j) for i in range(1, n - 1) for j in range(i + 1, n)]
    for cut in cuts:
        bounds = (0, *cut, n)
        parts = [" ".join(words[a:b]) for a, b in zip(bounds, bounds[1:])]
        w = max(width(p) for p in parts)
        if w < best_w:
            best, best_w = parts, w
    return best


def caption_styles(profile: LangProfile, style: "CaptionStyle", size: tuple[int, int] = (WIDTH, HEIGHT)) -> str:
    """The Caption and Headline style lines for `style` (see styles.CaptionStyle)."""
    from .styles import ass_color

    W, _ = size
    font = style.font or profile.font_name
    px = round(profile.font_size * {"s": 0.8, "m": 1.0, "l": 1.25}[style.size] * W / WIDTH)
    base = ass_color(style.color)
    # how the letters stand off the footage (same choices as the lyric videos). The default is the top Shorts look:
    # a thick, clean black outline (~8 px at 92 px / 1080 wide) and a soft drop shadow (60% black, softened by the
    # \blur build_ass adds), so white words read on snow as well as on night footage
    if style.outline == "box":
        border, outline, shadow, out_c, back_c = 3, max(10, px // 7), 0, "&H55000000&", "&H55000000&"
    elif style.outline == "shadow":
        # a dark halo (blurred by build_ass) rather than a hairline, plus a drop shadow
        border, outline, shadow, out_c, back_c = 1, max(5, px // 12), max(3, px // 24), "&H50000000&", "&H66000000&"
    elif style.outline == "glow":
        border, outline, shadow, out_c, back_c = 1, max(4, px // 18), 2, ass_color(style.highlight, 0x40), "&H70000000&"
    else:
        border, outline, shadow, out_c, back_c = 1, round(px * 8.5 / 92), 4, "&H00000000&", "&H66000000&"
    head = round(px * 0.8)
    # margins: the wrap width; the right one keeps clear of the platforms' like / comment buttons (~120 px)
    return (f"Style: Caption,{font},{px},{base},{base},{out_c},{back_c},-1,0,0,0,100,100,0,0,{border},{outline},{shadow},5,110,120,0,1\n"
            f"Style: Headline,{font},{head},&H00FFFFFF&,&H00FFFFFF&,&HFF000000&,&H1A000000&,-1,0,0,0,100,100,0,0,4,{round(head * 0.35)},0,8,80,80,0,1")


def build_ass(scenes: list[tuple], profile: LangProfile, style: "CaptionStyle | None" = None,
              extra: list[str] | None = None) -> str:
    """scenes: (scene_start, scene_end, words with times relative to scene_start, on_screen_text[, keywords]).
    Drawn in `style` (styles.CaptionStyle): the spoken word in its highlight colour, keywords (voiceover.keyword()
    form) in its keyword colour, the rest in its text colour. `extra`: more Dialogue lines (text overlays)."""
    from .styles import CaptionStyle, ass_color
    from .voiceover import keyword

    style = (style or CaptionStyle()).clean(profile.code)
    high, key_c, base = ass_color(style.highlight), ass_color(style.keyword), ass_color(style.color)
    # \blur on a bordered line softens only the outline and shadow (the letters stay sharp): a touch takes the
    # jaggies off the thick black outline and makes its drop shadow soft
    blur = (r"\blur4" if style.outline == "shadow" else r"\blur10" if style.outline == "glow"
            else "" if style.outline == "box" else r"\blur1.2")
    # the opening scene's headline is the hook: bigger than other headlines, dark on a white box, so it reads in the
    # feed at a glance on any footage
    hook_px = round(profile.font_size * {"s": 0.8, "m": 1.0, "l": 1.25}[style.size] * 0.8 * 1.3)
    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {WIDTH}
PlayResY: {HEIGHT}
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
{caption_styles(profile, style)}
Style: Overlay,{style.font or profile.font_name},{profile.font_size},&H00FFFFFF&,&H00FFFFFF&,&H00000000&,&H80000000&,-1,0,0,0,100,100,0,0,1,{round(profile.font_size * 6 / 92)},2,5,40,40,0,1
Style: Hook,{style.font or profile.font_name},{hook_px},&H00141414&,&H00141414&,&H00FFFFFF&,&H00FFFFFF&,-1,0,0,0,100,100,0,0,3,{round(hook_px * 0.22)},0,8,70,70,0,1
Style: OverlayBox,{style.font or profile.font_name},{profile.font_size},&H00FFFFFF&,&H00FFFFFF&,&H33000000&,&H33000000&,-1,0,0,0,100,100,0,0,3,{round(profile.font_size * 14 / 92)},0,5,40,40,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    lines: list[str] = []
    cap_y = round(HEIGHT * style.y)
    head_y = round(HEIGHT * style.headline_y)
    n = style.words or profile.words_per_caption
    for si, (scene_start, scene_end, words, headline, *rest) in enumerate(scenes):
        keywords = rest[0] if rest else set()
        if headline and si == 0:  # the hook pops in on the very first frame
            lines += _hook_events(_esc(_case(headline, "upper", profile.code)), scene_start, scene_end, head_y,
                                  style.font or profile.font_name, hook_px, profile.code)
            continue  # one strong line of text in the hook: its spoken words aren't captioned too
        elif headline:
            lines.append(f"Dialogue: 1,{_ts(scene_start)},{_ts(scene_end)},Headline,,0,0,0,,"
                         f"{{\\an8\\pos({WIDTH // 2},{head_y})}}{_esc(headline.upper())}")

        groups = [words[i:i + n] for i in range(0, len(words), n)]
        for gi, group in enumerate(groups):
            # each group stays on screen until the next group starts (no flicker between words)
            group_end = groups[gi + 1][0].start if gi + 1 < len(groups) else group[-1].end + 0.15
            for wi, word in enumerate(group):
                start = scene_start + word.start
                end = scene_start + (group[wi + 1].start if wi + 1 < len(group) else group_end)
                parts = []
                for wj, w in enumerate(group):
                    color = high if wj == wi else key_c if keyword(w.text) in keywords else base
                    parts.append(f"{{\\c{color}}}{_esc(_case(w.text, style.case, profile.code))}")
                pop = r"{\fscx85\fscy85\t(0,90,\fscx100\fscy100)}" if wi == 0 else ""
                text = f"{{\\pos({WIDTH // 2},{cap_y}){blur}}}{pop}" + " ".join(parts)
                lines.append(f"Dialogue: 0,{_ts(start)},{_ts(end)},Caption,,0,0,0,,{text}")
    return header + "\n".join(lines + (extra or [])) + "\n"


HOOK_SIDE = 64  # px kept clear on each side of the hook's box (1080 wide)
HOOK_TOP = 130  # the box never starts above this: the platforms' top bar


def _hook_events(text: str, start: float, end: float, top: int, family: str, px: int, lang: str) -> list[str]:
    """The hook: dark words on one tidy white rounded card (instead of the ragged per-line boxes BorderStyle 3
    draws), the same padding on every side, at most 2 lines (3 only when even a smaller size can't fit 2), a soft
    shadow under the card. Top edge at `top`; pops in from 80% on the first frames."""
    words = text.split()
    pad_x, pad_y = round(px * 0.42), round(px * 0.26)
    room = WIDTH - 2 * HOOK_SIDE - 2 * pad_x  # widest a line of text may be
    size, rows, fits = px, [text], True
    for n in (1, 2, 3):
        for s in [px] + ([round(px * f) for f in (0.92, 0.84, 0.76, 0.68)] if n > 1 else []):
            rows = _balance(words, n, lambda t, s=s: _text_width(t, family, s, lang))
            if max(_text_width(r, family, s, lang) for r in rows) <= room:
                size = s
                break
        else:
            continue
        break
    else:  # very long: 3 lines at the smallest size, libass wraps whatever is left
        size, fits = round(px * 0.68), False
    pad_x, pad_y = round(size * 0.42), round(size * 0.26)
    w = min(max(_text_width(r, family, size, lang) for r in rows), room) + 2 * pad_x
    h = len(rows) * size + 2 * pad_y
    top = max(top, HOOK_TOP)
    cx, cy = WIDTH // 2, round(top + h / 2)
    t0, t1 = _ts(start), _ts(end)
    pop = r"\fscx80\fscy80\t(0,120,\fscx100\fscy100)"
    card = _rounded(w, h, size * 0.2)
    q = r"\q2" if fits else ""  # no wrapping: the rows are already measured to fit
    # every part centred on the same point (\an5), so the pop scales them together
    return [f"Dialogue: 2,{t0},{t1},Hook,,0,0,0,,{{\\an5\\pos({cx},{cy + round(size * 0.07)}){pop}\\bord0\\shad0"
            f"\\blur{round(size * 0.18)}\\1c&H000000&\\1a&H90&\\p1}}{card}",
            f"Dialogue: 3,{t0},{t1},Hook,,0,0,0,,{{\\an5\\pos({cx},{cy}){pop}\\bord0\\shad0\\blur0.6"
            f"\\1c&HFFFFFF&\\p1}}{card}",
            f"Dialogue: 4,{t0},{t1},Hook,,0,0,0,,{{\\an5\\pos({cx},{cy}){pop}\\fs{size}\\bord0\\shad0{q}}}"
            + r"\N".join(rows)]


OVERLAY_SIZES = {"s": 0.6, "m": 0.85, "l": 1.2}  # of the language's caption size


def overlay_lines(texts: list, scene_start: float, scene_end: float, profile: LangProfile) -> list[str]:
    """Dialogue lines for a scene's text overlays (script.TextOverlay), for build_ass(extra=...)."""
    from .styles import _hex, ass_color

    lines = []
    for t in texts:
        text = _esc(t.text)
        start = scene_start + max(t.at, 0)
        end = min(start + max(t.duration, 0.1), scene_end)
        if not text or end <= start:
            continue
        x, y = round(WIDTH * min(max(t.x, 0), 1)), round(HEIGHT * min(max(t.y, 0), 1))
        fs = round(profile.font_size * OVERLAY_SIZES.get(t.size, OVERLAY_SIZES["m"]))
        color = ass_color(_hex(t.color, "#FFFFFF"))
        lines.append(f"Dialogue: 2,{_ts(start)},{_ts(end)},{'OverlayBox' if t.box else 'Overlay'},,0,0,0,,"
                     f"{{\\an5\\pos({x},{y})\\fs{fs}\\c{color}\\fad(120,120)}}{text}")
    return lines


def _case(text: str, case: str, lang: str) -> str:
    if lang == "km":
        return text
    return text.upper() if case == "upper" else text.lower() if case == "lower" else text


def build_karaoke_ass(lines, profile: LangProfile, lead_in: float = 0.35, hold: float = 0.8,
                      size: tuple[int, int] = (WIDTH, HEIGHT), style: "LyricStyle | None" = None,
                      title: tuple | None = None,
                      now_playing: dict | None = None, glitch_words: set[str] | None = None,
                      title_at: tuple[int, int] | None = None) -> str:
    """Lyrics as karaoke, drawn in `style` (font, colours, size, position, effect; see styles.py).

    lines: align.LyricLine items (absolute word times). A line appears `lead_in` s before its first word and
    stays until the next line starts or `hold` s after its last word, so two lines never overlap. Effects:
    karaoke: the whole line shown, words change colour as they're sung (words still to come a little see-through).
    fill: a smooth colour sweep through each word.  pop: words appear one by one with a little bounce.  fade: the
    whole line fades in and out.  glitch: the line breaks in like a bad signal (red and cyan copies splitting apart,
    a torn slice, a flicker) for a quarter of a second, and for a few frames on every sung word in `glitch_words`
    (the song title's words), which stay in the highlight colour; between those hits the line is solid.
    Landscape frames show the upcoming line dimmed underneath (karaoke and fill), like a lyric video.
    title: (text, start, end[, #RRGGBB]) the song's title flickering on like a neon sign, in that colour (else the
    sung-word colour), away from the lyrics. title_at: (x, y) pixel centre for it (an empty area beside the
    character); there it's sized to fit ~38% of the frame's width, on 2 lines if long. None: centred, above or below
    the lyrics.
    now_playing: {"title", "label", "start", "length", "accent"} for a now-playing card (now_playing_events).
    """
    from .styles import LyricStyle, ass_color

    style = (style or LyricStyle()).clean(profile.code)
    W, H = size
    landscape = W > H
    # ~68 px at 1080p landscape, ~74-80 px on a 1080x1920 frame (Khmer a little bigger: its stacked vowels)
    font = round(profile.font_size * (0.85 if profile.code == "km" else 0.8))
    font = round(font * (0.92 if landscape else 1.04) * min(W, H) / 1080)
    font = round(font * {"s": 0.8, "m": 1.0, "l": 1.25}[style.size])
    small = round(font * 0.72)
    base, high = ass_color(style.color), ass_color(style.highlight)
    unsung = 0x38  # words not sung yet: ~78% opaque, so the sung ones stand out even when both are white

    # how the letters stand off the footage. Each lyric event can get a copy under it (`back`): a soft drop shadow
    # for outline / shadow, a coloured glow for glow, so the line itself keeps a crisp dark edge on a pale picture
    sa = 0x70  # the soft shadow's alpha
    back = ""
    if style.outline == "box":
        border, outline, shadow, out_c, back_c = 3, max(10, font // 7), 0, "&H55000000&", "&H55000000&"
        blur = ""
    elif style.outline == "shadow":
        # a strong dark halo hugging the letters (a wide outline, blurred: the letters stay sharp) and a soft drop
        # shadow underneath: white reads on light pastel pictures too
        border, outline, shadow, out_c, back_c = 1, max(4, font // 9), 0, "&H40000000&", "&H70000000&"
        blur = f"\\blur{max(3, font // 12)}"
        back = f"\\bord{max(3, font // 14)}\\shad{max(3, font // 18)}\\blur{max(5, font // 7)}\\4c&H000000&"
    elif style.outline == "glow":
        # a thin dark edge for legibility on the line; the accent glow is the copy under it
        border, outline, shadow, out_c, back_c = 1, max(2, font // 30), 0, "&H40000000&", "&H70000000&"
        blur = r"\blur0.8"
        back = (f"\\bord{max(5, font // 11)}\\shad0\\blur{max(8, font // 6)}\\3c{high}\\3a&H30&"
                f"\\1c{high}")
    else:
        # a clean 3-4 px dark outline, softened a hair, and a soft drop shadow (the copy) under it
        border, outline, shadow, out_c, back_c = 1, max(3, round(font / 17)), 0, "&H10000000&", "&H70000000&"
        blur = r"\blur0.9"
        back = f"\\bord{max(3, round(font / 17))}\\shad{max(3, font // 20)}\\blur{max(4, font // 10)}\\4c&H000000&"
    glow_back = style.outline == "glow"
    # fill sweeps from SecondaryColour (not sung yet) to PrimaryColour (sung)
    primary = high if style.effect == "fill" else base
    secondary = ass_color(style.color, unsung) if style.effect == "fill" else base
    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Lyric,{style.font},{font},{primary},{secondary},{out_c},{back_c},-1,0,0,0,100,100,0,0,{border},{outline},{shadow},5,80,80,0,1
Style: LyricNext,{style.font},{small},&H48FFFFFF&,&H48FFFFFF&,&H50000000&,&H90000000&,-1,0,0,0,100,100,0,0,1,{max(2, round(small / 18))},2,5,80,80,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    events: list[str] = []
    # landscape "low": the line's baseline ~85% down, like a lyric video; the dimmed next line under it is kept
    # clear of the frame's bottom edge (the whole pair moves up if it would touch)
    if landscape:
        ys = {"low": 0.85 - 0.3 * font / H, "middle": 0.5, "high": 0.2}
    else:
        ys = {"low": 0.64, "middle": 0.5, "high": 0.24}
    y = round(H * ys[style.position])
    next_off = round(font * 0.62 + small * 0.6)  # centre to centre
    if landscape and style.effect in ("karaoke", "fill"):
        y = min(y, round(H * 0.965 - small * 0.6) - next_off)
    pos = f"{{\\pos({W // 2},{y}){blur}}}"
    next_pos = f"{{\\pos({W // 2},{y + next_off})\\blur0.8}}"
    prev_end = 0.0
    for li, line in enumerate(lines):
        words = [w for w in line.words if _esc(w.text)]
        if not words:
            continue
        texts = [_esc(_case(w.text, style.case, profile.code)) for w in words]
        next_start = lines[li + 1].start if li + 1 < len(lines) else float("inf")
        line_end = min(next_start, words[-1].end + hold)
        show = max(prev_end, words[0].start - lead_in)

        def dialogue(start: float, end: float, text: str, name: str = "Lyric", layer: int = 1) -> None:
            if end > start:
                if name == "Lyric" and back:
                    events.append(f"Dialogue: 0,{_ts(start)},{_ts(end)},{name},,0,0,0,,"
                                  f"{_backing(text, back, None if glow_back else sa)}")
                events.append(f"Dialogue: {layer},{_ts(start)},{_ts(end)},{name},,0,0,0,,{text}")

        if style.effect == "fill":
            # one event per line: \kf sweeps each word over its sung time (centiseconds from when the line shows;
            # counted from there rather than word by word so rounding never drifts)
            mark = [round((w.start - show) * 100) for w in words] + [round((words[-1].end - show) * 100)]
            body = f"{{\\k{max(0, mark[0])}}}" + " ".join(
                f"{{\\kf{max(1, mark[i + 1] - mark[i])}}}{t}" for i, t in enumerate(texts))
            dialogue(show, line_end, pos + r"{\fad(120,200)}" + body)
        elif style.effect == "fade":
            dialogue(show, line_end, pos + r"{\fad(250,300)}" + " ".join(texts))
        elif style.effect == "glitch":
            main, bursts = _glitch_line(words, texts, show, line_end, glitch_words or set(), W // 2, y, font, blur,
                                        base, high)
            dialogue(show, line_end, main, layer=2)  # its split copies go on layer 1, between it and its shadow
            events.extend(bursts)
        elif style.effect == "pop":
            for wi, w in enumerate(words):
                end = words[wi + 1].start if wi + 1 < len(words) else line_end
                parts = []
                for j, t in enumerate(texts):
                    if j < wi:
                        parts.append(f"{{\\alpha&H00&\\c{base}\\fscx100\\fscy100}}{t}")
                    elif j == wi:
                        parts.append(f"{{\\alpha&H00&\\c{high}\\fscx118\\fscy118\\t(0,140,\\fscx100\\fscy100)}}{t}")
                    else:  # not sung yet: invisible, but holding its place so the line doesn't shift
                        parts.append(f"{{\\alpha&HFF&\\fscx100\\fscy100}}{t}")
                dialogue(w.start, end, pos + " ".join(parts))
        else:
            def text(sung: int) -> str:
                return pos + " ".join(f"{{\\c{high}\\1a&H00&}}{t}" if j < sung else f"{{\\c{base}\\1a&H{unsung:02X}&}}{t}"
                                      for j, t in enumerate(texts))

            dialogue(show, words[0].start, r"{\fscx90\fscy90\t(0,120,\fscx100\fscy100)}" + text(0))
            for wi, w in enumerate(words):
                dialogue(w.start, words[wi + 1].start if wi + 1 < len(words) else line_end, text(wi + 1))
        if (landscape and style.effect in ("karaoke", "fill") and li + 1 < len(lines)
                and next_start - line_end < 2.5 and _esc(lines[li + 1].text)):
            dialogue(show, line_end, next_pos + r"{\fad(150,150)}"
                     + _esc(_case(lines[li + 1].text, style.case, profile.code)), "LyricNext")
        prev_end = line_end
    if title and _esc(title[0]):
        glow = style.model_copy(update={"highlight": title[3]}) if len(title) > 3 and title[3] else style
        at = title_at or (W // 2, round(H * (0.72 if style.position == "high" else 0.3)))
        events += _neon_title(_esc(_case(title[0], "upper", profile.code)), title[1], title[2], glow, font, size,
                              at, fit=0.38 if title_at else 0.8, lang=profile.code)
    if now_playing:
        events += now_playing_events(now_playing["title"], now_playing.get("label") or "Now playing",
                                     now_playing["start"], now_playing["length"], size, style.font,
                                     now_playing.get("accent") or style.highlight)
    return header + "\n".join(events) + "\n"


def _alpha_over(a: int, b: int) -> int:
    """ASS alpha (0 opaque .. 255 invisible) of something `a`-transparent seen through `b`."""
    return 255 - (255 - a) * (255 - b) // 255


def _backing(text: str, tags: str, shadow_alpha: int | None) -> str:
    """The copy drawn under a lyric event: `text` (its override blocks and words) with `tags` added up front.
    shadow_alpha set: only its shadow shows (the fill and outline are see-through, every \\alpha in the line,
    including animated ones, turned into the shadow's alpha), so the line gets a soft drop shadow that follows its
    fades and flickers. None (glow): the copy keeps its alphas and colours; `tags` give it the glow."""
    if shadow_alpha is None:
        return "{" + tags + "}" + text

    def block(m: re.Match) -> str:
        inner = re.sub(r"\\(?:1?c|2c)&H[0-9A-Fa-f]+&", "", m.group(1))  # colours don't matter: it's a shadow
        inner = re.sub(r"\\[123]a&H[0-9A-Fa-f]{2}&", "", inner)
        inner = re.sub(r"\\alpha&H([0-9A-Fa-f]{2})&",
                       lambda a: f"\\4a&H{_alpha_over(int(a.group(1), 16), shadow_alpha):02X}&", inner)
        return "{" + inner + "\\1a&HFF&\\2a&HFF&\\3a&HFF&}"

    return "{" + tags + f"\\4a&H{shadow_alpha:02X}&\\1a&HFF&\\2a&HFF&\\3a&HFF&}}" + re.sub(r"\{([^}]*)\}", block, text)


def _glitch_line(words: list, texts: list[str], show: float, end: float, hot: set[str], x: int, y: int, font: int,
                 blur: str, base: str, high: str) -> tuple[str, list[str]]:
    """One lyric line in the glitch effect (build_karaoke_ass): (the line's text, its burst events). The line
    breaks in for 0.24 s: it blinks while red and cyan copies split apart and snap together and a torn slice jumps
    sideways; on every sung word in `hot` (drawn in the highlight colour) the same happens for 4 frames. Between
    bursts the line is solid and fully opaque: no copies or see-through frames linger."""
    marked = [_bare(w.text) in hot for w in words]
    bursts: list[float] = [show]
    for w, m in zip(words, marked):
        if m and w.start - bursts[-1] > 0.35:
            bursts.append(w.start)
    body = " ".join(f"{{\\c{high if m else base}}}{t}" for t, m in zip(texts, marked))
    plain = " ".join(texts)
    # the break-in: out for 2 frames, in, a dimmed frame, then solid from 170 ms; a hit: one dimmed frame
    flicker = (r"\alpha&HFF&\t(66,67,\alpha&H00&)\t(120,121,\alpha&H90&)\t(170,171,\alpha&H00&)"
               + "".join(f"\\t({o},{o + 1},\\alpha&H70&)\\t({o + 40},{o + 41},\\alpha&H00&)"
                         for o in (round((b - show) * 1000) for b in bursts[1:])))
    d = max(5, font // 7)  # how far the colour copies split
    main = f"{{\\pos({x},{y}){blur}\\fad(0,160){flicker}}}{body}"
    out = []
    for i, b in enumerate(bursts):
        ms = 240 if i == 0 else 133  # the break-in / a hit (4 frames at 30 fps)
        split = d if i == 0 else max(3, d // 2)
        stop = min(b + ms / 1000, end)
        if stop <= b:
            continue
        # the copies slide together and are gone (alpha to invisible) by the end of the burst: nothing lingers
        copy = f"\\bord0\\shad0\\blur1\\alpha&H20&\\t({ms // 2},{ms},\\alpha&HFF&)"
        out.append(f"Dialogue: 1,{_ts(b)},{_ts(stop)},Lyric,,0,0,0,,"
                   f"{{\\move({x + split},{y},{x},{y},0,{ms}){copy}\\1c&H3C2DFF&}}{plain}")
        out.append(f"Dialogue: 1,{_ts(b)},{_ts(stop)},Lyric,,0,0,0,,"
                   f"{{\\move({x - split},{y},{x},{y},0,{ms}){copy}\\1c&HFFF02D&}}{plain}")
        tear = min(b + (0.1 if i == 0 else 0.066), end)  # a slice of the line torn sideways for 2-3 frames
        out.append(f"Dialogue: 3,{_ts(b)},{_ts(tear)},Lyric,,0,0,0,,"
                   f"{{\\pos({x + 2 * split},{y})\\clip(0,{y - font // 4},{x * 2},{y + font // 10}){blur}}}{body}")
    return main, out


def _rounded(w: float, h: float, r: float) -> str:
    """An ASS drawing of a w x h rectangle with corners of radius r (from 0,0)."""
    k = r * 0.45  # bezier handle: close enough to a quarter circle
    return (f"m {r:.0f} 0 l {w - r:.0f} 0 b {w - k:.0f} 0 {w:.0f} {k:.0f} {w:.0f} {r:.0f} l {w:.0f} {h - r:.0f} "
            f"b {w:.0f} {h - k:.0f} {w - k:.0f} {h:.0f} {w - r:.0f} {h:.0f} l {r:.0f} {h:.0f} "
            f"b {k:.0f} {h:.0f} 0 {h - k:.0f} 0 {h - r:.0f} l 0 {r:.0f} b 0 {k:.0f} {k:.0f} 0 {r:.0f} 0")


def _circle(cx: float, cy: float, r: float) -> str:
    """An ASS drawing of a circle (four bezier quarters)."""
    k = r * 0.5523
    return (f"m {cx:.1f} {cy - r:.1f} b {cx + k:.1f} {cy - r:.1f} {cx + r:.1f} {cy - k:.1f} {cx + r:.1f} {cy:.1f} "
            f"b {cx + r:.1f} {cy + k:.1f} {cx + k:.1f} {cy + r:.1f} {cx:.1f} {cy + r:.1f} "
            f"b {cx - k:.1f} {cy + r:.1f} {cx - r:.1f} {cy + k:.1f} {cx - r:.1f} {cy:.1f} "
            f"b {cx - r:.1f} {cy - k:.1f} {cx - k:.1f} {cy - r:.1f} {cx:.1f} {cy - r:.1f}")


def now_playing_events(title: str, label: str, start: float, length: float, size: tuple[int, int], font: str,
                       accent: str) -> list[str]:
    """A "now playing" card in the top-left corner, the way playlist channels show the song: a dark rounded card
    with `label` (the channel or "NOW PLAYING"), the song `title`, a progress bar that fills over `length` seconds
    from `start`, and a vinyl record spinning at its right edge. `accent`: the record label's colour (#RRGGBB)."""
    from .styles import ass_color

    W, H = size
    u = min(W, H) / 1080  # everything scales with the frame's short side
    x, y, w, h = round(42 * u), round(42 * u), round(600 * u), round(150 * u)
    r = 64 * u  # the record
    cx, cy = w - 22 * u - r, h / 2
    pad = 30 * u
    text_w = cx - r - 26 * u - pad  # room left of the record
    end = start + length
    t0, t1 = _ts(start), _ts(end)
    fade = r"\fad(500,800)"
    at = f"\\an7\\pos({x},{y})"
    out = [f"Dialogue: 5,{t0},{t1},Lyric,,0,0,0,,{{{at}{fade}\\bord0\\shad0\\blur0\\1c&H1E1A18&\\1a&H38&\\p1}}"
           f"{_rounded(w, h, 26 * u)}"]
    # the record: black disc with grooves, a coloured label with a light spot that shows it turning
    spin = round(length * 0.55 * 360)  # 33 rpm
    org = f"\\org({x + cx:.0f},{y + cy:.0f})"
    turn = f"\\t(0,{round(length * 1000)},\\frz{-spin})"

    def disc(layer: int, dx: float, dy: float, radius: float, tags: str) -> None:
        # every circle in the same square (the record's), placed by its top-left corner, so they share a centre
        out.append(f"Dialogue: {layer},{t0},{t1},Lyric,,0,0,0,,{{\\an7\\pos({x + cx - r:.0f},{y + cy - r:.0f})"
                   f"{org}{fade}\\bord0\\shad0{tags}\\p1}}{_circle(r + dx, r + dy, radius)}")

    disc(6, 0, 0, r, "\\blur0.6\\1c&H101010&")
    for g in (0.86, 0.72, 0.58):  # grooves
        disc(7, 0, 0, r * g, f"\\bord{max(1, round(1.2 * u))}\\blur0.6\\1a&HFF&\\3c&H3A3A3A&")
    disc(8, 0, 0, r * 0.36, f"\\blur0.4\\1c{ass_color(accent)}")  # the label
    disc(9, r * 0.2, -r * 0.12, r * 0.07, f"\\blur1.5\\1c&HFFFFFF&\\1a&H60&{turn}")  # a light spot: it turns
    disc(9, 0, 0, r * 0.06, "\\1c&H101010&")  # the spindle hole
    # the words: the label small and dim, the title big; cut short with an ellipsis rather than run under the record
    label_px, title_px = round(22 * u), round(40 * u)
    title = _esc(title)
    most = max(4, int(text_w / (title_px * 0.56)))
    if len(title) > most:
        title = title[:most - 1].rstrip() + "…"
    out.append(f"Dialogue: 9,{t0},{t1},Lyric,,0,0,0,,{{\\an7\\pos({x + pad:.0f},{y + 26 * u:.0f}){fade}\\fn{font}"
               f"\\fs{label_px}\\b1\\fsp{round(2 * u)}\\bord0\\shad0\\blur0\\1c&HFFFFFF&\\1a&H70&}}{_esc(label.upper())}")
    out.append(f"Dialogue: 9,{t0},{t1},Lyric,,0,0,0,,{{\\an7\\pos({x + pad:.0f},{y + 54 * u:.0f}){fade}\\fn{font}"
               f"\\fs{title_px}\\b1\\bord0\\shad0\\blur0\\1c&HFFFFFF&}}{title}")
    # the progress bar: a dim track and a bright fill whose clip widens from nothing to the whole bar
    bx, by, bw, bh = x + pad, y + h - 34 * u, text_w, max(4, round(6 * u))
    bar = _rounded(bw, bh, bh / 2)
    out.append(f"Dialogue: 9,{t0},{t1},Lyric,,0,0,0,,{{\\an7\\pos({bx:.0f},{by:.0f}){fade}\\bord0\\shad0\\blur0"
               f"\\1c&HFFFFFF&\\1a&HC0&\\p1}}{bar}")
    out.append(f"Dialogue: 10,{t0},{t1},Lyric,,0,0,0,,{{\\an7\\pos({bx:.0f},{by:.0f}){fade}\\bord0\\shad0\\blur0"
               f"\\1c&HFFFFFF&\\clip({bx:.0f},{by - 4:.0f},{bx:.0f},{by + bh + 4:.0f})"
               f"\\t(0,{round(length * 1000)},\\clip({bx:.0f},{by - 4:.0f},{bx + bw:.0f},{by + bh + 4:.0f}))\\p1}}{bar}")
    return out


def _neon_title(text: str, start: float, end: float, style: "LyricStyle", font: int, size: tuple[int, int],
                at: tuple[int, int], fit: float = 0.8, lang: str = "en") -> list[str]:
    """A title that flickers on like a neon tube, centred on `at`: a white-hot core with a crisp outline in the neon
    colour, over a wide blurred glow in that colour (two layers, both switched by the same flicker, so they never
    drift into a double image). As big as the lyrics allow (~1.9x) but no wider than `fit` of the frame: two
    stacked lines when one is too wide. Flickers on over ~0.4 s, holds steady, then one clean 0.5 s fade."""
    from .styles import ass_color

    W, H = size
    neon = ass_color(style.highlight)
    px = round(font * 1.9)
    room = W * fit

    def wide(t: str, s: int) -> float:
        return _text_width(t, style.font, s, lang, spacing=round(s * 0.08)) + 2 * max(3, s // 22)

    rows = [text]
    words = text.split()
    if wide(text, px) > room and len(words) > 1:
        rows = _balance(words, 2, lambda t: wide(t, px))
    widest = max(wide(r, px) for r in rows)
    if widest > room:
        px = max(round(font * 0.9), int(px * room / widest))
    # kept inside the frame (its glow too) wherever `at` asks for it
    half_w = max(wide(r, px) for r in rows) / 2 + px * 0.3
    half_h = len(rows) * px / 2 + px * 0.3
    x = round(min(max(at[0], half_w), W - half_w))
    y = round(min(max(at[1], half_h), H - half_h))
    # off, on, off, dim, on, half, on (a tube catching), all within 0.4 s; then steady until a single fade out.
    # `on`: the layer's alpha when lit (the glow stays a little see-through)
    def flicker(on: int) -> str:
        steps = ((0, 30, on), (80, 90, 0xD0), (150, 170, on), (230, 240, 0xA0), (290, 310, on), (350, 360, 0x60),
                 (380, 400, on))
        return (r"\alpha&HFF&" + "".join(f"\\t({a},{b},\\alpha&H{max(v, on):02X}&)" for a, b, v in steps)
                + r"\fad(0,500)")

    common = (f"\\an5\\pos({x},{y})\\fn{style.font}\\fs{px}\\b1\\fsp{round(px * 0.08)}\\q2"
              f"\\fscx100\\fscy100")
    lines = r"\N".join(rows)
    # the glow: a wide soft halo of neon light; the core: near-white letters, a neon edge, a hair of bloom
    glow = (f"{{{common}\\1c{neon}\\3c{neon}\\bord{max(10, px // 6)}\\shad0\\blur{max(14, px // 4)}"
            f"{flicker(0x18)}}}{lines}")
    core = (f"{{{common}\\1c&HFFF8FF&\\3c{neon}\\bord{max(4, px // 15)}\\shad0\\blur2{flicker(0)}}}{lines}")
    return [f"Dialogue: 3,{_ts(start)},{_ts(end)},Lyric,,0,0,0,,{glow}",
            f"Dialogue: 4,{_ts(start)},{_ts(end)},Lyric,,0,0,0,,{core}"]


THUMB_STYLES = ("bold", "box", "stacked")
BOX_YELLOW = "&H0000D7FF&"
BLACK = "&H00000000&"
RED = "&H001E1EE6&"
_STOPWORDS = {"a", "an", "the", "of", "to", "in", "on", "for", "and", "or", "is", "are", "was", "be", "it", "this",
              "that", "you", "your", "my", "i", "we", "with", "at", "by", "from", "how", "why", "what", "about",
              "they", "their", "these", "those", "through", "into", "know", "didnt", "dont", "cant", "will", "can",
              "have", "has", "just", "really", "very", "most", "more", "than", "when", "who", "do", "does"}


def _bare(word: str) -> str:
    return re.sub(r"[^\w]", "", word.lower())


def auto_emphasis(text: str) -> str:
    """Word(s) to highlight when none are given: a number if there is one, else the longest meaningful word."""
    words = _esc(text).split()
    if not words:
        return ""
    numbers = [w for w in words if any(c.isdigit() for c in w)]
    if numbers:
        return numbers[0]
    content = [w for w in words if _bare(w) not in _STOPWORDS] or words
    return max(content, key=lambda w: len(_bare(w)))


def _wrap(words: list[str], max_chars: int) -> list[list[str]]:
    lines: list[list[str]] = [[]]
    for w in words:
        if lines[-1] and len(" ".join(lines[-1] + [w])) > max_chars:
            lines.append([])
        lines[-1].append(w)
    return lines


def build_thumbnail_ass(text: str, profile: LangProfile, style: str = "bold", emphasis: str = "",
                        size: tuple[int, int] = (WIDTH, HEIGHT)) -> str:
    """Cover headline sized to fill the width, with the key word(s) in `emphasis` picked out.

    bold: white, heavy outline, key word yellow.  box: black on yellow boxes, key word red.
    stacked: a word or two per line, key word yellow and bigger.
    """
    W, H = size
    style = style if style in THUMB_STYLES else "bold"
    words = _esc(text).split()
    if profile.code != "km":
        words = [w.upper() for w in words]
    keys = {_bare(w) for w in _esc(emphasis or auto_emphasis(text)).split()} - {""}
    accent = RED if style == "box" else HIGHLIGHT
    base = BLACK if style == "box" else WHITE

    if profile.code == "km":
        # Khmer phrases can't be measured by letter count; one phrase per line keeps clusters intact
        lines = [[w] for w in words] if style == "stacked" else _wrap(words, 12)
        longest = max((sum(len(w) for w in line) for line in lines), default=1)
        # code points include stacked subscripts and vowel signs, so a "letter" is narrower than it counts
        size = round(max(110, min(profile.font_size * 2.6, W * 0.86 / max(longest * 0.34, 1))))
    else:
        lines = _wrap(words, 8 if style == "stacked" else 10)
        longest = max((len(" ".join(line)) for line in lines), default=1)
        # Arial Bold caps average ~0.64 em wide
        size = round(max(100, min(240, W * 0.88 / (longest * 0.64))))

    grow = r"\fscx115\fscy115" if style == "stacked" else ""
    on, off = f"{{\\c{accent}{grow}}}", f"{{\\c{base}\\fscx100\\fscy100}}"

    def word(w: str) -> str:
        if _bare(w) in keys:
            return on + w + off
        if profile.code == "km":
            # Khmer writes words without spaces, so the key word may sit inside a longer phrase
            # (match the raw text: _bare() would drop Khmer vowel signs)
            for key in sorted(_esc(emphasis or auto_emphasis(text)).split(), key=len, reverse=True):
                if key in w:
                    return w.replace(key, on + key + off, 1)
        return w

    body = r"\N".join(" ".join(word(w) for w in line) for line in lines)
    if style == "box":
        # BorderStyle 3 draws an opaque box per line in the outline colour
        thumb_style = f"Thumb,{profile.font_name},{size},{BLACK},{BLACK},{BOX_YELLOW},&H66000000&,-1,0,0,0,100,100,0,0,3,18,6,5,60,60,0,1"
    else:
        outline = max(8, size // 11)
        thumb_style = f"Thumb,{profile.font_name},{size},{WHITE},{WHITE},{BLACK},&H80000000&,-1,0,0,0,100,100,0,0,1,{outline},{outline - 2},5,60,60,0,1"
    # upper-middle: clear of the like/comment buttons and caption bar that cover the bottom of Shorts/TikTok
    y = round(H * (0.40 if style == "stacked" else 0.36)) if H > W else H // 2
    return f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: {thumb_style}

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:00:00.00,9:00:00.00,Thumb,,0,0,0,,{{\\pos({W // 2},{y})}}{body}
"""
