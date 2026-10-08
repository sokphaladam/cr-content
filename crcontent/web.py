"""Local web app: FastAPI backend wrapping the pipeline, serving the UI in /web."""
import hashlib
import json
import os
import shutil
import threading
import traceback
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict
from datetime import datetime
from functools import lru_cache
from pathlib import Path

import anthropic
import requests
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import drafts
from .captions import THUMB_STYLES
from .config import ASSETS_DIR, CACHE_DIR, CODE_DIR, DRAFTS_DIR, LANGS, OUTPUT_DIR, ROOT
from .lyrics import SongScript, generate_song
from .align import lines_from_json, load_lines, save_lines
from .pipeline import (AUDIO_EXTS, import_song, make_music_video, make_song, make_thumbnail, make_video,
                       song_versions, split_song_renders, suggest_thumbnails, sync_lyrics)
from .render import duration
from .importer import import_script
from .script import VideoScript, generate_script, suggest_queries, translate_script
from .song import elevenlabs_key
from .tts import list_voices, synthesize
from .visuals import IMAGE_EXTS, VIDEO_EXTS, download_stock, project_path, search, stock_source

WEB_DIR = CODE_DIR / "web"
UPLOAD_DIR = ROOT / "uploads"
MAX_UPLOAD_MB = 300
for d in (OUTPUT_DIR, UPLOAD_DIR, CACHE_DIR, DRAFTS_DIR, *(ASSETS_DIR / k for k in ("music", "footage", "fonts"))):
    d.mkdir(parents=True, exist_ok=True)
try:
    split_song_renders()  # songs are drafts now: move music videos rendered inside a song folder into their own
except Exception:
    traceback.print_exc()

app = FastAPI(title="cr-content")
# The Next.js UI (frontend/, port 3000, or the desktop app's webview) calls this API directly.
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"^(https?://(localhost|127\.0\.0\.1):3000|https?://tauri\.localhost|tauri://localhost)$",
    allow_methods=["*"],
    allow_headers=["*"],
)
renderer = ThreadPoolExecutor(max_workers=1)  # FFmpeg is heavy: render one video at a time
jobs: dict[str, dict] = {}
jobs_lock = threading.Lock()


class ScriptRequest(BaseModel):
    topic: str
    lang: str = "en"
    scenes: int = 6
    seconds: int = 45
    style: str = ""


class RenderRequest(BaseModel):
    script: VideoScript
    topic: str = ""
    lang: str = "en"
    voice: str | None = None
    rate: str = "+5%"
    music: str = ""  # "" = random from assets/music, "none" = no music, or a file name
    draft_id: str = ""  # draft this render came from (recorded in the video's meta.json)


@lru_cache
def _voices(lang: str) -> list[str]:
    prefixes = {"en": ("en-US", "en-GB", "en-AU"), "km": ("km-KH",)}[lang]
    try:
        found = [v for p in prefixes for v in list_voices(p)]
    except Exception:
        found = []
    defaults = list(LANGS[lang].voices)
    return defaults + [v for v in found if v not in defaults]


@app.get("/api/options")
def options():
    music_dir = ASSETS_DIR / "music"
    return {
        "langs": {code: {"name": p.name, "voices": _voices(code)} for code, p in LANGS.items()},
        "music": sorted(p.name for p in music_dir.glob("*.mp3")) if music_dir.exists() else [],
        "keys": {
            "anthropic": bool(os.getenv("ANTHROPIC_API_KEY", "").startswith("sk-ant-")),
            "stock": stock_source(),
            "elevenlabs": bool(elevenlabs_key()),
        },
    }


