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
                    # the word being spoken gets a quick 106% bump as it lights up (the group's first word rides the
                    # group's pop instead); the word after it is set back to 100% so the bump stays on that word
                    scale = (r"\fscx100\fscy100\t(0,60,\fscx106\fscy106)\t(60,160,0.6,\fscx100\fscy100)"
                             if wj == wi and wi > 0 else r"\fscx100\fscy100" if wj == wi + 1 and wi > 0 else "")
                    parts.append(f"{{\\c{color}{scale}}}{_esc(_case(w.text, style.case, profile.code))}")
                # each group pops in: 80% -> 108% -> 100% over 130 ms
                pop = (r"{\fscx80\fscy80\t(0,80,0.7,\fscx108\fscy108)\t(80,130,\fscx100\fscy100)}"
                       if wi == 0 else "")
                text = f"{{\\pos({WIDTH // 2},{cap_y}){blur}}}{pop}" + " ".join(parts)
                lines.append(f"Dialogue: 0,{_ts(start)},{_ts(end)},Caption,,0,0,0,,{text}")
    return header + "\n".join(lines + (extra or [])) + "\n"


HOOK_SIDE = 64  # px kept clear on each side of the hook's box (1080 wide)
HOOK_TOP = 130  # the box never starts above this: the platforms' top bar


