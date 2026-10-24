"""1280x720 thumbnail: the same neon-city-on-a-river look for every song, big mood phrase, title, channel badge.

Brand files are optional and shared by all songs:
  brand/fonts/*.ttf   first file whose name contains "bold" (else the first one) is used
  brand/logo.png      shown in the badge instead of the drawn "NEON MEKONG" text
Without them: Impact / Segoe UI Black from Windows, and the drawn badge.
"""
import random
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from . import config, songjson

W, H = 1280, 720
HORIZON = int(H * 0.56)
MARGIN = 70
DEFAULT_PALETTE = ["#ff2e93", "#00e5ff", "#1a0b3b", "#ffd166"]  # accent, accent 2, dark sky, warm light
WINDOWS_FONTS = ("impact.ttf", "seguibl.ttf", "arialbd.ttf")
MAX_BYTES = 2_000_000  # YouTube's thumbnail limit is 2 MB


def rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def palette_of(data: dict) -> list[tuple[int, int, int]]:
    p = data.get("palette") or []
    try:
        cols = [rgb(c) for c in p[:4]]
    except (ValueError, TypeError, IndexError):
        cols = []
    return cols if len(cols) == 4 else [rgb(c) for c in DEFAULT_PALETTE]


def font_path() -> str | None:
    fonts = sorted((config.BRAND_DIR / "fonts").glob("*.ttf")) if (config.BRAND_DIR / "fonts").is_dir() else []
    if fonts:
        return str(next((f for f in fonts if "bold" in f.name.lower()), fonts[0]))
    return next((str(Path("C:/Windows/Fonts") / n) for n in WINDOWS_FONTS if (Path("C:/Windows/Fonts") / n).exists()), None)


def font(size: int) -> ImageFont.FreeTypeFont:
    p = font_path()
    return ImageFont.truetype(p, size) if p else ImageFont.load_default(size)


def background(pal: list[tuple[int, int, int]], seed: str, w: int = W, h: int = H, shade: bool = True) -> Image.Image:
    """Dark gradient sky, soft city-light bokeh above the horizon, the same lights stretched on the river below.
    Any size (the lyric video uses a larger canvas to pan over); `shade` darkens the left for thumbnail text."""
    rng = random.Random(seed)
    k, horizon = w / W, int(h * 0.56)
    vs = (h / w) / (H / W)  # taller frames get their lights spread higher up the sky
    sky, river = np.array(pal[2], float), np.array(pal[2], float) * 0.6
    y = np.linspace(0, 1, h)[:, None, None]
    glow = np.array(pal[0], float) * 0.35
    top = sky * (1 - y / 0.56) + (sky + glow) * (y / 0.56)
    base = np.where(y < 0.56, top, river + glow * 0.25 * (1 - (y - 0.56) / 0.44))
    img = Image.fromarray(np.clip(np.broadcast_to(base, (h, w, 3)), 0, 255).astype("uint8"))

    lights = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    reflect = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d, r = ImageDraw.Draw(lights), ImageDraw.Draw(reflect)
    colours = [pal[0], pal[1], pal[3]]
    for _ in range(int(46 * (w * h) / (W * H))):
        x, rad = rng.randint(0, W), rng.randint(6, 26)
        cy = rng.randint(8, 150)
        c = (*rng.choice(colours), rng.randint(110, 220))
        x, rad, cy = x * k, rad * k, horizon - cy * k * vs
        d.ellipse([x - rad, cy - rad, x + rad, cy + rad], fill=c)
        r.ellipse([x - rad * 0.7, horizon + 6 * k, x + rad * 0.7, horizon + 40 * k + (horizon - cy) * 1.6], fill=(*c[:3], 90))
    img = Image.alpha_composite(img.convert("RGBA"), lights.filter(ImageFilter.GaussianBlur(7 * k)))
    img = Image.alpha_composite(img, reflect.filter(ImageFilter.GaussianBlur(9 * k)))
    if not shade:
        return img.convert("RGB")
    # darken the left so the text always reads
    mask = np.linspace(170, 0, w)[None, :].repeat(h, 0).astype("uint8")
    return Image.alpha_composite(img, Image.merge("RGBA", (*[Image.new("L", (w, h), 0)] * 3, Image.fromarray(mask)))).convert("RGB")


