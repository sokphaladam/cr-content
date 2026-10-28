"""Lyric video tab: upload a Suno mp3 + paste its lyrics, review song.json, render. Wraps the neonmekong pipeline
(make_song.py); every song lives in songs/<slug>/ exactly as the command line expects."""
import contextlib
import subprocess
import json
import re
import sys
import threading
import time
import shutil
import traceback
import uuid
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field

from . import progress
from .config import CODE_DIR, ROOT

router = APIRouter()


SONGS_DIR = ROOT / "songs"   # in the data folder chosen in Settings > Storage, so it moves with the library
AUDIO_EXTS = {".mp3", ".wav"}
EDITABLE = ("title", "genre", "mood_phrase", "scene_theme", "subscribe_line", "plan", "generated_on", "playlist",
            "lyric_style", "mood_grade", "beat_pulse", "pulse_parts", "pulse_when", "neon_intro", "now_playing")
OUTPUTS = ("thumbnail.jpg", "lyric_full.mp4", "short_chorus.mp4", "instrumental.mp4")
STEPS = ("analyze", "text", "checklist", "thumbnail", "video", "short", "instrumental")

_jobs = None      # web.jobs, set by bind()
_lock = None
_submit = None


def bind(jobs: dict, lock, executor) -> None:
    """web.py hands over its job table and render queue, so these jobs show up in /api/jobs/<id> like any other."""
    global _jobs, _lock, _submit
    _jobs, _lock, _submit = jobs, lock, executor.submit


class _Capture:
    """sys.stdout stand-in: lines printed by the job's thread go to its log; other threads still reach the console."""

    def __init__(self, real, thread_id: int, log):
        self.real, self.thread_id, self.log, self.buf = real, thread_id, log, ""

    def write(self, text: str) -> int:
        if threading.get_ident() != self.thread_id:
            return self.real.write(text)
        self.buf += text
        while "\n" in self.buf:
            line, self.buf = self.buf.split("\n", 1)
            if line.strip():
                self.log(line)
        return len(text)

    def flush(self) -> None:
        self.real.flush()


def _folder(slug: str) -> Path:
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", slug):
        raise HTTPException(400, "Bad song name.")
    folder = SONGS_DIR / slug
    if not folder.is_dir():
        raise HTTPException(404, "Song not found.")
    return folder


def _run(job_id: str, argv: list[str], final_step: int) -> None:
    job = _jobs[job_id]
    try:
        root = str(CODE_DIR)  # make_song.py sits next to the crcontent package
        if root not in sys.path:
            sys.path.insert(0, root)
        import make_song
    except Exception as e:  # a failure here must reach the page, not vanish in the worker thread
        traceback.print_exc()
        with _lock:
            job.update(status="error", error=f"Could not start: {e.__class__.__name__}: {e}")
        return

    def log(line: str) -> None:
        with _lock:
            report = progress.parse(line)
            if report:  # a step's own progress: shown as the bar, not as log text
                job.update(progress=report[0], detail=report[1])
                return
            job["log"].append(line)
            if line.startswith("== "):
                name = line[3:].strip()
                if name in STEPS:
                    job.update(step=STEPS.index(name), detail=name, progress=None)

    with _lock:
        job["status"] = "running"
    cap = _Capture(sys.stdout, threading.get_ident(), log)
    progress.enabled = True
    try:
        with contextlib.redirect_stdout(cap):
            code = make_song.main(argv)
        if code:
            tail = [x for x in job["log"] if x.strip()][-1:] or ["The pipeline stopped."]
            raise RuntimeError(tail[0])
        with _lock:
            job.update(status="done", step=final_step)
    except Exception as e:
        traceback.print_exc()
        with _lock:
            job.update(status="error", error=str(e).strip().splitlines()[-1] if str(e).strip() else repr(e))
    finally:
        progress.enabled = False


def _start(kind_title: str, slug: str, argv: list[str], final_step: int) -> str:
    job_id = uuid.uuid4().hex[:10]
    with _lock:
        _jobs[job_id] = {"id": job_id, "kind": "lyric_video", "status": "queued", "step": 0, "log": [],
                         "title": kind_title, "slug": slug}
    _submit(_run, job_id, argv, final_step)
    return job_id


def _background_prompt(data: dict, lyrics_lrc: str) -> str:
    """A prompt for a text-to-video tool: a looping background that fits the song's mood and what it is about."""
    from types import SimpleNamespace

    from .pipeline import suggest_background_prompt

    lyrics = " ".join(re.sub(r"\[[^\]]*\]", " ", lyrics_lrc).split())  # drop the [00:12.30] times and [Verse] tags
    song = SimpleNamespace(title=data.get("title") or "",
                           mood=f"{data.get('mood_phrase') or ''}, {data.get('genre') or ''}")
    return suggest_background_prompt(song, data.get("scene_theme") or "", lyrics)


