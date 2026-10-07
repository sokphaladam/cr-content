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


def build_thumbnail_ass(text: str, profile: LangProfile) -> str:
    """Cover headline: huge outlined text, the second half of the words in the highlight colour."""
    words = _esc(text).split()
    if profile.code != "km":
        words = [w.upper() for w in words]
    split = max(1, (len(words) + 1) // 2) if len(words) > 1 else len(words)
    body = " ".join(words[:split])
    if words[split:]:
        body += f" {{\c{HIGHLIGHT}}}" + " ".join(words[split:])
    size = round(profile.font_size * 1.6)
    return f"""[Script Info]
ScriptType: v4.00+
PlayResX: {WIDTH}
PlayResY: {HEIGHT}
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Thumb,{profile.font_name},{size},{WHITE},{WHITE},&H00000000&,&H99000000&,-1,0,0,0,100,100,0,0,1,12,8,5,70,70,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:00:00.00,9:00:00.00,Thumb,,0,0,0,,{{\pos({WIDTH // 2},{round(HEIGHT * 0.4)})}}{body}
"""