def _claude_error(e: Exception) -> HTTPException:
    if isinstance(e, anthropic.BadRequestError) and "credit balance" in str(e.message):
        return HTTPException(402, "Your Claude account has no API credits. Add credits at "
                                  "platform.claude.com → Settings → Billing, then try again (no restart needed).")
    if isinstance(e, anthropic.BadRequestError) and "workspace" in str(e.message):
        return HTTPException(400, "Your Claude key isn't tied to a workspace. Either add ANTHROPIC_WORKSPACE_ID=wrkspc_... "
                                  "to .env, or create a new key inside a workspace in the Claude Console. Then restart the app.")
    if isinstance(e, anthropic.AuthenticationError):
        return HTTPException(401, "Claude rejected the API key. Put a valid key (starts with sk-ant-) "
                                  "in ANTHROPIC_API_KEY in .env, then restart the app.")
    if isinstance(e, anthropic.RateLimitError):
        return HTTPException(429, "Claude rate limit reached. Wait a minute and try again.")
    if isinstance(e, anthropic.APIConnectionError):
        return HTTPException(502, "Couldn't reach the Claude API. Check your internet connection.")
    if isinstance(e, anthropic.APIStatusError):
        return HTTPException(502, f"Claude API error {e.status_code}: {e.message}")
    return HTTPException(422, str(e))


@app.post("/api/script")
def write_script(req: ScriptRequest):
    if req.lang not in LANGS:
        raise HTTPException(400, f"Unknown language {req.lang}")
    if not req.topic.strip():
        raise HTTPException(400, "Enter a topic first.")
    try:
        script = generate_script(req.topic.strip(), lang=req.lang, scenes=req.scenes,
                                 seconds=req.seconds, style=req.style)
    except (anthropic.APIError, RuntimeError) as e:
        raise _claude_error(e)
    return script.model_dump()


# ---------- Scene backgrounds ----------

class IdeasRequest(BaseModel):
    narration: str
    current: str = ""


class PickRequest(BaseModel):
    source: str  # "pexels" | "pixabay"
    kind: str  # "video" | "photo"
    id: int


def _media_info(path: Path) -> dict:
    rel = project_path(path)
    return {"media": rel, "url": "/" + rel, "kind": "photo" if path.suffix.lower() in IMAGE_EXTS else "video"}


@app.post("/api/ideas")
def ideas(req: IdeasRequest):
    if not req.narration.strip():
        raise HTTPException(400, "Write the scene's narration first, so Claude knows what to look for.")
    try:
        return {"queries": suggest_queries(req.narration, req.current)}
    except (anthropic.APIError, RuntimeError) as e:
        raise _claude_error(e)


@app.get("/api/footage")
def footage(q: str, kind: str = "video"):
    if not stock_source():
        raise HTTPException(400, "Footage search needs a free Pixabay key. Add PIXABAY_API_KEY to .env "
                                 "(get one at pixabay.com/api/docs), then restart the app. You can still upload your own.")
    if not q.strip():
        raise HTTPException(400, "Type what to search for.")
    try:
        return {"results": search(q.strip(), "photo" if kind == "photo" else "video")}
    except requests.HTTPError as e:
        code = e.response.status_code if e.response is not None else 0
        name = stock_source().capitalize()
        msg = f"{name} rejected the API key." if code in (400, 401, 403) else f"{name} search failed ({code})."
        raise HTTPException(502, msg)
    except requests.RequestException:
        raise HTTPException(502, f"Couldn't reach {stock_source().capitalize()}. Check your internet connection.")


@app.post("/api/footage/pick")
def pick_footage(req: PickRequest):
    try:
        path = download_stock(req.source, req.kind, req.id)
    except (requests.RequestException, ValueError, KeyError) as e:
        raise HTTPException(502, f"Couldn't download that item: {e}")
    return _media_info(path)


def _save_upload(file: UploadFile, dest: Path) -> None:
    size = 0
    with open(dest, "wb") as out:
        while chunk := file.file.read(1 << 20):
            size += len(chunk)
            if size > MAX_UPLOAD_MB << 20:
                out.close()
                dest.unlink(missing_ok=True)
                raise HTTPException(413, f"That file is over {MAX_UPLOAD_MB} MB.")
            out.write(chunk)