def _audio(folder: Path) -> Path | None:
    from neonmekong import analyze

    return analyze.find_audio(folder)[0]


def _detail(folder: Path) -> dict:
    sj = folder / "song.json"
    data = json.loads(sj.read_text(encoding="utf-8")) if sj.exists() else {}
    out = folder / "out"
    files = [n for n in OUTPUTS if (out / n).exists()]
    bpm_ready = bool(data.get("bpm")) and (folder / "lyrics.lrc").exists()
    lrc = (folder / "lyrics.lrc").read_text(encoding="utf-8") if (folder / "lyrics.lrc").exists() else ""
    from neonmekong import mood, songjson
    from neonmekong import thumbnail
    own = thumbnail.custom_background_file(folder)
    audio = _audio(folder)
    return {
        "background": own.name if own else "",
        "video_prompt": _background_prompt(data, lrc) if data else "",
        "slug": folder.name,
        "audio": audio.name if audio else "",
        "title": data.get("title") or folder.name,
        "analyzed": bpm_ready,
        "song": {k: data.get(k, "") for k in EDITABLE},
        "sections": [{"tag": x.get("tag", ""), "kind": x.get("kind", ""), "start": x["start"], "end": x["end"]}
                     for x in data.get("sections", []) if "start" in x and "end" in x],
        "styles": mood.LYRIC_STYLES,
        "suggestion": mood.suggest(data) if data else None,
        "grades": mood.GRADES,
        "pulse": {"levels": mood.PULSE_LEVELS, "parts": mood.PULSE_PARTS, "when": mood.PULSE_WHEN},
        "chorus": data.get("chorus") or {"start": None, "end": None},
        "bpm": data.get("bpm"),
        "duration": data.get("duration"),
        "vocal_start": data.get("vocal_start"),
        "palette": data.get("palette") or [],
        "warnings": songjson.warnings(data) if data else [],
        "lyrics": (folder / "lyrics.lrc").read_text(encoding="utf-8") if (folder / "lyrics.lrc").exists() else "",
        "files": files,
        "upload_text": (folder / "upload.txt").read_text(encoding="utf-8") if (folder / "upload.txt").exists() else "",
        "has_instrumental": any((folder / n).exists() for n in ("instrumental.wav", "instrumental.mp3")),
    }


@router.get("/api/lyricvideo")
def list_songs():
    SONGS_DIR.mkdir(exist_ok=True)
    folders = [f for f in SONGS_DIR.iterdir() if f.is_dir() and (f / "suno.txt").exists()]
    folders.sort(key=lambda f: f.stat().st_mtime, reverse=True)
    rows = []
    for f in folders:
        d = _detail(f)
        rows.append({"slug": d["slug"], "title": d["title"], "analyzed": d["analyzed"], "rendered": bool(d["files"])})
    return rows


@router.post("/api/lyricvideo")
def create_song(audio: UploadFile = File(...), lyrics: str = Form(...), title: str = Form(""), style: str = Form("")):
    from neonmekong import songjson
    ext = Path(audio.filename or "").suffix.lower()
    if ext not in AUDIO_EXTS:
        raise HTTPException(400, "Upload the song as an mp3 or wav file.")
    if not lyrics.strip():
        raise HTTPException(400, "Paste the lyrics first.")
    title = title.strip() or Path(audio.filename or "").stem.replace("_", " ").strip() or "Untitled"
    base = songjson.slugify(title) or "song"
    slug, n = base, 2
    while (SONGS_DIR / slug).exists():
        slug, n = f"{base}-{n}", n + 1
    folder = SONGS_DIR / slug
    folder.mkdir(parents=True)
    with open(folder / f"audio{ext}", "wb") as out:
        while chunk := audio.file.read(1 << 20):
            out.write(chunk)
    header = f"Title: {title}\n" + (f"Style: {style.strip()}\n" if style.strip() else "")
    (folder / "suno.txt").write_text(header + "\n" + lyrics.strip() + "\n", encoding="utf-8")
    return {"slug": slug, "job": _start(f"Reading {title}", slug, ["all", str(folder)], len(STEPS))}


@router.get("/api/lyricvideo/{slug}")
def get_song(slug: str):
    return _detail(_folder(slug))


@router.delete("/api/lyricvideo/{slug}")
def delete_song(slug: str):
    """Delete the song's whole folder: its audio, lyrics, pictures and renders. Not while it is being made."""
    import shutil

    folder = _folder(slug)
    with _lock:
        if any(j.get("kind") == "lyric_video" and j.get("slug") == slug and j["status"] in ("queued", "running")
               for j in _jobs.values()):
            raise HTTPException(409, "It's being made right now: wait until it's done.")
    shutil.rmtree(folder)
    return {"deleted": slug}


class SongEdit(BaseModel):
    song: dict[str, str] = {}
    chorus_start: float | None = None
    chorus_end: float | None = None


