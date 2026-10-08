"""Build an .ass subtitle file: big centered captions with the spoken word highlighted."""
import re

from .config import HEIGHT, WIDTH, LangProfile
from .tts import Word

HIGHLIGHT = "&H0000E5FF&"  # ASS colours are &HAABBGGRR -> yellow
WHITE = "&H00FFFFFF&"


def _ts(sec: float) -> str:
    sec = max(sec, 0)
    h, rem = divmod(sec, 3600)
    m, s = divmod(rem, 60)
    return f"{int(h)}:{int(m):02d}:{s:05.2f}"


# emoji can't be drawn by the caption fonts (they'd show as empty boxes)
_EMOJI = re.compile("[🀀-🫿☀-➿⬀-⯿🇦-🇿️‍⃣]+")


def _esc(text: str) -> str:
    text = _EMOJI.sub("", text).strip()
    return text.replace("\\", "/").replace("{", "(").replace("}", ")").replace("\n", " ")


def build_ass(scenes: list[tuple[float, float, list[Word], str]], profile: LangProfile) -> str:
    """scenes: (scene_start, scene_end, words with times relative to scene_start, on_screen_text)."""
    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {WIDTH}
PlayResY: {HEIGHT}
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Caption,{profile.font_name},{profile.font_size},{WHITE},{WHITE},&H00000000&,&H80000000&,-1,0,0,0,100,100,0,0,1,7,3,5,90,90,0,1
Style: Headline,{profile.font_name},{round(profile.font_size * 0.8)},{WHITE},{WHITE},&HFF000000&,&H1A000000&,-1,0,0,0,100,100,0,0,4,26,0,8,80,80,230,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    lines: list[str] = []
    cap_y = round(HEIGHT * 0.62)
    for scene_start, scene_end, words, headline in scenes:
        if headline:
            lines.append(f"Dialogue: 1,{_ts(scene_start)},{_ts(scene_end)},Headline,,0,0,0,,{_esc(headline.upper())}")

        n = profile.words_per_caption
        groups = [words[i:i + n] for i in range(0, len(words), n)]
        for gi, group in enumerate(groups):
            # each group stays on screen until the next group starts (no flicker between words)
            group_end = groups[gi + 1][0].start if gi + 1 < len(groups) else group[-1].end + 0.15
            for wi, word in enumerate(group):
                start = scene_start + word.start
                end = scene_start + (group[wi + 1].start if wi + 1 < len(group) else group_end)
                parts = []
                for wj, w in enumerate(group):
                    color = HIGHLIGHT if wj == wi else WHITE
                    parts.append(f"{{\\c{color}}}{_esc(w.text)}")
                pop = r"{\fscx85\fscy85\t(0,90,\fscx100\fscy100)}" if wi == 0 else ""
                text = f"{{\\pos({WIDTH // 2},{cap_y})}}{pop}" + " ".join(parts)
                lines.append(f"Dialogue: 0,{_ts(start)},{_ts(end)},Caption,,0,0,0,,{text}")
    return header + "\n".join(lines) + "\n"


def build_karaoke_ass(lines, profile: LangProfile, lead_in: float = 0.35, hold: float = 0.8) -> str:
    """Lyrics as karaoke: each sung line shown whole, words turning yellow as they're sung.

    lines: align.LyricLine items (absolute word times). A line appears `lead_in` s before its first word and
    stays until the next line starts or `hold` s after its last word.
    """
    size = round(profile.font_size * (0.85 if profile.code == "km" else 0.8))
    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {WIDTH}
PlayResY: {HEIGHT}
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Lyric,{profile.font_name},{size},{WHITE},{WHITE},&H00000000&,&H80000000&,-1,0,0,0,100,100,0,0,1,6,3,5,80,80,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    events: list[str] = []
    pos = f"{{\\pos({WIDTH // 2},{round(HEIGHT * 0.62)})}}"
    prev_end = 0.0
    for li, line in enumerate(lines):
        words = [w for w in line.words if _esc(w.text)]
        if not words:
            continue
        next_start = lines[li + 1].start if li + 1 < len(lines) else float("inf")
        line_end = min(next_start, words[-1].end + hold)
        show = max(prev_end, words[0].start - lead_in)

        def text(sung: int) -> str:
            return pos + " ".join(f"{{\\c{HIGHLIGHT if j < sung else WHITE}}}{_esc(w.text)}" for j, w in enumerate(words))

        if show < words[0].start:
            pop = r"{\fscx90\fscy90\t(0,120,\fscx100\fscy100)}"
            events.append(f"Dialogue: 0,{_ts(show)},{_ts(words[0].start)},Lyric,,0,0,0,,{pop}{text(0)}")
        for wi, w in enumerate(words):
            end = words[wi + 1].start if wi + 1 < len(words) else line_end
            if end > w.start:
                events.append(f"Dialogue: 0,{_ts(w.start)},{_ts(end)},Lyric,,0,0,0,,{text(wi + 1)}")
        prev_end = line_end
    return header + "\n".join(events) + "\n"


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


def build_thumbnail_ass(text: str, profile: LangProfile, style: str = "bold", emphasis: str = "") -> str:
    """Cover headline sized to fill the width, with the key word(s) in `emphasis` picked out.

    bold: white, heavy outline, key word yellow.  box: black on yellow boxes, key word red.
    stacked: a word or two per line, key word yellow and bigger.
    """
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
        size = round(max(110, min(profile.font_size * 2.6, WIDTH * 0.86 / max(longest * 0.34, 1))))
    else:
        lines = _wrap(words, 8 if style == "stacked" else 10)
        longest = max((len(" ".join(line)) for line in lines), default=1)
        # Arial Bold caps average ~0.64 em wide
        size = round(max(100, min(240, WIDTH * 0.88 / (longest * 0.64))))

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
    y = round(HEIGHT * (0.40 if style == "stacked" else 0.36))
    return f"""[Script Info]
ScriptType: v4.00+
PlayResX: {WIDTH}
PlayResY: {HEIGHT}
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: {thumb_style}

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:00:00.00,9:00:00.00,Thumb,,0,0,0,,{{\\pos({WIDTH // 2},{y})}}{body}
"""
