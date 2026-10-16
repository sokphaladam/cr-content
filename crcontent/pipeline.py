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


def draw_thumbnail(job: Path, text: str, at: float, lang: str, out: Path,
                   style: str = "bold", emphasis: str = "", image: Path | None = None) -> float:
    """Draw the frame at `at` seconds (or the photo `image` instead) with `text` as a big headline (no text = plain
    picture) into `out`.

    Returns the frame time actually used (clamped to the video).
    """
    profile = LANGS.get(lang, LANGS["en"])
    work = job / "work"
    work.mkdir(exist_ok=True)
    source = thumbnail_source(job)
    at = max(0.0, min(at, duration(source) - 0.1))
    ass_name = None
    if text.strip():
        ass_name = f"{out.stem}.ass"
        (work / ass_name).write_text(build_thumbnail_ass(text, profile, style, emphasis, size=job_size(job)),
                                     encoding="utf-8")
        if not (work / "fonts" / profile.font_file).exists():
            _install_font(profile, work / "fonts")
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
         "-frames:v", "1", "-vf", f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},setsar=1,"
         f"eq=contrast=1.08:saturation=1.3,unsharp=5:5:0.8", "-q:v", "2", str(out.resolve())])
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


def _fit_font(draw, text: str, file: str, width: float, most: int, least: int):
    """The biggest font (at most `most` px) at which `text` fits `width`; None below `least`."""
    from PIL import ImageFont

    from .styles import font_path

    found = font_path(file)
    px = most
    while px >= least:
        font = ImageFont.truetype(str(found), px) if found else ImageFont.load_default(px)
        if draw.textlength(text, font=font) <= width:
            return font
        px = int(px * 0.92)
    return None


