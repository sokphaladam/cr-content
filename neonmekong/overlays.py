"""Two overlays for the lyric video, switched on per song in song.json ("neon_intro", "now_playing"):

- NeonTitle   the song's name flickers on in neon like a sign switching on, over the first seconds, and fades before
              the singing starts (the video still starts with the song). Skipped when the singing starts at once
              (the trimmed video and the chorus preview), since the title would sit on the lyrics.
- NowPlaying  a dark card in the top-left corner with the song's title, a progress bar and a spinning vinyl record, like
              playlist channels.
"""
import math
import re

import cv2
import numpy as np
from PIL import Image, ImageDraw

from . import thumbnail

INTRO = (0.6, 5.5)   # when the neon title flickers on, and the latest it fades (like pipeline.TITLE_INTRO)
MIN_SHOWN = 2.6      # shorter than this and it is not worth showing
SOON = 1.5           # singing before this second: no neon title


def neon_name(title: str) -> str:
    """The song's name from a post title: "Signal Lost - Song About ... (Official Lyric Video)" -> "Signal Lost"."""
    name = re.split(r"\s[-–—|:]\s|\s*[(\[]", title, maxsplit=1)[0].strip()
    return name or title.strip()


def intro_span(first_line: float | None) -> tuple[float, float] | None:
    """(on, off) seconds of the neon title for a video whose first sung line is at `first_line`, or None when there is
    no room: it must be gone 0.3 s before the singing and be shown for at least MIN_SHOWN - 0.6 seconds."""
    first = INTRO[1] + 0.3 if first_line is None else first_line
    if first < SOON:
        return None
    end = min(INTRO[1], first - 0.3)
    return (INTRO[0], end) if end - INTRO[0] >= MIN_SHOWN - 0.6 else None


# a sign catching: short bursts of light, then it holds (with the odd tiny dip, like a tube that hums)
BURSTS = [(0.00, 0.10, 0.55), (0.22, 0.30, 0.7), (0.46, 0.52, 0.5), (0.70, 1.15, 0.9), (1.30, 1.38, 0.8)]


def neon_gain(t: float, on: float, off: float) -> float:
    """0..1.1 brightness of the sign at `t`: dark tube, flicker, steady, and a fade out over the last 0.7 s."""
    u = t - on
    if u < 0 or t >= off:
        return 0.0
    out = min((off - t) / 0.7, 1.0)
    if u < 1.45:
        lit = next((g for a, b, g in BURSTS if a <= u < b), 0.0)
        return max(lit, 0.10) * out   # a switched-off tube still shows faintly
    dip = 0.78 if int(u * 17) % 41 == 0 else 1.0
    return (1.0 + 0.04 * math.sin(u * 52)) * dip * out


class NeonTitle:
    def __init__(self, lv, title: str, span: tuple[float, float], pal: list, size: tuple[int, int]):
        self.lv, self.span = lv, span
        W, H = size
        sc = W / lv.FULL[0] if W >= H else W / 1080 * 1.1
        lines, px = lv.wrap(neon_name(title).upper(), int(168 * sc), int(W * 0.84), 2)
        neon = pal[0]
        core = tuple(int(c + (255 - c) * 0.5) for c in neon)   # the tube's hot centre
        self.sprite = lv.text_sprite(lines, px, core, neon, blur=34 * sc, stroke=max(2, int(3 * sc)))
        self.cx, self.cy = W / 2, H * 0.4

    def draw(self, frame: np.ndarray, t: float) -> None:
        g = neon_gain(t, *self.span)
        if g > 0:
            self.lv.place(frame, self.sprite, self.cx, self.cy, gain=min(g, 1.0), glow=max(g - 0.06, 0.0) * 1.7)