@app.post("/api/upload")
def upload(file: UploadFile = File(...)):
    ext = Path(file.filename or "").suffix.lower()
    if ext not in IMAGE_EXTS | VIDEO_EXTS:
        raise HTTPException(400, "Use a photo (jpg, png, webp) or a video (mp4, mov, webm).")
    dest = UPLOAD_DIR / f"{uuid.uuid4().hex[:12]}{ext}"
    _save_upload(file, dest)
    return _media_info(dest)


class SpeakRequest(BaseModel):
    text: str
    voice: str
    rate: str = "+0%"


SPEAK_CACHE = CACHE_DIR / "tts"
MAX_PREVIEW_CHARS = 800


@app.post("/api/speak")
def speak(req: SpeakRequest):
    """Voice preview: synthesize a short text so users can hear a voice before rendering."""
    text = req.text.strip()
    if not text:
        raise HTTPException(400, "Write some narration first, then listen.")
    if len(text) > MAX_PREVIEW_CHARS:
        text = text[:MAX_PREVIEW_CHARS]
    if not req.voice or "Neural" not in req.voice:
        raise HTTPException(400, "Pick a voice first.")
    key = hashlib.sha1(f"{req.voice}|{req.rate}|{text}".encode("utf-8")).hexdigest()[:20]
    out = SPEAK_CACHE / f"{key}.mp3"
    if not out.exists():
        SPEAK_CACHE.mkdir(parents=True, exist_ok=True)
        tmp = out.with_suffix(".part")
        try:
            synthesize(text, req.voice, tmp, rate=req.rate)
        except Exception as e:
            tmp.unlink(missing_ok=True)
            raise HTTPException(502, f"Couldn't generate the voice preview ({e.__class__.__name__}). "
                                     "Check your internet connection and try again.")
        tmp.replace(out)
    return FileResponse(out, media_type="audio/mpeg")


class ImportRequest(BaseModel):
    text: str
    lang: str = "auto"  # "auto" detects Khmer vs English


@app.post("/api/import")
def import_pasted(req: ImportRequest):
    """Pasted free-form script -> structured script (Claude, or the basic parser as a fallback)."""
    try:
        script, lang, method = import_script(req.text, req.lang, use_claude=bool(os.getenv("ANTHROPIC_API_KEY")))
    except ValueError as e:
        raise HTTPException(422, str(e))
    return {"script": script.model_dump(), "lang": lang, "method": method}


class TranslateRequest(BaseModel):
    script: VideoScript
    target: str


@app.post("/api/translate")
def translate(req: TranslateRequest):
    if req.target not in LANGS:
        raise HTTPException(400, f"Unknown language {req.target}")
    if not any(s.narration.strip() for s in req.script.scenes):
        raise HTTPException(400, "Write some narration first, then translate.")
    try:
        return translate_script(req.script, req.target).model_dump()
    except (anthropic.APIError, RuntimeError) as e:
        raise _claude_error(e)


def _run_render(job_id: str, req: RenderRequest) -> None:
    job = jobs[job_id]

    def log(line: str) -> None:
        with jobs_lock:
            job["log"].append(line)
            if line.startswith("[") and "/5]" in line:
                job["step"] = int(line[1])

    with jobs_lock:
        job["status"] = "running"
    try:
        music = req.music
        if music and music != "none":
            music = str(ASSETS_DIR / "music" / Path(music).name)
        final = make_video(req.topic or req.script.title, script=req.script, lang=req.lang,
                           voice=req.voice, rate=req.rate, music=music or None, log=log)
        if req.draft_id:
            meta_path = final.parent / "meta.json"
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            meta["draft"] = req.draft_id
            meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
        with jobs_lock:
            job.update(status="done", step=5, video=final.parent.name)
    except Exception as e:
        traceback.print_exc()
        with jobs_lock:
            job.update(status="error", error=str(e).strip().splitlines()[-1] if str(e).strip() else repr(e))