@router.put("/api/lyricvideo/{slug}")
def edit_song(slug: str, req: SongEdit):
    from neonmekong import songjson
    folder = _folder(slug)
    sj = folder / "song.json"
    if not sj.exists():
        raise HTTPException(400, "The song hasn't been read yet.")
    data = songjson.load(sj)
    for k, v in req.song.items():
        if k in EDITABLE:
            data[k] = v.strip()
    if req.chorus_start is not None and req.chorus_end is not None:
        if req.chorus_end <= req.chorus_start:
            raise HTTPException(400, "The chorus must end after it starts.")
        data["chorus"] = {"start": req.chorus_start, "end": req.chorus_end}
    songjson.save(sj, data, force=True)
    return _detail(folder)


def _preview_over(style: str, grade: str, neon: bool, playing: bool, pulse: str = "", parts: str = "",
                  when: str = "") -> dict:
    from neonmekong import mood

    return {"lyric_style": mood.pick(style, mood.LYRIC_STYLES, mood.DEFAULT_STYLE),
            "mood_grade": mood.pick(grade, mood.GRADES, mood.DEFAULT_GRADE),
            "neon_intro": "1" if neon else "", "now_playing": "1" if playing else "",
            "beat_pulse": pulse, "pulse_parts": parts, "pulse_when": when}


@router.get("/api/lyricvideo/{slug}/preview/stream")
def preview_stream(slug: str, t: float = 0.0, style: str = "", grade: str = "", neon: bool = False,
                   playing: bool = False, fps: int = 20, pulse: str = "", parts: str = "", when: str = ""):
    """The lyric video playing live from second `t`, as a motion-JPEG stream (an <img> shows it), drawn in real time at
    draft size. Frames follow the clock: a slow computer skips frames instead of falling behind the song's audio,
    which the page plays alongside. Ends with the song; closing the page's image stops it."""
    import cv2
    from fastapi.responses import StreamingResponse

    from neonmekong import lyricvideo

    folder = _folder(slug)
    if not _detail(folder)["analyzed"]:
        raise HTTPException(400, "The song hasn't been read yet.")
    try:
        scene = lyricvideo.build_scene(folder, "full", draft=True, over=_preview_over(style, grade, neon, playing, pulse, parts, when))
    except (OSError, ValueError, KeyError) as e:
        raise HTTPException(400, str(e))
    end = scene.v.duration
    fps = min(max(fps, 5), 30)

    def frames():
        start, last = time.monotonic(), -1
        while True:
            now = max(t, 0.0) + (time.monotonic() - start)
            if now >= end:
                return
            n = int(now * fps)
            if n == last:   # drawn this one already: wait for the next
                time.sleep(max((n + 1) / fps - now, 0.001))
                continue
            last = n
            ok, buf = cv2.imencode(".jpg", scene.frame(now), [cv2.IMWRITE_JPEG_QUALITY, 78])
            if ok:
                yield b"--frame\r\nContent-Type: image/jpeg\r\nContent-Length: " + str(len(buf)).encode() + b"\r\n\r\n" + buf.tobytes() + b"\r\n"

    return StreamingResponse(frames(), media_type="multipart/x-mixed-replace; boundary=frame",
                             headers={"Cache-Control": "no-store"})


@router.get("/api/lyricvideo/{slug}/preview")
def preview_frame(slug: str, t: float = 0.0, style: str = "", grade: str = "", neon: bool = False,
                  playing: bool = False, pulse: str = "", parts: str = "", when: str = ""):
    """One frame of the lyric video at `t` seconds with this lyric style and mood grade (not saved)."""
    import cv2
    from fastapi.responses import Response

    from neonmekong import lyricvideo, mood

    folder = _folder(slug)
    if not _detail(folder)["analyzed"]:
        raise HTTPException(400, "The song hasn't been read yet.")
    over = _preview_over(style, grade, neon, playing, pulse, parts, when)
    try:
        scene = lyricvideo.build_scene(folder, "full", draft=True, over=over)
        frame = scene.frame(min(max(t, 0.0), max(scene.v.duration - 0.1, 0.0)))
    except (OSError, ValueError, KeyError, FileNotFoundError) as e:
        raise HTTPException(400, str(e))
    ok, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 88])
    return Response(buf.tobytes(), media_type="image/jpeg", headers={"Cache-Control": "no-store"})


# ---------- the video's pictures: one per sung section, plus the cover (the background) ----------

