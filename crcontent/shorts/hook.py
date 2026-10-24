"""Rule 1: the hook beat (0-2 s) shows the animal in motion. Candidate clips are scored and the best one wins, with
the 2 s of it to show.

Each clip is sampled (SAMPLE_FPS) and, between samples, tracked corners fit the camera's move (pan, zoom: a
similarity transform, RANSAC), and dense optical flow measures how far everything else travels besides it: the
subject's own motion, as a distance (fine detail like fur can't fake it). So:
- a slow zoom or pan: the camera moves, nothing in the frame does -> rejected
- static: neither moves -> rejected
- dark (fades, night shots) or soft -> rejected
Every window of the beat's length is scored (own motion, sharpness, exposure; never across a cut or in the first
fade-in). The best window then goes to Gemini with the planned shot (match.py), and judged() applies what it saw:
the wrong animal, no movement, a logo or an intro rejects it. Clips that fail are listed with the reason.
"""
import math
import subprocess
from dataclasses import asdict, dataclass, field
from pathlib import Path

import numpy as np

from ..highlights.visual import sharpness
from ..render import duration

SAMPLE_FPS = 8
SAMPLE_W = 480
SCAN_SECONDS = 20.0      # how much of a clip is scanned for its best window
SKIP_START = 0.4         # stock clips often fade in from black
CUT_JUMP = 38.0          # a mean grey-level change this big between samples is a cut, not motion
OWN_MOTION_MIN = 1.5     # % of the width the animal travels per sample, besides the camera: under it it's still
OWN_MOTION_FULL = 4.0    # ... from here on, full marks for motion
CAMERA_MOVE = 0.001      # camera travel (fraction of the width per sample) that counts as a pan or zoom
DARK = 0.16              # mean brightness under this: too dark for the first frame people see
SOFT = 0.35              # sharpness under this: blurred



@dataclass
class Sample:
    t: float
    bright: float
    sharp: float
    own: float = 0.0       # the subject's motion: % of the width it travels, besides the camera's move
    camera: float = 0.0    # the camera's move: fraction of the width travelled (pan + zoom)
    cut: bool = False


@dataclass
class Scan:
    file: str
    seconds: float
    start: float = 0.0         # the best window
    own: float = 0.0
    camera: float = 0.0
    sharp: float = 0.0
    bright: float = 0.0
    score: float = 0.0
    reject: str = ""           # why the clip can't open the Short ("" = it can)
    check: dict = field(default_factory=dict)  # Gemini's look at the window

    def to_json(self) -> dict:
        return {k: round(v, 3) if isinstance(v, float) else v for k, v in asdict(self).items()}