def fit(text: str, max_w: int, max_h: int, top: int, max_lines: int) -> tuple[list[str], ImageFont.FreeTypeFont]:
    """Largest font (<= top px) whose wrapped lines fit the box."""
    probe = ImageDraw.Draw(Image.new("L", (1, 1)))
    for size in range(top, 24, -4):
        f, lines, cur = font(size), [], ""
        for word in text.split():
            trial = f"{cur} {word}".strip()
            if probe.textlength(trial, font=f) <= max_w or not cur:
                cur = trial
            else:
                lines.append(cur)
                cur = word
        lines.append(cur)
        if len(lines) <= max_lines and all(probe.textlength(ln, font=f) <= max_w for ln in lines) \
                and len(lines) * size * 1.08 <= max_h:
            return lines, f
    return [text], font(24)


def neon_text(img: Image.Image, xy: tuple[int, int], lines: list[str], f, fill, glow, leading: float = 1.08) -> int:
    """Draw glowing text; returns the y below the last line."""
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    x, y = xy
    for ln in lines:
        d.text((x, y), ln, font=f, fill=(*glow, 255), stroke_width=3, stroke_fill=(*glow, 255))
        y += int(f.size * leading)
    blur = layer.filter(ImageFilter.GaussianBlur(16))
    img.alpha_composite(blur)
    img.alpha_composite(blur)
    d = ImageDraw.Draw(img)
    y = xy[1]
    for ln in lines:
        d.text((x, y), ln, font=f, fill=fill, stroke_width=5, stroke_fill=(10, 6, 24))
        y += int(f.size * leading)
    return y


def badge(img: Image.Image, accent: tuple[int, int, int], scale: float = 1.0) -> None:
    """The channel badge, top left. `scale` = image width / 1280 so it sits in the same place at any size."""
    d = ImageDraw.Draw(img)
    m, top = int(MARGIN * scale), int(44 * scale)
    logo = config.BRAND_DIR / "logo.png"
    if logo.exists():
        im = Image.open(logo).convert("RGBA")
        im.thumbnail((int(300 * scale), int(76 * scale)))
        img.alpha_composite(im, (m, top))
        return
    f = font(int(34 * scale))
    text = config.CHANNEL.upper()
    w = int(d.textlength(text, font=f))
    d.rounded_rectangle([m, top, m + w + int(44 * scale), top + int(60 * scale)], radius=int(30 * scale),
                        fill=(10, 6, 24, 230), outline=accent, width=max(2, int(3 * scale)))
    d.text((m + int(22 * scale), top + int(8 * scale)), text, font=f, fill=(255, 255, 255))


def render(data: dict, out: Path) -> Path:
    pal = palette_of(data)
    img = background(pal, data.get("slug") or data["title"]).convert("RGBA")
    badge(img, pal[0])
    f_tag = font(28)
    ImageDraw.Draw(img).text((W - MARGIN, 58), "OFFICIAL LYRIC VIDEO", font=f_tag, fill=(235, 235, 245), anchor="ra")

    mood = (data.get("mood_phrase") or data["title"]).upper()
    lines, f_mood = fit(mood, 800, 360, 170, 3)
    y = neon_text(img, (MARGIN, 150), lines, f_mood, (255, 255, 255), pal[0])
    t_lines, f_title = fit(data["title"], 800, 120, 74, 2)
    neon_text(img, (MARGIN, y + 16), t_lines, f_title, pal[3], pal[1])

    out.parent.mkdir(parents=True, exist_ok=True)
    songjson.backup(out)
    img.convert("RGB").save(out, quality=92, subsampling=0)
    return out
