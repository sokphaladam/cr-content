"""A song's animated cover, shared by both video engines (the Library's music video and the Lyrics page's lyric video):
a seamless loop in the song folder (loop.mp4) that plays instead of the still cover picture, and loop.json with which
cover is in use and what the loop shows.

loop.json = {"mode": "picture" | "animated", "prompt": "..."}; no file = animated whenever a loop exists.
"""
import json
import math
import os
import shutil
import subprocess
import threading
import time
from pathlib import Path

from PIL import Image

LOOP = "loop.mp4"
META = "loop.json"
SECONDS = 12.0   # long enough that a song's ~15 repeats go unnoticed, and lofi motion can be slow
MODES = ("picture", "animated")
EXTS = {".mp4", ".webm", ".mov"}
SIZE = (1920, 1080)

SCENE = ("A cozy lo-fi illustration of a small room at night, seen from the side: an original young character "
         "with headphones and a loose sweater studying at a wooden desk by a big window, a desk lamp with a "
         "warm glow, a steaming mug, stacked books, potted plants, a sleeping cat on the windowsill, a city "
         "skyline far outside. Soft flat shading, a limited warm palette (amber lamp light against deep blue "
         "night). Gentle looping motion: rain streaks sliding down the window, steam curling up from the "
         "mug, the cat's tail slowly swaying, the character's head nodding slightly to the music, the lamp "
         "glow breathing, faint dust motes drifting in the light.")


def suggest(mood: str = "", theme: str = "") -> str:
    """The suggested animated cover: the lofi room, in the song's mood."""
    words = ", ".join(x for x in (mood, theme) if x)
    return SCENE + (f" The song's mood: {words}." if words else "")


def meta(folder: Path) -> dict:
    try:
        return json.loads((Path(folder) / META).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def save_meta(folder: Path, **changes) -> None:
    data = {**meta(folder), **changes}
    (Path(folder) / META).write_text(json.dumps(data), encoding="utf-8")


def mode(folder: Path) -> str:
    """The cover you picked (animated may still have no loop: the page then offers to draw one; renders use active())."""
    picked = meta(folder).get("mode")
    if picked in MODES:
        return picked
    return "animated" if (Path(folder) / LOOP).exists() else "picture"


def active(folder: Path) -> Path | None:
    """The loop, when the song uses it ("picture" keeps the still cover even when a loop was made)."""
    file = Path(folder) / LOOP
    return file if file.exists() and meta(folder).get("mode", "animated") == "animated" else None


def still(file: Path, at: float = 0.35) -> Image.Image | None:
    """One frame of the loop (`at` of the way through): the thumbnail, and the still behind an animated cover."""
    import cv2

    cap = cv2.VideoCapture(str(file))
    try:
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(cap.get(cv2.CAP_PROP_FRAME_COUNT) * at))
        ok, img = cap.read()
    finally:
        cap.release()
    return Image.fromarray(img[..., ::-1]) if ok else None


def state(folder: Path, suggested: str) -> dict:
    """What the page shows about the animated cover."""
    m = meta(folder)
    return {"loop": LOOP if (Path(folder) / LOOP).exists() else "", "cover_mode": mode(folder),
            "loop_prompt": m.get("prompt") or suggested, "loop_seconds": SECONDS,
            "loop_effects": [e for e in m.get("effects", DEFAULT_EFFECTS) if e in EFFECTS],
            "effect_choices": _effect_labels(), "loop_motion": m.get("motion", "parallax"),
            "loop_intensity": m.get("intensity", INTENSITY), "loop_depth": m.get("depth", True),
            "loop_regions": m.get("regions", []), "region_kinds": _region_kinds(),
            "loop_seam": m.get("seam"), "loop_changed": m.get("changed"), "loop_change_max": MAX_CHANGE, "loop_settings": m.get("settings"), "loop_movement": m.get("movement") or MOVEMENT,
            "video_model_ready": _video_model_ready(), "job": status(folder)}


def _region_kinds() -> dict[str, str]:
    from . import living

    return living.KINDS