def _pictures(folder: Path) -> dict:
    """The picture plan with each slot's file as a url-ready name; suggested the first time."""
    from neonmekong import pictures, songjson, traditions

    plan = pictures.with_motions(pictures.load(folder))
    if not plan["slots"]:
        data = songjson.load(folder / "song.json")
        plan = pictures.suggest(folder, data, ai=True)   # one Gemini call, then kept in pictures.json
        if plan["slots"]:
            pictures.save(folder, plan)
    from neonmekong import thumbnail
    own = thumbnail.custom_background_file(folder)
    from . import coverloop

    data = songjson.load(folder / "song.json")
    lrc = (folder / "lyrics.lrc").read_text(encoding="utf-8") if (folder / "lyrics.lrc").exists() else ""
    return {**plan, "cover": own.name if own else "", **coverloop.state(folder, _loop_subject(data)),
            "video_prompt": _background_prompt(data, lrc), "other_loops": _other_loops(folder), "cover_prompt": plan.get("cover_prompt", ""),
            "meaning": plan.get("meaning", ""), "motions": pictures.MOTIONS,
            "traditions": traditions.catalog(), "tradition": traditions.pick(plan.get("tradition")),
            "cover_motion": plan.get("cover_motion", ""), "custom_look": plan.get("custom_look", ""), "custom_avoid": plan.get("custom_avoid", ""),
            "tradition_suggested": traditions.suggest(data)}


@router.get("/api/lyricvideo/{slug}/pictures")
def get_pictures(slug: str):
    return _pictures(_folder(slug))


class PicturesEdit(BaseModel):
    prompts: dict[str, str] = {}   # slot id -> prompt
    motions: dict[str, str] = {}   # slot id -> camera move ("" = the slow drift)
    cover_mode: str | None = None  # "picture" | "animated": which cover the video and the thumbnail use
    loop_prompt: str | None = None  # what the animated cover shows ("" = the suggestion again)
    loop_movement: str | None = None  # how a character loop moves ("" = the suggestion again)
    loop_regions: list[dict] | None = None  # the parts of the cover a living loop moves (living.clean)


@router.put("/api/lyricvideo/{slug}/pictures")
def edit_pictures(slug: str, req: PicturesEdit):
    from neonmekong import pictures

    folder = _folder(slug)
    _pictures(folder)   # makes the plan the first time
    plan = pictures.with_motions(pictures.load(folder))
    for s in plan["slots"]:
        if s["id"] in req.prompts and req.prompts[s["id"]].strip() != s["prompt"]:
            s.update(prompt=req.prompts[s["id"]].strip(), edited=True)   # your words: new suggestions keep them
    from . import coverloop

    try:
        coverloop.edit(folder, req.cover_mode, req.loop_prompt, req.loop_movement, req.loop_regions)
    except ValueError as e:
        raise HTTPException(400, str(e))
    if "cover" in req.motions:
        if req.motions["cover"] not in pictures.MOTIONS:
            raise HTTPException(400, "Unknown camera move.")
        plan["cover_motion"] = req.motions["cover"]
    for s in plan["slots"]:
        if s["id"] in req.motions:
            if req.motions[s["id"]] not in pictures.MOTIONS:
                raise HTTPException(400, "Unknown camera move.")
            s.update(motion=req.motions[s["id"]], motion_edited=True)   # your choice: new suggestions keep it
    if "cover" in req.prompts and req.prompts["cover"].strip() != plan.get("cover_prompt"):
        plan.update(cover_prompt=req.prompts["cover"].strip(), cover_edited=True)
    pictures.save(folder, plan)
    return _pictures(folder)


@router.post("/api/lyricvideo/{slug}/pictures/{pid}/motion-clip")
def motion_clip(slug: str, pid: str, move: str | None = None):
    """A few seconds of this section's picture with its camera move (or `move`, to try one): {file} in the song folder."""
    from neonmekong import lyricvideo, pictures

    folder = _folder(slug)
    if move is not None and move not in pictures.MOTIONS:
        raise HTTPException(400, "Unknown camera move.")
    if pid != "cover" and not re.fullmatch(r"s\d+", pid):
        raise HTTPException(400, "Bad picture id.")
    name = f"{pictures.DIR}/motion-{pid}.mp4"
    try:
        lyricvideo.move_clip(folder, pid, folder / name, move=move)
    except ValueError as e:
        raise HTTPException(400, f"Draw or upload this section's picture first: {e}.")
    except (RuntimeError, OSError) as e:
        raise HTTPException(500, str(e)[-300:])
    return {"file": name}


def _loop_subject(data: dict) -> str:
    from . import coverloop

    return coverloop.suggest(data.get("mood_phrase") or "", data.get("scene_theme") or "")


def _other_loops(folder: Path) -> list[dict]:
    """Songs of both editors with an animated cover to reuse here; keys are "lyric:<slug>" or "video:<name>"."""
    from . import coverloop
    from .config import OUTPUT_DIR

    def title(f):
        try:
            return json.loads((f / "song.json").read_text(encoding="utf-8")).get("title") or f.name
        except (OSError, ValueError):
            return f.name

    rows = [{**r, "slug": f"lyric:{r['slug']}"} for r in coverloop.others(sorted(SONGS_DIR.iterdir()), folder, title)]
    if OUTPUT_DIR.exists():
        rows += [{**r, "slug": f"video:{r['slug']}"} for r in coverloop.others(sorted(OUTPUT_DIR.iterdir()), folder, title)]
    return rows


