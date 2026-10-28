"""A living illustration: the cover picture with parts of it moving, as a seamless loop (coverloop.LOOP), drawn on the
CPU from the original picture every frame. Nothing is redrawn by a model, so faces never melt and the art stays as
sharp as it was drawn.

You mark regions on the picture (boxes, 0..1 of its width and height, feathered at the edges) and give each a kind:
  sway     hair, a tail, leaves on a plant: bends, more at the end away from its anchor
  breathe  a body: a slow rise and fall from its anchor (usually the bottom)
  nod      a head: tilts gently to the music, pivoting at the middle of its anchor edge (the neck)
  write    a hand: small writing loops, the whole box moving together
  blink    an eye: squeezes shut for a moment now and then
  flicker  a lamp, a candle, a screen: its light breathes
  rain     rain falling inside the box only (a window), leaves: autumn leaves drifting down, steam: rising from a mug
  protect  never changes, whatever moves around it (a face next to swaying hair)
Each moves by small pixel shifts of the picture (a smooth displacement field, one remap per frame from the original:
nothing accumulates) or by particles drawn over it. Every motion repeats a whole number of times per loop, so the
loop joins itself exactly. Lyrics are drawn by the song renderer over the loop, so nothing here can touch them.
"""
import math
from pathlib import Path

KINDS = {
    "sway": "Sway (hair, tail, plants)",
    "breathe": "Breathe (body)",
    "nod": "Nod (head, from the neck)",
    "write": "Write (a hand on paper)",
    "blink": "Blink (eyes)",
    "flicker": "Flicker (lamp, candle)",
    "rain": "Rain (inside the box)",
    "leaves": "Falling leaves",
    "steam": "Steam",
    "protect": "Protect (never moves)",
}
ANCHORS = ("top", "bottom", "left", "right")
WARPS = ("sway", "breathe", "blink", "nod", "write")
PARTICLES = ("rain", "leaves", "steam")
MAX_REGIONS = 24


def clean(regions) -> list[dict]:
    """`regions` as checked regions ({kind, box, intensity, anchor}); ValueError for one that isn't."""
    out = []
    for r in list(regions or [])[:MAX_REGIONS]:
        kind = r.get("kind")
        if kind not in KINDS:
            raise ValueError(f"Unknown kind of motion: {kind!r}.")
        x, y, w, h = (float(v) for v in r.get("box", ()))
        x, y = min(max(x, 0.0), 1.0), min(max(y, 0.0), 1.0)
        w, h = min(w, 1 - x), min(h, 1 - y)
        if w < 0.01 or h < 0.01:
            raise ValueError("A region is too small: drag a bigger box.")
        anchor = r.get("anchor") if r.get("anchor") in ANCHORS else "top" if kind == "sway" else "bottom"   # nod: neck
        out.append({"kind": kind, "box": [round(x, 4), round(y, 4), round(w, 4), round(h, 4)],
                    "intensity": int(min(max(int(r.get("intensity", 50)), 0), 100)), "anchor": anchor})
    return out


def _bump(t: float, at: float, width: float, period: float) -> float:
    """A smooth 0..1..0 pulse `width` seconds wide centred at `at`, repeating every `period` (cyclic: seamless)."""
    d = abs((t - at + period / 2) % period - period / 2)
    return 0.5 + 0.5 * math.cos(math.pi * d / width) if d < width else 0.0