def _hook_events(text: str, start: float, end: float, top: int, family: str, px: int, lang: str) -> list[str]:
    """The hook: dark words on one tidy white rounded card (instead of the ragged per-line boxes BorderStyle 3
    draws), the same padding on every side, at most 2 lines (3 only when even a smaller size can't fit 2), a soft
    shadow under the card. Top edge at `top`; fades in over its first 0.15 s."""
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
    # a quick fade in (all three layers together), but never on the video's first frame: that's what the feed shows,
    # and the hook has to be readable on it
    pop = r"\fad(150,0)" if start > 0.05 else ""
    card = _rounded(w, h, size * 0.2)
    q = r"\q2" if fits else ""  # no wrapping: the rows are already measured to fit
    # every part centred on the same point (\an5)
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
                     f"{{\\an5\\pos({x},{y})\\fs{fs}\\c{color}\\fad(150,120)}}{text}")
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
    stays until the next line starts or `hold` s after its last word. karaoke, fill and fade lines enter rising
    ~16 px, fading in and coming into focus (0.25 s, easing out) and fade out over 0.2 s; when the next line follows
    straight on, the fade starts 0.12 s before it, so the two cross-fade (the only time two lines overlap). Effects:
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
    # karaoke / fill / fade entrance and exit (seconds), how far a line rises as it enters, the line's own blur
    fade_in, fade_out, cross = 0.25, 0.2, 0.12
    rise = round(16 * min(W, H) / 1080)
    sharp = float(blur[5:]) if blur else 0.0

    def enter(s: float, e: float, show: float, gone: float) -> str:
        """The override block that places one event [s, e] of a line on screen from `show` until `gone`: over its
        first 0.25 s the line fades in, slides up `rise` px and comes into focus (blur 6 -> its own, easing out);
        over its last 0.2 s it fades out. Times are per event (a karaoke line is one event per word), so each
        picks the motion up where the previous one left it; its shadow copy (_backing) keeps these tags, so it
        moves and fades with it."""
        x0, d = W // 2, max(e - s, 0.001)
        tin = min(fade_in, max((gone - show) / 2, 0.04))
        tout = min(fade_out, max((gone - show) / 2, 0.04))

        def alpha(t: float) -> int:  # 0 opaque .. 255 gone
            k = min(max((t - show) / tin, 0.0), 1.0, max((gone - t) / tout, 0.0))
            return round(255 * (1 - k))

        o = s - show
        if o < tin - 0.005:
            ms = round((tin - o) * 1000)
            k = o / tin
            tags = (f"\\move({x0},{y + rise * (1 - k):.1f},{x0},{y},0,{ms})"
                    f"\\blur{6 + (sharp - 6) * k ** 0.4:.2f}\\t(0,{ms},0.4,\\blur{sharp:g})")
        else:
            tags = f"\\pos({x0},{y}){blur}"
        t2 = min(max(show + tin - s, 0.0), d)
        t3 = min(max(gone - tout - s, t2), d)
        a1, a2, a3 = alpha(s), alpha(s + t2), alpha(e)
        if a1 or a2 or a3:
            tags += f"\\fade({a1},{a2},{a3},0,{round(t2 * 1000)},{round(t3 * 1000)},{round(d * 1000)})"
        return "{" + tags + "}"

    # when each line shows and ends (a line shows no earlier than the one before it ends)
    spans: dict[int, tuple[float, float]] = {}
    prev_end = 0.0
    for li, line in enumerate(lines):
        words = [w for w in line.words if _esc(w.text)]
        if words:
            next_start = lines[li + 1].start if li + 1 < len(lines) else float("inf")
            spans[li] = (max(prev_end, words[0].start - lead_in), min(next_start, words[-1].end + hold))
            prev_end = spans[li][1]
    order = sorted(spans)
    for li, line in enumerate(lines):
        words = [w for w in line.words if _esc(w.text)]
        if not words:
            continue
        texts = [_esc(_case(w.text, style.case, profile.code)) for w in words]
        next_start = lines[li + 1].start if li + 1 < len(lines) else float("inf")
        show, line_end = spans[li]
        later = [spans[k][0] for k in order if k > li]
        # straight into the next line: fade out from `cross` s before it shows, cross-fading with its entrance;
        # else fade out over the line's last 0.2 s
        gone = line_end + fade_out - cross if later and later[0] - line_end < 0.05 else line_end

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
            dialogue(show, gone, enter(show, gone, show, gone) + body)
        elif style.effect == "fade":
            dialogue(show, gone, enter(show, gone, show, gone) + " ".join(texts))
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
            def karaoke(s: float, e: float, sung: int) -> None:
                dialogue(s, e, enter(s, e, show, gone) + " ".join(
                    f"{{\\c{high}\\1a&H00&}}{t}" if j < sung else f"{{\\c{base}\\1a&H{unsung:02X}&}}{t}"
                    for j, t in enumerate(texts)))

            karaoke(show, words[0].start, 0)
            for wi, w in enumerate(words):
                karaoke(w.start, words[wi + 1].start if wi + 1 < len(words) else gone, wi + 1)
        if (landscape and style.effect in ("karaoke", "fill") and li + 1 < len(lines)
                and next_start - line_end < 2.5 and _esc(lines[li + 1].text)):
            # fades in with the line above it and out with it (as that next line rises into its place)
            dialogue(show, gone, next_pos + f"{{\\fad({round(fade_in * 1000)},{round(fade_out * 1000)})}}"
                     + _esc(_case(lines[li + 1].text, style.case, profile.code)), "LyricNext")
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
    from `start`, and a vinyl record spinning at its right edge. `accent`: the record label's colour (#RRGGBB).
    Fully opaque for its first 10 s, then dimmed to ~65% for the rest of the song."""
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
    # after 10 s the whole card settles back to ~65% opacity over 1 s (out of the way, still there): each layer's
    # fill and edge alphas go to themselves seen through 35% transparency, so the parts keep their relative looks
    if length > 11:
        def settle(m: re.Match) -> str:
            tags = m.group(1)
            a1 = re.search(r"\\1a&H([0-9A-Fa-f]{2})&", tags)
            a3 = re.search(r"\\3a&H([0-9A-Fa-f]{2})&", tags)
            a1, a3 = (int(a.group(1), 16) if a else 0 for a in (a1, a3))
            return (f"{{{tags}\\t(10000,11000,\\1a&H{_alpha_over(a1, 0x59):02X}&"
                    f"\\3a&H{_alpha_over(a3, 0x59):02X}&)}}")

        out = [re.sub(r"\{([^}]*)\}", settle, e, count=1) for e in out]
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


THUMB_YELLOW = "&H0000D4FF&"  # #FFD400: the cover's key word (warmer than the karaoke yellow, reads on sky and snow)
# the heavy display faces a cover headline is set in, best first: (family libass looks up, font file). Segoe UI Black
# keeps its counters open at feed size, where Impact's close up into blobs; Arial Black next, Arial Bold last
THUMB_FACES = (("Segoe UI Black", "seguibl.ttf"), ("Arial Black", "ariblk.ttf"), ("Arial", "arialbd.ttf"))


def thumb_font(profile: LangProfile) -> tuple[str, str]:
    """(family, file) a cover headline is set in: the heaviest installed face for Latin text; the language's own
    font for Khmer (no Latin black face has Khmer letters)."""
    from .styles import font_path

    if profile.code != "km":
        for family, file in THUMB_FACES:
            if font_path(file):
                return family, file
    return profile.font_name, profile.font_file


def _cap_metrics(file: str) -> tuple[float, float]:
    """(cap height, how far the caps' middle sits below the middle of the line) of a font, both as fractions of the
    ASS font size (ascent+descent), so a headline can be spaced and placed by its letters rather than by the font's
    tall line box. Arial-like values without the file."""
    from .styles import font_path

    try:
        from PIL import ImageFont

        path = font_path(file)
        if path:
            f = ImageFont.truetype(str(path), 200)
            asc, desc = f.getmetrics()
            top, bottom = f.getbbox("H", anchor="ls")[1::2]  # top is above the baseline: negative
            cap = (bottom - top) / (asc + desc)
            return cap, (asc - (bottom - top) / 2 - (asc + desc) / 2) / (asc + desc)
    except Exception:
        pass
    return 0.64, 0.12


def _thumb_width(text: str, family: str, file: str, px: float, lang: str) -> float:
    """How wide libass draws headline `text` at size `px`: measured in its font (_text_width, or the file itself for
    a face styles.FONTS doesn't list, e.g. Arial Black); an emoji (drawn in colour by emoji.py) is about a square."""
    from .emoji import EMOJI
    from .styles import FONTS, font_path

    emoji = len(EMOJI.findall(text))
    text = EMOJI.sub("", text)
    if lang == "km":
        # PIL here has no shaping: a subscript (coeng + consonant) or a vowel sign above/below would be counted as a
        # letter of its own, when shaped it stacks under/over the one before; measure what takes room on the line
        text = re.sub("[ិ-ួំ-៑៝​]", "", re.sub("្.", "", text))
        return _text_width(text, family, px, lang) * 1.06 + emoji * px * 0.85
    if family in FONTS.get(lang, FONTS["en"]) or family in FONTS["en"]:
        return _text_width(text, family, px, lang) + emoji * px * 0.85
    try:
        from PIL import ImageFont

        f = ImageFont.truetype(str(font_path(file)), 200)
        asc, desc = f.getmetrics()
        return f.getlength(text) * px / (asc + desc) + emoji * px * 0.85
    except Exception:
        return px * 0.62 * len(text) + emoji * px * 0.85


def _split_even(words: list[str], lines: int, width) -> list[str]:
    """`words` in `lines` lines (in order) whose widest line is as narrow as possible (`width(str)`); any number of
    lines (_balance stops at three)."""
    from itertools import combinations

    n = len(words)
    lines = max(1, min(lines, n))
    best, best_w = [" ".join(words)], float("inf")
    for cut in combinations(range(1, n), lines - 1):
        bounds = (0, *cut, n)
        parts = [" ".join(words[a:b]) for a, b in zip(bounds, bounds[1:])]
        w = max(width(p) for p in parts)
        if w < best_w - 1e-6:
            best, best_w = parts, w
    return best


def _overlap(a: tuple, b: tuple | None) -> float:
    """Area shared by two (x0, y0, x1, y1) boxes."""
    if not b:
        return 0.0
    return max(0.0, min(a[2], b[2]) - max(a[0], b[0])) * max(0.0, min(a[3], b[3]) - max(a[1], b[1]))


def build_thumbnail_ass(text: str, profile: LangProfile, style: str = "bold", emphasis: str = "",
                        size: tuple[int, int] = (WIDTH, HEIGHT), subject: tuple | None = None,
                        head: tuple | None = None) -> str:
    """Cover headline as big as it can be in two lines (three or four only when two would be too small), with the
    key word(s) in `emphasis` picked out, placed clear of the picture's subject.

    bold: white, thick black outline and a soft drop shadow, key word yellow.  box: black on yellow boxes, key word
    red.  stacked: a word or two per line, key word yellow and bigger.
    `subject` / `head`: where the picture's subject and its head (face) are, as (x0, y0, x1, y1) fractions of the
    frame (pipeline finds them from a depth map). The headline then goes where it covers the face least: on a 9:16
    cover inside the centre square (the 1:1 and 3:4 grid crops), normally above the face, else below it; on a 16:9
    cover beside the subject or in a band above/below it, never on YouTube's duration badge. Without them, the old
    fixed places (upper-middle on 9:16, the middle on 16:9). A dark feathered gradient sits behind the words so they
    read on any picture without a box over the subject.
    """
    W, H = size
    style = style if style in THUMB_STYLES else "bold"
    km = profile.code == "km"
    lang = "km" if km else "en"
    words = _esc(text).split()
    if not km:
        words = [w.upper() for w in words]
    if not words:
        words = [""]
    keys = {_bare(w) for w in _esc(emphasis or auto_emphasis(text)).split()} - {""}
    family, file = thumb_font(profile)
    # Khmer: stacked subscripts below and vowel signs above fill most of the line box, so it's spaced by the box
    cap, drop = (0.78, 0.0) if km else _cap_metrics(file)
    unit = min(W, H) / 1080  # sizes below are for a 1080-wide 9:16 frame / a 1080-high 16:9 one
    margin = round(60 * unit)
    least = round(140 * unit)  # caps ~70 px on 1080: what still reads at feed size (~170 px wide)
    most = round((260 if style == "stacked" else 230) * unit)
    grow = 1.15 if style == "stacked" else 1.0

    def edge(px: float) -> float:  # outline (bold/stacked) or box padding (box), each side
        return px * (0.13 if style == "box" else 0.07)

    def width(line: str, px: float) -> float:
        w = _thumb_width(line, family, file, px, lang) + 2 * edge(px)
        if grow > 1:  # the key word is drawn bigger
            w += sum(_thumb_width(x, family, file, px, lang) for x in line.split() if _bare(x) in keys) * (grow - 1)
        return w

    def step(px: float) -> float:  # baseline to baseline: tight caps, outlines/boxes just clear of each other
        if km:
            return px * 1.0
        # (boxes: each 0.15 of the size above and below the caps, so neighbouring lines' boxes just meet)
        return px * (cap + (0.30 if style == "box" else 0.22)) * (1.06 if grow > 1 else 1.0)

    def ink(lines: list[str], px: float) -> tuple[float, float]:  # (width, height) of the drawn block
        return (max(width(r, px) for r in lines),
                (len(lines) - 1) * step(px) + px * cap * (grow if grow > 1 else 1) + 2 * edge(px))

    def fit(avail: float, tall: float) -> tuple[list[str], int]:
        """The lines and size: two lines unless they'd be smaller than `least`, then three, then four (stacked: a
        word or two per line); as big as fits `avail` wide and `tall` high, at most `most`."""
        n = len(words)
        if style == "stacked":  # never one line: stacking is the look
            counts = list(range(max(min(n, 2), min((n + 1) // 2, 4)), min(n, 5) + 1))
        else:
            counts = [1] if n == 1 else [c for c in (2, 3, 4, 5) if c <= n]
        options = []
        # a headline too long for the band at the least size may take a taller block before it gets smaller
        for room in (tall, tall * 1.4):
            for c in counts:
                rows = _split_even(words, c, lambda t: width(t, 100))
                w100, h100 = ink(rows, 100)
                px = min(most, 100 * avail / w100, 100 * room / h100)
                options.append((rows, px))
                if px >= least:
                    return rows, int(px)
        rows, px = max(options, key=lambda o: o[1])  # never fits at the least size: the biggest it can be
        return rows, int(px)

    # where it goes: candidate layouts, each scored by how much of the face (and, less, the subject) it covers
    pad_y, pad_x = 0.035 * H, 0.03 * W
    face = (head[0] * W - pad_x, head[1] * H - pad_y, head[2] * W + pad_x, head[3] * H + pad_y) if head else None
    body = (subject[0] * W, subject[1] * H, subject[2] * W, subject[3] * H) if subject else None
    # YouTube draws the video's length over the bottom-right corner (~140x80 of a 1280x720 thumbnail)
    badge = (W - 150 * W / 1280, H - 90 * H / 720, W, H) if W > H else None
    layouts = []  # (cost, lines, px, x, y, align): y = middle of the block's ink, x per align
    if H > W:
        lo, hi = (H - W) / 2, (H + W) / 2  # the centre square: what the 1:1 and 3:4 grid crops keep
        rows, px = fit(W - 2 * margin, 0.26 * H)
        bw, bh = ink(rows, px)
        if not face and not body:
            ys = [H * (0.40 if style == "stacked" else 0.36)]  # upper-middle: clear of the Shorts/TikTok buttons
        else:
            first, last = lo + 10 + bh / 2, hi - 10 - bh / 2
            ys = [first + k * 8 for k in range(int(max(last - first, 0) // 8) + 1)] if last > first else [H / 2]
        for y in ys:
            box = (W / 2 - bw / 2, y - bh / 2, W / 2 + bw / 2, y + bh / 2)
            area = bw * bh
            # two homes: the upper band (y ~430-820 of 1920, the face below it: the usual cover, the eye reads down
            # into the picture) or, when the head's up there, the lower band (~1100-1450), not wedged under the chin
            home = min(abs(y - 0.33 * H), abs(y - 0.665 * H) + 0.03 * H) / H
            cost = 10 * _overlap(box, face) / area + _overlap(box, body) / area + 0.4 * home
            layouts.append((cost, rows, px, W / 2, y, 5))
    else:
        bands = [("band", W - 2 * margin, 0.42 * H)]
        if face or body:
            bands += [("left", W * 0.56 - 1.5 * margin, 0.8 * H), ("right", W * 0.56 - 1.5 * margin, 0.8 * H)]
        for kind, avail, tall in bands:
            rows, px = fit(avail, tall)
            bw, bh = ink(rows, px)
            if not face and not body:
                ys = [H / 2]
            else:
                first, last = 0.07 * H + bh / 2, 0.93 * H - bh / 2
                ys = [first + k * 8 for k in range(int(max(last - first, 0) // 8) + 1)] if last > first else [H / 2]
            x, align = {"band": (W / 2, 5), "left": (margin, 4), "right": (W - margin, 6)}[kind]
            x0 = {"band": W / 2 - bw / 2, "left": margin, "right": W - margin - bw}[kind]
            for y in ys:
                box = (x0, y - bh / 2, x0 + bw, y + bh / 2)
                area = bw * bh
                cost = (10 * _overlap(box, face) / area + _overlap(box, body) / area + 10 * _overlap(box, badge) / area
                        + 0.2 * abs(y - H / 2) / H - 0.5 * px / most)  # bigger letters win a close call
                layouts.append((cost, rows, px, x, y, align))
    _, rows, px, x, y, align = min(layouts, key=lambda o: o[0])
    bw, bh = ink(rows, px)
    x0 = {5: x - bw / 2, 4: x, 6: x - bw}[align]
    top = y - bh / 2

    out = round(edge(px))
    accent = RED if style == "box" else THUMB_YELLOW
    base = BLACK if style == "box" else WHITE
    big = r"\fscx115\fscy115" if grow > 1 else ""

    def word(w: str, shade: str = "") -> str:
        """`w` with the key word picked out; `shade` (an alpha) draws it as the drop shadow instead: all black, its
        emoji hidden (emoji.py would draw them in colour) but still taking their room."""
        if shade:
            from .emoji import EMOJI

            back = f"{{\\1a{shade}\\3a{shade}}}"
            w = EMOJI.sub(lambda m: "{\\alpha&HFF&}" + m.group() + back, w)
            on, off = f"{{{big}}}", "{\\fscx100\\fscy100}"
        else:
            on, off = f"{{\\c{accent}{big}}}", f"{{\\c{base}\\fscx100\\fscy100}}"
        if _bare(w) in keys and not km:
            return on + w + off
        if km:
            # Khmer writes words without spaces, so the key word may sit inside a longer phrase
            # (match the raw text: _bare() would drop Khmer vowel signs)
            for key in sorted(_esc(emphasis or auto_emphasis(text)).split(), key=len, reverse=True):
                if key in w:
                    return w.replace(key, on + key + off, 1)
        return w

    events = []
    # the gradient: black, ~38% at its heart (25% behind boxes, which carry themselves), feathered over ~6% of the
    # frame, from the headline's side of the picture to just past the words, so the subject stays bright
    feather = round(0.065 * min(W, H))
    reach = round(0.05 * min(W, H))
    if align == 4:
        band = (-feather, -feather, x0 + bw + reach, H + feather)
    elif align == 6:
        band = (x0 - reach, -feather, W + feather, H + feather)
    elif y < H / 2:
        band = (-feather, -feather, W + feather, top + bh + reach)
    else:
        band = (-feather, top - reach, W + feather, H + feather)
    shade = "&HC0&" if style == "box" else "&H9E&"
    a, b, c, d = (round(v) for v in band)
    events.append(f"Dialogue: 0,0:00:00.00,9:00:00.00,Plain,,0,0,0,,{{\\an7\\pos(0,0)\\p1\\bord0\\shad0"
                  f"\\1c&H000000&\\1a{shade}\\blur{feather}}}m {a} {b} l {c} {b} {c} {d} {a} {d}{{\\p0}}")
    for i, row in enumerate(rows):
        # each line on its own, so the leading is set by the letters (libass would space them by the tall line box)
        mid = top + edge(px) + px * cap * (grow if grow > 1 else 1) / 2 + i * step(px)
        line_y = round(mid - drop * px)
        pos = f"\\an{align}\\pos({round(x)},{line_y})"
        if style == "box":
            # the yellow box, drawn to the letters (libass's BorderStyle 3 box spans the font's whole tall line box,
            # so stacked lines' boxes overlapped the words above): the line's measured width plus padding, 0.15 of
            # the size above and below the caps, over a crisp 45% black drop shadow
            w = width(row, px)
            bx = {5: x - w / 2, 4: x, 6: x - w}[align]
            half = px * (cap / 2 + 0.15)
            r = [round(v) for v in (bx, mid - half, bx + w, mid + half)]
            off = max(4, round(px * 0.06))
            for colour, alpha, o in (("&H000000&", "&H73&", off), (BOX_YELLOW, "&H00&", 0)):
                events.append(f"Dialogue: 1,0:00:00.00,9:00:00.00,Plain,,0,0,0,,{{\\an7\\pos({o},{o})\\p1\\bord0"
                              f"\\shad0\\1c{colour}\\1a{alpha}}}m {r[0]} {r[1]} l {r[2]} {r[1]} {r[2]} {r[3]} "
                              f"{r[0]} {r[3]}{{\\p0}}")
        else:
            # the soft drop shadow: 60% black, ~6% of the size down, blurred; its own layer under the crisp letters
            dx, dy = round(px * 0.035), round(px * 0.06)
            ghost = " ".join(word(w, "&H66&") for w in row.split())
            events.append(f"Dialogue: 1,0:00:00.00,9:00:00.00,Plain,,0,0,0,,{{\\an{align}\\pos({round(x) + dx},"
                          f"{line_y + dy})\\1c&H000000&\\3c&H000000&\\1a&H66&\\3a&H66&\\blur{max(3, round(px * 0.05))}}}"
                          f"{ghost}")
        events.append(f"Dialogue: 2,0:00:00.00,9:00:00.00,Thumb,,0,0,0,,{{{pos}}}"
                      + " ".join(word(w) for w in row.split()))
    if style == "box":
        # black letters straight on their boxes (drawn above)
        thumb_style = f"Thumb,{family},{px},{BLACK},{BLACK},{BLACK},&H00000000&,-1,0,0,0,100,100,0,0,1,0,0,5,0,0,0,1"
    else:
        thumb_style = f"Thumb,{family},{px},{WHITE},{WHITE},{BLACK},&H00000000&,-1,0,0,0,100,100,0,0,1,{out},0,5,0,0,0,1"
    # the gradient, boxes and drop shadow
    plain = f"Plain,{family},{px},{WHITE},{WHITE},{BLACK},&H00000000&,-1,0,0,0,100,100,0,0,1,{out},0,5,0,0,0,1"
    nl = "\n"
    return f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: {thumb_style}
Style: {plain}

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
{nl.join(events)}
"""