def draw_magazine(job: Path, text: str, lang: str, out: Path) -> bool:
    """A magazine-cover thumbnail from a one-cover music video's frame: `text` in huge heavy letters across the
    top with the character standing in front of it, two small lines of info at the sides. False when the video has
    no cover frame (made before one-cover mode, or with several pictures)."""
    import numpy as np
    from PIL import Image, ImageDraw, ImageFilter, ImageOps

    from .lyrics import SongScript
    from .styles import FONTS, font_path

    frame = job / "work" / COVER_FRAME
    if not frame.exists():
        return False
    cover = Image.open(frame).convert("RGB")
    W, H = cover.size
    target = np.median(np.concatenate([np.asarray(cover)[0], np.asarray(cover)[:, 0]]), axis=0).astype(np.float32)
    _, bg = _flatten(cover, target, with_mask=True)
    person = ImageOps.invert(bg).filter(ImageFilter.GaussianBlur(1.2))  # the character, in front of the words
    ink = (22, 22, 26)
    words = Image.new("RGB", (W, H), tuple(int(c) for c in target))
    draw = ImageDraw.Draw(words)
    heavy = FONTS["km"]["Khmer OS Muol Light"] if lang == "km" else (
        "seguibl.ttf" if font_path("seguibl.ttf") else FONTS["en"]["Impact"])
    big = (text if lang == "km" else text.upper()).strip()
    # where the character's head and shoulders are: two or more words go either side of them ("CHILL" | "J-POP")
    top = np.asarray(person, dtype=np.float32)[: round(H * 0.35)] > 128
    cols = np.where(top.mean(0) > 0.3)[0]  # solid head and shoulders, not wisps of flowing hair
    x_left, x_right = (int(cols[0]), int(cols[-1])) if len(cols) else (W // 2, W // 2)
    words_ = big.split()
    y = round(H * 0.03)
    if len(words_) >= 2:
        half = len(big) // 2
        cut = min((i for i, ch in enumerate(big) if ch == " "), key=lambda i: abs(i - half))
        pair = [big[:cut], big[cut + 1:]]
        overlap = W * 0.07  # the words tuck a little behind the character
        room = [x_left + overlap - W * 0.04, W * 0.96 - (x_right - overlap)]
        sizes = [_fit_font(draw, t, heavy, r, round(H * 0.3), round(H * 0.08)) for t, r in zip(pair, room)]
        if all(sizes):
            font = min(sizes, key=lambda f: f.size)
            lbox, rbox = (draw.textbbox((0, 0), t, font=font) for t in pair)
            draw.text((x_left + overlap - (lbox[2] - lbox[0]) - lbox[0], y - lbox[1]), pair[0], font=font, fill=ink)
            draw.text((x_right - overlap - rbox[0], y - rbox[1]), pair[1], font=font, fill=ink)
            words_ = []
    if words_:  # one word (or the sides are too narrow): across the top, behind the head
        font = (_fit_font(draw, big, heavy, W * 0.94, round(H * 0.42), round(H * 0.12))
                or _fit_font(draw, big, heavy, W * 0.94, round(H * 0.12), 8))
        box = draw.textbbox((0, 0), big, font=font)
        draw.text(((W - (box[2] - box[0])) / 2 - box[0], y - box[1]), big, font=font, fill=ink)
    # the small print at the sides, the way playlist covers carry their mood and use
    try:
        song = SongScript.load(job / "song.json")
        mood, genre = song.mood.split(",")[0].strip().upper(), song.genre.split(",")[0].strip().upper()
    except Exception:
        mood, genre = "", ""
    small = _fit_font(draw, "LYRIC VIDEO", heavy if lang != "km" else FONTS["en"]["Impact"], W, round(H * 0.034), 8)
    left = [f"{datetime.now().year} {mood} MOOD".replace("  ", " "), f"{genre} SONG" if genre else ""]
    right = ["LYRIC VIDEO", "CHILL / WORK / STUDY"]
    for k, (l_txt, r_txt) in enumerate(zip(left, right)):
        ly = round(H * 0.8) + k * round(H * 0.045)  # low, beside the clothes rather than the hair
        if l_txt:
            draw.text((round(W * 0.05), ly), l_txt, font=small, fill=ink)
        rw = draw.textlength(r_txt, font=small)
        draw.text((round(W * 0.95 - rw), ly), r_txt, font=small, fill=ink)
    Image.composite(cover, words, person).save(out, quality=92)
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
COVER_EFFECTS = ["bokeh", "sparkles", "glow", "grain"]
COVER_SHAPE = "9:16"  # a cover character is drawn portrait (head to thighs with room above), then set on a flat frame


def _flatten(img, target, tolerance: float = 26, with_mask: bool = False):
    """`img` (a PIL picture) with its plain background (found by spreading in from the edges through pixels of its
    colour, plus pockets of that colour shut in by hair or arms) turned into the flat `target` colour, blended over a
    soft mask so hair edges stay soft and keep no rim of the old colour. Pixels already near `target` count as
    background too (a widened picture's kept middle). with_mask: also return the background mask (PIL "L")."""
    import numpy as np
    from PIL import Image, ImageFilter

    small = np.asarray(img.resize((max(img.width * 512 // img.height, 1), 512)), dtype=np.float32)
    edge = np.concatenate([small[0], small[:, 0], small[:, -1]])  # not the bottom: the body is cut off there
    ref = np.median(edge, axis=0)
    near = np.linalg.norm(small - ref, axis=2) < tolerance  # tight: hair or clothes close to it stay
    near |= np.linalg.norm(small - target, axis=2) < 18
    bg = np.zeros_like(near)
    bg[0], bg[-1], bg[:, 0], bg[:, -1] = near[0], near[-1], near[:, 0], near[:, -1]
    for _ in range(small.shape[0] + small.shape[1]):  # grow from the edges through similar pixels only
        grown = bg.copy()
        grown[1:] |= bg[:-1]
        grown[:-1] |= bg[1:]
        grown[:, 1:] |= bg[:, :-1]
        grown[:, :-1] |= bg[:, 1:]
        grown &= near
        if (grown == bg).all():
            break
        bg = grown
    bg |= (np.linalg.norm(small - ref, axis=2) < 18) | (np.linalg.norm(small - target, axis=2) < 12)
    mask = Image.fromarray((bg * 255).astype(np.uint8)).resize(img.size, Image.BILINEAR)
    core = np.asarray(mask.filter(ImageFilter.GaussianBlur(1.5)), dtype=np.float32)[..., None] / 255
    rim = np.asarray(mask.filter(ImageFilter.MaxFilter(7)).filter(ImageFilter.GaussianBlur(4)),
                     dtype=np.float32)[..., None] / 255
    pic = np.asarray(img, dtype=np.float32)
    # edge pixels are part old background: shift that part to the pastel (no coloured rim), then fill flat
    pic = np.clip(pic + (target - ref) * rim * (1 - core), 0, 255) * (1 - core) + target * core
    flat = Image.fromarray(pic.astype(np.uint8))
    return (flat, mask) if with_mask else flat


OUTPAINT_SIZE = (1344, 768)  # the SDXL size a landscape cover is widened at (16:9 within 2%)


def cover_canvas(picture: Path, size: tuple[int, int], colour: str, prompt: str = "", seed: int = 1,
                 log: Callable[[str], None] = print) -> Path:
    """The drawn cover character (portrait) as a picture of the frame's shape on a flat `colour` background. A
    landscape frame is widened by the drawing model itself: the character is set on a canvas of that colour and the
    sides, the strip above the head and a band over the picture's edges are painted to continue it (hair and clothes
    the portrait cut off run on), so there is no pasted-on edge. Made once next to the picture."""
    import numpy as np
    from PIL import Image, ImageDraw, ImageFilter, ImageOps

    from . import imagegen

    W, H = size
    out = picture.with_name(f"{picture.stem}-cover9-{W}x{H}-{colour.replace(' ', '_')}.png")
    if out.exists():
        return out
    target = np.array(COVER_COLOURS.get(colour, (246, 188, 212)), dtype=np.float32)
    flat, bg = _flatten(Image.open(picture).convert("RGB"), target, with_mask=True)
    if W > H and prompt:
        CW, CH = OUTPAINT_SIZE
        h = round(CH * 0.92)  # room above the head
        w = round(flat.width * h / flat.height)
        x0, y0 = (CW - w) // 2, CH - h
        canvas = Image.new("RGB", (CW, CH), tuple(int(c) for c in target))
        canvas.paste(flat.resize((w, h), Image.LANCZOS), (x0, y0))
        # keep only the character (a little inside its outline), minus a band along the picture's edges so what
        # they cut off continues; everything else is painted, so no trace of the picture's rectangle is left
        person = ImageOps.invert(bg).resize((w, h), Image.BILINEAR).point(lambda v: 255 if v > 128 else 0)
        band = 28
        ImageDraw.Draw(person).rectangle((0, 0, w, band), fill=0)
        ImageDraw.Draw(person).rectangle((0, 0, band, h), fill=0)
        ImageDraw.Draw(person).rectangle((w - band, 0, w, h), fill=0)
        keep = Image.new("L", (CW, CH), 0)
        keep.paste(person.filter(ImageFilter.MinFilter(7)), (x0, y0))
        mask = ImageOps.invert(keep)
        log("      widening the cover picture to the frame")
        wide = imagegen.outpaint(canvas, mask, prompt, "anime", seed, log=log)
        _flatten(wide, target, tolerance=34).resize((W, H), Image.LANCZOS).save(out)
        return out
    if abs(flat.width / flat.height - W / H) < 0.05:  # a portrait frame: the picture's own shape, edge to edge
        flat.resize((W, H), Image.LANCZOS).save(out)
        return out
    # no prompt to widen it with: the picture on the flat colour
    h = round(H * 0.94)
    w = round(flat.width * h / flat.height)
    frame = Image.new("RGB", (W, H), tuple(int(c) for c in target))
    frame.paste(flat.resize((w, h), Image.LANCZOS), ((W - w) // 2, H - h))
    frame.save(out)
    return out


def cover_colour(title: str) -> str:
    """The flat pastel background of a song's cover picture (the same every time for the same song)."""
    return list(COVER_COLOURS)[int(hashlib.sha1(title.strip().lower().encode()).hexdigest(), 16) % len(COVER_COLOURS)]


def cover_scene(song) -> str:
    """The direction for a song's single cover picture (director.plan_song follows it exactly)."""
    colour = cover_colour(song.title)
    return (f"COVER ART for the whole song, like a J-pop playlist cover: one anime character (the main character of "
            f"the creator's idea when it describes one, with their look, hair and outfit; otherwise one who fits the "
            f"song's mood and lyrics), cowboy shot (head to thighs, with room above the head), centred, eye level, facing the viewer with a lively expressive "
            f"pose (hands near the face or at the sides, never reaching at the camera), a stylish outfit with {colour} "
            f"accents, on a plain flat {colour} background with nothing else in it. Keep the prompt under 30 words "
            f"and end it with: simple background, {colour} background")


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
        tags = f"simple background, {cover_colour(song.title)} background"
        if not bible:  # Claude couldn't plan it: a short tag prompt the model reads whole (the direction is too long)
            plans = [director.ShotPlan(f"1girl, solo, cowboy shot, looking at viewer, {song.mood.split(',')[0].strip().lower()} expression, "
                                       f"stylish casual outfit, dark hoodie", "breathe", [])]
        plans = [director.ShotPlan(p.prompt if tags in p.prompt else f"{p.prompt.rstrip(' ,.')}, {tags}", "breathe",
                                   COVER_EFFECTS) for p in plans]
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
    for k, s in enumerate(plan["slots"]):
        seed = s.get("seed") or k + 1
        plans.append(director.ShotPlan(s["prompt"], s.get("motion") or "push_in", s.get("effects") or []))
        shape = picture_shape(s, size)
        log(f"      drawing picture {k + 1}/{len(plan['slots'])}"
            + (" (already drawn)" if imagegen.drawn(s["prompt"], style, shape, seed) else ""))
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


COLD_OPEN_GAP = 1.8  # seconds of lightning and thunder between the chorus preview and the song's start
COLD_OPEN_SECONDS = (3.5, 5.5, 8.0)  # the preview's shortest, ideal and longest length


def cold_open_window(song, lines: list, spans: list[tuple[float, float]], total: float) -> tuple[float, float] | None:
    """(start, end) in the song of a cold open's chorus preview: the first chorus (else the first section sung again),
    from just before its first line to the end of the line that ends nearest ~5.5 s in. None without a chorus."""
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


def _cold_open_lines(lines: list, start: float, end: float) -> list:
    """The lyrics for a cold open: the preview's lines moved to the very start, then every line after the gap."""
    from dataclasses import replace

    def moved(line, by: float, upto: float = float("inf")):
        words = [replace(w, start=min(w.start + by, upto), end=min(w.end + by, upto)) for w in line.words]
        return replace(line, start=min(line.start + by, upto), end=min(line.end + by, upto), words=words)

    length = end - start
    preview = [moved(l, -start, length) for l in lines if start - 0.05 <= l.start < end - 0.5]
    # a blank line where the lightning strikes: the preview's last line ends there instead of lingering on the flash
    cut = replace(lines[0], text="", start=length, end=length, words=[])
    return preview + [cut] + [moved(l, length + COLD_OPEN_GAP) for l in lines]


def neon_title(title: str) -> str:
    """The song's name from a post title: "Signal Lost - Song About ... (Official Lyric Video)" -> "Signal Lost"."""
    name = re.split(r"\s[-–—|:]\s|\s*[(\[]", title, maxsplit=1)[0].strip()
    return name or title.strip()


def _cold_open_media(work: Path, song_video: str, mix: Path, start: float, end: float, size: tuple[int, int]) -> Path:
    """The cold open's pictures and sound: preview.mp4 (the chorus's shots), flash.mp4 (lightning: white flickering,
    then fading to black) and the soundtrack cold_open.wav (the chorus, cut dead into thunder, then the whole song)."""
    from .config import FPS

    length, W, H = end - start, *size
    clip = ["-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p", "-r", str(FPS),
            "-c:a", "aac", "-b:a", "192k", "-ar", "44100", "-ac", "2"]
    run(["ffmpeg", "-y", "-hide_banner", "-ss", f"{start:.3f}", "-i", song_video, "-t", f"{length:.3f}", *clip,
         "preview.mp4"], cwd=work)
    # on, a flicker off, on again, then the white dies to black before the intro
    light = "if(lt(t,0.1),0,if(lt(t,0.18),-0.75,if(lt(t,0.34),0,-min(1,(t-0.34)/0.9))))"
    run(["ffmpeg", "-y", "-hide_banner", "-f", "lavfi", "-i", f"color=c=white:s={W}x{H}:r={FPS}:d={COLD_OPEN_GAP}",
         "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo", "-vf", f"format=yuv420p,eq=brightness='{light}':eval=frame",
         "-t", f"{COLD_OPEN_GAP}", *clip, "flash.mp4"], cwd=work)
    stereo = "aresample=44100,aformat=channel_layouts=stereo"
    ms = round(length * 1000)
    run(["ffmpeg", "-y", "-hide_banner", "-i", str(mix.resolve()), "-i", str(sfx.sound("thunder").resolve()),
         "-filter_complex",
         f"[0:a]{stereo},asplit=2[x][y];"
         f"[x]atrim={start:.3f}:{end:.3f},asetpts=PTS-STARTPTS,afade=t=out:st={max(length - 0.12, 0):.3f}:d=0.12[p];"
         f"anullsrc=r=44100:cl=stereo:d={COLD_OPEN_GAP}[g];[y]asetpts=PTS-STARTPTS[s];"
         f"[p][g][s]concat=n=3:v=0:a=1[c];[1:a]{stereo},adelay={ms}|{ms},volume=0.8[t];"
         f"[c][t]amix=inputs=2:duration=first:normalize=0[a]",
         "-map", "[a]", "-c:a", "pcm_s16le", "cold_open.wav"], cwd=work)
    return work / "cold_open.wav"


def make_music_video(song_dir: Path, log: Callable[[str], None] = print, idea: str = "", look: str = "",
                     lyric_style: "dict | None" = None, art_style: str | None = None,
                     pictures: str | None = None, direction: dict | None = None,
                     cold_open: bool | None = None) -> Path:
    """Song folder in -> a NEW video folder next to it: beat-cut footage per section, karaoke lyrics, the song as audio.

    The song folder works like a draft: its lyrics and timing stay editable, and every render is a separate version
    whose meta.json "song" points back to it. `idea`: your own idea for the video; the footage follows it (this
    version only, the song keeps its own searches). `look`: colour grade for the footage (styles.LOOKS);
    `lyric_style`: how the lyrics are drawn (styles.LyricStyle fields). `art_style`: "" = stock footage, else an
    imagegen.STYLES look drawn on this computer (None = the song's last choice). `pictures`: how many of them
    (PICTURE_PACES: "fewer", "normal", "more"; None = the song's last choice). `cold_open`: open on a few seconds
    of the chorus with the title in neon, then a lightning flash and thunder, then the song from the start (None =
    the song's last choice). Idea, look and styles are remembered on the song for the next version. Returns the new
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
    # the shot list made from this idea (director.direct_idea, maybe edited); None = the song's, if it fits the idea
    direction = song_direction(song, song_meta.get("direction") if direction is None else direction, idea)
    remembered = {"idea": idea, "look": look, "lyric_style": style.model_dump(), "art_style": art_style,
                  "pictures": pictures, "cold_open": cold_open, **({"direction": direction} if direction else {})}
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
    held = bool(shot_art) and pictures == "cover"
    if held:  # one picture held for the whole song: no cuts, no beat punches
        picture, plan = shot_art[0]
        seed = (json.loads((work / "art.json").read_text(encoding="utf-8"))["slots"][0].get("seed") or 1)
        picture = cover_canvas(picture, size, cover_colour(song.title), plan.prompt, seed, log)
        shutil.copy(picture, work / COVER_FRAME)  # for the magazine thumbnail
        log(f"      holding one picture for the whole song ({total:.0f}s)")
        clip = work / "shot_00.mp4"
        fx.render_shot(picture, total, clip, size=size, motion="breathe", effects=plan.effects or COVER_EFFECTS,
                       look=look, seed=7)
        clips.append(clip)
    for i, shot in enumerate([] if held else shots):
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
    opening = cold_open_window(song, lines, spans, total) if cold_open else None
    soundtrack, sung, title = mix, lines, None
    if opening:
        # the chorus's own shots, then lightning, then the whole video; the song cut the same way
        a, b = opening
        log(f"      cold open: the chorus from {a:.1f}s to {b:.1f}s, then lightning and thunder")
        concat(clips, work, "song_cut.mp4")
        soundtrack = _cold_open_media(work, "song_cut.mp4", mix, a, b, size)
        concat([work / "preview.mp4", work / "flash.mp4", work / "song_cut.mp4"], work, "joined.mp4")
        sung = _cold_open_lines(lines, a, b)
        title = (neon_title(song.title), min(1.0, (b - a) * 0.2), b - a)
    else:
        if cold_open:
            log("      no chorus found for a cold open; the video starts with the song")
        concat(clips, work, "joined.mp4")

    # 3. Karaoke captions
    log("[3/4] Captions")
    (work / "captions.ass").write_text(build_karaoke_ass(sung, profile, size=size, style=style, title=title),
                                       encoding="utf-8")
    _install_font(profile, work / "fonts", FONTS.get(lang, FONTS["en"]).get(style.font, ""))

    # 4. Final render with the song as the soundtrack + cover + post text
    log("[4/4] Final render")
    final = job / "video.mp4"
    finalize(work, "joined.mp4", "captions.ass", final, None, soundtrack=soundtrack, fade_out=2.0)
    if opening:
        total += opening[1] - opening[0] + COLD_OPEN_GAP
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
                     "cold_open": bool(opening), "duration": round(total, 2)})
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
                # (sparkles, speed lines, glow) look fake on it; keep only film grain and the flash
                effects = ["grain", *(e for e in scene.effects if e == "flash")]
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
    finalize(work, "joined.mp4", "captions.ass", final, track, effects=sfx.impact_track(pacing.sound_times(hits)))
    try:
        if 1 <= script.key_scene <= len(clips):  # the cover shows the key visual
            k = script.key_scene - 1
            cover_at = sum(length for _, _, length in timed[:k]) + thumbs.best_frames(clips[k], 1)[0]
        else:
            cover_at = thumbs.best_frames(work / "joined.mp4", 1)[0]
    except Exception:
        cover_at = min(1.0, t / 2)
    make_thumbnail(job, script.title, cover_at, lang)

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
