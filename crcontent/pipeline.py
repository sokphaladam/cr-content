"""Topic (or script file) in -> finished vertical video + post metadata out."""
import hashlib
import json
import platform
import random
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Callable

from . import art, fx, pacing, sfx, thumbs, voiceover
from .captions import THUMB_STYLES, build_ass, build_thumbnail_ass, overlay_lines
from .captions import _bare as _bare_word
from .config import ASSETS_DIR, LANGS, OUTPUT_DIR, ROOT, SCENE_PAD_SEC, frame_size, orientation
from .render import concat, duration, finalize, render_scene, run, thumbnail
from .script import VideoScript, generate_script
from .visuals import IMAGE_EXTS, FootagePicker


def slugify(text: str, limit: int = 40) -> str:
    slug = re.sub(r"[^\w]+", "-", text.lower(), flags=re.ASCII).strip("-")
    return (slug or "video")[:limit]


def post_body(title: str, caption: str, tags: str, track: Path | str | None = None, sources: str = "",
              photos: list[str] = ()) -> str:
    """post.txt: title line, the caption (plus the works it cites, the credits of real photos used and the music's
    credit when its licence asks for one), then the #tags."""
    from .music import credit

    cited = f"Sources: {sources.strip()}" if sources.strip() else ""
    shown = "\n".join(dict.fromkeys(p for p in photos if p))
    body = "\n\n".join(x for x in (caption.strip(), cited, shown, credit(track)) if x)
    return f"{title}\n\n{body}\n\n{tags}\n"


def _existing(media: str) -> Path | None:
    """A project-relative media path chosen in the editor, if the file is still there."""
    path = ROOT / media if media else None
    return path if path and path.is_file() else None


def pick_music(music: str | None, mood: str = "") -> Path | None:
    """`music`: "none", a file, or None for a random track, preferring those whose file name shares the most words
    with `mood`."""
    from .music import best_matches

    if music == "none":
        return None
    if music:
        return Path(music)
    from .music import track_use

    tracks = list((ASSETS_DIR / "music").glob("*.mp3")) if (ASSETS_DIR / "music").exists() else []
    # a random or mood pick only takes tracks a monetized video may use (unknown licences only when nothing else)
    safe = [t for t in tracks if track_use(t) == "ok"] or [t for t in tracks if track_use(t) == "unknown"]
    tracks = safe or tracks
    matching = best_matches(mood, [t.name for t in tracks])
    return random.choice([t for t in tracks if t.name in matching] or tracks) if tracks else None


def _install_font(profile, fonts_dir: Path, font_file: str = "") -> None:
    """Copy the caption font (the language's, or `font_file`) next to the subtitles so libass always finds it."""
    from .styles import font_path

    font_file = font_file or profile.font_file
    fonts_dir.mkdir(exist_ok=True)
    found = font_path(font_file)
    if found:
        shutil.copy(found, fonts_dir / found.name)
        return
    print(f"  ! font {font_file} not found; captions will use a fallback font")


def _meta(job: Path) -> dict:
    path = job / "meta.json"
    try:
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    except (ValueError, OSError):
        return {}  # empty or corrupt: one broken folder mustn't break every listing


def _save_meta(job: Path, meta: dict) -> None:
    (job / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")


def job_size(job: Path) -> tuple[int, int]:
    """Frame size of a job's video: vertical unless it was made as a 16:9 music video."""
    return frame_size(_meta(job).get("aspect"))


def thumbnail_source(job: Path) -> Path:
    """The caption-free work/joined.mp4 when it's still there, so the video's own captions don't show through."""
    joined = job / "work" / "joined.mp4"
    return joined if joined.exists() else job / "video.mp4"


def _cover_subject(job: Path, source: Path, at: float, image: Path | None) -> tuple[tuple | None, tuple | None]:
    """(subject, head) of a cover's picture as (x0, y0, x1, y1) fractions of the cover frame, so the headline can
    keep off the face; (None, None) when it can't be told (no torch / depth model: the headline takes its usual
    place). The picture is cropped the way the cover is (render.thumbnail) at half size, its depth map (fx) split
    into near and far (Otsu), and the head is the top of what's near: the subject's top, as wide as it is there."""
    import numpy as np

    if not fx.available():
        return None, None
    W, H = job_size(job)
    try:
        src = image or source
        key = hashlib.sha1(f"{src.resolve()}|{src.stat().st_mtime_ns}|{0 if image else round(at, 2)}|{W}x{H}"
                           .encode()).hexdigest()[:12]
        probe = job / "work" / f"cover_probe_{key}.png"  # same picture, same file: the depth map stays cached
        if not probe.exists():
            pick = ["-i", str(src.resolve())] if image else ["-ss", f"{at:.2f}", "-i", str(src.resolve())]
            run(["ffmpeg", "-y", "-hide_banner", "-v", "error", *pick, "-frames:v", "1", "-vf",
                 f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},scale={W // 2}:-2",
                 str(probe.resolve())])
        d = fx.depth_map(probe)[0, 0].float().cpu().numpy()
        # Otsu: the depth that best splits the picture into a near and a far group
        hist, edges = np.histogram(d, bins=64, range=(0.0, 1.0))
        p = hist / max(hist.sum(), 1)
        mids = (edges[:-1] + edges[1:]) / 2
        w0 = np.cumsum(p)
        m0 = np.cumsum(p * mids)
        between = (m0[-1] * w0 - m0) ** 2 / np.maximum(w0 * (1 - w0), 1e-9)
        near = d > mids[int(np.argmax(between))]
        if not 0.03 <= near.mean() <= 0.7:  # no clear figure (a landscape, a wall): the nearest 15%
            near = d >= np.quantile(d, 0.85)
        h, w = near.shape
        rows = near.mean(1)
        solid = np.nonzero(rows >= max(0.04, 0.2 * rows.max()))[0]  # not a stray beak, hair or branch tip
        if not len(solid):
            return None, None
        ys, xs = np.nonzero(near)
        subject = (np.percentile(xs, 2) / w, solid[0] / h, np.percentile(xs, 98) / w, np.percentile(ys, 98) / h)
        # a head is about a third of a figure (less of a full body, all of a close-up), within sensible limits
        tall = subject[3] - subject[1]
        hh = min(max(0.3 * tall, 0.12), 0.25) if H > W else min(max(0.35 * tall, 0.2), 0.45)
        top = near[solid[0]: solid[0] + max(1, round(hh * h))]
        hx = np.nonzero(top.any(0))[0]
        cols = np.nonzero(top.mean(0) > 0.15)[0] if top.size else hx
        cols = cols if len(cols) else hx
        head = (cols[0] / w, solid[0] / h, (cols[-1] + 1) / w, solid[0] / h + hh)
        return tuple(float(v) for v in subject), tuple(float(v) for v in head)
    except Exception as e:  # no model download, a broken frame: the headline takes its usual place
        print(f"  ! cover subject: {type(e).__name__}: {e}")
        return None, None


def draw_thumbnail(job: Path, text: str, at: float, lang: str, out: Path,
                   style: str = "bold", emphasis: str = "", image: Path | None = None) -> float:
    """Draw the frame at `at` seconds (or the photo `image` instead) with `text` as a big headline (no text = plain
    picture) into `out`, placed clear of the picture's subject (_cover_subject).

    Returns the frame time actually used (clamped to the video).
    """
    from .captions import thumb_font

    profile = LANGS.get(lang, LANGS["en"])
    work = job / "work"
    work.mkdir(exist_ok=True)
    source = thumbnail_source(job)
    at = max(0.0, min(at, duration(source) - 0.1))
    ass_name = None
    if text.strip():
        ass_name = f"{out.stem}.ass"
        subject, head = _cover_subject(job, source, at, image)
        (work / ass_name).write_text(build_thumbnail_ass(text, profile, style, emphasis, size=job_size(job),
                                                         subject=subject, head=head), encoding="utf-8")
        _, font_file = thumb_font(profile)  # the heavy headline face (Segoe UI Black...), or the Khmer font
        if not (work / "fonts" / font_file).exists():
            _install_font(profile, work / "fonts", font_file)
    out.parent.mkdir(exist_ok=True)
    thumbnail(source, at, out, work, ass_name, size=job_size(job), image=image)
    return at


COVER_STYLES = (*THUMB_STYLES, "designed")  # designed: a whole layout Claude draws around the picture


def _photo_for_cover(job: Path, at: float, image: Path | None, out: Path) -> Path:
    """The picture a designed cover is built around: the photo `image`, or the frame at `at` with the same lift in
    contrast and colour that classic covers get."""
    if image:
        return image
    W, H = job_size(job)
    run(["ffmpeg", "-y", "-hide_banner", "-ss", f"{at:.2f}", "-i", str(thumbnail_source(job).resolve()),
         "-frames:v", "1", "-vf", f"scale={W}:{H}:force_original_aspect_ratio=increase:flags=lanczos,crop={W}:{H},"
         f"setsar=1,eq=contrast=1.06:saturation=1.15,cas=0.4", "-q:v", "2", str(out.resolve())])
    return out


def _design_about(job: Path) -> tuple[str, str]:
    """(kind, description) of the job for Claude's cover design."""
    info = thumbs.brief(job)
    return info.get("kind", "video"), json.dumps(info, ensure_ascii=False, indent=2)


def draw_designed(job: Path, text: str, at: float, lang: str, out: Path, emphasis: str = "",
                  image: Path | None = None, design: Path | None = None, direction: str = "") -> float:
    """A designed cover in `out` (with its template next to it as .svg and what it says as .json): reuses `design`
    (a template Claude made earlier) as is when its headline matches, re-sets the headline in the same design when it
    doesn't, and asks Claude for a fresh design when there's none. Returns the frame time used."""
    work = job / "work"
    work.mkdir(exist_ok=True)
    at = max(0.0, min(at, duration(thumbnail_source(job)) - 0.1))
    photo = _photo_for_cover(job, at, image, work / f"{out.stem}_photo.jpg")
    baked = json.loads(design.with_suffix(".json").read_text(encoding="utf-8")) \
        if design and design.with_suffix(".json").exists() else {}
    svg = design.read_text(encoding="utf-8") if design and design.exists() else ""
    out.parent.mkdir(exist_ok=True)
    if svg and baked.get("text") == text and baked.get("emphasis", "") == emphasis:
        art.rasterize(svg, job_size(job), out, photo)  # same words: only the picture may have changed
        if design != out.with_suffix(".svg"):
            shutil.copy(design, out.with_suffix(".svg"))
    else:
        kind, about = _design_about(job)
        art.make_cover(photo, text, emphasis, about, lang, job_size(job), out, kind, direction, base_svg=svg)
    out.with_suffix(".json").write_text(json.dumps({"text": text, "emphasis": emphasis}, ensure_ascii=False),
                                        encoding="utf-8")
    return at


COVER_FRAME = "cover.png"  # a one-cover music video keeps its frame in work/ for the magazine thumbnail


def _mag_sprite(text: str, px: int, file: str, cache: dict, family: str = "", track: float = 0.0) -> dict:
    """One line of `text` at `px` (a 1x font size) as white ink on black, drawn at 2x and cropped to the ink:
    {"img2": 2x PIL "L", "img1": the same at 1x, "w": 1x width, "asc"/"desc": 1x ink above / below the baseline}.
    `family` (Khmer): drawn by resvg, which shapes the script; Pillow here has no raqm, so its subscripts and vowels
    fall apart into dotted circles. `track`: extra space after each letter, in ems (spaced small caps)."""
    import html
    import io

    from PIL import Image, ImageDraw, ImageFont

    from .styles import font_path

    key = (text, px, file, family, track)
    if key in cache:
        return cache[key]
    p2 = px * 2
    img = None
    if family and px < 360:  # resvg is slow at big sizes: smaller ones are taken down from one big drawing
        big = _mag_sprite(text, 360, file, cache, family)
        k = px / 360
        img2 = big["img2"].resize((max(1, round(big["img2"].width * k)), max(1, round(big["img2"].height * k))),
                                  Image.LANCZOS)
        img1 = img2.resize((max(1, round(img2.width / 2)), max(1, round(img2.height / 2))), Image.LANCZOS)
        cache[key] = out = {"img2": img2, "img1": img1, "w": img2.width / 2, "asc": big["asc"] * k,
                            "desc": big["desc"] * k}
        return out
    if family:
        import resvg_py

        from .art import _font_dirs

        w, h = round(p2 * (len(text) * 0.75 + 1.5)), round(p2 * 2.6)  # Khmer: several code points per letter
        base = round(p2 * 1.6)
        svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}"><text x="{p2 // 2}" y="{base}" '
               f'font-family="{family}" font-size="{p2}" fill="white">{html.escape(text)}</text></svg>')
        try:
            png = bytes(resvg_py.svg_to_bytes(svg_string=svg, width=w, height=h, font_dirs=_font_dirs()))
            img = Image.open(io.BytesIO(png)).getchannel("A")
            img = img if img.getbbox() else None  # font not found: Pillow's unshaped letters beat nothing
        except Exception:
            img = None
    if img is None:
        found = font_path(file)
        font = ImageFont.truetype(str(found), p2) if found else ImageFont.load_default(p2)
        steps = [font.getlength(ch) + track * p2 for ch in text] if track else [font.getlength(text)]
        w, h, base = round(sum(steps) + p2), round(p2 * 2.4), round(p2 * 1.6)
        img = Image.new("L", (w, h), 0)
        draw = ImageDraw.Draw(img)
        x = p2 / 2
        for part, step in zip(text if track else [text], steps):
            draw.text((x, base), part, font=font, fill=255, anchor="ls")
            x += step
    box = img.getbbox() or (0, 0, 2, 2)
    img2 = img.crop(box)
    img1 = img2.resize((max(1, round(img2.width / 2)), max(1, round(img2.height / 2))), Image.LANCZOS)
    cache[key] = out = {"img2": img2, "img1": img1, "w": img2.width / 2, "asc": (base - box[1]) / 2,
                        "desc": (box[3] - base) / 2}
    return out


