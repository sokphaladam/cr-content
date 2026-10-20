"""Motion and effects for still pictures (AI scene art, photos): what makes a slideshow look like an edited video.

Every frame is drawn on the GPU with torch (sub-pixel sampling, so slow camera moves glide instead of stepping a
pixel at a time like FFmpeg's zoompan) and piped to FFmpeg, which grades, adds the audio and encodes.

- camera moves (MOTIONS), eased in and out; the "3D" ones use a depth map of the picture (Depth Anything V2) so the
  foreground slides over the background, a 2.5D parallax like a real camera move
- effects (EFFECTS): bloom glow, light leaks, floating particles (dust, snow, embers, sparkles, petals), anime speed
  lines, chromatic aberration, film grain, vignette
- old tape (TAPES): VHS playback, rewinding, TV static, a camcorder date stamp, a 4:3 home-video frame inside the
  video's frame, and `wear` (0..1) that makes each replay of a memory worse: more tracking noise, faded colour,
  skipped frames, and with `fade` the nearest subject (found by depth) fading away from the scene
- beat accents for music videos: on each beat inside the shot a zoom punch, and with "flash" a white flash
"""
import hashlib
import math
import subprocess
import threading
from pathlib import Path

from .config import CACHE_DIR, FPS, HEIGHT, WIDTH, ROOT

DEPTH_REPO = "depth-anything/Depth-Anything-V2-Small-hf"
DEPTH_CACHE = CACHE_DIR / "depth"

MOTIONS: dict[str, str] = {
    "push_in": "Push in",
    "pull_out": "Pull out",
    "pan_left": "Pan left",
    "pan_right": "Pan right",
    "tilt_up": "Tilt up",
    "tilt_down": "Tilt down",
    "orbit_3d": "3D orbit",
    "dolly_3d": "3D dolly in",
    "rise_3d": "3D crane up",
    "still": "Hold",
    "breathe": "Breathe (slow loop)",  # a slow zoom and drift that never ends: one picture held for a whole song
}
EFFECTS: dict[str, str] = {
    "glow": "Bloom glow",
    "light_leak": "Light leaks",
    "dust": "Floating dust",
    "snow": "Snow",
    "embers": "Embers",
    "sparkles": "Sparkles",
    "petals": "Petals",
    "bokeh": "Bokeh lights",
    "rain": "Rain",
    "neon_glow": "Neon glow",
    "speed_lines": "Speed lines",
    "light_trails": "Light trails",
    "chromatic": "Chromatic aberration",
    "grain": "Film grain",
    "vignette": "Vignette",
    "flash": "Beat flash",
}
PARTICLES = ("dust", "snow", "embers", "sparkles", "petals", "bokeh", "rain")
# old-tape treatments for a whole section of a music video (render_shot's tape / wear / frame / stamp / fade)
TAPES: dict[str, str] = {
    "": "None",
    "play": "VHS playback",  # tracking lines, colour bleed, scanlines, tape noise
    "rewind": "Rewinding",  # the shot runs backwards with tearing bands, harder on the beat
    "static_in": "Static clearing",  # TV static that clears to the picture
    "static": "TV static",  # only static
}
FRAMES: dict[str, str] = {"full": "Full frame", "4:3": "4:3 home video"}

_depth_lock = threading.Lock()
_depth_model = None


def available() -> bool:
    try:
        import torch  # noqa: F401

        return True
    except ImportError:
        return False


def _device():
    import torch

    return torch.device("cuda" if torch.cuda.is_available() else "cpu")


def _ease(t):
    """Smooth start and stop (cosine ease-in-out) for t in 0..1."""
    return 0.5 - 0.5 * math.cos(math.pi * min(max(t, 0.0), 1.0))


# ---------- depth ----------

def depth_map(image: Path):
    """Relative depth of `image` (1 = nearest), a float16 tensor on the GPU at a quarter of its size. Cached."""
    import numpy as np
    import torch
    from PIL import Image

    key = hashlib.sha1(f"{image.resolve()}\n{image.stat().st_mtime_ns}".encode()).hexdigest()[:16]
    cached = DEPTH_CACHE / f"{key}.npy"
    if cached.exists():
        d = np.load(cached)
    else:
        global _depth_model
        with _depth_lock:
            from transformers import pipeline

            if _depth_model is None:
                local = ROOT / "models" / "depth-anything-v2-small"
                if not (local / "config.json").exists():
                    from huggingface_hub import snapshot_download

                    snapshot_download(DEPTH_REPO, local_dir=local)
                _depth_model = pipeline("depth-estimation", model=str(local), device=0 if torch.cuda.is_available() else -1)
            pic = Image.open(image).convert("RGB")
            pic.thumbnail((768, 768))
            d = np.asarray(_depth_model(pic)["predicted_depth"].squeeze().float().cpu().numpy(), dtype=np.float32)
        d = (d - d.min()) / max(float(d.max() - d.min()), 1e-6)
        DEPTH_CACHE.mkdir(parents=True, exist_ok=True)
        np.save(cached, d)
    t = torch.from_numpy(d)[None, None].to(_device())
    # soften edges: a sharp depth step tears the picture apart when the layers slide
    t = torch.nn.functional.avg_pool2d(t, 9, stride=1, padding=4)
    return t.half() if t.is_cuda else t


def release_depth() -> None:
    global _depth_model
    with _depth_lock:
        _depth_model = None


# ---------- camera ----------

# the framings a held picture cuts between (render_shot's `cuts`): (extra zoom, how far the frame moves toward the
# subject: 1 = centred on it); always on the subject, at different sizes. The first is the shot as planned. Kept
# moderate: a 1.45x punch-in on a 1-megapixel picture shows its pixels, and big jumps read as amateur
FRAMINGS = [(1.0, 0.0), (1.18, 1.0), (1.08, 0.6), (1.25, 1.0), (1.12, 0.8)]


