"""Footage for every shot of a Director Plan (AI-DIRECTOR.md 6, 9; milestone 3).

Per shot, in this order:
  1. your own file: <media>/shot-003-2.mp4 (or .mov / .jpg ...), or for a scene's first shot the long-video
     convention <media>/scene-03.*; used as it is
  2. the AI Director's searches, most specific first ("raven bending wire hook" before "raven close up"), in the
     same libraries and caches as long videos (longform/footage.py: Pexels, Pixabay, Wikimedia, iNaturalist, ...)
Each candidate is downloaded and Gemini looks at three of its frames: is it the right subject, does it show the
action the narration states (only asked when the shot needs the exact action), and how good it looks. A pretty clip
of the wrong animal is never used. Resolution, length, motion and orientation come from the file itself.
The best match is kept with its source and licence, the others become alternatives, and every problem is written
in plain words on the shot. Shots the user locked keep their footage.
"""
import base64
import io
import json
import re
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from .config import CACHE_DIR, LLM_MODEL
from .director_plan import DirectorPlan, Footage, Shot
from .longform import footage as lf
from .visuals import IMAGE_EXTS, VIDEO_EXTS

PASS = lf.PASS          # 7: clearly right
MIN_SHOW = lf.MIN_SHOW  # 5: under it, never used
TRIES = 3               # candidates downloaded and checked per search before moving on
KEEP = 4                # alternatives kept per shot
MOVING = {"tracking", "aerial", "handheld", "slow_motion"}  # camera moves a still photo can't fake
SIZES = {"short": (1080, 1920), "long": (1920, 1080)}
# words that mean nothing to a stock library and make its search return junk ("octopus coral reef vertical": a burger)
FORMAT_WORDS = re.compile(r"\b(vertical|horizontal|portrait|landscape|9:16|16:9|[48]k|hd|footage|video|clip|stock)\b", re.I)

CHECK_SCHEMA = {
    "type": "object",
    "properties": {"subject": {"type": "integer"}, "action": {"type": "integer"}, "quality": {"type": "integer"},
                   "problem": {"type": "string"}},
    "required": ["subject", "action", "quality", "problem"],
}


# ---------- looking at a candidate ----------

def _frames(path: Path) -> bytes:
    """A JPEG of the picture, or of three frames of a clip side by side (an action needs more than one moment)."""
    from PIL import Image

    from .render import duration, run

    if path.suffix.lower() in IMAGE_EXTS:
        pics = [Image.open(path).convert("RGB")]
    else:
        length, pics = duration(path), []
        for k, at in enumerate((0.2, 0.5, 0.8)):
            frame = path.with_suffix(f".shot{k}.jpg")
            if not frame.exists():
                run(["ffmpeg", "-y", "-v", "error", "-ss", f"{length * at:.2f}", "-i", str(path), "-frames:v", "1",
                     "-vf", "scale=-2:480", str(frame)])
            pics.append(Image.open(frame).convert("RGB"))
    for p in pics:
        p.thumbnail((640, 640))
    strip = Image.new("RGB", (sum(p.width for p in pics), max(p.height for p in pics)))
    x = 0
    for p in pics:
        strip.paste(p, (x, 0))
        x += p.width
    buf = io.BytesIO()
    strip.save(buf, "JPEG", quality=85)
    return buf.getvalue()


