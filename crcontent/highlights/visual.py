"""Step 3 — visuals: how good the picture looks each second, as it will appear in the vertical clip.

The lyric-free picture (work/joined.mp4) is scored when there is one, so burned-in lyrics don't count as detail or
motion, cropped to the 9:16 window the clip will show. Each sample is scored for sharpness, colourfulness, motion
and faces; black, blurry or frozen stretches score low. Scene cuts come from PySceneDetect.
Needs opencv-python-headless and scenedetect (requirements-highlights.txt).
"""
import math
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from .settings import blend

SAMPLE_W, SAMPLE_H = 360, 640


def crop_filter(size: tuple[int, int], out_w: int = SAMPLE_W, out_h: int = SAMPLE_H) -> str:
    """ffmpeg filter: the centre 9:16 window of a frame (the whole frame when it's already vertical), scaled."""
    w, h = size
    crop = f"crop=ih*9/16:ih," if w * 16 > h * 9 + 16 else ""
    return f"{crop}scale={out_w}:{out_h}:flags=area"


def frames(video: Path, size: tuple[int, int], fps: float, start: float = 0.0, length: float | None = None,
           out_w: int = SAMPLE_W, out_h: int = SAMPLE_H):
    """(time, BGR frame) samples of the clip's 9:16 window, streamed from ffmpeg."""
    cmd = ["ffmpeg", "-v", "error", *(["-ss", f"{start:.3f}"] if start else []), "-i", str(video),
           *(["-t", f"{length:.3f}"] if length else []), "-an",
           "-vf", f"fps={fps},{crop_filter(size, out_w, out_h)}", "-f", "rawvideo", "-pix_fmt", "bgr24", "-"]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stdin=subprocess.DEVNULL)
    n = out_w * out_h * 3
    k = 0
    try:
        while True:
            buf = proc.stdout.read(n)
            if len(buf) < n:
                break
            yield start + (k + 0.5) / fps, np.frombuffer(buf, np.uint8).reshape(out_h, out_w, 3)
            k += 1
    finally:
        proc.stdout.close()
        proc.wait()


_cascades: dict = {}


def cascade(name: str):
    import cv2

    if name not in _cascades:
        c = cv2.CascadeClassifier(str(Path(cv2.data.haarcascades) / name))
        if c.empty():  # the .xml is missing (an engine build without cv2's data): score frames without faces
            print(f"  ! OpenCV's {name} is missing, so highlights are picked without face detection")
            c = None
        _cascades[name] = c
    return _cascades[name]