class NowPlaying:
    def __init__(self, lv, title: str, pal: list, size: tuple[int, int], duration: float):
        self.lv, self.duration = lv, duration
        W, H = size
        s = W / lv.FULL[0] if W >= H else W / 1080 * 1.15
        self.s = s
        self.accent = tuple(int(c) for c in pal[0][::-1])   # BGR for cv2
        self.w, self.h = int(560 * s), int(150 * s)
        self.x, self.y = int(54 * s), int(196 * s) if W >= H else int(190 * s)
        pad = int(18 * s)
        self.d = self.h - 2 * pad   # the record's diameter
        card = Image.new("RGBA", (self.w, self.h), (0, 0, 0, 0))
        dr = ImageDraw.Draw(card)
        dr.rounded_rectangle([0, 0, self.w - 1, self.h - 1], radius=int(22 * s), fill=(12, 8, 26, 222),
                             outline=(*pal[0], 255), width=max(2, int(2 * s)))
        probe = ImageDraw.Draw(Image.new("L", (1, 1)))
        tx = pad + self.d + int(22 * s)
        label_f, title_f = thumbnail.font(int(24 * s)), thumbnail.font(int(40 * s))
        dr.text((tx, int(pad + 6 * s)), "NOW PLAYING", font=label_f, fill=(*pal[3], 255))
        name, room = neon_name(title), self.w - tx - pad
        while probe.textlength(name, font=title_f) > room and len(name) > 4:
            name = name[:-2].rstrip() + "…" if not name.endswith("…") else name[:-2] + "…"
        dr.text((tx, int(pad + 40 * s)), name, font=title_f, fill=(255, 255, 255, 255))
        pm, a = lv._arrays(card)
        self.card = {"pm": pm, "a": a, "glow": pm * 0, "w": self.w, "h": self.h}
        self.bar = (tx, self.h - pad - int(14 * s), self.w - pad, self.h - pad - int(14 * s))   # card-relative
        self.vinyl_rgba = self._vinyl(pal[0])
        self.tx = tx

    def _vinyl(self, accent) -> np.ndarray:
        """The record at 4x, then reduced: grooves, a coloured label with a hole, and two bright glints (so the
        spin can be seen)."""
        n = self.d * 4
        im = Image.new("RGBA", (n, n), (0, 0, 0, 0))
        dr = ImageDraw.Draw(im)
        dr.ellipse([0, 0, n - 1, n - 1], fill=(14, 14, 20, 255), outline=(60, 60, 72, 255), width=n // 60)
        for k in range(8, 20):
            r = n / 2 * k / 20
            dr.ellipse([n / 2 - r, n / 2 - r, n / 2 + r, n / 2 + r], outline=(34, 34, 44, 255), width=max(1, n // 200))
        glint = Image.new("RGBA", (n, n), (0, 0, 0, 0))
        gd = ImageDraw.Draw(glint)
        for start in (200, 20):
            gd.pieslice([n * 0.04, n * 0.04, n * 0.96, n * 0.96], start, start + 28, fill=(255, 255, 255, 70))
        im = Image.alpha_composite(im, glint)
        dr = ImageDraw.Draw(im)
        lr = n * 0.17
        dr.ellipse([n / 2 - lr, n / 2 - lr, n / 2 + lr, n / 2 + lr], fill=(*accent, 255))
        dr.ellipse([n / 2 - n * 0.022, n / 2 - n * 0.022, n / 2 + n * 0.022, n / 2 + n * 0.022], fill=(12, 8, 26, 255))
        return np.asarray(im.resize((self.d, self.d), Image.LANCZOS), np.float32) / 255.0

    def draw(self, frame: np.ndarray, t: float, alpha: float = 1.0) -> None:
        lv = self.lv
        cx, cy = self.x + self.w / 2, self.y + self.h / 2
        lv.place(frame, self.card, cx, cy, gain=alpha)
        # the record: turned by `t`, premultiplied the way sprites are
        deg = (t * 120.0) % 360.0
        M = cv2.getRotationMatrix2D((self.d / 2, self.d / 2), -deg, 1.0)
        rot = cv2.warpAffine(self.vinyl_rgba, M, (self.d, self.d), flags=cv2.INTER_LINEAR, borderValue=(0, 0, 0, 0))
        a = rot[..., 3:4]
        sprite = {"pm": rot[..., 2::-1] * a, "a": a, "glow": rot[..., :3] * 0, "w": self.d, "h": self.d}
        pad = (self.h - self.d) / 2
        lv.place(frame, sprite, self.x + pad + self.d / 2, cy, gain=alpha)
        # the progress bar: a track and the part played, with a dot
        x0, y0, x1, _ = self.bar
        x0, x1, y = self.x + x0, self.x + x1, self.y + y0
        th = max(3, int(7 * self.s))
        part = min(max(t / max(self.duration, 1.0), 0.0), 1.0)
        over = frame.copy() if alpha < 1.0 else None
        cv2.line(frame, (x0, y), (x1, y), (70, 56, 96), th, cv2.LINE_AA)
        xe = int(x0 + (x1 - x0) * part)
        cv2.line(frame, (x0, y), (xe, y), self.accent, th, cv2.LINE_AA)
        cv2.circle(frame, (xe, y), int(th * 1.1), (255, 255, 255), -1, cv2.LINE_AA)
        if over is not None:   # fading in: blend the bar back by the card's alpha
            cv2.addWeighted(frame, alpha, over, 1.0 - alpha, 0, dst=frame)
