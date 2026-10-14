"""Looks for music videos: how the lyrics are drawn (font, colours, effect) and how the footage is graded."""
from pathlib import Path

from pydantic import BaseModel

from .config import ASSETS_DIR, LANGS, SYSTEM_FONT_DIRS

# family name libass looks up -> font file (assets/fonts, or the system's / the user's installed fonts)
FONTS: dict[str, dict[str, str]] = {
    "en": {
        "Arial": "arialbd.ttf",
        "Impact": "impact.ttf",
        "Segoe UI Black": "seguibl.ttf",
        "Bahnschrift": "bahnschrift.ttf",
        "Georgia": "georgiab.ttf",
        "Trebuchet MS": "trebucbd.ttf",
        "Verdana": "verdanab.ttf",
        "Comic Sans MS": "comicbd.ttf",
        "Gabriola": "Gabriola.ttf",
        # retro display faces that come with Microsoft Office (listed only when installed)
        "Cooper Black": "COOPBL.TTF",
        "Broadway": "BROADW.TTF",
        "Bauhaus 93": "BAUHS93.TTF",
        "Rockwell Extra Bold": "ROCKEB.TTF",
        "Showcard Gothic": "SHOWG.TTF",
    },
    "km": {
        "Khmer OS Battambang": "KhmerOSbattambang.ttf",
        "Khmer OS Siemreap": "KhmerOSsiemreap.ttf",
        "Khmer OS Content": "KhmerOScontent.ttf",
        "Khmer OS Muol Light": "KhmerOSmuollight.ttf",
        "Khmer OS Bokor": "KhmerOSbokor.ttf",
        "Khmer OS Fasthand": "KhmerOSfasthand.ttf",
        "Khmer OS Freehand": "KhmerOSfreehand.ttf",
        "Khmer UI": "KhmerUIb.ttf",
        "Leelawadee UI": "LeelaUIb.ttf",
        # the Khmer fonts that come with macOS
        "Khmer Sangam MN": "Khmer Sangam MN.ttf",
        "Khmer MN": "Khmer MN.ttc",
    },
}

# the same families under the file names macOS gives them
MAC_FILES: dict[str, str] = {
    "arialbd.ttf": "Arial Bold.ttf",
    "impact.ttf": "Impact.ttf",
    "georgiab.ttf": "Georgia Bold.ttf",
    "trebucbd.ttf": "Trebuchet MS Bold.ttf",
    "verdanab.ttf": "Verdana Bold.ttf",
    "comicbd.ttf": "Comic Sans MS Bold.ttf",
}


def font_dirs() -> list[Path]:
    return [d for d in (ASSETS_DIR / "fonts", *SYSTEM_FONT_DIRS) if d.is_dir()]


def font_path(file: str) -> Path | None:
    names = [file, MAC_FILES[file]] if file in MAC_FILES else [file]
    for folder in font_dirs():
        for name in names:
            if (folder / name).exists():
                return folder / name
    return None


def available_fonts(lang: str) -> list[str]:
    """Font families for `lang` that are installed on this computer."""
    return [name for name, file in FONTS.get(lang, FONTS["en"]).items() if font_path(file)]


EFFECTS = ("karaoke", "fill", "pop", "fade")  # word by word / smooth sweep / words appear / whole line fades
OUTLINES = ("outline", "shadow", "box", "glow")
POSITIONS = ("low", "middle", "high")
SIZES = ("s", "m", "l")
CASES = ("as_is", "upper", "lower")


class LyricStyle(BaseModel):
    preset: str = "classic"
    font: str = ""  # "" = the preset's font for the song's language
    size: str = "m"
    position: str = "low"
    color: str = "#FFFFFF"  # words not sung yet
    highlight: str = "#FFE500"  # sung words
    effect: str = "karaoke"
    outline: str = "outline"
    case: str = "as_is"

    def clean(self, lang: str) -> "LyricStyle":
        """Unknown values back to the defaults, and a font that exists for this language."""
        s = self.model_copy()
        s.size = s.size if s.size in SIZES else "m"
        s.position = s.position if s.position in POSITIONS else "low"
        s.effect = s.effect if s.effect in EFFECTS else "karaoke"
        s.outline = s.outline if s.outline in OUTLINES else "outline"
        s.case = s.case if s.case in CASES else "as_is"
        s.color, s.highlight = _hex(s.color, "#FFFFFF"), _hex(s.highlight, "#FFE500")
        fonts = available_fonts(lang)
        preset = PRESETS.get(s.preset, PRESETS["classic"])
        wanted = s.font or (preset["font_km"] if lang == "km" else preset["font"])
        s.font = wanted if wanted in fonts else (fonts[0] if fonts else LANGS["km" if lang == "km" else "en"].font_name)
        return s


