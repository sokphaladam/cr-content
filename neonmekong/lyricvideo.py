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
import sys
import tempfile
import time
from dataclasses import dataclass, replace
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from . import analyze, config, hook, mood, overlays, pictures, songjson, thumbnail
from .suno import parse as parse_suno

FULL = (1920, 1080)
DRAFT = (960, 540)
FPS = 30
TITLE_CARD = (0.4, 5.6)   # seconds on screen (max 6)
PILL_LEN = 4.0
END_ZONE = 20.0
PULSE_DECAY = 0.18
SCRIM = 0.26   # how much the band behind the lyric darkens the picture at its middle
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
    cut: float = 0.0                          # song seconds at this video's 0 (the trim and the Short start later)
    preview: tuple[float, float, float] | None = None   # chorus preview first: (its length, where it starts, the offset)
    skip: float = 0.0                         # preview: song seconds left out before the song part (the long intro)

    def song_time(self, t: float) -> float:
        """Seconds into the song that this video's second `t` shows (the pictures are planned on the song)."""
        if self.preview:
            length, p0, off = self.preview
            return t + p0 if t < length else t - off + self.skip
        return t + self.cut


def variant(folder: Path, data: dict, option: str) -> Variant:
    """The song on the video's own timeline: option is full (no hook edit), trim or preview."""
    mix, _ = analyze.find_audio(folder)
    beats, dur = list(data["beat_times"]), float(data["duration"])
    ce = (data.get("chorus") or {}).get("end")
    lines = analyze.parse_lrc((folder / "lyrics.lrc").read_text(encoding="utf-8"))
    audio, extra = mix, {}
    if option != "full":
        hdir = folder / "out" / "hook"
        spec = json.loads((hdir / "hook.json").read_text(encoding="utf-8"))[option]
        lines = analyze.parse_lrc((hdir / f"lyrics_{option}.lrc").read_text(encoding="utf-8"))
        audio, dur = hdir / f"audio_{option}.wav", float(spec["duration"])
        if option == "trim":
            cut = spec["audio_start"]
            extra = {"cut": cut}
            beats, ce = [b - cut for b in beats if b >= cut], None if ce is None else ce - cut
        else:
            p0, off, skip = spec["src_start"], spec["song_offset"], spec.get("song_start", 0.0)
            extra = {"preview": (spec["length"], p0, off), "skip": skip}
            beats = [b - p0 for b in beats if p0 <= b < p0 + spec["length"]] + [b + off - skip for b in beats if b >= skip]
            ce = None if ce is None else ce + off - skip
    if audio is not None and not audio.exists():
        if not config.dry_run():
            raise FileNotFoundError(f"missing {audio} (run the hook step first)" if option != "full"
                                    else f"no audio.wav / audio.mp3 in {folder}")
        audio = None
    return Variant(option, audio, lines, beats, ce, dur, **extra)


# ---------------------------------------------------------------- pure timing helpers

def crisp(img: np.ndarray, amount: float = 0.45, radius: float = 1.2) -> np.ndarray:
    """Unsharp mask for artwork that was scaled up to the canvas (BGR uint8): takes the softness off the linework."""
    soft = cv2.GaussianBlur(img, (0, 0), radius)
    return cv2.addWeighted(img, 1.0 + amount, soft, -amount, 0)


def ease(x: float) -> float:
    x = min(max(x, 0.0), 1.0)
    return x * x * (3 - 2 * x)


def pulse(t: float, beats: list[float]) -> float:
    """1.0 on a beat, decaying to 0."""
    i = bisect.bisect_right(beats, t) - 1
    return math.exp(-(t - beats[i]) / PULSE_DECAY) if i >= 0 else 0.0


def lyric_y(t: float, dur: float, base: float = LYRIC_Y) -> float:
    """Lyric centre (fraction of height): moves up for the end screen over 0.8s at dur - 20s."""
    return base + (END_LYRIC_Y - base) * ease((t - (dur - END_ZONE)) / 0.8)


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