@app.post("/api/render")
def render(req: RenderRequest):
    if req.lang not in LANGS:
        raise HTTPException(400, f"Unknown language {req.lang}")
    if not req.script.scenes:
        raise HTTPException(400, "The script has no scenes.")
    job_id = uuid.uuid4().hex[:10]
    with jobs_lock:
        jobs[job_id] = {"id": job_id, "status": "queued", "step": 0, "log": [], "title": req.script.title}
    renderer.submit(_run_render, job_id, req)
    return {"id": job_id}


# ---------- Songs (Claude lyrics -> ElevenLabs Music) ----------

class SongWriteRequest(BaseModel):
    topic: str
    lang: str = "en"
    seconds: int = 45
    style: str = ""
    vocal: str = ""


class SongComposeRequest(BaseModel):
    song: SongScript
    topic: str = ""
    lang: str = "en"
    stems: bool = True


@app.post("/api/song/write")
def write_song(req: SongWriteRequest):
    if req.lang not in LANGS:
        raise HTTPException(400, f"Unknown language {req.lang}")
    if not req.topic.strip():
        raise HTTPException(400, "Enter what the song is about first.")
    try:
        song = generate_song(req.topic.strip(), lang=req.lang, seconds=max(10, min(180, req.seconds)),
                             style=req.style, vocal=req.vocal)
    except (anthropic.APIError, RuntimeError) as e:
        raise _claude_error(e)
    return song.model_dump()


def _run_song(job_id: str, req: SongComposeRequest) -> None:
    job = jobs[job_id]

    def log(line: str) -> None:
        with jobs_lock:
            job["log"].append(line)
            if line.startswith("[") and "/2]" in line:
                job["step"] = int(line[1])

    with jobs_lock:
        job["status"] = "running"
    try:
        mix = make_song(req.topic or req.song.title, song=req.song, lang=req.lang, stems=req.stems, log=log)
        with jobs_lock:
            job.update(status="done", step=2, video=mix.parent.name)
    except Exception as e:
        traceback.print_exc()
        with jobs_lock:
            job.update(status="error", error=str(e).strip().splitlines()[-1] if str(e).strip() else repr(e))


@app.post("/api/song/compose")
def compose_song(req: SongComposeRequest):
    if req.lang not in LANGS:
        raise HTTPException(400, f"Unknown language {req.lang}")
    if not elevenlabs_key():
        raise HTTPException(400, "Songs need an ElevenLabs key. Add ELEVENLABS_API_KEY to .env, then restart the engine.")
    if not req.song.sections:
        raise HTTPException(400, "The song has no sections.")
    if not any(line.strip() for s in req.song.sections for line in s.lyrics):
        raise HTTPException(400, "Write some lyrics first.")
    job_id = uuid.uuid4().hex[:10]
    with jobs_lock:
        jobs[job_id] = {"id": job_id, "kind": "song", "status": "queued", "step": 0, "log": [], "title": req.song.title}
    renderer.submit(_run_song, job_id, req)
    return {"id": job_id}


def _run_music_video(job_id: str, folder: Path, idea: str = "") -> None:
    job = jobs[job_id]

    def log(line: str) -> None:
        with jobs_lock:
            job["log"].append(line)
            if line.startswith("[") and "/4]" in line:
                job["step"] = int(line[1])

    with jobs_lock:
        job["status"] = "running"
    try:
        final = make_music_video(folder, log=log, idea=idea)
        with jobs_lock:
            job.update(status="done", step=4, video=final.parent.name)
    except Exception as e:
        traceback.print_exc()
        with jobs_lock:
            job.update(status="error", error=str(e).strip().splitlines()[-1] if str(e).strip() else repr(e))


class MusicVideoRequest(BaseModel):
    idea: str = ""  # your idea for the video; the footage follows it


