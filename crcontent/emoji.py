"""Colour emoji in the burned-in text (captions, headlines, text boxes, covers).

libass draws one colour per glyph, so it can't draw colour emoji itself. Each emoji is taken apart into the flat colour
layers of Twemoji (Mozilla's COLRv0 font: downloaded once, ~1.5 MB, CC-BY 4.0 graphics by Twitter), and every layer
becomes a glyph in its own small font, made per render. A subtitle line with emoji is then drawn once more per layer
with its text invisible and only that layer's emoji shown in the layer's colour. libass lays out every copy the same
way (same text, same advances), so the layers land exactly on top of each other, and pops, fades and karaoke
colours still apply. Without the font (offline) emoji are left out, as before.
"""
import re
import threading
from pathlib import Path

from .config import CACHE_DIR

FONT_URL = "https://github.com/mozilla/twemoji-colr/releases/download/v0.7.0/Twemoji.Mozilla.ttf"
FONT_FILE = CACHE_DIR / "fonts" / "Twemoji.Mozilla.ttf"
FAMILY = "CREmoji"  # layer k is the font family f"{FAMILY}{k}"
PUA = 0xE000  # the n-th distinct emoji of a subtitle file is drawn as this code point + n

_PICTO = "☀-➿⬅-⭕⌚⌛⏩-⏺‼⁉〰〽㊗㊙\U0001F000-\U0001FAFF"
_MOD = "(?:️|[\U0001F3FB-\U0001F3FF])?"
# one emoji as people see it: a flag, a keycap, or a pictograph with its skin tone and ZWJ parts (family, professions)
EMOJI = re.compile(
    "[\U0001F1E6-\U0001F1FF]{2}"
    "|[#*0-9]️?⃣"
    f"|[{_PICTO}]{_MOD}(?:[\U000E0020-\U000E007F]+)?(?:‍[{_PICTO}]{_MOD})*"
)


def strip(text: str) -> str:
    """`text` without emoji (what the voice reads)."""
    return re.sub(r"[ \t]{2,}", " ", EMOJI.sub("", text)).strip()


_lock = threading.Lock()
_font: dict | None = None


def _download() -> Path | None:
    if FONT_FILE.exists() and FONT_FILE.stat().st_size:
        return FONT_FILE
    import requests

    try:
        r = requests.get(FONT_URL, timeout=30)
        r.raise_for_status()
    except requests.RequestException as e:
        print(f"  ! couldn't download the emoji font ({type(e).__name__}); emoji are left out")
        return None
    FONT_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = FONT_FILE.with_suffix(".part")
    tmp.write_bytes(r.content)
    tmp.replace(FONT_FILE)
    return FONT_FILE


def _load() -> dict | None:
    """The emoji font's parts: glyph lookup, colour layers and palette (None when there is no font)."""
    global _font
    with _lock:
        if _font is not None:
            return _font or None
        path = _download()
        try:
            from fontTools.ttLib import TTFont
        except ImportError:
            print("  ! fonttools isn't installed; emoji are left out")
            path = None
        if not path:
            _font = {}
            return None
        font = TTFont(path)
        ligatures: dict[tuple[str, ...], str] = {}
        for lookup in font["GSUB"].table.LookupList.Lookup:
            for sub in lookup.SubTable:
                sub = getattr(sub, "ExtSubTable", sub)
                for first, ligs in (getattr(sub, "ligatures", None) or {}).items():
                    for lig in ligs:
                        ligatures[(first, *lig.Component)] = lig.LigGlyph
        _font = {"font": font, "cmap": font.getBestCmap(), "ligatures": ligatures, "glyphs": font.getGlyphSet(),
                 "layers": font["COLR"].ColorLayers, "palette": font["CPAL"].palettes[0],
                 "upem": font["head"].unitsPerEm, "hmtx": font["hmtx"]}
        return _font


def _glyph(f: dict, cluster: str) -> str | None:
    """The font's glyph for one emoji (ligatures for flags, keycaps, skin tones and ZWJ sequences)."""
    for seq in (cluster, cluster.replace("️", "")):
        names = tuple(f["cmap"][ord(c)] for c in seq if ord(c) in f["cmap"])
        if not names:
            continue
        if len(names) == 1:
            return names[0]
        if names in f["ligatures"]:
            return f["ligatures"][names]
    first = f["cmap"].get(ord(cluster[0]))
    return first


def _layers(f: dict, glyph: str) -> list[tuple[str, str, str]]:
    """(glyph, ASS colour, ASS alpha) per colour layer, bottom first."""
    out = []
    for layer in f["layers"].get(glyph) or []:
        if layer.colorID == 0xFFFF:  # "the text colour": Twemoji has none in practice
            out.append((layer.name, "&HFFFFFF&", "&H00&"))
            continue
        c = f["palette"][layer.colorID]
        out.append((layer.name, f"&H{c.blue:02X}{c.green:02X}{c.red:02X}&", f"&H{255 - c.alpha:02X}&"))
    return out or [(glyph, "&HFFFFFF&", "&H00&")]