def loop_source(key: str) -> Path:
    """The song folder named by an _other_loops key."""
    from .config import OUTPUT_DIR

    kind, _, name = key.partition(":")
    if kind == "video":
        folder = (OUTPUT_DIR / name).resolve()
        if folder.parent != OUTPUT_DIR.resolve() or not folder.is_dir():
            raise HTTPException(404, "Song not found.")
        return folder
    return _folder(name if kind == "lyric" else key)


def _loop_call(folder: Path, work) -> None:
    """Run a coverloop step, its errors as the page's messages."""
    from . import llm

    try:
        work()
    except ValueError as e:
        raise HTTPException(400, str(e))
    except FileNotFoundError as e:
        raise HTTPException(404, str(e))
    except (llm.APIError, RuntimeError) as e:
        raise HTTPException(502, f"The animated cover could not be drawn: {str(e)[-300:]}")
    except (OSError, subprocess.CalledProcessError) as e:
        raise HTTPException(500, f"The animated cover could not be saved: {str(getattr(e, 'stderr', e))[-300:]}")


@router.post("/api/lyricvideo/{slug}/loop")
def draw_loop(slug: str, again: bool = False):
    """Gemini draws the song's cover as an animated loop (<song>/loop.mp4); it plays behind the lyrics wherever the
    cover shows. One Gemini request, a minute or two."""
    from neonmekong import songjson

    from . import coverloop

    folder = _folder(slug)
    _loop_call(folder, lambda: coverloop.draw(folder, _loop_subject(songjson.load(folder / "song.json")), again))
    return _pictures(folder)


class GpuLoop(BaseModel):
    effects: list[str] | None = None  # what moves (coverloop.EFFECTS); None = the last choice
    use_cover: bool = False           # bring the song's cover picture to life instead of drawing a new one
    again: bool = False               # a new drawing and new particles
    motion: str = "light"             # "light" (particles over the still) | "character" (the picture itself moves)
    #                                   | "parallax" (a slow 2.5D camera over the picture)
    intensity: int = Field(40, ge=0, le=100)   # parallax strength


@router.post("/api/lyricvideo/{slug}/loop/gpu")
def gpu_loop(slug: str, req: GpuLoop):
    """The animated cover drawn and brought to life on this computer's GPU: free, no Gemini, a minute or two."""
    from neonmekong import songjson, thumbnail

    from . import coverloop

    folder = _folder(slug)
    picture = thumbnail.custom_background_file(folder) if req.use_cover else None
    if req.use_cover and not picture:
        raise HTTPException(400, "Draw or upload the cover picture first (Picture), then bring it to life here.")
    effects = req.effects if req.effects is not None else coverloop.meta(folder).get("effects")
    suggested = _loop_subject(songjson.load(folder / "song.json"))
    _start_gpu(folder, lambda log, progress: coverloop.animate(folder, suggested, picture, effects, req.again, log,
                                                              req.motion, progress, req.intensity), picture is None)
    return {**_pictures(folder), "job": coverloop.status(folder)}


def _start_gpu(folder: Path, work, drawing: bool) -> None:
    """Start a GPU loop job, its setup problems as the page's messages before anything runs."""
    from . import coverloop

    try:
        if drawing:
            coverloop.gpu_check()
        coverloop.start(folder, work)
    except ValueError as e:
        raise HTTPException(400, str(e))
    except RuntimeError as e:
        raise HTTPException(409, str(e))


class LivingPreview(BaseModel):
    regions: list[dict]


@router.post("/api/lyricvideo/{slug}/loop/preview")
def preview_loop(slug: str, req: LivingPreview):
    """A quick small preview of a living loop of the song's cover with `regions` moving (saved as the song's regions;
    the loop itself is made with motion "living")."""
    from neonmekong import thumbnail

    from . import coverloop, living

    folder = _folder(slug)
    picture = thumbnail.custom_background_file(folder)
    if not picture:
        raise HTTPException(400, "Draw or upload the cover picture first (Picture), then mark what moves.")
    try:
        coverloop.edit(folder, regions=req.regions)
        if Path(picture).resolve() != (folder / coverloop.STILL).resolve():
            shutil.copy(picture, folder / coverloop.STILL)
        living.preview(folder / coverloop.STILL, folder / living.PREVIEW, req.regions)
    except ValueError as e:
        raise HTTPException(400, str(e))
    except RuntimeError as e:
        raise HTTPException(500, str(e))
    return {**_pictures(folder), "preview": living.PREVIEW}


@router.get("/api/lyricvideo/{slug}/loop/status")
def gpu_loop_status(slug: str):
    from . import coverloop

    return coverloop.status(_folder(slug))