def _video_model_ready() -> bool:
    from . import videogen

    return videogen.downloaded()


def _effect_labels() -> dict[str, str]:
    from .fx import EFFECTS as LABELS

    return {e: LABELS[e] for e in EFFECTS}


def edit(folder: Path, cover_mode: str | None = None, prompt: str | None = None, movement: str | None = None,
         regions: list | None = None) -> None:
    """ValueError for an unknown mode or a bad living region."""
    if cover_mode is not None and cover_mode not in MODES:
        raise ValueError("The cover is a picture or animated.")
    changes = {}
    if cover_mode is not None:
        changes["mode"] = cover_mode
    if prompt is not None:
        changes["prompt"] = prompt.strip()[:1500]
    if movement is not None:
        changes["movement"] = movement.strip()[:1500]
    if regions is not None:
        from . import living

        changes["regions"] = living.clean(regions)
    if changes:
        save_meta(folder, **changes)


def draw(folder: Path, suggested: str, again: bool = False, log=print) -> None:
    """Gemini draws the loop from the saved prompt (or `suggested`). One request; the result is cached by prompt."""
    from . import art

    subject = meta(folder).get("prompt") or suggested
    if again:   # motion_background caches by subject: a new take needs a different one
        subject += f" (take {int(time.time())})"
    clip = art.motion_background(subject, SIZE, loop=SECONDS, log=log)
    shutil.copy(clip, Path(folder) / LOOP)
    save_meta(folder, mode="animated")


# ---------- on this computer's GPU: a drawn still brought to life by crcontent/fx.py (free, no Gemini) ----------

STILL = "loop.png"   # the picture the GPU loop was made from
EFFECTS = ("rain", "dust", "bokeh", "glow", "snow", "sparkles", "embers", "petals")   # what can move (fx.EFFECTS)
DEFAULT_EFFECTS = ("dust", "bokeh", "glow")
FADE = 2.0   # seconds of the clip's end cross-faded into its start, so the loop has no seam
GPU_STYLE = "anime"   # the art model the room is drawn with, in the lofi tradition


def gpu_check() -> None:
    """ValueError saying what's missing when this computer can't draw the GPU loop."""
    from . import imagegen

    if not imagegen.installed():
        raise ValueError("Drawing on the GPU needs the AI add-on: Settings → AI features → Install AI add-on.")
    if not imagegen.gpu_name():
        raise ValueError("Drawing on the GPU needs an NVIDIA graphics card or an Apple Silicon Mac, and none was found.")
    if not imagegen.downloaded(GPU_STYLE):
        raise ValueError(f"Download the {imagegen.STYLES[GPU_STYLE]['label']} model first (Settings → AI features).")


def seamless(clip: Path, out: Path, loop: float, fade: float) -> None:
    """`clip` (loop + fade seconds long) as a `loop`-second clip that repeats with no seam: its last `fade` seconds
    dissolve into its first, so the end of each pass is exactly where the next one starts."""
    graph = (f"[0:v]split=3[x][y][z];"
             f"[x]trim=start={fade}:end={loop},setpts=PTS-STARTPTS[body];"
             f"[y]trim=start=0:end={fade},setpts=PTS-STARTPTS[a];"
             f"[z]trim=start={loop}:end={loop + fade},setpts=PTS-STARTPTS[b];"
             f"[b][a]xfade=transition=fade:duration={fade}:offset=0[head];"
             f"[head][body]concat=n=2:v=1:a=0,format=yuv420p[out]")
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(clip), "-filter_complex", graph, "-map", "[out]", "-an",
                    "-c:v", "libx264", "-crf", "18", "-preset", "medium", str(out)], check=True, capture_output=True)


MOTIONS = ("light", "character", "parallax", "living")   # light and particles over the still (fx) | the picture itself
# moving (videogen) | a slow 2.5D camera over the picture (parallax(), CPU) | parts you mark moving (living.py, CPU)
INTENSITY = 40   # parallax strength, 0..100
# what a character loop's video model is told: only how things move. Describing the picture (the drawing prompt's
# tags) makes it redraw the scene to match them, which is what tears a character apart
MOVEMENT = ("She blinks slowly and breathes gently, her head tilting a little to the music, her hair moving slightly. "
            "The camera stays fixed; keep the original illustration style and change nothing else in the scene.")


