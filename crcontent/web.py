"""Local web app: FastAPI backend wrapping the pipeline, serving the UI in /web."""
import hashlib
import json
import os
import re
import shutil
import threading
import traceback
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict
from datetime import datetime, timedelta
from functools import lru_cache
from pathlib import Path

from . import llm
import requests
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import addons, art, campaigns, director_plan, drafts, locations, profiles, lyricvideo, music, packaging, publish, quality, quality_preview, rights, schedule, sheet, voiceover
from .history.models import ResearchBrief as ResearchBriefModel
from .config import ASSETS_DIR, CACHE_DIR, CODE_DIR, DRAFTS_DIR, LANGS, OUTPUT_DIR, ROOT, SCENE_PAD_SEC, frame_size
from .lyrics import SongScript, generate_song, suggest_video_ideas
from .align import lines_from_json, load_lines, save_lines
from .pipeline import (AUDIO_EXTS, COVER_STYLES, import_song, make_music_video, make_song, make_thumbnail, make_video,
                       song_versions, split_song_renders, suggest_thumbnails, sync_lyrics)
from .post import set_title, suggest_posts, write_post
from .render import duration, run as run_ffmpeg
from .importer import import_script
from .script import VideoScript, generate_script, suggest_queries, suggest_topics, translate_script
from .song import elevenlabs_key
from .styles import caption_catalog, catalog as style_catalog
from .tts import list_voices, synthesize
from .visuals import IMAGE_EXTS, VIDEO_EXTS, FootagePicker, download_stock, project_path, search, stock_source

addons.activate()  # the desktop app's AI add-on (torch, diffusers, Whisper), when it's installed
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


# Added before CORS so it runs inside it: an unexpected error still answers with CORS headers, and the UI shows
# the error instead of a network failure ("Can't reach the video engine").
@app.middleware("http")
async def report_errors(request, call_next):
    try:
        return await call_next(request)
    except Exception as e:
        traceback.print_exc()
        return JSONResponse({"detail": f"The video engine hit an error: {type(e).__name__}: {e}"}, status_code=500)


# The Next.js UI (frontend/, port 3000, or the desktop app's webview) calls this API directly.
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"^(https?://(localhost|127\.0\.0\.1):3000|https?://tauri\.localhost|tauri://localhost)$",
    allow_methods=["*"],
    allow_headers=["*"],
)
class JobStopped(Exception):
    """Raised by a job's log function once the user has stopped the job (POST /api/jobs/<id>/cancel)."""


STOPPED = "Stopped. Work saved so far is kept: start it again to carry on."


class JobPool(ThreadPoolExecutor):
    """A queue of job runners (fn(job_id, ...)): a job stopped while queued never starts, and one whose runner lets
    JobStopped escape (or swallows it) still ends as stopped instead of looking like it's running forever."""

    def submit(self, fn, job_id, *args, **kwargs):
        def run():
            job = jobs.get(job_id)
            try:
                if not (job and job.get("cancel")):
                    fn(job_id, *args, **kwargs)
            except JobStopped:
                pass
            finally:
                with jobs_lock:
                    # runners that catch errors themselves mark a stop as a failure: it was the user's stop
                    if job and job.get("cancel") and job.get("status") in ("queued", "running", "error"):
                        job.update(status="error", error=STOPPED, cancelled=True)
        return super().submit(run)


renderer = JobPool(max_workers=1)  # FFmpeg is heavy: render one video at a time
uploader = ThreadPoolExecutor(max_workers=1)  # uploads to YouTube/TikTok, separate so renders don't wait on them
jobs: dict[str, dict] = {}
jobs_lock = threading.Lock()
lyricvideo.bind(jobs, jobs_lock, renderer)
app.include_router(lyricvideo.router)
quality.bind(jobs, jobs_lock)
app.include_router(quality_preview.router)  # before quality's /api/inspect/{scope}/{name}
app.include_router(quality.router)
app.include_router(rights.router)


class ScriptRequest(BaseModel):
    topic: str
    lang: str = "en"
    scenes: int = 4
    seconds: int = 20  # 15-25 s Shorts get watched to the end (and again) far more often than 45-60 s ones
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


@app.get("/api/profiles")
def channel_profiles():
    """The channel profiles a new Script-to-Video project can start from (profiles.py)."""
    return [p.model_dump() for p in profiles.PROFILES.values()]


@app.get("/api/options")
def options():
    music_dir = ASSETS_DIR / "music"
    return {
        "langs": {code: {"name": p.name, "voices": _voices(code)} for code, p in LANGS.items()},
        "music": sorted(p.name for p in music_dir.glob("*.mp3")) if music_dir.exists() else [],
        # each track's licence for monetized videos: ok / nc (non-commercial) / nd (no derivatives) / unknown
        "music_use": {p.name: music.track_use(p) for p in music_dir.glob("*.mp3")} if music_dir.exists() else {},
        "keys": {
            "ai": bool(os.getenv("GEMINI_API_KEY", "").strip()),
            "stock": stock_source(),
            "elevenlabs": bool(elevenlabs_key()),
            "jamendo": bool(music.jamendo_key()),
        },
        "styles": style_catalog(),  # lyric style presets, footage looks, installed fonts per language
        "captions": caption_catalog(),  # caption presets of narrated videos
    }


def _llm_error(e: Exception) -> HTTPException:
    if isinstance(e, llm.AuthenticationError):
        return HTTPException(401, "Gemini rejected the API key. Put a valid key in Settings (get one free at "
                                  "aistudio.google.com/apikey), then try again.")
    if isinstance(e, llm.RateLimitError):
        return HTTPException(429, "Gemini rate limit or free quota reached. Wait a minute and try again, "
                                  "or use a paid key.")
    if isinstance(e, llm.APIConnectionError):
        return HTTPException(502, "Couldn't reach the Gemini API. Check your internet connection.")
    if isinstance(e, llm.BadRequestError):
        return HTTPException(400, f"Gemini rejected the request: {e.message}")
    if isinstance(e, llm.APIStatusError):
        return HTTPException(502, f"Gemini API error {e.status_code}: {e.message}")
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
    except (llm.APIError, RuntimeError) as e:
        raise _llm_error(e)
    return script.model_dump()


# ---------- Scene backgrounds ----------

class IdeasRequest(BaseModel):
    narration: str
    current: str = ""


class PickRequest(BaseModel):
    source: str  # "pexels" | "pixabay" | "mixkit" | "unsplash"
    kind: str  # "video" | "photo"
    id: int | str  # Unsplash ids are text (checked in download_stock)


def _media_info(path: Path) -> dict:
    rel = project_path(path)
    return {"media": rel, "url": "/" + rel, "kind": "photo" if path.suffix.lower() in IMAGE_EXTS else "video"}


@app.post("/api/ideas")
def ideas(req: IdeasRequest):
    if not req.narration.strip():
        raise HTTPException(400, "Write the scene's narration first, so Gemini knows what to look for.")
    try:
        return {"queries": suggest_queries(req.narration, req.current)}
    except (llm.APIError, RuntimeError) as e:
        raise _llm_error(e)


class TopicIdeasRequest(BaseModel):
    niche: str = ""  # what the channel is about ("" = whatever its recent videos are about)
    lang: str = "en"


@app.post("/api/topic-ideas")
def topic_ideas(req: TopicIdeasRequest):
    """Ideas for the next Shorts, in a mix of hook formats and never a near-repeat of the channel's recent titles."""
    recent = [d["title"] for d in sorted(drafts.list_drafts(), key=lambda d: d.get("updated", ""), reverse=True)]
    recent += [v["title"] for v in videos() if v["kind"] == "video"]
    lang = req.lang if req.lang in LANGS else "en"
    try:
        return {"topics": suggest_topics(req.niche.strip()[:300], lang, list(dict.fromkeys(recent))[:60])}
    except (llm.APIError, RuntimeError) as e:
        raise _llm_error(e)


@app.get("/api/footage")
def footage(q: str, kind: str = "video"):
    if not q.strip():
        raise HTTPException(400, "Type what to search for.")
    try:
        return {"results": search(q.strip(), "photo" if kind == "photo" else "video")}
    except requests.HTTPError as e:
        code = e.response.status_code if e.response is not None else 0
        site = e.request.url.split("/")[2] if e.request is not None else "the stock site"
        msg = f"{site} rejected the API key." if code in (400, 401, 403) else f"{site} search failed ({code})."
        raise HTTPException(502, msg)
    except requests.RequestException:
        raise HTTPException(502, "Couldn't reach the stock sites. Check your internet connection.")


@app.post("/api/footage/pick")
def pick_footage(req: PickRequest):
    try:
        path = download_stock(req.source, req.kind, req.id)
    except (requests.RequestException, ValueError, KeyError) as e:
        raise HTTPException(502, f"Couldn't download that item: {e}")
    return _media_info(path)


class DesignRequest(BaseModel):
    prompt: str | None = ""  # what to draw: the search words or your own description
    narration: str | None = ""  # the scene's voiceover, for context (null for a scene with none yet)
    aspect: str | None = "9:16"
    animate: bool = False  # a seamless looping clip instead of a still


@app.post("/api/footage/design")
def design_footage(req: DesignRequest):
    """Gemini draws a background for the scene (artwork, no text); it's used like a photo, with a slow zoom. Animated,
    it comes back as a looping video clip instead."""
    subject = "\n".join(t.strip() for t in (req.prompt or "", req.narration or "") if t.strip())
    if not subject:
        raise HTTPException(400, "Describe the background, or write the scene's narration first.")
    try:
        make = art.motion_background if req.animate else art.background
        return _media_info(make(subject, frame_size(req.aspect)))
    except (llm.APIError, RuntimeError) as e:
        raise _llm_error(e)


# ---------- AI scene art (Stable Diffusion XL on this computer's GPU) ----------

art_downloads: dict[str, str] = {}  # style -> "downloading" or the error of the last try
art_lock = threading.Lock()


@app.get("/api/art/status")
def art_status():
    """Is the GPU usable, which looks are downloaded (or downloading), and the camera moves and effects to offer."""
    from . import fx, imagegen

    status = imagegen.status()
    with art_lock:
        for key, item in status["styles"].items():
            # started here, or a download already running (a render job, another process) that is still growing
            item["downloading"] = art_downloads.get(key) == "downloading" or bool((item["progress"] or {}).get("active"))
            item["error"] = "" if item["downloading"] else art_downloads.get(key, "")
    return {**status, "addon": addons.status(), "motions": fx.MOTIONS, "effects": fx.EFFECTS}


@app.get("/api/art/progress")
def art_progress():
    """Download progress as it happens (server-sent events): the art status every quarter second while a model is
    downloading, then once more when it's done, and the stream ends."""
    import time

    def events():
        quiet = 0
        while quiet < 2:  # one last update after the download ends, so the page sees "Ready"
            status = art_status()
            yield f"data: {json.dumps(status)}\n\n"
            busy = status["addon"]["installing"] or any(s["downloading"] for s in status["styles"].values())
            quiet = 0 if busy else quiet + 1
            time.sleep(0.25)

    return StreamingResponse(events(), media_type="text/event-stream", headers={"Cache-Control": "no-cache"})


@app.post("/api/addon/install")
def addon_install():
    """Install the AI add-on (~3 GB; ~1.5 GB on an Apple Silicon Mac, the music extras only on an Intel Mac). Progress streams from /api/art/progress."""
    if not addons.needed() and not addons.status()["installing"]:
        raise HTTPException(400, "The AI add-on is already installed, or can't be installed here.")
    addons.install()
    return addons.status()


@app.post("/api/art/download/{style}")
def art_download(style: str):
    """Download a look's model in the background (~7 GB); /api/art/status shows when it's done."""
    from . import imagegen

    if style not in imagegen.STYLES:
        raise HTTPException(404, "Unknown art style.")
    if not imagegen.installed():
        raise HTTPException(400, "AI scene art needs an Apple Silicon Mac (M1 or newer)." if addons.MUSIC_ONLY
                            else "AI scene art isn't installed. Install the AI add-on in Settings → AI features.")
    with art_lock:
        if art_downloads.get(style) == "downloading":
            return {"downloading": True}
        art_downloads[style] = "downloading"

    def fetch():
        try:
            imagegen.download(style)
            result = ""
        except Exception as e:
            traceback.print_exc()
            result = f"Download failed: {type(e).__name__}: {str(e)[:200]}"
        with art_lock:
            art_downloads[style] = result

    threading.Thread(target=fetch, daemon=True).start()
    return {"downloading": True}


def _art_check(style: str) -> None:
    from . import imagegen

    if style not in imagegen.STYLES:
        raise HTTPException(400, "Pick an art style first.")
    if not imagegen.installed():
        raise HTTPException(400, "AI scene art needs an Apple Silicon Mac (M1 or newer)." if addons.MUSIC_ONLY
                            else "AI scene art isn't installed. Install the AI add-on in Settings → AI features.")
    if not imagegen.gpu_name():
        raise HTTPException(400, "AI scene art needs an NVIDIA graphics card or an Apple Silicon Mac, and none was found.")
    if not imagegen.downloaded(style):
        raise HTTPException(400, f"Download the {imagegen.STYLES[style]['label']} model first (Settings → AI features).")


class ArtDrawRequest(BaseModel):
    prompt: str
    style: str
    seed: int = 0  # 0 = the prompt's own seed; another number = another take of the same prompt
    aspect: str = "9:16"
    subject: str = ""  # the video's real subject (script.art_subject): checked, and drawn again when it's wrong
    avoid: str = ""  # what the model must not draw instead (script.art_avoid)


@app.post("/api/art/draw")
def art_draw(req: ArtDrawRequest):
    """Draw one scene picture (about 30 s the first time, while the model loads; a picture of the video's real
    subject that comes out wrong is drawn again, up to 3 takes). Returns it like a picked photo, with its check."""
    from . import imagegen
    from .pipeline import draw_checked

    _art_check(req.style)
    if not req.prompt.strip():
        raise HTTPException(400, "Describe the picture first.")
    seed = req.seed or imagegen.default_seed(req.prompt)
    try:
        path, seed, score, problem = draw_checked(req.prompt, req.style, frame_size(req.aspect), seed=seed,
                                                  subject=req.subject.strip(), avoid=req.avoid.strip(), log=print)
    except RuntimeError as e:
        raise HTTPException(422, str(e))
    imagegen.unload_later()  # keep the model warm while you're drawing, free the GPU when you stop
    return {**_media_info(path), "seed": seed, "score": score, "problem": problem}


class ArtCheckRequest(BaseModel):
    media: str  # a drawn picture (project-relative, cache/gen/...)
    subject: str  # "name: visible features" (script.art_subject)
    prompt: str = ""


@app.post("/api/art/check")
def art_check(req: ArtCheckRequest):
    """How well a picture you drew shows the video's real subject (Gemini's check, kept with the picture, so each
    one is only ever checked once). score is null when the picture isn't meant to show the subject."""
    from .pipeline import _verdict

    path = ROOT / req.media
    name = req.subject.split(":")[0].strip().lower()
    if not path.is_file() or not name or name.split()[-1] not in req.prompt.lower():
        return {"score": None, "problem": ""}
    try:
        score, problem = _verdict(path, req.subject.strip(), req.prompt)
    except llm.APIError as e:
        raise _llm_error(e)
    return {"score": score, "problem": problem}


class RealSubjectRequest(BaseModel):
    subject: str  # "name: visible features" (script.art_subject)
    exclude: list[str] = []  # media already used in the video (project-relative), to get a different one


@app.post("/api/art/real")
def art_real(req: RealSubjectRequest):
    """Real footage or a real photo of the subject (a stock clip, else Wikimedia Commons), checked by Gemini, for a
    scene whose AI picture can't get the subject right."""
    from .pipeline import real_subject_media

    if not req.subject.strip():
        raise HTTPException(400, "Name the real subject first (under the look of the video).")
    used = {str(ROOT / m) for m in req.exclude}
    try:
        path = real_subject_media(req.subject.strip(), used, log=print)
    except llm.APIError as e:
        raise _llm_error(e)
    if not path:
        raise HTTPException(404, f"No stock clip or Wikimedia Commons photo clearly shows a {req.subject.split(':')[0].strip()}. "
                                 "Upload your own clip or photo for this scene.")
    from .commons import credit

    return {**_media_info(path), "credit": credit(path)}


class ArtPlanRequest(BaseModel):
    script: VideoScript
    replace: bool = False  # also rewrite prompts that already exist


@app.post("/api/art/plan")
def art_plan(req: ArtPlanRequest):
    """Gemini plans a picture prompt, camera move and effects for each scene (keeping your own prompts unless
    `replace`); returns the script with them filled in."""
    from .pipeline import plan_scene_art

    script = req.script
    if script.art_style not in ("anime", "cinematic", "flat"):
        raise HTTPException(400, "Pick an art style first.")
    if req.replace:
        for scene in script.scenes:
            scene.art_prompt, scene.motion, scene.effects = "", "", []
        script.art_bible = script.art_subject = script.art_avoid = ""
    try:
        plan_scene_art(script, log=lambda _: None)
    except (llm.APIError, RuntimeError) as e:
        raise _llm_error(e)
    return script.model_dump()


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


class VoiceoverRequest(BaseModel):
    scenes: list[str]  # each scene's narration ("" = a silent scene)
    voice: str
    rate: str = "+5%"


@app.post("/api/voiceover")
def make_voiceover(req: VoiceoverRequest):
    """The draft's voiceover for the transcript editor: each scene's audio (cached, and reused by the render) with
    its word timings. Silent scenes come back as null."""
    if not req.voice or "Neural" not in req.voice:
        raise HTTPException(400, "Pick a voice first.")
    if len(req.scenes) > 60 or any(len(t) > 3000 for t in req.scenes):
        raise HTTPException(400, "The script is too long for the transcript.")

    def one(text: str):
        return voiceover.transcript(text, req.voice, req.rate) if text.strip() else None

    try:
        with ThreadPoolExecutor(max_workers=2) as pool:  # more at once makes Edge TTS reject requests
            scenes = list(pool.map(one, req.scenes))
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(502, f"Couldn't generate the voiceover ({e.__class__.__name__}). "
                                 "Check your internet connection and try again.")
    return {"pad": SCENE_PAD_SEC, "scenes": scenes}


@app.get("/api/voiceover/{key}.mp3")
def voiceover_audio(key: str):
    path = voiceover.VOICE_CACHE / f"{key}.mp3"
    if not re.fullmatch(r"[0-9a-f]{20}", key) or not path.exists():
        raise HTTPException(404, "That voiceover is gone. Refresh the transcript.")
    return FileResponse(path, media_type="audio/mpeg")


@app.get("/api/voiceover/{key}/peaks")
def voiceover_peaks(key: str):
    """The voiceover's loudness, `rate` values per second (0-1), for the timeline's waveform."""
    path = voiceover.VOICE_CACHE / f"{key}.mp3"
    if not re.fullmatch(r"[0-9a-f]{20}", key) or not path.exists():
        raise HTTPException(404, "That voiceover is gone.")
    return voiceover.peaks(path)


@app.get("/api/timeline/catalog")
def timeline_catalog():
    """What the timeline's graphics and sound-effect clips can use: the synthesized sounds (with their length) and
    the Remotion templates with the props a new graphic starts from."""
    from . import graphic_templates, sfx

    return {"sounds": sfx.catalog(duration), "templates": graphic_templates.TEMPLATES,
            "categories": sfx.CATEGORIES, "licences": sfx.LICENCES, "needs_credit": sorted(sfx.NEEDS_CREDIT)}