def look(path: Path, shot: Shot, client=None) -> dict:
    """Gemini's 0-10 scores for `path` as footage for `shot`: subject, action (None when the shot doesn't need the
    exact action), quality, and what's wrong. Kept next to the file, so the same clip is never paid for twice."""
    exact = shot.evidence == "exact_action" and bool(shot.action)
    ask = {"subject": shot.subject or shot.visual_description, "action": shot.action if exact else ""}
    note = path.with_suffix(".shot-check.json")
    saved = json.loads(note.read_text(encoding="utf-8")) if note.exists() else {}
    if saved.get("ask") == ask:
        return saved["verdict"]
    if client is None:
        from .script import make_client

        client = make_client()
    what = "a video (three moments, left to right)" if path.suffix.lower() in VIDEO_EXTS else "a photo"
    task = (f"This is {what}, a candidate for one shot of a documentary.\nThe shot must show: {ask['subject']}\n"
            + (f"Doing exactly this (stated as fact in the narration): {ask['action']}\n" if exact else "")
            + f"Shot: {shot.shot_type.replace('_', ' ')}; {shot.visual_description}\n"
            "subject: 0 = a different animal/thing or not visible, 5 = recognisable but wrong in key features (a crow "
            "for a raven), 8 = clearly right, 10 = perfect. "
            + ("action: 0 = not happening, 5 = related but not the stated action, 8 = clearly this action. "
               if exact else "action: return 0 (not asked). ")
            + "quality: framing, sharpness and light as documentary footage, 0-10 (watermarks, text over the picture "
            "or heavy blur lower it). problem: one short sentence on what's wrong for this shot, \"\" if nothing.")
    response = client.beta.messages.create(
        model=LLM_MODEL, max_tokens=1000,
        output_config={"effort": "low", "format": {"type": "json_schema", "schema": CHECK_SCHEMA}},
        messages=[{"role": "user", "content": [
            {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg",
                                         "data": base64.b64encode(_frames(path)).decode()}},
            {"type": "text", "text": task}]}])
    data = json.loads(next(b.text for b in response.content if b.type == "text"))
    clamp = lambda v: max(0, min(int(v), 10))  # noqa: E731
    verdict = {"subject": clamp(data["subject"]), "action": clamp(data["action"]) if exact else None,
               "quality": clamp(data["quality"]), "problem": str(data.get("problem", "")).strip()}
    note.write_text(json.dumps({"ask": ask, "verdict": verdict}), encoding="utf-8")
    return verdict


def match_of(shot: Shot, v: dict | None) -> str:
    if v is None:
        return "unchecked"
    if v["subject"] < MIN_SHOW:
        return "weak"
    if v["action"] is not None:  # the narration states an action: the subject alone isn't the shot
        if v["subject"] >= PASS and v["action"] >= PASS:
            return "exact"
        return "subject_only" if v["subject"] >= PASS else "weak"
    return "good" if v["subject"] >= PASS else "weak"


TIER = {"own": 0, "drawn": 0, "exact": 1, "good": 1, "unchecked": 2, "subject_only": 3, "weak": 4}
CARDS = CACHE_DIR / "director-cards"


def graphic(shot: Shot, scene_text: str, fmt: str, lang: str) -> Footage:
    """A graphic shot drawn by the app as a card: the scene's on-screen text (or the shot's subject) as the title,
    and a short list when the shot's description names a few items ("hearts: 3; blood: blue; brains: 9")."""
    import hashlib

    from .longform import cards

    title = scene_text or shot.subject or shot.purpose
    pieces = [p.strip(" .") for p in re.split(r"[;\n]|, (?=[A-Z0-9])", shot.visual_description) if p.strip(" .")]
    items = pieces if 2 <= len(pieces) <= 5 and all(len(p) <= 40 for p in pieces) else []
    card = {"style": "list" if items else "headline", "title": title, "items": items}
    key = hashlib.sha1(json.dumps([card, fmt, lang], ensure_ascii=False).encode()).hexdigest()[:16]
    out = CARDS / f"{key}.png"
    if not out.exists():
        CARDS.mkdir(parents=True, exist_ok=True)
        cards.draw(card, out, SIZES[fmt], lang)
    return Footage(source="card", kind="photo", file=str(out), author="drawn by the app", licence="made by the app",
                   match="drawn")


def _footage(item: dict, query: str) -> Footage:
    return Footage(source=item["source"], kind=item["kind"], thumb=item.get("thumb", ""), page=item.get("page", ""),
                   author=item.get("author", ""), licence=item.get("licence", ""),
                   licence_url=item.get("licence_url", ""), query=query, width=int(item.get("width") or 0),
                   height=int(item.get("height") or 0), duration=float(item.get("duration") or 0),
                   raw={k: v for k, v in item.items() if k not in ("check", "problem")})


def _scored(f: Footage, shot: Shot, v: dict | None) -> Footage:
    if v:
        f.subject_score, f.action_score, f.quality_score, f.problem = v["subject"], v["action"], v["quality"], v["problem"]
    f.match = match_of(shot, v)
    return f