def text_sprite(lines: list[str], size: int, fill, glow, blur: float, align: str = "center", stroke: int = 4,
                maker=None, shadow: float = 0.0) -> dict:
    """`maker` makes the font (default the headline face); `shadow` > 0 puts a soft dark drop shadow of that blur
    under the text (the lyrics: a thin edge and a shadow read cleaner than a thick outline)."""
    f = (maker or thumbnail.font)(size)
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
    if shadow > 0:
        dark = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        dark.putalpha(text.getchannel("A").filter(ImageFilter.GaussianBlur(shadow)).point(lambda v: min(255, int(v * 1.6))))
        dark = ImageChops_offset(dark, 0, max(2, int(shadow * 0.9)))
        text = Image.alpha_composite(dark, text)
    pm_t, a_t = _arrays(text)
    pm_g, _ = _arrays(halo)
    rows = []   # each text row's (top, bottom, left, right) in the sprite: the karaoke fill runs along them
    for i, ln in enumerate(lines):
        lw = int(probe.textlength(ln, font=f)) + 2 * stroke
        x0 = int((w - lw) / 2) if align == "center" else pad - stroke
        rows.append((pad + i * lead, min(pad + (i + 1) * lead, h), max(x0, 0), min(x0 + lw, w)))
    return {"pm": pm_t, "a": a_t, "glow": pm_g, "w": w, "h": h, "rows": rows}


def ImageChops_offset(im: Image.Image, dx: int, dy: int) -> Image.Image:
    out = Image.new("RGBA", im.size, (0, 0, 0, 0))
    out.paste(im, (dx, dy))
    return out


def wrap(text: str, size: int, max_w: int, max_lines: int = 2, maker=None) -> tuple[list[str], int]:
    """Wrap to <= max_lines lines; shrink the font if that is not enough."""
    probe = ImageDraw.Draw(Image.new("L", (1, 1)))
    for s in range(size, 20, -4):
        f, lines, cur = (maker or thumbnail.font)(s), [], ""
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

LOOP = "loop.mp4"   # crcontent/coverloop.py: the song's animated cover


class Loop:
    """The frames of a looping clip, cover-cropped to w x h, at any video second (wrapping round). Read one at a time
    (a whole loop at 1.25x 1080p would be ~2 GB): rendering asks in order, so it seeks only when the time jumps."""

    def __init__(self, file: Path, w: int, h: int):
        self.cap = cv2.VideoCapture(str(file))
        self.count = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.fps = self.cap.get(cv2.CAP_PROP_FPS) or FPS
        if self.count <= 0:
            raise ValueError(f"{file.name} has no frames")
        self.w, self.h, self.pos, self.last = w, h, -1, None

    def at(self, t: float) -> np.ndarray:
        i = int(t * self.fps) % self.count
        if i == self.pos and self.last is not None:
            return self.last
        if i != self.pos + 1:
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, i)
        ok, img = self.cap.read()
        if not ok:   # a short last frame or a bad seek: start the loop again rather than fail the render
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            ok, img = self.cap.read()
            i = 0
        k = max(self.w / img.shape[1], self.h / img.shape[0])
        img = cv2.resize(img, (max(self.w, round(img.shape[1] * k)), max(self.h, round(img.shape[0] * k))),
                         interpolation=cv2.INTER_CUBIC)
        y, x = (img.shape[0] - self.h) // 2, (img.shape[1] - self.w) // 2
        self.pos, self.last = i, np.ascontiguousarray(img[y:y + self.h, x:x + self.w])
        return self.last