@app.post("/api/videos/{name}/music-video")
def music_video(name: str, req: MusicVideoRequest | None = None):
    """Render the song as a music video with karaoke lyrics; each render is a new version, earlier ones stay."""
    folder = _video_dir(name)
    if not (folder / "song.json").exists() or not (folder / "song.mp3").exists():
        raise HTTPException(400, "Compose the song first.")
    job_id = uuid.uuid4().hex[:10]
    title = json.loads((folder / "song.json").read_text(encoding="utf-8")).get("title", name)
    with jobs_lock:
        jobs[job_id] = {"id": job_id, "kind": "song_video", "status": "queued", "step": 0, "log": [], "title": title}
    renderer.submit(_run_music_video, job_id, folder, (req.idea if req else "")[:1000])
    return {"id": job_id}


# ---------- Your own songs (upload mp3 + lyrics -> lyric timing -> music video) ----------

def _job_logger(job: dict, steps: int):
    def log(line: str) -> None:
        with jobs_lock:
            job["log"].append(line)
            if line.startswith("[") and f"/{steps}]" in line:
                job["step"] = int(line[1])
    return log


def _fail(job: dict, e: Exception) -> None:
    traceback.print_exc()
    with jobs_lock:
        job.update(status="error", error=str(e).strip().splitlines()[-1] if str(e).strip() else repr(e))


def _run_import(job_id: str, audio: Path, title: str, lyrics: str, lang: str, aspect: str) -> None:
    job = jobs[job_id]
    log = _job_logger(job, 2)
    with jobs_lock:
        job["status"] = "running"
    try:
        folder = import_song(audio, title, lyrics, lang, aspect, log=log)
        with jobs_lock:
            job["video"] = folder.name  # the song exists now, even if timing fails below
        sync_lyrics(folder, log=log)
        with jobs_lock:
            job.update(status="done", step=2)
    except Exception as e:
        _fail(job, e)
    finally:
        audio.unlink(missing_ok=True)


@app.post("/api/song/import")
def import_own_song(file: UploadFile = File(...), title: str = Form(""), lyrics: str = Form(...),
                    lang: str = Form("en"), aspect: str = Form("16:9")):
    """Your finished song: the audio plus its lyrics. Lyric timing runs as a job; then check it and render."""
    if lang not in LANGS:
        raise HTTPException(400, f"Unknown language {lang}")
    ext = Path(file.filename or "").suffix.lower()
    if ext not in AUDIO_EXTS:
        raise HTTPException(400, "Use an audio file: mp3, wav, m4a, flac or ogg.")
    if not lyrics.strip():
        raise HTTPException(400, "Paste the song's lyrics.")
    audio = UPLOAD_DIR / f"song-{uuid.uuid4().hex[:12]}{ext}"
    _save_upload(file, audio)
    title = title.strip() or Path(file.filename or "song").stem
    job_id = uuid.uuid4().hex[:10]
    with jobs_lock:
        jobs[job_id] = {"id": job_id, "kind": "lyrics_sync", "status": "queued", "step": 0, "log": [], "title": title}
    renderer.submit(_run_import, job_id, audio, title, lyrics, lang, aspect)
    return {"id": job_id}


def _run_sync(job_id: str, folder: Path) -> None:
    job = jobs[job_id]
    log = _job_logger(job, 2)
    with jobs_lock:
        job["status"] = "running"
    try:
        log("[1/2] Loading the song")
        sync_lyrics(folder, log=log)
        with jobs_lock:
            job.update(status="done", step=2, video=folder.name)
    except Exception as e:
        _fail(job, e)


@app.post("/api/videos/{name}/lyrics/sync")
def resync_lyrics(name: str):
    """Time the lyrics against the song again (replaces any hand corrections)."""
    folder = _video_dir(name)
    if not (folder / "song.json").exists() or not (folder / "song.mp3").exists():
        raise HTTPException(400, "This isn't a song.")
    job_id = uuid.uuid4().hex[:10]
    title = json.loads((folder / "song.json").read_text(encoding="utf-8")).get("title", name)
    with jobs_lock:
        jobs[job_id] = {"id": job_id, "kind": "lyrics_sync", "status": "queued", "step": 0, "log": [], "title": title}
    renderer.submit(_run_sync, job_id, folder)
    return {"id": job_id}


