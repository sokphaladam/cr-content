"""Step 5 — covers: the best frames of each clip as 1080x1920 covers with the song title in big readable type.

Frames are scored for sharpness, face size, open eyes, contrast, colourfulness and how well the subject sits on a
rule-of-thirds point. The title stays clear of what Shorts / Reels / TikTok draw over a video: the bottom 20%
(caption, music line) and the right 15% (like / comment / share buttons), and the top 8% (the app's header).
Text is drawn by pipeline._mag_sprite, which shapes Khmer through resvg (Pillow here can't).
"""
import math
import re
import subprocess
from pathlib import Path

import numpy as np

from ..config import HEIGHT, WIDTH
from .settings import blend
from .visual import colourfulness, contrast, eyes_open, faces, frames, sharpness

PARTS = {"sharpness": 0.25, "faces": 0.20, "eyes": 0.10, "contrast": 0.15, "colour": 0.15, "thirds": 0.15}
SAFE = {"left": 0.055, "right": 0.85, "top": 0.08, "bottom": 0.80}  # fractions of the frame the text stays inside
KHMER = re.compile("[ក-៿᧠-᧿]")


def _subject(gray: np.ndarray, face: tuple | None) -> tuple[float, float]:
    """Where the eye goes (0..1, 0..1): the biggest face, else the peak of a spectral-residual saliency map."""
    import cv2

    h, w = gray.shape
    if face:
        x, y, fw, fh = face
        return (x + fw / 2) / w, (y + fh * 0.4) / h
    small = cv2.resize(gray, (72, 128), interpolation=cv2.INTER_AREA).astype(np.float32)
    f = np.fft.fft2(small)
    log_amp = np.log(np.abs(f) + 1e-6)
    resid = log_amp - cv2.blur(log_amp, (3, 3))
    sal = np.abs(np.fft.ifft2(np.exp(resid + 1j * np.angle(f)))) ** 2
    sal = cv2.GaussianBlur(sal, (9, 9), 2.5)
    top = sal >= np.percentile(sal, 92)
    ys, xs = np.nonzero(top)
    return float(xs.mean() / 72), float(ys.mean() / 128)


def _thirds(cx: float, cy: float) -> float:
    """1 on a rule-of-thirds point, falling to 0 a sixth of the frame away (dead centre scores ~0.4)."""
    d = min(math.hypot(cx - px, cy - py) for px in (1 / 3, 2 / 3) for py in (1 / 3, 2 / 3))
    return max(0.0, 1 - d / 0.3)


def score_frame(bgr: np.ndarray) -> dict:
    import cv2

    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    found = faces(gray)
    face = found[0] if found else None
    cx, cy = _subject(gray, face)
    parts = {"sharpness": sharpness(gray), "contrast": contrast(gray), "colour": min(1.0, colourfulness(bgr) / 0.7),
             "faces": min(1.0, face[2] * face[3] / (gray.size * 0.05)) if face else 0.0,
             "eyes": eyes_open(gray, face) if face else 0.0, "thirds": _thirds(cx, cy)}
    bright = gray.mean() / 255
    exposure = max(0.0, 1 - abs(bright - 0.5) / 0.42)  # neither near-black nor blown out
    if not face:  # no face to judge: its parts don't count against the frame
        parts.pop("faces"), parts.pop("eyes")
    return {"score": round(blend(parts, PARTS) * (0.6 + 0.4 * exposure), 4), "parts": parts,
            "subject": (round(cx, 3), round(cy, 3)), "face": face}


def best_frames(video: Path, size: tuple[int, int], start: float, end: float, count: int, samples: int) -> list[dict]:
    """The `count` best frames in [start, end], at least ~1/6 of the clip apart (so they aren't the same moment)."""
    length = end - start
    rows = []
    for t, bgr in frames(video, size, samples / length, start + 0.3, length - 0.6, 540, 960):
        rows.append({"t": round(t, 2), **score_frame(bgr)})
    gap = max(1.0, length / 6)
    picked = []
    for r in sorted(rows, key=lambda r: -r["score"]):
        if all(abs(r["t"] - p["t"]) >= gap for p in picked):
            picked.append(r)
        if len(picked) == count:
            break
    return picked


def _frame_image(video: Path, size: tuple[int, int], at: float):
    """The 9:16 window of the frame at `at`, at full quality, as a 1080x1920 PIL image."""
    from PIL import Image

    from .visual import crop_filter

    proc = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{at:.3f}", "-i", str(video), "-frames:v", "1",
                           "-vf", crop_filter(size, WIDTH, HEIGHT).replace("flags=area", "flags=lanczos"),
                           "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                          stdin=subprocess.DEVNULL, capture_output=True, check=True)
    return Image.frombytes("RGB", (WIDTH, HEIGHT), proc.stdout[:WIDTH * HEIGHT * 3])


