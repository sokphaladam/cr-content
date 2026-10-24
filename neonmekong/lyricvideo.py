"""16:9 lyric video, drawn frame by frame (OpenCV + numpy) and piped to ffmpeg.

Look is the same for every song: slow zoom/pan over the neon-city-on-a-river background, shimmering river, drifting
particles, brightness pulse on the real beat times, large lyrics (chorus lines bigger with a neon glow), the channel
badge in the same corner, a title card for the first seconds, a subscribe pill just after the first chorus, and
clean space for the end screen in the last 20 seconds.
"""
import bisect
import json
import math
import random
import re
import subprocess
import tempfile
import time
from dataclasses import dataclass, replace
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from . import analyze, config, hook, songjson, thumbnail
from .suno import parse as parse_suno

FULL = (1920, 1080)
DRAFT = (960, 540)
FPS = 30
TITLE_CARD = (0.4, 5.6)   # seconds on screen (max 6)
PILL_LEN = 4.0
END_ZONE = 20.0
PULSE_DECAY = 0.18
LYRIC_Y, END_LYRIC_Y = 0.58, 0.24   # lyric centre as a fraction of the height


# ---------------------------------------------------------------- timeline for each hook option

@dataclass
class Variant:
    name: str
    audio: Path | None
    lines: list[dict]
    beats: list[float]
    chorus_end: float | None
    duration: float


def variant(folder: Path, data: dict, option: str) -> Variant:
    """The song on the video's own timeline: option is full (no hook edit), trim or preview."""
    mix, _ = analyze.find_audio(folder)
    beats, dur = list(data["beat_times"]), float(data["duration"])
    ce = (data.get("chorus") or {}).get("end")
    lines = analyze.parse_lrc((folder / "lyrics.lrc").read_text(encoding="utf-8"))
    audio = mix
    if option != "full":
        hdir = folder / "out" / "hook"
        spec = json.loads((hdir / "hook.json").read_text(encoding="utf-8"))[option]
        lines = analyze.parse_lrc((hdir / f"lyrics_{option}.lrc").read_text(encoding="utf-8"))
        audio, dur = hdir / f"audio_{option}.wav", float(spec["duration"])
        if option == "trim":
            cut = spec["audio_start"]
            beats, ce = [b - cut for b in beats if b >= cut], None if ce is None else ce - cut
        else:
            p0, off = spec["src_start"], spec["song_offset"]
            beats = [b - p0 for b in beats if p0 <= b < p0 + spec["length"]] + [b + off for b in beats]
            ce = None if ce is None else ce + off
    if audio is not None and not audio.exists():
        if not config.dry_run():
            raise FileNotFoundError(f"missing {audio} (run the hook step first)" if option != "full"
                                    else f"no audio.wav / audio.mp3 in {folder}")
        audio = None
    return Variant(option, audio, lines, beats, ce, dur)


# ---------------------------------------------------------------- pure timing helpers

def ease(x: float) -> float:
    x = min(max(x, 0.0), 1.0)
    return x * x * (3 - 2 * x)


def pulse(t: float, beats: list[float]) -> float:
    """1.0 on a beat, decaying to 0."""
    i = bisect.bisect_right(beats, t) - 1
    return math.exp(-(t - beats[i]) / PULSE_DECAY) if i >= 0 else 0.0


def lyric_y(t: float, dur: float) -> float:
    """Lyric centre (fraction of height): moves up for the end screen over 0.8s at dur - 20s."""
    return LYRIC_Y + (END_LYRIC_Y - LYRIC_Y) * ease((t - (dur - END_ZONE)) / 0.8)


def card_alpha(t: float) -> float:
    a, b = TITLE_CARD
    return min(ease((t - a) / 0.5), ease((b - t) / 0.5))


def pill_state(t: float, chorus_end: float | None, dur: float) -> tuple[float, float]:
    """(alpha, slide) of the subscribe pill: shown PILL_LEN seconds from the end of the first chorus."""
    if chorus_end is None or t > dur - END_ZONE:
        return 0.0, 0.0
    u = t - (chorus_end + 0.3)
    if u < 0 or u > PILL_LEN:
        return 0.0, 0.0
    return min(ease(u / 0.5), ease((PILL_LEN - u) / 0.5)), 1.0 - ease(u / 0.5)


def active_line(t: float, lines: list[dict], starts: list[float]) -> tuple[int, float] | None:
    """(index, alpha) of the lyric on screen at t. A line fades in just before it is sung and out after it."""
    i = bisect.bisect_right(starts, t + 0.1) - 1
    if i < 0:
        return None
    end = lines[i]["end"] + 0.5
    if i + 1 < len(lines):
        end = min(end, starts[i + 1] - 0.1)
    if t > end:
        return None
    return i, min(ease((t - (starts[i] - 0.1)) / 0.25), ease((end - t) / 0.3))


