"""Graphic scenes drawn by the app instead of searched for: no stock library has "parrot brain vs monkey brain", a
logo sting or an end screen, and a loose search for them finds glowing hearts and paint in water.

Four layouts, all in the video's own look (dark backdrop, the accent colour of the title cards, the same fonts):
- headline: one line, big, with an optional small line under it (a logo sting, a key number, a chapter break)
- versus: two panels side by side, each a picture (when one is found) with its label, "VS" between them
- list: up to six numbered items (a recap, "colours, shapes, numbers")
- end: the video's title on the left, two empty 16:9 slots on the right where YouTube's end-screen videos go

Cards are stills; the render gives them the same slow push-in as photos.
"""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

from ..styles import font_path

ACCENT = (245, 159, 0)    # #F59F00, as the title cards (video.ACCENT)
INK = (240, 240, 244)
SOFT = (160, 164, 176)
STYLES = ("headline", "versus", "list", "end")


def _font(lang: str, px: int, heavy: bool) -> ImageFont.FreeTypeFont:
    from .video import _fonts

    (_, body), (_, title) = _fonts(lang)
    path = font_path(title if heavy else body)
    return ImageFont.truetype(str(path), px) if path else ImageFont.load_default(px)


def _backdrop(size: tuple[int, int], under: Path | None) -> Image.Image:
    """A dark backdrop: the scene's neighbouring footage blurred far out of focus when there is one (so the card sits
    in the video's colours), else a deep blue-grey gradient; vignetted either way."""
    W, H = size
    if under and under.exists():
        img = ImageOps.fit(Image.open(under).convert("RGB"), (W // 8, H // 8)).filter(ImageFilter.GaussianBlur(6))
        img = Image.blend(img.resize(size, Image.BICUBIC), Image.new("RGB", size, (12, 14, 20)), 0.72)
    else:
        top, bottom = (28, 32, 44), (10, 11, 16)
        grad = Image.linear_gradient("L").resize(size)
        img = Image.composite(Image.new("RGB", size, bottom), Image.new("RGB", size, top), grad)
    shade = Image.radial_gradient("L").resize(size).point(lambda v: int(v * 0.55))
    return Image.composite(Image.new("RGB", size, (0, 0, 0)), img, shade)


def _fit(draw: ImageDraw.ImageDraw, text: str, lang: str, px: int, heavy: bool, width: float) -> ImageFont.FreeTypeFont:
    font = _font(lang, px, heavy)
    while draw.textlength(text, font=font) > width and px > 24:
        px -= 4
        font = _font(lang, px, heavy)
    return font


def _wrap(draw: ImageDraw.ImageDraw, text: str, font, width: float, lines: int = 2) -> list[str]:
    words, out, line = text.split(), [], ""
    for w in words:
        trial = f"{line} {w}".strip()
        if line and draw.textlength(trial, font=font) > width:
            out.append(line)
            line = w
        else:
            line = trial
    out.append(line)
    return out[:lines]


def _centred(draw, y: float, text: str, font, fill, W: int) -> None:
    draw.text(((W - draw.textlength(text, font=font)) / 2, y), text, font=font, fill=fill)


def _picture(path: Path | None, box: tuple[int, int]) -> Image.Image | None:
    if not path or not path.exists():
        return None
    from ..render import run

    if path.suffix.lower() not in (".jpg", ".jpeg", ".png", ".webp"):  # a video: its frame from 40% in
        still = path.with_suffix(".card.jpg")
        if not still.exists():
            from ..render import duration
            run(["ffmpeg", "-y", "-v", "error", "-ss", f"{duration(path) * 0.4:.2f}", "-i", str(path),
                 "-frames:v", "1", str(still)])
        path = still
    return ImageOps.fit(Image.open(path).convert("RGB"), box, Image.LANCZOS)


def _rounded(img: Image.Image, radius: int) -> Image.Image:
    mask = Image.new("L", img.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, *img.size), radius, fill=255)
    out = Image.new("RGBA", img.size)
    out.paste(img, (0, 0), mask)
    return out


def draw(card: dict, out: Path, size: tuple[int, int], lang: str = "en", under: Path | None = None,
         pictures: list[Path | None] = ()) -> Path:
    """The card {style, title, items} as a png at `size`. `under`: footage to blur into the backdrop; `pictures`: one
    per versus item."""
    W, H = size
    k = H / 1080
    style = card.get("style") if card.get("style") in STYLES else "headline"
    title = " ".join(str(card.get("title") or "").split())
    items = [" ".join(str(i).split()) for i in card.get("items") or [] if str(i).strip()]
    items = [i[:1].upper() + i[1:] for i in items]  # "parrot brain" -> "Parrot brain"
    img = _backdrop(size, under)
    d = ImageDraw.Draw(img)

    if style == "versus" and len(items) >= 2:
        left, right = items[0], items[1]
        pw, ph = round(W * 0.36), round(H * 0.5)
        top = round(H * (0.30 if title else 0.22))
        for i, (label, x) in enumerate(((left, W * 0.25), (right, W * 0.75))):
            x0 = round(x - pw / 2)
            pic = _picture(pictures[i] if i < len(pictures) else None, (pw, ph))
            if pic:
                img.paste(_rounded(pic, round(18 * k)), (x0, top), _rounded(pic, round(18 * k)))
            else:  # no picture: the name itself fills the panel
                d.rounded_rectangle((x0, top, x0 + pw, top + ph), round(18 * k), fill=(30, 33, 42), outline=(60, 64, 76),
                                    width=max(round(2 * k), 1))
                big = _font(lang, round(76 * k), True)
                lines = _wrap(d, label, big, pw * 0.84, 3)
                y = top + ph / 2 - big.size * 1.15 * len(lines) / 2
                for ln in lines:
                    d.text((x - d.textlength(ln, font=big) / 2, y), ln, font=big, fill=INK)
                    y += big.size * 1.15
                continue
            font = _fit(d, label, lang, round(54 * k), True, pw)
            d.text((x - d.textlength(label, font=font) / 2, top + ph + round(26 * k)), label, font=font, fill=INK)
        vs = _font(lang, round(84 * k), True)
        cy = top + ph / 2
        d.ellipse((W / 2 - 70 * k, cy - 70 * k, W / 2 + 70 * k, cy + 70 * k), fill=ACCENT)
        d.text((W / 2, cy), "VS", font=vs, fill=(20, 20, 24), anchor="mm")
        if title:
            font = _fit(d, title, lang, round(64 * k), True, W * 0.8)
            _centred(d, H * 0.11, title, font, INK, W)

    elif style == "list" and items:
        items = items[:6]
        font_t = _fit(d, title, lang, round(76 * k), True, W * 0.8) if title else None
        y = H * 0.16
        if font_t:
            _centred(d, y, title, font_t, INK, W)
            y += font_t.size * 1.6
        cols = 3 if len(items) > 4 else 2 if len(items) > 1 else 1
        rows = -(-len(items) // cols)
        cw, ch, gap = W * 0.8 / cols, min(H * 0.17, (H * 0.84 - y) / rows - 24 * k), 24 * k
        x_start = (W - (cw * cols - gap * 0)) / 2
        for n, label in enumerate(items):
            r, c = divmod(n, cols)
            x0, y0 = x_start + c * cw + gap / 2, y + r * (ch + gap)
            d.rounded_rectangle((x0, y0, x0 + cw - gap, y0 + ch), round(16 * k), fill=(24, 27, 36),
                                outline=(54, 58, 70), width=max(round(2 * k), 1))
            num = _font(lang, round(ch * 0.46), True)
            d.text((x0 + 26 * k, y0 + ch / 2), str(n + 1), font=num, fill=ACCENT, anchor="lm")
            font = _fit(d, label, lang, round(min(46 * k, ch * 0.32)), False, cw - gap - 130 * k)
            d.text((x0 + 110 * k, y0 + ch / 2), label, font=font, fill=INK, anchor="lm")

    elif style == "end":
        x0 = round(W * 0.07)
        d.rectangle((x0, H * 0.36, x0 + 10 * k, H * 0.62), fill=ACCENT)
        font = _font(lang, round(70 * k), True)
        lines = _wrap(d, title or "Thanks for watching", font, W * 0.36, 3)
        y = H * 0.36
        for ln in lines:
            d.text((x0 + 40 * k, y), ln, font=font, fill=INK)
            y += font.size * 1.15
        if items:
            d.text((x0 + 40 * k, y + 16 * k), items[0], font=_font(lang, round(38 * k), False), fill=SOFT)
        # YouTube's end-screen elements: two videos stacked on the right, kept clear
        sw, sh = round(W * 0.36), round(W * 0.36 * 9 / 16)
        sx = round(W * 0.57)
        for sy in (round(H * 0.12), round(H * 0.88 - sh)):
            d.rounded_rectangle((sx, sy, sx + sw, sy + sh), round(14 * k), outline=(70, 74, 88),
                                width=max(round(3 * k), 1))

    else:  # headline
        text = title or (items[0] if items else "")
        font = _font(lang, round(108 * k), True)
        lines = _wrap(d, text, font, W * 0.78, 2)
        if len(lines) == 1:
            font = _fit(d, text, lang, round(120 * k), True, W * 0.8)
        step = font.size * 1.12
        sub = items[0] if title and items else ""
        y = H / 2 - step * len(lines) / 2 - (30 * k if sub else 0)
        bar = 140 * k
        if text:
            d.rectangle((W / 2 - bar / 2, y - 46 * k, W / 2 + bar / 2, y - 36 * k), fill=ACCENT)
        for ln in lines:
            _centred(d, y, ln, font, INK, W)
            y += step
        if sub:
            sf = _fit(d, sub, lang, round(44 * k), False, W * 0.7)
            _centred(d, y + 40 * k, sub, sf, SOFT, W)

    img.save(out)
    return out