class _Region:
    def __init__(self, r: dict, size: tuple[int, int], index: int):
        import numpy as np

        W, H = size
        self.frame_w = W
        self.kind, self.a, self.anchor = r["kind"], r["intensity"] / 100, r["anchor"]
        x, y, w, h = r["box"]
        self.x0, self.y0 = int(x * W), int(y * H)
        self.x1, self.y1 = max(self.x0 + 2, int((x + w) * W)), max(self.y0 + 2, int((y + h) * H))
        self.w, self.h = self.x1 - self.x0, self.y1 - self.y0
        # feathered box: full inside, easing to 0 over the outer 18% (so a warp blends into what's around it)
        f = 0.18
        u = np.linspace(0, 1, self.w, dtype=np.float32)
        v = np.linspace(0, 1, self.h, dtype=np.float32)
        ease = lambda s: np.clip(np.minimum(s, 1 - s) / f, 0, 1) ** 2 * (3 - 2 * np.clip(np.minimum(s, 1 - s) / f, 0, 1))  # noqa: E731
        self.mask = np.outer(ease(v), ease(u))
        if self.kind == "protect":   # the whole box, edge to edge: what you protect stays exactly as drawn
            self.mask = np.ones_like(self.mask)
        # how far from the anchor each pixel is, 0 at it, 1 at the far edge
        self.reach = {"top": np.repeat(v[:, None], self.w, 1), "bottom": np.repeat(1 - v[:, None], self.w, 1),
                      "left": np.repeat(u[None, :], self.h, 0), "right": np.repeat(1 - u[None, :], self.h, 0)}[self.anchor]
        self.u, self.v = np.meshgrid(u, v)
        self.phase = index * 1.7   # regions don't move in step
        self.rng = np.random.default_rng(1000 + index)
        if self.kind in PARTICLES:
            self._particles()

    def _particles(self):
        n = {"rain": 0.00045, "leaves": 0.000018, "steam": 0.00006}[self.kind] * self.w * self.h * (0.3 + self.a)
        n = max(3, int(n))
        g = self.rng
        self.p_x = g.random(n)
        self.p_y = g.random(n)
        # whole numbers of trips through the box per loop: each particle is back where it started at the loop's end
        self.p_trips = {"rain": g.integers(10, 17, n), "leaves": g.integers(1, 3, n), "steam": g.integers(1, 3, n)}[self.kind]
        self.p_wobble = g.integers(1, 4, n)
        self.p_turn = g.integers(-2, 3, n)
        self.p_phase = g.random(n) * 2 * math.pi
        self.p_size = 0.6 + 0.8 * g.random(n)
        self.p_tint = g.integers(0, 3, n)

    def warp(self, t: float, T: float, dx, dy):
        """Add this region's pixel shifts at t to dx, dy (the whole frame's, in place)."""
        import numpy as np

        sl = (slice(self.y0, self.y1), slice(self.x0, self.x1))
        w = 2 * math.pi * t / T
        if self.kind == "sway":
            # 3 swings a loop, a ripple travelling out from the anchor, the free end moving most
            amp = self.a * 0.06 * min(self.w, self.h)
            bend = amp * self.reach ** 2 * np.sin(3 * w + self.phase - 2.2 * self.reach) * self.mask
            if self.anchor in ("top", "bottom"):
                dx[sl] += bend
            else:
                dy[sl] += bend
        elif self.kind == "breathe":
            # 3 breaths a loop (4 s each): the far side rises and falls, the anchor stays put
            s = self.a * 0.02 * self.h * (0.5 - 0.5 * math.cos(3 * w + self.phase))
            dy[sl] += (-s if self.anchor == "bottom" else s) * self.reach * self.mask
        elif self.kind == "nod":
            # 6 nods a loop (2 s each), up to 2.5 degrees, turning about the middle of the anchor edge: the neck
            th = math.radians(self.a * 2.5) * math.sin(6 * w + self.phase)
            px, py = {"bottom": (0.5, 1.0), "top": (0.5, 0.0), "left": (0.0, 0.5), "right": (1.0, 0.5)}[self.anchor]
            rx, ry = (self.u - px) * self.w, (self.v - py) * self.h
            dx[sl] += (-th * ry) * self.mask
            dy[sl] += (th * rx) * self.mask
        elif self.kind == "write":
            # a pen's small loops along the line: 12 a loop, wobbling up and down twice as fast
            r = self.a * 0.05 * min(self.w, self.h)
            dx[sl] += r * math.sin(12 * w + self.phase) * self.mask
            dy[sl] += 0.5 * r * math.sin(24 * w + self.phase) * self.mask
        elif self.kind == "blink":
            # twice a loop, 0.18 s each side of closed: rows squeeze toward the middle line
            c = max(_bump(t, T * (0.3 + 0.5 * k), 0.18, T) for k in range(2))
            if c:
                dy[sl] += (self.v - 0.5) * self.h * 0.95 * c * self.mask

    def light(self, t: float, T: float, frame):
        """Flicker: the region's brightness breathes (in place, frame is float32 RGB)."""
        w = 2 * math.pi * t / T
        f = 1 + self.a * 0.22 * (0.6 * math.sin(5 * w + self.phase) + 0.4 * math.sin(13 * w + 1 + self.phase))
        sl = (slice(self.y0, self.y1), slice(self.x0, self.x1))
        frame[sl] *= (1 + (f - 1) * self.mask)[..., None]

    def draw(self, t: float, T: float, frame):
        """Rain, leaves or steam inside the box at t (in place, frame is float32 RGB), faded at its feathered edge."""
        import cv2
        import numpy as np

        color = np.zeros((self.h, self.w, 3), np.float32)
        alpha = np.zeros((self.h, self.w), np.float32)
        s = t / T
        if self.kind == "rain":
            ys = (self.p_y + self.p_trips * s) % 1.0
            length = max(4, int(self.h * 0.07))
            thick = max(1, round(self.frame_w / 1000))   # 2 px streaks at 1080p, 1 px in the small preview
            for x, y in zip(self.p_x, ys):
                px, py = int(x * self.w + 0.12 * y * self.h), int(y * self.h)
                cv2.line(alpha, (px % self.w, py), ((px - int(0.12 * length)) % self.w, py - length), 0.45, thick,
                         cv2.LINE_AA)
            color[:] = (210, 225, 255)
        elif self.kind == "leaves":
            ys = (self.p_y + self.p_trips * s) % 1.0
            tints = np.array([(214, 110, 40), (196, 70, 38), (230, 170, 60)], np.float32)
            r0 = max(3, int(min(self.w, self.h) * 0.025))
            for i, y in enumerate(ys):
                x = (self.p_x[i] + 0.06 * math.sin(2 * math.pi * self.p_wobble[i] * s + self.p_phase[i])) % 1.0
                angle = (360 * self.p_turn[i] * s + math.degrees(self.p_phase[i])) % 360
                axes = (int(r0 * self.p_size[i]), max(1, int(r0 * self.p_size[i] * 0.45)))
                one = np.zeros_like(alpha)
                cv2.ellipse(one, (int(x * self.w), int(y * self.h)), axes, angle, 0, 360, 0.95, -1, cv2.LINE_AA)
                color += one[..., None] * (tints[self.p_tint[i]] - color)
                alpha = np.maximum(alpha, one)
        else:   # steam: soft puffs rising, growing and fading
            ys = 1 - (self.p_y + self.p_trips * s) % 1.0
            r0 = max(3, int(self.w * 0.12))
            for i, y in enumerate(ys):
                x = 0.5 + 0.25 * (self.p_x[i] - 0.5) + 0.08 * math.sin(2 * math.pi * self.p_wobble[i] * s + self.p_phase[i])
                up = 1 - y
                cv2.circle(alpha, (int(x * self.w), int(y * self.h)), int(r0 * (0.6 + up)), 0.10 * (1 - up), -1, cv2.LINE_AA)
            alpha = cv2.GaussianBlur(alpha, (0, 0), max(1.0, r0 / 2))
            color[:] = (245, 245, 245)
        a = (alpha * self.mask * min(1.0, 0.4 + self.a))[..., None]
        sl = (slice(self.y0, self.y1), slice(self.x0, self.x1))
        frame[sl] += a * (color - frame[sl])