def _subject(depth) -> tuple[float, float]:
    """Centre of the nearest part of the picture (what's in front: usually the subject), in -1..1 grid units, from
    its depth map; a little above the middle without one."""
    if depth is None:
        return 0.0, -0.1
    import torch

    d = depth[0, 0].float()
    near = (d >= torch.quantile(d.flatten()[:: max(d.numel() // 20000, 1)], 0.85)).float()
    total = float(near.sum())
    if total < 1:
        return 0.0, -0.1
    h, w = d.shape
    ys = torch.linspace(-1, 1, h, device=d.device)[:, None]
    xs = torch.linspace(-1, 1, w, device=d.device)[None, :]
    return float((near * xs).sum() / total), float((near * ys).sum() / total)


def _camera(motion: str, p: float, room_x: float, room_y: float) -> tuple[float, float, float, float]:
    """(zoom, centre x, centre y, parallax amount) at progress p (eased), in grid units of the source picture.

    room_x/room_y: how far the centre can move at zoom 1 before the frame shows past the picture's edge."""
    e = _ease(p)
    # gentle on purpose: a slow 8% push reads as a camera move, 16% as a zoom effect (and magnifies the picture)
    if motion == "push_in":
        return 1.0 + 0.08 * e, 0.0, 0.0, 0.0
    if motion == "pull_out":
        return 1.08 - 0.08 * e, 0.0, 0.0, 0.0
    if motion in ("pan_left", "pan_right"):
        z = 1.08
        reach = min(room_x + (1 - 1 / z), 0.6) * 0.9
        x = reach * (1 - 2 * e) * (1 if motion == "pan_left" else -1)
        return z, x, 0.0, 0.0
    if motion in ("tilt_up", "tilt_down"):
        z = 1.08
        reach = min(room_y + (1 - 1 / z), 0.6) * 0.9
        y = reach * (1 - 2 * e) * (1 if motion == "tilt_up" else -1)
        return z, 0.0, y, 0.0
    if motion == "orbit_3d":
        return 1.12, 0.05 * (1 - 2 * e), 0.0, (1 - 2 * e)
    if motion == "dolly_3d":
        return 1.04 + 0.1 * e, 0.0, 0.0, e
    if motion == "rise_3d":
        return 1.12, 0.0, 0.05 * (1 - 2 * e), (1 - 2 * e)
    return 1.04 + 0.02 * e, 0.0, 0.0, 0.0  # still: a barely-there drift so it never looks frozen


# ---------- effects ----------

class _Particles:
    """Particles drifting through the frame: small, crisp, faint dots. The round ones (a gaussian is separable) are
    drawn as one matrix product of per-particle row and column profiles, so they're cheap at full resolution; rain
    streaks and tumbling petals aren't separable and are drawn per pixel, on the smaller canvas render_shot gives
    them (still sharp: the old quarter-size canvas blew every flake up into a blurry blob). `aspect`: the frame's
    width / height, when the canvas pixels aren't square."""

    ROUND = ("dust", "snow", "embers", "sparkles", "bokeh")

    def __init__(self, kind: str, w: int, h: int, seed: int, aspect: float | None = None):
        import torch

        g = torch.Generator().manual_seed(seed)
        self.aspect = aspect or w / h
        # few: a frame full of flakes is noise (and x264 spends the bitrate on them instead of the picture)
        n = {"dust": 40, "snow": 70, "embers": 45, "sparkles": 36, "petals": 26, "bokeh": 12, "rain": 170}[kind]
        self.kind, self.w, self.h = kind, w, h
        self.pos = torch.rand(n, 2, generator=g)
        self.size = torch.rand(n, generator=g)
        self.phase = torch.rand(n, generator=g) * 6.28
        speed = {"dust": (0.004, -0.012), "snow": (0.01, 0.06), "embers": (0.012, -0.07), "sparkles": (0, 0),
                 "petals": (0.03, 0.045), "bokeh": (0.003, -0.009),
                 "rain": (0.004, 0.75)}[kind]
        self.vel = torch.stack([(torch.rand(n, generator=g) - 0.5) * 2 * speed[0] + (speed[0] if kind == "petals" else 0),
                                (0.5 + torch.rand(n, generator=g)) * speed[1]], 1)
        self.color = {"dust": (1.0, 0.94, 0.82), "snow": (1.0, 1.0, 1.0), "embers": (1.0, 0.55, 0.18),
                      "sparkles": (1.0, 0.97, 0.85), "petals": (1.0, 0.72, 0.82),
                      "bokeh": (1.0, 0.97, 0.99), "rain": (0.86, 0.92, 1.0)}[kind]
        dev = _device()
        self.x1, self.y1 = torch.linspace(0, 1, w, device=dev), torch.linspace(0, 1, h, device=dev)
        if kind not in self.ROUND:  # the per-pixel kinds need the whole grid
            ys, xs = torch.meshgrid(self.y1, self.x1, indexing="ij")
            self.xs, self.ys = xs, ys
        self.pos, self.size, self.phase, self.vel = (t.to(dev) for t in (self.pos, self.size, self.phase, self.vel))
        self.colorv = torch.tensor(self.color, device=dev).view(3, 1, 1)

    def layer(self, t: float):
        """(3, h, w) light to add at time t seconds."""
        import torch

        sway = torch.stack([torch.sin(self.phase + t * 0.9) * 0.01, torch.zeros_like(self.phase)], 1)
        p = (self.pos + self.vel * t + sway) % 1.0
        # radius in frame heights: snow is a fleck, not a blob over the subject's face
        radius = {"dust": 0.0032, "snow": 0.0018, "embers": 0.0018, "sparkles": 0.0014, "petals": 0.0045,
                  "bokeh": 0.014, "rain": 0.0008}[self.kind]
        # never thinner than ~0.6 px: a sub-pixel gaussian flickers in brightness as it crosses the pixel grid
        aspect = self.aspect
        r = (radius * (0.5 + self.size)).clamp(min=0.6 * aspect / self.w)
        if self.kind == "rain":  # thin streaks falling fast at a slight slant
            dx = (self.xs[None] - p[:, 0, None, None]) * aspect
            dy = self.ys[None] - p[:, 1, None, None]
            dx = dx - dy * 0.12
            d2 = dx * dx + (dy / 30) ** 2
            streaks = (torch.exp(-d2 / (r * r)[:, None, None] / 2) * (0.25 + 0.3 * self.size)[:, None, None]).sum(0)
            return (streaks.clamp(max=0.8) * 0.6)[None] * self.colorv
        bright = (0.45 + 0.55 * self.size) * 0.6  # faint: they sit over the picture, they aren't the picture
        if self.kind == "sparkles":
            bright = bright * (0.5 + 0.5 * torch.sin(self.phase + t * 5.0)).clamp(min=0) ** 3 * 2.0
        if self.kind == "embers":
            bright = bright * (0.75 + 0.25 * torch.sin(self.phase + t * 7.0))
        if self.kind == "bokeh":  # big, faint, slowly breathing discs of out-of-focus light
            bright = bright * 0.2 * (0.7 + 0.3 * torch.sin(self.phase + t * 0.7))
        if self.kind == "petals":  # small tumbling ovals
            dx = (self.xs[None] - p[:, 0, None, None]) * aspect
            dy = self.ys[None] - p[:, 1, None, None]
            ang = self.phase[:, None, None] + t * 2.0
            dx, dy = dx * torch.cos(ang) - dy * torch.sin(ang), (dx * torch.sin(ang) + dy * torch.cos(ang)) * 2.2
            blobs = (torch.exp(-(dx * dx + dy * dy) / (r * r)[:, None, None] / 2) * bright[:, None, None]).sum(0)
        else:  # exp(-(dx^2 + dy^2)) = exp(-dx^2) * exp(-dy^2): sum over particles of a row profile times a column one
            inv = 1 / (2 * r * r)[:, None]
            gx = torch.exp(-((self.x1[None] - p[:, 0, None]) * aspect) ** 2 * inv)  # (n, w)
            gy = torch.exp(-(self.y1[None] - p[:, 1, None]) ** 2 * inv) * bright[:, None]  # (n, h)
            blobs = gy.T @ gx
        return blobs.clamp(max=1.2)[None] * self.colorv


class _LightLeak:
    """Two or three big warm glows drifting slowly across the frame."""

    def __init__(self, w: int, h: int, seed: int, neon: bool = False):
        import random

        rnd = random.Random(seed)
        # warm film light, or pink and blue city neon spilling in from the edges
        colours = [(1.0, 0.2, 0.75), (0.25, 0.55, 1.0), (0.7, 0.25, 1.0)] if neon else             [(1.0, 0.45, 0.15), (1.0, 0.25, 0.35), (1.0, 0.7, 0.3), (0.5, 0.35, 1.0)]
        self.blobs = [(rnd.uniform(-0.3, 1.3), rnd.uniform(-0.2, 1.2), rnd.uniform(-0.05, 0.05), rnd.uniform(-0.03, 0.03),
                       rnd.uniform(0.35, 0.6), rnd.choice(colours)) for _ in range(rnd.randint(2, 3))]
        self.gain = 0.45 if neon else 0.22  # neon has to read as coloured light, film light only warms (a hint, not a haze)
        import torch

        ys, xs = torch.meshgrid(torch.linspace(0, 1, h), torch.linspace(0, 1, w), indexing="ij")
        self.xs, self.ys, self.aspect = xs.to(_device()), ys.to(_device()), w / h

    def layer(self, t: float):
        import torch

        out = torch.zeros(3, *self.xs.shape, device=self.xs.device)
        for x, y, vx, vy, r, c in self.blobs:
            d2 = ((self.xs - (x + vx * t)) * self.aspect) ** 2 + (self.ys - (y + vy * t)) ** 2
            glow = torch.exp(-d2 / (r * r)) * (0.75 + 0.25 * math.sin(t * 0.8 + x * 5))
            out += glow[None] * torch.tensor(c, device=out.device).view(3, 1, 1)
        return out * self.gain


class _LightTrails:
    """Long-exposure car light streaks sweeping across the lower part of the frame: warm headlights one way, red and
    pink taillights the other."""

    def __init__(self, w: int, h: int, seed: int):
        import random

        import torch

        rnd = random.Random(seed)
        colors = [(1.0, 0.86, 0.6), (1.0, 0.95, 0.85), (1.0, 0.22, 0.25), (1.0, 0.35, 0.6), (1.0, 0.55, 0.2)]
        # (lane y, thickness, speed in frame widths per second (sign = direction), phase, length, colour)
        self.trails = []
        for _ in range(14):
            c = rnd.choice(colors)
            direction = 1 if c[1] > 0.5 else -1  # headlights come one way, taillights go the other
            self.trails.append((rnd.uniform(0.55, 0.95), rnd.uniform(0.003, 0.009), direction * rnd.uniform(0.6, 1.4),
                                rnd.random(), rnd.uniform(0.35, 0.8), c))
        ys, xs = torch.meshgrid(torch.linspace(0, 1, h), torch.linspace(0, 1, w), indexing="ij")
        self.xs, self.ys = xs.to(_device()), ys.to(_device())

    def layer(self, t: float):
        import torch

        out = torch.zeros(3, *self.xs.shape, device=self.xs.device)
        for y, thick, speed, phase, length, c in self.trails:
            head = (phase + speed * t) % (1 + length) - length / 2  # where the streak's bright end is
            behind = (head - self.xs) * (1 if speed > 0 else -1)  # 0 at the head, growing along the tail
            along = torch.where(behind >= 0, torch.exp(-behind / (length * 0.45)), torch.exp(behind * 60))
            across = torch.exp(-((self.ys - y) ** 2) / (2 * thick * thick))
            out += (along * across)[None] * torch.tensor(c, device=out.device).view(3, 1, 1)
        return out.clamp(max=1.4) * 0.8


def _blur(x, radius: int):
    """Cheap wide blur: three box blurs approximate a gaussian."""
    import torch.nn.functional as F

    k = radius * 2 + 1
    for _ in range(3):
        x = F.avg_pool2d(x, k, stride=1, padding=radius, count_include_pad=False)
    return x


def _screen(a, b):
    return 1 - (1 - a) * (1 - b.clamp(0, 1))


# ---------- old tape ----------

def _stamp_font(px: int):
    from PIL import ImageFont

    for name in ("consolab.ttf", "consola.ttf", "lucon.ttf", "courbd.ttf", "Menlo.ttc", "DejaVuSansMono-Bold.ttf"):
        for folder in ("C:/Windows/Fonts", "/System/Library/Fonts", "/Library/Fonts", "/usr/share/fonts/truetype/dejavu"):
            try:
                return ImageFont.truetype(f"{folder}/{name}", px)
            except OSError:
                continue
    return ImageFont.load_default(px)


class _Tape:
    """A VHS tape played on an old TV: per-row horizontal displacement (tracking band, head-switching noise at the
    bottom, rewind tears), then the picture's colour (smeared, shifted chroma, soft luma, lifted blacks, scanlines,
    noise), TV static, and the camcorder's on-screen display. `wear` 0..1: how worn the tape is."""

    def __init__(self, tape: str, wear: float, stamp: str, w: int, h: int, seed: int, dev, half):
        import random

        import torch

        self.tape, self.wear, self.w, self.h, self.dev, self.half = tape, min(max(wear, 0.0), 1.0), w, h, dev, half
        self.rnd = random.Random(seed)
        self.seed = seed
        self.rows = torch.linspace(0, 1, h, device=dev)
        self.scan = (1 - 0.07 * (torch.arange(h, device=dev) % 2)).to(half).view(1, 1, h, 1)
        self.osd = [self._osd(stamp, False), self._osd(stamp, True)] if tape in ("play", "rewind") else None

    def _osd(self, stamp: str, scrambled: bool):
        """The camcorder's text (PLAY / REW top left, the date stamp bottom left) as (rgb, alpha) tensors."""
        import numpy as np
        import torch
        from PIL import Image, ImageDraw

        w, h = self.w, self.h
        px = max(14, round(h * 0.06))
        font = _stamp_font(px)
        img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        m = round(px * 0.9)
        rew = self.tape == "rewind"
        label = "REW" if rew else "PLAY"
        if stamp and scrambled:  # a worn tape's date stamp glitching to wrong numbers for a frame
            stamp = "".join(str(self.rnd.randint(0, 9)) if c.isdigit() else c for c in stamp)

        def text(x, y, s):
            d.text((x + 3, y + 3), s, font=font, fill=(0, 0, 0, 170))
            d.text((x, y), s, font=font, fill=(255, 250, 235, 235))

        def triangles(x, y, n, left):
            s = px * 0.8
            for k in range(n):
                ox = x + k * s * 0.75
                pts = [(ox, y + s / 2), (ox + s * 0.75, y), (ox + s * 0.75, y + s)] if left else \
                      [(ox, y), (ox + s * 0.75, y + s / 2), (ox, y + s)]
                d.polygon([(a + 3, b + 3) for a, b in pts], fill=(0, 0, 0, 170))
                d.polygon(pts, fill=(255, 250, 235, 235))
            return x + n * s * 0.75 + s * 0.4

        y = m + px * 0.1
        if rew:
            x = triangles(m, y, 2, True)
            text(x, m, label)
        else:
            x = d.textlength(label, font=font) + m + px * 0.4
            text(m, m, label)
            triangles(x, y, 1, False)
        if stamp:
            lines = stamp.upper().splitlines()[:2]
            for k, line in enumerate(reversed(lines)):
                text(m, h - m - px * (k + 1) * 1.2, line)
        a = torch.from_numpy(np.array(img)).to(self.dev).permute(2, 0, 1)[None].to(self.half) / 255.0
        return a[:, :3], a[:, 3:]

    def offsets(self, n: int, t: float, hit: float):
        """Horizontal shift of every row this frame, in pixels: a (h,) tensor."""
        import torch

        g = torch.Generator(device=self.dev).manual_seed(self.seed * 7919 + n)
        noise = torch.rand(self.h, generator=g, device=self.dev) - 0.5
        noise = torch.nn.functional.avg_pool1d(noise[None, None], 9, stride=1, padding=4)[0, 0] * 3  # smooth ripples
        wear, y = self.wear, self.rows
        off = torch.zeros(self.h, device=self.dev)
        if self.tape in ("play", "rewind"):
            jitter = (torch.rand(1, generator=g, device=self.dev) - 0.5) * (0.6 + 3.0 * wear) if n % 3 == 0 else 0.0
            off = off + jitter
            # a tracking band rolling slowly down the picture
            centre = (t * (0.11 + 0.2 * wear) + (self.seed % 97) / 97) % 1.3 - 0.15
            width = 0.025 + 0.06 * wear + 0.04 * hit * wear
            band = torch.exp(-((y - centre) / width) ** 2)
            off = off + band * noise * (3 + 26 * wear + 20 * hit * wear)
            # head-switching noise along the bottom edge
            bottom = (y > 0.975).float()
            off = off + bottom * (8 + 14 * wear) * (0.6 + noise)
        if self.tape == "rewind":  # fast tearing bands sweeping up, harder on the beat
            for k in range(3):
                c = 1.1 - ((t * (1.6 + 0.5 * k) + k * 0.37) % 1.3)
                band = torch.exp(-((y - c) / (0.035 + 0.02 * k)) ** 2)
                off = off + band * (40 + 30 * k + 60 * hit) * (0.5 + noise)
            off = off + torch.sin(y * 40 + t * 30) * (1.5 + 6 * hit)
        return off

    def colour(self, frame, n: int, t: float, hit: float):
        """The tape's picture: frame (1, 3, h, w) in 0..1 -> the same frame through a VHS deck."""
        import torch
        import torch.nn.functional as F

        wear = self.wear
        luma = (frame * torch.tensor([0.299, 0.587, 0.114], device=self.dev, dtype=self.half).view(1, 3, 1, 1)).sum(1, keepdim=True)
        chroma = frame - luma
        k = 7 + 2 * round(5 * wear)
        chroma = F.avg_pool2d(chroma, (1, k), stride=1, padding=(0, k // 2), count_include_pad=False)  # colour smears sideways
        chroma = torch.roll(chroma, shifts=round(3 + 5 * wear), dims=-1)  # and lags behind the picture
        chroma = chroma * (0.9 - 0.55 * wear)
        luma = F.avg_pool2d(luma, (1, 3), stride=1, padding=(0, 1), count_include_pad=False)  # soft tape resolution
        luma = luma * (0.9 - 0.08 * wear) + 0.05 + 0.03 * wear  # lifted blacks, dimmer whites
        out = luma + chroma
        out = out + torch.tensor([0.035, 0.012, -0.03], device=self.dev, dtype=self.half).view(1, 3, 1, 1) * (1 - 0.6 * wear)
        g = torch.Generator(device=self.dev).manual_seed(self.seed * 104729 + n)
        noise = torch.randn(1, 1, self.h // 2, self.w // 4, generator=g, device=self.dev, dtype=self.half)
        noise = F.interpolate(noise, size=(self.h, self.w), mode="nearest")  # tape noise is stretched sideways
        out = out + noise * (0.025 + 0.045 * wear)
        # white dropout streaks: a few short scratches, many more on a worn tape or on a rewind beat
        streaks = int(self.rnd.random() < 0.15 + 0.6 * wear) * self.rnd.randint(1, 2 + round(8 * wear)) \
            + (self.rnd.randint(3, 9) if self.tape == "rewind" and hit > 0.3 else 0)
        for _ in range(streaks):
            r0, length = self.rnd.randrange(self.h - 2), self.rnd.uniform(0.04, 0.35) * self.w
            c0 = self.rnd.uniform(-0.1, 1) * self.w
            a, b = max(0, int(c0)), min(self.w, int(c0 + length))
            if b > a:
                out[:, :, r0:r0 + 2, a:b] = out[:, :, r0:r0 + 2, a:b] * 0.3 + 0.7
        out = out * self.scan
        if self.osd is not None:
            rgb, alpha = self.osd[1 if wear > 0.55 and self.rnd.random() < wear * 0.18 else 0]
            if self.tape != "rewind" or (t * 2) % 1 < 0.6:  # REW blinks
                out = out * (1 - alpha) + rgb * alpha
        return out.clamp(0, 1)

    def static(self, frame, n: int, amount: float):
        """TV static over `frame`, `amount` 0..1 (1 = only static)."""
        import torch
        import torch.nn.functional as F

        if amount <= 0:
            return frame
        g = torch.Generator(device=self.dev).manual_seed(self.seed * 15485863 + n)
        snow = torch.rand(1, 1, self.h // 2, self.w // 2, generator=g, device=self.dev, dtype=self.half)
        snow = F.interpolate(snow, size=(self.h, self.w), mode="nearest") ** 1.4
        roll = ((self.rows * 3 - n * 0.04) % 1.0 < 0.12).to(self.half).view(1, 1, self.h, 1)  # a brighter rolling bar
        snow = (snow * 0.85 + roll * 0.12).expand(1, 3, self.h, self.w) * self.scan
        return frame * (1 - amount) + snow * amount


def _rounded_mask(w: int, h: int, radius: float, dev, half):
    """1 inside a rounded rectangle filling w x h, softened over a pixel: an old TV's screen."""
    import torch

    ys, xs = torch.meshgrid(torch.arange(h, device=dev, dtype=torch.float32) + 0.5,
                            torch.arange(w, device=dev, dtype=torch.float32) + 0.5, indexing="ij")
    dx = (radius - xs).clamp(min=0) + (xs - (w - radius)).clamp(min=0)
    dy = (radius - ys).clamp(min=0) + (ys - (h - radius)).clamp(min=0)
    return (radius + 0.5 - torch.sqrt(dx * dx + dy * dy)).clamp(0, 1).to(half)[None, None]


# ---------- the shot ----------

BLOOM_FROM, BLOOM_KNEE = 0.82, 0.08  # luma where bloom starts, and how softly it fades in around that
# the shot's grade without a look: no darkening, a true black point and a little contrast and colour (eq pivots
# contrast at mid grey, so whites lift as blacks drop), then a light sharpen. The colour matrix is set on purpose:
# FFmpeg converts RGB to YUV with BT.601 by default, while players show HD video as BT.709 (a slight colour shift)
CLEAN_GRADE = "colorlevels=rimin=0.02:gimin=0.02:bimin=0.02,eq=contrast=1.05:saturation=1.06"
# contrast-adaptive: crisper lines without the halos of unsharp. On the luma plane of the YUV picture only: no
# colour fringes, and ~3x faster than on packed RGB (a 5-minute held shot is 9000 frames)
SHARPEN = "cas=0.35:planes=1"
TO_BT709 = ("scale=out_color_matrix=bt709:out_range=tv,format=yuv420p,"
            "setparams=colorspace=bt709:color_primaries=bt709:color_trc=bt709:range=tv")  # tags the frames too
BT709_TAGS = ["-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709", "-color_range", "tv"]


def _zoom_reach(motion: str, parallax: float, beats: bool, cuts: bool, impacts: bool) -> float:
    """The most a shot magnifies its picture (relative to cover-fit at zoom 1): the camera move's peak, times the
    beat punch, the tightest cut framing and an impact punch, and the 3D dolly's push on its near layer."""
    z = 1.055 if motion == "breathe" else max(_camera(motion, i / 20, 0.0, 0.0)[0] for i in range(21))
    if motion == "dolly_3d":
        z *= 1 + 0.09 * max(parallax, 0) * 1.2
    return z * (1.025 if beats else 1) * (max(f for f, _ in FRAMINGS) if cuts else 1) * (1.07 if impacts else 1)


def render_shot(image: Path, length: float, out: Path, *, size: tuple[int, int] = (WIDTH, HEIGHT),
                motion: str = "push_in", effects: tuple[str, ...] | list[str] = (), beats: list[float] = (),
                voice: Path | None = None, look: str = "", seed: int = 0, parallax: float = 1.0,
                tape: str = "", wear: float = 0.0, frame: str = "full", stamp: str = "", fade: bool = False,
                impacts: list[float] = (), cuts: list[float] = (), focus: tuple[float, float] | None = None,
                progress=None) -> None:
    """`image` filling a `size` frame for `length` seconds with a camera move and effects, as an mp4.

    beats: seconds (from the shot's start) to accent: a quick zoom punch, a flash with the "flash" effect, a
    colour split with "chromatic". impacts: seconds to HIT (pacing.impacts): a hard zoom punch, a shake, a white
    flash, a colour split and a shockwave ring from the subject. cuts: seconds to cut to a new framing of the
    picture (punch-ins on the subject at different sizes), so a held picture still changes every 1-2 s. focus: where
    the subject is (-1..1 grid units; from Claude's check of the picture), else it's found from the depth map.
    voice: the shot's audio (silent without). look: a colour grade (styles.LOOKS).
    parallax: strength of the 3D moves (0 = flat).
    tape: an old-tape treatment (TAPES); wear: 0..1, how worn that tape is; frame: "4:3" shows the shot as a home
    video on a dark screen inside the frame (FRAMES); stamp: the camcorder's date ("MAY 31 1998"; with tape play or
    rewind); fade: the nearest subject fades out of the scene, more with wear.
    progress: called with 0..1 as the frames are drawn (a long held shot takes minutes).
    """
    import numpy as np
    import torch
    import torch.nn.functional as F
    from PIL import Image

    OW, OH = size  # the video's frame; W x H is the picture inside it (smaller in a 4:3 home-video frame)
    W, H = size
    if frame == "4:3":
        margin = round(min(OW, OH) * 0.045)
        W = min(OW - 2 * margin, round((OH - 2 * margin) * 4 / 3)) // 2 * 2
        H = round(W * 3 / 4) // 2 * 2
    dev = _device()
    half = torch.float16 if dev.type == "cuda" else torch.float32
    pic = Image.open(image).convert("RGB")
    sw, sh = pic.size

    # cover-fit: the part of the picture (in its -1..1 grid units) the frame shows at zoom 1
    frame_aspect, pic_aspect = W / H, sw / sh
    fx, fy = (frame_aspect / pic_aspect, 1.0) if pic_aspect > frame_aspect else (1.0, pic_aspect / frame_aspect)
    room_x, room_y = 1 - fx, 1 - fy
    motion = motion if motion in MOTIONS else "push_in"
    # resample the picture ONCE with Lanczos to what the closest framing needs: grid_sample's bicubic is fine for the
    # small per-frame moves, but blurry when it has to magnify a 1-megapixel picture onto a 1080p frame, and it
    # aliases (shimmers) when it has to shrink a much bigger one. The grid is in normalized -1..1 units, so the move,
    # the depth map and every effect stay aligned whatever size the picture ends up
    zmax = _zoom_reach(motion, parallax, bool(beats), bool(cuts), bool(impacts))
    scale = W * min(zmax, 1.6) / fx / sw  # 1:1 sampling at the tightest framing (capped at 1.6x the frame)
    if scale > 1.02 or scale < 1 / 1.3:
        pic = pic.resize((max(round(sw * scale), 2), max(round(sh * scale), 2)), Image.LANCZOS)
    src = torch.from_numpy(np.array(pic)).to(dev).permute(2, 0, 1)[None].to(half) / 255.0
    ys, xs = torch.meshgrid(torch.linspace(-1, 1, H, device=dev, dtype=half),
                            torch.linspace(-1, 1, W, device=dev, dtype=half), indexing="ij")
    depth = None
    tape = tape if tape in TAPES else ""
    if (motion.endswith("_3d") and parallax > 0) or fade:
        try:
            depth = depth_map(image).to(half)
        except Exception as e:  # no depth model (offline): the move still happens, just flat
            print(f"  ! depth map unavailable ({type(e).__name__}); flat camera move")
    effects = set(effects)
    lw, lh = W // 4, H // 4
    # round particles are cheap at full size (_Particles), petals are drawn at half size and rain at half width (its
    # streaks are 30x longer than wide: height resolution is wasted on them): crisp either way
    canvas = {"rain": (W // 2, H // 4), "petals": (W // 2, H // 2)}
    particles = [_Particles(k, *canvas.get(k, (W, H)), seed + i, aspect=W / H)
                 for i, k in enumerate(PARTICLES) if k in effects]
    leak = _LightLeak(lw // 2, lh // 2, seed) if "light_leak" in effects else None
    neon = _LightLeak(lw // 2, lh // 2, seed + 11, neon=True) if "neon_glow" in effects else None
    trails = _LightTrails(lw, lh, seed) if "light_trails" in effects else None
    vignette = None
    if "vignette" in effects:
        r = torch.sqrt((xs.float() * (W / max(W, H))) ** 2 + (ys.float() * (H / max(W, H))) ** 2)
        # a light touch: it should guide the eye to the subject, not read as a dark ring
        vignette = (1 - 0.18 * ((r - 0.35) / 0.75).clamp(0, 1) ** 1.6).to(half)[None, None]
    angle = torch.atan2(ys.float() * H, xs.float() * W) if "speed_lines" in effects else None
    # distance from the centre in pixels, 1 at the corners: the lines only cover the edges of the frame
    radius = (torch.sqrt((xs.float() * W) ** 2 + (ys.float() * H) ** 2) / math.hypot(W, H)) if angle is not None else None
    beats = [b for b in beats if 0 <= b < length]
    impacts = sorted(b for b in impacts if 0 <= b < length)
    cuts = sorted(c for c in cuts if 0 < c < length)
    if (impacts or cuts) and depth is None and parallax > 0 and focus is None:
        try:  # only to find the subject, so punch-ins and shockwaves centre on it
            depth = depth_map(image).to(half)
        except Exception:
            pass
    focus = focus or _subject(depth)  # the subject's centre, in the picture's -1..1 grid units
    deck = _Tape(tape, wear, stamp, W, H, seed, dev, half) if tape else None
    screen = None
    if (OW, OH) != (W, H):  # the home-video picture on a dark screen, lit by its own glow
        screen = _rounded_mask(W, H, min(W, H) * 0.035, dev, half)
        x0, y0 = (OW - W) // 2, (OH - H) // 2
    skip = 0.3 * deck.wear ** 1.5 if deck and tape == "play" else 0.0  # worn tapes skip frames
    luma_w = torch.tensor([0.2126, 0.7152, 0.0722], device=dev, dtype=half).view(1, 3, 1, 1)  # BT.709 luma
    prev = None

    frames = max(round(length * FPS), 1)
    grade = CLEAN_GRADE + ","  # no darkening (captions have their own outline/box): true blacks
    if look:
        from .styles import look_filter

        grade = look_filter(look) + ","
    audio_in = ["-i", str(voice)] if voice else ["-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo"]
    log = out.with_suffix(".ffmpeg.log")
    with open(log, "w", encoding="utf-8", errors="replace") as err:
        proc = subprocess.Popen(
            ["ffmpeg", "-y", "-hide_banner", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{OW}x{OH}", "-r", str(FPS),
             "-i", "-", *audio_in, "-filter_complex",
             f"[0:v]{grade}setsar=1,{TO_BT709},{SHARPEN}[v];[1:a]aresample=44100,apad[a]",
             # near-lossless: this is an intermediate (render.finalize encodes the video once more for upload), so
             # it must not throw detail away twice; without grain a held picture is cheap even at crf 10
             "-map", "[v]", "-map", "[a]", "-t", f"{length:.3f}", "-c:v", "libx264", "-preset", "veryfast", "-crf", "10",
             *BT709_TAGS,
             "-c:a", "aac", "-b:a", "192k", "-ar", "44100", "-ac", "2", str(out)],
            stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=err)
        try:
            with torch.no_grad():
                for n in range(frames):
                    t = n / FPS
                    if progress and n % 15 == 0:
                        progress(n / frames)
                    p = n / max(frames - 1, 1)
                    since = [t - b for b in beats if t >= b]
                    hit = math.exp(-min(since) * 9) if since else 0.0  # 1 on the beat, fading over ~0.3 s
                    if prev is not None and skip and deck.rnd.random() < skip:
                        proc.stdin.write(prev)  # the tape skips: the last frame again
                        continue
                    if tape == "rewind":  # the move plays backwards, fast, over and over
                        p = 1 - (t * 1.6 / max(length, 0.5) + hit * 0.04) % 1.0
                    if motion == "breathe":  # by the clock, not the shot's progress: as slow in a 3-minute shot.
                        # prime periods (17 / 29 / 23 s): the zoom and the two drifts only line up again after
                        # ~3 hours, so the loop never visibly repeats. The zoom swings 1.015..1.055 (_zoom_reach)
                        zoom, cx, cy, par = (1.035 + 0.02 * math.sin(2 * math.pi * t / 17),
                                             0.015 * math.sin(2 * math.pi * t / 29), 0.01 * math.sin(2 * math.pi * t / 23), 0.0)
                    else:
                        zoom, cx, cy, par = _camera(motion, p, room_x, room_y)
                    zoom *= 1 + 0.025 * hit
                    # cut to the next framing of the picture (each holds until the next cut)
                    if cuts:
                        fz, pull = FRAMINGS[sum(1 for c in cuts if t >= c) % len(FRAMINGS)]
                        zoom *= fz
                        cx += (focus[0] - cx) * pull
                        cy += (focus[1] - cy) * pull
                    since_hit = [t - b for b in impacts if t >= b]
                    strike = math.exp(-min(since_hit) * 7) if since_hit else 0.0  # 1 on the hit, gone in ~0.4 s
                    if strike > 0.01:
                        zoom *= 1 + 0.07 * strike
                        cx += 0.021 * strike * math.sin(t * 91 + 1.3) / zoom  # shake
                        cy += 0.018 * strike * math.sin(t * 73) / zoom
                    # keep the frame inside the picture (punch-ins and shakes can push it past an edge)
                    cx = min(max(cx, -1 + fx / zoom), 1 - fx / zoom)
                    cy = min(max(cy, -1 + fy / zoom), 1 - fy / zoom)
                    gx = xs * (fx / zoom) + cx
                    gy = ys * (fy / zoom) + cy
                    d = None
                    if depth is not None:
                        grid0 = torch.stack([gx, gy], -1)[None]
                        d = F.grid_sample(depth, grid0, mode="bilinear", padding_mode="border", align_corners=False)[0, 0]
                        near = d - 0.5
                        if not motion.endswith("_3d") or parallax <= 0:
                            pass  # depth only for fading the subject
                        elif motion == "dolly_3d":  # near things grow faster than far ones as the camera moves in
                            k = 1 / (1 + 0.09 * parallax * par * (d + 0.2))
                            gx, gy = cx + (gx - cx) * k, cy + (gy - cy) * k
                        elif motion == "orbit_3d":
                            gx = gx - near * 0.05 * parallax * par
                        else:  # rise_3d
                            gy = gy - near * 0.05 * parallax * par
                    if deck is not None:  # tracking noise and tears shift whole rows sideways
                        gx = gx + (deck.offsets(n, t, hit) * (2 * fx / (W * zoom))).to(half)[:, None]
                    grid = torch.stack([gx, gy], -1)[None]
                    frame = F.grid_sample(src, grid, mode="bicubic", padding_mode="reflection", align_corners=False)
                    if "chromatic" in effects or strike > 0.02:
                        shift = ((1.5 if "chromatic" in effects else 0) + 9 * hit + 14 * strike) / W
                        r_ch = F.grid_sample(src[:, :1], grid + torch.tensor([shift, 0], device=dev, dtype=half),
                                             mode="bilinear", padding_mode="reflection", align_corners=False)
                        b_ch = F.grid_sample(src[:, 2:], grid - torch.tensor([shift, 0], device=dev, dtype=half),
                                             mode="bilinear", padding_mode="reflection", align_corners=False)
                        frame = torch.cat([r_ch, frame[:, 1:2], b_ch], 1)
                    frame = frame.clamp(0, 1)
                    if "glow" in effects:
                        # only real highlights glow: by luma, from 0.82 with a soft knee. Per channel from 0.62 a
                        # pastel sky (178,214,245) bloomed whole and the frame went hazy
                        small = F.avg_pool2d(frame, 4)
                        luma = (small * luma_w).sum(1, keepdim=True)
                        knee = (luma - (BLOOM_FROM - BLOOM_KNEE)).clamp(0, 2 * BLOOM_KNEE) ** 2 / (4 * BLOOM_KNEE)
                        bright = small * (torch.maximum(knee, luma - BLOOM_FROM) / luma.clamp(min=1e-3))
                        bloom = F.interpolate(_blur(bright, 6), size=(H, W), mode="bilinear", align_corners=False)
                        frame = _screen(frame, (bloom * 1.3).clamp(0, 1))
                    if leak is not None:
                        frame = _screen(frame, F.interpolate(leak.layer(t)[None].to(half), size=(H, W), mode="bilinear",
                                                             align_corners=False))
                    if neon is not None:
                        frame = _screen(frame, F.interpolate(neon.layer(t)[None].to(half), size=(H, W), mode="bilinear",
                                                             align_corners=False))
                    if trails is not None:
                        streaks = F.interpolate(trails.layer(t)[None].to(half), size=(H, W), mode="bilinear", align_corners=False)
                        frame = _screen(frame, streaks + _blur(streaks, 6) * 0.6)  # a soft glow around each streak
                    # flakes pass behind the subject (where the depth map is loaded anyway), not over their face
                    shield = None
                    if particles and d is not None:
                        shield = 1 - 0.7 * ((d - 0.55) / 0.2).clamp(0, 1)[None, None].to(half)
                    for pt in particles:
                        dots = pt.layer(t)[None].to(half)
                        if dots.shape[-1] != W:
                            dots = F.interpolate(dots, size=(H, W), mode="bilinear", align_corners=False)
                        frame = _screen(frame, dots if shield is None else dots * shield)
                    if angle is not None:
                        g = torch.Generator(device=dev).manual_seed(seed * 1000 + n // 2)  # lines change every 2 frames
                        spokes = torch.rand(420, generator=g, device=dev)
                        reach = 0.5 + 0.25 * torch.rand(420, generator=g, device=dev)  # each line starts at its own depth
                        idx = ((angle + math.pi) / (2 * math.pi) * 420).long().clamp(0, 419)
                        lines = ((spokes[idx] > 0.9).to(half) * ((radius - reach[idx]) / 0.25).clamp(0, 1).to(half))
                        frame = _screen(frame, (lines * 0.55)[None, None].expand(1, 3, H, W))
                    if fade and d is not None:  # the nearest subject loses its colour and turns to a ghost
                        near = ((d - 0.55) / 0.2).clamp(0, 1)[None, None].to(half)
                        amount = (0.35 + 0.5 * min(max(wear, 0.0), 1.0)) * (0.9 + 0.1 * math.sin(t * 13))
                        grey = frame.mean(1, keepdim=True) * 0.6 + 0.32
                        frame = frame * (1 - near * amount) + grey * near * amount
                    if deck is not None:
                        frame = deck.colour(frame, n, t, hit) if tape in ("play", "rewind") else frame * deck.scan
                        if tape == "static":
                            frame = deck.static(frame, n, 0.94)
                        elif tape == "static_in":  # static, then the picture comes through
                            frame = deck.static(frame, n, (1 - (p - 0.12) / 0.38) if p > 0.12 else 1.0)
                    if vignette is not None:
                        frame = frame * vignette
                    if "flash" in effects and hit > 0:
                        frame = frame + (1 - frame) * (0.55 * hit ** 2)
                    if strike > 0.01:
                        age = min(since_hit)
                        if age < 0.4:  # a shockwave ring racing out from the subject
                            sx_f = (focus[0] - cx) / (fx / zoom)  # the subject on screen, -1..1
                            sy_f = (focus[1] - cy) / (fy / zoom)
                            dist = torch.sqrt(((xs - sx_f) * (W / H)) ** 2 + (ys - sy_f) ** 2)
                            ring = torch.exp(-((dist - (0.12 + age * 3.2)) / 0.07) ** 2) * (0.7 * strike)
                            frame = _screen(frame, ring[None, None].expand(1, 3, H, W))
                        frame = frame + (1 - frame) * (0.92 * strike ** 4)  # white flash: 2-3 frames
                    if "grain" in effects:  # fine, faint, luma only and per pixel (2x2 blocks turned to mush in x264)
                        frame = frame + torch.randn(1, 1, H, W, device=dev, dtype=half) * 0.010
                    frame = frame.clamp(0, 1)
                    if screen is not None:  # the picture on a dark screen, its light spilling around it
                        spill = F.interpolate(frame, size=(max(H // 16, 1), max(W // 16, 1)), mode="area")
                        canvas = F.interpolate(_blur(F.pad(spill, (6, 6, 6, 6)), 3), size=(OH, OW), mode="bilinear",
                                               align_corners=False) * 0.22
                        inner = canvas[:, :, y0:y0 + H, x0:x0 + W]
                        canvas[:, :, y0:y0 + H, x0:x0 + W] = inner * (1 - screen) + frame * screen
                        frame = canvas
                    rgb = (frame[0].clamp(0, 1) * 255).to(torch.uint8).permute(1, 2, 0).contiguous().cpu().numpy()
                    prev = rgb.tobytes()
                    proc.stdin.write(prev)
            proc.stdin.close()
        except BrokenPipeError:
            pass
        code = proc.wait()
    if code != 0:
        raise RuntimeError(f"ffmpeg failed ({code}) rendering {out.name}:\n{log.read_text(encoding='utf-8')[-1500:]}")
    log.unlink(missing_ok=True)


def default_effects(style: str, music: bool) -> list[str]:
    """A sensible effect set for an art style when the director didn't pick one."""
    # no grain by default: it reads as noise on phone screens and x264 smears it (clean beats "filmic" for shorts);
    # it's still there when a director picks it
    base = {"anime": ["glow", "light_leak", "vignette"], "cinematic": ["vignette", "light_leak"],
            "flat": []}.get(style, ["vignette"])
    return base + (["chromatic"] if music and style != "flat" else [])