def animate(folder: Path, suggested: str, picture: Path | None = None, effects=None, again: bool = False,
            log=print, motion: str = "light", progress=None, intensity: int = INTENSITY) -> None:
    """Draw the cover on this computer's GPU (or take `picture`, the song's own cover) and bring it to life as a
    seamless SECONDS loop, free. motion "light": a slow breathing camera and moving light and particles (a minute or
    two). "parallax": the picture itself, a slow depth-layered camera loop (CPU; under a minute). "character": an
    image-to-video model moves the picture itself as the prompt says (a character nodding,
    steam rising; a few minutes, and a 24 GB download the first time). progress(done, total) while it is drawn."""
    import random

    from neonmekong import traditions

    from . import fx, imagegen, pipeline

    folder = Path(folder)
    effects = [e for e in (effects if effects is not None else DEFAULT_EFFECTS) if e in EFFECTS]
    motion = motion if motion in MOTIONS else "light"
    if motion == "character":
        from . import videogen

        videogen.check()
    if picture is None:
        gpu_check()
        prompt = meta(folder).get("prompt") or suggested
        log("drawing the cover on the GPU")
        picture = imagegen.generate(traditions.apply(prompt, "lofi"), GPU_STYLE, SIZE,
                                    seed=random.randint(1, 2 ** 31) if again else None,
                                    negative=", ".join(x for x in (traditions.avoid("lofi"), "text, watermark, logo") if x),
                                    log=log)
    try:
        if Path(picture).resolve() != (folder / STILL).resolve():
            shutil.copy(picture, folder / STILL)
        raw = folder / "loop.raw.mp4"
        depth, settings, changed = True, None, None
        try:
            if motion == "living":
                from . import living

                living.render(folder / STILL, folder / LOOP, meta(folder).get("regions"), log=log, progress=progress)
            elif motion == "parallax":
                log("Bringing it to life…")
                depth = parallax(folder / STILL, folder / LOOP, intensity, log=log, progress=progress)
            elif motion == "character":
                pipeline.release_gpu()   # the art model out, so the video model has the whole card
                free_memory()
                prompt = meta(folder).get("movement") or MOVEMENT
                seed, changed = best_take(folder / STILL, prompt, raw, random.randint(0, 2 ** 31) if again else 0,
                                          log, progress)
                settings = {**videogen.settings(), "seed": seed, "prompt": prompt, "changed": changed}
                log("Keeping the picture sharp…")
                composite(raw, folder / STILL)
                repeat(raw, folder / LOOP, SECONDS)
            else:
                log("Bringing it to life…")
                fx.render_shot(folder / STILL, SECONDS + FADE, raw, size=SIZE, motion="breathe", effects=effects,
                               seed=random.randint(0, 999) if again else 7,
                               progress=(lambda f: progress(round(f * 100), 100)) if progress else None)
                seamless(raw, folder / LOOP, SECONDS, FADE)
        finally:
            raw.unlink(missing_ok=True)
    finally:
        pipeline.release_gpu()   # the art and depth models give the GPU back to lyric timing and renders
    save_meta(folder, mode="animated", effects=effects, motion=motion, intensity=intensity, depth=depth,
              settings=settings, seam=seam(folder / LOOP), changed=changed)


def free_memory() -> None:
    """Drop the models the engine keeps in system RAM between jobs (the art model parked after a drawing, Whisper):
    the video model runs in its own process and needs that memory."""
    import gc

    from . import align, imagegen

    imagegen.drop_parked()
    align.release()
    gc.collect()


