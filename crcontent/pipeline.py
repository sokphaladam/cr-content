"""Topic (or script file) in -> finished vertical video + post metadata out."""
import json
import random
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Callable

from . import art, fx, thumbs, voiceover
from .captions import THUMB_STYLES, build_ass, build_thumbnail_ass, overlay_lines
from .config import ASSETS_DIR, LANGS, OUTPUT_DIR, ROOT, SCENE_PAD_SEC, frame_size, orientation
from .render import concat, duration, finalize, render_scene, run, thumbnail
from .script import VideoScript, generate_script
from .visuals import IMAGE_EXTS, FootagePicker


def slugify(text: str, limit: int = 40) -> str:
    slug = re.sub(r"[^\w]+", "-", text.lower(), flags=re.ASCII).strip("-")
    return (slug or "video")[:limit]


def post_body(title: str, caption: str, tags: str, track: Path | str | None = None, sources: str = "") -> str:
    """post.txt: title line, the caption (plus the works it cites and the music's credit when its licence asks for
    one), then the #tags."""
    from .music import credit

    cited = f"Sources: {sources.strip()}" if sources.strip() else ""
    body = "\n\n".join(x for x in (caption.strip(), cited, credit(track)) if x)
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
    tracks = list((ASSETS_DIR / "music").glob("*.mp3")) if (ASSETS_DIR / "music").exists() else []
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


def make_thumbnail(job: Path, text: str, at: float, lang: str, style: str = "bold", emphasis: str = "",
                   image: str = "", design: str = "") -> Path:
    """(Re)draw job/thumbnail.jpg and remember the choices in meta.json. `image`: a project-relative photo to use
    instead of a video frame ("" = the frame at `at`). style "designed": Claude's layout; `design` names the
    suggestion it starts from (e.g. "suggest/thumb_2.svg"), otherwise the current one is kept or a new one made."""
    out = job / "thumbnail.jpg"
    photo = ROOT / image if image else None
    photo = photo if photo and photo.exists() else None
    if style == "designed" and text.strip():
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
    if sys.platform == "darwin":
        log("      ! AI scene art needs an NVIDIA GPU, which Macs don't have; using stock footage")
        return False
    if not imagegen.installed():
        log("      ! AI scene art isn't installed (Settings → AI features → Install AI add-on); using stock footage")
        return False
    if not imagegen.gpu_name():
        log("      ! AI scene art needs an NVIDIA GPU, none found; using stock footage")
        return False
    return True


def plan_scene_art(script: VideoScript, log: Callable[[str], None] = print) -> bool:
    """Fill in a picture prompt, camera move and effects for every scene that has no chosen media and no prompt yet,
    keeping prompts you edited. All scenes are planned together so the pictures share one look. True if changed."""
    from . import director

    todo = [i for i, sc in enumerate(script.scenes) if not sc.media and not sc.art_prompt.strip()]
    if not todo:
        return False
    log("      planning the pictures (Claude)")
    bible, shots = director.plan_scenes(script.title, [{"narration": sc.narration, "visual_query": sc.visual_query}
                                                       for sc in script.scenes], script.art_style, bible=script.art_bible)
    script.art_bible = script.art_bible or bible
    for i in todo:
        sc = script.scenes[i]
        sc.art_prompt = shots[i].prompt
        sc.motion = sc.motion or shots[i].motion
        sc.effects = sc.effects or shots[i].effects
    return True


# how many AI pictures a music video gets: seconds each picture stays on screen, and a cap for long songs.
# A picture takes ~40 s to draw on an RTX 3060, so "normal" on a 3-minute song is ~25 minutes of drawing.
PICTURE_PACES = {"fewer": (8.0, 24), "normal": (4.5, 40), "more": (3.0, 60)}


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
ART_PLAN = "art_plan.json"  # a song's picture plan, kept in the song folder so it can be checked before a render


def song_slots(song, spans: list[tuple[float, float]], shots: list, lines: list, pace: str = "normal",
               scenes: list[str] | None = None, frames: list[str] | None = None) -> tuple[list[dict], list[int], set[int]]:
    """The pictures a music video needs: consecutive shots of a section grouped so each picture stays on screen
    ~PICTURE_PACES seconds. A section that repeats an earlier one (a chorus sung again) shows that section's pictures
    again, unless `scenes` (a directed idea, one per section) asks for something else there. `frames`: the
    directed frame per section; "4:3" slots are drawn as landscape home-video pictures.
    Returns (slots, the slot of every shot, the shots that show a repeated picture)."""
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


def _direction_key(direction: dict | None) -> str:
    """Changes whenever the shot list does, so a picture plan made from another one isn't reused."""
    if not direction:
        return ""
    import hashlib

    return hashlib.sha1(json.dumps([direction.get("bible", ""), direction["sections"]], sort_keys=True,
                                   ensure_ascii=False).encode()).hexdigest()[:12]


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
    if plan.get("direction", "") != _direction_key(direction):
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
        shape = HOME_VIDEO if s.get("frame") == "4:3" else size  # a home video's picture is drawn landscape
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