def _lines(title: str, sprite, px: int, max_w: float) -> list[str]:
    """The title in 2 lines that fit `max_w` at `px` (balanced: the break nearest the middle), or 3 when a long
    title (a Short's) can't fit in 2."""
    words = title.split()
    if len(words) < 2 or sprite(title, px)["w"] <= max_w:
        return [title]
    widest = lambda rows: max(sprite(r, px)["w"] for r in rows)
    splits = [(" ".join(words[:k]), " ".join(words[k:])) for k in range(1, len(words))]
    two = list(min(splits, key=widest))
    if widest(two) <= max_w or len(words) < 3:
        return two
    threes = [(" ".join(words[:a]), " ".join(words[a:b]), " ".join(words[b:]))
              for a in range(1, len(words) - 1) for b in range(a + 1, len(words))]
    return list(min(threes, key=widest))


def _mixed_sprite(text: str, px: int, cache: dict, track: float = 0.0, weight: str = "heavy") -> dict:
    """One line like pipeline._mag_sprite, with each script in its own font: Khmer runs in a Khmer face (shaped by
    resvg), the rest in a Latin display face, so "ចាក់ម្ដងទៀត Replay" has heavy letters in both."""
    from PIL import Image

    from ..pipeline import _mag_sprite
    from ..styles import FONTS, font_path

    latin = ("seguibl.ttf" if font_path("seguibl.ttf") else FONTS["en"]["Impact"]) if weight == "heavy" else (
        "seguisb.ttf" if font_path("seguisb.ttf") else FONTS["en"]["Arial"])
    khmer_family = "Khmer OS Muol Light" if weight == "heavy" else "Khmer OS Battambang"
    khmer_file = FONTS["km"][khmer_family]
    runs = [m.group(0) for m in re.finditer(r"[ក-៿᧠-᧿​‌‍]+|[^ក-៿᧠-᧿]+",
                                            text)]
    if len(runs) == 1:
        km = bool(KHMER.search(text))
        return _mag_sprite(text, px, khmer_file if km else latin, cache, khmer_family if km else "",
                           0.0 if km else track)
    parts = []
    for run in runs:
        if run[:1].isspace():
            parts.append({"space": px * 0.22})
        if run.strip():
            km = bool(KHMER.search(run))
            parts.append(_mag_sprite(run.strip(), px, khmer_file if km else latin, cache,
                                     khmer_family if km else "", 0.0 if km else track))
            if run[-1:].isspace():
                parts.append({"space": px * 0.22})
    inks = [p for p in parts if "img1" in p]
    asc = max(p["asc"] for p in inks)
    desc = max(p["desc"] for p in inks)
    width = sum(p.get("w", 0) + p.get("space", 0) for p in parts) + px * 0.12 * (len(inks) - 1)
    img = Image.new("L", (math.ceil(width) + 2, math.ceil(asc + desc) + 2), 0)
    x = 0.0
    for p in parts:
        if "space" in p:
            x += p["space"]
            continue
        img.paste(p["img1"], (round(x), round(asc - p["asc"])), p["img1"])
        x += p["w"] + px * 0.12
    img = img.crop(img.getbbox() or (0, 0, 2, 2))
    return {"img1": img, "w": img.width, "asc": asc, "desc": desc}