def repeat(take: Path, out: Path, loop: float, fps: int = 30) -> None:
    """A take played forward then backward (no frame twice at either turn), a whole number of times in exactly `loop`
    seconds at `fps` (each pass sped up or slowed down a little to fit), scaled up to SIZE: seamless whatever the
    take's last frame is, and the wrap from the clip's end to its start lands on a turn, not mid-motion.
    shortcut: one take repeated (every ~6-12 s the same motion); several takes with other seeds would vary it, ~3x slower."""
    import cv2

    cap = cv2.VideoCapture(str(take))
    count, rate = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)), cap.get(cv2.CAP_PROP_FPS) or 24
    cap.release()
    if count < 2:
        raise RuntimeError("The video model came back without any frames.")
    one = take.with_name(take.stem + ".once.mp4")
    tmp = out.with_name(out.stem + ".tmp.mp4")
    try:
        # forward 0..n-1, then backward n-2..1: the next pass starts on frame 0 again
        graph = (f"[0:v]split[f][r];[r]reverse,trim=start_frame=1:end_frame={count - 1},setpts=PTS-STARTPTS[b];"
                 f"[f][b]concat=n=2:v=1:a=0[out]")
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(take), "-filter_complex", graph, "-map", "[out]",
                        "-an", "-c:v", "libx264", "-crf", "16", str(one)], check=True, capture_output=True)
        once = (2 * count - 2) / rate
        times = max(1, round(loop / once))
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-stream_loop", str(times - 1), "-i", str(one), "-vf",
                        f"setpts={loop / times / once:.6f}*PTS,fps={fps},scale={SIZE[0]}:{SIZE[1]}:flags=lanczos,"
                        f"format=yuv420p", "-frames:v", str(round(loop * fps)), "-an", "-c:v", "libx264", "-crf", "18",
                        "-preset", "medium", "-movflags", "+faststart", str(tmp)], check=True, capture_output=True)
        os.replace(tmp, out)   # only a finished clip replaces the old loop
    finally:
        one.unlink(missing_ok=True)
        tmp.unlink(missing_ok=True)