class Scene:
    def __init__(self, data: dict, v: Variant, chorus_lines: list[str], size: tuple[int, int], fps: int,
                 show_lyrics: bool = True, *, text_scale: float = 1.0, title_card: bool = True, pill: bool = True,
                 end_screen: bool = True, instant_first: bool = False, lyric_frac: float = LYRIC_Y,
                 max_lines: int = 2, wrap_frac: float = 0.82):
        """Defaults give the 16:9 lyric video; the vertical Short turns the extras off and doubles the text."""
        self.W, self.H = size
        self.title_card, self.pill_on, self.end_screen = title_card, pill, end_screen
        self.instant_first = instant_first
        self.sc = self.W / FULL[0]
        self.style = mood.pick(data.get("lyric_style"), mood.LYRIC_STYLES, mood.DEFAULT_STYLE)
        self.grader = mood.Grader(data.get("mood_grade"), size)
        if self.style == "minimal":   # smaller type, no big glow, the lower third
            text_scale *= 0.78
            if lyric_frac == LYRIC_Y:
                lyric_frac = 0.8
        self.lyric_frac = lyric_frac
        self.v, self.fps, self.show_lyrics = v, fps, show_lyrics
        pal = thumbnail.palette_of(data)
        self.pal = pal
        seed = data.get("slug") or data["title"]
        bw, bh = int(self.W * 1.25), int(self.H * 1.25)
        own = thumbnail.custom_background(data, bw, bh)  # the song's own picture: no drawn river to shimmer
        self.own_background = own is not None
        self.canvas = crisp(np.asarray(own or thumbnail.background(pal, seed, bw, bh, shade=False))[..., ::-1].copy())
        loop = thumbnail.active_loop(Path(data["_dir"])) if data.get("_dir") else None
        self.loop = Loop(loop, bw, bh) if loop else None   # the animated cover, over its own still
        self.starts = [ln["start"] for ln in v.lines]
        # one picture per sung section (pictures.py), dissolving into each other; the cover / drawn city between
        folder = data.get("_dir")
        self.pics = []
        plan = pictures.load(Path(folder)) if folder else {}
        self.cover_move = plan.get("cover_motion") if plan.get("cover_motion") in pictures.MOTIONS else ""
        if folder:
            for a, b, file, move in pictures.spans(Path(folder), float(data.get("duration") or v.duration)):
                with Image.open(file) as im:
                    self.pics.append((a, b, crisp(np.asarray(thumbnail.cover_crop(im, bw, bh))[..., ::-1].copy()), move))
        self.on_picture = False
        # the beat effect: how much, on which parts, and when (mood.pulse_settings)
        self.pulse_light, self.pulse_zoom, self.pulse_parts, self.pulse_when = mood.pulse_settings(data)
        self.chorus_spans = [(float(s["start"]), float(s["end"])) for s in (data.get("sections") or [])
                             if s.get("kind") == "chorus" and "start" in s and "end" in s]
        # the neon title and the now-playing card (overlays.py), when the song asks for them
        span = overlays.intro_span(v.lines[0]["start"] if v.lines else None) if data.get("neon_intro") else None
        self.neon = overlays.NeonTitle(sys.modules[__name__], data["title"], span, pal, size) if span else None
        self.playing = overlays.NowPlaying(sys.modules[__name__], data["title"], pal, size, v.duration) \
            if data.get("now_playing") else None

        chorus_texts = {norm(t) for t in chorus_lines}
        self.chorus = [norm(ln["text"]) in chorus_texts for ln in v.lines]
        sc, maxw = self.sc, int(self.W * wrap_frac)
        self.sprites = []
        for ln, is_chorus in zip(v.lines, self.chorus):
            ts = sc * text_scale
            lines, size_px = wrap(ln["text"], int((88 if is_chorus else 66) * ts), maxw, max_lines, thumbnail.lyric_font)
            self.sprites.append(text_sprite(lines, size_px, (255, 255, 255), pal[0] if is_chorus else pal[1],
                                            blur=(16 if is_chorus else 8) * ts, stroke=max(1, int(2 * ts)),
                                            maker=thumbnail.lyric_font, shadow=7 * ts))

        # the line after the current one, small and faint underneath (the Short opens on its lyric: no room for it)
        self.next_on = not instant_first and self.style != "minimal"
        self.next_sprites = []
        if self.next_on:
            for ln in v.lines:
                lines, size_px = wrap(ln["text"], int(38 * sc * text_scale), maxw, 1, thumbnail.lyric_font)
                self.next_sprites.append(text_sprite(lines, size_px, (255, 255, 255), pal[1], blur=2 * sc, stroke=0,
                                                     maker=thumbnail.lyric_font, shadow=4 * sc))

        bk = 1.0 if self.W >= self.H else 1.3   # the Short's badge is bigger, and its sprite taller to hold it
        badge = Image.new("RGBA", (self.W, int(170 * sc * bk)), (0, 0, 0, 0))
        thumbnail.badge(badge, pal[0], scale=self.W / thumbnail.W * bk)
        pm, a = _arrays(badge)
        self.badge = {"pm": pm, "a": a, "glow": pm * 0}

        title_lines, tsize = wrap(overlays.neon_name(data["title"]).upper(), int(84 * sc), int(self.W * 0.55))
        self.title = text_sprite(title_lines, tsize, (255, 255, 255), pal[1], blur=10 * sc, align="left",
                                 stroke=max(2, int(3 * sc)))
        sub = (data.get("mood_phrase") or "").upper()
        self.subtitle = text_sprite([sub], int(32 * sc), pal[3], pal[3], blur=3 * sc, align="left", stroke=1) if sub else None

        self.pill = self._pill(data.get("subscribe_line") or config.SUBSCRIBE_LINE)

        rng = random.Random(seed + "-particles")
        self.dots = [(rng.uniform(0, self.W), rng.uniform(0, self.H), rng.uniform(-8, 8) * sc, rng.uniform(10, 38) * sc,
                      rng.randint(0, 2), rng.randint(0, 2)) for _ in range(70)]
        self.dot_sprites = [[self._dot(r, c) for c in (pal[0], pal[1], pal[3])] for r in (3 * sc, 5 * sc, 8 * sc)]

        nrng = np.random.default_rng(7)
        self.dither = [nrng.integers(0, 3, (self.H, self.W, 1), dtype=np.uint8).repeat(3, 2) for _ in range(4)]
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

    def _view(self, img: np.ndarray, move: str, prog: float, t: float, push: float) -> np.ndarray:
        """`img` (the oversized canvas) seen through the camera: `move` at progress `prog` (0..1) of its section, with
        the beat's small push-in `push` (a fraction). "" is the slow drift over the whole song."""
        W, H = self.W, self.H
        bh, bw = img.shape[:2]
        e = ease(prog)
        cx, cy = bw / 2, bh / 2
        if move == "":
            cw = W * (1.12 - 0.06 * t / max(self.v.duration, 1.0))
            cx += 0.04 * W * math.sin(2 * math.pi * t / 40)
            cy += 0.025 * H * math.sin(2 * math.pi * t / 53 + 1)
        elif move == "push_in":
            cw = W * (1.22 - 0.12 * e)
        elif move == "pull_out":
            cw = W * (1.10 + 0.12 * e)
        elif move == "breathe":
            cw = W * (1.14 + 0.03 * math.sin(2 * math.pi * t / 16))
            cx += 0.02 * W * math.sin(2 * math.pi * t / 31)
            cy += 0.015 * H * math.sin(2 * math.pi * t / 23 + 1)
        else:
            cw = W * 1.12 if move != "still" else W * 1.14
            if move in ("pan_left", "pan_right"):
                cx += (bw - cw) / 2 * 0.9 * (1 - 2 * e) * (1 if move == "pan_left" else -1)
            elif move in ("tilt_up", "tilt_down"):
                cy += (bh - cw * H / W) / 2 * 0.9 * (1 - 2 * e) * (1 if move == "tilt_up" else -1)
        cw *= 1.0 - push
        ch = cw * H / W
        cx, cy = min(max(cx, cw / 2), bw - cw / 2), min(max(cy, ch / 2), bh - ch / 2)   # never past the picture's edge
        k = W / cw
        M = np.array([[k, 0, W / 2 - cx * k], [0, k, H / 2 - cy * k]], np.float32)
        return cv2.warpAffine(img, M, (W, H), flags=cv2.INTER_CUBIC)

    def _background(self, t: float, push: float) -> np.ndarray:
        """The picture behind the lyrics at video second `t`: the section's picture with its own camera move,
        dissolving in from the one before (at the end of its move, so nothing jumps), or the cover / drawn city."""
        self.on_picture = False
        if self.pics:
            st = self.v.song_time(t)
            for k, (a, b, pic, move) in enumerate(self.pics):
                if a <= st < b:
                    self.on_picture = True
                    here = self._view(pic, move, (st - a) / max(b - a, 1.0), t, push)
                    u = ease((st - a) / pictures.FADE)
                    if u >= 1.0:
                        return here
                    if k and abs(self.pics[k - 1][1] - a) < 0.01:
                        before = self._view(self.pics[k - 1][2], self.pics[k - 1][3], 1.0, t, push)
                    else:
                        before = self._view(self._cover(t), self.cover_move, t / max(self.v.duration, 1.0), t, push)
                    return cv2.addWeighted(before, 1.0 - u, here, u, 0)
        return self._view(self._cover(t), self.cover_move, t / max(self.v.duration, 1.0), t, push)

    def _cover(self, t: float) -> np.ndarray:
        return self.loop.at(t) if self.loop else self.canvas

    def _beat(self, t: float) -> tuple[float, float, float, float]:
        """(brightness, zoom push, lyric glow, grade pulse) for this moment: the beat's pulse, scaled by the song's
        beat-effect level and cut down to the parts it is meant for (and to the choruses, when set so)."""
        p = pulse(t, self.v.beats)
        if self.pulse_when == "chorus":
            st = self.v.song_time(t)
            p = p if any(a <= st < b for a, b in self.chorus_spans) else 0.0
        return (self.pulse_light * p if "light" in self.pulse_parts else 0.0,
                self.pulse_zoom * p if "zoom" in self.pulse_parts else 0.0,
                p if "glow" in self.pulse_parts else 0.0,
                p if "light" in self.pulse_parts else 0.0)

    def _scrim(self, frame: np.ndarray, cy: float, a: float) -> None:
        """Darken a soft horizontal band centred on the lyric (rows only, so it is cheap)."""
        H = self.H
        half = int(H * 0.2)
        y0, y1 = max(int(cy) - half, 0), min(int(cy) + half, H)
        if y1 <= y0:
            return
        rows = np.arange(y0, y1, dtype=np.float32)
        k = 1.0 - SCRIM * a * np.exp(-((rows - cy) / (H * 0.09)) ** 2)
        reg = frame[y0:y1].astype(np.float32) * k[:, None, None]
        frame[y0:y1] = reg.astype(np.uint8)

    def _karaoke(self, frame: np.ndarray, i: int, t: float, a: float, glow: float, cy: float) -> None:
        """The line dim, then lit row by row from the left as it is sung (the line's own start and end)."""
        sp = self.sprites[i]
        place(frame, sp, self.W / 2, cy, gain=a * 0.5)
        ln = self.v.lines[i]
        left, top = self.W / 2 - sp["w"] / 2, cy - sp["h"] / 2
        for part, x0, y0 in mood.cut(sp, sp["rows"], mood.fill_fraction(t, ln["start"], ln["end"])):
            place(frame, part, left + x0 + part["w"] / 2, top + y0 + part["h"] / 2, gain=a, glow=glow)

    def frame(self, t: float) -> np.ndarray:
        W, H, v = self.W, self.H, self.v
        light, push, glow, grade = self._beat(t)
        frame = self._background(t, push)

        dx = (self.row_amp * np.sin(self.row_phase + 2.2 * t))[:, None]
        if not self.own_background and not self.on_picture:
            frame[self.y0:] = cv2.remap(frame, self.grid_x + dx, self.grid_y, cv2.INTER_LINEAR,
                                        borderMode=cv2.BORDER_REPLICATE)
        frame = cv2.convertScaleAbs(frame, alpha=1.0 + light)
        frame = self.grader.grade(frame, t, grade)

        for x0, y0, vx, vy, si, ci in self.dots:
            d = self.dot_sprites[si][ci]
            n = d.shape[0]
            x, y = int((x0 + vx * t) % (W - n)), int((y0 - vy * t) % (H - n))
            cv2.add(frame[y:y + n, x:x + n], d, dst=frame[y:y + n, x:x + n])

        if self.show_lyrics:
            hit = active_line(t, v.lines, self.starts)
            if hit:   # a soft dark band behind the words, so they read on any picture
                self._scrim(frame, (lyric_y(t, v.duration, self.lyric_frac) if self.end_screen else self.lyric_frac) * H,
                            hit[1])
            if hit is None and self.instant_first and self.starts and t < self.starts[0]:
                hit = (0, 1.0)  # the Short opens with its first lyric already on screen
            if hit:
                i, a = hit
                slide = (1 - a) * 14 * self.sc
                gain = 0.55 + 0.9 * glow if self.chorus[i] else 0.5
                if self.style == "minimal":
                    gain *= 0.3
                cy = (lyric_y(t, v.duration, self.lyric_frac) if self.end_screen else self.lyric_frac) * H + slide
                sp = self.sprites[i]
                if self.style == "kinetic":
                    sp = mood.scaled(sp, mood.pop_scale(t, self.starts[i], glow, self.chorus[i]))
                if self.style == "karaoke":
                    self._karaoke(frame, i, t, a, gain, cy)
                else:
                    place(frame, sp, W / 2, cy, gain=a, glow=gain)
                if self.next_on and i + 1 < len(self.next_sprites):
                    nx = self.next_sprites[i + 1]
                    place(frame, nx, W / 2, cy + self.sprites[i]["h"] / 2 + nx["h"] / 2 + 6 * self.sc, gain=a * 0.62)

        place(frame, self.badge, W / 2, self.badge["pm"].shape[0] / 2)

        if self.neon:
            self.neon.draw(frame, t)
        if self.playing:
            self.playing.draw(frame, t, ease((t - 0.3) / 0.6))

        # the title card sits under the badge; the now-playing card already says the title, so one or the other
        ca = card_alpha(t) if self.title_card and not self.neon and not self.playing else 0.0
        if ca > 0:
            x, top = 70 * self.sc, 190 * self.sc   # the badge's left edge, just below it
            place(frame, self.title, x + self.title["w"] / 2, top + self.title["h"] / 2, gain=ca, glow=0.5)
            if self.subtitle:
                place(frame, self.subtitle, x + self.subtitle["w"] / 2,
                      top + self.title["h"] + self.subtitle["h"] / 2 + 6 * self.sc, gain=ca * 0.9, glow=0.3)

        pa, slide = pill_state(t, v.chorus_end, v.duration) if self.pill_on else (0.0, 0.0)
        if pa > 0:
            place(frame, self.pill, W / 2, H * 0.9 + slide * 30 * self.sc, gain=pa)
        return cv2.add(frame, self.dither[int(t * self.fps) % 4])