@router.post("/api/lyricvideo/{slug}/loop/upload")
def upload_loop(slug: str, video: UploadFile = File(...)):
    """Your own looping clip as the animated cover (made in another tool from the suggested video prompt)."""
    from . import coverloop

    folder = _folder(slug)
    _loop_call(folder, lambda: coverloop.upload(folder, video.filename or "", video.file))
    return _pictures(folder)


@router.post("/api/lyricvideo/{slug}/loop/from/{source}")
def copy_loop(slug: str, source: str):
    """Use another song's animated cover for this one: no Gemini request, and one room becomes the channel's look."""
    from . import coverloop

    folder = _folder(slug)
    _loop_call(folder, lambda: coverloop.copy(folder, loop_source(source)))
    return _pictures(folder)


@router.delete("/api/lyricvideo/{slug}/loop")
def remove_loop(slug: str):
    from . import coverloop

    folder = _folder(slug)
    coverloop.remove(folder)
    return _pictures(folder)


@router.get("/api/lyricvideo/{slug}/thumbnail/preview")
def thumbnail_preview(slug: str):
    """The thumbnail as the render will make it from the cover in use (nothing is saved)."""
    import tempfile

    from fastapi.responses import Response

    from neonmekong import songjson, thumbnail

    folder = _folder(slug)
    with tempfile.TemporaryDirectory() as tmp:
        out = thumbnail.render(songjson.load(folder / "song.json"), Path(tmp) / "thumbnail.jpg")
        body = out.read_bytes()
    return Response(body, media_type="image/jpeg", headers={"Cache-Control": "no-store"})


@router.post("/api/lyricvideo/{slug}/pictures/motion/suggest")
def suggest_motions(slug: str):
    """Every section's camera move set to what suits it (moves you picked are replaced)."""
    from neonmekong import pictures

    folder = _folder(slug)
    _pictures(folder)
    plan = pictures.load(folder)
    plan.pop("cover_motion", None)
    for s in plan["slots"]:
        s.pop("motion", None)
        s.pop("motion_edited", None)
    pictures.save(folder, pictures.with_motions(plan))
    return _pictures(folder)


@router.post("/api/lyricvideo/{slug}/pictures/reset")
def reset_pictures(slug: str, prompts_only: bool = False):
    """New prompts written from what the lyrics mean (pictures you made stay; prompts you edited stay too when
    prompts_only is set)."""
    from neonmekong import pictures, songjson

    folder = _folder(slug)
    old = pictures.load(folder)
    if not prompts_only:   # only the pictures stay; every prompt, edited or not, is written again
        for s in old["slots"]:
            s.pop("edited", None)
        old.pop("cover_edited", None)
    plan = pictures.suggest(folder, songjson.load(folder / "song.json"), keep=old, ai=True)
    pictures.save(folder, plan)
    return _pictures(folder)


def _slot(folder: Path, pid: str) -> tuple[dict, dict]:
    from neonmekong import pictures

    plan = pictures.load(folder)
    slot = next((s for s in plan["slots"] if s["id"] == pid), None)
    if not slot:
        raise HTTPException(404, "No such picture.")
    return plan, slot


def _put_picture(folder: Path, pid: str, source: Path, ext: str) -> None:
    """Keep `source` as the picture of slot `pid` (pid "cover": the song's background)."""
    import shutil

    from neonmekong import pictures

    if pid == "cover":
        _clear_background(folder)
        shutil.copy(source, folder / f"background{ext}")
        from . import coverloop
        coverloop.edit(folder, "picture")   # a new cover picture is the one in use
        return
    plan, slot = _slot(folder, pid)
    (folder / pictures.DIR).mkdir(exist_ok=True)
    for old in (folder / pictures.DIR).glob(f"{pid}-*"):
        old.unlink(missing_ok=True)
    name = f"{pid}-{int(time.time())}{ext}"   # a new name each time, so the page and the render never show a stale one
    shutil.copy(source, folder / pictures.DIR / name)
    slot["file"] = name
    pictures.save(folder, plan)


@router.post("/api/lyricvideo/{slug}/pictures/{pid}/upload")
def upload_picture(slug: str, pid: str, image: UploadFile = File(...)):
    import tempfile
    from PIL import Image

    folder = _folder(slug)
    ext = Path(image.filename or "").suffix.lower()
    if ext not in BACKGROUND_EXTS:
        raise HTTPException(400, "Upload a png, jpg or webp picture.")
    with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
        while chunk := image.file.read(1 << 20):
            tmp.write(chunk)
    path = Path(tmp.name)
    try:
        with Image.open(path) as im:
            im.verify()
        _put_picture(folder, pid, path, ext)
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(400, "That file isn't a picture I can read.")
    finally:
        path.unlink(missing_ok=True)
    return _pictures(folder)