def _hex(value: str, default: str) -> str:
    v = (value or "").strip().lstrip("#")
    return f"#{v.upper()}" if len(v) == 6 and all(c in "0123456789abcdefABCDEF" for c in v) else default


def ass_color(hex_color: str, alpha: int = 0) -> str:
    """'#RRGGBB' -> ASS '&HAABBGGRR&' (alpha 0 = opaque, 255 = invisible)."""
    v = _hex(hex_color, "#FFFFFF").lstrip("#")
    return f"&H{alpha:02X}{v[4:6]}{v[2:4]}{v[0:2]}&"


# label shown in the UI, plus the style; font_km is used for Khmer songs
PRESETS: dict[str, dict] = {
    "classic": {"label": "Classic", "font": "Arial", "font_km": "Khmer OS Battambang", "size": "m", "position": "low",
                "color": "#FFFFFF", "highlight": "#FFE500", "effect": "karaoke", "outline": "outline", "case": "as_is"},
    "neon": {"label": "Neon", "font": "Bahnschrift", "font_km": "Khmer OS Siemreap", "size": "m", "position": "middle",
             "color": "#FFFFFF", "highlight": "#3DF5FF", "effect": "fill", "outline": "glow", "case": "upper"},
    "bold_pop": {"label": "Bold pop", "font": "Impact", "font_km": "Khmer OS Muol Light", "size": "l", "position": "middle",
                 "color": "#FFFFFF", "highlight": "#FFE500", "effect": "pop", "outline": "outline", "case": "upper"},
    "cinematic": {"label": "Cinematic", "font": "Georgia", "font_km": "Khmer OS Content", "size": "m", "position": "low",
                  "color": "#F4EDE1", "highlight": "#F4EDE1", "effect": "fade", "outline": "shadow", "case": "as_is"},
    "minimal": {"label": "Minimal", "font": "Bahnschrift", "font_km": "Khmer UI", "size": "s", "position": "low",
                "color": "#9AA4B5", "highlight": "#FFFFFF", "effect": "fill", "outline": "shadow", "case": "lower"},
    "retro": {"label": "Retro 70s", "font": "Cooper Black", "font_km": "Khmer OS Muol Light", "size": "l",
              "position": "middle", "color": "#FFE9C7", "highlight": "#FF8A3D", "effect": "fill", "outline": "shadow",
              "case": "as_is"},
    "boxed": {"label": "Boxed", "font": "Arial", "font_km": "Khmer OS Battambang", "size": "m", "position": "low",
              "color": "#FFFFFF", "highlight": "#FFE500", "effect": "karaoke", "outline": "box", "case": "as_is"},
}


def preset_style(name: str) -> LyricStyle:
    p = PRESETS.get(name, PRESETS["classic"])
    return LyricStyle(preset=name if name in PRESETS else "classic",
                      **{k: v for k, v in p.items() if k not in ("label", "font", "font_km")})


# Colour grades for the footage: applied to every shot so clips from different sources look like one film.
LOOKS: dict[str, dict[str, str]] = {
    "natural": {"label": "Natural", "vf": "eq=brightness=-0.04:saturation=1.08"},
    "cinematic": {"label": "Cinematic", "vf": (
        "colorbalance=rs=-0.06:gs=-0.01:bs=0.08:rh=0.07:gh=0.02:bh=-0.07,"
        "eq=contrast=1.1:saturation=1.05:brightness=-0.05,vignette=angle=PI/5")},
    "film": {"label": "Warm film", "vf": (
        "colorbalance=rs=0.04:bs=-0.04:rm=0.05:bm=-0.03,eq=contrast=1.05:saturation=0.88:brightness=-0.03,"
        "noise=alls=7:allf=t,vignette=angle=PI/5")},
    "moody": {"label": "Moody", "vf": (
        "eq=contrast=1.12:saturation=0.72:brightness=-0.09:gamma=0.95,colorbalance=bs=0.05:bm=0.03,"
        "vignette=angle=PI/4")},
    "vibrant": {"label": "Vibrant", "vf": "eq=contrast=1.06:saturation=1.35:brightness=-0.03,unsharp=5:5:0.4"},
    "dusk": {"label": "Neon dusk", "vf": (  # pink shadows, orange highlights: synthwave sunsets and city nights
        "colorbalance=rs=0.09:gs=-0.07:bs=0.07:rm=0.05:gm=-0.04:bm=0.02:rh=0.10:gh=0.03:bh=-0.09,"
        "eq=contrast=1.08:saturation=1.25:brightness=-0.04,vignette=angle=PI/5")},
    "mono": {"label": "Black & white", "vf": "hue=s=0,eq=contrast=1.15:brightness=-0.04,noise=alls=5:allf=t,vignette=angle=PI/5"},
}