def warnings_for(shot: Shot, fmt: str) -> list[str]:
    """Plain-words problems with a shot's footage."""
    f, what = shot.footage, shot.subject or shot.visual_description or "this shot"
    if f is None:
        tip = f" Try: {'; '.join(shot.alternatives)}." if shot.alternatives else ""
        return [f"No footage found that really shows {shot.action or what}.{tip} "
                f"Pick an alternative, or add your own file named {shot.id}.mp4."]
    out = []
    if f.match == "subject_only":
        out.append(f"Shows {what}, but not the stated action ({shot.action}): mark it for review or add real footage.")
    elif f.match == "weak":
        out.append(f"May not show {what} ({f.subject_score}/10): {f.problem or 'check it'}")
    elif f.match == "unchecked":
        out.append("Not checked by Gemini (no key): make sure it shows the right subject.")
    if f.source in ("own", "card"):
        return out
    if f.kind == "photo" and shot.camera.movement in MOVING:
        out.append(f"A still photo can't be a {shot.camera.movement.replace('_', ' ')} shot: it gets a slow zoom instead.")
    if f.kind == "video" and f.duration and shot.duration_seconds and f.duration < shot.duration_seconds:
        out.append(f"The clip is {f.duration:.0f} s for a {shot.duration_seconds:.1f} s shot: it loops.")
    width = SIZES[fmt][0]
    usable = lf.usable_width({"width": f.width, "height": f.height}, fmt == "short")
    if f.width and f.source in lf.LICENCES and usable < width * 0.95:
        out.append(f"Only {usable:.0f} px wide{' once cropped to 9:16' if fmt == 'short' else ''}: soft on screen.")
    return out


def plan_warnings(plan: DirectorPlan) -> list[str]:
    """Variety problems across the whole video (section 9.3)."""
    out = []
    run_size, run_photo = 1, 0
    for a, b in zip(plan.shots, plan.shots[1:]):
        run_size = run_size + 1 if a.shot_type == b.shot_type else 1
        if run_size == 3:
            out.append(f"Three {b.shot_type.replace('_', ' ')} shots in a row (up to {b.id}): vary the framing.")
    for s in plan.shots:
        run_photo = run_photo + 1 if s.footage and s.footage.kind == "photo" else 0
        if run_photo == 3:
            out.append(f"Three still photos in a row (up to {s.id}): the video feels like a slideshow there.")
    found = [s for s in plan.shots if s.footage]
    if plan.shots and len(found) < len(plan.shots):
        out.append(f"{len(plan.shots) - len(found)} of {len(plan.shots)} shots have no footage yet.")
    return out


# ---------- choosing ----------

def own_file(media: Path | None, shot: Shot, first_in_scene: bool) -> Path | None:
    if not media or not media.is_dir():
        return None
    for ext in (*VIDEO_EXTS, *IMAGE_EXTS):
        if (path := media / f"{shot.id}{ext}").is_file():
            return path
    if first_in_scene:
        return lf.own_media(media, int(shot.scene_id.split("-")[1]))
    return None


def queries(shot: Shot) -> list[str]:
    """The shot's searches without format words, most specific first, ending with the subject's plain name
    ("Common octopus (Octopus vulgaris)" -> "Common octopus") when the specific ones find nothing right."""
    qs = [" ".join(FORMAT_WORDS.sub(" ", q).split()) for q in (shot.footage_queries or [shot.visual_description])]
    qs.append(" ".join(re.sub(r"\(.*?\)", " ", shot.subject).split()))
    return list(dict.fromkeys(q for q in qs if q))


def sources(plan: DirectorPlan, cfg: dict) -> list[str]:
    kind = "species" if plan.project.visual_style == "cinematic_wildlife" else "footage"
    return lf.sources_for(kind, cfg)