def faces(gray: np.ndarray) -> list[tuple[int, int, int, int]]:
    """Frontal faces (x, y, w, h), biggest first. Haar cascades find real people; drawn (anime) faces mostly not."""
    detector = cascade("haarcascade_frontalface_default.xml")
    if detector is None:
        return []
    min_side = max(24, gray.shape[1] // 12)
    found = detector.detectMultiScale(
        gray, scaleFactor=1.15, minNeighbors=6, minSize=(min_side, min_side))
    return sorted((tuple(int(v) for v in f) for f in found), key=lambda f: -f[2] * f[3])


def eyes_open(gray: np.ndarray, face: tuple[int, int, int, int]) -> float:
    """0..1: open eyes found in the upper half of the face (the eye cascade misses closed eyes)."""
    detector = cascade("haarcascade_eye_tree_eyeglasses.xml")
    if detector is None:
        return 0.0
    x, y, w, h = face
    top = gray[y:y + h // 2, x:x + w]
    found = detector.detectMultiScale(
        top, scaleFactor=1.1, minNeighbors=5, minSize=(max(8, w // 10), max(8, w // 10)))
    return min(1.0, len(found) / 2)


def sharpness(gray: np.ndarray) -> float:
    """0..1 from the variance of the Laplacian (log scale: soft art ~0.4, crisp detail ~0.9, blur < 0.25)."""
    import cv2

    v = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    return float(np.clip((math.log10(v + 1) - 0.8) / 2.2, 0, 1))


def colourfulness(bgr: np.ndarray) -> float:
    """0..1 Hasler & Süsstrunk colourfulness (~0.5 is a nicely colourful picture)."""
    b, g, r = (bgr[..., i].astype(np.float32) for i in range(3))
    rg, yb = r - g, (r + g) / 2 - b
    c = math.hypot(rg.std(), yb.std()) + 0.3 * math.hypot(rg.mean(), yb.mean())
    return float(min(c / 100, 1))


def contrast(gray: np.ndarray) -> float:
    return float(min(gray.std() / 64, 1))


@dataclass
class Visual:
    source: str                                   # the file that was scored
    cuts: list[float]                             # scene changes (s)
    per_second: dict[str, list[float]] = field(default_factory=dict)  # motion/sharpness/colour/faces/cuts/brightness
    method: str = ""


def _scene_cuts(video: Path, log) -> tuple[list[float], str]:
    try:
        from scenedetect import ContentDetector, detect
    except ImportError:
        log("      PySceneDetect isn't installed (pip install -r requirements-highlights.txt); cuts from frame changes")
        return [], ""
    scenes = detect(str(video), ContentDetector(threshold=27.0, min_scene_len=8), show_progress=False)
    return [float(s[0].get_seconds()) for s in scenes[1:]], "PySceneDetect"


def analyze(video: Path, size: tuple[int, int], total: float, cfg: dict, log=print) -> Visual:
    import cv2

    n = max(1, math.ceil(total))
    fps = float(cfg["visual"].get("samples_per_second", 2))
    rows: list[tuple[float, dict]] = []
    prev = None
    for t, bgr in frames(video, size, fps):
        gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
        small = cv2.resize(gray, (90, 160), interpolation=cv2.INTER_AREA).astype(np.float32)
        motion = 0.0 if prev is None else float(np.abs(small - prev).mean())
        prev = small
        found = faces(gray)
        face = min(1.0, (found[0][2] * found[0][3]) / (gray.size * 0.06)) if found else 0.0
        rows.append((t, {"sharpness": sharpness(gray), "colour": colourfulness(bgr), "motion_raw": motion,
                         "faces": face, "brightness": float(gray.mean() / 255), "contrast": contrast(gray)}))
    if not rows:
        raise RuntimeError(f"couldn't read frames from {video.name}")

    cuts, method = _scene_cuts(video, log)
    if not method:  # no PySceneDetect: a big jump between samples is a cut
        cuts = [t for t, r in rows if r["motion_raw"] > 40]

    def per_second(key: str) -> np.ndarray:
        out, cnt = np.zeros(n), np.zeros(n)
        for t, r in rows:
            s = min(n - 1, int(t))
            out[s] += r[key]
            cnt[s] += 1
        filled = cnt > 0
        out[filled] /= cnt[filled]
        if (~filled).any() and filled.any():
            out[~filled] = np.interp(np.arange(n)[~filled], np.arange(n)[filled], out[filled])
        return out

    # motion: mean pixel change between samples half a second apart; busy footage with a camera drift is ~25 levels,
    # fast action 40, a held picture with drifting particles ~3. A cut is one big change, not motion, so it's capped
    motion = np.clip(per_second("motion_raw"), 0, 45) / 40
    # cuts: a fresh picture every few seconds holds attention; each cut lifts the 3 s around it
    cut_score = np.zeros(n)
    for c in cuts:
        for s in range(max(0, int(c) - 1), min(n, int(c) + 2)):
            cut_score[s] = max(cut_score[s], 1 - abs(s + 0.5 - c) / 2)
    brightness = per_second("brightness")
    # black or near-black seconds (fades, title cards) are worth nothing whatever else they score
    usable = np.clip((brightness - 0.04) / 0.12, 0, 1)
    out = {"motion": np.clip(motion, 0, 1) * usable, "sharpness": per_second("sharpness") * usable,
           "colour": per_second("colour") * usable, "faces": per_second("faces") * usable,
           "cuts": cut_score * usable, "brightness": brightness, "contrast": per_second("contrast")}
    return Visual(video.name, cuts, {k: v.tolist() for k, v in out.items()},
                  f"OpenCV + {method or 'frame differences'}")


def score(v: Visual, cfg: dict) -> list[float]:
    w = cfg["visual"]["parts"]
    n = len(v.per_second["motion"])
    return [blend({k: v.per_second[k][t] for k in w}, w) for t in range(n)]