def norm(text: str) -> str:
    return re.sub(r"[^a-z0-9 ]", "", text.lower()).strip()


# ---------------------------------------------------------------- sprites (premultiplied BGR float + alpha)

def _arrays(layer: Image.Image) -> tuple[np.ndarray, np.ndarray]:
    a = np.asarray(layer, np.float32) / 255.0
    return a[..., 2::-1] * a[..., 3:4], a[..., 3:4]  # RGB -> BGR, premultiplied


def text_sprite(lines: list[str], size: int, fill, glow, blur: float, align: str = "center", stroke: int = 4) -> dict:
    f = thumbnail.font(size)
    probe = ImageDraw.Draw(Image.new("L", (1, 1)))
    pad = int(blur * 3) + stroke + 4
    lead = int(size * 1.14)
    w = int(max(probe.textlength(ln, font=f) for ln in lines)) + 2 * pad
    h = lead * len(lines) + 2 * pad
    text, halo = Image.new("RGBA", (w, h), (0, 0, 0, 0)), Image.new("RGBA", (w, h), (0, 0, 0, 0))
    for layer, colour, edge, sc in ((halo, glow, glow, stroke + 2), (text, fill, (10, 6, 24), stroke)):
        d = ImageDraw.Draw(layer)
        for i, ln in enumerate(lines):
            x, anchor = (w / 2, "ma") if align == "center" else (pad, "la")
            d.text((x, pad + i * lead), ln, font=f, fill=(*colour, 255), anchor=anchor, stroke_width=sc,
                   stroke_fill=(*edge, 255))
    halo = halo.filter(ImageFilter.GaussianBlur(blur))
    pm_t, a_t = _arrays(text)
    pm_g, _ = _arrays(halo)
    return {"pm": pm_t, "a": a_t, "glow": pm_g, "w": w, "h": h}


def wrap(text: str, size: int, max_w: int, max_lines: int = 2) -> tuple[list[str], int]:
    """Wrap to <= max_lines lines; shrink the font if that is not enough."""
    probe = ImageDraw.Draw(Image.new("L", (1, 1)))
    for s in range(size, 20, -4):
        f, lines, cur = thumbnail.font(s), [], ""
        for word in text.split():
            trial = f"{cur} {word}".strip()
            if probe.textlength(trial, font=f) <= max_w or not cur:
                cur = trial
            else:
                lines.append(cur)
                cur = word
        lines.append(cur)
        if len(lines) <= max_lines and all(probe.textlength(ln, font=f) <= max_w for ln in lines):
            return lines, s
    return [text], 20


def place(frame: np.ndarray, sp: dict, cx: float, cy: float, gain: float = 1.0, glow: float = 0.0) -> None:
    """Blend a sprite into frame (BGR uint8) centred on (cx, cy): glow is added as light, the text is alpha-blended."""
    h, w = sp["pm"].shape[:2]
    x0, y0 = int(cx - w / 2), int(cy - h / 2)
    fx0, fy0, fx1, fy1 = max(x0, 0), max(y0, 0), min(x0 + w, frame.shape[1]), min(y0 + h, frame.shape[0])
    if fx1 <= fx0 or fy1 <= fy0:
        return
    sx0, sy0 = fx0 - x0, fy0 - y0
    sx1, sy1 = sx0 + fx1 - fx0, sy0 + fy1 - fy0
    reg = frame[fy0:fy1, fx0:fx1].astype(np.float32)
    if glow > 0:
        reg += sp["glow"][sy0:sy1, sx0:sx1] * (255.0 * glow * gain)
    reg = reg * (1.0 - sp["a"][sy0:sy1, sx0:sx1] * gain) + sp["pm"][sy0:sy1, sx0:sx1] * (255.0 * gain)
    frame[fy0:fy1, fx0:fx1] = np.clip(reg, 0, 255).astype(np.uint8)


# ---------------------------------------------------------------- the scene