class StillsRequest(BaseModel):
    lang: str = "en"
    items: list[dict] = Field(default_factory=list, max_length=20)  # {template, props, seconds, version}


@app.post("/api/graphics/stills")
def graphic_stills(req: StillsRequest):
    """Preview frames of graphics (Remotion, transparent PNGs, cached by template, version, props and length). Each
    item answers {key, url} when made, or {errors} (invalid props) / {failed} (couldn't render), never silently."""
    from . import graphic_templates as gt
    from .shorts import motion
    from .styles import font_path

    out, jobs = [], []
    for it in req.items:
        props, errors = gt.validate(str(it.get("template", "")), it.get("props") or {}, int(it.get("version") or 0))
        seconds = min(max(float(it.get("seconds") or 2), 0.4), 30)
        if errors:
            out.append({"errors": errors})
            continue
        job = {"template": it["template"], "props": props, "seconds": seconds}
        jobs.append(job)
        out.append(job)
    profile = LANGS.get(req.lang, LANGS["en"])
    made = gt.render_stills(jobs, motion.font_url(font_path(profile.font_file))) if jobs else {}
    for k, item in enumerate(out):
        if "errors" in item:
            continue
        key = gt.still_key(item["template"], item["props"], item["seconds"])
        out[k] = {"key": key, "url": f"/api/graphics/stills/{key}.png"} if not made.get(key) else {"failed": made[key]}
    return {"items": out}


class AutoKeywordsRequest(BaseModel):
    scenes: list[dict] = Field(default_factory=list, max_length=200)  # {narration, visual_query, impacts}


@app.post("/api/keywords/auto")
def auto_keywords(req: AutoKeywordsRequest):
    """The caption keywords each scene would get by itself (the Transcript's Auto-pick, for drafts made before)."""
    from .pacing import auto_keywords as pick

    return {"keywords": [pick(str(s.get("narration") or ""), str(s.get("visual_query") or ""),
                              [str(w) for w in s.get("impacts") or []]) for s in req.scenes]}


@app.get("/api/graphics/stills/{key}.png")
def graphic_still(key: str):
    from . import graphic_templates as gt

    path = gt.STILLS / f"{key}.png"
    if not re.fullmatch(r"[0-9a-f]{20}", key) or not path.is_file():
        raise HTTPException(404, "That preview frame is gone.")
    return FileResponse(path, media_type="image/png")


def _sfx_file(name: str) -> Path:
    from . import sfx

    try:
        return sfx.sound(name)
    except KeyError:
        raise HTTPException(404, "Unknown sound effect.")


@app.get("/api/sfx/{name}.wav")
def sfx_audio(name: str):
    return FileResponse(_sfx_file(name), media_type="audio/wav")


@app.get("/api/sfx/{name}/peaks")
def sfx_peaks(name: str):
    """A sound effect's loudness for its waveform on the timeline (voiceover.peaks)."""
    return voiceover.peaks(_sfx_file(name))


class SoundSuggestRequest(BaseModel):
    script: VideoScript
    lengths: list[float] = []
    draft: str = ""      # its Director Plan's beats and shot notes guide the suggestions
    ai: bool = True      # ask Gemini (when a key is set); false: the rules only


@app.post("/api/sounds/suggest")
def sounds_suggest(req: SoundSuggestRequest):
    """A few sound events for the timeline, tied to the story beats and shots (sound_director.py). Nothing is added
    here: the editor shows them and adds the ones the creator ticks."""
    from . import sound_director

    plan = None
    if req.draft:
        try:
            plan = drafts.load(req.draft).plan
        except (KeyError, ValueError, OSError):
            pass
    existing = [c.start for c in req.script.clips if c.track == "sfx"]
    return sound_director.suggest(req.script, plan, req.lengths, existing, use_ai=req.ai and bool(os.getenv("GEMINI_API_KEY")))


@app.post("/api/edit/direct")
def edit_direct(req: SoundSuggestRequest):
    """The Edit Director's proposals for this draft (edit_director.py): calm scenes, graphics, sounds, each with its
    reason, and the footage gaps it won't cover up. Nothing is applied here: the editor applies the ticked ones."""
    from . import edit_director

    plan = None
    if req.draft:
        try:
            plan = drafts.load(req.draft).plan
        except (KeyError, ValueError, OSError):
            pass
    return edit_director.propose(req.script, plan, req.lengths, use_ai=req.ai and bool(os.getenv("GEMINI_API_KEY")))


MAX_SFX_SEC = 120


