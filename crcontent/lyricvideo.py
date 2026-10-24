"""Lyric video tab: upload a Suno mp3 + paste its lyrics, review song.json, render. Wraps the neonmekong pipeline
(make_song.py); every song lives in songs/<slug>/ exactly as the command line expects."""
import contextlib
import json
import re
import sys
import threading
import traceback
import uuid
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from .config import ROOT

router = APIRouter()


SONGS_DIR = ROOT / "songs"   # in the data folder chosen in Settings > Storage, so it moves with the library
AUDIO_EXTS = {".mp3", ".wav"}
EDITABLE = ("title", "genre", "mood_phrase", "scene_theme", "subscribe_line", "plan", "generated_on", "playlist")
OUTPUTS = ("thumbnail.jpg", "lyric_trim.mp4", "lyric_preview.mp4", "lyric_full.mp4", "short_chorus.mp4", "instrumental.mp4")
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
    root = str(CODE_DIR)  # make_song.py sits next to the crcontent package
    if root not in sys.path:
        sys.path.insert(0, root)
    import make_song
    job = _jobs[job_id]

    def log(line: str) -> None:
        with _lock:
            job["log"].append(line)
            if line.startswith("== "):
                name = line[3:].strip()
                if name in STEPS:
                    job.update(step=STEPS.index(name), detail=name)

    with _lock:
        job["status"] = "running"
    cap = _Capture(sys.stdout, threading.get_ident(), log)
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


def _start(kind_title: str, slug: str, argv: list[str], final_step: int) -> str:
    job_id = uuid.uuid4().hex[:10]
    with _lock:
        _jobs[job_id] = {"id": job_id, "kind": "lyric_video", "status": "queued", "step": 0, "log": [],
                         "title": kind_title, "slug": slug}
    _submit(_run, job_id, argv, final_step)
    return job_id


def _detail(folder: Path) -> dict:
    sj = folder / "song.json"
    data = json.loads(sj.read_text(encoding="utf-8")) if sj.exists() else {}
    out = folder / "out"
    files = [n for n in OUTPUTS if (out / n).exists()]
    bpm_ready = bool(data.get("bpm")) and (folder / "lyrics.lrc").exists()
    from neonmekong import songjson
    return {
        "slug": folder.name,
        "title": data.get("title") or folder.name,
        "analyzed": bpm_ready,
        "song": {k: data.get(k, "") for k in EDITABLE},
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