class Scene:
    def __init__(self, data: dict, v: Variant, chorus_lines: list[str], size: tuple[int, int], fps: int,
                 show_lyrics: bool = True, *, text_scale: float = 1.0, title_card: bool = True, pill: bool = True,
                 end_screen: bool = True, instant_first: bool = False, lyric_frac: float = LYRIC_Y,
                 max_lines: int = 2, wrap_frac: float = 0.82):
        """Defaults give the 16:9 lyric video; the vertical Short turns the extras off and doubles the text."""
        self.W, self.H = size
        self.title_card, self.pill_on, self.end_screen = title_card, pill, end_screen
        self.instant_first, self.lyric_frac = instant_first, lyric_frac
        self.sc = self.W / FULL[0]
        self.v, self.fps, self.show_lyrics = v, fps, show_lyrics
        pal = thumbnail.palette_of(data)
        self.pal = pal
        seed = data.get("slug") or data["title"]
        bw, bh = int(self.W * 1.25), int(self.H * 1.25)
        self.canvas = np.asarray(thumbnail.background(pal, seed, bw, bh, shade=False))[..., ::-1].copy()
        self.starts = [ln["start"] for ln in v.lines]

        chorus_texts = {norm(t) for t in chorus_lines}
        self.chorus = [norm(ln["text"]) in chorus_texts for ln in v.lines]
        sc, maxw = self.sc, int(self.W * wrap_frac)
        self.sprites = []
        for ln, is_chorus in zip(v.lines, self.chorus):
            ts = sc * text_scale
            lines, size_px = wrap(ln["text"], int((104 if is_chorus else 76) * ts), maxw, max_lines)
            self.sprites.append(text_sprite(lines, size_px, (255, 255, 255), pal[0] if is_chorus else pal[1],
                                            blur=(18 if is_chorus else 10) * ts, stroke=max(2, int(5 * ts))))

        badge = Image.new("RGBA", (self.W, int(170 * sc)), (0, 0, 0, 0))
        thumbnail.badge(badge, pal[0], scale=self.W / thumbnail.W)
        pm, a = _arrays(badge)
        self.badge = {"pm": pm, "a": a, "glow": pm * 0}

        title_lines, tsize = wrap(data["title"].upper(), int(92 * sc), int(self.W * 0.55))
        self.title = text_sprite(title_lines, tsize, (255, 255, 255), pal[1], blur=14 * sc, align="left", stroke=max(2, int(5 * sc)))
        sub = f"{(data.get('mood_phrase') or '').upper()}  -  OFFICIAL LYRIC VIDEO".strip(" -")
        self.subtitle = text_sprite([sub], int(34 * sc), pal[3], pal[3], blur=4 * sc, align="left", stroke=2)

        self.pill = self._pill(data.get("subscribe_line") or config.SUBSCRIBE_LINE)

        rng = random.Random(seed + "-particles")
        self.dots = [(rng.uniform(0, self.W), rng.uniform(0, self.H), rng.uniform(-8, 8) * sc, rng.uniform(10, 38) * sc,
                      rng.randint(0, 2), rng.randint(0, 2)) for _ in range(70)]
        self.dot_sprites = [[self._dot(r, c) for c in (pal[0], pal[1], pal[3])] for r in (3 * sc, 5 * sc, 8 * sc)]

        self.y0 = int(self.H * 0.57)
        rows = self.H - self.y0
        gx, gy = np.meshgrid(np.arange(self.W, dtype=np.float32), np.arange(rows, dtype=np.float32) + self.y0)
        self.grid_x, self.grid_y = gx, gy
        self.row_amp = (0.25 + 0.75 * np.arange(rows, dtype=np.float32) / rows) * 3.0 * sc
        self.row_phase = np.arange(rows, dtype=np.float32) * 0.09

    def _pill(self, text: str) -> dict:
        sc = self.sc
        f = thumbnail.font(int(36 * sc))
        probe = ImageDraw.Draw(Image.new("L", (1, 1)))
        tw = int(probe.textlength(text, font=f))
        h, w, pad = int(72 * sc), tw + int(120 * sc), 6
        layer = Image.new("RGBA", (w + 2 * pad, h + 2 * pad), (0, 0, 0, 0))
        d = ImageDraw.Draw(layer)
        d.rounded_rectangle([pad, pad, pad + w, pad + h], radius=h // 2, fill=(10, 6, 24, 235), outline=self.pal[0],
                            width=max(2, int(3 * sc)))
        r = int(11 * sc)
        d.ellipse([pad + int(30 * sc), pad + h // 2 - r, pad + int(30 * sc) + 2 * r, pad + h // 2 + r], fill=(235, 40, 60, 255))
        d.text((pad + int(66 * sc), pad + h // 2), text, font=f, fill=(255, 255, 255, 255), anchor="lm")
        pm, a = _arrays(layer)
        return {"pm": pm, "a": a, "glow": pm * 0}

    @staticmethod
    def _dot(radius: float, colour) -> np.ndarray:
        n = int(radius * 4) | 1
        y, x = np.mgrid[:n, :n] - n // 2
        g = np.exp(-(x * x + y * y) / (2 * (radius * 0.7) ** 2))[..., None]
        return (g * np.array(colour[::-1], np.float32)).astype(np.uint8)

    def frame(self, t: float) -> np.ndarray:
        W, H, v = self.W, self.H, self.v
        p = pulse(t, v.beats)
        u = t / max(v.duration, 1.0)
        cw = W * (1.12 - 0.06 * u - 0.012 * p)
        k = W / cw
        cx = self.canvas.shape[1] / 2 + 0.04 * W * math.sin(2 * math.pi * t / 40)
        cy = self.canvas.shape[0] / 2 + 0.025 * H * math.sin(2 * math.pi * t / 53 + 1)
        M = np.array([[k, 0, W / 2 - cx * k], [0, k, H / 2 - cy * k]], np.float32)
        frame = cv2.warpAffine(self.canvas, M, (W, H), flags=cv2.INTER_LINEAR)

        dx = (self.row_amp * np.sin(self.row_phase + 2.2 * t))[:, None]
        frame[self.y0:] = cv2.remap(frame, self.grid_x + dx, self.grid_y, cv2.INTER_LINEAR,
                                    borderMode=cv2.BORDER_REPLICATE)
        frame = cv2.convertScaleAbs(frame, alpha=1.0 + 0.12 * p)

        for x0, y0, vx, vy, si, ci in self.dots:
            d = self.dot_sprites[si][ci]
            n = d.shape[0]
            x, y = int((x0 + vx * t) % (W - n)), int((y0 - vy * t) % (H - n))
            cv2.add(frame[y:y + n, x:x + n], d, dst=frame[y:y + n, x:x + n])

        if self.show_lyrics:
            hit = active_line(t, v.lines, self.starts)
            if hit is None and self.instant_first and self.starts and t < self.starts[0]:
                hit = (0, 1.0)  # the Short opens with its first lyric already on screen
            if hit:
                i, a = hit
                slide = (1 - a) * 14 * self.sc
                gain = 0.55 + 0.9 * p if self.chorus[i] else 0.5
                place(frame, self.sprites[i], W / 2, (lyric_y(t, v.duration) if self.end_screen else self.lyric_frac) * H + slide, gain=a, glow=gain)

        place(frame, self.badge, W / 2, self.badge["pm"].shape[0] / 2)

        ca = card_alpha(t) if self.title_card else 0.0
        if ca > 0:
            x = 100 * self.sc
            place(frame, self.title, x + self.title["w"] / 2, H * 0.22, gain=ca, glow=0.6)
            place(frame, self.subtitle, x + self.subtitle["w"] / 2, H * 0.22 + self.title["h"] / 2 + 28 * self.sc, gain=ca, glow=0.4)

        pa, slide = pill_state(t, v.chorus_end, v.duration) if self.pill_on else (0.0, 0.0)
        if pa > 0:
            place(frame, self.pill, W / 2, H * 0.9 + slide * 30 * self.sc, gain=pa)
        return frame


# ---------------------------------------------------------------- encode

def encode(scene: Scene, out: Path, seconds: float | None, draft: bool, log=print) -> None:
    v, W, H, fps = scene.v, scene.W, scene.H, scene.fps
    total = min(v.duration, seconds) if seconds else v.duration
    cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "bgr24",
           "-s", f"{W}x{H}", "-r", str(fps), "-i", "-"]
    if v.audio:
        cmd += ["-i", str(v.audio), "-map", "0:v", "-map", "1:a", "-c:a", "aac", "-b:a", "256k"]
    cmd += ["-t", f"{total:.3f}", "-c:v", "libx264", "-preset", "ultrafast" if draft else "medium",
            "-crf", "28" if draft else "18", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(out)]
    n = int(total * fps)
    with tempfile.TemporaryFile() as err:
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=err)
        try:
            for i in range(n):
                proc.stdin.write(scene.frame(i / fps).tobytes())
                if n >= 300 and i % (n // 10) == 0:
                    log(f"      {100 * i // n}%")
            proc.stdin.close()
            code = proc.wait()
        except BrokenPipeError:
            code = proc.wait()
        if code:
            err.seek(0)
            raise RuntimeError(f"ffmpeg failed:\n{err.read().decode(errors='replace')[-1500:]}")


def render(folder: Path, option: str, seconds: float | None = None, draft: bool = False, show_lyrics: bool = True,
           name: str | None = None, audio: Path | None = None, log=print) -> Path:
    """Render one 16:9 video. `audio` replaces the soundtrack (the instrumental version)."""
    data = songjson.load(folder / "song.json")
    suno_file = folder / "suno.txt"
    chorus_lines = [ln for sec in parse_suno(suno_file.read_text(encoding="utf-8")).sections if sec.kind == "chorus"
                    for ln in sec.lines] if suno_file.exists() else []
    v = variant(folder, data, option)
    if audio:
        v = replace(v, audio=audio)
    scene = Scene(data, v, chorus_lines, DRAFT if draft else FULL, 15 if draft else FPS, show_lyrics)
    out = folder / "out" / (name or f"lyric_{option}.mp4")
    out.parent.mkdir(parents=True, exist_ok=True)
    songjson.move_aside(out)  # large file: moved aside instead of copied
    log(f"  {option}: {scene.W}x{scene.H} @{scene.fps}fps, {min(v.duration, seconds or v.duration):.1f}s -> {out.name}")
    encode(scene, out, seconds, draft, log)
    return out
