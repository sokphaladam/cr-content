"""Caption fonts the app can download for you (Settings → Caption fonts): the channel profiles' brand faces, from
Google's font repository (all SIL Open Font License). They go into assets/fonts, where the renderer and the live preview
look, so nothing is installed into the OS. Google ships some only as variable fonts; those are cut to a static face at
the weight the captions use (styles.FONT_WEIGHTS), named as the plain family, because the caption renderer (libass)
picks fonts by family name and weight."""
import io

import requests
from fontTools.ttLib import TTFont
from fontTools.varLib import instancer

from .config import ASSETS_DIR
from .profiles import PROFILES
from .styles import FONT_WEIGHTS, FONTS, font_path

REPO = "https://raw.githubusercontent.com/google/fonts/main/ofl/"
# family -> path in the repository (a variable font when its name has [axes])
SOURCES = {
    "Anton": "anton/Anton-Regular.ttf",
    "Bebas Neue": "bebasneue/BebasNeue-Regular.ttf",
    "Cinzel": "cinzel/Cinzel[wght].ttf",
    "Cormorant Garamond": "cormorantgaramond/CormorantGaramond[wght].ttf",
    "Inter": "inter/Inter[opsz,wght].ttf",
    "Montserrat": "montserrat/Montserrat[wght].ttf",
    "Oswald": "oswald/Oswald[wght].ttf",
}
MAX_BYTES = 20 << 20


class FontError(Exception):
    pass


def folder():
    return ASSETS_DIR / "fonts"


def catalog() -> list[dict]:
    """Each downloadable font: whether this PC has it (in the app's folder or the OS) and which channels use it."""
    out = []
    for family in SOURCES:
        used_by = []  # "Hidden History Files headline", "Wildlife Facts captions"
        for p in PROFILES.values():
            if p.headline_font_preferences[:1] == [family]:
                used_by.append(f"{p.display_name} headline")
            if p.caption_font_preferences[:1] == [family]:
                used_by.append(f"{p.display_name} captions")
            if p.emphasis_font_preferences[:1] == [family]:
                used_by.append(f"{p.display_name} emphasis")
        out.append({"family": family, "installed": font_path(FONTS["en"][family]) is not None, "used_by": used_by,
                    "weight": WEIGHT_NAMES.get(FONT_WEIGHTS.get(family, 700), "Bold")})
    return out


WEIGHT_NAMES = {400: "Regular", 500: "Medium", 600: "SemiBold", 700: "Bold", 800: "ExtraBold", 900: "Black"}


def _static(font: TTFont, family: str, weight: int) -> TTFont:
    """A variable font cut at `weight` (styles.FONT_WEIGHTS), named as the plain family with that weight."""
    axes = {a.axisTag: a for a in font["fvar"].axes}
    w = min(max(weight, axes["wght"].minValue), axes["wght"].maxValue)
    loc = {tag: (w if tag == "wght" else axis.defaultValue) for tag, axis in axes.items()}
    font = instancer.instantiateVariableFont(font, loc)
    sub = WEIGHT_NAMES.get(int(w), "Regular")
    bold = w >= 700
    name = font["name"]
    # nameID 2 may only be Regular/Bold; the real weight goes in 17 (typographic subfamily) and usWeightClass
    for rec, value in {1: family, 2: "Bold" if bold else "Regular", 4: f"{family} {sub}",
                       6: f"{family.replace(' ', '')}-{sub}", 16: family, 17: sub}.items():
        name.removeNames(nameID=rec)
        name.setName(value, rec, 3, 1, 0x409)
    font["OS/2"].usWeightClass = int(w)
    font["OS/2"].fsSelection = (font["OS/2"].fsSelection & ~0b1100001) | (0b100000 if bold else 0b1000000)
    font["head"].macStyle = (font["head"].macStyle | 1) if bold else (font["head"].macStyle & ~1)
    return font


def download(family: str) -> dict:
    """Fetch `family` into the fonts folder. Only the families in SOURCES (the name comes from the app's UI)."""
    if family not in SOURCES:
        raise FontError(f"{family} can't be downloaded here.")
    try:
        r = requests.get(REPO + SOURCES[family], timeout=60)
        r.raise_for_status()
    except requests.RequestException as e:
        raise FontError(f"Couldn't download {family}: {e}") from e
    if len(r.content) > MAX_BYTES:
        raise FontError(f"{family} is larger than expected; not saved.")
    try:
        font = TTFont(io.BytesIO(r.content))
        if "fvar" in font:
            font = _static(font, family, FONT_WEIGHTS.get(family, 700))
    except Exception as e:  # a broken or unexpected file never lands in the folder
        raise FontError(f"{family} downloaded, but the file couldn't be read: {e}") from e
    target = folder() / FONTS["en"][family]
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_suffix(".part")
    font.save(str(tmp))
    tmp.replace(target)  # no half-written font if the save fails
    return {"family": family, "installed": True}
