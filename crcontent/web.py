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

import anthropic
import requests
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import addons, art, campaigns, drafts, locations, music, packaging, publish, schedule, sheet, voiceover
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
renderer = ThreadPoolExecutor(max_workers=1)  # FFmpeg is heavy: render one video at a time
uploader = ThreadPoolExecutor(max_workers=1)  # uploads to YouTube/TikTok, separate so renders don't wait on them
jobs: dict[str, dict] = {}
jobs_lock = threading.Lock()


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


@app.get("/api/options")
def options():
    music_dir = ASSETS_DIR / "music"
    return {
        "langs": {code: {"name": p.name, "voices": _voices(code)} for code, p in LANGS.items()},
        "music": sorted(p.name for p in music_dir.glob("*.mp3")) if music_dir.exists() else [],
        # each track's licence for monetized videos: ok / nc (non-commercial) / nd (no derivatives) / unknown
        "music_use": {p.name: music.track_use(p) for p in music_dir.glob("*.mp3")} if music_dir.exists() else {},
        "keys": {
            "anthropic": bool(os.getenv("ANTHROPIC_API_KEY", "").startswith("sk-ant-")),
            "stock": stock_source(),
            "elevenlabs": bool(elevenlabs_key()),
            "jamendo": bool(music.jamendo_key()),
        },
        "styles": style_catalog(),  # lyric style presets, footage looks, installed fonts per language
        "captions": caption_catalog(),  # caption presets of narrated videos
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


class DesignRequest(BaseModel):
    prompt: str | None = ""  # what to draw: the search words or your own description
    narration: str | None = ""  # the scene's voiceover, for context (null for a scene with none yet)
    aspect: str | None = "9:16"
    animate: bool = False  # a seamless looping clip instead of a still


@app.post("/api/footage/design")
def design_footage(req: DesignRequest):
    """Claude draws a background for the scene (artwork, no text); it's used like a photo, with a slow zoom. Animated,
    it comes back as a looping video clip instead."""
    subject = "\n".join(t.strip() for t in (req.prompt or "", req.narration or "") if t.strip())
    if not subject:
        raise HTTPException(400, "Describe the background, or write the scene's narration first.")
    try:
        make = art.motion_background if req.animate else art.background
        return _media_info(make(subject, frame_size(req.aspect)))
    except (anthropic.APIError, RuntimeError) as e:
        raise _claude_error(e)


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
    """How well a picture you drew shows the video's real subject (Claude's check, kept with the picture, so each
    one is only ever checked once). score is null when the picture isn't meant to show the subject."""
    from .pipeline import _verdict

    path = ROOT / req.media
    name = req.subject.split(":")[0].strip().lower()
    if not path.is_file() or not name or name.split()[-1] not in req.prompt.lower():
        return {"score": None, "problem": ""}
    try:
        score, problem = _verdict(path, req.subject.strip(), req.prompt)
    except anthropic.APIError as e:
        raise _claude_error(e)
    return {"score": score, "problem": problem}


class RealSubjectRequest(BaseModel):
    subject: str  # "name: visible features" (script.art_subject)
    exclude: list[str] = []  # media already used in the video (project-relative), to get a different one


@app.post("/api/art/real")
def art_real(req: RealSubjectRequest):
    """Real footage or a real photo of the subject (a stock clip, else Wikimedia Commons), checked by Claude, for a
    scene whose AI picture can't get the subject right."""
    from .pipeline import real_subject_media

    if not req.subject.strip():
        raise HTTPException(400, "Name the real subject first (under the look of the video).")
    used = {str(ROOT / m) for m in req.exclude}
    try:
        path = real_subject_media(req.subject.strip(), used, log=print)
    except anthropic.APIError as e:
        raise _claude_error(e)
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
    """Claude plans a picture prompt, camera move and effects for each scene (keeping your own prompts unless
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
    except (anthropic.APIError, RuntimeError) as e:
        raise _claude_error(e)
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
    """One draft per chosen episode, footage searches planned by Claude, to check and render one by one."""
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
    """Claude turns your concept into a shot list for the song: a scene and cutting pace per section, the recurring
    characters, a matching colour grade and lyric style, and notes on what can't be done literally. Saved with the
    song (one Claude call); edit it in the app before planning pictures or rendering."""
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
    except (anthropic.APIError, RuntimeError) as e:
        raise _claude_error(e)
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


LONG_SCRIPTS = ROOT / "scripts"  # uploaded script .md files; the file name picks its media/<name>/ folder


def _run_storyboard(job_id: str, script_md: Path) -> None:
    from . import longform

    job = jobs[job_id]
    log = _job_logger(job, longform.STEPS)
    with jobs_lock:
        job["status"] = "running"
    try:
        folder = longform.make_storyboard(script_md, log=log)
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


def _run_long_video(job_id: str, folder: Path) -> None:
    from . import longform

    job = jobs[job_id]
    log = _job_logger(job, longform.STEPS)
    with jobs_lock:
        job["status"] = "running"
    try:
        longform.render_video(folder, log=log)
        with jobs_lock:
            job.update(status="done", step=longform.STEPS)
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
    storyboard.approve(folder)
    job_id = uuid.uuid4().hex[:10]
    with jobs_lock:
        jobs[job_id] = {"id": job_id, "kind": "long_video", "status": "queued", "step": 5, "log": [],
                        "title": _summary(folder)["title"], "source": name}
    renderer.submit(_run_long_video, job_id, folder)
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
    """Claude plans the music video's pictures (one call, a few cents); nothing is drawn or rendered yet."""
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
    except anthropic.APIError as e:
        raise _claude_error(e)
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
    its cover picture: instant and free, no Claude call. {"look", "lyric_preset", "reason", "prompt"}."""
    from .styles import suggest_style

    folder = _video_dir(name)
    if not (folder / "song.json").exists():
        raise HTTPException(400, "This isn't a song.")
    from .pipeline import suggest_cover_prompt

    song = SongScript.load(folder / "song.json")
    idea = req.idea[:IDEA_MAX]
    lyrics = " ".join(line for sec in song.sections for line in sec.lyrics)
    return {**suggest_style(song.mood, song.genre, idea, cover=req.pictures == "cover"),
            "prompt": suggest_cover_prompt(song, idea, lyrics)}


@app.post("/api/videos/{name}/video-ideas")
def video_ideas(name: str):
    """Claude pitches a few music video concepts for the song, each with a matching look and lyric style."""
    folder = _video_dir(name)
    if not (folder / "song.json").exists():
        raise HTTPException(400, "This isn't a song.")
    try:
        return {"ideas": suggest_video_ideas(SongScript.load(folder / "song.json"), _summary(folder)["lang"])}
    except (anthropic.APIError, RuntimeError) as e:
        raise _claude_error(e)


# ---------- Your own songs (upload mp3 + lyrics -> lyric timing -> music video) ----------

def _job_logger(job: dict, steps: int):
    """A log function for a job: "[n/steps]" lines move it to step n (and reset its progress); "@progress f text"
    lines (pipeline.progress_reporter) set how far the current step is, 0..1, and what it's doing, without going
    into the log; everything else is appended to the log."""
    def log(line: str) -> None:
        with jobs_lock:
            if line.startswith("@progress "):
                _, fraction, *detail = line.split(" ", 2)
                job["progress"], job["detail"] = float(fraction), (detail[0] if detail else "")
                return
            job["log"].append(line)
            if line.startswith("[") and f"/{steps}]" in line:
                job.update(step=int(line[1]), progress=None, detail="")
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
    except anthropic.APIError as e:  # a designed cover needs Claude
        raise _claude_error(e)
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(500, f"Couldn't make the thumbnail: {str(e).strip().splitlines()[-1]}")
    return _summary(folder)


class ThumbnailIdeaRequest(BaseModel):
    idea: str = ""  # what the cover should show or say, in your words


@app.post("/api/videos/{name}/thumbnail/suggest")
def video_thumbnail_suggest(name: str, req: ThumbnailIdeaRequest | None = None):
    """Cover ideas to pick from: Claude looks at the best frames and writes headlines, following your idea for the
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
    except anthropic.APIError as e:
        raise _claude_error(e)
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(500, f"Couldn't suggest post text: {str(e).strip().splitlines()[-1]}")
    return {"items": items}


@app.post("/api/videos/{name}/packaging")
def video_packaging(name: str):
    """Claude scores the title, thumbnail and opening together and writes stronger ones."""
    folder = _video_dir(name)
    try:
        return packaging.review(folder, _summary(folder)["lang"])
    except (anthropic.APIError, RuntimeError) as e:
        raise _claude_error(e)


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
    except (anthropic.APIError, RuntimeError) as e:  # still show the numbers without Claude's verdicts
        print(f"  ! outlier verdicts: {type(e).__name__}: {e}")
        return {"videos": found[:10], "found": len(found), "note": "Claude was unavailable, so there are no verdicts."}


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
    """Read a campaign (brief, requirements, reference links) from the pasted Whop page with Claude."""
    try:
        c = campaigns.read_campaign(req.text[:80_000], req.url.strip()[:500])
    except ValueError as e:
        raise HTTPException(400, str(e))
    except anthropic.APIError as e:
        raise _claude_error(e)
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
        log(f"[1/2] Claude is picking {req.count} moments that fit the brief…")
        plans = campaigns.plan_clips(c, req.count, req.idea)
        if not plans:
            raise RuntimeError("Claude found no moments that fit the campaign's rules in these videos.")
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
    except anthropic.APIError as e:
        _fail(job, RuntimeError(_claude_error(e).detail))
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
    "ANTHROPIC_API_KEY": "Claude",
    "ANTHROPIC_WORKSPACE_ID": "Claude workspace",
    "PIXABAY_API_KEY": "Pixabay",
    "PEXELS_API_KEY": "Pexels",
    "ELEVENLABS_API_KEY": "ElevenLabs",
    "JAMENDO_CLIENT_ID": "Jamendo",
    "YOUTUBE_API_KEY": "YouTube Data API",
}


def _masked(value: str) -> str:
    return "" if not value else ("•" * 6 + value[-4:] if len(value) > 8 else "•" * 6)


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


app.mount("/media", StaticFiles(directory=OUTPUT_DIR), name="media")
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")
app.mount("/cache", StaticFiles(directory=CACHE_DIR), name="cache")
app.mount("/assets", StaticFiles(directory=ASSETS_DIR), name="assets")  # music and local footage for the live preview
app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")


@app.get("/")
def index():
    return FileResponse(WEB_DIR / "index.html")