@app.get("/api/videos/{name}/lyrics")
def get_lyrics(name: str):
    folder = _video_dir(name)
    lines = load_lines(folder / "lyrics.json")
    meta = json.loads((folder / "meta.json").read_text(encoding="utf-8")) if (folder / "meta.json").exists() else {}
    return {"lines": [asdict(l) for l in lines] if lines is not None else None, "timing": meta.get("timing", "")}


class TimedWord(BaseModel):
    text: str
    start: float
    end: float


class TimedLine(BaseModel):
    section: int = 0
    text: str
    words: list[TimedWord]
    check: bool = False  # still to be checked by ear


class LyricsRequest(BaseModel):
    lines: list[TimedLine]


@app.put("/api/videos/{name}/lyrics")
def put_lyrics(name: str, req: LyricsRequest):
    """Save hand-corrected lyric timing; the next music-video render uses it."""
    folder = _video_dir(name)
    total = float(json.loads((folder / "meta.json").read_text(encoding="utf-8")).get("duration") or 1e9) \
        if (folder / "meta.json").exists() else 1e9
    data = []
    for line in req.lines:
        words = [w for w in line.words if w.text.strip()]
        if not words:
            continue
        data.append({"section": line.section, "text": line.text, "check": line.check,
                     "words": [{"text": w.text, "start": max(0.0, min(w.start, total)),
                                "end": max(0.0, min(max(w.end, w.start + 0.05), total))} for w in words]})
    lines = lines_from_json(data)
    save_lines(lines, folder / "lyrics.json")
    meta_path = folder / "meta.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else {}
    meta["timing"] = "edited"
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"lines": [asdict(l) for l in lines], "timing": "edited"}


@app.get("/api/jobs/{job_id}")
def job_status(job_id: str):
    with jobs_lock:
        if job_id not in jobs:
            raise HTTPException(404, "Job not found (the app may have restarted).")
        return dict(jobs[job_id], log=list(jobs[job_id]["log"]))


# ---------- Drafts (drafts/<id>/draft.json) ----------

@app.get("/api/drafts")
def list_drafts():
    """Script drafts and songs (a song's lyrics and timing stay editable until you make a music video from it)."""
    items = [{"kind": "script", **d} for d in drafts.list_drafts()]
    for folder in OUTPUT_DIR.iterdir():
        meta = _read_meta(folder) if folder.is_dir() else {}
        if meta.get("kind") != "song":
            continue
        summary = _summary(folder)
        versions = song_versions(folder)
        edited = [p.stat().st_mtime for p in (folder / "lyrics.json", folder / "song.json") if p.exists()]
        updated = datetime.fromtimestamp(max(edited)).isoformat(timespec="seconds") if edited else summary["created"]
        latest = next((v for v in versions if (v / "thumbnail.jpg").exists()), None)
        items.append({"kind": "song", "id": folder.name, "title": summary["title"], "lang": summary["lang"],
                      "updated": max([updated] + [_read_meta(v).get("created", "") for v in versions]),
                      "scenes": 0, "cover": "", "source": summary["source"], "versions": len(versions),
                      "thumb": latest.name if latest else "",
                      "thumb_v": int((latest / "thumbnail.jpg").stat().st_mtime) if latest else 0})
    return sorted(items, key=lambda x: x["updated"], reverse=True)


@app.post("/api/drafts")
def create_draft(draft: drafts.Draft):
    draft_id, saved = drafts.create(draft)
    return {"id": draft_id, "updated": saved.updated}