def _mag_accent(art, person, bg) -> tuple[int, int, int]:
    """The title colour: the darkest saturated hue the character wears (hair, eyes, a ribbon), found as the
    heaviest bin of a hue histogram that weighs each pixel by how saturated and how dark it is, then set deep
    (~42% value) and darkened until it stands 4.5:1 against the background (comfortably over the 3:1 floor). Pale
    pixels and warm ones (skin; orange or blonde hair, which only darken into brown) don't vote. A character with no
    colour to give gets deep plum on pink/violet, else navy."""
    import colorsys

    import numpy as np

    def lum(c):  # WCAG relative luminance
        c = np.asarray(c, dtype=np.float64) / 255
        c = np.where(c <= 0.03928, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
        return float(c @ [0.2126, 0.7152, 0.0722])

    pix = art[person > 0.9][::7].astype(np.float64) / 255
    hue, sat = None, 0.7
    if len(pix) > 500:
        mx, mn = pix.max(1), pix.min(1)
        s = (mx - mn) / np.maximum(mx, 1e-6)
        r, g, b = pix.T
        d = np.maximum(mx - mn, 1e-6)
        h = np.where(mx == r, (g - b) / d % 6, np.where(mx == g, (b - r) / d + 2, (r - g) / d + 4)) * 60
        # orange, gold and olive go brown and muddy when darkened enough to read: they don't vote either
        ok = (s > 0.25) & (mx > 0.1) & (mx < 0.85) & ~((h > 12) & (h < 70))
        weight = s * (1.2 - mx)
        if weight[ok].sum() > 0.004 * len(pix):
            hist = np.bincount((h[ok] // 15).astype(int) % 24, weights=weight[ok], minlength=24)
            hist = hist + 0.5 * (np.roll(hist, 1) + np.roll(hist, -1))  # a hue on a bin edge isn't split in two
            centre = np.argmax(hist) * 15 + 7.5
            near = ok & (np.abs((h - centre + 180) % 360 - 180) < 22)
            ang = np.deg2rad(h[near])
            hue = np.rad2deg(np.arctan2((np.sin(ang) * weight[near]).sum(), (np.cos(ang) * weight[near]).sum())) % 360
            sat = float(np.clip(np.median(s[near]), 0.55, 0.9))
    if hue is None:
        bh = colorsys.rgb_to_hsv(*(np.asarray(bg) / 255))[0] * 360
        hue, sat = (290, 0.6) if bh > 270 or bh < 20 else (228, 0.68)
    v = 0.42
    while True:
        rgb = tuple(round(c * 255) for c in colorsys.hsv_to_rgb(hue / 360, sat, v))
        if (lum(bg) + 0.05) / (lum(rgb) + 0.05) >= 4.5 or v < 0.12:
            return rgb
        v *= 0.92


def draw_magazine(job: Path, text: str, lang: str, out: Path) -> bool:
    """A magazine / playlist-cover thumbnail from a one-cover music video's frame: `text` in huge heavy letters in
    a deep colour taken from the character, set behind her, and one short spaced line of info in a left corner.
    False when the video has no cover frame (made before one-cover mode, or with several pictures).

    The title must stay readable with her in front of it, so each layout is tried in turn and checked by laying the
    character's mask (plus the halo kept clear round her) over the letters: a placement fails when any letter is over
    15% hidden or the hidden letters add up to over 8%. In order: (a) the words either side of her head across the
    top, (b) one line across the top that clears the head (or lets it fall in a word gap), (c) the same lower down,
    either side of / behind the shoulders, (d) a panel: one word per line, left-aligned in the emptier side of the
    frame (above her in a 9:16 frame), which is always taken (drawn in front of her when even that is covered)."""
    import numpy as np
    from PIL import Image, ImageEnhance, ImageFilter, ImageOps
    from scipy import ndimage

    from .lyrics import SongScript
    from .styles import FONTS, font_path

    frame = job / "work" / COVER_FRAME
    if not frame.exists():
        return False
    cover = Image.open(frame).convert("RGB")
    W, H = cover.size
    base_px = min(W, H)  # sizes are set against the short side: 1080 in both 16:9 and 9:16
    target = np.median(np.concatenate([np.asarray(cover)[0], np.asarray(cover)[:, 0]]), axis=0).astype(np.float32)
    _, bg = _flatten(cover, target, with_mask=True)
    person = np.asarray(ImageOps.invert(bg).filter(ImageFilter.GaussianBlur(1.2)), dtype=np.float32) / 255
    # the art only, before any lettering: a light unsharp mask, +10% colour and +6% contrast, the way covers are
    # finished; the background colour is read again after, so halos and grain match it exactly
    art = ImageEnhance.Contrast(ImageEnhance.Color(cover.filter(ImageFilter.UnsharpMask(0.8, 60, 2))).enhance(1.10))
    art = np.asarray(art.enhance(1.06), dtype=np.float32)
    paper = np.median(np.concatenate([art[0], art[:, 0]]), axis=0)
    accent = np.array(_mag_accent(art, person, paper), dtype=np.float32)
    away = ndimage.distance_transform_edt(person < 0.5)  # how far each pixel is from the character

    km = lang == "km"
    heavy = FONTS["km"]["Khmer OS Muol Light"] if km else (
        "seguibl.ttf" if font_path("seguibl.ttf") else FONTS["en"]["Impact"])
    family = "Khmer OS Muol Light" if km else ""
    cache: dict = {}

    def sprite(t, px):
        return _mag_sprite(t, px, heavy, cache, family)

    # emoji have no glyph in the heavy title fonts (they'd draw as empty boxes): left out of the cover's title
    text = re.sub("[\U0001F000-\U0001FAFF\u2600-\u27BF\uFE0F\u200D]", "", text)
    big = re.sub(r"\s+", " ", text if km else text.upper()).strip()
    if not big:  # nothing but emoji: the classic cover instead
        return False
    toks = [t for t in re.split(r"[ ​]+", big) if t]
    join = "" if km else " "
    # font size from a wanted cap height (Latin: the H; Khmer: the line's ink above the baseline)
    ratio = sprite("H" if not km else join.join(toks), 200)["asc"] / 200
    m, mt = W * 0.045, H * 0.045

    def sizes(most, least):  # font sizes, biggest first, for cap heights from `most` down to `least` px
        cap, out_ = most, []
        while cap >= least:
            out_.append(max(8, round(cap / ratio)))
            cap *= 0.93
        return list(dict.fromkeys(out_))

    def render(items, scale):  # items: (text, px, ink left x, baseline y) at 1x -> the title's alpha at 1x
        canvas = Image.new("L", (W * scale, H * scale), 0)
        for t, px, x, y in items:
            s = sprite(t, px)
            canvas.paste(255, (round(x * scale), round((y - s["asc"]) * scale)), s[f"img{scale}"])
        return canvas if scale == 1 else canvas.resize((W, H), Image.LANCZOS)

    def bounds(items):
        boxes = [(x, y - sprite(t, px)["asc"], x + sprite(t, px)["w"], y + sprite(t, px)["desc"])
                 for t, px, x, y in items]
        return (max(0, int(min(b[0] for b in boxes)) - 2), max(0, int(min(b[1] for b in boxes)) - 2),
                min(W, int(max(b[2] for b in boxes)) + 3), min(H, int(max(b[3] for b in boxes)) + 3))

    def hidden(px, box):  # what covers the letters: the character plus the halo kept clear round her
        x0, y0, x1, y1 = box
        halo = max(1.5, px * 0.035)
        return np.maximum(person[y0:y1, x0:x1], np.clip(halo + 0.5 - away[y0:y1, x0:x1], 0, 1))

    def legible(items) -> bool:
        box = bounds(items)
        if box[0] < 0 or box[2] > W or box[3] > H or box[2] <= box[0] or box[3] <= box[1]:
            return False
        x0, y0, x1, y1 = box
        ink = np.asarray(render(items, 1))[y0:y1, x0:x1] > 127
        letters, n = ndimage.label(ink, np.ones((3, 3)))
        if not n:
            return False
        idx = np.arange(1, n + 1)
        area = ndimage.sum(ink, letters, idx)
        lost = ndimage.sum(hidden(items[0][1], box), letters, idx)
        whole = area >= 0.15 * np.median(area)  # an apostrophe or a Khmer mark isn't a letter of its own
        # stricter than "over a third hidden": at 20% an F already loses the ends of its arms and reads as an E or I
        return (lost[whole] / area[whole]).max() <= 0.15 and lost.sum() / area.sum() <= 0.08

    def cols_in(y0, y1, share):  # the character's columns across rows y0..y1 (those she fills `share` of)
        rows = person[max(0, int(y0)): max(int(y0) + 1, int(y1))]
        return np.where(rows.mean(0) > share)[0]

    def split(top, pxs):  # (a)/(c): two halves of the title either side of her, tucked a little behind
        cuts = sorted(range(1, len(toks)), key=lambda i: abs(len(join.join(toks[:i])) - len(join.join(toks[i:]))))
        for px in pxs:
            for i in cuts[:2]:
                left, right = join.join(toks[:i]), join.join(toks[i:])
                sl, sr = sprite(left, px), sprite(right, px)
                y = top + max(sl["asc"], sr["asc"])
                cols = cols_in(top, y + max(sl["desc"], sr["desc"]), 0.15)
                if not len(cols):
                    continue  # she isn't at this height: that's a straight line's job
                for tuck in (0.05, 0.03, 0.015, 0):
                    end, start = cols[0] + tuck * W, cols[-1] - tuck * W
                    if start - end < px * 0.3:  # always at least a word space between the halves
                        mid = (cols[0] + cols[-1]) / 2
                        end, start = mid - px * 0.15, mid + px * 0.15
                    if sl["w"] <= end - m and sr["w"] <= W - m - start:
                        yield [(left, px, end - sl["w"], y), (right, px, start, y)]

    def line(top, pxs):  # (b)/(c): one line, centred, or shifted so her head falls in a gap between words
        whole = join.join(toks)
        for px in pxs:
            s = sprite(whole, px)
            if s["w"] > W - 2 * m:
                continue
            y = top + s["asc"]
            xs = [(W - s["w"]) / 2]
            cols = cols_in(top, y + s["desc"], 0.15)
            if len(cols) and not km:
                centre = (cols[0] + cols[-1]) / 2
                for i in range(1, len(toks)):
                    gap = (sprite(join.join(toks[:i]), px)["w"] + s["w"] - sprite(join.join(toks[i:]), px)["w"]) / 2
                    xs.append(min(max(centre - gap, m), W - m - s["w"]))
            for x in xs:
                yield [(whole, px, x, y)]

    def panel_lines():  # one word per line; past four lines the shortest neighbours share one
        rows = list(toks)
        while len(rows) > 4:
            i = min(range(len(rows) - 1), key=lambda k: len(rows[k]) + len(rows[k + 1]))
            rows[i:i + 2] = [join.join(rows[i:i + 2])]
        return rows

    def panel(px, x_at, centre_y, align="left"):
        rows = panel_lines()
        ss = [sprite(r, px) for r in rows]
        pitch = (ratio * px * 1.2) if not km else max(s["asc"] + s["desc"] for s in ss) * 1.05
        y = centre_y - ((len(rows) - 1) * pitch + ss[-1]["asc"]) / 2 + ss[0]["asc"]
        return [(r, px, x_at if align == "left" else x_at - s["w"] / 2, y + k * pitch)
                for k, (r, s) in enumerate(zip(rows, ss))]

    def panel_tall(items):
        b = bounds(items)
        return b[1] < mt * 0.8 or b[3] > H * 0.84  # keep the bottom for the info line

    top_px = sizes(base_px * 0.22, base_px * 0.11)
    tries = []
    if len(toks) >= 2:
        tries.append(("split", split(mt, top_px)))
    tries.append(("line", line(mt, top_px)))
    for k in (0.22, 0.32, 0.42) if W >= H else (0.2, 0.3):  # (c) lower down: behind / either side of the shoulders
        if len(toks) >= 2:
            tries.append(("split", split(H * k, top_px)))
        tries.append(("line", line(H * k, top_px)))
    chosen, layout, front, x_at = None, "", False, m
    for name, gen in tries:
        chosen = next((items for items in gen if legible(items)), None)
        if chosen:
            layout = name
            break
    if not chosen:  # (d) the side panel
        layout, rows = "panel", panel_lines()
        widest = lambda px: max(sprite(r, px)["w"] for r in rows)  # noqa: E731
        if W >= H:
            occupied = np.where((person > 0.5).mean(0) > 0.02)[0]
            lfree = occupied[0] if len(occupied) else W
            rfree = W - 1 - occupied[-1] if len(occupied) else W
            on_left = lfree >= rfree or rfree < W * 0.3  # a sliver on the right is no panel: left, over her hair
            x_at = W * 0.065 if on_left else occupied[-1] + W * 0.04
            # the letters may run on behind her shoulder or hair a little, as long as they still read
            room = max(lfree - W * 0.02, W * 0.47) - x_at if on_left else W * 0.95 - x_at
            fits = [px for px in sizes(base_px * 0.157, base_px * 0.06) if widest(px) <= room]
            fits = [px for px in fits if not panel_tall(panel(px, x_at, H * 0.44))] or fits[-1:] or [12]
            # behind her, as big as still reads (a little higher or lower clears a shoulder or a fall of hair);
            # below ~70 px caps it's no cover title any more, and it goes in front of her instead
            chosen = next((items for items in (panel(px, x_at, H * cy) for px in fits if px * ratio >= base_px * 0.065
                                               for cy in (0.44, 0.36, 0.52)) if not panel_tall(items)
                           and legible(items)), None)
            if not chosen:  # her hair fills both sides: the biggest that fits, in front of her
                chosen, front = panel(fits[0], x_at, H * 0.44), True
        else:  # 9:16: stacked and centred in the space above her head
            head = np.where((person > 0.5).mean(1) > 0.02)[0]
            free = head[0] if len(head) else H * 0.3
            for px in sizes(base_px * 0.157, base_px * 0.06):
                if widest(px) > W - 2 * m:
                    continue
                items = panel(px, W / 2, max(free / 2, 0), align="centre")
                shift = mt - bounds(items)[1]
                items = [(t, p, x, y + max(shift, 0)) for t, p, x, y in items]
                if legible(items):
                    chosen = items
                    break
            if not chosen:  # her head is at the very top: the title goes in front of her, low over her clothes
                px = next((px for px in sizes(base_px * 0.24, 8) if widest(px) <= W - 2 * m), 8)
                chosen, front = panel(px, W / 2, H * 0.76, align="centre"), True
                lift = max(bounds(chosen)[3] - H * 0.93, 0)  # a tall Khmer block stays off the bottom edge
                chosen = [(t, p, x, y - lift) for t, p, x, y in chosen]

    # composing: the art (with a whisper of paper grain on the plain background), then the title through the
    # character's mask, kept clear of her by a halo of background colour ~3.5% of the font size wide, so dark hair
    # never melts into dark letters
    px = chosen[0][1]
    title = np.asarray(render(chosen, 2), dtype=np.float32) / 255
    grain = np.random.default_rng(7).normal(0, 2.2, (H, W)).astype(np.float32)
    canvas = art + (grain * (1 - person))[..., None]
    halo = max(1.5, px * 0.035)
    if front:  # over her: a background-coloured outline round the letters keeps them off the picture
        near = ndimage.distance_transform_edt(title < 0.5)
        rim = np.clip(halo * 1.6 + 0.5 - near, 0, 1)[..., None]
        canvas = canvas * (1 - rim) + paper * rim
        alpha = title
    else:
        alpha = title * (1 - np.maximum(person, np.clip(halo + 0.5 - away, 0, 1)))
    canvas = canvas * (1 - alpha[..., None]) + accent * alpha[..., None]

    # the one line of info: all caps, spaced +10%, accent at 70%, in a left corner (never bottom-right, where
    # YouTube puts the duration); the genre leads when it's short enough to sit clear of her
    try:
        song = SongScript.load(job / "song.json")
        genre = re.split(r"[,/(]| and | with ", song.genre)[0].strip().upper()
    except Exception:
        genre = ""
    info_file = "segoeuib.ttf" if font_path("segoeuib.ttf") else FONTS["en"]["Arial"]
    info_px = round(base_px * 0.034 / (_mag_sprite("H", 200, info_file, cache)["asc"] / 200))
    tbox = bounds(chosen)
    pad = H * 0.03
    x_info = x_at if layout == "panel" and not front and x_at < W / 2 else m  # under a left panel: its margin
    spots = [H - H * 0.065, mt + _mag_sprite("H", info_px, info_file, cache)["asc"]]  # bottom-left, top-left
    best = None
    for label in ([f"{genre} · LYRIC VIDEO"] if genre and len(genre) <= 18 else []) + ["LYRIC VIDEO"]:
        s = _mag_sprite(label, info_px, info_file, cache, track=0.1)
        if x_info + s["w"] > W * 0.86:  # the bottom-right ~11% stays clear for the duration badge
            continue
        for y in spots:
            box = (int(x_info), int(y - s["asc"]), int(x_info + s["w"]), int(y + s["desc"]) + 1)
            if box[0] < tbox[2] + pad and tbox[0] - pad < box[2] and box[1] < tbox[3] + pad and tbox[1] - pad < box[3]:
                continue  # on (or crowding) the title
            near = float((away[box[1]:box[3], box[0]:box[2]] < W * 0.012).mean())  # on her, or touching her
            if best is None or near < best[0] - 1e-3:
                best = (near, label, y)
        if best and best[0] < 0.005:
            break
    if best:
        _, label, y = best
        s = _mag_sprite(label, info_px, info_file, cache, track=0.1)
        layer = Image.new("L", (W * 2, H * 2), 0)
        layer.paste(255, (round(x_info * 2), round((y - s["asc"]) * 2)), s["img2"])
        a = np.asarray(layer.resize((W, H), Image.LANCZOS), dtype=np.float32)[..., None] / 255 * 0.7
        canvas = canvas * (1 - a) + accent * a
    picture = Image.fromarray(np.clip(canvas + 0.5, 0, 255).astype(np.uint8))
    for quality in (92, 88, 84, 80):  # 4:4:4 keeps the coloured letters' edges clean; YouTube takes < 2 MB
        picture.save(out, quality=quality, subsampling=0, optimize=True)
        if out.stat().st_size < 2_000_000:
            break
    return True


def make_thumbnail(job: Path, text: str, at: float, lang: str, style: str = "bold", emphasis: str = "",
                   image: str = "", design: str = "") -> Path:
    """(Re)draw job/thumbnail.jpg and remember the choices in meta.json. `image`: a project-relative photo to use
    instead of a video frame ("" = the frame at `at`). style "designed": Claude's layout; `design` names the
    suggestion it starts from (e.g. "suggest/thumb_2.svg"), otherwise the current one is kept or a new one made."""
    out = job / "thumbnail.jpg"
    photo = ROOT / image if image else None
    photo = photo if photo and photo.exists() else None
    if style == "magazine" and text.strip() and draw_magazine(job, text, lang, out):
        at = 0.0
    elif style == "designed" and text.strip():
        start = job / design if design else out.with_suffix(".svg")
        at = draw_designed(job, text, at, lang, out, emphasis, photo, start if start.exists() else None)
    else:
        style = style if style in THUMB_STYLES else "bold"
        at = draw_thumbnail(job, text, at, lang, out, style, emphasis, photo)
    meta_path = job / "meta.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else {}
    meta.update(thumb_text=text, thumb_at=round(at, 2), thumb_style=style, thumb_emphasis=emphasis,
                thumb_image=image if photo else "")
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    return out


def _cover_photo(query: str, size: tuple[int, int], used: set[str]) -> str:
    """A stock photo for a cover idea (project path), or "" when none is found or no stock key is set."""
    from .visuals import download_stock, project_path, search

    try:
        for item in search(query, "photo", per_page=6, orientation=orientation(size)):
            key = f"{item['source']}-{item['id']}"
            if key not in used:
                used.add(key)
                return project_path(download_stock(item["source"], "photo", item["id"], orientation(size)))
    except Exception as e:  # no key, offline: the idea falls back to a video frame
        print(f"  ! cover photo search for {query!r}: {type(e).__name__}: {e}")
    return ""


def suggest_thumbnails(job: Path, lang: str, count: int = 4, idea: str = "") -> tuple[list[dict], str]:
    """Render `count` cover ideas to job/suggest/ and save the list. Claude looks at the best frames and writes the
    headlines, following your `idea` for the cover when there is one; a cover whose picture isn't in the video
    gets a stock photo instead."""
    ideas, note = thumbs.suggestions(thumbnail_source(job), thumbs.brief(job), lang, count, idea)
    folder = job / "suggest"
    if folder.exists():
        shutil.rmtree(folder)
    used: set[str] = set()
    for i, cover in enumerate(ideas):
        query = cover.pop("photo_query", "")
        cover["image"] = _cover_photo(query, job_size(job), used) if query else ""
        cover["file"] = f"suggest/thumb_{i}.jpg"
        cover["at"] = round(draw_thumbnail(job, cover["text"], cover["at"], lang, job / cover["file"], cover["style"],
                                           cover["emphasis"], ROOT / cover["image"] if cover["image"] else None), 2)
    designs = [c.pop("direction", "") for c in ideas]
    if not note and any(c["text"].strip() for c in ideas):
        # Claude planned these: it also designs each one as a finished layout (in parallel); a cover whose design
        # fails keeps its classic look
        kind, about = _design_about(job)
        work = job / "work"
        jobs = [dict(photo=_photo_for_cover(job, c["at"], ROOT / c["image"] if c["image"] else None,
                                            work / f"suggest_photo_{i}.jpg"),
                     text=c["text"], emphasis=c["emphasis"], about=about, lang=lang, size=job_size(job),
                     out=job / f"suggest/designed_{i}.jpg", kind=kind, direction=d)
                for i, (c, d) in enumerate(zip(ideas, designs)) if c["text"].strip()]
        for kw, result in zip(jobs, art.make_covers(jobs)):
            if isinstance(result, Exception):
                continue
            cover = ideas[int(kw["out"].stem.split("_")[1])]
            kw["out"].with_suffix(".json").write_text(json.dumps({"text": cover["text"], "emphasis": cover["emphasis"]},
                                                                 ensure_ascii=False), encoding="utf-8")
            cover.update(style="designed", file=f"suggest/{kw['out'].name}", design=f"suggest/{kw['out'].stem}.svg")
    folder.mkdir(exist_ok=True)
    (folder / "suggestions.json").write_text(json.dumps({"items": ideas, "note": note, "idea": idea},
                                                        ensure_ascii=False, indent=2), encoding="utf-8")
    return ideas, note


# ---------- AI scene art ----------

# camera moves for pictures the director didn't plan (or picked by hand), so consecutive shots never repeat a move
MOTION_CYCLE = ["dolly_3d", "pan_left", "push_in", "orbit_3d", "pull_out", "pan_right", "rise_3d", "tilt_up"]


def art_ready(style: str, log: Callable[[str], None] = print) -> bool:
    """Can this computer draw scene art in `style`? If not, say why (the video then uses stock footage)."""
    from . import imagegen

    if style not in imagegen.STYLES:
        return False
    if sys.platform == "darwin" and platform.machine() != "arm64":
        log("      ! AI scene art needs an Apple Silicon Mac (M1 or newer); using stock footage")
        return False
    if not imagegen.installed():
        log("      ! AI scene art isn't installed (Settings → AI features → Install AI add-on); using stock footage")
        return False
    if not imagegen.gpu_name():
        log("      ! AI scene art needs an NVIDIA GPU or an Apple Silicon Mac, none found; using stock footage")
        return False
    return True


def plan_scene_art(script: VideoScript, log: Callable[[str], None] = print) -> bool:
    """Fill in a picture prompt, camera move and effects for every scene that has no chosen media and no prompt yet,
    keeping prompts you edited. All scenes are planned together so the pictures share one look. True if changed."""
    from . import director

    # an AI picture drawn without a plan (from the footage search words) is planned too, so it can be redrawn
    if not script.art_bible:
        for sc in script.scenes:
            if sc.art_prompt.strip() == sc.visual_query.strip():
                sc.art_prompt = ""
    todo = [i for i, sc in enumerate(script.scenes)
            if (not sc.media or sc.media.startswith("cache/gen/")) and not sc.art_prompt.strip()]
    if not todo:
        return False
    log("      planning the pictures (Claude)")
    bible, shots, subject = director.plan_scenes(script.title, [{"narration": sc.narration, "visual_query": sc.visual_query}
                                                                for sc in script.scenes], script.art_style, bible=script.art_bible)
    script.art_bible = script.art_bible or bible
    script.art_subject = script.art_subject or subject["subject"]
    script.art_avoid = script.art_avoid or subject["avoid"]
    for i in todo:
        sc = script.scenes[i]
        sc.art_prompt = shots[i].prompt
        sc.motion = sc.motion or shots[i].motion
        sc.effects = sc.effects or shots[i].effects
    return True


CHECK_PASS = 8  # a picture of a real subject scoring this (out of 10) is right; below, another take is drawn
MAX_TAKES = 3  # takes drawn at most per picture, keeping the best (each ~25 s on an RTX 3060)
REAL_PASS = 7  # a stock clip or photo must score this to stand in for a drawing that came out wrong
WRONG = 6  # a drawing scoring under this is the wrong animal/thing: real footage or a real photo is used instead


def _verdict(path: Path, subject: str, prompt: str = "") -> tuple[int, str]:
    """Claude's check of how well `path` (a picture, or a video: a frame from its middle) shows `subject`, kept in a
    file next to it, so the same picture is never paid for twice."""
    from . import director

    note = path.with_suffix(".check.json")
    saved = json.loads(note.read_text(encoding="utf-8")) if note.exists() else {}
    if saved.get("subject") == subject and "centre" in saved:
        return saved["score"], saved["problem"]
    image = path
    if path.suffix.lower() not in IMAGE_EXTS:
        image = path.with_suffix(".check.jpg")
        run(["ffmpeg", "-y", "-v", "error", "-ss", f"{duration(path) * 0.4:.2f}", "-i", str(path), "-frames:v", "1",
             "-vf", "scale=-2:720", str(image)])
    score, problem, centre = director.check_picture(image, subject, prompt)
    note.write_text(json.dumps({"subject": subject, "score": score, "problem": problem, "centre": centre}),
                    encoding="utf-8")
    return score, problem


def subject_focus(path: Path | None) -> tuple[float, float] | None:
    """Where the checked subject is in a picture (-1..1 grid units, for fx.render_shot's punch-ins), if known."""
    note = path.with_suffix(".check.json") if path else None
    if not note or not note.exists():
        return None
    centre = json.loads(note.read_text(encoding="utf-8")).get("centre")
    return (centre[0] * 2 - 1, centre[1] * 2 - 1) if centre else None


def real_subject_media(subject: str, used: set[str], log: Callable[[str], None] = print) -> Path | None:
    """Real footage of `subject` ("name: visible features") when the image model can't draw it: a stock clip, else
    a Wikimedia Commons photo, each checked by Claude to really show it (stock sites' searches are loose: "mantis
    shrimp" also finds a praying mantis and sushi). Skips files in `used` and adds the one it returns."""
    from . import commons
    from .visuals import download_stock, search

    name = subject.split(":")[0].strip()
    candidates = []
    try:
        candidates += [lambda it=it: download_stock(it["source"], "video", it["id"]) for it in search(name, "video", 6)[:4]]
    except Exception as e:
        log(f"      ! stock search for {name!r} failed ({type(e).__name__})")
    try:
        candidates += [lambda it=it: commons.download(it) for it in commons.search(name, 6)]
    except Exception as e:
        log(f"      ! Wikimedia Commons search for {name!r} failed ({type(e).__name__})")
    for fetch in candidates:
        try:
            path = fetch()
            if str(path) in used:
                continue
            score, problem = _verdict(path, subject)
        except Exception as e:
            log(f"      ! couldn't check a candidate ({type(e).__name__}: {str(e)[:120]})")
            continue
        if score >= REAL_PASS:
            used.add(str(path))
            log(f"      real {'photo' if path.suffix.lower() in IMAGE_EXTS else 'footage'} of {name}: {path.name} ({score}/10)")
            return path
    return None


_no_reference: set[str] = set()  # subjects with no real photo found (this run), so they aren't searched per picture


def subject_reference(subject: str, log: Callable[[str], None] = print) -> Path | None:
    """A real photo of `subject` that drawings of it copy the look of (IP-Adapter): what real_subject_media finds
    (checked by Claude), as a square around the subject. Found once per subject and kept in cache/ref."""
    from PIL import Image

    from .config import CACHE_DIR

    out = CACHE_DIR / "ref" / f"{hashlib.sha1(subject.encode()).hexdigest()[:16]}.jpg"
    if out.exists():
        return out
    if subject in _no_reference:
        return None
    media = real_subject_media(subject, set(), log)
    if not media:
        _no_reference.add(subject)
        return None
    still = media if media.suffix.lower() in IMAGE_EXTS else media.with_suffix(".check.jpg")  # _verdict's frame
    cx, cy = subject_focus(media) or (0.0, 0.0)
    with Image.open(still) as im:
        im = im.convert("RGB")
        side = min(im.size)
        left = min(max(round((cx + 1) / 2 * im.width - side / 2), 0), im.width - side)
        top = min(max(round((cy + 1) / 2 * im.height - side / 2), 0), im.height - side)
        out.parent.mkdir(parents=True, exist_ok=True)
        im.crop((left, top, left + side, top + side)).resize((512, 512), Image.LANCZOS).save(out, quality=92)
    log(f"      drawing {subject.split(':')[0].strip()} from a real photo: {media.name}")
    return out


def draw_checked(prompt: str, style: str, size: tuple[int, int], seed: int | None = None, subject: str = "",
                 avoid: str = "", log: Callable[[str], None] = print) -> tuple[Path, int, int | None, str]:
    """Draw a scene picture; when it shows the video's real `subject` ("name: visible features"), it is drawn from a
    real photo of it (subject_reference) and Claude checks it looks right; a wrong one is drawn again with another seed
    (MAX_TAKES at most, the best kept). `avoid`: what the image model must not draw instead (its negative prompt).
    Returns (picture, seed, score or None, problem)."""
    from . import director, imagegen

    seed = seed or imagegen.default_seed(prompt)
    name = subject.split(":")[0].strip().lower()
    checking = bool(name) and name.split()[-1] in prompt.lower()  # this picture shows the subject
    reference = None
    if checking:
        try:
            reference = subject_reference(subject, log)
        except Exception as e:  # no photo to go by: draw from the prompt alone
            log(f"      ! couldn't get a real photo of {name} to draw from ({type(e).__name__})")
    best: tuple[Path, int, int | None, str] | None = None
    for take in range(MAX_TAKES if checking else 1):
        s = seed if take == 0 else imagegen.default_seed(f"{prompt}\n{seed}\n{take}")
        path = imagegen.generate(prompt, style, size, seed=s, negative=avoid, reference=reference, log=log)
        if not checking:
            return path, s, None, ""
        try:
            score, problem = _verdict(path, subject, prompt)
        except Exception as e:  # no Claude: keep the picture unchecked rather than fail the video
            log(f"      ! couldn't check the picture ({type(e).__name__}); keeping it")
            return path, s, None, ""
        if best is None or score > (best[2] or 0):
            best = (path, s, score, problem)
        if score >= CHECK_PASS:
            break
        log(f"      take {take + 1}: {score}/10, {problem or 'not right'}"
            + ("; drawing another" if take + 1 < MAX_TAKES else "; keeping the best"))
    return best


# how many AI pictures a music video gets: seconds each picture stays on screen, and a cap for long songs.
# A picture takes ~40 s to draw on an RTX 3060, so "normal" on a 3-minute song is ~25 minutes of drawing.
# "cover": one character picture for the whole song on a flat pastel background, held with a slow breathing move and
# floating lights, never cut (the playlist / lyric-video look).
PICTURE_PACES = {"fewer": (8.0, 24), "normal": (4.5, 40), "more": (3.0, 60), "cover": (float("inf"), 1)}
# the model's own colour tags (a softer "pastel pink" draws as near-white), and the flat pastel each becomes
COVER_COLOURS = {"purple": (201, 182, 238), "light blue": (178, 214, 245), "orange": (250, 203, 168),
                 "aqua": (170, 228, 216), "pink": (246, 188, 212), "yellow": (250, 230, 160), "red": (240, 150, 152),
                 "blue": (160, 186, 240)}
COVER_EFFECTS = ["bokeh", "sparkles", "glow"]  # no film grain: on flat pastel it reads as noise, and costs bitrate
COVER_SHAPE = "9:16"  # a cover character is drawn portrait (head to thighs with room above), then set on a flat frame


def _background(small, target, tolerance: float = 26):
    """Which pixels of `small` (a float RGB array) are its plain background, and the background's colour on each row
    (it may be a gradient). The picture is split into smooth regions by its line art and shading edges; regions
    touching the top or sides in the background's colour are background, whatever their gradient, and so are
    regions shut in by hair or arms whose colour matches the background's at the same height."""
    import numpy as np
    from scipy import ndimage

    h, w = small.shape[:2]
    soft = ndimage.uniform_filter(small, size=(3, 3, 1))
    gy, gx = np.gradient(soft, axis=(0, 1))
    edges = np.sqrt((gx ** 2 + gy ** 2).sum(2)) > 4.5  # outlines and shading steps; a smooth gradient stays under
    regions, n = ndimage.label(~edges)
    border = np.zeros((h, w), dtype=bool)
    border[0], border[:, 0], border[:, -1] = True, True, True  # not the bottom: the body is cut off there
    ref = np.median(np.concatenate([small[0], small[:, 0], small[:, -1]]), axis=0)
    ids = np.arange(1, n + 1)
    means = np.stack([ndimage.mean(small[..., c], regions, ids) for c in range(3)], 1) if n else np.zeros((0, 3))
    touching = np.zeros(n + 1, dtype=bool)
    touching[np.unique(regions[border])] = True
    near_ref = np.linalg.norm(means - ref, axis=1) < 45
    near_target = np.linalg.norm(means - target, axis=1) < 18
    is_bg = np.zeros(n + 1, dtype=bool)
    is_bg[1:] = (touching[1:] & (near_ref | near_target)) | near_target
    bg = is_bg[regions] & ~edges
    # the background's colour on each row, for the regions it shuts in and for the soft edges' old colour
    counts = bg.sum(1)
    rows = np.where(counts > 0)[0]
    if len(rows) == 0:
        return bg, np.tile(ref, (h, 1))
    sums = (small * bg[..., None]).sum(1)
    profile = np.stack([np.interp(np.arange(h), rows, sums[rows, c] / counts[rows]) for c in range(3)], 1)
    sizes = ndimage.sum(np.ones((h, w)), regions, ids) if n else np.zeros(0)
    off = np.linalg.norm(small - profile[:, None, :], axis=2)
    match = ndimage.mean(off, regions, ids) if n else np.zeros(0)
    pocket = np.zeros(n + 1, dtype=bool)
    pocket[1:] = ~is_bg[1:] & (match < tolerance * 0.8) & (sizes >= 40)
    bg |= pocket[regions]
    # the edge pixels between background pieces belong to it, and so does the blended border round the character
    # wherever it is still mostly background colour (else it shows as a light outline)
    bg |= ndimage.binary_closing(bg, iterations=2) & (off < tolerance)
    bg |= ndimage.binary_dilation(bg, iterations=3) & (off < tolerance * 1.4)
    bg |= off < tolerance * 0.6  # specks of background between hair strands, too small to be regions
    return bg, profile


def _flatten(img, target, tolerance: float = 26, with_mask: bool = False):
    """`img` (a PIL picture) with its plain background (_background: even a gradient, and pockets shut in by hair or
    arms) turned into the flat `target` colour, blended over a soft mask so hair edges stay soft and keep no rim of
    the old colour. Pixels already near `target` count as background too (a widened picture's kept middle).
    with_mask: also return the background mask (PIL "L")."""
    import numpy as np
    from PIL import Image, ImageFilter

    small = np.asarray(img.resize((max(img.width * 512 // img.height, 1), 512)), dtype=np.float32)
    bg, profile = _background(small, target, tolerance)
    mask = Image.fromarray((bg * 255).astype(np.uint8)).resize(img.size, Image.BILINEAR)
    core = np.asarray(mask.filter(ImageFilter.GaussianBlur(1.5)), dtype=np.float32)[..., None] / 255
    rim = np.asarray(mask.filter(ImageFilter.MaxFilter(7)).filter(ImageFilter.GaussianBlur(4)),
                     dtype=np.float32)[..., None] / 255
    pic = np.asarray(img, dtype=np.float32)
    old = np.interp(np.linspace(0, len(profile) - 1, img.height), np.arange(len(profile)), profile[:, 0]),         np.interp(np.linspace(0, len(profile) - 1, img.height), np.arange(len(profile)), profile[:, 1]),         np.interp(np.linspace(0, len(profile) - 1, img.height), np.arange(len(profile)), profile[:, 2])
    old = np.stack(old, 1)[:, None, :]  # the background's own colour on each row (a gradient stays a gradient)
    # edge pixels are part old background: shift that part to the pastel (no coloured rim), then fill flat
    pic = np.clip(pic + (target - old) * rim * (1 - core), 0, 255) * (1 - core) + target * core
    flat = Image.fromarray(pic.astype(np.uint8))
    return (flat, mask) if with_mask else flat


OUTPAINT_SIZE = (1344, 768)  # the SDXL size a landscape cover is widened at (16:9 within 2%)


def _drop_strays(img, character, target, tolerance: float = 34):
    """`img` flattened (_flatten), without anything the painting added that floats free of the character (a loose
    piece of scarf, a stray blob): only shapes joined to `character` (a PIL "L" mask at any size: where it was
    before painting) are kept."""
    import numpy as np
    from PIL import Image, ImageFilter
    from scipy import ndimage

    small = np.asarray(img.resize((max(img.width * 512 // img.height, 1), 512)), dtype=np.float32)
    bg, _ = _background(small, target, tolerance)
    shapes, n = ndimage.label(~bg)
    was = np.asarray(character.resize((small.shape[1], small.shape[0]))) > 128
    joined = np.unique(shapes[was & ~bg])
    stray = (~bg) & ~np.isin(shapes, joined[joined > 0])
    if stray.any():
        m = Image.fromarray((ndimage.binary_dilation(stray, iterations=2) * 255).astype(np.uint8))
        soft = np.asarray(m.resize(img.size, Image.BILINEAR).filter(ImageFilter.GaussianBlur(2)),
                          dtype=np.float32)[..., None] / 255
        img = Image.fromarray((np.asarray(img, dtype=np.float32) * (1 - soft) + target * soft).astype(np.uint8))
    return _flatten(img, target, tolerance=tolerance)


def cover_canvas(picture: Path, size: tuple[int, int], colour: str, prompt: str = "", seed: int = 1,
                 log: Callable[[str], None] = print) -> Path:
    """The drawn cover character (portrait) as a picture of the frame's shape on a flat `colour` background, set
    in the middle with room above the head. Only what the portrait cut off is painted on by the drawing model (hair
    or a sleeve running off a side or the top continues past it); a character the portrait shows whole is simply
    placed, untouched (painting next to it invents ghost limbs and smears its outline). Made once next to it."""
    import numpy as np
    from PIL import Image, ImageDraw, ImageFilter, ImageOps

    from . import imagegen

    W, H = size
    out = picture.with_name(f"{picture.stem}-cover18-{W}x{H}-{colour.replace(' ', '_')}.png")
    if out.exists():
        return out
    target = np.array(COVER_COLOURS.get(colour, (246, 188, 212)), dtype=np.float32)
    flat, bg = _flatten(Image.open(picture).convert("RGB"), target, with_mask=True)
    fill = tuple(int(c) for c in target)
    if abs(flat.width / flat.height - W / H) < 0.05:  # a portrait frame: the picture's own shape, edge to edge
        _crisp(flat.resize((W, H), Image.LANCZOS)).save(out)
        return out
    person = np.asarray(ImageOps.invert(bg)) > 128
    cut = {"left": person[:, :4].mean() > 0.02, "right": person[:, -4:].mean() > 0.02, "top": person[:4].mean() > 0.02}
    if W > H and prompt and any(cut.values()):
        CW, CH = OUTPAINT_SIZE
        h = round(CH * 0.92)  # room above the head
        w = round(flat.width * h / flat.height)
        x0, y0 = (CW - w) // 2, CH - h
        canvas = Image.new("RGB", (CW, CH), fill)
        canvas.paste(flat.resize((w, h), Image.LANCZOS), (x0, y0))
        band = 16  # painted over the picture's edge too, so the cut-off hair or sleeve runs on smoothly
        mask = Image.new("L", (CW, CH), 0)
        draw = ImageDraw.Draw(mask)
        if cut["left"]:
            draw.rectangle((0, 0, x0 + band, CH), fill=255)
        if cut["right"]:
            draw.rectangle((x0 + w - band, 0, CW, CH), fill=255)
        if cut["top"]:
            draw.rectangle((x0, 0, x0 + w, y0 + band), fill=255)
        log("      painting on what the cover picture cuts off (" + ", ".join(k for k, v in cut.items() if v) + ")")
        whole = Image.new("L", (CW, CH), 0)  # where the character was before painting
        whole.paste(Image.fromarray((person * 255).astype(np.uint8)).resize((w, h)), (x0, y0))
        # tidied before the detail pass too: a faint seam between old and new background would become a drawn line
        wide = imagegen.outpaint(canvas, mask, prompt, "anime", seed, log=log,
                                 tidy=lambda im: _drop_strays(im, whole, target, tolerance=34))
        wide = _drop_strays(wide, whole, target, tolerance=34)
        # The painted picture is only ~1344 wide (x the hi-res pass): blown up to the frame, the character went soft.
        # So only the painted extension (past the portrait's cut edges) and the flat colour come from it; the
        # character itself is the original portrait, resized once from its own resolution to its place in the frame.
        # Scaled evenly by W/CW (1344x768 is 1.75:1, not 16:9) and cut to H, so the two line up and nothing stretches.
        s = W / CW
        tall = round(wide.height * W / wide.width)
        dy = (tall - H) // 2
        frame = wide.resize((W, tall), Image.LANCZOS).crop((0, dy, W, dy + H))
        cw, ch = round(w * s), round(h * s)
        cx, cy = round(x0 * s), round(y0 * s) - dy
        sharp = _crisp(flat.resize((cw, ch), Image.LANCZOS))
        # where the portrait's character is: a hair inside its outline (the painted continuation, drawn over the
        # outline too, meets it there rather than a light rim), then feathered so no hard edge shows
        alpha = ImageOps.invert(bg).resize((cw, ch), Image.BILINEAR).filter(ImageFilter.MinFilter(5)) \
            .filter(ImageFilter.GaussianBlur(2.5))
        # and faded out towards the cut edges over the band the painting redrew, so hair or a sleeve running off the
        # portrait's side melts into its painted continuation instead of stopping at a seam
        ramp = np.ones((ch, cw), dtype=np.float32)
        fade = max(round(band * s), 2)
        edge = np.linspace(0, 1, fade, dtype=np.float32)
        if cut["left"]:
            ramp[:, :fade] *= edge[None, :]
        if cut["right"]:
            ramp[:, -fade:] *= edge[::-1][None, :]
        if cut["top"]:
            ramp[:fade] *= edge[:, None]
        alpha = Image.fromarray((np.asarray(alpha, dtype=np.float32) * ramp).astype(np.uint8))
        frame.paste(sharp, (cx, cy), alpha)
        frame.save(out)
        return out
    # nothing cut off (or nothing to paint with): the picture on the flat colour
    h = round(H * 0.92)
    w = round(flat.width * h / flat.height)
    frame = Image.new("RGB", (W, H), fill)
    frame.paste(_crisp(flat.resize((w, h), Image.LANCZOS)), ((W - w) // 2, H - h))
    frame.save(out)
    return out


def _crisp(img):
    """`img` (just resized) with a light unsharp mask: resizing softens the line art a little, and the video's
    encoder softens it again, so the art is given back its edge once, gently (no halos on flat colour)."""
    from PIL import ImageFilter

    return img.filter(ImageFilter.UnsharpMask(radius=1.2, percent=60, threshold=2))


def title_spot(cover_png: Path, size: tuple[int, int], colour: str) -> tuple[int, int]:
    """Where the neon title's centre goes on a one-cover video (pixels in a `size` frame): in the biggest empty
    stretch of flat colour beside the character, not over its face. Landscape: the left or right third with fewer
    character pixels in the upper 60% of the frame, at ~38% of the height; the left third's top is the now-playing
    card's (~40..640 x 40..190 at 1920x1080), so a free left side gets the title below the card unless the right is
    about as free. Portrait: the empty space above the head, centred."""
    import numpy as np
    from PIL import Image

    W, H = size
    target = np.array(COVER_COLOURS.get(colour, (246, 188, 212)), dtype=np.float32)
    img = Image.open(cover_png).convert("RGB")
    small = np.asarray(img.resize((max(img.width * 270 // img.height, 1), 270)), dtype=np.float32)
    bg, _ = _background(small, target)
    person = ~bg
    h, w = person.shape
    if H > W:  # above the head: the title sits midway between the top and the head (never higher than 12%)
        rows = np.where(person[:, w // 6: w - w // 6].mean(1) > 0.02)[0]
        head = rows[0] / h if len(rows) else 0.3
        if head < 0.2:  # no room above the head (the card is up there too): low over the body, under the face;
            return W // 2, round(H * 0.8)  # the title is gone before the first sung line, so the lyrics never meet it
        return W // 2, round(H * min(max(head / 2, 0.12), 0.16))
    upper = person[: round(h * 0.6)]
    third = w // 3
    left, right = upper[:, :third].mean(), upper[:, -third:].mean()

    def centre(cols: np.ndarray, offset: int) -> int:
        """The middle of the widest run of empty columns in a third (in frame pixels)."""
        best, start, at = 0, 0, (0, len(cols) - 1)
        for i, empty in enumerate(cols < 0.03):
            if not empty:
                start = i + 1
            elif i - start + 1 > best:
                best, at = i - start + 1, (start, i)
        return round(((at[0] + at[1] + 1) / 2 + offset) * W / w)

    y = round(H * 0.38)
    if right <= left * 1.5 + 0.01:  # the right is (about) as free: it has no card in the way
        return centre(upper[:, -third:].mean(0), w - third), y
    # the left is clearly freer: below the card (it ends at ~18% of the height), clear of it
    return centre(upper[:, :third].mean(0), 0), max(y, round(H * 0.42))


# words in an idea -> the cover colour they ask for (longer phrases are matched first: "light blue" before "blue")
COLOUR_WORDS = {
    "light blue": "light blue", "sky blue": "light blue", "baby blue": "light blue", "pastel blue": "light blue",
    "lavender": "purple", "lilac": "purple", "violet": "purple", "purple": "purple", "mauve": "purple",
    "peach": "orange", "coral": "orange", "orange": "orange", "sunset": "orange", "amber": "orange",
    "teal": "aqua", "turquoise": "aqua", "mint": "aqua", "aqua": "aqua", "cyan": "aqua", "green": "aqua",
    "emerald": "aqua",
    "pink": "pink", "rose": "pink", "magenta": "pink", "sakura": "pink", "blush": "pink",
    "yellow": "yellow", "gold": "yellow", "golden": "yellow", "lemon": "yellow", "sunflower": "yellow",
    "red": "red", "crimson": "red", "scarlet": "red", "cherry": "red",
    "blue": "blue", "navy": "blue", "cobalt": "blue", "cold": "blue", "icy": "blue",
    # Khmer
    "ខៀវខ្ចី": "light blue", "ស្វាយ": "purple", "ទឹកក្រូច": "orange", "បៃតង": "aqua", "ផ្កាឈូក": "pink",
    "លឿង": "yellow", "ក្រហម": "red", "ខៀវ": "blue",
}


def colour_from_idea(idea: str) -> str:
    """The cover colour an idea names first ("rain on pink and blue neon" -> pink), or "" when it names none."""
    text = idea.lower()
    found = []
    for word in sorted(COLOUR_WORDS, key=len, reverse=True):
        for m in re.finditer(rf"(?<![\w-]){re.escape(word)}(?![\w-])" if word.isascii() else re.escape(word), text):
            if not any(a <= m.start() < b for a, b, _ in found):  # "light blue" already covers its "blue"
                found.append((m.start(), m.end(), COLOUR_WORDS[word]))
    return min(found)[2] if found else ""


def cover_colour(title: str, idea: str = "") -> str:
    """The flat pastel background of a song's cover picture: the colour your idea names, else one picked from the
    title (the same every time for the same song)."""
    return colour_from_idea(idea) or list(COVER_COLOURS)[
        int(hashlib.sha1(title.strip().lower().encode()).hexdigest(), 16) % len(COVER_COLOURS)]


# words in an idea -> the weather and light a cover video gets on top of its floating lights (and the picture shows)
ATMOSPHERES = {
    "rain": ("rain", "rainy", "monsoon", "storm", "drizzle", "downpour", "umbrella", "thunder", "wet", "ភ្លៀង"),
    "snow": ("snow", "snowy", "winter", "christmas", "frost", "ព្រិល"),
    "petals": ("sakura", "cherry blossom", "petal", "petals", "spring", "flower"),
    "embers": ("fire", "flame", "embers", "campfire", "burning"),
    "neon_glow": ("neon", "city lights", "cyberpunk", "night city", "nightclub", "arcade"),
}
ATMOSPHERE_LOOKS = {"rain": "wet hair and raindrops on her", "snow": "snowflakes in her hair",
                    "petals": "petals drifting around her", "embers": "warm firelight on her",
                    "neon_glow": "pink and blue neon light on her face"}


def atmospheres(idea: str) -> list[str]:
    """The ATMOSPHERES an idea calls for ("rain on pink neon" -> rain, neon_glow), in a fixed order."""
    text = idea.lower()
    return [k for k, words in ATMOSPHERES.items()
            if any(re.search(rf"(?<!\w){re.escape(w)}(?!\w)" if w.isascii() else re.escape(w), text)  # "neon-lit" too
                   for w in words)]


def cover_effects(idea: str) -> list[str]:
    """A cover video's effects: the floating lights, plus the idea's weather and light (rain replaces sparkles)."""
    extra = atmospheres(idea)
    base = [e for e in COVER_EFFECTS if not (e == "sparkles" and {"rain", "snow"} & set(extra))]
    return base + [e for e in extra if e not in base]


# what the song is about -> the one object that says it at a glance (first match wins: the idea, then the title,
# then the lyrics), written the way the anime model draws it reliably
COVER_PROPS = [
    (("umbrella", "rain", "monsoon", "downpour", "storm", "ភ្លៀង"), "holding clear umbrella over shoulder"),
    (("signal", "phone", "call", "text me", "no service", "connection"), "arm up, holding flip phone up to the sky"),
    (("replay", "vhs", "videotape", "rewind", "tape"), "holding videocassette near face"),
    (("cassette", "mixtape", "walkman"), "holding cassette tape near face"),
    (("radio", "frequency", "broadcast"), "holding old radio against chest with both hands"),
    (("awake", "asleep", "sleep", "bed", "pillow", "wake", "morning"), "hugging pillow, blanket over shoulders"),
    (("guitar",), "holding acoustic guitar"),
    (("headphones", "playlist", "listening"), "headphones around neck"),
    (("letter", "write to you", "words unsaid"), "holding letter against chest with both hands"),
    (("polaroid", "photo", "picture of you", "camera"), "holding polaroid photo near face"),
    (("flower", "rose", "bouquet", "sakura", "petal"), "holding flowers against chest"),
    (("coffee", "cafe", "café"), "holding coffee cup with both hands"),
    (("book", "pages", "chapter"), "holding book against chest"),
    (("star", "stars", "moon", "sky", "satellite", "galaxy"), "looking up at the sky"),
]
_HAIR_COLOURS = ("black", "brown", "blonde", "blond", "red", "orange", "auburn", "pink", "blue", "silver", "white",
                 "purple", "green", "grey", "gray")
_CLOTHES = ("hoodie", "sweater", "sundress", "dress", "t-shirt", "shirt", "jacket", "school uniform", "kimono",
            "scarf", "skirt", "jeans", "coat", "cardigan", "blouse")


def suggest_cover_prompt(song, idea: str = "", lyrics: str = "") -> str:
    """A starter prompt for a song's cover picture, without Claude: the character and outfit the idea describes,
    one object that says what the song is about (COVER_PROPS), the mood, the idea's weather, framing and the
    background colour last. Edit it in the pictures panel and redraw; Plan pictures (Claude) writes its own."""
    text = idea.lower()
    he = re.search(r"\b(he|him|his|boy|man|guy)\b", text) and not re.search(r"\b(she|her|girl|woman)\b", text)
    hair = re.search(rf"\b((?:long|short|shoulder-length|wavy|curly|straight)\s+)?({'|'.join(_HAIR_COLOURS)})\s+hair\b",
                     text)
    hair_tag = (f"{hair.group(1) or ''}{'orange' if hair.group(2) == 'auburn' else hair.group(2)} hair".strip()
                if hair else ("short black hair" if he else "long black hair"))
    clothes = [m.group(0) for m in re.finditer(rf"\b(?:[a-z-]+\s+)?(?:{'|'.join(_CLOTHES)})\b", text)][:2]
    if not clothes:
        clothes = ["oversized white hoodie"]
    prop = ""
    for source in (text, song.title.lower(), lyrics.lower()):
        prop = next((tag for words, tag in COVER_PROPS
                     if any(re.search(rf"(?<!\w){re.escape(w)}(?!\w)", source) for w in words)), "")
        if prop:
            break
    mood = song.mood.lower()
    feel = ("sad" if re.search(r"sad|melanchol|lonely|longing|yearning|heartbreak|grief", mood) else
            "wistful smile" if re.search(r"nostalgi|bittersweet|wistful", mood) else
            "gentle smile" if re.search(r"romantic|tender|love", mood) else
            "smile" if re.search(r"happy|euphoric|upbeat|joy|playful|energetic", mood) else "soft smile")
    if "pillow" in prop:
        feel = "half-closed eyes, sleepy, " + feel
    weather = {"rain": "wet hair, raindrops", "snow": "snowflakes", "petals": "cherry blossom petals",
               "neon_glow": "neon light on face"}
    extra = [weather[a] for a in atmospheres(idea) if a in weather]
    look = "looking up" if "sky" in prop or "up to the sky" in prop else "looking at viewer"
    parts = ["1boy" if he else "1girl", "solo", hair_tag, prop, *clothes, feel, *extra, look, "cowboy shot",
             "simple background", f"{cover_colour(song.title, idea)} background"]
    return ", ".join(p for p in parts if p)


def cover_scene(song, idea: str = "") -> str:
    """The direction for a song's single cover picture (director.plan_song follows it exactly): the character, one
    object that says what the song is about, an expression that fits its mood and the idea's weather, on a flat
    colour."""
    colour = cover_colour(song.title, idea)
    weather = ", ".join(ATMOSPHERE_LOOKS[a] for a in atmospheres(idea))
    return (f"COVER ART for the whole song, like a J-pop playlist cover: one anime character (the main character of "
            f"the creator's idea when it describes one, with their look, hair and outfit; otherwise one who fits the "
            f"song's mood and lyrics), cowboy shot (head to thighs, with room above the head), centred, eye level. "
            f"The picture must say what THIS song is about at a glance: give the character ONE key object from the "
            f"song or idea, held or worn (e.g. a cassette tape for a song about replaying a memory, an old radio or a "
            f"flip phone for a song about a lost signal, a clear umbrella for a rain song), saying exactly where it is "
            f"(e.g. 'holding an old radio against her chest with both hands'): never in front of the face, never "
            f"floating, and the whole face visible; and an expression and "
            f"pose that match the song's mood ({song.mood}: no smile for a sad or lonely song; hands near the face, "
            f"on the object or at the sides, never reaching at the camera)"
            + (f", with {weather}" if weather else "")
            + f". A stylish outfit with {colour} accents, on a plain flat {colour} background with nothing else in it. "
            f"Keep the prompt under 35 words. Start with 1girl or 1boy, solo, then the hair colour and style (so the "
            f"background colour can't tint the hair), then the object, and end it with: simple background, {colour} "
            f"background")


def _repeats(song) -> dict[int, int]:
    """Sections that sing (almost) the same lyrics as an earlier one, e.g. the 2nd and 3rd chorus -> the first one."""
    from difflib import SequenceMatcher

    def words(sec) -> str:
        return " ".join(re.sub(r"[^\w\s]", " ", " ".join(sec.lyrics).lower()).split())

    texts = [words(s) for s in song.sections]
    same: dict[int, int] = {}
    for i, text in enumerate(texts):
        if len(text) < 12:  # instrumental or a one-word tag: nothing to recognise
            continue
        for j in range(i):
            if j not in same and SequenceMatcher(None, texts[j], text).ratio() >= 0.8:
                same[i] = j
                break
    return same


HOME_VIDEO = (1440, 1080)  # the shape a 4:3 home-video section's pictures are drawn in


def picture_shape(slot: dict, size: tuple[int, int]) -> tuple[int, int]:
    """The shape a planned picture is drawn in: landscape for a 4:3 home video, portrait for a cover character."""
    return HOME_VIDEO if slot.get("frame") == "4:3" else frame_size(COVER_SHAPE) if slot.get("frame") == "cover" else size
ART_PLAN = "art_plan.json"  # a song's picture plan, kept in the song folder so it can be checked before a render


def song_slots(song, spans: list[tuple[float, float]], shots: list, lines: list, pace: str = "normal",
               scenes: list[str] | None = None, frames: list[str] | None = None) -> tuple[list[dict], list[int], set[int]]:
    """The pictures a music video needs: consecutive shots of a section grouped so each picture stays on screen
    ~PICTURE_PACES seconds. A section that repeats an earlier one (a chorus sung again) shows that section's pictures
    again, unless `scenes` (a directed idea, one per section) asks for something else there. `frames`: the
    directed frame per section; "4:3" slots are drawn as landscape home-video pictures.
    Returns (slots, the slot of every shot, the shots that show a repeated picture)."""
    if pace == "cover" and shots:  # one picture for every shot (the render holds it as one long shot)
        chorus = cold_open_window(song, lines, spans, spans[-1][1]) if lines else None
        sung = " / ".join(l.text for l in lines if chorus and chorus[0] <= l.start < chorus[1])
        return ([{"section": song.sections[shots[0].section].name, "lyrics": sung[:300], "start": 0.0,
                  "seconds": round(shots[-1].end, 2), "also": [], "scene": cover_scene(song), "frame": "cover"}],
                [0] * len(shots), set())
    seconds_each, cap = PICTURE_PACES.get(pace, PICTURE_PACES["normal"])
    per_section: dict[int, list[int]] = {}
    for i, shot in enumerate(shots):
        per_section.setdefault(shot.section, []).append(i)
    repeat_of = {sec: orig for sec, orig in _repeats(song).items() if sec in per_section and orig in per_section
                 and (not scenes or scenes[sec].strip().lower() == scenes[orig].strip().lower())
                 and (not frames or frames[sec] == frames[orig])}
    # (the cap counts every slot on screen, so repeats lower the number drawn even in long songs)
    want = {sec: min(len(idx), max(1, round((spans[sec][1] - spans[sec][0]) / seconds_each)))
            for sec, idx in per_section.items()}
    total = sum(want.values())
    if total > cap:
        want = {sec: max(1, round(n * cap / total)) for sec, n in want.items()}
    for sec in repeat_of:
        del want[sec]
    slots, slot_of, first_slot = [], [0] * len(shots), {}
    for sec in sorted(per_section):
        if sec in repeat_of:
            continue
        idx, n = per_section[sec], want[sec]
        first_slot[sec] = len(slots)
        for k in range(n):
            group = idx[k * len(idx) // n:(k + 1) * len(idx) // n]
            start, end = shots[group[0]].start, shots[group[-1]].end
            sung = " / ".join(l.text for l in lines if l.section == sec and l.end > start and l.start < end)
            for g in group:
                slot_of[g] = len(slots)
            slots.append({"section": song.sections[sec].name, "lyrics": sung[:300], "start": round(start, 2),
                          "seconds": round(end - start, 2), "also": [],
                          **({"scene": scenes[sec]} if scenes and scenes[sec].strip() else {}),
                          **({"frame": "4:3"} if frames and frames[sec] == "4:3" else {})})
    reused: set[int] = set()
    for sec, orig in sorted(repeat_of.items()):
        idx, n = per_section[sec], min(len(per_section[sec]), want[orig])
        name = song.sections[sec].name
        nth = sum(s.name == name for s in song.sections[:sec + 1])
        label = f"{name} #{nth}" if nth > 1 else name  # "Chorus #2"
        for k in range(n):
            slot = slots[first_slot[orig] + k]
            if label not in slot["also"]:
                slot["also"].append(label)
            for g in idx[k * len(idx) // n:(k + 1) * len(idx) // n]:
                slot_of[g] = first_slot[orig] + k
                reused.add(g)
    return slots, slot_of, reused


def _song_layout(song_dir: Path, song, lines: list, total: float, log: Callable[[str], None],
                 paces: list[str] | None = None):
    """Beats, section spans and the beat-cut shots of a song (the same every time for the same song, timing and
    `paces`: per section "slow" / "normal" / "fast" cutting, from a directed idea)."""
    from .align import section_spans, spans_from_lines
    from .beats import beat_times, plan_shots

    beats, beat_method = beat_times(song_dir / "song.mp3", song.bpm, total, log=log)
    if not song.bpm and len(beats) > 4:  # your own song: tempo from the detected beats
        gaps = sorted(b - a for a, b in zip(beats, beats[1:]))
        song.bpm = round(60 / gaps[len(gaps) // 2])
        song.save(song_dir / "song.json")
    own = _meta(song_dir).get("source") == "upload"
    spans = spans_from_lines(song, lines, total) if own else section_spans(song, total)
    return beats, beat_method, spans, plan_shots(song, spans, beats, total, paces)


def song_direction(song, direction: dict | None, idea: str) -> dict | None:
    """The shot list to follow (director.direct_idea, maybe edited): only when it was made from this idea and has a
    row for every section of the song."""
    if not isinstance(direction, dict) or len(direction.get("sections") or []) != len(song.sections):
        return None
    return direction if (direction.get("idea") or "").strip() == idea.strip() else None


def _direction_key(direction: dict | None, legacy: bool = False) -> str:
    """Changes whenever the shot list does, so a picture plan made from another one isn't reused."""
    if not direction:
        return ""
    import hashlib

    from .director import clean_section

    if legacy:  # how plans made before 2026-10-15 were keyed: the shot list as sent, so formatting counted too
        parts = [direction.get("bible", ""), direction["sections"]]
    else:  # cleaned first: the app's copy and the saved one differ in whitespace and default fields, not content
        parts = [str(direction.get("bible") or "").strip(), [clean_section(r) for r in direction["sections"]]]
    return hashlib.sha1(json.dumps(parts, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:12]


def plan_follows(plan: dict, direction: dict | None) -> bool:
    """Was the picture plan made from this shot list (or from none, when there is none)?"""
    key = plan.get("direction", "")
    return key == _direction_key(direction) or (bool(direction) and key == _direction_key(direction, legacy=True))


def load_art_plan(song_dir: Path) -> dict | None:
    try:
        return json.loads((song_dir / ART_PLAN).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def save_art_plan(song_dir: Path, plan: dict) -> None:
    (song_dir / ART_PLAN).write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")


def plan_fits(plan: dict | None, style: str, pace: str, idea: str, slots: list[dict] | None = None,
              direction: dict | None = None) -> bool:
    """Can a render use this saved plan as it is (same look, pace, idea and shot list, the same pictures needed)?"""
    if not plan or plan.get("style") != style or plan.get("pictures") != pace or plan.get("idea", "") != idea.strip():
        return False
    if not plan_follows(plan, direction):
        return False
    return slots is None or [s["section"] for s in plan.get("slots", [])] == [s["section"] for s in slots]


def _new_art_plan(song, slots: list[dict], style: str, pace: str, aspect: str, idea: str,
                  log: Callable[[str], None], bible: str = "", direction: dict | None = None) -> dict:
    """Claude's picture plan for the slots (one call); falls back to the sections' search words without Claude."""
    from . import director

    bible = bible or (direction or {}).get("bible", "")  # the shot list's characters and world
    if pace == "cover":  # the cover's colour can come from the idea, which song_slots doesn't know
        slots = [{**s, "scene": cover_scene(song, idea)} for s in slots]
    log(f"      planning {len(slots)} pictures (Claude)")
    try:
        written, plans = director.plan_song(song.title, song.mood, song.genre, slots, style, aspect, idea, bible)
        bible = bible or written  # yours, if you gave one
    except Exception as e:
        log(f"      ! couldn't plan the pictures ({type(e).__name__}: {str(e)[:120]}); drawing from the search words")
        plans = []
        for s in slots:
            sec = next(x for x in song.sections if x.name == s["section"])
            plans.append(director.ShotPlan(s.get("scene") or sec.visual_query or f"{song.mood} {song.genre}",
                                           "push_in", []))
    if pace == "cover":  # held for the whole song: the breathing move and floating lights, on a flat background
        tags = f"simple background, {cover_colour(song.title, idea)} background"
        if not bible:  # Claude couldn't plan it: the idea's character and the song's object, as tags
            lyrics = " ".join(line for sec in song.sections for line in sec.lyrics)
            plans = [director.ShotPlan(suggest_cover_prompt(song, idea, lyrics), "breathe", [])]
        plans = [director.ShotPlan(p.prompt if tags in p.prompt else f"{p.prompt.rstrip(' ,.')}, {tags}", "breathe",
                                   cover_effects(idea)) for p in plans]
    return {"style": style, "pictures": pace, "idea": idea, "aspect": aspect, "bible": bible,
            "direction": _direction_key(direction),
            "slots": [{**s, "prompt": p.prompt, "motion": p.motion, "effects": p.effects, "seed": k + 1}
                      for k, (s, p) in enumerate(zip(slots, plans))]}


def plan_song_pictures(song_dir: Path, style: str, pace: str = "normal", idea: str = "", bible: str = "",
                       log: Callable[[str], None] = print, direction: dict | None = None) -> dict:
    """Plan a music video's pictures before rendering it, so each one can be looked at, redrawn or rewritten first.
    Saved with the song; the next music video with the same look, pace and idea uses it as it is."""
    from .align import load_lines
    from .lyrics import SongScript

    song = SongScript.load(song_dir / "song.json")
    lines = load_lines(song_dir / "lyrics.json")
    if not lines:
        raise RuntimeError("Sync the lyrics first: the pictures follow what is sung when.")
    aspect = _meta(song_dir).get("aspect") or "9:16"
    direction = song_direction(song, direction, idea)
    rows = direction["sections"] if direction else None
    *_, spans, shots = _song_layout(song_dir, song, lines, duration(song_dir / "song.mp3"), log,
                                    [r["pace"] for r in rows] if rows else None)
    slots, *_ = song_slots(song, spans, shots, lines, pace, [r["scene"] for r in rows] if rows else None,
                           [r.get("frame", "full") for r in rows] if rows else None)
    plan = _new_art_plan(song, slots, style, pace, aspect, idea.strip(), log, bible.strip(), direction)
    save_art_plan(song_dir, plan)
    return plan


def song_art(song_dir: Path, song, spans: list[tuple[float, float]], shots: list, lines: list, style: str,
             aspect: str, idea: str, size: tuple[int, int], workdir: Path, log: Callable[[str], None] = print,
             pace: str = "normal", direction: dict | None = None) -> list[tuple[Path, "object"]]:
    """One AI picture per few shots of each section, prompted from the lyrics sung over them: the song's saved plan
    (checked and edited before the render) when it fits, else a new one from Claude, saved with the song.
    Returns (picture, director's ShotPlan) per shot; shots in a slot share its picture with different moves."""
    from dataclasses import replace

    from . import director, imagegen

    scenes = [r["scene"] for r in direction["sections"]] if direction else None
    frames = [r.get("frame", "full") for r in direction["sections"]] if direction else None
    slots, slot_of, reused = song_slots(song, spans, shots, lines, pace, scenes, frames)
    plan = load_art_plan(song_dir)
    if plan_fits(plan, style, pace, idea, slots, direction):
        log(f"      using your planned pictures ({len(slots)})")
    else:
        plan = _new_art_plan(song, slots, style, pace, aspect, idea, log, direction=direction)
        save_art_plan(song_dir, plan)
    if reused:
        log(f"      repeated sections show their pictures again ({len(reused)} shots)")
    (workdir / "art.json").write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
    plans, pictures = [], []
    report = progress_reporter(log)
    for k, s in enumerate(plan["slots"]):
        seed = s.get("seed") or k + 1
        plans.append(director.ShotPlan(s["prompt"], s.get("motion") or "push_in", s.get("effects") or []))
        shape = picture_shape(s, size)
        done = imagegen.drawn(s["prompt"], style, shape, seed)
        log(f"      drawing picture {k + 1}/{len(plan['slots'])}" + (" (already drawn)" if done else ""))
        report(k / len(plan["slots"]), f"Picture {k + 1} of {len(plan['slots'])}" + (" (already drawn)" if done else ""))
        pictures.append(imagegen.generate(s["prompt"], style, shape, seed=seed, log=log))

    def plan_for(i: int):
        shot_plan = plans[slot_of[i]]
        if i not in reused:
            return shot_plan
        # the same picture as before, but not the same shot: another camera move
        moves = [m for m in MOTION_CYCLE if m != shot_plan.motion]
        return replace(shot_plan, motion=moves[(slot_of[i] + 3) % len(moves)])

    return [(pictures[slot_of[i]], plan_for(i)) for i in range(len(shots))]


def release_gpu() -> None:
    """Free the image and depth models after a job, so lyric timing and the next job have the GPU."""
    try:
        from . import imagegen

        imagegen.unload()
        fx.release_depth()
    except Exception:
        pass


def make_song(topic: str | None = None, *, song: "SongScript | None" = None, song_path: Path | None = None,
              lang: str = "en", seconds: int = 45, style: str = "", vocal: str = "",
              backend: str = "elevenlabs", stems: bool = True, script_only: bool = False,
              log: Callable[[str], None] = print) -> Path:
    """Topic (or song.json) in -> job folder with song.json, song.mp3 and optional vocal/instrumental stems."""
    from .lyrics import SongScript, generate_song
    from .song import get_backend

    if song:
        log(f"[1/3] Using edited song: {song.title}")
    elif song_path:
        song = SongScript.load(song_path)
        log(f"[1/3] Loaded song: {song.title}")
    else:
        log(f"[1/3] Writing song with Claude: {topic!r} ({LANGS[lang].name}, {seconds}s)")
        song = generate_song(topic, lang=lang, seconds=seconds, style=style, vocal=vocal)
        log(f"      -> {song.title} ({song.genre}, {song.bpm} bpm, {len(song.sections)} sections, {song.seconds}s)")

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    job = OUTPUT_DIR / f"{stamp}-{lang}-song-{slugify(topic or song.title)}"
    job.mkdir(parents=True)
    song.save(job / "song.json")
    meta = {"kind": "song", "lang": lang, "topic": topic or "", "backend": backend,
            "created": datetime.now().isoformat(timespec="seconds")}
    (job / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    if script_only:
        log(f"Song saved: {job / 'song.json'}")
        return job / "song.json"

    log(f"[2/3] Composing with {backend}" + (" + stem separation" if stems else ""))
    result = get_backend(backend).generate(song, job, stems=stems)
    meta.update(song_id=result.song_id, duration=round(duration(result.mix), 2),
                vocals=result.vocals.relative_to(job).as_posix() if result.vocals else "",
                instrumental=result.instrumental.relative_to(job).as_posix() if result.instrumental else "",
                timestamps=result.timestamps.relative_to(job).as_posix() if result.timestamps else "")
    (job / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    log("      the song came with its own word timings" if result.timestamps
        else "      no word timings came with the song; the lyrics will be timed by listening")
    # time the lyrics now, so the timing editor and every music video start from the same timing
    try:
        sync_lyrics(job, log=log, step="[3/3]")
    except Exception as e:  # the song itself is fine; timing can be redone from the editor
        log(f"      ! lyric timing failed ({e.__class__.__name__}: {e}); sync again from the timing editor")
    log(f"Done: {result.mix}  ({meta['duration']:.1f}s)")
    return result.mix


AUDIO_EXTS = {".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg", ".opus"}


def import_song(audio: Path, title: str, lyrics: str, lang: str = "en", aspect: str = "16:9",
                log: Callable[[str], None] = print) -> Path:
    """Your own finished song (audio file + lyrics) -> a song job folder ready for lyric sync and a music video."""
    from .lyrics import own_song

    log("[1/2] Reading your lyrics")
    song = own_song(title, lyrics, lang, log=log)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    job = OUTPUT_DIR / f"{stamp}-{lang}-song-{slugify(song.title)}"
    job.mkdir(parents=True)
    mix = job / "song.mp3"
    if audio.suffix.lower() == ".mp3":
        shutil.copy(audio, mix)
    else:
        run(["ffmpeg", "-y", "-hide_banner", "-i", str(audio), "-vn", "-c:a", "libmp3lame", "-q:a", "2", str(mix)])
    song.save(job / "song.json")
    _save_meta(job, {"kind": "song", "source": "upload", "lang": lang, "aspect": aspect if aspect in ("9:16", "16:9")
                     else "16:9", "duration": round(duration(mix), 2), "created": datetime.now().isoformat(timespec="seconds")})
    log(f"      -> {song.title}: {len(song.sections)} sections, {duration(mix):.0f}s of audio")
    return job


def _time_song(song_dir: Path, song, meta: dict, total: float, log: Callable[[str], None]) -> tuple[list, str]:
    """Time the song's lyrics with the best source it has: the generator's own word timings (composed songs),
    else Whisper on the vocals stem, else Whisper on the mix with the music stripped (your own songs)."""
    from .align import align_lyrics, load_timestamps

    vocals = song_dir / meta["vocals"] if meta.get("vocals") and (song_dir / meta["vocals"]).exists() else None
    known = load_timestamps(song_dir / (meta.get("timestamps") or "timestamps.json"))
    source = "the song's word timings" if known else "vocals stem" if vocals else "your song"
    log(f"      timing from {source}")
    return align_lyrics(vocals or song_dir / "song.mp3", song, meta.get("lang", "en"), total, log=log,
                        isolate_vocals=vocals is None, known=known)


def sync_lyrics(job: Path, log: Callable[[str], None] = print, step: str = "[2/2]") -> list:
    """Time every lyric line against the song and save it to lyrics.json, where it can be corrected by hand."""
    from .align import save_lines
    from .lyrics import SongScript, move_notes

    song = SongScript.load(job / "song.json")
    meta = _meta(job)
    if move_notes(song):  # sound directions pasted among the lyrics are never sung, so they'd throw the timing off
        song.save(job / "song.json")
        log("      moved sound directions like (drums drop out) out of the lyrics")
    log(f"{step} Lyric timing")
    lines, timing = _time_song(job, song, meta, duration(job / "song.mp3"), log)
    save_lines(lines, job / "lyrics.json")
    meta.update(timing=timing)
    _save_meta(job, meta)
    log(f"      -> {len(lines)} lines timed ({timing})")
    return lines


TITLE_INTRO = (0.6, 5.5)  # when the neon song title flickers on and fades (the "cold open" option)
COLD_OPEN_SECONDS = (3.5, 5.5, 8.0)  # a chorus excerpt's shortest, ideal and longest length


def cold_open_window(song, lines: list, spans: list[tuple[float, float]], total: float) -> tuple[float, float] | None:
    """(start, end) in the song of a few seconds of its chorus (a cover picture's lyrics): the first chorus (else the
    first section sung again), from just before its first line to the end of the line that ends nearest ~5.5 s in.
    None without a chorus."""
    names = [s.name.lower() for s in song.sections]
    chorus = next((i for i, n in enumerate(names) if any(w in n for w in ("chorus", "hook", "refrain"))
                   and "pre" not in n), None)
    if chorus is None:
        chorus = min(_repeats(song).values(), default=None)
    sung = [l for l in lines if l.section == chorus] if chorus is not None else []
    if not sung:
        return None
    start = max(spans[chorus][0], sung[0].start - 0.3)
    shortest, ideal, longest = COLD_OPEN_SECONDS
    ends = [l.end for l in sung if shortest <= l.end - start <= longest]
    end = (min(ends, key=lambda e: abs(e - start - ideal)) if ends else start + ideal) + 0.25
    return (start, min(end, total)) if min(end, total) - start >= shortest else None


def _hex_brightness(colour: str) -> float:
    """0..1: how light a #RRGGBB colour is (a white "neon" glows like nothing)."""
    c = colour.lstrip("#")
    return min(int(c[i:i + 2], 16) for i in (0, 2, 4)) / 255 if len(c) == 6 else 1.0


def neon_title(title: str) -> str:
    """The song's name from a post title: "Signal Lost - Song About ... (Official Lyric Video)" -> "Signal Lost"."""
    name = re.split(r"\s[-–—|:]\s|\s*[(\[]", title, maxsplit=1)[0].strip()
    return name or title.strip()


def _clock(seconds: float) -> str:
    return f"{int(seconds // 60)}:{int(seconds % 60):02d}"


def progress_reporter(log: Callable[[str], None]):
    """A function (fraction 0..1, what is happening) that sends live progress through `log` as "@progress" lines,
    which the app shows as a bar under the current step (and leaves out of the log). At most one per whole percent."""
    last = [-1, ""]

    def report(fraction: float, detail: str = "") -> None:
        pct = int(max(0.0, min(fraction, 1.0)) * 100)
        if pct != last[0] or detail != last[1]:
            last[:] = [pct, detail]
            log(f"@progress {max(0.0, min(fraction, 1.0)):.3f} {detail}")
    return report


def make_music_video(song_dir: Path, log: Callable[[str], None] = print, idea: str = "", look: str = "",
                     lyric_style: "dict | None" = None, art_style: str | None = None,
                     pictures: str | None = None, direction: dict | None = None,
                     cold_open: bool | None = None, now_playing: bool | None = None) -> Path:
    """Song folder in -> a NEW video folder next to it: beat-cut footage per section, karaoke lyrics, the song as audio.

    The song folder works like a draft: its lyrics and timing stay editable, and every render is a separate version
    whose meta.json "song" points back to it. `idea`: your own idea for the video; the footage follows it (this
    version only, the song keeps its own searches). `look`: colour grade for the footage (styles.LOOKS);
    `lyric_style`: how the lyrics are drawn (styles.LyricStyle fields). `art_style`: "" = stock footage, else an
    imagegen.STYLES look drawn on this computer (None = the song's last choice). `pictures`: how many of them
    (PICTURE_PACES: "fewer", "normal", "more"; None = the song's last choice). `cold_open`: the song's name flickers on
    in neon over its first seconds, until the singing starts (None = the song's last choice). `now_playing`: a now-playing card in the top-left corner (title, progress bar, a
    spinning record; None = the song's last choice). Idea, look and styles are remembered on the song for the next version. Returns the new
    video.mp4.
    """
    from .align import load_lines, save_lines
    from .captions import build_karaoke_ass
    from .lyrics import SongScript, idea_queries
    from .styles import FONTS, LOOKS, LyricStyle

    song = SongScript.load(song_dir / "song.json")
    song_meta = _meta(song_dir)
    lang = song_meta.get("lang", "en")
    idea = idea.strip()
    look = look if look in LOOKS else song_meta.get("look") or "natural"
    style = LyricStyle.model_validate(lyric_style or song_meta.get("lyric_style") or {}).clean(lang)
    art_style = song_meta.get("art_style", "") if art_style is None else art_style
    pictures = pictures if pictures in PICTURE_PACES else song_meta.get("pictures") or "normal"
    cold_open = bool(song_meta.get("cold_open")) if cold_open is None else cold_open
    now_playing = bool(song_meta.get("now_playing")) if now_playing is None else now_playing
    # the shot list made from this idea (director.direct_idea, maybe edited); None = the song's, if it fits the idea
    direction = song_direction(song, song_meta.get("direction") if direction is None else direction, idea)
    remembered = {"idea": idea, "look": look, "lyric_style": style.model_dump(), "art_style": art_style,
                  "pictures": pictures, "cold_open": cold_open, "now_playing": now_playing, **({"direction": direction} if direction else {})}
    if any(song_meta.get(k) != v for k, v in remembered.items()):  # remembered for the next version
        song_meta.update(remembered)
        _save_meta(song_dir, song_meta)
    profile = LANGS.get(lang, LANGS["en"])
    aspect = song_meta.get("aspect") or "9:16"
    size = frame_size(aspect)
    own = song_meta.get("source") == "upload"
    mix = song_dir / "song.mp3"
    if not mix.exists():
        raise RuntimeError("This song hasn't been composed yet.")
    total = duration(mix)
    job = OUTPUT_DIR / f"{datetime.now():%Y%m%d-%H%M%S}-{lang}-mv-{slugify(song.title)}"
    work = job / "work"
    work.mkdir(parents=True)
    _save_meta(job, {"kind": "music_video", "song": song_dir.name, "lang": lang, "aspect": aspect, "idea": idea,
                     "look": look, "lyric_style": style.model_dump(), "art_style": art_style, "pictures": pictures, "duration": round(total, 2), "created": datetime.now().isoformat(timespec="seconds")})

    # 1. When each word is sung: the saved (hand-checked) timing if there is one, else align now
    #    (isolated vocals align far better than the full mix) and keep it with the song for editing
    saved = load_lines(song_dir / "lyrics.json")
    if saved:
        lines, timing = saved, song_meta.get("timing") or "saved"
        log("[1/4] Lyric timing (your saved timing)")
    else:
        log("[1/4] Lyric timing")
        lines, timing = _time_song(song_dir, song, song_meta, total, log)
        save_lines(lines, song_dir / "lyrics.json")
        _save_meta(song_dir, {**song_meta, "timing": timing})
    save_lines(lines, job / "lyrics.json")  # the timing this version was made with
    log(f"      -> {len(lines)} lines timed ({timing})")

    # 2. Cuts on the beat, footage per section; one clip can cover several shots of its section
    drawn = art_style if art_style and art_ready(art_style, log) else ""
    log(f"[2/4] Beats and {'pictures' if drawn else 'footage'} ({LOOKS[look]['label'].lower()} look)")
    if direction:
        log("      following your shot list: " + ", ".join(f"{s.name} {r['pace']}"
                                                         for s, r in zip(song.sections, direction["sections"])))
    beats, beat_method, spans, shots = _song_layout(song_dir, song, lines, total, log,
                                                    [r["pace"] for r in direction["sections"]] if direction else None)
    if idea and not drawn:  # (the picture plan follows the idea itself)
        log(f"      planning footage for your idea: {idea[:80]}")
        shot_list = "\n".join(f"{s.name}: {r['scene']}" for s, r in zip(song.sections, direction["sections"])) \
            if direction else ""
        for section, query in zip(song.sections, idea_queries(song, lang, (idea + "\n\nShot list:\n" + shot_list)
                                                              if shot_list else idea, log=log)):
            section.visual_query = query
    song.save(job / "song.json")  # this version's searches; the song folder keeps its own
    log(f"      -> {len(shots)} shots ({beat_method})")
    shot_art = (song_art(song_dir, song, spans, shots, lines, drawn, aspect, idea, size, work, log, pictures, direction)
                if drawn else None)
    picker = FootagePicker(orientation(size))
    per_section: dict[int, list[list]] = {}  # section -> [[clip, seconds used], ...]
    shown: dict[int, int] = {}  # section -> shots so far
    exhausted: set[int] = set()  # sections whose search has no new clips left
    clips = []
    report = progress_reporter(log)  # live progress for the app's bar
    held = bool(shot_art) and pictures == "cover"
    if held:  # one picture held for the whole song: no cuts, no beat punches
        picture, plan = shot_art[0]
        seed = (json.loads((work / "art.json").read_text(encoding="utf-8"))["slots"][0].get("seed") or 1)
        report(0.0, "Setting the cover on the frame")
        picture = cover_canvas(picture, size, cover_colour(song.title, idea), plan.prompt, seed, log)
        shutil.copy(picture, work / COVER_FRAME)  # for the magazine thumbnail
        log(f"      holding one picture for the whole song ({total:.0f}s)")
        clip = work / "shot_00.mp4"
        fx.render_shot(picture, total, clip, size=size, motion="breathe", effects=cover_effects(idea),
                       look=look, seed=7, progress=lambda f: report(f, f"Rendering the cover {_clock(f * total)} / "
                                                                       f"{_clock(total)}"))
        clips.append(clip)
    for i, shot in enumerate([] if held else shots):
        report(i / max(len(shots), 1), f"Shot {i + 1} of {len(shots)}")
        if shot_art:
            picture, plan = shot_art[i]
            first = i == 0 or shot_art[i - 1][0] != picture
            chorus = any(w in song.sections[shot.section].name.lower() for w in ("chorus", "hook", "drop"))
            section_start = i == 0 or shots[i - 1].section != shot.section
            # the picture's planned move on its first shot, other moves when it comes back; zoom punches on every
            # beat in choruses, a flash where a new section starts
            move = plan.motion if first else MOTION_CYCLE[(i + len(MOTION_CYCLE) // 2) % len(MOTION_CYCLE)]
            row = direction["sections"][shot.section] if direction else {}
            tape = row.get("tape", "")
            hits = [b - shot.start for b in beats if shot.start <= b < shot.end] if chorus or tape == "rewind"                 else ([0.0] if section_start else [])
            effects = [*fx.default_effects(drawn, music=True), *plan.effects]
            if not section_start:
                effects = [e for e in effects if e != "flash"]
            elif i > 0:
                effects.append("flash")
            clip = work / f"shot_{i:02d}.mp4"
            fx.render_shot(picture, shot.length, clip, size=size, motion=move, effects=effects, beats=hits, look=look,
                           seed=i, tape=tape, wear=row.get("wear", 0.0), frame=row.get("frame", "full"),
                           stamp=row.get("stamp", ""), fade=bool(row.get("fade")))
            clips.append(clip)
            continue
        section = song.sections[shot.section]
        pool = per_section.setdefault(shot.section, [])
        # different clips per section: 3, or one per ~10 s in long sections (full-length songs), then cycle
        start_s, end_s = spans[shot.section]
        wanted = min(8, max(3, round((end_s - start_s) / 10)))
        if len(pool) < wanted and shot.section not in exhausted:
            query = section.visual_query or f"{song.mood} {song.genre}"
            footage = picker.pick(query)
            if footage or not pool:
                if not footage and not pool:  # nothing found: Claude draws this section, then borrow a clip
                    footage = art.try_background(f"{query}\nA {song.mood} {song.genre} song, {section.name}: "
                                                 + " / ".join(section.lyrics[:4]), size, log)
                if not footage:
                    footage = next((e[0] for p in per_section.values() for e in p if e[0]), None)
                pool.append([footage, 0.0])
                log(f"      {section.name}: {query!r} -> {footage.name if footage else 'gradient'}")
            if not footage:
                exhausted.add(shot.section)
        n = shown.get(shot.section, 0)
        shown[shot.section] = n + 1
        entry = pool[n % len(pool)]
        footage, used = entry
        start = 0.0
        if footage and footage.suffix.lower() not in IMAGE_EXTS:
            length = duration(footage)
            start = used % length if length > shot.length + 0.5 else 0.0
        entry[1] = used + shot.length
        clip = work / f"shot_{i:02d}.mp4"
        # a slow camera drift on video clips, alternating direction, so the cuts feel like one moving camera
        drift = 0 if not footage or footage.suffix.lower() in IMAGE_EXTS else (1 if i % 2 else -1)
        render_scene(footage, None, shot.length, clip, start=start, size=size, look=look, drift=drift)
        clips.append(clip)
    release_gpu()
    concat(clips, work, "joined.mp4")
    title = None
    if cold_open:  # the song's name in neon over the opening, gone before the first sung line
        first = min((l.start for l in lines), default=TITLE_INTRO[1])
        end = min(TITLE_INTRO[1], max(TITLE_INTRO[0] + 2.0, first - 0.3))
        # the lyrics' sung-word colour, unless that's white: then a neon that stands out on the cover's colour
        cool = held and cover_colour(song.title, idea) in ("light blue", "blue", "aqua", "yellow", "orange")
        neon = style.highlight if _hex_brightness(style.highlight) < 0.9 else ("#FF4FD8" if cool else "#5CF2FF")
        title = (neon_title(song.title), TITLE_INTRO[0], end, neon)
        log(f"      the title in neon until {end:.1f}s")
    # on a held cover, the title goes in the empty colour beside the character (not across its face)
    title_at = title_spot(work / COVER_FRAME, size, cover_colour(song.title, idea)) if title and held else None

    # 3. Karaoke captions
    log("[3/4] Captions")
    card = None
    if now_playing:  # over the whole song
        start = 0.0
        accent = "#%02X%02X%02X" % COVER_COLOURS[cover_colour(song.title, idea)] if held else style.highlight
        card = {"title": neon_title(song.title), "label": "Now playing", "start": start, "length": total,
                "accent": accent}
    hot = {w for w in (_bare_word(t) for t in neon_title(song.title).split()) if len(w) > 2}  # glitch hits these
    (work / "captions.ass").write_text(build_karaoke_ass(lines, profile, size=size, style=style, title=title,
                                                         now_playing=card, glitch_words=hot, title_at=title_at),
                                       encoding="utf-8")
    _install_font(profile, work / "fonts", FONTS.get(lang, FONTS["en"]).get(style.font, ""))

    # 4. Final render with the song as the soundtrack + cover + post text
    log("[4/4] Final render")
    final = job / "video.mp4"
    report(0.0, "Mixing the sound")
    # drawn pictures: x264 tuned for flat colour and line art; a 1080p landscape video goes up as 1440p (lanczos,
    # before the lyrics are burnt in so they stay sharp), which YouTube serves in VP9 at a far higher bitrate
    finalize(work, "joined.mp4", "captions.ass", final, None, soundtrack=mix, fade_out=2.0,
             progress=lambda f: report(f, f"Encoding the video {_clock(f * total)} / {_clock(total)}"),
             animation=bool(drawn), out_size=(2560, 1440) if size == (1920, 1080) else None)
    try:
        cover_at = thumbs.best_frames(work / "joined.mp4", 1)[0]
    except Exception:
        cover_at = min(1.0, total / 2)
    hook = next((l.text for l in lines), "")
    if held:  # the song's name in huge letters behind the character
        make_thumbnail(job, neon_title(song.title), cover_at, lang, style="magazine")
    else:
        make_thumbnail(job, song.title, cover_at, lang)
    tags = " ".join(f"#{h}" for h in song.hashtags)
    credit = "" if own else "\nMusic and vocals are AI-generated.\n"
    (job / "post.txt").write_text(f"{song.title}\n\n{song.caption}\n\n{tags}\n{credit}", encoding="utf-8")
    _save_meta(job, {**_meta(job), "timing": timing, "beats": beat_method, "shots": len(shots), "hook": hook,
                     "cold_open": bool(title), "duration": round(total, 2)})
    log(f"Done: {final}  ({total:.1f}s)")
    return final


# what a music video render keeps in its own folder (older versions rendered into the song folder itself)
_RENDER_FILES = ("video.mp4", "thumbnail.jpg", "post.txt", "work", "suggest")
_RENDER_META = ("timing", "beats", "shots", "hook", "thumb_text", "thumb_at", "thumb_style", "thumb_emphasis")


def split_song_renders(output_dir: Path = OUTPUT_DIR) -> list[str]:
    """Move music videos that were rendered inside their song folder into a version folder of their own, so the
    song can stay a draft. Returns the new folder names. Safe to run on every start."""
    moved = []
    for folder in sorted(output_dir.iterdir()):
        meta = _meta(folder) if folder.is_dir() else {}
        if meta.get("kind") != "song" or not (folder / "video.mp4").exists():
            continue
        target = output_dir / folder.name.replace("-song-", "-mv-", 1)
        if target == folder or target.exists():
            target = output_dir / f"{folder.name}-mv"
        target.mkdir()
        for name in _RENDER_FILES:
            if (folder / name).exists():
                shutil.move(str(folder / name), str(target / name))
        for name in ("song.json", "lyrics.json"):
            if (folder / name).exists():
                shutil.copy(folder / name, target / name)
        created = datetime.fromtimestamp((target / "video.mp4").stat().st_mtime).isoformat(timespec="seconds")
        _save_meta(target, {"kind": "music_video", "song": folder.name, "lang": meta.get("lang", "en"),
                            "aspect": meta.get("aspect") or "9:16", "duration": meta.get("duration", 0),
                            "created": created, **{k: meta[k] for k in _RENDER_META if k in meta}})
        _save_meta(folder, {k: v for k, v in meta.items() if k not in _RENDER_META or k == "timing"})
        moved.append(target.name)
    return moved


def song_versions(song_dir: Path, output_dir: Path = OUTPUT_DIR) -> list[Path]:
    """Video folders rendered from this song, newest first."""
    found = [f for f in output_dir.iterdir() if f.is_dir() and f != song_dir and _meta(f).get("song") == song_dir.name]
    return sorted(found, key=lambda f: _meta(f).get("created", ""), reverse=True)


def make_video(topic: str | None = None, *, script_path: Path | None = None, lang: str = "en",
               voice: str | None = None, scenes: int = 6, seconds: int = 45, style: str = "",
               music: str | None = None, rate: str = "+5%", script_only: bool = False,
               script: VideoScript | None = None, log: Callable[[str], None] = print) -> Path:
    profile = LANGS[lang]
    voice = voice or profile.voices[0]

    # 1. Script
    if script:
        log(f"[1/5] Using edited script: {script.title}")
    elif script_path:
        script = VideoScript.load(script_path)
        log(f"[1/5] Loaded script: {script.title}")
    else:
        log(f"[1/5] Writing script with Claude: {topic!r} ({profile.name})")
        script = generate_script(topic, lang=lang, scenes=scenes, seconds=seconds, style=style)
        log(f"      -> {script.title} ({len(script.scenes)} scenes)")

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    job = OUTPUT_DIR / f"{stamp}-{lang}-{slugify(topic or script.title)}"
    work = job / "work"
    work.mkdir(parents=True)
    script.save(job / "script.json")
    (job / "meta.json").write_text(json.dumps(
        {"lang": lang, "voice": voice, "topic": topic or "", "created": datetime.now().isoformat(timespec="seconds")},
        ensure_ascii=False, indent=2), encoding="utf-8")
    if script_only:
        log(f"Script saved: {job / 'script.json'}")
        return job / "script.json"

    # 2. Voiceover per scene (per-scene audio keeps visuals and narration aligned)
    log(f"[2/5] Voiceover ({voice})")
    timed = []
    for i, scene in enumerate(script.scenes):
        if not scene.narration.strip():  # silent beat (sound cue): no voice, fixed length
            timed.append((None, [], scene.seconds or 3.0))
            continue
        # the same cached audio the transcript editor played, with the pauses cut there removed
        cached, words = voiceover.scene_voice(scene.narration, voice, rate)
        mp3 = work / f"voice_{i:02d}.mp3"
        shutil.copy(cached, mp3)
        if scene.cuts and scene.cuts_key == voiceover.voice_key(scene.narration, voice, rate):
            mp3, words = voiceover.apply_cuts(mp3, words, scene.cuts, work / f"voice_{i:02d}_cut.wav")
        timed.append((mp3, voiceover.with_emoji(scene.narration, words), duration(mp3) + SCENE_PAD_SEC))

    # 3. Footage (or AI pictures) + scene clips
    art_style = script.art_style if script.art_style and art_ready(script.art_style, log) else ""
    log("[3/5] " + (f"Scene pictures ({art_style}) and clips" if art_style else "Footage and scene clips"))
    picker = FootagePicker()
    if art_style:
        try:
            if plan_scene_art(script, log):
                script.save(job / "script.json")
        except Exception as e:  # no Claude: draw from the search words instead
            log(f"      ! couldn't plan the pictures ({type(e).__name__}: {str(e)[:120]}); drawing from the search words")
    # every scene's own clip first, then the second clips of split scenes: the live preview picks in this order too
    picked: list[Path | None] = []
    if art_style and not script.art_subject.strip():  # planned before subjects were: name it now (once, saved)
        try:
            from . import director

            found = director.find_subject(script.title, script.narration)
            script.art_subject, script.art_avoid = found["subject"], script.art_avoid or found["avoid"]
            if script.art_subject:
                log(f"      real subject: {script.art_subject.split(':')[0]}")
        except Exception as e:
            log(f"      ! couldn't name the video's subject ({type(e).__name__}); pictures aren't checked")
    subject = script.art_subject.strip() if art_style else ""
    name = subject.split(":")[0].strip()
    real_used: set[str] = set()

    def wrong(picture: Path, prompt: str) -> bool:
        """An AI picture meant to show the real subject that doesn't (Claude's check, cached with the picture)."""
        if not name or name.split()[-1].lower() not in prompt.lower():
            return False
        try:
            return _verdict(picture, subject, prompt)[0] < WRONG
        except Exception:
            return False

    for i, scene in enumerate(script.scenes):
        chosen = (ROOT / scene.media) if scene.media else None
        prompt = scene.art_prompt or scene.visual_query
        if chosen and chosen.exists():
            footage = chosen
            log(f"      scene {i + 1}: your pick -> {footage.name}")
            # your pick is what you saw in the preview, so it's never swapped; a drawing that shows the wrong animal
            # is flagged in the editor (with "Use a real photo"), and noted here
            if chosen.parent.name == "gen" and wrong(chosen, prompt):
                log(f"      ! scene {i + 1}: the picture doesn't look like a {name}; kept as you chose it "
                    "(use 'Use a real photo' in the editor to change it)")
        else:
            if chosen:
                log(f"      scene {i + 1}: chosen file {scene.media} is missing, picking automatically")
            footage = None
            if art_style:
                try:
                    log(f"      scene {i + 1}/{len(script.scenes)}: drawing")
                    footage, scene.art_seed, score, _ = draw_checked(
                        prompt, art_style, frame_size(None), seed=scene.art_seed or None,
                        subject=subject, avoid=script.art_avoid, log=log)
                    if score is not None:
                        log(f"      scene {i + 1}: {name} check {score}/10")
                    if score is not None and score < WRONG:  # the image model can't draw it: the real thing
                        footage = real_subject_media(subject, real_used, log) or footage
                except Exception as e:
                    log(f"      ! scene {i + 1}: couldn't draw it ({type(e).__name__}: {str(e)[:120]}); using stock")
            if not footage:  # the opening scene is the frame people see in the feed: the brightest, liveliest clip
                footage = picker.pick(scene.visual_query, hook=i == 0)
            if not footage:  # no stock clip: Claude draws the scene instead of a plain gradient
                footage = art.try_background(f"{scene.visual_query}\n{scene.narration}", frame_size(None), log)
            log(f"      scene {i + 1}: {scene.visual_query!r} -> {footage.name if footage else 'gradient'}")
        picked.append(footage)
    if art_style:
        script.save(job / "script.json")  # the takes kept (their seeds), so a re-render draws the same pictures
    second = {i: _existing(scene.media2) or picker.pick(scene.visual_query)
              for i, scene in enumerate(script.scenes) if scene.layout == "split"}
    base_fx = fx.default_effects(art_style, music=False) if art_style else ["vignette"]
    clips, hits, scene_at = [], [], 0.0
    for i, (scene, (mp3, words, length)) in enumerate(zip(script.scenes, timed)):
        broll = [(path, b.at, b.duration) for b in scene.broll
                 if (path := _existing(b.media)) and b.duration > 0 and b.at < length]
        clip = work / f"scene_{i:02d}.mp4"
        still = picked[i] is not None and picked[i].suffix.lower() in IMAGE_EXTS
        # pacing: a hit on the punchy words (and always one in the hook, within its first 2 s), and cuts to new
        # framings so a picture never sits unchanged for more than ~2 s (moving footage needs fewer)
        impacts = pacing.impacts(words, scene.impacts, length, hook=i == 0)
        cuts = pacing.cuts(length, impacts, pacing.CUT_EVERY if still else 2.6) if not broll else []
        hits += [scene_at + t for t in impacts]
        scene_at += length
        if still and scene.layout == "fill" and not broll and fx.available():
            # pictures get a real camera move (3D parallax where planned) and effects instead of a flat zoom
            # no vignette on the opening shot: it should look bright in the feed
            effects = [*(e for e in base_fx if not (i == 0 and e == "vignette")), *scene.effects]
            if art_style and picked[i].parent.name != "gen":
                # a real photo (in place of a drawing that got the subject wrong): the drawing's anime effects
                # (sparkles, speed lines, glow) look fake on it; keep only the flash (no film grain: it muddies the
                # picture and eats the encoder's bitrate)
                effects = [e for e in scene.effects if e == "flash"]
            fx.render_shot(picked[i], length, clip, motion=scene.motion or MOTION_CYCLE[i % len(MOTION_CYCLE)],
                           effects=effects,
                           voice=mp3, seed=i, impacts=impacts, cuts=cuts, focus=subject_focus(picked[i]),
                           # flash = a hard cut into the scene; never on the opening frame (it's what the feed shows)
                           beats=[0.0] if "flash" in scene.effects and i > 0 else [])
        else:
            render_scene(picked[i], mp3, length, clip, start=max(scene.media_start, 0.0), layout=scene.layout,
                         footage2=second.get(i), broll=broll, bright=i == 0, impacts=impacts, cuts=cuts)
        clips.append(clip)
    if hits:
        log(f"      {len(hits)} hits, {len(pacing.sound_times(hits))} with a sound")
    release_gpu()
    concat(clips, work, "joined.mp4")

    # 4. Captions (timings are offset by each scene's start in the joined video)
    log("[4/5] Captions")
    caption_scenes, overlays, t = [], [], 0.0
    for scene, (_, words, length) in zip(script.scenes, timed):
        caption_scenes.append((t, t + length, words, scene.on_screen_text, set(scene.keywords)))
        overlays += overlay_lines(scene.texts, t, t + length, profile)
        t += length
    style = script.captions.clean(lang)
    (work / "captions.ass").write_text(build_ass(caption_scenes, profile, style, overlays), encoding="utf-8")
    _install_font(profile, work / "fonts")
    if style.font:
        _install_font(profile, work / "fonts", style.font_file(lang))

    # 5. Final render + post metadata
    log("[5/5] Final render")
    final = job / "video.mp4"
    track = pick_music(music, script.mood)
    finalize(work, "joined.mp4", "captions.ass", final, track, effects=sfx.impact_track(pacing.sound_times(hits)),
             animation=bool(art_style))  # drawn scenes: x264 tuned for flat colour and line art
    try:
        if 1 <= script.key_scene <= len(clips):  # the cover shows the key visual
            k = script.key_scene - 1
            cover_at = sum(length for _, _, length in timed[:k]) + thumbs.best_frames(clips[k], 1)[0]
        else:
            cover_at = thumbs.best_frames(work / "joined.mp4", 1)[0]
    except Exception:
        cover_at = min(1.0, t / 2)
    # a scene drawn from a still picture (AI art, a photo): the cover uses that picture itself, sharper than any
    # frame of the video (no punch-in, no particles, flashes or motion blur); the editor can still switch it back to
    # a frame (image ""). Footage keeps the frame
    cover_image, start = "", 0.0
    for scene, picture, (_, _, length) in zip(script.scenes, picked, timed):
        if start <= cover_at < start + length:
            if picture and picture.is_file() and picture.suffix.lower() in IMAGE_EXTS and scene.layout == "fill":
                from .visuals import project_path

                try:
                    cover_image = project_path(picture)
                except Exception:  # outside the project folder: make_thumbnail only takes project paths
                    cover_image = ""
            break
        start += length
    make_thumbnail(job, script.title, cover_at, lang, image=cover_image)

    meta = _meta(job)
    meta["music"] = track.name if track else ""  # its credit goes into the description (music.credit)
    _save_meta(job, meta)
    tags = " ".join(f"#{h}" for h in script.hashtags)
    from .commons import credit as photo_credit

    photos = [photo_credit(p) for p in picked if p]  # real photos used (Wikimedia Commons) must be credited
    (job / "post.txt").write_text(post_body(script.title, script.caption, tags, track, script.sources, photos),
                                  encoding="utf-8")
    log(f"Done: {final}  ({t:.1f}s)")
    return final