# ---------------------------------------------------------------- one picture's camera move, as a short clip

MOVE_CLIP = 4.0   # seconds a section's whole move is squeezed into for the preview


def move_clip(folder: Path, pid: str, out: Path, seconds: float = MOVE_CLIP, move: str | None = None) -> Path:
    """A short silent clip of slot `pid`'s picture going through its camera move from start to end (the move is
    sped up to `seconds`), as it will look behind the lyrics. `move` tries one that is not saved yet."""
    scene = build_scene(folder, "full", draft=True, show_lyrics=False)
    if pid == "cover":   # the background the pictures dissolve from, moving over the whole song
        a, saved, img = 0.0, scene.cover_move, scene.canvas
    else:
        slot = next((x for x in pictures.load(folder)["slots"] if x["id"] == pid), None)
        if not slot or not slot.get("file"):
            raise ValueError("this section has no picture yet")
        pic = next(((a, m, img) for a, b, img, m in scene.pics if abs(a - float(slot["start"])) < 0.01), None)
        if pic is None:
            raise ValueError("this section's picture could not be found")
        a, saved, img = pic
    move = saved if move is None else move
    n, fps = int(seconds * scene.fps), scene.fps
    cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "bgr24",
           "-s", f"{scene.W}x{scene.H}", "-r", str(fps), "-i", "-", "-c:v", "libx264", "-preset", "veryfast",
           "-crf", "22", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(out)]
    out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryFile() as err:
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=err)
        try:
            for i in range(n):
                prog = i / max(n - 1, 1)
                proc.stdin.write(scene._view(img, move, prog, a + prog * 30, 0.0).tobytes())
            proc.stdin.close()
        except BrokenPipeError:
            pass
        if proc.wait():
            err.seek(0)
            raise RuntimeError("ffmpeg failed: " + err.read().decode(errors="replace")[-1500:])
    return out