def look_filter(name: str) -> str:
    return LOOKS.get(name, LOOKS["natural"])["vf"]


def catalog() -> dict:
    """What the UI offers: presets, looks and fonts per language."""
    return {
        "presets": {k: {**preset_style(k).model_dump(), "label": v["label"], "font": v["font"], "font_km": v["font_km"]}
                    for k, v in PRESETS.items()},
        "looks": {k: v["label"] for k, v in LOOKS.items()},
        "fonts": {lang: available_fonts(lang) for lang in FONTS},
    }


# ---------- Captions of narrated videos (word by word, spoken word highlighted) ----------

class CaptionStyle(BaseModel):
    """How a narrated video's captions and scene headlines look. Positions are fractions of the frame height, set by
    dragging them on the live preview."""
    preset: str = "classic"
    font: str = ""  # "" = the language's caption font
    size: str = "m"
    y: float = 0.62  # middle of the caption
    headline_y: float = 0.12  # top of the scene headline
    color: str = "#FFFFFF"  # words not being spoken
    highlight: str = "#FFE500"  # the word being spoken
    keyword: str = "#4ADE80"  # words marked as keywords in the transcript
    outline: str = "outline"
    case: str = "as_is"
    words: int = 0  # words shown together; 0 = the language's default

    def clean(self, lang: str) -> "CaptionStyle":
        """Unknown values back to the defaults, positions inside the frame, a font installed for this language."""
        s = self.model_copy()
        s.size = s.size if s.size in SIZES else "m"
        s.outline = s.outline if s.outline in OUTLINES else "outline"
        s.case = s.case if s.case in CASES else "as_is"
        s.y = min(max(float(s.y), 0.08), 0.92)
        s.headline_y = min(max(float(s.headline_y), 0.03), 0.85)
        s.words = min(max(int(s.words), 0), 6)
        s.color, s.highlight = _hex(s.color, "#FFFFFF"), _hex(s.highlight, "#FFE500")
        s.keyword = _hex(s.keyword, "#4ADE80")
        fonts = available_fonts(lang)
        s.font = s.font if s.font in fonts else ""
        return s

    def font_file(self, lang: str) -> str:
        return FONTS.get(lang, FONTS["en"]).get(self.font, "")


CAPTION_PRESETS: dict[str, dict] = {
    "classic": {"label": "Classic", "font": "", "size": "m", "color": "#FFFFFF", "highlight": "#FFE500",
                "keyword": "#4ADE80", "outline": "outline", "case": "as_is"},
    "bold": {"label": "Bold", "font": "Impact", "size": "l", "color": "#FFFFFF", "highlight": "#FFE500",
             "keyword": "#FF5A5A", "outline": "outline", "case": "upper"},
    "boxed": {"label": "Boxed", "font": "", "size": "m", "color": "#FFFFFF", "highlight": "#FFE500",
              "keyword": "#4ADE80", "outline": "box", "case": "as_is"},
    "neon": {"label": "Neon", "font": "Bahnschrift", "size": "m", "color": "#FFFFFF", "highlight": "#3DF5FF",
             "keyword": "#FF5AF0", "outline": "glow", "case": "upper"},
    "minimal": {"label": "Minimal", "font": "Bahnschrift", "size": "s", "color": "#FFFFFF", "highlight": "#FFE500",
                "keyword": "#FFE500", "outline": "shadow", "case": "lower"},
}


def caption_catalog() -> dict:
    return {"presets": CAPTION_PRESETS, "outlines": list(OUTLINES), "sizes": list(SIZES), "cases": list(CASES)}
