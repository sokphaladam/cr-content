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
}
EFFECTS: dict[str, str] = {
    "glow": "Bloom glow",
    "light_leak": "Light leaks",
    "dust": "Floating dust",
    "snow": "Snow",
    "embers": "Embers",
    "sparkles": "Sparkles",
    "petals": "Petals",
    "speed_lines": "Speed lines",
    "light_trails": "Light trails",
    "chromatic": "Chromatic aberration",
    "grain": "Film grain",
    "vignette": "Vignette",
    "flash": "Beat flash",
}
PARTICLES = ("dust", "snow", "embers", "sparkles", "petals")
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
# subject: 1 = centred on it); always on the subject, at different sizes. The first is the shot as planned
FRAMINGS = [(1.0, 0.0), (1.3, 1.0), (1.14, 0.6), (1.45, 1.0), (1.2, 0.8)]


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
    if motion == "push_in":
        return 1.0 + 0.16 * e, 0.0, 0.0, 0.0
    if motion == "pull_out":
        return 1.16 - 0.16 * e, 0.0, 0.0, 0.0
    if motion in ("pan_left", "pan_right"):
        z = 1.14
        reach = min(room_x + (1 - 1 / z), 0.6) * 0.9
        x = reach * (1 - 2 * e) * (1 if motion == "pan_left" else -1)
        return z, x, 0.0, 0.0
    if motion in ("tilt_up", "tilt_down"):
        z = 1.14
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
    """Particles drifting through the frame, drawn as soft dots on a quarter-size canvas."""

    def __init__(self, kind: str, w: int, h: int, seed: int):
        import torch

        g = torch.Generator().manual_seed(seed)
        n = {"dust": 70, "snow": 140, "embers": 60, "sparkles": 50, "petals": 36}[kind]
        self.kind, self.w, self.h = kind, w, h
        self.pos = torch.rand(n, 2, generator=g)
        self.size = torch.rand(n, generator=g)
        self.phase = torch.rand(n, generator=g) * 6.28
        speed = {"dust": (0.004, -0.012), "snow": (0.01, 0.06), "embers": (0.012, -0.07), "sparkles": (0, 0),
                 "petals": (0.03, 0.045)}[kind]
        self.vel = torch.stack([(torch.rand(n, generator=g) - 0.5) * 2 * speed[0] + (speed[0] if kind == "petals" else 0),
                                (0.5 + torch.rand(n, generator=g)) * speed[1]], 1)
        self.color = {"dust": (1.0, 0.94, 0.82), "snow": (1.0, 1.0, 1.0), "embers": (1.0, 0.55, 0.18),
                      "sparkles": (1.0, 0.97, 0.85), "petals": (1.0, 0.72, 0.82)}[kind]
        ys, xs = torch.meshgrid(torch.linspace(0, 1, h), torch.linspace(0, 1, w), indexing="ij")
        dev = _device()
        self.xs, self.ys = xs.to(dev), ys.to(dev)
        self.pos, self.size, self.phase, self.vel = (t.to(dev) for t in (self.pos, self.size, self.phase, self.vel))
        self.colorv = torch.tensor(self.color, device=dev).view(3, 1, 1)

    def layer(self, t: float):
        """(3, h, w) light to add at time t seconds."""
        import torch

        sway = torch.stack([torch.sin(self.phase + t * 0.9) * 0.01, torch.zeros_like(self.phase)], 1)
        p = (self.pos + self.vel * t + sway) % 1.0
        radius = {"dust": 0.006, "snow": 0.0035, "embers": 0.0028, "sparkles": 0.0022, "petals": 0.006}[self.kind]
        r = radius * (0.5 + self.size)
        aspect = self.w / self.h
        dx = (self.xs[None] - p[:, 0, None, None]) * aspect
        dy = self.ys[None] - p[:, 1, None, None]
        if self.kind == "petals":  # small tumbling ovals
            ang = self.phase[:, None, None] + t * 2.0
            dx, dy = dx * torch.cos(ang) - dy * torch.sin(ang), (dx * torch.sin(ang) + dy * torch.cos(ang)) * 2.2
        d2 = dx * dx + dy * dy
        bright = 0.45 + 0.55 * self.size
        if self.kind == "sparkles":
            bright = bright * (0.5 + 0.5 * torch.sin(self.phase + t * 5.0)).clamp(min=0) ** 3 * 2.0
        if self.kind == "embers":
            bright = bright * (0.75 + 0.25 * torch.sin(self.phase + t * 7.0))
        blobs = (torch.exp(-d2 / (r * r)[:, None, None] / 2) * bright[:, None, None]).sum(0).clamp(max=1.2)
        return blobs[None] * self.colorv