def _build_fonts(f: dict, glyphs: list[str], fonts_dir: Path) -> None:
    """One font per colour layer: glyph n (at PUA + n) is layer k of emoji n, or empty."""
    from fontTools.fontBuilder import FontBuilder
    from fontTools.pens.recordingPen import DecomposingRecordingPen
    from fontTools.pens.ttGlyphPen import TTGlyphPen

    layers = [_layers(f, g) for g in glyphs]
    count = max(len(ls) for ls in layers)
    upem = f["upem"]
    # the caption fonts' (Arial's) line height, so a box drawn behind an emoji is as tall as the one behind the text
    ascent, descent = round(upem * 0.905), round(upem * 0.212)
    fonts_dir.mkdir(parents=True, exist_ok=True)
    for k in range(count):
        names = [".notdef"] + [f"e{n}" for n in range(len(glyphs))]
        outlines = {".notdef": TTGlyphPen(None).glyph()}
        for n, ls in enumerate(layers):
            pen = TTGlyphPen(None)
            if k < len(ls):
                rec = DecomposingRecordingPen(f["glyphs"])
                f["glyphs"][ls[k][0]].draw(rec)
                rec.replay(pen)
            outlines[f"e{n}"] = pen.glyph()
        fb = FontBuilder(upem, isTTF=True)
        fb.setupGlyphOrder(names)
        fb.setupCharacterMap({PUA + n: f"e{n}" for n in range(len(glyphs))})
        fb.setupGlyf(outlines)
        glyf = fb.font["glyf"]
        fb.setupHorizontalMetrics({".notdef": (0, 0), **{
            f"e{n}": (f["hmtx"][g][0], getattr(glyf[f"e{n}"], "xMin", 0)) for n, g in enumerate(glyphs)}})
        fb.setupHorizontalHeader(ascent=ascent, descent=-descent)
        family = f"{FAMILY}{k}"
        fb.setupNameTable({"familyName": family, "styleName": "Regular", "psName": family, "fullName": family})
        fb.setupOS2(sTypoAscender=ascent, sTypoDescender=-descent, usWinAscent=ascent, usWinDescent=descent)
        fb.setupPost()
        fb.save(str(fonts_dir / f"{family}.ttf"))


_BLOCK = re.compile(r"(\{[^}]*\})")
_COLOUR = re.compile(r"\\1?c(?![a-z])(&H[0-9A-Fa-f]+&)?")
_ALPHA = re.compile(r"\\(?:alpha|1a)(&H[0-9A-Fa-f]+&)?")
_ALPHA_ANY = re.compile(r"\\(?:alpha|[1-4]a)(&H[0-9A-Fa-f]+&)?")


def _rewrite(text: str, index: dict[str, int], layers: list[list[tuple]], k: int) -> str:
    """The Dialogue text drawn as colour layer k: layer 0 is the line itself with the emoji's first layer; every other
    layer hides the text and shows just that layer of each emoji."""
    out = [r"{\alpha&HFF&}"] if k else []
    colour, hidden = "", False  # the text colour and whether the text is invisible (karaoke "pop") at this point
    for part in _BLOCK.split(text):
        if part.startswith("{"):
            for m in _COLOUR.finditer(part):
                colour = m.group(1) or ""
            for m in _ALPHA.finditer(part):
                hidden = (m.group(1) or "").upper() == "&HFF&"
            out.append(_ALPHA_ANY.sub("", part) if k else part)
            continue
        pos = 0
        for m in EMOJI.finditer(part):
            out.append(part[pos:m.start()])
            pos = m.end()
            n = index[m.group()]
            if k < len(layers[n]):
                _, c, a = layers[n][k]
            else:
                c, a = "&HFFFFFF&", "&HFF&"  # this emoji has fewer layers: an empty glyph holds its place
            a = "&HFF&" if hidden else a
            if k:
                out.append(rf"{{\fn{FAMILY}{k}\b0\i0\bord0\shad0\blur0\1c{c}\1a{a}}}{chr(PUA + n)}{{\fn\b\i\alpha&HFF&}}")
            else:
                alpha = rf"\1a{a}" if a != "&H00&" else ""
                after = r"\1a" if alpha else ""
                out.append(rf"{{\fn{FAMILY}0\b0\i0\1c{c}{alpha}}}{chr(PUA + n)}{{\fn\b\i\1c{colour}{after}}}")
        out.append(part[pos:])
    return "".join(out)


def emojify_ass(ass: str, fonts_dir: Path) -> str:
    """`ass` (a whole subtitle file) with its emoji drawn in colour: writes the layer fonts into `fonts_dir` (the
    folder libass reads fonts from). Emoji are left out when the emoji font can't be had."""
    lines = ass.split("\n")
    events = [i for i, line in enumerate(lines) if line.startswith("Dialogue:")]
    found = list(dict.fromkeys(m.group() for i in events for m in EMOJI.finditer(lines[i].split(",", 9)[-1])))
    if not found:
        return ass
    try:
        f = _load()
    except Exception as e:  # a broken download: same as none
        print(f"  ! couldn't read the emoji font ({type(e).__name__}); emoji are left out")
        f = None
    glyphs = [_glyph(f, e) for e in found] if f else []
    if not f or not all(glyphs):
        known = {e for e, g in zip(found, glyphs) if g} if f else set()
        for i in events:
            fields = lines[i].split(",", 9)
            fields[9] = EMOJI.sub(lambda m: m.group() if m.group() in known else "", fields[9])
            lines[i] = ",".join(fields)
        if not known:
            return "\n".join(lines)
        found = [e for e in found if e in known]
        glyphs = [_glyph(f, e) for e in found]
    index = {e: n for n, e in enumerate(found)}
    _build_fonts(f, glyphs, fonts_dir)
    layers = [_layers(f, g) for g in glyphs]
    out = []
    for i, line in enumerate(lines):
        if not line.startswith("Dialogue:"):
            out.append(line)
            continue
        fields = line[len("Dialogue:"):].split(",", 9)
        layer = int(fields[0].strip() or 0) * 100  # room above each line for its emoji layers
        used = [index[m.group()] for m in EMOJI.finditer(fields[9])]
        if not used:
            out.append(f"Dialogue: {layer}," + ",".join(fields[1:]))
            continue
        for k in range(max(len(layers[n]) for n in used)):
            out.append(f"Dialogue: {layer + k}," + ",".join(fields[1:9]) + "," + _rewrite(fields[9], index, layers, k))
    return "\n".join(out)