def render_cover(video: Path, size: tuple[int, int], at: float, title: str, artist: str, out: Path,
                 subject: tuple[float, float], face: tuple | None, place: str = "auto") -> str:
    """Draw one cover; returns where the title went ("top" or "low")."""
    from PIL import Image, ImageChops, ImageEnhance, ImageFilter

    img = _frame_image(video, size, at)
    img = img.filter(ImageFilter.UnsharpMask(1.0, 50, 2))
    img = ImageEnhance.Contrast(ImageEnhance.Color(img).enhance(1.12)).enhance(1.06)
    W, H = img.size

    cache: dict = {}
    big = re.sub(r"\s+", " ", title.upper()).strip()  # upper() leaves Khmer as it is

    # the biggest size whose (up to 2) lines fit the safe width and a third of the safe height
    max_w = (SAFE["right"] - SAFE["left"]) * W
    px = 260
    while px > 70:
        rows = _lines(big, lambda t, p: _mixed_sprite(t, p, cache), px, max_w)
        sprites = [_mixed_sprite(r, px, cache) for r in rows]
        block_h = sum(s["asc"] + s["desc"] for s in sprites) + px * 0.12 * (len(rows) - 1)
        if max(s["w"] for s in sprites) <= max_w and block_h <= (SAFE["bottom"] - SAFE["top"]) * H / 3:
            break
        px -= 10
    small = None
    if artist.strip():
        small = _mixed_sprite(artist.strip().upper(), max(34, round(px * 0.28)), cache, 0.12, "light")
    gap = px * 0.22
    total_h = block_h + ((small["asc"] + small["desc"] + gap) if small else 0)

    # top of the safe area, or its bottom: whichever keeps the text off the face / subject
    if place == "auto":
        sy = (face[1] + face[3] / 2) / 960 if face else subject[1]
        place = "low" if sy < 0.5 else "top"
    y0 = SAFE["top"] * H + px * 0.15 if place == "top" else SAFE["bottom"] * H - total_h - px * 0.1
    x0 = SAFE["left"] * W

    # a soft dark band behind the text so it reads on any picture
    shade = Image.new("L", (W, H), 0)
    band = Image.new("L", (W, round(total_h + px * 1.2)), 150)
    shade.paste(band, (0, round(y0 - px * 0.6)))
    shade = shade.filter(ImageFilter.GaussianBlur(px * 0.55))
    img = Image.composite(Image.new("RGB", (W, H), (8, 8, 14)), img, shade)

    # ink: the letters, a dark outline round them and a soft drop shadow; title white, artist in the accent
    ink = Image.new("L", (W, H), 0)
    accent_ink = Image.new("L", (W, H), 0)
    y = y0
    for s in sprites:
        ink.paste(s["img1"], (round(x0), round(y)), s["img1"])
        y += s["asc"] + s["desc"] + px * 0.12
    if small:
        accent_ink.paste(small["img1"], (round(x0 + px * 0.04), round(y - px * 0.12 + gap)), small["img1"])
    both = ImageChops.lighter(ink, accent_ink)
    outline = both.filter(ImageFilter.MaxFilter(max(3, (px // 22) | 1)))
    shadow = outline.filter(ImageFilter.GaussianBlur(px * 0.06))
    shadow = ImageChops.offset(shadow, round(px * 0.03), round(px * 0.05))
    img = Image.composite(Image.new("RGB", (W, H), (0, 0, 0)), img, shadow.point(lambda v: v * 0.75))
    img = Image.composite(Image.new("RGB", (W, H), (10, 10, 18)), img, outline)
    img = Image.composite(Image.new("RGB", (W, H), (255, 255, 255)), img, ink)
    img = Image.composite(Image.new("RGB", (W, H), _accent(img)), img, accent_ink)
    img.save(out, quality=93, subsampling=0)
    return place


def _accent(img) -> tuple[int, int, int]:
    """A bright colour from the picture itself (its most saturated common hue), for the artist line."""
    hsv = np.asarray(img.convert("HSV").resize((90, 160))).reshape(-1, 3).astype(int)
    vivid = hsv[(hsv[:, 1] > 110) & (hsv[:, 2] > 120)]
    if len(vivid) < 50:
        return 255, 214, 74
    hue = int(np.bincount(vivid[:, 0] // 8, minlength=32).argmax() * 8 + 4)
    from PIL import Image
    return Image.new("HSV", (1, 1), (hue, 200, 255)).convert("RGB").getpixel((0, 0))


def make_covers(video: Path, size: tuple[int, int], start: float, end: float, title: str, artist: str,
                out_dir: Path, cfg: dict) -> list[dict]:
    """The clip's best frames as covers in out_dir (cover_1.jpg, ...), best first, with their scores."""
    c = cfg["covers"]
    picked = best_frames(video, size, start, end, c["per_clip"], c["samples"])
    out = []
    used: set[str] = set()
    for k, f in enumerate(picked, 1):
        path = out_dir / f"cover_{k}.jpg"
        # the best frame puts the title where it fits; the next tries the other place, to compare layouts, unless
        # the subject is there (a face in the top third stays uncovered)
        sy = (f["face"][1] + f["face"][3] / 2) / 960 if f["face"] else f["subject"][1]
        free = [p for p in ("top", "low") if p not in used and not (p == "top" and sy < 0.4)
                and not (p == "low" and sy > 0.6)]
        place = "auto" if not used or not free else free[0]
        place = render_cover(video, size, f["t"], title, artist, path, f["subject"], f["face"], place)
        used.add(place)
        out.append({"file": path.name, "at": f["t"], "score": f["score"], "subject_y": round(sy, 3),
                    "parts": {k2: round(v, 3) for k2, v in f["parts"].items()}, "title_at": place})
    return out