# ---------------------------------------------------------------- encode

def encode(scene: Scene, out: Path, seconds: float | None, draft: bool, log=print) -> None:
    v, W, H, fps = scene.v, scene.W, scene.H, scene.fps
    total = min(v.duration, seconds) if seconds else v.duration
    cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "bgr24",
           "-s", f"{W}x{H}", "-r", str(fps), "-i", "-"]
    if v.audio:
        cmd += ["-i", str(v.audio), "-map", "0:v", "-map", "1:a", "-c:a", "aac", "-b:a", "256k"]
    # BGR frames -> BT.709 YUV (ffmpeg's default would be BT.601 and shift the colours), tagged so players agree
    cmd += ["-t", f"{total:.3f}", "-vf", "scale=out_color_matrix=bt709:out_range=tv,format=yuv420p",
            "-c:v", "libx264", "-preset", "ultrafast" if draft else "medium", "-crf", "24" if draft else "16",
            "-tune", "fastdecode" if draft else "animation", "-profile:v", "high", "-g", str(fps * 2),
            "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709", "-color_range", "tv",
            "-movflags", "+faststart", str(out)]
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


def build_scene(folder: Path, option: str, draft: bool = False, show_lyrics: bool = True, audio: Path | None = None,
                over: dict | None = None) -> Scene:
    """The scene for one video of the song; `over` replaces song.json's values (the web page's style preview)."""
    data = {**songjson.load(folder / "song.json"), **(over or {})}
    suno_file = folder / "suno.txt"
    chorus_lines = [ln for sec in parse_suno(suno_file.read_text(encoding="utf-8")).sections if sec.kind == "chorus"
                    for ln in sec.lines] if suno_file.exists() else []
    v = variant(folder, data, option)
    if audio:
        v = replace(v, audio=audio)
    return Scene(data, v, chorus_lines, DRAFT if draft else FULL, 15 if draft else FPS, show_lyrics)


def render(folder: Path, option: str, seconds: float | None = None, draft: bool = False, show_lyrics: bool = True,
           name: str | None = None, audio: Path | None = None, log=print) -> Path:
    """Render one 16:9 video. `audio` replaces the soundtrack (the instrumental version)."""
    scene = build_scene(folder, option, draft, show_lyrics, audio)
    v = scene.v
    out = folder / "out" / (name or f"lyric_{option}.mp4")
    out.parent.mkdir(parents=True, exist_ok=True)
    songjson.move_aside(out)  # large file: moved aside instead of copied
    log(f"  {option}: {scene.W}x{scene.H} @{scene.fps}fps, {min(v.duration, seconds or v.duration):.1f}s -> {out.name}")
    encode(scene, out, seconds, draft, log)
    return out