def frames(picture, regions: list[dict], size: tuple[int, int], seconds: float):
    """frame(t) for the picture (a PIL image at `size`) with `regions` moving: RGB uint8 arrays. Periodic in t."""
    import cv2
    import numpy as np

    W, H = size
    base = np.asarray(picture.convert("RGB").resize(size), np.float32)
    rs = [_Region(r, size, i) for i, r in enumerate(clean(regions))]
    warps = [r for r in rs if r.kind in WARPS]
    xs, ys = np.meshgrid(np.arange(W, dtype=np.float32), np.arange(H, dtype=np.float32))

    def frame(t: float):
        if warps:
            dx, dy = np.zeros((H, W), np.float32), np.zeros((H, W), np.float32)
            for r in warps:
                r.warp(t, seconds, dx, dy)
            out = cv2.remap(base, xs - dx, ys - dy, cv2.INTER_CUBIC, borderMode=cv2.BORDER_REFLECT)
        else:
            out = base.copy()
        for r in rs:
            if r.kind == "flicker":
                r.light(t, seconds, out)
            elif r.kind in PARTICLES:
                r.draw(t, seconds, out)
        for r in rs:   # last, so nothing that moved around it can reach in
            if r.kind == "protect":
                sl = (slice(r.y0, r.y1), slice(r.x0, r.x1))
                m = r.mask[..., None]
                out[sl] = out[sl] * (1 - m) + base[sl] * m
        return np.clip(out, 0, 255).astype(np.uint8)

    return frame


def render(still: Path, out: Path, regions, log=print, progress=None) -> None:
    """The living loop of `still` at coverloop.SIZE / SECONDS / FPS, written to `out` (swapped in only once it checks
    out). ValueError for no regions, a bad region or an unreadable picture."""
    from . import coverloop

    regions = clean(regions)
    if not regions:
        raise ValueError("Mark at least one part of the picture to move (drag a box over it).")
    log("Bringing the picture to life…")
    coverloop.write_loop(out, frames(coverloop.read_still(still), regions, coverloop.SIZE, coverloop.SECONDS),
                         coverloop.SIZE, progress=progress)


PREVIEW = "loop.preview.mp4"
PREVIEW_SIZE = (640, 360)


def preview(still: Path, out: Path, regions) -> None:
    """A quick small preview of the living loop (the whole loop at 640x360, 15 fps: a few seconds to make)."""
    from . import coverloop

    regions = clean(regions)
    if not regions:
        raise ValueError("Mark at least one part of the picture to move (drag a box over it).")
    coverloop.write_loop(out, frames(coverloop.read_still(still), regions, PREVIEW_SIZE, coverloop.SECONDS),
                         PREVIEW_SIZE, fps=15)