def make_music_video(song_dir: Path, log: Callable[[str], None] = print, idea: str = "", look: str = "",
                     lyric_style: "dict | None" = None, art_style: str | None = None,
                     pictures: str | None = None, direction: dict | None = None) -> Path:
    """Song folder in -> a NEW video folder next to it: beat-cut footage per section, karaoke lyrics, the song as audio.

    The song folder works like a draft: its lyrics and timing stay editable, and every render is a separate version
    whose meta.json "song" points back to it. `idea`: your own idea for the video; the footage follows it (this
    version only, the song keeps its own searches). `look`: colour grade for the footage (styles.LOOKS);
    `lyric_style`: how the lyrics are drawn (styles.LyricStyle fields). `art_style`: "" = stock footage, else an
    imagegen.STYLES look drawn on this computer (None = the song's last choice). `pictures`: how many of them
    (PICTURE_PACES: "fewer", "normal", "more"; None = the song's last choice). Idea, look and styles are
    remembered on the song for the next version. Returns the new video.mp4.
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
    # the shot list made from this idea (director.direct_idea, maybe edited); None = the song's, if it fits the idea
    direction = song_direction(song, song_meta.get("direction") if direction is None else direction, idea)
    remembered = {"idea": idea, "look": look, "lyric_style": style.model_dump(), "art_style": art_style,
                  "pictures": pictures, **({"direction": direction} if direction else {})}
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
    for i, shot in enumerate(shots):
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

    # 3. Karaoke captions
    log("[3/4] Captions")
    (work / "captions.ass").write_text(build_karaoke_ass(lines, profile, size=size, style=style), encoding="utf-8")
    _install_font(profile, work / "fonts", FONTS.get(lang, FONTS["en"]).get(style.font, ""))

    # 4. Final render with the song as the soundtrack + cover + post text
    log("[4/4] Final render")
    final = job / "video.mp4"
    finalize(work, "joined.mp4", "captions.ass", final, None, soundtrack=mix, fade_out=2.0)
    try:
        cover_at = thumbs.best_frames(work / "joined.mp4", 1)[0]
    except Exception:
        cover_at = min(1.0, total / 2)
    hook = next((l.text for l in lines), "")
    make_thumbnail(job, song.title, cover_at, lang)
    tags = " ".join(f"#{h}" for h in song.hashtags)
    credit = "" if own else "\nMusic and vocals are AI-generated.\n"
    (job / "post.txt").write_text(f"{song.title}\n\n{song.caption}\n\n{tags}\n{credit}", encoding="utf-8")
    _save_meta(job, {**_meta(job), "timing": timing, "beats": beat_method, "shots": len(shots), "hook": hook})
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
        timed.append((mp3, words, duration(mp3) + SCENE_PAD_SEC))

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
    for i, scene in enumerate(script.scenes):
        chosen = (ROOT / scene.media) if scene.media else None
        if chosen and chosen.exists():
            footage = chosen
            log(f"      scene {i + 1}: your pick -> {footage.name}")
        else:
            if chosen:
                log(f"      scene {i + 1}: chosen file {scene.media} is missing, picking automatically")
            footage = None
            if art_style:
                from . import imagegen

                try:
                    log(f"      scene {i + 1}/{len(script.scenes)}: drawing")
                    footage = imagegen.generate(scene.art_prompt or scene.visual_query, art_style, frame_size(None),
                                                seed=scene.art_seed or None, log=log)
                except Exception as e:
                    log(f"      ! scene {i + 1}: couldn't draw it ({type(e).__name__}: {str(e)[:120]}); using stock")
            if not footage:
                footage = picker.pick(scene.visual_query)
            if not footage:  # no stock clip: Claude draws the scene instead of a plain gradient
                footage = art.try_background(f"{scene.visual_query}\n{scene.narration}", frame_size(None), log)
            log(f"      scene {i + 1}: {scene.visual_query!r} -> {footage.name if footage else 'gradient'}")
        picked.append(footage)
    second = {i: _existing(scene.media2) or picker.pick(scene.visual_query)
              for i, scene in enumerate(script.scenes) if scene.layout == "split"}
    base_fx = fx.default_effects(art_style, music=False) if art_style else ["vignette"]
    clips = []
    for i, (scene, (mp3, _, length)) in enumerate(zip(script.scenes, timed)):
        broll = [(path, b.at, b.duration) for b in scene.broll
                 if (path := _existing(b.media)) and b.duration > 0 and b.at < length]
        clip = work / f"scene_{i:02d}.mp4"
        still = picked[i] is not None and picked[i].suffix.lower() in IMAGE_EXTS
        if still and scene.layout == "fill" and not broll and fx.available():
            # pictures get a real camera move (3D parallax where planned) and effects instead of a flat zoom
            fx.render_shot(picked[i], length, clip, motion=scene.motion or MOTION_CYCLE[i % len(MOTION_CYCLE)],
                           effects=[*base_fx, *scene.effects], voice=mp3, seed=i,
                           beats=[0.0] if "flash" in scene.effects else [])  # flash = a hard cut into the scene
        else:
            render_scene(picked[i], mp3, length, clip, start=max(scene.media_start, 0.0), layout=scene.layout,
                         footage2=second.get(i), broll=broll)
        clips.append(clip)
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
    finalize(work, "joined.mp4", "captions.ass", final, track)
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
    (job / "post.txt").write_text(post_body(script.title, script.caption, tags, track, script.sources), encoding="utf-8")
    log(f"Done: {final}  ({t:.1f}s)")
    return final