class DrawReq(BaseModel):
    prompt: str
    style: str
    seed: int = 0
    tradition: str = ""   # an art tradition (neonmekong/traditions.py) for the anime look; kept for the whole song
    custom_look: str = ""      # for tradition "custom": the user's own words for the look
    custom_avoid: str = ""     # ...and what it must not look like


_draws: dict[str, dict] = {}        # slug -> the picture being drawn (or the last one drawn): what the page polls
_draw_lock = threading.Lock()       # one picture at a time: the GPU draws one anyway


def _draw_state(slug: str, **kw) -> None:
    with _lock:
        _draws.setdefault(slug, {}).update(kw)


def _draw_job(slug: str, folder: Path, pid: str, req: DrawReq, seed: int) -> None:
    from . import imagegen
    from .config import frame_size
    from .pipeline import draw_checked

    def log(line: str) -> None:   # the generator says what it is doing: loading the model, downloading...
        text = line.strip()
        if "download" in text.lower():
            _draw_state(slug, phase="loading", text="Downloading the model (once)…")
        elif "loading" in text.lower() or "moving" in text.lower():
            _draw_state(slug, phase="loading", text="Loading the model onto the GPU…")

    def step(phase: str, done: int, total: int) -> None:
        _draw_state(slug, phase=phase, done=done, total=total,
                    text=f"{'Drawing' if phase == 'drawing' else 'Adding detail'} {done}/{total}")

    _draw_state(slug, phase="queued", text="Waiting for the GPU…", done=0, total=0)
    with _draw_lock:
        imagegen.step_hook = step
        try:
            _draw_state(slug, phase="loading", text="Getting ready…", done=0, total=0)
            prompt = req.prompt
            if req.style == "anime":   # the anime model reads tags, not sentences: people vanish from a long description
                _draw_state(slug, phase="loading", text="Writing the prompt as tags for the anime model…")
                prompt = imagegen.anime_tags(prompt, log=log)
            avoid = imagegen.NO_LETTERS
            if req.style in ("anime", "flat"):   # in the manner of the song's chosen tradition (Ghibli-like, lofi room...)
                from neonmekong import traditions
                prompt = traditions.apply(prompt, req.tradition, req.custom_look)
                avoid = ", ".join(x for x in (avoid, traditions.avoid(req.tradition), traditions.clean(req.custom_avoid)
                                              if req.tradition == traditions.CUSTOM else "") if x)
            # a lyric video's picture never holds writing: the lyrics are drawn over it
            path, _, _, _ = draw_checked(prompt, req.style, frame_size("16:9"), seed=seed, avoid=avoid, log=log)
            _put_picture(folder, pid, path, path.suffix.lower() or ".png")
            if req.style in ("anime", "flat"):   # every picture of the song follows the same tradition
                from neonmekong import pictures, traditions
                plan = pictures.load(folder)
                plan["tradition"] = traditions.pick(req.tradition)
                if plan["tradition"] == traditions.CUSTOM:
                    plan["custom_look"], plan["custom_avoid"] = traditions.clean(req.custom_look), traditions.clean(req.custom_avoid)
                pictures.save(folder, plan)
            if pid != "cover":
                from neonmekong import pictures
                plan, slot = _slot(folder, pid)
                if req.prompt.strip() != slot["prompt"]:
                    slot.update(prompt=req.prompt.strip(), edited=True)
                pictures.save(folder, plan)
            _draw_state(slug, state="done", phase="done", text="Done")
        except Exception as e:
            traceback.print_exc()
            _draw_state(slug, state="error", phase="error", text="", error=str(e).strip().splitlines()[-1] if str(e).strip() else repr(e))
        finally:
            imagegen.step_hook = None
            imagegen.unload_later()   # keep the model warm while you're drawing, free the GPU when you stop


@router.post("/api/lyricvideo/{slug}/pictures/{pid}/draw")
def draw_picture(slug: str, pid: str, req: DrawReq):
    """Start drawing this picture on this computer's GPU (free) from its prompt, 16:9. Returns at once: the page
    follows it with GET .../draw-status (the model loading, then each drawing step)."""
    from . import imagegen
    from .web import _art_check

    folder = _folder(slug)
    if pid != "cover":
        _slot(folder, pid)
    if not req.prompt.strip():
        raise HTTPException(400, "Describe the picture first.")
    _art_check(req.style)
    with _lock:
        if _draws.get(slug, {}).get("state") == "running":
            raise HTTPException(409, "A picture of this song is already being drawn.")
        _draws[slug] = {"state": "running", "pid": pid, "phase": "queued", "text": "Starting…", "done": 0, "total": 0,
                        "error": ""}
    seed = req.seed or imagegen.default_seed(req.prompt)
    threading.Thread(target=_draw_job, args=(slug, folder, pid, req, seed), daemon=True).start()
    return {"started": pid}


