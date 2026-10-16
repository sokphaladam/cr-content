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


def caption_styles(profile: LangProfile, style: "CaptionStyle", size: tuple[int, int] = (WIDTH, HEIGHT)) -> str:
    """The Caption and Headline style lines for `style` (see styles.CaptionStyle)."""
    from .styles import ass_color

    W, _ = size
    font = style.font or profile.font_name
    px = round(profile.font_size * {"s": 0.8, "m": 1.0, "l": 1.25}[style.size] * W / WIDTH)
    base = ass_color(style.color)
    # how the letters stand off the footage (same choices as the lyric videos)
    if style.outline == "box":
        border, outline, shadow, out_c, back_c = 3, max(10, px // 7), 0, "&H55000000&", "&H55000000&"
    elif style.outline == "shadow":
        border, outline, shadow, out_c, back_c = 1, 1, max(3, px // 22), "&H60000000&", "&H70000000&"
    elif style.outline == "glow":
        border, outline, shadow, out_c, back_c = 1, max(4, px // 18), 2, ass_color(style.highlight, 0x40), "&H70000000&"
    else:
        border, outline, shadow, out_c, back_c = 1, round(px * 7 / 92), 3, "&H00000000&", "&H80000000&"
    head = round(px * 0.8)
    return (f"Style: Caption,{font},{px},{base},{base},{out_c},{back_c},-1,0,0,0,100,100,0,0,{border},{outline},{shadow},5,90,90,0,1\n"
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
    blur = r"\blur3" if style.outline == "shadow" else r"\blur10" if style.outline == "glow" else ""
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
            lines.append(f"Dialogue: 2,{_ts(scene_start)},{_ts(scene_end)},Hook,,0,0,0,,"
                         f"{{\\an8\\pos({WIDTH // 2},{head_y})\\fscx80\\fscy80\\t(0,120,\\fscx100\\fscy100)}}"
                         f"{_esc(headline.upper())}")
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
                      title: tuple[str, float, float] | None = None) -> str:
    """Lyrics as karaoke, drawn in `style` (font, colours, size, position, effect; see styles.py).

    lines: align.LyricLine items (absolute word times). A line appears `lead_in` s before its first word and
    stays until the next line starts or `hold` s after its last word, so two lines never overlap. Effects:
    karaoke: the whole line shown, words change colour as they're sung.  fill: a smooth colour sweep through
    each word.  pop: words appear one by one with a little bounce.  fade: the whole line fades in and out.
    Landscape frames show the upcoming line dimmed underneath (karaoke and fill), like a lyric video.
    title: (text, start, end) the song's title flickering on like a neon sign in the sung-word colour (a cold open),
    away from the lyrics.
    """
    from .styles import LyricStyle, ass_color

    style = (style or LyricStyle()).clean(profile.code)
    W, H = size
    landscape = W > H
    font = round(profile.font_size * (0.85 if profile.code == "km" else 0.8))
    if landscape:
        font = round(font * 0.82)
    font = round(font * {"s": 0.8, "m": 1.0, "l": 1.25}[style.size])
    small = round(font * 0.72)
    base, high = ass_color(style.color), ass_color(style.highlight)

    # how the letters stand off the footage
    blur = ""
    if style.outline == "box":
        border, outline, shadow, out_c, back_c = 3, max(10, font // 7), 0, "&H55000000&", "&H55000000&"
    elif style.outline == "shadow":
        # a soft dark halo as well as the drop shadow, so white lines read on light pictures too
        border, outline, shadow, out_c, back_c = 1, max(2, font // 28), max(3, font // 22), "&H70000000&", "&H70000000&"
        blur = r"\blur3"
    elif style.outline == "glow":
        border, outline, shadow, out_c, back_c = 1, max(4, font // 18), 2, ass_color(style.highlight, 0x40), "&H70000000&"
        blur = r"\blur10"
    else:
        border, outline, shadow, out_c, back_c = 1, max(4, font // 14), 3, "&H00000000&", "&H80000000&"
    # fill sweeps from SecondaryColour (not sung yet) to PrimaryColour (sung)
    primary, secondary = (high, base) if style.effect == "fill" else (base, base)
    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Lyric,{style.font},{font},{primary},{secondary},{out_c},{back_c},-1,0,0,0,100,100,0,0,{border},{outline},{shadow},5,80,80,0,1
Style: LyricNext,{style.font},{small},&H60FFFFFF&,&H60FFFFFF&,&H60000000&,&HA0000000&,-1,0,0,0,100,100,0,0,1,{max(2, outline - 2)},2,5,80,80,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    events: list[str] = []
    ys = {"low": 0.80, "middle": 0.5, "high": 0.2} if landscape else {"low": 0.64, "middle": 0.5, "high": 0.24}
    y = round(H * ys[style.position])
    pos = f"{{\\pos({W // 2},{y}){blur}}}"
    next_pos = f"{{\\pos({W // 2},{y + round(font * 1.35)})}}"
    prev_end = 0.0
    for li, line in enumerate(lines):
        words = [w for w in line.words if _esc(w.text)]
        if not words:
            continue
        texts = [_esc(_case(w.text, style.case, profile.code)) for w in words]
        next_start = lines[li + 1].start if li + 1 < len(lines) else float("inf")
        line_end = min(next_start, words[-1].end + hold)
        show = max(prev_end, words[0].start - lead_in)

        def dialogue(start: float, end: float, text: str, name: str = "Lyric") -> None:
            if end > start:
                events.append(f"Dialogue: 0,{_ts(start)},{_ts(end)},{name},,0,0,0,,{text}")

        if style.effect == "fill":
            # one event per line: \kf sweeps each word over its sung time (centiseconds from when the line shows;
            # counted from there rather than word by word so rounding never drifts)
            mark = [round((w.start - show) * 100) for w in words] + [round((words[-1].end - show) * 100)]
            body = f"{{\\k{max(0, mark[0])}}}" + " ".join(
                f"{{\\kf{max(1, mark[i + 1] - mark[i])}}}{t}" for i, t in enumerate(texts))
            dialogue(show, line_end, pos + r"{\fad(120,200)}" + body)
        elif style.effect == "fade":
            dialogue(show, line_end, pos + r"{\fad(250,300)}" + " ".join(texts))
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
                return pos + " ".join(f"{{\\c{high if j < sung else base}}}{t}" for j, t in enumerate(texts))

            dialogue(show, words[0].start, r"{\fscx90\fscy90\t(0,120,\fscx100\fscy100)}" + text(0))
            for wi, w in enumerate(words):
                dialogue(w.start, words[wi + 1].start if wi + 1 < len(words) else line_end, text(wi + 1))
        if (landscape and style.effect in ("karaoke", "fill") and li + 1 < len(lines)
                and next_start - line_end < 2.5 and _esc(lines[li + 1].text)):
            dialogue(show, line_end, next_pos + _esc(_case(lines[li + 1].text, style.case, profile.code)), "LyricNext")
        prev_end = line_end
    if title and _esc(title[0]):
        events += _neon_title(_esc(_case(title[0], "upper", profile.code)), title[1], title[2], style, font, W,
                              round(H * (0.72 if style.position == "high" else 0.3)))
    return header + "\n".join(events) + "\n"


def _neon_title(text: str, start: float, end: float, style: "LyricStyle", font: int, W: int, y: int) -> list[str]:
    """A title that flickers on like a neon tube: a wide blurred glow in the neon colour under a pale, sharp core."""
    from .styles import ass_color

    neon = ass_color(style.highlight)
    px = round(font * 1.9)
    # on, off, on, dim, on: the first second of a neon sign being switched on; fades out at the end
    flicker = (r"\alpha&HFF&\t(0,40,\alpha&H00&)\t(90,110,\alpha&HC0&)\t(170,190,\alpha&H00&)"
               r"\t(330,350,\alpha&H70&)\t(420,440,\alpha&H00&)\fad(0,250)")
    common = f"\\pos({W // 2},{y})\\an5\\fn{style.font}\\fs{px}\\b1\\fsp{round(px * 0.08)}"
    glow = f"{{{common}\\1c{neon}\\3c{neon}\\bord{max(6, px // 9)}\\shad0\\blur{max(12, px // 5)}{flicker}}}{text}"
    core = f"{{{common}\\1c&H00F4F0FF&\\3c{neon}\\bord{max(2, px // 40)}\\shad0\\blur2{flicker}}}{text}"
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