def stabilize(take: Path) -> None:
    """`take` with the video model's camera drift (it pushes in or pans whatever the prompt says) undone, in place:
    each frame lined up back onto the first (the cover) by the background's features, and what the move cropped off
    the edges filled from the first frame. The background holds still; the subjects keep their own motion."""
    import cv2
    import numpy as np

    cap = cv2.VideoCapture(str(take))
    rate = cap.get(cv2.CAP_PROP_FPS) or 24
    frames = []
    while True:
        ok, f = cap.read()
        if not ok:
            break
        frames.append(f)
    cap.release()
    if len(frames) < 2:
        return
    h, w = frames[0].shape[:2]
    orb = cv2.ORB_create(3000)
    gray = lambda f: cv2.cvtColor(f, cv2.COLOR_BGR2GRAY)   # noqa: E731
    k0, d0 = orb.detectAndCompute(gray(frames[0]), None)
    match = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
    ones = np.full((h, w), 255, np.uint8)
    last = np.float32([[1, 0, 0], [0, 1, 0]])
    tmp = take.with_name(take.stem + ".still.mp4")
    enc = subprocess.Popen(["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{w}x{h}",
                            "-r", f"{rate:g}", "-i", "-", "-an", "-c:v", "libx264", "-crf", "14", "-pix_fmt", "yuv420p",
                            str(tmp)], stdin=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        for f in frames:
            k, d = orb.detectAndCompute(gray(f), None)
            pairs = match.match(d, d0) if d is not None and d0 is not None else []
            if len(pairs) >= 12:
                m, inliers = cv2.estimateAffinePartial2D(np.float32([k[p.queryIdx].pt for p in pairs]),
                                                         np.float32([k0[p.trainIdx].pt for p in pairs]),
                                                         method=cv2.RANSAC, ransacReprojThreshold=2.0)
                if m is not None and inliers.sum() >= 12:   # moving subjects are the outliers; too few = keep the last
                    last = m.astype(np.float32)
            held = cv2.warpAffine(f, last, (w, h), flags=cv2.INTER_CUBIC)
            # where the move had cropped the picture, the first frame; feathered so there's no hard edge
            keep = cv2.GaussianBlur(cv2.erode(cv2.warpAffine(ones, last, (w, h)), np.ones((9, 9), np.uint8)), (15, 15), 0)
            a = (keep.astype(np.float32) / 255)[..., None]
            enc.stdin.write((held * a + frames[0] * (1 - a)).astype(np.uint8).tobytes())
        enc.stdin.close()
        if enc.wait() != 0:
            raise RuntimeError("FFmpeg couldn't hold the camera still: "
                               + enc.stderr.read().decode(errors="replace").strip()[-300:])
        os.replace(tmp, take)
    finally:
        if enc.poll() is None:
            enc.kill()
        enc.stderr.close()
        tmp.unlink(missing_ok=True)


TAKES = 3          # video-model takes at most, for one that animates the picture instead of redrawing it
MAX_CHANGE = 0.35  # the share of the picture a good take moves: the good ones measured ~0.15-0.18, one that morphed
                   # the whole scene (the character fading out, window frames melting) 0.65


def _moving(frames) -> "np.ndarray":
    """Where a take moves (uint8 0/1 at a quarter of its size): each pixel's spread over the take, so the model's
    grain and lone flickering pixels don't count."""
    import cv2
    import numpy as np

    th, tw = frames[0].shape[:2]
    small = np.stack([cv2.resize(cv2.cvtColor(f, cv2.COLOR_BGR2GRAY), (tw // 4, th // 4), interpolation=cv2.INTER_AREA)
                      for f in frames]).astype(np.float32)
    moving = (small.std(0) > 6).astype(np.uint8)
    return cv2.morphologyEx(moving, cv2.MORPH_OPEN, np.ones((2, 2), np.uint8))


def changed(take: Path) -> float:
    """The share of the picture a take moves (0..1): above MAX_CHANGE the model redrew the scene."""
    import cv2

    cap = cv2.VideoCapture(str(take))
    frames = []
    while True:
        ok, f = cap.read()
        if not ok:
            break
        frames.append(f)
    cap.release()
    return round(float(_moving(frames).mean()), 3) if len(frames) > 1 else 0.0


def best_take(still: Path, prompt: str, out: Path, seed: int, log=print, progress=None) -> tuple[int, float]:
    """A video-model take of `still` at `out`, camera held still: one that moves at most MAX_CHANGE of the picture,
    trying up to TAKES seeds, else the one that changed it least. Returns (its seed, its share changed)."""
    import random

    from . import videogen

    best = None   # (changed, seed)
    keep = out.with_name(out.stem + ".best.mp4")
    try:
        for n in range(TAKES):
            if n:
                seed = random.randint(0, 2 ** 31)
                log(f"Take {n} redrew {best[0]:.0%} of the picture instead of animating it: trying another "
                    f"({n + 1} of {TAKES})")
            videogen.take(still, prompt, out, seed=seed, log=log, progress=progress)
            log("Holding the camera still…")
            stabilize(out)
            share = changed(out)
            if best is None or share < best[0]:
                best = (share, seed)
                shutil.copy(out, keep)
            if share <= MAX_CHANGE:
                break
        shutil.copy(keep, out)
    finally:
        keep.unlink(missing_ok=True)
    return best[1], best[0]


def composite(take: Path, still: Path) -> None:
    """`take` (the video model's low-resolution redraw of the whole picture, camera held still) rebuilt at SIZE, in
    place: the original picture at full resolution wherever nothing moves, the take's frames only where something
    does (found from how much each pixel changes over the take), feathered between. So the illustration stays crisp
    and its colours never flicker; only the moving parts (a hand, hair, a tail) come from the model."""
    import cv2
    import numpy as np

    from neonmekong.thumbnail import cover_crop

    cap = cv2.VideoCapture(str(take))
    rate = cap.get(cv2.CAP_PROP_FPS) or 24
    frames = []
    while True:
        ok, f = cap.read()
        if not ok:
            break
        frames.append(f)
    cap.release()
    if len(frames) < 2:
        return
    W, H = SIZE
    th, tw = frames[0].shape[:2]
    # the take is a cover crop of the picture at its own aspect (768x448): rebuild at that aspect, then cut SIZE
    # from the middle, so the picture and the take line up and nothing is stretched
    bh = round(W * th / tw)
    base = np.asarray(cover_crop(Image.open(still), W, bh))[..., ::-1]
    # what moves: each pixel's spread over the take, at low resolution so the model's grain doesn't count
    moving = cv2.dilate(_moving(frames), np.ones((5, 5), np.uint8))   # room for the motion's edges
    alpha = cv2.GaussianBlur(cv2.resize(moving.astype(np.float32), (W, bh), interpolation=cv2.INTER_LINEAR),
                             (0, 0), W / 150)[..., None]
    top = (bh - H) // 2
    base, alpha = base[top:top + H], alpha[top:top + H]
    tmp = take.with_name(take.stem + ".sharp.mp4")
    enc = subprocess.Popen(["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}",
                            "-r", f"{rate:g}", "-i", "-", "-an", "-c:v", "libx264", "-crf", "14", "-pix_fmt", "yuv420p",
                            str(tmp)], stdin=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        for f in frames:
            up = cv2.resize(f, (W, bh), interpolation=cv2.INTER_LANCZOS4)[top:top + H]
            enc.stdin.write((up * alpha + base * (1 - alpha)).astype(np.uint8).tobytes())
        enc.stdin.close()
        if enc.wait() != 0:
            raise RuntimeError("FFmpeg couldn't sharpen the animated cover: "
                               + enc.stderr.read().decode(errors="replace").strip()[-300:])
        os.replace(tmp, take)
    finally:
        if enc.poll() is None:
            enc.kill()
        enc.stderr.close()
        tmp.unlink(missing_ok=True)


def seam(file: Path) -> dict:
    """How well the clip joins its own start: {"jump": the change from its last frame to its first, in mean grey
    levels, "step": a typical (95th percentile) frame-to-frame change, "ok": the jump is no bigger than motion the
    clip already has}. Measured, so a loop that doesn't join (a cut, a pop) is reported, not assumed seamless."""
    import cv2
    import numpy as np

    cap = cv2.VideoCapture(str(file))
    frames = []
    while True:
        ok, f = cap.read()
        if not ok:
            break
        frames.append(cv2.resize(cv2.cvtColor(f, cv2.COLOR_BGR2GRAY), (160, 90), interpolation=cv2.INTER_AREA)
                      .astype(np.float32))
    cap.release()
    if len(frames) < 3:
        return {"jump": 0.0, "step": 0.0, "ok": False}
    steps = [float(np.abs(a - b).mean()) for a, b in zip(frames, frames[1:])]
    jump, step = float(np.abs(frames[-1] - frames[0]).mean()), float(np.percentile(steps, 95))
    # 2x headroom: an encoder keyframe alone roughly doubles one step; the floor keeps near-still clips from failing
    return {"jump": round(jump, 2), "step": round(step, 2), "ok": jump <= max(2 * step, 1.5)}


# ---------- parallax: the picture itself under a slow 2.5D camera, exactly periodic (CPU; depth from fx when it can) ----------

FPS = 30


def camera(t: float, intensity: int) -> tuple[float, float, float]:
    """The camera at t seconds: (x, y shift as fractions of the frame, zoom). Sines of whole turns per SECONDS, so
    position and velocity at SECONDS equal those at 0: pass after pass joins with no jump. Within 2% / 1.5% / 2% at
    intensity 100."""
    a, w = intensity / 100, 2 * math.pi * t / SECONDS
    return 0.02 * a * math.sin(w), 0.015 * a * math.sin(2 * w), 1 + 0.02 * a * (0.5 - 0.5 * math.cos(w))


def read_still(still: Path) -> Image.Image:
    """The cover picture at SIZE (cover-cropped, and saved back so a depth map or regions are of exactly what is
    shown); ValueError when it can't be read."""
    try:
        with Image.open(still) as im:
            pic = im.convert("RGB")
    except (OSError, ValueError):
        raise ValueError("The cover picture can't be read: upload it again as a PNG, JPEG or WebP.")
    from neonmekong.thumbnail import cover_crop

    if pic.size != SIZE:
        pic = cover_crop(pic, *SIZE)
        pic.save(still)
    return pic


def write_loop(out: Path, frame, size: tuple[int, int], seconds: float | None = None, fps: int | None = None,
               progress=None) -> None:
    """A loop of frame(t) (RGB uint8 arrays at `size`, t from 0 to just under `seconds`) encoded to `out` (H.264
    yuv420p, no audio): rendered beside it and swapped in only once it checks out, so a failed render keeps the old
    loop. RuntimeError when FFmpeg is missing or fails."""
    import cv2

    seconds, fps = seconds or SECONDS, fps or FPS
    W, H = size
    tmp = out.with_name(out.stem + ".tmp.mp4")
    frames = round(seconds * fps)
    try:
        enc = subprocess.Popen(["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                                "-r", str(fps), "-i", "-", "-frames:v", str(frames), "-an", "-c:v", "libx264", "-crf",
                                "18", "-preset", "medium", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(tmp)],
                               stdin=subprocess.PIPE, stderr=subprocess.PIPE)
    except FileNotFoundError:
        raise RuntimeError("FFmpeg isn't installed, so the animated cover can't be encoded.")
    try:
        try:
            for i in range(frames):
                enc.stdin.write(frame(i / fps).tobytes())
                if progress:
                    progress(i + 1, frames)
            enc.stdin.close()
        except BrokenPipeError:
            pass
        if enc.wait() != 0:
            raise RuntimeError("FFmpeg couldn't encode the animated cover: "
                               + enc.stderr.read().decode(errors="replace").strip()[-300:])
        cap = cv2.VideoCapture(str(tmp))
        got = (int(cap.get(cv2.CAP_PROP_FRAME_COUNT)), int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), cap.read()[0])
        cap.release()
        if got != (frames, W, True):
            raise RuntimeError(f"The animated cover came out wrong ({got[0]} frames at {got[1]} wide).")
        os.replace(tmp, out)
    finally:
        if enc.poll() is None:
            enc.kill()
        enc.stderr.close()
        tmp.unlink(missing_ok=True)


def parallax(still: Path, out: Path, intensity: int = INTENSITY, log=print, progress=None) -> bool:
    """`still` as a SECONDS loop at FPS (SIZE, H.264 yuv420p, no audio) written to `out`: the near parts of the
    picture (fx's depth map) slide further than the far ones. Without the depth model it is a flat 2D drift.
    Rendered beside `out` and swapped in only once it checks out, so a failed render keeps the old loop.
    Returns whether depth was used; ValueError for an unreadable picture or intensity out of 0..100."""
    import cv2
    import numpy as np

    if not 0 <= intensity <= 100:
        raise ValueError("Parallax intensity is 0 to 100.")
    pic = read_still(still)
    W, H = SIZE
    img = np.asarray(pic)
    k = 1.0   # how far each pixel moves with the camera: near 1, far 0.25
    try:
        from . import fx

        d = fx.depth_map(Path(still)).float().cpu().numpy()[0, 0]
        k = 0.25 + 0.75 * cv2.resize(d, SIZE, interpolation=cv2.INTER_LINEAR)
    except Exception as e:   # no torch / no depth model (offline): the documented flat fallback
        log(f"No depth model ({type(e).__name__}): a flat 2D drift instead of parallax")
    # zoomed in just enough that the furthest shift never samples past the picture's edge
    over = 1 / (1 - 2 * 0.02 * intensity / 100)
    xs, ys = np.meshgrid(np.arange(W, dtype=np.float32), np.arange(H, dtype=np.float32))
    cx, cy = (W - 1) / 2, (H - 1) / 2
    xs, ys = xs - cx, ys - cy

    def frame(t):   # every frame from the original picture and absolute time: nothing accumulates
        dx, dy, z = camera(t, intensity)
        mx = cx + xs / (over * z) - k * (dx * W)
        my = cy + ys / (over * z) - k * (dy * H)
        return cv2.remap(img, np.asarray(mx, np.float32), np.asarray(my, np.float32), cv2.INTER_CUBIC,
                         borderMode=cv2.BORDER_REFLECT)

    write_loop(out, frame, SIZE, progress=progress)
    return not isinstance(k, float)


# ---------- the GPU loop as a background job: its first run downloads 24 GB, far longer than a request ----------

_jobs: dict[str, dict] = {}   # song folder -> {state, text, done, total, error}
_gpu = threading.Lock()       # one GPU loop at a time: two would not fit the card


def status(folder: Path) -> dict:
    return dict(_jobs.get(str(Path(folder).resolve()), {"state": "idle", "text": "", "done": 0, "total": 0, "error": ""}))


def start(folder: Path, work) -> dict:
    """Run work(log, progress) in the background for this song; RuntimeError while another GPU loop is being made."""
    if not _gpu.acquire(blocking=False):
        raise RuntimeError("Another animated cover is being made on the GPU. Wait for it to finish.")
    key = str(Path(folder).resolve())
    job = _jobs[key] = {"state": "running", "text": "Starting…", "done": 0, "total": 0, "error": ""}

    def log(text):
        job["text"] = str(text).strip()

    def progress(done, total):
        job.update(done=done, total=total)

    def run():
        try:
            work(log, progress)
            job.update(state="done", text="Done")
        except Exception as e:   # shown on the page, so the job never just disappears
            job.update(state="error", error=(str(e).strip().splitlines() or [repr(e)])[-1][-300:])
        finally:
            _gpu.release()

    threading.Thread(target=run, daemon=True).start()
    return status(folder)


def upload(folder: Path, name: str, stream) -> None:
    """Your own clip (`stream`: a binary file) as the loop; ValueError when it isn't a video this can read."""
    import cv2

    ext = Path(name or "").suffix.lower()
    if ext not in EXTS:
        raise ValueError("Upload the animated cover as an mp4, webm or mov video.")
    tmp = Path(folder) / f"loop.new{ext}"
    with open(tmp, "wb") as out:
        while chunk := stream.read(1 << 20):
            out.write(chunk)
    cap = cv2.VideoCapture(str(tmp))
    ok = cap.read()[0]
    cap.release()
    if not ok:
        tmp.unlink(missing_ok=True)
        raise ValueError("That file isn't a video I can read.")
    try:
        if ext == ".mp4":
            tmp.replace(Path(folder) / LOOP)
        else:   # both renders and the page want one mp4
            subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(tmp), "-an", "-c:v", "libx264", "-pix_fmt",
                            "yuv420p", str(Path(folder) / LOOP)], check=True, capture_output=True)
    finally:
        tmp.unlink(missing_ok=True)
    save_meta(folder, mode="animated")


def copy(folder: Path, source: Path) -> None:
    """Another song's loop for this one (no Gemini request); FileNotFoundError when it has none."""
    src = Path(source) / LOOP
    if not src.exists():
        raise FileNotFoundError("That song has no animated cover.")
    if Path(source).resolve() != Path(folder).resolve():
        shutil.copy(src, Path(folder) / LOOP)
    save_meta(folder, mode="animated")


def remove(folder: Path) -> None:
    (Path(folder) / LOOP).unlink(missing_ok=True)
    (Path(folder) / STILL).unlink(missing_ok=True)
    (Path(folder) / "loop.preview.mp4").unlink(missing_ok=True)   # living.PREVIEW
    save_meta(folder, mode="picture")


def others(folders, here: Path, title) -> list[dict]:
    """[{key, title}] of the other song folders with a loop to reuse; `title(folder)` names one."""
    return [{"slug": f.name, "title": title(f)} for f in folders
            if f.is_dir() and Path(f).resolve() != Path(here).resolve() and (f / LOOP).exists()]