@router.get("/api/lyricvideo/{slug}/pictures/draw-status")
def draw_status(slug: str):
    """{state: idle|running|done|error, pid, phase, text, done, total, error}: the picture being drawn now."""
    _folder(slug)
    with _lock:
        return dict(_draws.get(slug) or {"state": "idle", "pid": "", "phase": "", "text": "", "done": 0, "total": 0,
                                         "error": ""})


class RewriteReq(BaseModel):
    prompt: str
    instruction: str


@router.post("/api/lyricvideo/{slug}/pictures/{pid}/rewrite")
def rewrite_prompt(slug: str, pid: str, req: RewriteReq):
    """The prompt changed the way you asked ("make it night", "add a lantern"): Gemini rewrites it and keeps the rest;
    without Gemini your words are added to the end."""
    import json as _json

    from .config import LLM_MODEL
    from .script import make_client

    _folder(slug)
    ask = req.instruction.strip()
    if not ask:
        raise HTTPException(400, "Say what to change.")
    schema = {"type": "object", "properties": {"prompt": {"type": "string"}}, "required": ["prompt"],
              "additionalProperties": False}
    try:
        response = make_client().beta.messages.create(
            model=LLM_MODEL, max_tokens=800,
            system="You edit text-to-image prompts. Apply the requested change and keep everything else (style, "
                   "palette, 16:9, empty centre for lyrics, no text in the picture). Reply with the new prompt only, "
                   "in English, under 70 words.",
            output_config={"effort": "low", "format": {"type": "json_schema", "schema": schema}},
            messages=[{"role": "user", "content": f"Prompt:\n{req.prompt}\n\nChange: {ask}"}])
        text = _json.loads(next(b.text for b in response.content if b.type == "text"))["prompt"].strip()
        if text:
            return {"prompt": text, "by": "Gemini"}
    except Exception as e:
        print(f"      ! prompt rewrite without Gemini ({type(e).__name__})")
    return {"prompt": f"{req.prompt.strip().rstrip('.')}. {ask[:1].upper() + ask[1:]}", "by": "added to the end"}


@router.delete("/api/lyricvideo/{slug}/pictures/{pid}")
def remove_picture(slug: str, pid: str):
    from neonmekong import pictures

    folder = _folder(slug)
    if pid == "cover":
        _clear_background(folder)
    else:
        plan, slot = _slot(folder, pid)
        if slot.get("file"):
            (folder / pictures.DIR / slot["file"]).unlink(missing_ok=True)
        slot["file"] = ""
        pictures.save(folder, plan)
    return _pictures(folder)


BACKGROUND_EXTS = {".png", ".jpg", ".jpeg", ".webp"}


@router.post("/api/lyricvideo/{slug}/background")
def set_background(slug: str, image: UploadFile = File(...)):
    """Use this picture as the video's background (and the thumbnail's) instead of the drawn neon city."""
    from PIL import Image
    folder = _folder(slug)
    ext = Path(image.filename or "").suffix.lower()
    if ext not in BACKGROUND_EXTS:
        raise HTTPException(400, "Upload the background as a png, jpg or webp picture.")
    tmp = folder / f"background.new{ext}"
    with open(tmp, "wb") as out:
        while chunk := image.file.read(1 << 20):
            out.write(chunk)
    try:
        with Image.open(tmp) as im:
            im.verify()
    except Exception:
        tmp.unlink(missing_ok=True)
        raise HTTPException(400, "That file isn't a picture I can read.")
    _clear_background(folder)
    tmp.replace(folder / f"background{ext}")
    return _detail(folder)


@router.delete("/api/lyricvideo/{slug}/background")
def remove_background(slug: str):
    folder = _folder(slug)
    _clear_background(folder)
    return _detail(folder)


def _clear_background(folder: Path) -> None:
    for ext in BACKGROUND_EXTS:
        (folder / f"background{ext}").unlink(missing_ok=True)


class RenderReq(BaseModel):
    draft: bool = False        # half size, 15 fps: a quick look before the full render
    ai: str = "template"       # template | gemini
    no_video: bool = False


@router.post("/api/lyricvideo/{slug}/render")
def render_song(slug: str, req: RenderReq):
    folder = _folder(slug)
    if not _detail(folder)["analyzed"]:
        raise HTTPException(400, "The song hasn't been read yet.")
    if req.ai not in ("template", "gemini"):
        raise HTTPException(400, "Unknown text writer.")
    argv = ["all", "--go", "--ai", req.ai]
    if req.draft:
        argv.append("--draft")
    if req.no_video:
        argv.append("--no-video")
    return {"job": _start(f"Rendering {slug}", slug, argv + [str(folder)], len(STEPS))}


@router.post("/api/lyricvideo/{slug}/reanalyze")
def reanalyze(slug: str):
    folder = _folder(slug)
    return {"job": _start(f"Reading {slug}", slug, ["all", "--reanalyze", str(folder)], len(STEPS))}