@app.get("/api/drafts/{draft_id}")
def get_draft(draft_id: str):
    try:
        return {"id": draft_id, **drafts.load(draft_id).model_dump()}
    except KeyError:
        raise HTTPException(404, "Draft not found. It may have been deleted.")


@app.put("/api/drafts/{draft_id}")
def save_draft(draft_id: str, draft: drafts.Draft):
    try:
        saved = drafts.save(draft_id, draft)
    except KeyError:
        raise HTTPException(404, "Draft not found. It may have been deleted.")
    return {"id": draft_id, "updated": saved.updated}


@app.delete("/api/drafts/{draft_id}")
def delete_draft(draft_id: str):
    try:
        drafts.delete(draft_id)
    except KeyError:
        raise HTTPException(404, "Draft not found.")
    return {"deleted": draft_id}


def _video_dir(name: str) -> Path:
    folder = (OUTPUT_DIR / name).resolve()
    if folder.parent != OUTPUT_DIR.resolve() or not folder.is_dir():
        raise HTTPException(404, "Video not found.")
    return folder


def _read_meta(folder: Path) -> dict:
    try:
        return json.loads((folder / "meta.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _summary(folder: Path) -> dict:
    meta = _read_meta(folder)
    title = folder.name
    for name in ("script.json", "song.json"):
        if (folder / name).exists():
            title = json.loads((folder / name).read_text(encoding="utf-8")).get("title", title)
            break
    lang = meta.get("lang") or (folder.name.split("-")[2] if folder.name.count("-") >= 2 else "en")
    created = meta.get("created") or datetime.fromtimestamp(folder.stat().st_mtime).isoformat(timespec="seconds")
    return {
        "name": folder.name,
        "title": title,
        "lang": lang,
        "created": created,
        "kind": meta.get("kind", "video"),
        "source": meta.get("source", ""),  # "upload" = your own song
        "aspect": meta.get("aspect", "9:16"),
        # music video: the song folder it was made from ("" once that song is deleted)
        "song_folder": meta.get("song", "") if meta.get("song") and (OUTPUT_DIR / meta["song"]).is_dir() else "",
        "video": (folder / "video.mp4").exists(),
        "audio": (folder / "song.mp3").exists(),
        "thumb": (folder / "thumbnail.jpg").exists(),
        # changes whenever the thumbnail is redrawn, so the UI can bust the browser cache
        "thumb_v": int((folder / "thumbnail.jpg").stat().st_mtime) if (folder / "thumbnail.jpg").exists() else 0,
    }


@app.get("/api/videos")
def videos():
    # songs are listed with the drafts; their music videos are here
    folders = [f for f in OUTPUT_DIR.iterdir() if f.is_dir() and _read_meta(f).get("kind") != "song"]
    items = [_summary(f) for f in folders]
    return sorted(items, key=lambda v: v["created"], reverse=True)


@app.get("/api/videos/{name}")
def video_detail(name: str):
    folder = _video_dir(name)
    data = _summary(folder)
    data["script"] = VideoScript.load(folder / "script.json").model_dump() if (folder / "script.json").exists() else None
    data["post"] = (folder / "post.txt").read_text(encoding="utf-8") if (folder / "post.txt").exists() else ""
    meta = json.loads((folder / "meta.json").read_text(encoding="utf-8")) if (folder / "meta.json").exists() else {}
    data["song"] = SongScript.load(folder / "song.json").model_dump() if (folder / "song.json").exists() else None
    data["stems"] = {k: meta[k] for k in ("vocals", "instrumental") if meta.get(k)}
    data["versions"] = [_summary(f) for f in song_versions(folder)] if meta.get("kind") == "song" else []
    data["idea"] = meta.get("idea", "")  # song: last idea used for a music video; music video: the one it was made with
    data["duration"] = (round(duration(folder / "video.mp4"), 2) if data["video"]
                        else meta.get("duration", 0))
    data["thumb_text"] = meta.get("thumb_text", data["title"])
    data["thumb_at"] = meta.get("thumb_at", min(1.0, data["duration"] / 2))
    data["thumb_style"] = meta.get("thumb_style", "bold")
    data["thumb_emphasis"] = meta.get("thumb_emphasis", "")
    saved = folder / "suggest" / "suggestions.json"
    data["thumb_suggestions"] = json.loads(saved.read_text(encoding="utf-8")) if saved.exists() else None
    return data


class ThumbnailRequest(BaseModel):
    text: str = ""
    at: float = 1.0
    style: str = "bold"  # one of captions.THUMB_STYLES
    emphasis: str = ""  # word(s) to highlight; "" = pick automatically


@app.post("/api/videos/{name}/thumbnail")
def video_thumbnail(name: str, req: ThumbnailRequest):
    folder = _video_dir(name)
    if not (folder / "video.mp4").exists():
        raise HTTPException(404, "This video hasn't been rendered.")
    lang = _summary(folder)["lang"]
    try:
        make_thumbnail(folder, req.text[:120], req.at, lang,
                       req.style if req.style in THUMB_STYLES else "bold", req.emphasis[:60])
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(500, f"Couldn't make the thumbnail: {str(e).strip().splitlines()[-1]}")
    return _summary(folder)


@app.post("/api/videos/{name}/thumbnail/suggest")
def video_thumbnail_suggest(name: str):
    """Claude-written headlines on the best-looking frames, rendered as preview covers to pick from."""
    folder = _video_dir(name)
    if not (folder / "video.mp4").exists():
        raise HTTPException(404, "This video hasn't been rendered.")
    if not (folder / "script.json").exists():
        raise HTTPException(400, "This video has no script.json to write headlines from.")
    try:
        items, note = suggest_thumbnails(folder, _summary(folder)["lang"])
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(500, f"Couldn't suggest thumbnails: {str(e).strip().splitlines()[-1]}")
    return {"items": items, "note": note}


@app.get("/api/videos/{name}/thumbnail.jpg")
def download_thumbnail(name: str):
    folder = _video_dir(name)
    if not (folder / "thumbnail.jpg").exists():
        raise HTTPException(404, "No thumbnail yet.")
    return FileResponse(folder / "thumbnail.jpg", media_type="image/jpeg", filename=f"{name}-thumbnail.jpg")


@app.get("/api/videos/{name}/download")
def download_video(name: str):
    folder = _video_dir(name)
    if not (folder / "video.mp4").exists():
        raise HTTPException(404, "This video hasn't been rendered.")
    return FileResponse(folder / "video.mp4", media_type="video/mp4", filename=f"{name}.mp4")


@app.get("/api/videos/{name}/song")
def download_song(name: str):
    folder = _video_dir(name)
    if not (folder / "song.mp3").exists():
        raise HTTPException(404, "This song hasn't been composed.")
    return FileResponse(folder / "song.mp3", media_type="audio/mpeg", filename=f"{name}.mp3")


@app.get("/api/videos/{name}/stem/{kind}")
def download_stem(name: str, kind: str):
    folder = _video_dir(name)
    meta = json.loads((folder / "meta.json").read_text(encoding="utf-8")) if (folder / "meta.json").exists() else {}
    file = folder / meta[kind] if kind in ("vocals", "instrumental") and meta.get(kind) else None
    if not file or not file.is_file() or file.resolve().parent != folder:
        raise HTTPException(404, "This stem doesn't exist.")
    return FileResponse(file, media_type="audio/mpeg", filename=f"{name}-{kind}{file.suffix}")


@app.delete("/api/videos/{name}")
def delete_video(name: str):
    shutil.rmtree(_video_dir(name))
    return {"deleted": name}


app.mount("/media", StaticFiles(directory=OUTPUT_DIR), name="media")
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")
app.mount("/cache", StaticFiles(directory=CACHE_DIR), name="cache")
app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")


@app.get("/")
def index():
    return FileResponse(WEB_DIR / "index.html")