def focus_sharpness(gray: np.ndarray, rows: int = 6, cols: int = 4) -> float:
    """0..1 like highlights' sharpness(), but of the sharpest quarter of the frame: wildlife footage keeps the animal
    in focus over a blurred background, which drags the whole frame's score down."""
    h, w = gray.shape
    tiles = [sharpness(gray[r * h // rows:(r + 1) * h // rows, c * w // cols:(c + 1) * w // cols])
             for r in range(rows) for c in range(cols)]
    top = sorted(tiles)[-max(1, len(tiles) // 4):]
    return float(np.mean(top))


def _samples(path: Path, seconds: float) -> list[tuple[float, np.ndarray]]:
    """(time, grey frame SAMPLE_W wide) for the first `seconds` of the clip."""
    import cv2

    probe = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                            "stream=width,height", "-of", "csv=p=0", str(path)], stdin=subprocess.DEVNULL,
                           capture_output=True, text=True).stdout.strip().split(",")
    w, h = int(probe[0]), int(probe[1])
    out_h = round(SAMPLE_W * h / w / 2) * 2
    cmd = ["ffmpeg", "-v", "error", "-i", str(path), "-t", f"{seconds:.2f}", "-an",
           "-vf", f"fps={SAMPLE_FPS},scale={SAMPLE_W}:{out_h}:flags=area", "-f", "rawvideo", "-pix_fmt", "bgr24", "-"]
    raw = subprocess.run(cmd, stdin=subprocess.DEVNULL, capture_output=True).stdout
    n = SAMPLE_W * out_h * 3
    return [((k + 0.5) / SAMPLE_FPS, cv2.cvtColor(np.frombuffer(raw[k * n:(k + 1) * n], np.uint8)
                                                  .reshape(out_h, SAMPLE_W, 3), cv2.COLOR_BGR2GRAY))
            for k in range(len(raw) // n)]


FLOW_W = 240  # dense flow is measured on frames this wide (fast, and fine detail like fur can't fake motion)


def motion(prev: np.ndarray, cur: np.ndarray) -> tuple[float, float, bool]:
    """(own motion, camera move, cut) between two grey frames. The camera's move (pan, zoom) is fitted from tracked
    corners; own motion is how far the frame's parts travel besides it: dense optical flow minus the camera's flow,
    its 95th percentile (the moving animal, not the still background), in % of the frame width. A distance, not a
    change in brightness: a still close-up of fur changes many pixels by a hair's shift, but goes nowhere."""
    import cv2

    raw = float(np.abs(cur.astype(np.int16) - prev.astype(np.int16)).mean())
    if raw > CUT_JUMP:
        return 0.0, 0.0, True
    h, w = prev.shape
    camera, m = 0.0, None
    p0 = cv2.goodFeaturesToTrack(prev, maxCorners=300, qualityLevel=0.01, minDistance=7)
    if p0 is not None and len(p0) >= 12:
        p1, ok, _ = cv2.calcOpticalFlowPyrLK(prev, cur, p0, None, winSize=(21, 21), maxLevel=3)
        good = ok.ravel() == 1
        if good.sum() >= 12:
            m, _ = cv2.estimateAffinePartial2D(p0[good], p1[good], method=cv2.RANSAC, ransacReprojThreshold=2.0)
            if m is not None:
                scale = math.hypot(m[0, 0], m[1, 0])
                camera = (math.hypot(m[0, 2] + (scale - 1) * w / 2, m[1, 2] + (scale - 1) * h / 2)
                          + abs(scale - 1) * w / 2) / w
    fh = round(FLOW_W * h / w)
    a, b = (cv2.resize(f, (FLOW_W, fh), interpolation=cv2.INTER_AREA) for f in (prev, cur))
    flow = cv2.calcOpticalFlowFarneback(a, b, None, 0.5, 3, 15, 3, 5, 1.2, 0)
    if m is not None:  # the camera's own flow at every point, in the small frame's pixels
        ys, xs = np.mgrid[0:fh, 0:FLOW_W].astype(np.float32)
        k = w / FLOW_W
        flow[..., 0] -= (m[0, 0] - 1) * xs + m[0, 1] * ys + m[0, 2] / k
        flow[..., 1] -= m[1, 0] * xs + (m[1, 1] - 1) * ys + m[1, 2] / k
    bx, by = FLOW_W // 10, fh // 10
    travel = np.hypot(flow[..., 0], flow[..., 1])[by:fh - by, bx:FLOW_W - bx]
    own = float(np.percentile(travel, 95)) / FLOW_W * 100
    return own, camera, False


def scan(path: Path, beat: float) -> Scan:
    """The clip's best window of `beat` seconds, or why none will do."""
    total = duration(path)
    frames = _samples(path, min(total, SCAN_SECONDS))
    if len(frames) < 3:
        return Scan(str(path), total, reject="couldn't read the clip")
    samples = []
    for k, (t, gray) in enumerate(frames):
        s = Sample(t, float(gray.mean() / 255), focus_sharpness(gray))
        if k:
            s.own, s.camera, s.cut = motion(frames[k - 1][1], gray)
        samples.append(s)
    per = SAMPLE_FPS
    span = max(2, round(beat * per))
    best: Scan | None = None
    for i in range(1, max(2, len(samples) - span + 1)):
        win = samples[i:i + span]
        if not win or win[0].t < SKIP_START and total > beat + SKIP_START or any(s.cut for s in win[1:]):
            continue
        own = float(np.mean([s.own for s in win]))
        camera = float(np.mean([s.camera for s in win]))
        sharp = float(np.mean([s.sharp for s in win]))
        bright = float(np.mean([s.bright for s in win]))
        exposure = max(0.0, 1 - abs(bright - 0.5) / 0.45)
        score = 0.5 * min(own / OWN_MOTION_FULL, 1) + 0.3 * sharp + 0.2 * exposure
        cand = Scan(str(path), total, round(max(win[0].t - 0.5 / per, 0), 3), own, camera, sharp, bright, score)
        if best is None or cand.score > best.score:
            best = cand
    if best is None:
        return Scan(str(path), total, reject="no stretch without a cut")
    if best.bright < DARK:
        best.reject = f"too dark (brightness {best.bright:.2f})"
    elif best.own < OWN_MOTION_MIN:
        best.reject = ("slow zoom or pan: only the camera moves" if best.camera > CAMERA_MOVE
                       else "static: nothing moves")
    elif best.sharp < SOFT:
        best.reject = f"soft or blurred (sharpness {best.sharp:.2f})"
    return best


def judged(s: Scan, check: dict) -> Scan:
    """`s` with Gemini's look at its window applied (match.check): the wrong animal, one that doesn't move, a logo or
    an intro rejects it. (How well it shows the planned shot is its match score, weighed by the picker.)"""
    s.check = check
    if s.reject:
        return s
    if not check.get("animal", True):
        s.reject = f"not the right animal ({check.get('seen', '')})"
    elif check.get("logo_or_text"):
        s.reject = "logo, watermark or text in the shot"
    elif check.get("intro_or_title"):
        s.reject = "an intro, title card or fade"
    elif check.get("in_motion") is False:
        s.reject = f"the animal doesn't move in the frames Gemini saw ({check.get('seen', '')})"
    return s