def find(plan: DirectorPlan, media: Path | None, cfg: dict, shot_ids: list[str] | None = None, log=print,
         save=None, cancelled=lambda: False, client=None) -> DirectorPlan:
    """Footage for every shot (or `shot_ids`), skipping locked shots that already have some. `save(shot)` is called
    after each shot (to keep progress); `cancelled()` stops between shots. Returns the plan with footage."""
    import os

    import requests

    out = plan.model_copy(deep=True)
    fmt = plan.project.format
    width, portrait = SIZES[fmt][0], fmt == "short"
    libs = sources(plan, cfg)
    check = bool(cfg["footage"].get("check_subject", True)) and bool(os.getenv("GEMINI_API_KEY") or client)
    firsts = {s.scene_id: s.id for s in reversed(out.shots)}
    used = {f"{s.footage.source}-{s.footage.kind}-{s.footage.raw.get('id', '')}" for s in out.shots
            if s.footage and s.footage.source != "own"}
    lock = threading.Lock()
    todo = [s for s in out.shots if (not shot_ids or s.id in shot_ids) and not (s.locked and s.footage)]
    done = [0]

    def claim(item: dict) -> bool:
        with lock:
            if lf.key(item) in used:
                return False
            used.add(lf.key(item))
            return True

    def one(shot: Shot) -> None:
        if cancelled():
            return
        own = own_file(media, shot, firsts.get(shot.scene_id) == shot.id)
        if own:
            shot.footage = Footage(source="own", kind="photo" if own.suffix.lower() in IMAGE_EXTS else "video",
                                   file=str(own), author="you", licence="your own media", match="own")
            shot.candidates = []
        elif shot.shot_type == "graphic":
            try:
                text = next((s.on_screen_text for s in out.scenes if s.id == shot.scene_id), "")
                shot.footage, shot.candidates = graphic(shot, text, fmt, plan.project.language), []
            except (OSError, ValueError) as e:
                log(f"      ! {shot.id}: couldn't draw the graphic ({type(e).__name__})")
                shot.footage, shot.candidates = None, []
        else:
            best, tried = None, []
            for query in queries(shot):
                found = [m for m in lf.search(query, libs, width, shot.duration_seconds or 3, log, portrait)
                         if lf.key(m) not in used]
                checked, satisfied, pending, trusted = 0, False, [], not check
                for item in lf.spread(found):
                    if satisfied or checked >= (TRIES if check else 1):
                        pending.append(_footage(item, query))  # an alternative, not downloaded yet
                        continue
                    if not claim(item):
                        continue
                    try:
                        path = lf.fetch(item)
                        v = look(path, shot, client) if check else None
                    except (requests.RequestException, OSError, ValueError, RuntimeError, KeyError) as e:
                        log(f"      ! {shot.id}: couldn't use {lf.key(item)} ({type(e).__name__})")
                        with lock:
                            used.discard(lf.key(item))
                        continue
                    checked += 1
                    f = _scored(_footage(item, query), shot, v)
                    f.file = str(path)
                    rank = (TIER[f.match], -((f.subject_score or 0) + (f.action_score or 0)), -(f.quality_score or 0))
                    if best is None or rank < best[0]:
                        if best:
                            tried.append(best[1])
                            with lock:
                                used.discard(lf.key(best[1].raw))
                        best = (rank, f)
                    else:
                        tried.append(f)
                        with lock:
                            used.discard(lf.key(item))
                    satisfied = f.match in ("exact", "good") or not check
                    trusted = trusted or (f.subject_score or 0) >= PASS
                if trusted:  # this search found the real subject, so its other results are worth offering
                    tried += pending
                if best and best[1].match in ("exact", "good", "unchecked"):
                    break  # good enough: the less specific searches aren't needed
            if best and best[1].subject_score is not None and best[1].subject_score < MIN_SHOW:
                tried.append(best[1])  # the wrong subject is worse than none
                with lock:
                    used.discard(lf.key(best[1].raw))
                best = None
            shot.footage = best[1] if best else None
            ok = [t for t in tried if not (t.subject_score is not None and t.subject_score < MIN_SHOW)]
            ok.sort(key=lambda t: (t.subject_score is None, TIER[t.match], -(t.subject_score or 0)))
            shot.candidates = list({lf.key(t.raw): t for t in ok}.values())[:KEEP]
        shot.warnings = warnings_for(shot, fmt)
        with lock:
            done[0] += 1
            f = shot.footage
            if save:  # before logging: a stopped job's log raises, and this shot's footage is kept
                save(shot)
            log(f"@progress {done[0] / max(len(todo), 1):.2f} {done[0]} of {len(todo)} shots")
            log(f"      {shot.id}: " + (f"{f.source} {f.kind} [{f.match}]" if f else "no footage")
                + (f"  ! {shot.warnings[0]}" if shot.warnings else ""))

    with ThreadPoolExecutor(3) as pool:
        list(pool.map(one, todo))
    out.warnings = plan_warnings(out)
    return out


def pick(plan: DirectorPlan, shot_id: str, index: int) -> DirectorPlan:
    """Use alternative `index` for a shot (downloading it if needed); the old pick becomes an alternative and the
    shot is locked so a new search keeps the user's choice."""
    out = plan.model_copy(deep=True)
    shot = next((s for s in out.shots if s.id == shot_id), None)
    if shot is None:
        raise KeyError(shot_id)
    if not 0 <= index < len(shot.candidates):
        raise IndexError(index)
    chosen = shot.candidates.pop(index)
    if not chosen.file:
        chosen.file = str(lf.fetch(chosen.raw))
    if shot.footage and shot.footage.source != "own":
        shot.candidates.insert(0, shot.footage)
    shot.footage, shot.locked = chosen, True
    shot.warnings = [w for w in warnings_for(shot, out.project.format)
                     if not w.startswith(("May not show", "Not checked"))]  # the user looked at it
    out.warnings = plan_warnings(out)
    return out