@app.post("/api/sfx/import")
def sfx_import(file: UploadFile = File(...), label: str = Form(...), category: str = Form(...),
               licence: str = Form(...), credit: str = Form(""), source: str = Form("")):
    """Add a sound to the library (assets/sfx), with the licence it comes under and the credit it asks for: the
    render puts that credit into the description. A sound with no known licence isn't taken."""
    from . import sfx

    ext = Path(file.filename or "").suffix.lower()
    label, credit, source = label.strip()[:60], credit.strip()[:200], source.strip()[:300]
    if ext not in sfx.AUDIO_EXTS:
        raise HTTPException(400, f"Use an audio file ({', '.join(sorted(sfx.AUDIO_EXTS))}).")
    if not label:
        raise HTTPException(400, "Give the sound a name.")
    if category not in sfx.CATEGORIES:
        raise HTTPException(400, f"Pick a category: {', '.join(sfx.CATEGORIES)}.")
    if licence not in sfx.LICENCES:
        raise HTTPException(400, "Pick the licence it comes under. A sound with no known licence can't be used.")
    if licence in sfx.NEEDS_CREDIT and not credit:
        raise HTTPException(400, f"{licence} asks for a credit: write who made it (as the source asks).")
    if source and not re.match(r"https?://", source):
        raise HTTPException(400, "The source should be a web address (https://...), or left empty.")
    sid = (re.sub(r"[^a-z0-9]+", "-", label.lower()).strip("-")[:28] or "sound") + "-" + uuid.uuid4().hex[:6]
    sfx.USER_DIR.mkdir(parents=True, exist_ok=True)
    dest = sfx.USER_DIR / f"{sid}{ext}"
    _save_upload(file, dest)
    try:
        seconds = duration(dest)
    except Exception:  # noqa: BLE001 - not audio ffmpeg can read
        seconds = 0
    if not 0.05 <= seconds <= MAX_SFX_SEC:
        dest.unlink(missing_ok=True)
        raise HTTPException(400, f"That isn't a sound file the app can read, or it's longer than {MAX_SFX_SEC} s.")
    info = {"label": label, "category": category, "licence": licence, "credit": credit, "source": source,
            "duration": round(seconds, 2), "file": dest.name, "imported": datetime.now().isoformat(timespec="seconds")}
    (sfx.USER_DIR / f"{sid}.json").write_text(json.dumps(info, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"name": f"user:{sid}", **info}


FILMSTRIP_CACHE = CACHE_DIR / "filmstrip"


@app.get("/api/filmstrip")
def filmstrip(path: str):
    """A strip of frames across a clip (one image, frames side by side) for the timeline, and the clip's length.
    Photos come back as themselves."""
    media = (ROOT / path).resolve()
    if not media.is_file() or ROOT.resolve() not in media.parents:
        raise HTTPException(404, "That file is gone.")
    if media.suffix.lower() in IMAGE_EXTS:
        return {"duration": 0, "frames": 1, "sprite": path}
    key = hashlib.sha1(f"{path}|{media.stat().st_mtime}".encode()).hexdigest()[:20]
    sprite = FILMSTRIP_CACHE / f"{key}.jpg"
    length = duration(media)
    frames = max(1, min(40, round(length)))
    if not sprite.exists():
        FILMSTRIP_CACHE.mkdir(parents=True, exist_ok=True)
        tmp = sprite.with_name(f"{key}.part.jpg")
        run_ffmpeg(["ffmpeg", "-y", "-hide_banner", "-i", str(media), "-vf",
                    f"fps={frames / max(length, 0.1):.4f},scale=72:128:force_original_aspect_ratio=increase,"
                    f"crop=72:128,tile={frames}x1", "-frames:v", "1", "-q:v", "5", str(tmp)])
        tmp.replace(sprite)
    return {"duration": round(length, 3), "frames": frames, "sprite": project_path(sprite)}


@app.get("/api/music/search")
def music_search(q: str):
    """Free instrumental tracks on Jamendo for some mood or style words, with a preview link each."""
    if not q.strip():
        raise HTTPException(400, "Type a mood or style, e.g. calm piano.")
    try:
        return {"results": music.search(q[:200])}
    except music.MusicError as e:
        raise HTTPException(400, str(e))


class MusicPick(BaseModel):
    id: str


@app.post("/api/music/pick")
def music_pick(req: MusicPick):
    """Download a Jamendo track into the music library (assets/music); returns its file name and credit."""
    try:
        name = music.download(req.id)
    except music.MusicError as e:
        raise HTTPException(400, str(e))
    return {"file": name, "credit": music.credit(name)}


class AutoFootageRequest(BaseModel):
    queries: list[str]  # search words of the scenes with automatic footage, in the order the render picks them
    hook: bool = False  # the first query is the video's opening scene (picked for its bright, lively opening)


@app.post("/api/footage/auto")
def auto_footage(req: AutoFootageRequest):
    """The clips the render would pick for scenes with automatic footage (the same picker, in the same order, so the
    live preview shows them), downloaded into the cache. null where nothing is found (the render then draws one)."""
    picker = FootagePicker()
    media = []
    for k, query in enumerate(req.queries[:60]):
        try:
            clip = picker.pick(query.strip() or "abstract background", hook=req.hook and k == 0)
        except Exception:
            traceback.print_exc()
            clip = None
        media.append(project_path(clip) if clip else None)
    return {"media": media}


class ImportRequest(BaseModel):
    text: str
    lang: str = "auto"  # "auto" detects Khmer vs English


@app.post("/api/import")
def import_pasted(req: ImportRequest):
    """Pasted free-form script -> structured script (Gemini, or the basic parser as a fallback)."""
    try:
        script, lang, method = import_script(req.text, req.lang, use_claude=bool(os.getenv("GEMINI_API_KEY")))
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
    except (llm.APIError, RuntimeError) as e:
        raise _llm_error(e)


# ---------- Excel content plan (one video per episode, see sheet.py) ----------

EXCEL_FILE = re.compile(r"^plan-[0-9a-f]{12}\.xlsx$")


def _plan_episodes(file: str, eps: list[int]) -> list[sheet.Episode]:
    if not EXCEL_FILE.match(file) or not (UPLOAD_DIR / file).is_file():
        raise HTTPException(404, "That spreadsheet is gone. Choose the file again.")
    chosen = [e for e in sheet.read_plan(UPLOAD_DIR / file) if e.ep in set(eps)]
    if not chosen:
        raise HTTPException(400, "Pick at least one episode.")
    return chosen


def _new_draft(e: sheet.Episode) -> str:
    draft_id, _ = drafts.create(drafts.Draft(script=e.script, lang=sheet.episode_lang(e), topic=e.topic))
    return draft_id


@app.post("/api/excel/read")
def excel_read(file: UploadFile = File(...)):
    """Upload a content plan and list its episodes (nothing is made yet)."""
    if Path(file.filename or "").suffix.lower() != ".xlsx":
        raise HTTPException(400, "Use an Excel workbook (.xlsx). In Excel or Google Sheets: Save as / Download → .xlsx.")
    dest = UPLOAD_DIR / f"plan-{uuid.uuid4().hex[:12]}.xlsx"
    _save_upload(file, dest)
    try:
        episodes = sheet.read_plan(dest)
    except Exception as e:
        dest.unlink(missing_ok=True)
        raise HTTPException(422, f"Couldn't read that workbook: {e}")
    if not episodes:
        dest.unlink(missing_ok=True)
        raise HTTPException(422, "No episodes found. The Scripts sheet needs rows under an 'Ep | … | Voiceover' header.")
    return {"file": dest.name, "name": file.filename, "episodes": [
        {"ep": e.ep, "title": e.title, "topic": e.topic, "status": e.status, "scenes": len(e.script.scenes),
         "posted": e.status.lower() == "posted"} for e in episodes]}


class ExcelRequest(BaseModel):
    file: str
    eps: list[int]
    voice: str | None = None
    rate: str = "+5%"
    music: str = ""


@app.post("/api/excel/drafts")
def excel_drafts(req: ExcelRequest):
    """One draft per chosen episode, footage searches planned by Gemini, to check and render one by one."""
    episodes = _plan_episodes(req.file, req.eps)
    sheet.plan_all(episodes, log=lambda line: None)
    return {"drafts": [{"ep": e.ep, "id": _new_draft(e), "title": e.script.title} for e in episodes]}


def _run_excel(job_id: str, req: ExcelRequest, episodes: list[sheet.Episode]) -> None:
    job = jobs[job_id]
    log = _job_logger(job, 5)
    with jobs_lock:
        job["status"] = "running"
    log("Planning footage for each scene…")
    sheet.plan_all(episodes, log=log)
    music = str(ASSETS_DIR / "music" / Path(req.music).name) if req.music and req.music != "none" else req.music
    made, failed = [], []
    for i, e in enumerate(episodes, 1):
        with jobs_lock:
            job.update(step=0, title=f"Ep {e.ep} ({i}/{len(episodes)}): {e.script.title}")
        log(f"=== Ep {e.ep} ({i}/{len(episodes)}): {e.script.title} ===")
        try:
            draft_id = _new_draft(e)  # editable afterwards, like any other video
            final = sheet.render_episode(e, log=log, voice=req.voice or None, rate=req.rate, music=music or None)
            meta_path = final.parent / "meta.json"
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            meta["draft"] = draft_id
            meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
            made.append(final.parent.name)
            with jobs_lock:
                job["video"] = final.parent.name
            _auto_publish(final.parent, log)
        except Exception as err:  # keep going with the next episode
            traceback.print_exc()
            failed.append(e.ep)
            log(f"  ! Ep {e.ep} failed: {str(err).strip().splitlines()[-1] if str(err).strip() else repr(err)}")
    summary = f"{len(made)} of {len(episodes)} videos made" + (f"; failed: Ep {', '.join(map(str, failed))}" if failed else "")
    log(summary)
    with jobs_lock:
        if made:
            job.update(status="done", step=5, summary=summary)
        else:
            job.update(status="error", error=summary)


@app.post("/api/excel/render")
def excel_render(req: ExcelRequest):
    """Render every chosen episode in one job (each also becomes a draft, so it can be fixed and rendered again)."""
    episodes = _plan_episodes(req.file, req.eps)
    job_id = uuid.uuid4().hex[:10]
    with jobs_lock:
        jobs[job_id] = {"id": job_id, "kind": "excel", "status": "queued", "step": 0, "log": [],
                        "title": f"{len(episodes)} episodes"}
    renderer.submit(_run_excel, job_id, req, episodes)
    return {"id": job_id}


def _run_render(job_id: str, req: RenderRequest) -> None:
    job = jobs[job_id]

    log = _job_logger(job, 5)

    with jobs_lock:
        job["status"] = "running"
    try:
        verdict = _history_sources(req) if req.draft_id else None
        music = req.music
        if music and music != "none":
            music = str(ASSETS_DIR / "music" / Path(music).name)
        final = make_video(req.topic or req.script.title, script=req.script, lang=req.lang,
                           voice=req.voice, rate=req.rate, music=music or None, log=log)
        if req.draft_id:
            meta_path = final.parent / "meta.json"
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            meta["draft"] = req.draft_id
            try:
                profiles.stamp(meta, drafts.load(req.draft_id).plan)
            except KeyError:  # the draft was deleted while it rendered
                pass
            if verdict is not None:
                meta["history_gate"] = verdict  # what was checked and approved, kept with the video
            meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
        with jobs_lock:
            job.update(status="done", step=5, video=final.parent.name)
        _auto_publish(final.parent, log)
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
    if req.draft_id:
        _history_gate_or_409("draft", req.draft_id)
    job_id = uuid.uuid4().hex[:10]
    with jobs_lock:
        jobs[job_id] = {"id": job_id, "status": "queued", "step": 0, "log": [], "title": req.script.title}
    renderer.submit(_run_render, job_id, req)
    return {"id": job_id}


# ---------- Songs (Gemini lyrics -> ElevenLabs Music) ----------

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
    except (llm.APIError, RuntimeError) as e:
        raise _llm_error(e)
    return song.model_dump()


def _run_song(job_id: str, req: SongComposeRequest) -> None:
    job = jobs[job_id]

    log = _job_logger(job, 3)

    with jobs_lock:
        job["status"] = "running"
    try:
        mix = make_song(req.topic or req.song.title, song=req.song, lang=req.lang, stems=req.stems, log=log)
        with jobs_lock:
            job.update(status="done", step=3, video=mix.parent.name)
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


def _run_music_video(job_id: str, folder: Path, req: "MusicVideoRequest") -> None:
    job = jobs[job_id]

    log = _job_logger(job, 4)

    with jobs_lock:
        job["status"] = "running"
    try:
        final = make_music_video(folder, log=log, idea=req.idea[:IDEA_MAX], look=req.look, lyric_style=req.lyric_style,
                                 art_style=req.art_style, pictures=req.pictures, direction=req.direction,
                                 cold_open=req.cold_open, now_playing=req.now_playing, fit=req.picture_fit)
        with jobs_lock:
            job.update(status="done", step=4, video=final.parent.name)
        _auto_publish(final.parent, log)
    except Exception as e:
        traceback.print_exc()
        with jobs_lock:
            job.update(status="error", error=str(e).strip().splitlines()[-1] if str(e).strip() else repr(e))


IDEA_MAX = 12000  # a scene-by-scene concept runs to a page or more (an uploaded .md idea doc)


class DirectRequest(BaseModel):
    idea: str


@app.post("/api/videos/{name}/direct")
def direct_video_idea(name: str, req: DirectRequest):
    """Gemini turns your concept into a shot list for the song: a scene and cutting pace per section, the recurring
    characters, a matching colour grade and lyric style, and notes on what can't be done literally. Saved with the
    song (one Gemini call); edit it in the app before planning pictures or rendering."""
    from . import director
    from .styles import LOOKS, PRESETS, available_fonts

    folder = _video_dir(name)
    if not (folder / "song.json").exists():
        raise HTTPException(400, "This isn't a song.")
    idea = req.idea.strip()[:IDEA_MAX]
    if len(idea) < 20:
        raise HTTPException(400, "Describe your idea first: the story, and what each part of the song shows.")
    song = SongScript.load(folder / "song.json")
    meta = _read_meta(folder)
    try:
        direction = director.direct_idea(
            song.title, song.mood, song.genre, [{"name": s.name, "lyrics": s.lyrics} for s in song.sections], idea,
            {k: v["label"] for k, v in LOOKS.items()}, {k: v["label"] for k, v in PRESETS.items()},
            available_fonts(meta.get("lang", "en")))
    except (llm.APIError, RuntimeError) as e:
        raise _llm_error(e)
    direction = {"idea": idea, **direction}
    _save_direction(folder, direction)
    return direction


class DirectionEdit(BaseModel):
    idea: str
    bible: str = ""
    sections: list[dict]
    notes: list[str] = []


@app.put("/api/videos/{name}/direct")
def edit_video_direction(name: str, req: DirectionEdit):
    """Save your changes to the shot list (scenes, paces, old-tape treatments, characters)."""
    from .director import clean_section

    folder = _video_dir(name)
    song = SongScript.load(folder / "song.json")
    if len(req.sections) != len(song.sections):
        raise HTTPException(409, "The song's sections changed; direct the idea again.")
    direction = {"idea": req.idea.strip()[:IDEA_MAX], "bible": req.bible.strip()[:2000], "notes": req.notes[:6],
                 "sections": [clean_section(r) for r in req.sections]}
    _save_direction(folder, direction)
    return direction


def _save_direction(folder: Path, direction: dict) -> None:
    meta = _read_meta(folder)
    meta["direction"] = direction
    (folder / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")


class MusicVideoRequest(BaseModel):
    idea: str = ""  # your idea for the video; the footage follows it
    look: str = ""  # colour grade (styles.LOOKS); "" = the song's last one
    lyric_style: dict | None = None  # styles.LyricStyle fields; None = the song's last one
    art_style: str | None = None  # "" = stock footage, else an AI art look (imagegen.STYLES); None = the song's last
    pictures: str | None = None  # how many AI pictures (pipeline.PICTURE_PACES); None = the song's last choice
    direction: dict | None = None  # the shot list for the idea (POST .../direct); None = the song's, if it fits
    cold_open: bool | None = None  # the song's name in neon over the opening; None = the song's last choice
    now_playing: bool | None = None  # a now-playing card (title, progress, spinning record); None = the song's last
    picture_fit: str | None = None  # a cover picture "fit" (whole, on its colour) or "fill"s the screen; None = last


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
    renderer.submit(_run_music_video, job_id, folder, req or MusicVideoRequest())
    return {"id": job_id}


# ---------- Smart Highlights (crcontent/highlights: the best Shorts / Reels clips of a music video) ----------

class HighlightsRequest(BaseModel):
    ai_judge: bool | None = None  # None = highlights.json's "ai_judge.enabled"
    artist: str = ""  # drawn under the title on the covers


def _highlights_job(name: str) -> str | None:
    """The id of a queued or running highlights job for this video."""
    with jobs_lock:
        return next((j["id"] for j in jobs.values() if j.get("kind") == "highlights" and j.get("source") == name
                     and j["status"] in ("queued", "running")), None)


def _run_highlights(job_id: str, folder: Path, req: HighlightsRequest) -> None:
    from .highlights import make_highlights

    job = jobs[job_id]
    log = _job_logger(job, 7)
    with jobs_lock:
        job["status"] = "running"
    try:
        make_highlights(folder, artist=req.artist.strip()[:80], ai_judge=req.ai_judge, log=log)
        # the clips are alternatives to choose from, so they aren't auto-uploaded like other renders
        with jobs_lock:
            job.update(status="done", step=7)
    except Exception as e:
        traceback.print_exc()
        with jobs_lock:
            job.update(status="error", error=str(e).strip().splitlines()[-1] if str(e).strip() else repr(e))


@app.post("/api/videos/{name}/highlights")
def find_highlights(name: str, req: HighlightsRequest | None = None):
    """Pick the video's best 15–30 s for Shorts / Reels, make covers, render the top 3 as clips and write a report
    (several minutes). A run already going for this video is returned instead of starting another."""
    folder = _video_dir(name)
    if not (folder / "video.mp4").exists() or not (folder / "lyrics.json").exists():
        raise HTTPException(400, "Smart Highlights needs a music video with timed lyrics.")
    running = _highlights_job(name)
    if running:
        return {"id": running}
    job_id = uuid.uuid4().hex[:10]
    with jobs_lock:
        jobs[job_id] = {"id": job_id, "kind": "highlights", "status": "queued", "step": 0, "log": [],
                        "title": _summary(folder)["title"], "source": name}
    renderer.submit(_run_highlights, job_id, folder, req or HighlightsRequest())
    return {"id": job_id}


@app.get("/api/videos/{name}/highlights")
def get_highlights(name: str):
    """The last Smart Highlights report (files relative to the video's folder; a clip's `job` is "" once it's been
    deleted) and the id of a run still going."""
    folder = _video_dir(name)
    path = folder / "highlights" / "report.json"
    report = None
    if path.exists():
        try:
            report = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            report = None
    if report:
        report.pop("curve", None)  # per-second curves: only the HTML report draws them
        for e in report.get("candidates", []):
            e["covers"] = [{**c, "file": f"highlights/{c['file']}"} for c in e.get("covers", [])]
            e["job"] = e.get("job", "") if e.get("job") and (OUTPUT_DIR / e["job"] / "video.mp4").exists() else ""
            e.pop("video", None)
        report["page"] = "highlights/report.html"
    return {"report": report, "job": _highlights_job(name)}


# ---------- Script to Video (crcontent/longform: a long YouTube video from a script .md) ----------
# The storyboard page (<job>/storyboard.html, served under /media) calls these to swap footage and approve.

class FootagePick(BaseModel):
    key: str


class FootageSearch(BaseModel):
    query: str


def _longform_dir(name: str) -> Path:
    folder = _video_dir(name)
    if not (folder / "footage.json").exists():
        raise HTTPException(404, "This isn't a Script to Video storyboard.")
    return folder


def _longform_job(name: str) -> str | None:
    """The id of a queued or running render of this storyboard."""
    with jobs_lock:
        return next((j["id"] for j in jobs.values() if j.get("kind") == "long_video" and j.get("source") == name
                     and j["status"] in ("queued", "running")), None)


def _longform_busy(name: str) -> None:
    if _longform_job(name):
        raise HTTPException(409, "It's rendering: changes have to wait until it's done.")


@app.post("/api/longform/{name}/scenes/{n}/pick")
def longform_pick(name: str, n: int, req: FootagePick):
    """Scene `n` uses one of its alternatives (downloaded and checked now)."""
    from . import longform

    folder = _longform_dir(name)
    _longform_busy(name)
    try:
        return longform.pick_footage(folder, n, req.key)
    except KeyError as e:
        raise HTTPException(404, str(e).strip("'\""))
    except (requests.RequestException, ValueError, OSError) as e:
        raise HTTPException(502, f"Couldn't get that one ({type(e).__name__}): try another.")


@app.post("/api/longform/{name}/scenes/{n}/search")
def longform_search(name: str, n: int, req: FootageSearch):
    """New alternatives for scene `n` from other search words."""
    from . import longform

    folder = _longform_dir(name)
    _longform_busy(name)
    try:
        return longform.search_footage(folder, n, req.query)
    except KeyError as e:
        raise HTTPException(404, str(e).strip("'\""))
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.post("/api/longform/{name}/reload")
def longform_reload(name: str):
    """Use the files put in media/<script>/ (scene-XX.*) since the storyboard was made."""
    from . import longform

    folder = _longform_dir(name)
    _longform_busy(name)
    entries, found = longform.reload_media(folder)
    return {"footage": entries, "found": found}


@app.post("/api/longform/{name}/scenes/{n}/upload")
def longform_upload(name: str, n: int, file: UploadFile = File(...)):
    """Scene `n` uses your own clip or photo (saved as scene-NN.<ext> in the script's media folder)."""
    from . import longform

    folder = _longform_dir(name)
    _longform_busy(name)
    tmp = UPLOAD_DIR / f"scene-{uuid.uuid4().hex[:12]}{Path(file.filename or '').suffix.lower()}"
    _save_upload(file, tmp)
    try:
        return longform.use_own_file(folder, n, tmp, file.filename or tmp.name)
    except KeyError as e:
        raise HTTPException(404, str(e).strip("'\""))
    except ValueError as e:
        raise HTTPException(400, str(e))
    finally:
        tmp.unlink(missing_ok=True)


LONG_SCRIPTS = ROOT / "scripts"  # uploaded script .md files; the file name picks its media/<name>/ folder


def _analytics_view(data: dict | None) -> dict:
    from .shorts import analytics

    if not data:
        return {"imported": None}
    return {"imported": data.get("imported", ""), "videos": len(data.get("videos", [])),
            "summary": data.get("summary", {}), "evidence": analytics.director_brief(data)[1],
            "min_videos": analytics.EVIDENCE_MIN}


@app.get("/api/analytics")
def analytics_get():
    """The last YouTube Studio import (what the AI Director and the hook judge are given)."""
    from .shorts import analytics

    return _analytics_view(analytics.load())


@app.post("/api/analytics")
def analytics_import(file: UploadFile = File(...)):
    """Import YouTube Studio's Content export: the .csv, or the .zip it downloads as (its "Table data.csv")."""
    import csv
    import io
    import tempfile
    import zipfile

    from .shorts import analytics

    name = Path(file.filename or "").name
    data = file.file.read(20_000_001)
    if len(data) > 20_000_000:
        raise HTTPException(400, "That file is too big for a Studio export.")
    with tempfile.TemporaryDirectory() as tmp:
        csv_path = Path(tmp) / "Table data.csv"
        if name.lower().endswith(".zip"):
            try:
                with zipfile.ZipFile(io.BytesIO(data)) as z:
                    inner = [n for n in z.namelist() if n.lower().endswith(".csv")]
                    pick = next((n for n in inner if Path(n).name.lower() == "table data.csv"), inner[0] if inner else None)
                    if pick is None:
                        raise HTTPException(400, "No .csv inside that zip. Export the Content tab from YouTube Studio.")
                    csv_path.write_bytes(z.read(pick))
            except zipfile.BadZipFile:
                raise HTTPException(400, "That zip can't be opened.")
        elif name.lower().endswith(".csv"):
            csv_path.write_bytes(data)
        else:
            raise HTTPException(400, "Use the .csv (or .zip) YouTube Studio exports.")
        try:
            saved = analytics.import_csv(csv_path)
        except (ValueError, csv.Error, UnicodeDecodeError) as e:
            raise HTTPException(400, f"Couldn't read it: {e}")
    saved["source"] = name  # not the temp file's path
    analytics.PATH.write_text(json.dumps(saved, ensure_ascii=False, indent=2), encoding="utf-8")
    return _analytics_view(saved)


def _run_storyboard(job_id: str, script_md: Path, plan=None, choice: dict | None = None) -> None:
    from . import longform

    job = jobs[job_id]
    log = _job_logger(job, longform.STEPS)
    with jobs_lock:
        job["status"] = "running"
    try:
        if plan is not None:
            plan = _direct_or_keep(plan, log)
        folder = longform.make_storyboard(script_md, log=log, choice=choice)
        if plan is not None:  # a Script-to-Video project keeps its Director Plan beside the storyboard
            (folder / "plan.json").write_text(plan.model_dump_json(indent=2), encoding="utf-8")
            if plan.project.channel_profile_id:
                meta = profiles.stamp(_read_meta(folder), plan)
                (folder / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
        with jobs_lock:
            job.update(status="done", step=5, video=folder.name, source=folder.name)
    except Exception as e:
        _fail(job, e)


@app.post("/api/longform")
def longform_new(file: UploadFile = File(...)):
    """A long 16:9 video from a script .md: voiceover, timing and footage up to the storyboard to check (steps 1-5)."""
    from .longform.parse import parse

    name = Path(file.filename or "").name
    if Path(name).suffix.lower() not in (".md", ".markdown", ".txt"):
        raise HTTPException(400, "Use the script as a .md file (a markdown table: Time | Visual | On-screen Text | Voiceover).")
    data = file.file.read(2_000_001)
    if len(data) > 2_000_000:
        raise HTTPException(400, "That script is too big (over 2 MB). It should be text only.")
    stem = re.sub(r"[^\w\-. ]+", "", Path(name).stem).strip(" .") or "script"
    LONG_SCRIPTS.mkdir(parents=True, exist_ok=True)
    dest = LONG_SCRIPTS / f"{stem}.md"
    dest.write_bytes(data)
    try:  # catch a script the app can't read now, not minutes into the job
        script = parse(dest)
    except Exception as e:
        raise HTTPException(400, f"Couldn't read that script: {str(e).strip().splitlines()[-1] if str(e).strip() else type(e).__name__}")
    if not script.scenes:
        raise HTTPException(400, "No scenes found. The script needs a table with the columns Time | Visual | On-screen Text | Voiceover.")
    job_id = uuid.uuid4().hex[:10]
    with jobs_lock:
        jobs[job_id] = {"id": job_id, "kind": "long_video", "status": "queued", "step": 0, "log": [], "title": script.title}
    renderer.submit(_run_storyboard, job_id, dest)
    return {"id": job_id, "title": script.title, "scenes": len(script.scenes), "notes": script.notes}


class ScriptVideoRequest(BaseModel):
    text: str
    format: str  # "short" (9:16 draft) or "long" (16:9 storyboard)
    lang: str = "auto"
    visual_style: str = director_plan.STYLES[0]
    voice: str = ""  # "" = the language's default voice (a long video: the one in Settings → Script Video)
    rate: str = ""
    music: str = ""  # "" = matches the mood (a long video: your tracks in Settings), "none", or a track in assets/music
    target_seconds: float = 0  # optional; a pacing hint for the AI Director, the narration is never cut
    channel_profile_id: str = ""  # profiles.PROFILES key; "" = the general defaults
    research_brief_id: str = ""   # an approved topic brief the script was written from (a Short then keeps it)


RATES = ("-10%", "+0%", "+5%", "+15%")  # the editor's Speed choices


@app.post("/api/script-video")
def script_video(req: ScriptVideoRequest):
    """Script to Video: a pasted finished script becomes a project in either format, with its Director Plan saved.
    A Short opens as a draft; a Long Video starts the storyboard job (voiceover, timing, footage)."""
    from .longform.parse import parse

    if req.format not in director_plan.ASPECTS:
        raise HTTPException(400, "Choose Short or Long video.")
    if req.visual_style not in director_plan.STYLES:
        raise HTTPException(400, f"Unknown visual style {req.visual_style}.")
    if len(req.text) > 2_000_000:
        raise HTTPException(400, "That script is too big (over 2 MB). It should be text only.")
    if req.rate and req.rate not in RATES:
        raise HTTPException(400, f"Unknown speed {req.rate}.")
    if req.music not in ("", "none") and not (ASSETS_DIR / "music" / Path(req.music).name).is_file():
        raise HTTPException(400, f"Music track not found: {req.music}")
    if not 0 <= req.target_seconds <= 4 * 3600:
        raise HTTPException(400, "The target length should be between 0 and 4 hours.")
    if req.voice and req.voice not in {v for code in LANGS for v in _voices(code)}:
        raise HTTPException(400, f"Unknown voice {req.voice}.")
    profile, profile_note = profiles.resolve(req.channel_profile_id)
    if req.research_brief_id and req.format != "short":
        raise HTTPException(400, "A script written from research becomes a Short; long videos can't take it yet.")

    def tag(plan):  # the project remembers its channel profile (none: the general defaults, as before profiles)
        if profile:
            plan.project.channel_profile_id, plan.project.channel_profile_version = profile.id, profile.version
        return plan

    if req.format == "long":  # a script already written as the long-video table keeps its chapters and title cards
        LONG_SCRIPTS.mkdir(parents=True, exist_ok=True)
        probe = LONG_SCRIPTS / f".paste-{uuid.uuid4().hex[:8]}.md"
        probe.write_text(req.text, encoding="utf-8")
        try:
            table = parse(probe)
        except Exception:  # not a table (or not one it can read): the importer below handles any layout
            table = None
        finally:
            probe.unlink(missing_ok=True)
        if table:
            title = "Untitled" if table.title == probe.stem else table.title  # no "# Title" line
            plan = director_plan.from_scenes(title, "long", table.lang, req.visual_style, [
                {"narration": s.voiceover, "visual_query": s.visual, "on_screen_text": s.text} for s in table.scenes])
            plan.project.target_seconds = req.target_seconds
            return _start_long(req.text, tag(plan), _choice(req)) | {"profile_note": profile_note}
    try:
        script, lang, method = import_script(req.text, req.lang, use_claude=bool(os.getenv("GEMINI_API_KEY")))
    except ValueError as e:
        raise HTTPException(422, str(e))
    plan = director_plan.from_scenes(script.title, req.format, lang, req.visual_style,
                                     [s.model_dump() for s in script.scenes])
    plan.project.target_seconds = req.target_seconds
    tag(plan)
    if req.format == "long":  # the job directs it, so the plan shows up in its progress log
        return _start_long(director_plan.longform_markdown(plan), plan, _choice(req)) | {"method": method, "profile_note": profile_note}
    problems: list[str] = []
    research = _topic_research(req.research_brief_id, plan) if req.research_brief_id else None
    plan = _direct_or_keep(plan, problems.append, research)
    if research is not None:  # also when Gemini didn't direct it: linking claims needs no model
        from . import ai_director

        plan = ai_director.link_research(plan, research)
    voice = req.voice if req.voice in _voices(lang) else ""  # a voice for the other language: its default instead
    voice_note = f"{req.voice} doesn't speak this script's language, so the default voice is used." if req.voice and not voice else ""
    draft_id, _ = drafts.create(drafts.Draft(script=script, lang=lang, topic=script.title, plan=plan, voice=voice,
                                             rate=req.rate or drafts.Draft.model_fields["rate"].default, music=req.music))
    if research is not None:  # the topic's approved research now belongs to this project
        from .history import research as hr

        hr.write(_research_path("draft", draft_id), research.model_copy(update={
            "id": draft_id, "project_kind": "draft", "project_ref": draft_id, "written_script": []}))
    footage_job = _start_plan_footage("draft", draft_id, [], script.title)  # the AI finds the footage, not the user
    return {"format": "short", "id": draft_id, "title": script.title, "scenes": len(script.scenes), "method": method,
            "planned_by": plan.planned_by, "director_note": problems[-1] if problems else "", "footage_job": footage_job,
            "voice_note": voice_note, "profile_note": profile_note}


def _direct_or_keep(plan: "director_plan.DirectorPlan", log, research=None) -> "director_plan.DirectorPlan":
    """The AI Director's plan when Gemini is set up and answers; otherwise the plan seeded from the script, said in `log`."""
    from . import ai_director

    if not os.getenv("GEMINI_API_KEY"):
        log("Director: Gemini isn't set up, so the plan is one shot per scene from your script. Add a key in Settings.")
        return plan
    log("Director: reading the whole script and planning the shots")
    try:
        directed = ai_director.direct(plan, research=research)
    except (llm.APIError, RuntimeError, ValueError) as e:
        log(f"Director: couldn't plan the shots ({_llm_error(e).detail if isinstance(e, llm.APIError) else e}); "
            "kept one shot per scene from your script")
        return plan
    log(f"Director: {len(directed.shots)} shots planned for {len(directed.scenes)} scenes")
    return directed


def _choice(req: ScriptVideoRequest) -> dict | None:
    """A long video's own voice, speed and music from the form (None: the Script Video settings as they are)."""
    return {"voice": req.voice, "rate": req.rate, "music": req.music} if req.voice or req.rate or req.music else None


def _start_long(markdown: str, plan: "director_plan.DirectorPlan", choice: dict | None = None) -> dict:
    from .pipeline import slugify

    # the file name picks media/<name>/ for the user's own clips: never overwrite another script's file
    stem = slugify(plan.project.title)
    dest = LONG_SCRIPTS / f"{stem}.md"
    if dest.exists():
        dest = LONG_SCRIPTS / f"{stem}-{datetime.now():%Y%m%d-%H%M%S}.md"
    dest.write_text(markdown, encoding="utf-8")
    job_id = uuid.uuid4().hex[:10]
    with jobs_lock:
        jobs[job_id] = {"id": job_id, "kind": "long_video", "status": "queued", "step": 0, "log": [], "title": plan.project.title}
    renderer.submit(_run_storyboard, job_id, dest, plan, choice)
    return {"format": "long", "id": job_id, "title": plan.project.title, "scenes": len(plan.scenes)}


def _run_long_video(job_id: str, folder: Path) -> None:
    from . import longform

    job = jobs[job_id]
    log = _job_logger(job, longform.STEPS)
    with jobs_lock:
        job["status"] = "running"
    try:
        longform.render_video(folder, log=log)
        with jobs_lock:
            job.update(status="done", step=longform.STEPS, video=folder.name)
    except Exception as e:
        _fail(job, e)


@app.post("/api/longform/{name}/approve")
def longform_approve(name: str):
    """Approve the storyboard as it is now and render it (steps 6-7: many minutes for a 10 minute video)."""
    from .longform import storyboard

    folder = _longform_dir(name)
    running = _longform_job(name)
    if running:
        return {"id": running}
    if (verdict := _history_gate_or_409("long", name)) is not None:
        meta = _read_meta(folder)
        meta["history_gate"] = verdict
        (folder / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    storyboard.approve(folder)
    job_id = uuid.uuid4().hex[:10]
    with jobs_lock:
        jobs[job_id] = {"id": job_id, "kind": "long_video", "status": "queued", "step": 5, "log": [],
                        "title": _summary(folder)["title"], "source": name}
    renderer.submit(_run_long_video, job_id, folder)
    return {"id": job_id}


# ---------- Director Plans: read, edit and re-direct the plan of a Script-to-Video project ----------
# kind "draft": a Short's draft id (the plan lives in draft.json); kind "long": a long video's output folder (plan.json);
# kind "short": a Shorts Mode job folder (plan.json, made at its step 1; its footage is found by making it again).

plan_busy: set[str] = set()
plan_jobs: dict[str, str] = {}  # "kind/ref" -> its footage job id while one is queued or running
footage_pool = JobPool(max_workers=1)  # footage searches don't wait behind a render


def _plan_get(kind: str, ref: str) -> "director_plan.DirectorPlan":
    if kind == "draft":
        try:
            plan = drafts.load(ref).plan
        except KeyError:
            raise HTTPException(404, "Draft not found. It may have been deleted.")
    elif kind in ("long", "short"):
        path = _plan_file(kind, ref)
        try:
            plan = director_plan.DirectorPlan.model_validate_json(path.read_text(encoding="utf-8")) if path.exists() else None
        except ValueError as e:  # hand-edited or from a newer app
            raise HTTPException(422, f"This project's plan.json can't be read: {str(e).splitlines()[0]}")
    else:
        raise HTTPException(404, "Unknown project kind.")
    if plan is None and kind == "short":  # made before the AI Director: one shot per beat until it's made again
        from .shorts import directed, plan as splan

        plan = directed.seed(splan.ShortPlan.load(_short_dir(ref) / "episode.json"))
    if plan is None:
        raise HTTPException(404, "This project has no Director Plan. Projects made with Script to video have one.")
    return plan


def _plan_file(kind: str, ref: str) -> Path:
    return (_short_dir(ref) if kind == "short" else _longform_dir(ref)) / "plan.json"


def _plan_put(kind: str, ref: str, plan: "director_plan.DirectorPlan") -> None:
    if kind == "draft":
        draft = drafts.load(ref)
        draft.plan = plan
        drafts.save(ref, draft)
    else:
        path = _plan_file(kind, ref)
        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(plan.model_dump_json(indent=2), encoding="utf-8")
        os.replace(tmp, path)


def _plan_media(kind: str, ref: str) -> Path:
    """Where the user's own clips for a plan go: shot-003-2.mp4 (or scene-03.mp4 for a scene's first shot)."""
    from . import longform
    from .longform import settings as lsettings
    from .longform.parse import Script

    if kind == "short":
        from . import shorts
        from .shorts import settings as ssettings

        return shorts.media_folder(Script.load(_short_dir(ref) / "scenes.json").slug, ssettings.load())
    cfg = lsettings.load()
    if kind == "long":
        return longform.media_folder(Script.load(_longform_dir(ref) / "scenes.json").slug, cfg)
    return longform.media_folder(ref, cfg)


# ---------- Research briefs (Hidden History Files spec, H2): source-backed claims for a project or a topic ----------
# kind "draft" / "long": research.json in the project's folder; kind "topic": <data>/research/<id>.json.

research_jobs: dict[str, str] = {}  # "kind/ref" -> its research job id while queued or running


def _research_path(kind: str, ref: str) -> Path:
    if kind == "draft":
        folder = drafts.DRAFTS_DIR / ref
        if not ref or ref.startswith(".") or folder.resolve().parent != drafts.DRAFTS_DIR.resolve() \
                or not (folder / "draft.json").exists():
            raise HTTPException(404, "Draft not found. It may have been deleted.")
        return folder / "research.json"
    if kind == "long":
        return _longform_dir(ref) / "research.json"
    if kind == "topic":
        if not re.fullmatch(r"[0-9a-f]{10}", ref):
            raise HTTPException(404, "Research brief not found.")
        return ROOT / "research" / f"{ref}.json"
    raise HTTPException(404, "Unknown project kind.")


def _research_scenes(kind: str, ref: str) -> list[tuple[str, str]]:
    """The project's narration as (plan scene id, text); nothing for a topic."""
    if kind == "topic":
        return []
    try:
        return [(s.id, s.narration) for s in _plan_get(kind, ref).scenes if s.narration.strip()]
    except HTTPException:
        if kind != "draft":
            raise
        return [(f"scene-{i:03d}", s.narration) for i, s in enumerate(drafts.load(ref).script.scenes, 1) if s.narration.strip()]


def _research_brief(kind: str, ref: str):
    from .history import research

    path = _research_path(kind, ref)
    try:
        return path, research.load(path)
    except ValueError as e:
        raise HTTPException(422, f"This research brief can't be read: {str(e).splitlines()[0]}")


def _run_research(job_id: str, kind: str, ref: str) -> None:
    from .history import research

    job = jobs[job_id]
    log = _job_logger(job, research.STEPS)
    with jobs_lock:
        job["status"] = "running"
    try:
        path, brief = _research_brief(kind, ref)
        research.run(path, brief or research.new(kind, ref), _research_scenes(kind, ref), log=log)
        with jobs_lock:
            job.update(status="done", step=research.STEPS)
    except Exception as e:
        _fail(job, e)


def _start_research(kind: str, ref: str, title: str) -> str:
    key = f"{kind}/{ref}"
    with jobs_lock:
        running = research_jobs.get(key)
        if running and jobs.get(running, {}).get("status") in ("queued", "running"):
            return running
        job_id = uuid.uuid4().hex[:10]
        jobs[job_id] = {"id": job_id, "kind": "research", "status": "queued", "step": 0, "log": [], "title": title}
        research_jobs[key] = job_id
    footage_pool.submit(_run_research, job_id, kind, ref)
    return job_id


class TopicResearchRequest(BaseModel):
    topic: str


@app.post("/api/research/topic")
def research_topic(req: TopicResearchRequest):
    """Topic workflow: a new research brief for a topic, researched in the background (watch /api/jobs/<id>)."""
    from .history import research

    topic = req.topic.strip()
    if len(topic) < 3 or len(topic) > 500:
        raise HTTPException(400, "Describe the topic in a few words (up to 500 characters).")
    brief = research.new("topic", "", topic)
    brief.project_ref = brief.id
    research.write(_research_path("topic", brief.id), brief)
    return {"id": brief.id, "job": _start_research("topic", brief.id, topic)}


@app.get("/api/research/{kind}/{ref}")
def research_get(kind: str, ref: str):
    from .history import research

    _, brief = _research_brief(kind, ref)
    running = research_jobs.get(f"{kind}/{ref}")
    running = running if running and jobs.get(running, {}).get("status") in ("queued", "running") else None
    return {"brief": brief, "job": running, "blockers": research.blockers(brief) if brief else []}


@app.post("/api/research/{kind}/{ref}/run")
def research_run(kind: str, ref: str):
    """Research (or re-check) the brief: claims, sources and evidence. Claims the creator edited are kept."""
    path, brief = _research_brief(kind, ref)
    if kind != "topic" and not _research_scenes(kind, ref):
        raise HTTPException(400, "This project has no narration to research yet.")
    return {"id": _start_research(kind, ref, brief.topic if brief else ref)}


@app.put("/api/research/{kind}/{ref}")
def research_save(kind: str, ref: str, brief: ResearchBriefModel):
    """Save the creator's edits; statuses are settled from the attached evidence again."""
    from .history import research

    path, _ = _research_brief(kind, ref)
    brief.project_kind, brief.project_ref = kind, ref
    return research.save_edit(path, brief)


class SourceRequest(BaseModel):
    url: str
    note: str = ""
    excerpt: str = ""


@app.post("/api/research/{kind}/{ref}/sources")
def research_add_source(kind: str, ref: str, req: SourceRequest):
    """Add a source by its link (with an optional note and the passage that backs a claim)."""
    from .history import research

    path, brief = _research_brief(kind, ref)
    try:
        return research.add_source(path, brief or research.new(kind, ref), req.url, req.note, req.excerpt)
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.post("/api/research/{kind}/{ref}/approve")
def research_approve(kind: str, ref: str):
    """Approve the brief; a project's Director Plan then carries its claims (scene claim ids, key facts)."""
    from . import ai_director
    from .history import research

    path, _ = _research_brief(kind, ref)
    try:
        brief = research.approve(path)
    except ValueError as e:
        raise HTTPException(409, str(e))
    if kind != "topic":
        try:
            _plan_put(kind, ref, ai_director.link_research(_plan_get(kind, ref), brief))
        except HTTPException:
            pass  # a project without a Director Plan: nothing to link
    return brief


def _approved_research(kind: str, ref: str):
    """The project's research brief when it's approved (what the AI Director may rely on), else None."""
    if kind not in ("draft", "long"):
        return None
    try:
        _, brief = _research_brief(kind, ref)
    except HTTPException:
        return None
    return brief if brief and brief.research_status == "approved" else None


def _topic_research(brief_id: str, plan: "director_plan.DirectorPlan"):
    """An approved topic brief, its claims linked to the plan's scenes by the script written from it."""
    from .history import script as hscript

    _, brief = _research_brief("topic", brief_id)
    if brief is None or brief.research_status != "approved":
        raise HTTPException(409, "Approve the research before making the video from it.")
    return hscript.attach(brief, brief.written_script, [s.id for s in plan.scenes], [s.narration for s in plan.scenes])


def _history_project(kind: str, ref: str):
    """(plan, approved-or-not research brief, folder) of a history project; None when it isn't one."""
    from .ai_director import is_history

    if kind not in ("draft", "long"):
        raise HTTPException(404, "Unknown project kind.")
    plan = _plan_get(kind, ref)
    if not is_history(plan):
        return None
    path, brief = _research_brief(kind, ref)
    return plan, brief, path.parent


def _history_gate_or_409(kind: str, ref: str) -> dict | None:
    """The gate's verdict for a history project's render (None: not a history project); 409 unless it's ready."""
    from .history import gate

    try:
        found = _history_project(kind, ref)
    except HTTPException as e:
        if e.status_code == 404 and kind == "draft":
            return None  # an ordinary draft without a Director Plan
        raise
    if found is None:
        return None
    verdict = gate.evaluate(*found)
    if verdict["status"] != "ready":
        left = [it["title"] for it in verdict["items"] if not it["approved"]]
        word = "blocked" if verdict["status"] == "blocked" else "waiting for your review"
        raise HTTPException(409, f"History check {word}: {'; '.join(left[:4])}{' …' if len(left) > 4 else ''}. "
                                 "Open the Pre-render check to see and resolve each item.")
    return {"status": "ready", "checked_at": verdict["checked_at"], "approved": verdict["approved"], "open": [],
            "trace": gate.trace(found[0], found[1])}


def _history_sources(req: RenderRequest) -> dict | None:
    """A history draft's render: the research sources (and rights the creator confirmed) go into post.txt."""
    from .history import gate

    try:
        found = _history_project("draft", req.draft_id)
    except HTTPException:
        return None
    if found is None:
        return None
    plan, brief, folder = found
    confirmed = [f"- {s.footage.page or s.footage.source}: rights confirmed by the creator ({s.footage.rights_note})"
                 for s in plan.shots if s.footage and s.footage.rights_note]
    listed = "\n".join(x for x in (gate.sources_text(plan, brief), gate.credits_text(plan, req.script.clips), *confirmed) if x)
    if listed:
        req.script.sources = "\n".join(x for x in (req.script.sources.strip(), listed) if x)
    verdict = gate.evaluate(plan, brief, folder)
    return {"status": verdict["status"], "checked_at": verdict["checked_at"], "approved": verdict["approved"],
            "open": [{"key": it["key"], "level": it["level"], "title": it["title"]} for it in verdict["items"] if not it["approved"]],
            "trace": gate.trace(plan, brief)}


def _history_publish_block(folder: Path) -> str:
    """Why a rendered history video may not go out ("" = it may): it needs the gate's passing verdict, recorded when
    it was rendered."""
    meta = _read_meta(folder)
    if meta.get("channel_profile_id") != "hidden_history_files":
        return ""
    if (meta.get("history_gate") or {}).get("status") == "ready":
        return ""
    return ("This history video wasn't rendered through the history check (sources, rights, misleading pictures). "
            "Resolve the check in its draft and render it again.")


@app.get("/api/history/{kind}/{ref}/gate")
def history_gate(kind: str, ref: str):
    from .history import gate

    found = _history_project(kind, ref)
    if found is None:
        return {"status": "not_history", "items": [], "approved": []}
    return {**gate.evaluate(*found), "trace": gate.trace(found[0], found[1])}


# ---------- AI reconstructions (H6): drawn from approved research, labelled, reviewable ----------

def _reconstruction_shot(kind: str, ref: str, shot_id: str):
    from .history import reconstruct

    found = _history_project(kind, ref)
    if found is None:
        raise HTTPException(400, "Reconstructions are for Hidden History projects.")
    plan, brief, _ = found
    shot = next((s for s in plan.shots if s.id == shot_id), None)
    if shot is None:
        raise HTTPException(404, "That shot isn't in the plan any more.")
    try:
        return plan, shot, reconstruct.brief(plan, shot, brief)
    except ValueError as e:
        raise HTTPException(409, str(e))


@app.get("/api/history/{kind}/{ref}/shots/{shot_id}/reconstruction")
def reconstruction_brief(kind: str, ref: str, shot_id: str):
    """The shot's reconstruction brief (what's verified, what's uncertain, what mustn't be invented) and its prompt."""
    from . import imagegen

    _, _, b = _reconstruction_shot(kind, ref, shot_id)
    return {"brief": b, "installed": imagegen.installed()}


class ReconstructRequest(BaseModel):
    prompt: str = Field("", max_length=600)  # the creator's edit of the brief's prompt ("" = as built)
    seed: int | None = None                  # None: a new picture each time


def _run_reconstruction(job_id: str, kind: str, ref: str, shot_id: str, b: dict, seed: int | None, fmt: str) -> None:
    from . import shot_footage
    from .history import reconstruct

    job = jobs[job_id]
    job["status"] = "running"
    try:
        f = reconstruct.draw(b, shot_footage.SIZES[fmt], seed,
                             log=lambda m: job["log"].append(str(m)))
        plan = _plan_get(kind, ref)  # again: the plan may have changed while it drew
        shot = next(s for s in plan.shots if s.id == shot_id)
        if shot.footage and shot.footage.asset_type == "reconstruction":
            shot.candidates.insert(0, shot.footage)  # the earlier drawing stays as an alternative
        shot.footage, shot.locked = f, True
        shot.warnings = shot_footage.warnings_for(shot, plan.project.format, True)
        _plan_put(kind, ref, plan)
        job.update(status="done", step=1, summary=f"Drew the reconstruction for {shot_id}")
    except Exception as e:
        _fail(job, e)


@app.post("/api/history/{kind}/{ref}/shots/{shot_id}/reconstruction")
def reconstruction_draw(kind: str, ref: str, shot_id: str, req: ReconstructRequest):
    """Draw (or redraw) the shot's reconstruction with the local generator, in the background (watch /api/jobs/<id>)."""
    import random

    from . import imagegen

    plan, _, b = _reconstruction_shot(kind, ref, shot_id)
    if not imagegen.installed():
        raise HTTPException(400, "The local image generator isn't installed (Settings → AI add-on). "
                                 f"Or add your own picture named {shot_id}.jpg to the media folder and search again.")
    if req.prompt.strip():
        b["prompt"] = " ".join(req.prompt.split())
    seed = req.seed if req.seed is not None else random.randrange(2**31)
    job_id = uuid.uuid4().hex[:10]
    with jobs_lock:
        jobs[job_id] = {"id": job_id, "kind": "reconstruction", "status": "queued", "step": 0, "log": [],
                        "title": f"{plan.project.title}: {shot_id}"}
    footage_pool.submit(_run_reconstruction, job_id, kind, ref, shot_id, b, seed, plan.project.format)
    return {"id": job_id}


@app.delete("/api/history/{kind}/{ref}/shots/{shot_id}/reconstruction")
def reconstruction_reject(kind: str, ref: str, shot_id: str):
    """Reject the shot's reconstruction: it leaves the video (kept as an alternative to pick back)."""
    from . import shot_footage

    plan, shot, _ = _reconstruction_shot(kind, ref, shot_id)
    if shot.footage and shot.footage.asset_type == "reconstruction":
        shot.candidates.insert(0, shot.footage)
        shot.footage = None
    shot.warnings = shot_footage.warnings_for(shot, plan.project.format, True)
    _plan_put(kind, ref, plan)
    return plan.model_dump()


class GateApproval(BaseModel):
    key: str
    note: str


@app.post("/api/history/{kind}/{ref}/gate/approve")
def history_gate_approve(kind: str, ref: str, req: GateApproval):
    """Approve one review item with your reason (kept in history_review.json); blockers and rights can't be."""
    from .history import gate

    found = _history_project(kind, ref)
    if found is None:
        raise HTTPException(400, "This isn't a history project.")
    try:
        return gate.approve(found[2], *found[:2], req.key, req.note)
    except KeyError:
        raise HTTPException(404, "That item isn't in the check any more. Refresh it.")
    except ValueError as e:
        raise HTTPException(409, str(e))


class RightsConfirm(BaseModel):
    shot_id: str
    note: str


@app.post("/api/history/{kind}/{ref}/rights")
def history_rights(kind: str, ref: str, req: RightsConfirm):
    """Confirm the rights of a picture whose source states no licence, saying what you checked (the note goes into
    the post's credits). Replacing the picture asks again."""
    from .history import gate

    note = " ".join(req.note.split())
    if len(note) < gate.NOTE_MIN:
        raise HTTPException(400, "Say what you checked (e.g. 'Item page: public domain, US government film').")
    plan = _plan_get(kind, ref)
    shot = next((s for s in plan.shots if s.id == req.shot_id), None)
    if shot is None or shot.footage is None:
        raise HTTPException(404, "That shot has no picture.")
    shot.footage.rights, shot.footage.rights_note = "licensed", note[:300]
    _plan_put(kind, ref, plan)
    found = _history_project(kind, ref)
    return gate.evaluate(*found) if found else {"status": "not_history", "items": [], "approved": []}


class HistoryScriptRequest(BaseModel):
    target_seconds: float = 40


@app.post("/api/research/topic/{ref}/script")
def research_script(ref: str, req: HistoryScriptRequest):
    """Write a Hidden History Files script from an approved topic brief (only its sourced claims). The creator
    reviews the text in the form before making the video; nothing is created here."""
    from .history import research, script as hscript

    if not os.getenv("GEMINI_API_KEY"):
        raise HTTPException(400, "Writing the script needs Gemini. Add your key in Settings.")
    if not 10 <= req.target_seconds <= 180:
        raise HTTPException(400, "The target length should be between 10 seconds and 3 minutes.")
    path, brief = _research_brief("topic", ref)
    if brief is None:
        raise HTTPException(404, "Research brief not found.")
    try:
        out = hscript.write(brief, req.target_seconds)
    except ValueError as e:
        raise HTTPException(409, str(e))
    except llm.APIError as e:
        raise _llm_error(e)
    except RuntimeError as e:
        raise HTTPException(502, str(e))
    brief.written_script = out["scenes"]
    research.write(path, brief)  # not an edit of the research: no new revision, approval stands
    return out


def _running_plan_job(key: str) -> str | None:
    job_id = plan_jobs.get(key)
    return job_id if job_id and jobs.get(job_id, {}).get("status") in ("queued", "running") else None


@app.get("/api/plans/{kind}/{ref}")
def plan_read(kind: str, ref: str):
    with jobs_lock:
        job = _running_plan_job(f"{kind}/{ref}")
    return _plan_get(kind, ref).model_dump() | {"footage_job": job, "media_folder": str(_plan_media(kind, ref))}


def _run_plan_footage(job_id: str, kind: str, ref: str, shot_ids: list[str]) -> None:
    from . import shot_footage
    from .longform import settings as lsettings

    job = jobs[job_id]
    log = _job_logger(job, 1)
    with jobs_lock:
        job["status"] = "running"
    save_lock = threading.Lock()

    def save(shot) -> None:
        """Keep each shot's footage as it's found, merged into the plan on disk (the user may be editing it)."""
        with save_lock:
            stored = _plan_get(kind, ref)
            for s in stored.shots:
                if s.id == shot.id:
                    s.footage, s.candidates, s.warnings = shot.footage, shot.candidates, shot.warnings
            _plan_put(kind, ref, stored)

    try:
        log("[1/1] Finding footage for every shot")
        plan = shot_footage.find(_plan_get(kind, ref), _plan_media(kind, ref), lsettings.load(), shot_ids, log=log,
                                 save=save, cancelled=lambda: job.get("cancel", False))
        with save_lock:
            stored = _plan_get(kind, ref)
            stored.warnings = shot_footage.plan_warnings(stored)
            _plan_put(kind, ref, stored)
        if kind == "long" and not job.get("cancel"):  # the storyboard shows the shots, ready to approve
            from . import longform

            for note in longform.apply_plan(_longform_dir(ref), stored):
                log(f"      {note}")
        with jobs_lock:
            if job.get("cancel"):
                job.update(status="error", error="Stopped. The shots done so far keep their footage.")
            else:
                found = sum(1 for s in plan.shots if s.footage)
                job.update(status="done", step=1, summary=f"Footage for {found} of {len(plan.shots)} shots")
    except Exception as e:
        _fail(job, e)


def _start_plan_footage(kind: str, ref: str, shot_ids: list[str], title: str) -> str:
    key = f"{kind}/{ref}"
    with jobs_lock:
        running = _running_plan_job(key)
        if running:  # a second click: the same job
            return running
        job_id = uuid.uuid4().hex[:10]
        jobs[job_id] = {"id": job_id, "kind": "plan_footage", "status": "queued", "step": 0, "log": [], "title": title}
        plan_jobs[key] = job_id
    footage_pool.submit(_run_plan_footage, job_id, kind, ref, shot_ids)
    return job_id


class FootageRequest(BaseModel):
    shots: list[str] = []  # empty: every shot (locked shots with footage are kept)


@app.post("/api/plans/{kind}/{ref}/footage")
def plan_footage(kind: str, ref: str, req: FootageRequest):
    """Search, download and check footage for the plan's shots, in the background (watch /api/jobs/<id>)."""
    plan = _plan_get(kind, ref)
    if kind == "short":
        return {"id": _start_short_rebuild(ref, plan.project.title)}
    unknown = set(req.shots) - {s.id for s in plan.shots}
    if unknown:
        raise HTTPException(400, f"Unknown shots: {', '.join(sorted(unknown))}")
    return {"id": _start_plan_footage(kind, ref, req.shots, plan.project.title)}


def _start_short_rebuild(name: str, title: str) -> str:
    """A Shorts Mode job made again in its folder (voice cached, footage searched with the plan's shots, a new
    pre-flight), one beat clip each: Shorts Mode picks per beat, not per shot."""
    from .shorts import plan as splan

    folder = _short_dir(name)
    _short_idle(name)
    key = f"short/{name}"
    with jobs_lock:
        running = _running_plan_job(key)
        if running:
            return running
        job_id = uuid.uuid4().hex[:10]
        jobs[job_id] = {"id": job_id, "kind": "short", "source": name, "status": "queued", "step": 0, "log": [],
                        "title": title}
        plan_jobs[key] = job_id
    renderer.submit(_run_shorts, job_id, [splan.ShortPlan.load(folder / "episode.json")], folder)
    return job_id


@app.post("/api/plans/{kind}/{ref}/footage/cancel")
def plan_footage_cancel(kind: str, ref: str):
    with jobs_lock:
        job_id = _running_plan_job(f"{kind}/{ref}")
        if job_id:
            jobs[job_id]["cancel"] = True
    return {"id": job_id}


class PickRequest(BaseModel):
    index: int


class AssembleRequest(BaseModel):
    scenes: list[dict] = []  # a Short: the editor's scenes as they are now (unsaved edits included)


@app.post("/api/plans/{kind}/{ref}/assemble")
def plan_assemble(kind: str, ref: str, req: AssembleRequest):
    """Put the plan's footage into the video: a Short gets its scenes back to load into the editor (where they can
    be undone and are saved like any edit); a long video's storyboard is updated in place."""
    from . import plan_render

    plan = _plan_get(kind, ref)
    if kind == "short":
        raise HTTPException(400, "A Shorts Mode video uses its beats' clips already: check them on the Pre-flight page.")
    if kind == "long":
        from . import longform

        if _longform_job(ref):  # takes jobs_lock itself
            raise HTTPException(409, "This video is rendering. Wait for it to finish.")
        return {"notes": longform.apply_plan(_longform_dir(ref), plan)}
    scenes, notes = plan_render.short_scenes(plan, req.scenes)
    return {"scenes": scenes, "mood": plan.edit_plan.music_mood, "notes": notes}


@app.post("/api/plans/{kind}/{ref}/shots/{shot_id}/pick")
def plan_pick(kind: str, ref: str, shot_id: str, req: PickRequest):
    """Use one of a shot's alternatives instead (downloaded now if it wasn't yet)."""
    import requests as _requests

    from . import shot_footage

    if kind == "short":
        raise HTTPException(400, "Swap a beat's clip on the Pre-flight page.")
    try:
        plan = shot_footage.pick(_plan_get(kind, ref), shot_id, req.index)
    except KeyError:
        raise HTTPException(404, "That shot isn't in the plan any more.")
    except IndexError:
        raise HTTPException(400, "That alternative is gone. Reload the plan.")
    except (_requests.RequestException, OSError, RuntimeError) as e:
        raise HTTPException(502, f"Couldn't download that alternative: {e}")
    _plan_put(kind, ref, plan)
    return plan.model_dump()


@app.put("/api/plans/{kind}/{ref}")
def plan_update(kind: str, ref: str, plan: director_plan.DirectorPlan):
    """The user's edits (validated like any plan). Edited shots should come back with locked=true.
    Footage isn't edited here (a search may be saving some right now): it changes through /footage and /pick."""
    stored = {s.id: s for s in _plan_get(kind, ref).shots}  # 404 for a project without one
    for shot in plan.shots:
        if shot.id in stored:
            old = stored[shot.id]
            shot.footage, shot.candidates, shot.warnings = old.footage, old.candidates, old.warnings
    from . import shot_footage

    plan.warnings = shot_footage.plan_warnings(plan)
    plan.story_warnings = director_plan.story_check(plan)
    _plan_put(kind, ref, plan)
    return plan.model_dump()


class DirectRequest(BaseModel):
    scenes: list[str] = []  # empty: the whole video
    note: str = ""


@app.post("/api/plans/{kind}/{ref}/direct")
def plan_direct(kind: str, ref: str, req: DirectRequest):
    """Ask the AI Director again: the whole plan, or only some scenes (locked shots are kept)."""
    from . import ai_director

    if not os.getenv("GEMINI_API_KEY"):
        raise HTTPException(400, "The AI Director needs Gemini. Add your key in Settings.")
    key = f"{kind}/{ref}"
    with jobs_lock:
        if _running_plan_job(key):
            raise HTTPException(409, "Footage is still being found for this plan. Wait for it (or stop it), then re-plan.")
        if key in plan_busy:
            raise HTTPException(409, "The AI Director is already planning this video.")
        plan_busy.add(key)
    try:
        plan = ai_director.direct(_plan_get(kind, ref), req.scenes, req.note[:1000],
                                  research=_approved_research(kind, ref))
        _plan_put(kind, ref, plan)
        new = [] if kind == "short" else [s.id for s in plan.shots if s.footage is None and s.shot_type != "graphic"]
        job = _start_plan_footage(kind, ref, new, plan.project.title) if new else None  # only the re-planned shots
        return plan.model_dump() | {"footage_job": job}
    except ValueError as e:
        raise HTTPException(400, str(e))
    except llm.APIError as e:
        raise _llm_error(e)
    except RuntimeError as e:
        raise HTTPException(502, str(e))
    finally:
        with jobs_lock:
            plan_busy.discard(key)


# ---------- Shorts Mode (crcontent/shorts): a Short per episode, held to the channel's rules ----------
# The pre-flight page (<job>/preflight.html, served under /media) approves the render through /api/shorts/<job>/approve.

@app.get("/api/shorts/rules")
def shorts_rules():
    """The numbers the pre-flight checks hold a Short to (shorts.json's rules and the checks' own), shown before a
    plan is uploaded so a script can be written to pass them."""
    from .shorts import hook, match, preflight, registry, settings

    rules = settings.load()["rules"]
    return {"hook_max": rules["hook_max"], "length_min": rules["length"]["min"], "length_max": rules["length"]["max"],
            "loop_tail": rules["loop_tail"], "match_pass": match.PASS, "generic_max": match.GENERIC_MAX,
            "fresh_days": registry.RECENT_DAYS, "judge_ready": preflight.JUDGE_READY, "bright_min": hook.DARK,
            "sharp_min": hook.SOFT}


@app.post("/api/shorts/read")
def shorts_read(file: UploadFile = File(...)):
    """Upload a Shorts content plan and list its episodes (nothing is made yet)."""
    from .shorts import plan

    if Path(file.filename or "").suffix.lower() != ".xlsx":
        raise HTTPException(400, "Use an Excel workbook (.xlsx). In Excel or Google Sheets: Save as / Download → .xlsx.")
    dest = UPLOAD_DIR / f"plan-{uuid.uuid4().hex[:12]}.xlsx"
    _save_upload(file, dest)
    try:
        episodes = plan.read(dest)
    except Exception as e:
        dest.unlink(missing_ok=True)
        raise HTTPException(422, f"Couldn't read that workbook: {e}")
    if not episodes:
        dest.unlink(missing_ok=True)
        raise HTTPException(422, "No episodes found. The Scripts sheet needs rows under an 'Ep | Time | Visual | "
                                 "On-screen Text | Voiceover' header.")
    return {"file": dest.name, "name": file.filename, "episodes": [
        {"ep": e.ep, "title": e.title, "beats": len(e.script.scenes), "status": e.status,
         "posted": e.status.lower() == "posted", "loops": e.loop_marked} for e in episodes]}


class ShortsRequest(BaseModel):
    file: str
    eps: list[int]


def _run_shorts(job_id: str, episodes: list, folder: Path | None = None) -> None:
    """Steps 1-5 (up to the pre-flight report) for each episode, one after another (again in `folder`: one episode)."""
    from . import shorts

    job = jobs[job_id]
    log = _job_logger(job, shorts.STEPS)
    with jobs_lock:
        job["status"] = "running"
    made, failed, ready = [], [], 0
    for i, ep in enumerate(episodes, 1):
        with jobs_lock:
            job.update(step=0, title=f"Ep {ep.ep} ({i}/{len(episodes)}): {ep.title}")
        try:
            out = shorts.make_job(ep, log=log, job=folder)
            made.append(out.name)
            ready += shorts.report_status(out).get("state") == "ready"
            with jobs_lock:
                job.setdefault("video", out.name)  # the first one opens when they're all ready
        except Exception as err:  # keep going with the next episode
            traceback.print_exc()
            failed.append(ep.ep)
            log(f"  ! Ep {ep.ep} failed: {str(err).strip().splitlines()[-1] if str(err).strip() else repr(err)}")
    # honest: a report being built isn't the Short being ready (preflight.status)
    summary = (f"{len(made)} pre-flight report{'s' if len(made) != 1 else ''} built: {ready} ready, "
               f"{len(made) - ready} need{'s' if len(made) - ready == 1 else ''} work"
               + (f"; failed: Ep {', '.join(map(str, failed))}" if failed else ""))
    log(summary)
    with jobs_lock:
        if made:
            job.update(status="done", step=5, summary=summary, videos=made)
        else:
            job.update(status="error", error=summary)


@app.post("/api/shorts/make")
def shorts_make(req: ShortsRequest):
    """Voiceover, timing, footage and the pre-flight report for each chosen episode; renders wait for approval."""
    from .shorts import plan

    if not EXCEL_FILE.match(req.file) or not (UPLOAD_DIR / req.file).is_file():
        raise HTTPException(404, "That spreadsheet is gone. Choose the file again.")
    episodes = [e for e in plan.read(UPLOAD_DIR / req.file) if e.ep in set(req.eps)]
    if not episodes:
        raise HTTPException(400, "Pick at least one episode.")
    job_id = uuid.uuid4().hex[:10]
    title = episodes[0].title if len(episodes) == 1 else f"{len(episodes)} Shorts"
    with jobs_lock:
        jobs[job_id] = {"id": job_id, "kind": "short", "status": "queued", "step": 0, "log": [], "title": title}
    renderer.submit(_run_shorts, job_id, episodes)
    return {"id": job_id}


def _short_dir(name: str) -> Path:
    from .shorts import is_short

    folder = _video_dir(name)
    if not is_short(folder):
        raise HTTPException(404, "This isn't a Shorts Mode video.")
    return folder


def _run_short_render(job_id: str, folder: Path) -> None:
    from . import shorts

    job = jobs[job_id]
    log = _job_logger(job, shorts.STEPS)
    with jobs_lock:
        job["status"] = "running"
    try:
        shorts.render_job(folder, log=log)
        with jobs_lock:
            job.update(status="done", step=shorts.STEPS, video=folder.name)
        _auto_publish(folder, log)
    except Exception as e:
        _fail(job, e)


class ShortsApply(BaseModel):
    field: str  # "line" (beat 1's voiceover), "text" (its on-screen hook) or "last" (the last beat's voiceover)
    value: str


@app.post("/api/shorts/{name}/apply")
def shorts_apply(name: str, req: ShortsApply):
    """Use a suggested first line or on-screen hook in this Short: re-voiced, re-timed, every check run again."""
    from . import shorts

    folder = _short_dir(name)
    _short_idle(name)
    try:
        report = shorts.apply_change(folder, req.field, req.value, log=lambda line: None)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {"status": report["status"]}


def _short_idle(name: str) -> None:
    with jobs_lock:
        if any(j.get("kind") == "short" and j.get("source") == name and j["status"] in ("queued", "running")
               for j in jobs.values()):
            raise HTTPException(409, "It's rendering: changes have to wait until it's done.")


@app.post("/api/shorts/{name}/beats/{n}/clip")
def shorts_upload_clip(name: str, n: int, file: UploadFile = File(...)):
    """Use your own clip or photo for beat `n`; the checks run again."""
    from . import shorts

    folder = _short_dir(name)
    _short_idle(name)
    tmp = UPLOAD_DIR / f"clip-{uuid.uuid4().hex[:12]}{Path(file.filename or '').suffix.lower()}"
    _save_upload(file, tmp)
    try:
        report = shorts.use_own_clip(folder, n, tmp, file.filename or tmp.name, log=lambda line: None)
    except ValueError as e:
        raise HTTPException(400, str(e))
    finally:
        tmp.unlink(missing_ok=True)
    return {"status": report["status"]}


class ShortsTrim(BaseModel):
    start: float          # seconds into the beat's clip where the beat starts showing it
    end: float | None = None   # where it stops: the stretch plays faster or slower to fit the beat (None: normal speed)
    apply: bool = False   # False: only score that stretch against the planned shot


@app.post("/api/shorts/{name}/beats/{n}/trim")
def shorts_trim_beat(name: str, n: int, req: ShortsTrim):
    """Score the stretch of beat `n`'s clip from `start` against its planned shot; with apply, keep it."""
    from . import shorts

    folder = _short_dir(name)
    _short_idle(name)
    try:
        return shorts.trim_beat(folder, n, req.start, req.apply, log=lambda line: None, end=req.end)
    except ValueError as e:
        raise HTTPException(400, str(e))


class ShortsEdit(BaseModel):
    look: str | None = None        # a styles.LOOKS key, or "" for the channel default
    caption: str | None = None     # a captions.STYLES key
    transition: str | None = None  # shorts/edit.py TRANSITIONS
    graphics: list[str] | None = None  # motion graphics (shorts/graphics.py NAMES)
    beats: dict[str, dict[str, str]] | None = None  # per-beat {look, transition} overrides
    caption_size: float | None = None  # the fine-tune sliders (shorts/edit.py NUMBERS)
    caption_y: float | None = None
    music_volume: float | None = None
    push: bool | None = None           # slow push-in on clips with no camera move


@app.post("/api/shorts/{name}/edit")
def shorts_edit(name: str, req: ShortsEdit):
    """Save the Edit panel's mood, caption look and cut style; the render uses them once it's approved again."""
    from . import shorts

    folder = _short_dir(name)
    _short_idle(name)
    try:
        return shorts.set_edit(folder, req.model_dump(exclude_none=True), log=lambda line: None)
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.post("/api/shorts/{name}/edit/suggest")
def shorts_edit_suggest(name: str):
    """The mood, captions, cuts and motion graphics that fit this Short (nothing is saved)."""
    from . import shorts

    folder = _short_dir(name)
    try:
        return shorts.suggest_edit(folder)
    except (OSError, ValueError, KeyError) as e:
        raise HTTPException(400, str(e))


@app.get("/api/shorts/{name}/edit/preview")
def shorts_edit_preview(name: str, beat: int = 1, look: str = "", caption: str = "classic", graphics: str = "",
                        size: float = 1.0, y: float = 0.64):
    """One frame of beat `beat` as the render would draw it with this mood and caption look (the Edit panel)."""
    import tempfile

    from .shorts import edit

    folder = _short_dir(name)
    fd, tmp = tempfile.mkstemp(suffix=".jpg")
    os.close(fd)  # Windows can't delete a file while the mkstemp handle is still open
    out = Path(tmp)
    try:
        (lo, hi), (ylo, yhi) = edit.NUMBERS["caption_size"], edit.NUMBERS["caption_y"]
        edit.preview(folder, beat, {"look": look, "caption": caption, "graphics": [g for g in graphics.split(",") if g],
                                    "caption_size": min(max(size, lo), hi), "caption_y": min(max(y, ylo), yhi)}, out)
        data = out.read_bytes()
    except (ValueError, RuntimeError, OSError) as e:
        raise HTTPException(400, str(e))
    finally:
        out.unlink(missing_ok=True)
    return Response(data, media_type="image/jpeg", headers={"Cache-Control": "no-store"})


class ShortsVoice(BaseModel):
    voice: str  # an Edge voice of the Short's language, or "" for the channel's
    rate: str = ""  # shorts.RATES, or "" for the channel's speed


@app.post("/api/shorts/{name}/voice")
def shorts_set_voice(name: str, req: ShortsVoice):
    """Change who narrates this Short: every beat is voiced again, re-timed and checked again."""
    from . import shorts

    folder = _short_dir(name)
    _short_idle(name)
    try:
        report = shorts.set_voice(folder, req.voice, req.rate, log=lambda line: None)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {"status": report["status"]}


@app.post("/api/shorts/{name}/beats/{n}/voice")
def shorts_upload_voice(name: str, n: int, file: UploadFile = File(...)):
    """Beat `n` is spoken by your recording (uploaded or recorded in the page); re-timed and checked again."""
    from . import shorts

    folder = _short_dir(name)
    _short_idle(name)
    tmp = UPLOAD_DIR / f"voice-{uuid.uuid4().hex[:12]}{Path(file.filename or '').suffix.lower()}"
    _save_upload(file, tmp)
    try:
        report = shorts.use_own_voice(folder, n, tmp, log=lambda line: None)
    except ValueError as e:
        raise HTTPException(400, str(e))
    finally:
        tmp.unlink(missing_ok=True)
    return {"status": report["status"]}


@app.delete("/api/shorts/{name}/beats/{n}/voice")
def shorts_remove_voice(name: str, n: int):
    """Beat `n` goes back to the narrator's voice."""
    from . import shorts

    folder = _short_dir(name)
    _short_idle(name)
    try:
        report = shorts.remove_own_voice(folder, n, log=lambda line: None)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {"status": report["status"]}


@app.get("/api/shorts/{name}/beats/{n}/source")
def shorts_beat_source(name: str, n: int):
    """Beat `n`'s clip, for the trim panel's player."""
    folder = _short_dir(name)
    try:
        entries = json.loads((folder / "footage.json").read_text(encoding="utf-8"))
        path = Path(entries[n - 1]["chosen"]["file"])
    except (OSError, ValueError, IndexError, KeyError):
        raise HTTPException(404, "There's no clip for that beat.")
    if not path.is_file():
        raise HTTPException(404, "That clip is gone.")
    return FileResponse(path)


@app.delete("/api/shorts/{name}/beats/{n}/clip")
def shorts_remove_clip(name: str, n: int):
    """Beat `n` goes back to the stock pick your clip replaced; the checks run again."""
    from . import shorts

    folder = _short_dir(name)
    _short_idle(name)
    try:
        report = shorts.remove_own_clip(folder, n, log=lambda line: None)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {"status": report["status"]}


@app.post("/api/shorts/{name}/approve")
def shorts_approve(name: str):
    """Approve the pre-flight as it is now and render the Short (steps 6-7: render, cover and metadata)."""
    from .longform import storyboard

    folder = _short_dir(name)
    with jobs_lock:
        running = next((j["id"] for j in jobs.values() if j.get("kind") == "short" and j.get("source") == name
                        and j["status"] in ("queued", "running")), None)
    if running:
        return {"id": running}
    storyboard.approve(folder)
    job_id = uuid.uuid4().hex[:10]
    with jobs_lock:
        jobs[job_id] = {"id": job_id, "kind": "short", "status": "queued", "step": 5, "log": [],
                        "title": _summary(folder)["title"], "source": name}
    renderer.submit(_run_short_render, job_id, folder)
    return {"id": job_id}


def _plan_view(folder: Path, plan: dict | None) -> dict:
    """A song's picture plan with each picture that is already drawn (drawing is free, so it can be checked first)."""
    from . import imagegen

    if not plan:
        return {"plan": None}
    from .pipeline import plan_follows, song_direction

    # does it follow the song's current shot list (or no shot list, if there is none for its idea)?
    song = SongScript.load(folder / "song.json")
    current = song_direction(song, _read_meta(folder).get("direction"), plan.get("idea", ""))
    plan["direction_current"] = plan_follows(plan, current)
    from .pipeline import picture_shape

    size = frame_size(plan.get("aspect") or "9:16")
    for k, slot in enumerate(plan["slots"]):
        shape = picture_shape(slot, size, plan.get("fit", "fit"))  # a home video landscape, a cover character portrait
        slot["draw_aspect"] = "9:16" if shape == frame_size("9:16") else plan.get("aspect") or "9:16"
        path = imagegen.drawn(slot["prompt"], plan["style"], shape, slot.get("seed") or k + 1)
        slot["picture"] = _media_info(path) if path else None
    return {"plan": plan}


# ---------- a song's animated cover (crcontent/coverloop.py, shared with the Lyrics page) ----------

def _song_dir(name: str) -> Path:
    folder = _video_dir(name)
    if not (folder / "song.json").exists():
        raise HTTPException(400, "This isn't a song.")
    return folder


def _loop_suggestion(folder: Path) -> str:
    from . import coverloop

    try:   # only the mood: a song.json from an older version still gets its cover
        mood = json.loads((folder / "song.json").read_text(encoding="utf-8")).get("mood") or ""
    except (OSError, ValueError):
        mood = ""
    return coverloop.suggest(mood, "")


def _cover_loop_view(folder: Path) -> dict:
    from . import coverloop

    return {**coverloop.state(folder, _loop_suggestion(folder)), "other_loops": lyricvideo._other_loops(folder)}


class CoverLoopEdit(BaseModel):
    cover_mode: str | None = None  # "picture" | "animated": what a one-cover music video holds for the whole song
    loop_prompt: str | None = None
    loop_movement: str | None = None


@app.get("/api/videos/{name}/cover-loop")
def get_cover_loop(name: str):
    return _cover_loop_view(_song_dir(name))


@app.put("/api/videos/{name}/cover-loop")
def edit_cover_loop(name: str, req: CoverLoopEdit):
    from . import coverloop

    folder = _song_dir(name)
    try:
        coverloop.edit(folder, req.cover_mode, req.loop_prompt, req.loop_movement)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return _cover_loop_view(folder)


@app.post("/api/videos/{name}/cover-loop")
def draw_cover_loop(name: str, again: bool = False):
    """Gemini draws the animated cover (one request, a minute or two)."""
    from . import coverloop

    folder = _song_dir(name)
    lyricvideo._loop_call(folder, lambda: coverloop.draw(folder, _loop_suggestion(folder), again))
    return _cover_loop_view(folder)


@app.post("/api/videos/{name}/cover-loop/gpu")
def gpu_cover_loop(name: str, req: lyricvideo.GpuLoop):
    """The animated cover drawn and brought to life on this computer's GPU (free, no Gemini)."""
    from . import coverloop

    folder = _song_dir(name)
    effects = req.effects if req.effects is not None else coverloop.meta(folder).get("effects")
    suggested = _loop_suggestion(folder)
    lyricvideo._start_gpu(folder, lambda log, progress: coverloop.animate(folder, suggested, None, effects, req.again,
                                                                         log, req.motion, progress, req.intensity), True)
    return {**_cover_loop_view(folder), "job": coverloop.status(folder)}


@app.get("/api/videos/{name}/cover-loop/status")
def gpu_cover_loop_status(name: str):
    from . import coverloop

    return coverloop.status(_song_dir(name))


@app.post("/api/videos/{name}/cover-loop/upload")
def upload_cover_loop(name: str, video: UploadFile = File(...)):
    from . import coverloop

    folder = _song_dir(name)
    lyricvideo._loop_call(folder, lambda: coverloop.upload(folder, video.filename or "", video.file))
    return _cover_loop_view(folder)


@app.post("/api/videos/{name}/cover-loop/from/{source}")
def copy_cover_loop(name: str, source: str):
    from . import coverloop

    folder = _song_dir(name)
    lyricvideo._loop_call(folder, lambda: coverloop.copy(folder, lyricvideo.loop_source(source)))
    return _cover_loop_view(folder)


@app.delete("/api/videos/{name}/cover-loop")
def remove_cover_loop(name: str):
    from . import coverloop

    folder = _song_dir(name)
    coverloop.remove(folder)
    return _cover_loop_view(folder)


@app.get("/api/videos/{name}/art-plan")
def get_art_plan(name: str):
    """The song's planned music video pictures (None until planned)."""
    from .pipeline import load_art_plan

    folder = _video_dir(name)
    return _plan_view(folder, load_art_plan(folder))


class ArtPlanSongRequest(BaseModel):
    style: str
    pictures: str = "normal"
    idea: str = ""
    bible: str = ""  # keep this visual bible (yours, edited) instead of writing a new one
    direction: dict | None = None  # the shot list for the idea; None = the song's, if it fits the idea


@app.post("/api/videos/{name}/art-plan")
def new_art_plan(name: str, req: ArtPlanSongRequest):
    """Gemini plans the music video's pictures (one call, a few cents); nothing is drawn or rendered yet."""
    from .pipeline import PICTURE_PACES, plan_song_pictures

    folder = _video_dir(name)
    if not (folder / "song.json").exists() or not (folder / "song.mp3").exists():
        raise HTTPException(400, "Compose the song first.")
    if req.style not in ("anime", "cinematic", "flat"):
        raise HTTPException(400, "Pick an art style first.")
    direction = _read_meta(folder).get("direction")
    song = SongScript.load(folder / "song.json")
    if req.direction is not None and len(req.direction.get("sections") or []) == len(song.sections):
        # the shot list on screen may not be saved yet (it saves a moment after each edit): save it now, so the plan
        # and the song's shot list are the same one and the plan doesn't look out of date when the song is reopened
        from .director import clean_section

        d = req.direction
        direction = {"idea": str(d.get("idea") or "").strip()[:IDEA_MAX], "bible": str(d.get("bible") or "").strip()[:2000],
                     "notes": list(d.get("notes") or [])[:6], "sections": [clean_section(r) for r in d["sections"]],
                     **{k: d[k] for k in ("look", "lyric_preset", "lyric_font") if k in d}}
        _save_direction(folder, direction)
    try:
        plan = plan_song_pictures(folder, req.style, req.pictures if req.pictures in PICTURE_PACES else "normal",
                                  req.idea[:IDEA_MAX], req.bible[:2000], log=lambda _: None, direction=direction)
    except llm.APIError as e:
        raise _llm_error(e)
    except RuntimeError as e:
        raise HTTPException(400, str(e))
    return _plan_view(folder, plan)


class ArtPlanSlotEdit(BaseModel):
    prompt: str
    motion: str = ""
    effects: list[str] = []
    seed: int = 0


class ArtPlanEdit(BaseModel):
    bible: str | None = None
    fit: str | None = None  # pipeline.PICTURE_FITS: a cover that fills the screen is drawn in the frame's shape
    slots: list[ArtPlanSlotEdit]


@app.put("/api/videos/{name}/art-plan")
def edit_art_plan(name: str, req: ArtPlanEdit):
    """Save your changes to the planned pictures (prompts, takes, camera moves, effects)."""
    from .fx import EFFECTS, MOTIONS
    from .pipeline import PICTURE_FITS, load_art_plan, save_art_plan

    folder = _video_dir(name)
    plan = load_art_plan(folder)
    if not plan:
        raise HTTPException(404, "Plan the pictures first.")
    if len(req.slots) != len(plan["slots"]):
        raise HTTPException(409, "The plan changed meanwhile; reload it.")
    if req.bible is not None:
        plan["bible"] = req.bible.strip()
    if req.fit in PICTURE_FITS:
        plan["fit"] = req.fit
    for k, (slot, edit) in enumerate(zip(plan["slots"], req.slots)):
        if edit.prompt.strip():
            slot["prompt"] = edit.prompt.strip()
        slot["motion"] = edit.motion if edit.motion in MOTIONS else slot.get("motion", "push_in")
        slot["effects"] = [e for e in edit.effects if e in EFFECTS][:3]
        slot["seed"] = edit.seed or slot.get("seed") or k + 1
        slot.pop("picture", None)
    save_art_plan(folder, plan)
    return _plan_view(folder, plan)


class ShotPreviewRequest(BaseModel):
    media: str  # a drawn picture (project-relative, from /api/art/draw)
    style: str = "anime"
    motion: str = "push_in"
    effects: list[str] = []
    aspect: str = "9:16"
    look: str = ""


@app.post("/api/art/preview-shot")
def preview_shot(req: ShotPreviewRequest):
    """A few seconds of one picture with its camera move and effects, as it will move in the video (free, local)."""
    from . import fx, imagegen

    _art_check(req.style)
    picture = (ROOT / req.media).resolve()
    if not picture.is_file() or (imagegen.GEN_CACHE.resolve() not in picture.parents):
        raise HTTPException(400, "Draw the picture first.")
    motion = req.motion if req.motion in fx.MOTIONS else "push_in"
    effects = [*fx.default_effects(req.style, music=True), *(e for e in req.effects if e in fx.EFFECTS)]
    key = hashlib.sha1(json.dumps([picture.name, motion, effects, req.aspect, req.look]).encode()).hexdigest()[:16]
    out = CACHE_DIR / "preview" / f"{key}.mp4"
    if not out.exists():
        out.parent.mkdir(parents=True, exist_ok=True)
        tmp = out.with_suffix(".part.mp4")
        try:
            fx.render_shot(picture, 4.0, tmp, size=frame_size(req.aspect), motion=motion, effects=effects,
                           beats=[0.0], look=req.look)
        except RuntimeError as e:
            raise HTTPException(422, str(e))
        os.replace(tmp, out)
    imagegen.unload_later()
    return _media_info(out)


class StyleSuggestionRequest(BaseModel):
    idea: str = ""
    pictures: str = ""  # "cover" keeps to looks that leave a flat pastel clean


@app.post("/api/videos/{name}/style-suggestion")
def style_suggestion(name: str, req: StyleSuggestionRequest):
    """The footage look and lyric style that fit the song (its mood, genre and your idea), and a starter prompt for
    its cover picture: instant and free, no Gemini call. {"look", "lyric_preset", "reason", "prompt"}."""
    from .styles import suggest_style

    folder = _video_dir(name)
    if not (folder / "song.json").exists():
        raise HTTPException(400, "This isn't a song.")
    from .pipeline import suggest_background_prompt, suggest_cover_prompt

    song = SongScript.load(folder / "song.json")
    idea = req.idea[:IDEA_MAX]
    lyrics = " ".join(line for sec in song.sections for line in sec.lyrics)
    return {**suggest_style(song.mood, song.genre, idea, cover=req.pictures == "cover"),
            "prompt": suggest_cover_prompt(song, idea, lyrics),
            "video_prompt": suggest_background_prompt(song, idea, lyrics)}


@app.post("/api/videos/{name}/video-ideas")
def video_ideas(name: str):
    """Gemini pitches a few music video concepts for the song, each with a matching look and lyric style."""
    folder = _video_dir(name)
    if not (folder / "song.json").exists():
        raise HTTPException(400, "This isn't a song.")
    try:
        return {"ideas": suggest_video_ideas(SongScript.load(folder / "song.json"), _summary(folder)["lang"])}
    except (llm.APIError, RuntimeError) as e:
        raise _llm_error(e)


# ---------- Your own songs (upload mp3 + lyrics -> lyric timing -> music video) ----------

def _job_logger(job: dict, steps: int):
    """A log function for a job: "[n/steps]" lines move it to step n (and reset its progress); "@progress f text"
    lines (pipeline.progress_reporter) set how far the current step is, 0..1, and what it's doing, without going
    into the log; everything else is appended to the log. Once the job is stopped, any log call raises JobStopped:
    the work stops at its next line of progress (a running FFmpeg encode is killed by render.run_progress)."""
    def log(line: str) -> None:
        with jobs_lock:
            if job.get("cancel"):
                raise JobStopped(STOPPED)
            if line.startswith("@progress "):
                _, fraction, *detail = line.split(" ", 2)
                job["progress"], job["detail"] = float(fraction), (detail[0] if detail else "")
                return
            job["log"].append(line)
            if line.startswith("[") and f"/{steps}]" in line:
                job.update(step=int(line[1]), progress=None, detail="")
    return log


def _fail(job: dict, e: Exception) -> None:
    if isinstance(e, JobStopped) or job.get("cancel"):
        with jobs_lock:
            job.update(status="error", error=STOPPED, cancelled=True)
        return
    traceback.print_exc()
    # a Gemini error as the API answers say it (its own text's last line can be just "Please retry in 19.5s.")
    msg = _llm_error(e).detail if isinstance(e, llm.APIError) else str(e).strip().splitlines()[-1] if str(e).strip() else repr(e)
    with jobs_lock:
        job.update(status="error", error=msg)


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
    meta = _read_meta(folder)
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


@app.post("/api/jobs/{job_id}/cancel")
def job_cancel(job_id: str):
    """Stop a render or footage job: a queued one never starts, a running one stops at its next step of progress."""
    with jobs_lock:
        job = jobs.get(job_id)
        if job is None:
            raise HTTPException(404, "Job not found (the app may have restarted).")
        if job.get("kind") in ("lyric_video", "inspect", "publish"):  # their own runners: no stop between steps
            raise HTTPException(400, "This job can't be stopped here.")
        if job["status"] in ("queued", "running"):
            job["cancel"] = True
        return {"id": job_id, "status": job["status"]}


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
    title = meta.get("title") or folder.name  # a campaign clip names itself in meta.json
    for name in ("script.json", "song.json"):
        if (folder / name).exists():
            try:
                title = json.loads((folder / name).read_text(encoding="utf-8")).get("title", title)
            except (OSError, ValueError):
                pass  # empty or corrupt: keep the folder name
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
        "aspect": meta.get("aspect", "16:9" if meta.get("kind") == "long_video" else "9:16"),
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
    data["published"] = publish.published(folder)
    data["youtube"] = publish.youtube_options(folder) if (folder / "video.mp4").exists() else None
    meta = _read_meta(folder)
    data["song"] = SongScript.load(folder / "song.json").model_dump() if (folder / "song.json").exists() else None
    data["stems"] = {k: meta[k] for k in ("vocals", "instrumental") if meta.get(k)}
    data["versions"] = [_summary(f) for f in song_versions(folder)] if meta.get("kind") == "song" else []
    # Song: the settings its last music video used. Before the first video there are none, so fall back to what was
    # already chosen for it: the shot list (idea, look) and the planned pictures (art style, pace, idea). Otherwise the
    # picture plan looks out of date the moment the song is opened again, and its pictures can't be drawn.
    from .pipeline import load_art_plan

    made = "idea" in meta  # a music video was made from it (and saved these settings)
    direction = meta.get("direction") or {}
    plan = (load_art_plan(folder) if meta.get("kind") == "song" and not made else None) or {}
    data["idea"] = meta["idea"] if made else (direction.get("idea") or plan.get("idea", ""))
    data["look"] = meta.get("look", "" if made else direction.get("look", ""))  # same, for the colour grade
    data["lyric_style"] = meta.get("lyric_style")
    data["art_style"] = meta.get("art_style", plan.get("style", ""))
    data["pictures"] = meta.get("pictures", plan.get("pictures", "normal"))
    data["direction"] = meta.get("direction")  # the shot list made from the idea (songs)
    data["cold_open"] = bool(meta.get("cold_open"))
    data["now_playing"] = bool(meta.get("now_playing"))
    data["picture_fit"] = meta.get("picture_fit", "fit")
    data["duration"] = (round(duration(folder / "video.mp4"), 2) if data["video"]
                        else meta.get("duration", 0))
    data["thumb_text"] = meta.get("thumb_text", data["title"])
    data["thumb_at"] = meta.get("thumb_at", min(1.0, data["duration"] / 2))
    data["thumb_style"] = meta.get("thumb_style", "bold")
    data["thumb_emphasis"] = meta.get("thumb_emphasis", "")
    data["thumb_image"] = meta.get("thumb_image", "")
    saved = folder / "suggest" / "suggestions.json"
    data["thumb_suggestions"] = json.loads(saved.read_text(encoding="utf-8")) if saved.exists() else None
    return data


class ThumbnailRequest(BaseModel):
    text: str = ""
    at: float = 1.0
    style: str = "bold"  # one of pipeline.COVER_STYLES
    emphasis: str = ""  # word(s) to highlight; "" = pick automatically
    image: str = ""  # photo to use instead of a video frame: a project path under uploads/ or cache/
    design: str = ""  # style "designed": the suggestion to start from, e.g. "suggest/designed_1.svg"


def _cover_image(path: str) -> str:
    """A thumbnail background photo the client sent: only your uploads or downloaded stock, never another file."""
    if not path:
        return ""
    file = (ROOT / path).resolve()
    if (file.suffix.lower() not in IMAGE_EXTS or not file.is_file()
            or not any(file.is_relative_to(d.resolve()) for d in (UPLOAD_DIR, CACHE_DIR))):
        raise HTTPException(400, "That picture can't be used for the thumbnail. Upload a jpg, png or webp.")
    return project_path(file)


@app.post("/api/videos/{name}/thumbnail")
def video_thumbnail(name: str, req: ThumbnailRequest):
    folder = _video_dir(name)
    if not (folder / "video.mp4").exists():
        raise HTTPException(404, "This video hasn't been rendered.")
    lang = _summary(folder)["lang"]
    image = _cover_image(req.image)
    design = req.design if re.fullmatch(r"suggest/designed_\d+\.svg", req.design) else ""
    try:
        make_thumbnail(folder, req.text[:120], req.at, lang,
                       req.style if req.style in COVER_STYLES else "bold", req.emphasis[:60], image, design)
    except llm.APIError as e:  # a designed cover needs Gemini
        raise _llm_error(e)
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(500, f"Couldn't make the thumbnail: {str(e).strip().splitlines()[-1]}")
    return _summary(folder)


class ThumbnailIdeaRequest(BaseModel):
    idea: str = ""  # what the cover should show or say, in your words


@app.post("/api/videos/{name}/thumbnail/suggest")
def video_thumbnail_suggest(name: str, req: ThumbnailIdeaRequest | None = None):
    """Cover ideas to pick from: Gemini looks at the best frames and writes headlines, following your idea for the
    cover when you give one (a picture the video doesn't have comes from stock photos)."""
    folder = _video_dir(name)
    if not (folder / "video.mp4").exists():
        raise HTTPException(404, "This video hasn't been rendered.")
    try:
        items, note = suggest_thumbnails(folder, _summary(folder)["lang"], idea=(req.idea if req else "")[:600])
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(500, f"Couldn't suggest thumbnails: {str(e).strip().splitlines()[-1]}")
    return {"items": items, "note": note}


class PostIdeaRequest(BaseModel):
    idea: str = ""  # direction for the title and description, in your words


@app.post("/api/videos/{name}/post/suggest")
def video_post_suggest(name: str, req: PostIdeaRequest | None = None):
    """Title + description + hashtag packages to pick from, each written from a different angle."""
    folder = _video_dir(name)
    try:
        items = suggest_posts(folder, _summary(folder)["lang"], idea=(req.idea if req else "")[:600])
    except llm.APIError as e:
        raise _llm_error(e)
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(500, f"Couldn't suggest post text: {str(e).strip().splitlines()[-1]}")
    return {"items": items}


@app.post("/api/videos/{name}/packaging")
def video_packaging(name: str):
    """Gemini scores the title, thumbnail and opening together and writes stronger ones."""
    folder = _video_dir(name)
    try:
        return packaging.review(folder, _summary(folder)["lang"])
    except (llm.APIError, RuntimeError) as e:
        raise _llm_error(e)


class OutliersRequest(BaseModel):
    query: str
    lang: str = "en"
    length: str = "any"  # "short" | "long" | "any"
    months: int = 12
    min_ratio: float = 5.0


@app.post("/api/outliers")
def outliers(req: OutliersRequest):
    """Videos with far more views than subscribers about a topic, judged for weak packaging, with a remake plan."""
    if not req.query.strip():
        raise HTTPException(400, "Type a topic to search YouTube for.")
    lang = req.lang if req.lang in LANGS else "en"
    length = req.length if req.length in ("short", "long", "any") else "any"
    try:
        found = packaging.find_outliers(req.query.strip()[:100], max(1, min(req.months, 60)),
                                        max(1.0, req.min_ratio), length)
    except packaging.OutlierError as e:
        raise HTTPException(400, str(e))
    except requests.RequestException as e:
        raise HTTPException(502, f"Couldn't reach YouTube: {e}")
    try:
        return {"videos": packaging.judge_outliers(found, lang, "long YouTube video" if length == "long" else "short"),
                "found": len(found)}
    except (llm.APIError, RuntimeError) as e:  # still show the numbers without Gemini's verdicts
        print(f"  ! outlier verdicts: {type(e).__name__}: {e}")
        return {"videos": found[:10], "found": len(found), "note": "Gemini was unavailable, so there are no verdicts."}


class TitleRequest(BaseModel):
    title: str


@app.put("/api/videos/{name}/post/title")
def video_post_title(name: str, req: TitleRequest):
    if not req.title.strip():
        raise HTTPException(400, "The title is empty.")
    return {"post": set_title(_video_dir(name), req.title[:200])}


class JourneyRequest(BaseModel):
    journey: str = ""


@app.get("/api/settings/journey")
def settings_journey():
    return {"journey": packaging.journey()}


@app.put("/api/settings/journey")
def save_settings_journey(req: JourneyRequest):
    return {"journey": packaging.set_journey(req.journey)}


class PostText(BaseModel):
    title: str
    description: str
    hashtags: list[str] = []


@app.put("/api/videos/{name}/post")
def video_post_save(name: str, req: PostText):
    folder = _video_dir(name)
    return {"post": write_post(folder, req.title[:200], req.description[:3000], req.hashtags[:15])}


# ---------- Campaigns (Whop Content Rewards: brief + requirements + reference materials -> clips) ----------

def _campaign(campaign_id: str) -> campaigns.Campaign:
    try:
        return campaigns.load(campaign_id)
    except KeyError:
        raise HTTPException(404, "Campaign not found. It may have been deleted.")


def _campaign_view(c: campaigns.Campaign) -> dict:
    """The campaign plus its clips, each with where it's uploaded or scheduled."""
    pending: dict[str, list] = {}
    for item in schedule.items():
        if item["status"] in ("scheduled", "uploading"):
            pending.setdefault(item["video"], []).append(item)
    clips = []
    for folder in campaigns.clips(c.id):
        meta = _read_meta(folder)
        post = (folder / "post.txt").read_text(encoding="utf-8") if (folder / "post.txt").exists() else ""
        clips.append({**_summary(folder), "post": post, "duration": round(meta.get("end", 0) - meta.get("start", 0), 1),
                      "hook": meta.get("hook", ""), "why": meta.get("why", ""), "reference": meta.get("reference", ""),
                      "published": publish.published(folder), "scheduled": pending.get(folder.name, [])})
    data = c.model_dump(exclude={"source_text"})
    data["clips"] = clips
    return data


@app.get("/api/campaigns")
def campaign_list():
    out = []
    for c in campaigns.list_all():
        made = campaigns.clips(c.id)
        out.append({"id": c.id, "name": c.name, "brand": c.brand, "rate": c.rate, "platforms": c.platforms,
                    "updated": c.updated, "references": len(c.references), "clips": len(made),
                    "uploaded": sum(1 for f in made if publish.published(f))})
    return out


class CampaignReadRequest(BaseModel):
    text: str = ""  # the campaign page, copied from Whop
    url: str = ""


@app.post("/api/campaigns")
def campaign_create(req: CampaignReadRequest):
    """Read a campaign (brief, requirements, reference links) from the pasted Whop page with Gemini."""
    try:
        c = campaigns.read_campaign(req.text[:80_000], req.url.strip()[:500])
    except ValueError as e:
        raise HTTPException(400, str(e))
    except llm.APIError as e:
        raise _llm_error(e)
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(500, f"Couldn't read the campaign: {str(e).strip().splitlines()[-1]}")
    return _campaign_view(c)


@app.get("/api/campaigns/{campaign_id}")
def campaign_get(campaign_id: str):
    return _campaign_view(_campaign(campaign_id))


class CampaignEdit(BaseModel):
    name: str | None = None
    brand: str | None = None
    url: str | None = None
    rate: str | None = None
    budget: str | None = None
    brief: str | None = None
    lang: str | None = None
    platforms: list[str] | None = None
    requirements: campaigns.Requirements | None = None


@app.put("/api/campaigns/{campaign_id}")
def campaign_edit(campaign_id: str, req: CampaignEdit):
    c = _campaign(campaign_id)
    changes = {k: getattr(req, k) for k in req.model_fields_set if getattr(req, k) is not None}
    if "lang" in changes and changes["lang"] not in LANGS:
        raise HTTPException(400, f"Unknown language {changes['lang']}")
    if "requirements" in changes:
        r = changes["requirements"]
        r.min_seconds, r.max_seconds = sorted((max(3, r.min_seconds), max(5, r.max_seconds)))
    return _campaign_view(campaigns.save(c.model_copy(update=changes)))


@app.delete("/api/campaigns/{campaign_id}")
def campaign_delete(campaign_id: str):
    """Deletes the campaign and its downloaded references; its clips stay in Videos."""
    _campaign(campaign_id)
    campaigns.delete(campaign_id)
    return {"deleted": campaign_id}


class ReferenceLink(BaseModel):
    url: str
    title: str = ""


@app.post("/api/campaigns/{campaign_id}/references")
def campaign_add_link(campaign_id: str, req: ReferenceLink):
    c = _campaign(campaign_id)
    url = req.url.strip()
    if not re.match(r"https?://", url):
        raise HTTPException(400, "Paste a full link, starting with https://")
    c.references.append(campaigns.Reference(url=url[:1000], title=req.title.strip()[:200]))
    return _campaign_view(campaigns.save(c))


@app.post("/api/campaigns/{campaign_id}/references/upload")
def campaign_upload(campaign_id: str, file: UploadFile = File(...)):
    c = _campaign(campaign_id)
    ext = Path(file.filename or "").suffix.lower()
    if ext not in campaigns.VIDEO_EXTS | campaigns.AUDIO_EXTS | campaigns.IMAGE_EXTS | {".pdf", ".txt"}:
        raise HTTPException(400, "Add a video, audio, image, PDF or text file.")
    tmp = UPLOAD_DIR / f"campaign-{uuid.uuid4().hex[:8]}{ext}"
    _save_upload(file, tmp)
    campaigns.add_file(c, tmp, Path(file.filename or "").stem[:200])
    return _campaign_view(_campaign(campaign_id))


@app.delete("/api/campaigns/{campaign_id}/references/{ref_id}")
def campaign_remove_ref(campaign_id: str, ref_id: str):
    c = _campaign(campaign_id)
    ref = next((r for r in c.references if r.id == ref_id), None)
    if not ref:
        raise HTTPException(404, "Reference not found.")
    path = campaigns.ref_path(c, ref)
    if path:
        path.unlink(missing_ok=True)
    c.references = [r for r in c.references if r.id != ref_id]
    return _campaign_view(campaigns.save(c))


def _run_prepare(job_id: str, campaign_id: str) -> None:
    job = jobs[job_id]
    with jobs_lock:
        job["status"] = "running"
    try:
        campaigns.prepare_references(campaign_id, log=_job_logger(job, 2))
        with jobs_lock:
            job.update(status="done", step=2)
    except Exception as e:
        _fail(job, e)


@app.post("/api/campaigns/{campaign_id}/prepare")
def campaign_prepare(campaign_id: str):
    """Download the reference links and transcribe the reference videos (one job, on the render queue)."""
    c = _campaign(campaign_id)
    job_id = uuid.uuid4().hex[:10]
    with jobs_lock:
        jobs[job_id] = {"id": job_id, "kind": "campaign_prepare", "status": "queued", "step": 0, "log": [],
                        "title": c.name, "campaign": c.id}
    renderer.submit(_run_prepare, job_id, campaign_id)
    return {"id": job_id}


class ClipRequest(BaseModel):
    count: int = 3
    layout: str = "fill"  # fill: whole picture over a blurred copy; crop: fill the vertical frame
    idea: str = ""  # extra direction for picking moments


def _run_clips(job_id: str, campaign_id: str, req: ClipRequest) -> None:
    job = jobs[job_id]
    log = _job_logger(job, 2)
    with jobs_lock:
        job["status"] = "running"
    try:
        c = campaigns.load(campaign_id)
        log(f"[1/2] Gemini is picking {req.count} moments that fit the brief…")
        plans = campaigns.plan_clips(c, req.count, req.idea)
        if not plans:
            raise RuntimeError("Gemini found no moments that fit the campaign's rules in these videos.")
        made = []
        for i, plan in enumerate(plans, 1):
            log(f"[2/2] Cutting clip {i} of {len(plans)}: {plan.title}")
            try:
                folder = campaigns.render_clip(c, plan, req.layout, log=log)
            except Exception as e:  # keep going with the next clip
                traceback.print_exc()
                log(f"  ! clip {i} failed: {str(e).strip().splitlines()[-1] if str(e).strip() else repr(e)}")
                continue
            made.append(folder.name)
            with jobs_lock:
                job["video"] = folder.name
            _auto_publish(folder, log)
        summary = f"{len(made)} of {len(plans)} clips made"
        log(summary)
        with jobs_lock:
            if made:
                job.update(status="done", step=2, summary=summary)
            else:
                job.update(status="error", error="No clip could be made. See the log.")
    except llm.APIError as e:
        _fail(job, RuntimeError(_llm_error(e).detail))
    except Exception as e:
        _fail(job, e)


@app.post("/api/campaigns/{campaign_id}/clips")
def campaign_clips(campaign_id: str, req: ClipRequest):
    c = _campaign(campaign_id)
    if not any(r.kind == "video" and r.transcribed for r in c.references):
        raise HTTPException(400, "Prepare the reference videos first (download and transcribe them).")
    req.count = max(1, min(req.count, 10))
    req.layout = req.layout if req.layout in ("fill", "crop") else "fill"
    job_id = uuid.uuid4().hex[:10]
    with jobs_lock:
        jobs[job_id] = {"id": job_id, "kind": "campaign_clips", "status": "queued", "step": 0, "log": [],
                        "title": c.name, "campaign": c.id}
    renderer.submit(_run_clips, job_id, campaign_id, req)
    return {"id": job_id}

class CampaignScheduleRequest(BaseModel):
    platforms: list[str]


@app.post("/api/campaigns/{campaign_id}/schedule")
def campaign_schedule(campaign_id: str, req: CampaignScheduleRequest):
    """Schedule every clip not uploaded or scheduled yet on each platform, one per posting time (Settings)."""
    c = _campaign(campaign_id)
    prefs = publish.settings()
    for p in req.platforms:
        if not publish.connected(_platform(p)):
            raise HTTPException(400, f"Connect {PLATFORM_NAMES[p]} first.")
    busy = {(i["video"], i["platform"]) for i in schedule.items() if i["status"] in ("scheduled", "uploading")}
    added = 0
    for folder in reversed(campaigns.clips(c.id)):  # oldest clip goes out first
        done = publish.published(folder)
        for p in dict.fromkeys(req.platforms):
            if p in done or (folder.name, p) in busy or not (folder / "video.mp4").exists():
                continue
            schedule.add(folder.name, p, schedule.next_slot(p, prefs[p]["times"]))
            added += 1
    return {"scheduled": added, "campaign": _campaign_view(c)}


# ---------- Settings (API keys, saved to <ROOT>/.env and applied right away) ----------

SERVICE_KEYS = {
    "GEMINI_API_KEY": "Gemini",
    "PIXABAY_API_KEY": "Pixabay",
    "PEXELS_API_KEY": "Pexels",
    "UNSPLASH_ACCESS_KEY": "Unsplash",
    "ELEVENLABS_API_KEY": "ElevenLabs",
    "JAMENDO_CLIENT_ID": "Jamendo",
    "YOUTUBE_API_KEY": "YouTube Data API",
}


def _masked(value: str) -> str:
    return "" if not value else ("•" * 6 + value[-4:] if len(value) > 8 else "•" * 6)


@app.get("/api/gemini/usage")
def gemini_usage():
    """Today's Gemini requests as this app counted them, and any limit Google has said is reached."""
    return llm.usage()


@app.get("/api/settings/keys")
def settings_keys():
    """Which service keys are set (only the last 4 characters, never the key itself)."""
    return {name: {"set": bool(os.getenv(name, "").strip()), "hint": _masked(os.getenv(name, "").strip())}
            for name in SERVICE_KEYS}


class KeysRequest(BaseModel):
    keys: dict[str, str]  # name -> new value; "" removes it


@app.put("/api/settings/keys")
def save_settings_keys(req: KeysRequest):
    from dotenv import set_key, unset_key

    env = ROOT / ".env"
    env.touch(exist_ok=True)
    for name, value in req.keys.items():
        if name not in SERVICE_KEYS:
            raise HTTPException(400, f"Unknown setting {name}.")
        value = value.strip()
        if any(c.isspace() or c in "\"'" for c in value) or len(value) > 400:  # keys never contain these
            raise HTTPException(400, f"That {SERVICE_KEYS[name]} key doesn't look right.")
        if value:
            set_key(str(env), name, value, quote_mode="never")
            os.environ[name] = value
        else:
            unset_key(str(env), name, quote_mode="never")
            os.environ.pop(name, None)
    return settings_keys()


# ---------- Settings (where the library is kept: crcontent/locations.py) ----------

RESTART_CODE = 3  # same as app.py: under `app.py --reload` the parent process starts the new engine


def _restart_engine() -> None:
    """Start a fresh engine on the same port, then exit: the folders are read once, when the engine starts. The
    desktop app's --parent-pid is passed on, so the new engine still exits with the app."""
    if os.getenv("CRCONTENT_RELOADER"):
        os._exit(RESTART_CODE)
    import subprocess
    import sys

    args = list(sys.argv) if getattr(sys, "frozen", False) else [sys.executable, *sys.argv]
    if "--no-browser" not in args:
        args.append("--no-browser")
    def handle(stream):  # keep writing to the same log (the desktop app's engine.log)
        try:
            return stream.fileno()
        except (AttributeError, OSError, ValueError):
            return subprocess.DEVNULL

    flags = 0x0800_0000 if sys.platform == "win32" else 0  # CREATE_NO_WINDOW
    try:
        subprocess.Popen(args, stdin=subprocess.DEVNULL, stdout=handle(sys.stdout), stderr=handle(sys.stderr),
                         creationflags=flags)
    except OSError:
        traceback.print_exc()
        return  # keep serving; the new folders apply the next time the app starts
    os._exit(0)


def _locations_view() -> dict:
    data, videos, default = locations.current()
    return {"data": str(data), "videos": str(videos), "videos_default": default,
            "default_data": str(locations.DEFAULT_DATA), "locked": bool(os.getenv("CRCONTENT_DATA_DIR"))}


@app.get("/api/settings/cleanup")
def settings_cleanup():
    """What can be cleaned up to save space: groups of files nothing needs now, with their sizes (nothing is deleted)."""
    from . import cleanup

    groups = cleanup.scan(ROOT, OUTPUT_DIR)
    return {"groups": groups, "bytes": sum(g["bytes"] for g in groups)}


class CleanupRequest(BaseModel):
    groups: list[str]


@app.post("/api/settings/cleanup")
def settings_cleanup_run(req: CleanupRequest):
    """Delete the chosen groups (not while a video is being made: its files would be in them)."""
    from . import cleanup

    with jobs_lock:
        if any(j["status"] in ("queued", "running") for j in jobs.values()):
            raise HTTPException(409, "A video is being made. Clean up when it's done.")
    unknown = [g for g in req.groups if g not in cleanup.CATEGORIES]
    if unknown:
        raise HTTPException(400, f"Unknown group: {unknown[0]}")
    return cleanup.run(ROOT, OUTPUT_DIR, req.groups)


@app.get("/api/settings/locations")
def settings_locations():
    return _locations_view()


class LocationsRequest(BaseModel):
    data: str
    videos: str = ""  # "" = the default, <data>/output


@app.put("/api/settings/locations")
def save_settings_locations(req: LocationsRequest):
    """Move the library (and the finished videos) to new folders, then restart the engine on them."""
    if os.getenv("CRCONTENT_DATA_DIR"):
        raise HTTPException(400, "The data folder is set by CRCONTENT_DATA_DIR, so it can't be changed here.")
    with jobs_lock:
        working = any(j.get("status") in ("queued", "running") for j in jobs.values())
    if working or any(i["status"] == "uploading" for i in schedule.items()):
        raise HTTPException(409, "Wait for the current render or upload to finish, then change the folders.")
    data = Path(os.path.expandvars(req.data.strip())).expanduser()
    videos = Path(os.path.expandvars(req.videos.strip())).expanduser() if req.videos.strip() else None
    try:
        left = locations.relocate(data, videos, CODE_DIR)
    except ValueError as e:
        raise HTTPException(400, str(e))
    except OSError as e:
        traceback.print_exc()
        raise HTTPException(500, f"Couldn't move everything ({e.strerror or e}). Close any file open from the "
                                 "library, then try again: what was already moved stays in the new folder.")
    threading.Timer(0.5, _restart_engine).start()  # after this response is sent
    return {**_locations_view(), "left_behind": len(left), "restarting": True}


class OpenFolderRequest(BaseModel):
    which: str  # "data" | "videos"


@app.post("/api/settings/locations/open")
def open_location(req: OpenFolderRequest):
    data, videos, _ = locations.current()
    folder = {"data": data, "videos": videos}.get(req.which)
    if not folder:
        raise HTTPException(400, "Unknown folder.")
    folder.mkdir(parents=True, exist_ok=True)
    if hasattr(os, "startfile"):
        os.startfile(folder)
    else:
        import subprocess
        import sys

        opener = "open" if sys.platform == "darwin" else "xdg-open"  # Finder on macOS
        try:
            subprocess.Popen([opener, str(folder)], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL)
        except OSError:
            raise HTTPException(400, f"Open {folder} in your file manager.")
    return {"opened": str(folder)}


# ---------- Publishing (YouTube / TikTok uploads) ----------

PLATFORM_NAMES = {"youtube": "YouTube", "tiktok": "TikTok", "facebook": "Facebook", "instagram": "Instagram"}


def _platform(platform: str) -> str:
    if platform not in publish.PLATFORMS:
        raise HTTPException(404, "Unknown platform.")
    return platform


def _run_publish(job_id: str, folder: Path, platform: str, **options) -> None:
    job = jobs[job_id]
    with jobs_lock:
        job["status"] = "running"
    try:
        info = publish.upload(folder, platform, log=_job_logger(job, 1), **options)
        with jobs_lock:
            job.update(status="done", step=1, video=folder.name, url=info.get("url", ""), publish_at=info.get("publish_at", ""),
                       comment=info.get("comment") or None, thumbnail=info.get("thumbnail") or None,
                       channel_name=info.get("channel_name") or info.get("page_name") or info.get("account_name") or "")
    except Exception as e:
        _fail(job, e)


def _queue_publish(folder: Path, platform: str, **options) -> str:
    job_id = uuid.uuid4().hex[:10]
    where = PLATFORM_NAMES[platform]
    if platform == "youtube" and len(publish.status()["youtube"]["channels"]) > 1:
        where = publish.channel_name(options.get("channel")) or where  # several channels: name the one it goes to
    with jobs_lock:
        jobs[job_id] = {"id": job_id, "kind": "publish", "platform": platform, "status": "queued", "step": 0,
                        "log": [], "title": f"{where}: {_summary(folder)['title']}", "video": folder.name}
    uploader.submit(_run_publish, job_id, folder, platform, **options)
    return job_id


def _auto_publish(folder: Path, log) -> None:
    """After a render: upload to every connected platform with auto-upload on, right away or at its next posting
    time (never fails the render)."""
    try:
        if why := _history_publish_block(folder):
            log(f"Auto-upload skipped: {why}")
            return
        prefs = publish.settings()
        for p in publish.PLATFORMS:
            if not (prefs[p]["auto"] and publish.connected(p)):
                continue
            if prefs[p]["when"] == "slots":
                at = schedule.next_slot(p, prefs[p]["times"])
                schedule.add(folder.name, p, at, source="auto")
                log(f"Auto-upload to {PLATFORM_NAMES[p]} scheduled for {at:%a %d %b, %H:%M}.")
            else:
                _queue_publish(folder, p)
                log(f"Auto-upload to {PLATFORM_NAMES[p]} queued.")
    except Exception:
        traceback.print_exc()


def _run_scheduled(item: dict) -> None:
    folder = OUTPUT_DIR / item["video"]
    if item.get("action") == "comment":
        return _run_scheduled_comment(item, folder)
    try:
        if not (folder / "video.mp4").exists():
            raise publish.PublishError("The video was deleted.")
        if why := _history_publish_block(folder):
            raise publish.PublishError(why)
        at = datetime.fromisoformat(item["at"])
        # Facebook publishes it at its time itself (schedule.EARLY): uploaded ahead with that time
        native = item["platform"] == "facebook" and publish.fb_can_schedule(at)
        info = publish.upload(folder, item["platform"], log=lambda line: None, channel=item.get("channel") or None,
                              privacy=item.get("privacy") or None, publish_at=at if native else None)
        schedule.mark(item["id"], status="done", url=info.get("url", ""), done=datetime.now().isoformat(timespec="seconds"),
                      **({"publish_at": info["publish_at"]} if info.get("publish_at") else {}))
    except Exception as e:
        traceback.print_exc()
        schedule.mark(item["id"], status="error", error=str(e).strip().splitlines()[-1] if str(e).strip() else repr(e))


def _run_scheduled_comment(item: dict, folder: Path) -> None:
    """A scheduled video went public: post its comment, trying again a few times while YouTube catches up."""
    try:
        if not folder.is_dir():
            raise publish.PublishError("The video was deleted.")
        publish.post_comment(folder, log=lambda line: None, channel=item.get("channel") or None)
        schedule.mark(item["id"], status="done", done=datetime.now().isoformat(timespec="seconds"))
    except Exception as e:
        error = str(e).strip().splitlines()[-1] if str(e).strip() else repr(e)
        tries = item.get("tries", 0) + 1
        if tries < publish.COMMENT_RETRIES and folder.is_dir():
            later = (datetime.now() + timedelta(minutes=10)).isoformat(timespec="minutes")
            schedule.mark(item["id"], status="scheduled", at=later, tries=tries, error=error)
        else:
            schedule.mark(item["id"], status="error", error=error)
            if folder.is_dir():
                publish._comment_state(folder, status="error", error=error)


schedule.start(lambda item: uploader.submit(_run_scheduled, item))


def _schedule_view(item: dict) -> dict:
    folder = OUTPUT_DIR / item["video"]
    view = {**item, "title": _summary(folder)["title"] if folder.is_dir() else item["video"]}
    if item["platform"] == "youtube":
        view["channel_name"] = publish.channel_name(item.get("channel") or None)
    return view


@app.get("/api/schedule")
def schedule_list(video: str = ""):
    return [_schedule_view(i) for i in schedule.items(video)]


class ScheduleRequest(BaseModel):
    platforms: list[str]
    at: str  # local time, "2026-10-13T09:00"
    channel: str = ""  # YouTube channel id; "" = the default channel when it goes out
    tiktok_privacy: str = ""  # TikTok: the visibility it posts with at that time; "" = Settings when it goes out


def _check_channel(channel: str) -> str:
    if channel and not publish.connected("youtube", channel):
        raise HTTPException(400, "That YouTube channel isn't connected any more. Connect it again in Settings.")
    return channel


@app.post("/api/videos/{name}/schedule")
def schedule_video(name: str, req: ScheduleRequest):
    folder = _video_dir(name)
    if why := _history_publish_block(folder):
        raise HTTPException(409, why)
    if not (folder / "video.mp4").exists():
        raise HTTPException(400, "Render the video first.")
    try:
        at = schedule.parse_time(req.at)
    except ValueError:
        raise HTTPException(400, "Pick a date and time.")
    if at < datetime.now().replace(second=0, microsecond=0):
        raise HTTPException(400, "That time has passed. Pick a later one.")
    for p in req.platforms:
        if not publish.connected(_platform(p)):
            raise HTTPException(400, f"Connect {PLATFORM_NAMES[p]} first.")
    channel = _check_channel(req.channel)
    if req.tiktok_privacy and req.tiktok_privacy not in publish.TIKTOK_PRIVACY:
        raise HTTPException(400, "Unknown TikTok visibility.")
    return [_schedule_view(schedule.add(name, p, at, channel=channel if p == "youtube" else "",
                                        privacy=req.tiktok_privacy if p == "tiktok" else ""))
            for p in dict.fromkeys(req.platforms)]


@app.delete("/api/schedule/{item_id}")
def schedule_cancel(item_id: str):
    if not schedule.cancel(item_id):
        raise HTTPException(404, "That upload already started or was cancelled.")
    return {"cancelled": item_id}


@app.get("/api/publish/accounts")
def publish_accounts():
    return publish.status()


@app.post("/api/publish/{platform}/connect")
def publish_connect(platform: str):
    try:
        return {"url": publish.start_connect(_platform(platform))}
    except publish.PublishError as e:
        raise HTTPException(400, str(e))


@app.delete("/api/publish/{platform}")
def publish_disconnect(platform: str, channel: str = ""):
    """Disconnect the account; for YouTube just the channel `channel` when it's given."""
    publish.disconnect(_platform(platform), channel)
    return publish.status()


class PublishApp(BaseModel):
    client_id: str = ""
    client_secret: str = ""  # "" keeps the saved secret while the client ID is set


@app.put("/api/publish/{platform}/app")
def publish_app(platform: str, req: PublishApp):
    """Save (or with an empty client ID, remove) the developer app keys used to connect this platform."""
    try:
        publish.set_app(_platform(platform), req.client_id[:300], req.client_secret[:300])
    except publish.PublishError as e:
        raise HTTPException(400, str(e))
    return publish.status()


class PublishSettings(BaseModel):
    auto: bool | None = None
    privacy: str | None = None
    mode: str | None = None
    when: str | None = None  # "now" | "slots"
    times: list[str] | None = None  # daily posting times, "HH:MM"
    comment: bool | None = None  # youtube: post the video's pinned comment after upload
    category: str | None = None  # youtube: default category id, or "auto"
    channel: str | None = None  # youtube: the default channel's id
    page: str | None = None  # facebook: the default Page's id
    account_id: str | None = None  # instagram: the default account's id
    share_to_feed: bool | None = None  # instagram: Reels also show in the profile grid


@app.put("/api/publish/{platform}/settings")
def publish_settings(platform: str, req: PublishSettings):
    publish.update_settings(_platform(platform), req.model_dump(exclude_none=True))
    return publish.status()


class YouTubeOptions(BaseModel):
    tags: list[str] | None = None
    reset_tags: bool = False  # back to the video's hashtags
    thumbnail: str | None = None  # auto | cover | youtube
    comment: str | None = None  # your comment to post under the video ("" = none)
    reset_comment: bool = False  # back to the automatic fact-check comment


@app.put("/api/videos/{name}/youtube")
def video_youtube_options(name: str, req: YouTubeOptions):
    """Save a video's YouTube tags and thumbnail choice; every later upload of it (auto and scheduled too) uses them."""
    folder = _video_dir(name)
    if req.thumbnail is not None and req.thumbnail not in publish.THUMBNAIL_CHOICES:
        raise HTTPException(400, "Unknown thumbnail choice.")
    return publish.set_youtube_options(folder, [t[:100] for t in req.tags[:100]] if req.tags is not None else None,
                                       req.thumbnail, req.reset_tags, req.comment, req.reset_comment)


@app.post("/api/videos/{name}/youtube/comment")
def video_youtube_comment(name: str):
    """Post the video's comment under its YouTube upload now (it was uploaded without one, or posting failed)."""
    folder = _video_dir(name)
    try:
        return publish.post_comment(folder, log=lambda _: None)
    except publish.PublishError as e:
        publish._comment_state(folder, status="error", error=str(e))
        raise HTTPException(400, str(e))


@app.post("/api/videos/{name}/youtube/thumbnail")
def video_youtube_thumbnail(name: str):
    """Set the cover as the YouTube thumbnail of a video already uploaded (after verifying the channel, say)."""
    folder = _video_dir(name)
    try:
        return publish.set_youtube_thumbnail(folder, log=lambda _: None)
    except publish.PublishError as e:
        raise HTTPException(400, str(e))


class PublishRequest(BaseModel):
    platforms: list[str]
    privacy: str | None = None  # YouTube only: public | unlisted | private for this upload
    publish_at: str | None = None  # YouTube only: local time it goes public ("2026-10-13T09:00"); uploads now as private
    facebook_publish_at: str | None = None  # Facebook: uploads now, Facebook publishes it at this local time
    category: str | None = None  # YouTube only: a category id for this upload (see publish.YT_CATEGORIES)
    channel: str = ""  # YouTube only: the channel id to upload to; "" = the default channel
    tiktok_privacy: str | None = None  # TikTok: a privacy level or "DRAFT" for this upload; None = Settings
    tiktok_post: "TikTokPost | None" = None  # TikTok direct post: interactions and content disclosure picked on the card


class TikTokPost(BaseModel):
    """What TikTok's Direct Post guidelines ask the creator to choose for each post (all off unless they turn it on)."""
    allow_comment: bool = False
    allow_duet: bool = False
    allow_stitch: bool = False
    brand_organic: bool = False  # "Your brand": promoting yourself or your own business
    brand_content: bool = False  # "Branded content": a paid partnership with a third party


PublishRequest.model_rebuild()


@app.get("/api/tiktok/creator")
def tiktok_creator():
    """The connected TikTok account and the visibilities it may post with."""
    if not publish.connected("tiktok"):
        raise HTTPException(400, "Connect TikTok first.")
    try:
        return publish.tiktok_creator()
    except publish.PublishError as e:
        raise HTTPException(400, str(e))


@app.post("/api/videos/{name}/publish")
def publish_video(name: str, req: PublishRequest):
    """Upload the rendered video with its post text; one job per platform."""
    folder = _video_dir(name)
    if not (folder / "video.mp4").exists():
        raise HTTPException(400, "Render the video first.")
    if why := _history_publish_block(folder):
        raise HTTPException(409, why)
    for p in req.platforms:
        if not publish.connected(_platform(p)):
            raise HTTPException(400, f"Connect {PLATFORM_NAMES[p]} first.")
    youtube = {}
    if req.privacy:
        if req.privacy not in ("public", "unlisted", "private"):
            raise HTTPException(400, "Unknown visibility.")
        youtube["privacy"] = req.privacy
    if req.publish_at:
        try:
            at = schedule.parse_time(req.publish_at)
        except ValueError:
            raise HTTPException(400, "Pick a date and time.")
        if at <= datetime.now():
            raise HTTPException(400, "That time has passed. Pick a later one.")
        youtube["publish_at"] = at
    if req.category:
        if req.category not in publish.YT_CATEGORIES:
            raise HTTPException(400, "Unknown category.")
        youtube["category"] = req.category
    if _check_channel(req.channel):
        youtube["channel"] = req.channel
    tiktok = {}
    if req.tiktok_privacy:
        if req.tiktok_privacy not in (*publish.TIKTOK_PRIVACY, "DRAFT"):
            raise HTTPException(400, "Unknown TikTok visibility.")
        tiktok["privacy"] = req.tiktok_privacy
    if req.tiktok_post and "tiktok" in req.platforms:
        tiktok["tiktok_post"] = req.tiktok_post.model_dump()
    facebook = {}
    if req.facebook_publish_at and "facebook" in req.platforms:
        try:
            at = schedule.parse_time(req.facebook_publish_at)
        except ValueError:
            raise HTTPException(400, "Pick a date and time for Facebook.")
        if not publish.fb_can_schedule(at):
            raise HTTPException(400, "Facebook schedules posts from 10 minutes to 28 days ahead. Pick a time in that range.")
        facebook["publish_at"] = at
    options = {"youtube": youtube, "tiktok": tiktok, "facebook": facebook}
    return {"jobs": {p: _queue_publish(folder, p, **options.get(p, {})) for p in dict.fromkeys(req.platforms)}}


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
    meta = _read_meta(folder)
    file = folder / meta[kind] if kind in ("vocals", "instrumental") and meta.get(kind) else None
    if not file or not file.is_file() or file.resolve().parent != folder:
        raise HTTPException(404, "This stem doesn't exist.")
    return FileResponse(file, media_type="audio/mpeg", filename=f"{name}-{kind}{file.suffix}")


@app.delete("/api/videos/{name}")
def delete_video(name: str):
    shutil.rmtree(_video_dir(name))
    schedule.forget_video(name)
    return {"deleted": name}


lyricvideo.SONGS_DIR.mkdir(exist_ok=True)
app.mount("/songs", StaticFiles(directory=lyricvideo.SONGS_DIR), name="songs")  # the lyric video tab's files
app.mount("/media", StaticFiles(directory=OUTPUT_DIR), name="media")
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")
app.mount("/cache", StaticFiles(directory=CACHE_DIR), name="cache")
app.mount("/assets", StaticFiles(directory=ASSETS_DIR), name="assets")  # music and local footage for the live preview
app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")


@app.get("/")
def index():
    return FileResponse(WEB_DIR / "index.html")