class _LightLeak:
    """Two or three big warm glows drifting slowly across the frame."""

    def __init__(self, w: int, h: int, seed: int):
        import random

        rnd = random.Random(seed)
        self.blobs = [(rnd.uniform(-0.3, 1.3), rnd.uniform(-0.2, 1.2), rnd.uniform(-0.05, 0.05), rnd.uniform(-0.03, 0.03),
                       rnd.uniform(0.35, 0.6), rnd.choice([(1.0, 0.45, 0.15), (1.0, 0.25, 0.35), (1.0, 0.7, 0.3),
                                                          (0.5, 0.35, 1.0)])) for _ in range(rnd.randint(2, 3))]
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
        return out * 0.38


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

def render_shot(image: Path, length: float, out: Path, *, size: tuple[int, int] = (WIDTH, HEIGHT),
                motion: str = "push_in", effects: tuple[str, ...] | list[str] = (), beats: list[float] = (),
                voice: Path | None = None, look: str = "", seed: int = 0, parallax: float = 1.0,
                tape: str = "", wear: float = 0.0, frame: str = "full", stamp: str = "", fade: bool = False,
                impacts: list[float] = (), cuts: list[float] = (), focus: tuple[float, float] | None = None) -> None:
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
    src = torch.from_numpy(np.array(pic)).to(dev).permute(2, 0, 1)[None].to(half) / 255.0
    sh, sw = src.shape[-2:]

    # cover-fit: the part of the picture (in its -1..1 grid units) the frame shows at zoom 1
    frame_aspect, pic_aspect = W / H, sw / sh
    fx, fy = (frame_aspect / pic_aspect, 1.0) if pic_aspect > frame_aspect else (1.0, pic_aspect / frame_aspect)
    room_x, room_y = 1 - fx, 1 - fy
    ys, xs = torch.meshgrid(torch.linspace(-1, 1, H, device=dev, dtype=half),
                            torch.linspace(-1, 1, W, device=dev, dtype=half), indexing="ij")
    motion = motion if motion in MOTIONS else "push_in"
    depth = None
    tape = tape if tape in TAPES else ""
    if (motion.endswith("_3d") and parallax > 0) or fade:
        try:
            depth = depth_map(image).to(half)
        except Exception as e:  # no depth model (offline): the move still happens, just flat
            print(f"  ! depth map unavailable ({type(e).__name__}); flat camera move")
    effects = set(effects)
    lw, lh = W // 4, H // 4
    particles = [_Particles(k, lw, lh, seed + i) for i, k in enumerate(PARTICLES) if k in effects]
    leak = _LightLeak(lw // 2, lh // 2, seed) if "light_leak" in effects else None
    trails = _LightTrails(lw, lh, seed) if "light_trails" in effects else None
    vignette = None
    if "vignette" in effects:
        r = torch.sqrt((xs.float() * (W / max(W, H))) ** 2 + (ys.float() * (H / max(W, H))) ** 2)
        vignette = (1 - 0.42 * ((r - 0.35) / 0.75).clamp(0, 1) ** 1.6).to(half)[None, None]
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
    prev = None

    frames = max(round(length * FPS), 1)
    grade = "eq=brightness=-0.03:saturation=1.04,"  # a touch darker, so white captions always read
    if look:
        from .styles import look_filter

        grade = look_filter(look) + ","
    audio_in = ["-i", str(voice)] if voice else ["-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo"]
    log = out.with_suffix(".ffmpeg.log")
    with open(log, "w", encoding="utf-8", errors="replace") as err:
        proc = subprocess.Popen(
            ["ffmpeg", "-y", "-hide_banner", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{OW}x{OH}", "-r", str(FPS),
             "-i", "-", *audio_in, "-filter_complex", f"[0:v]{grade}setsar=1,format=yuv420p[v];[1:a]aresample=44100,apad[a]",
             "-map", "[v]", "-map", "[a]", "-t", f"{length:.3f}", "-c:v", "libx264", "-preset", "veryfast", "-crf", "18",
             "-c:a", "aac", "-b:a", "192k", "-ar", "44100", "-ac", "2", str(out)],
            stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=err)
        try:
            with torch.no_grad():
                for n in range(frames):
                    t = n / FPS
                    p = n / max(frames - 1, 1)
                    since = [t - b for b in beats if t >= b]
                    hit = math.exp(-min(since) * 9) if since else 0.0  # 1 on the beat, fading over ~0.3 s
                    if prev is not None and skip and deck.rnd.random() < skip:
                        proc.stdin.write(prev)  # the tape skips: the last frame again
                        continue
                    if tape == "rewind":  # the move plays backwards, fast, over and over
                        p = 1 - (t * 1.6 / max(length, 0.5) + hit * 0.04) % 1.0
                    zoom, cx, cy, par = _camera(motion, p, room_x, room_y)
                    zoom *= 1 + 0.035 * hit
                    # cut to the next framing of the picture (each holds until the next cut)
                    if cuts:
                        fz, pull = FRAMINGS[sum(1 for c in cuts if t >= c) % len(FRAMINGS)]
                        zoom *= fz
                        cx += (focus[0] - cx) * pull
                        cy += (focus[1] - cy) * pull
                    since_hit = [t - b for b in impacts if t >= b]
                    strike = math.exp(-min(since_hit) * 7) if since_hit else 0.0  # 1 on the hit, gone in ~0.4 s
                    if strike > 0.01:
                        zoom *= 1 + 0.11 * strike
                        cx += 0.035 * strike * math.sin(t * 91 + 1.3) / zoom  # shake
                        cy += 0.03 * strike * math.sin(t * 73) / zoom
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
                        small = F.avg_pool2d(frame, 4)
                        bright = ((small - 0.62).clamp(min=0) * 2.2)
                        bloom = F.interpolate(_blur(bright, 6), size=(H, W), mode="bilinear", align_corners=False)
                        frame = _screen(frame, bloom * 0.75)
                    if leak is not None:
                        frame = _screen(frame, F.interpolate(leak.layer(t)[None].to(half), size=(H, W), mode="bilinear",
                                                             align_corners=False))
                    if trails is not None:
                        streaks = F.interpolate(trails.layer(t)[None].to(half), size=(H, W), mode="bilinear", align_corners=False)
                        frame = _screen(frame, streaks + _blur(streaks, 6) * 0.6)  # a soft glow around each streak
                    for pt in particles:
                        frame = _screen(frame, F.interpolate(pt.layer(t)[None].to(half), size=(H, W), mode="bilinear",
                                                             align_corners=False))
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
                    if "grain" in effects:
                        frame = frame + torch.randn(1, 1, H // 2, W // 2, device=dev, dtype=half).repeat_interleave(
                            2, -1).repeat_interleave(2, -2) * 0.028
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
    base = {"anime": ["glow", "light_leak", "grain", "vignette"], "cinematic": ["grain", "vignette", "light_leak"],
            "flat": ["grain"]}.get(style, ["vignette"])
    return base + (["chromatic"] if music and style != "flat" else [])
