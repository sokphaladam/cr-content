"""Animated SVG -> seamless looping video clip.

resvg only draws still pictures, so the SMIL animation in Gemini's SVG (<animate>, <animateTransform>, <set>) is
played here: for every frame each animated attribute is computed at that moment and written into a static copy of
the SVG, which resvg rasterizes (in worker processes: resvg holds the GIL). FFmpeg then joins the frames, adding
moving film grain, which would be far too slow to draw per frame with feTurbulence.

Every repeating animation's duration is snapped to a whole fraction of the loop, so the clip loops without a jump.
"""
import os
import re
import shutil
import subprocess
import tempfile
import time
import xml.etree.ElementTree as ET
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path

from .config import FPS

SVG_NS = "http://www.w3.org/2000/svg"
XLINK_NS = "http://www.w3.org/1999/xlink"
ET.register_namespace("", SVG_NS)
ET.register_namespace("xlink", XLINK_NS)

ANIMATIONS = {"animate", "animateTransform", "animateColor", "set"}
UNSUPPORTED = {"animateMotion", "discard"}
_NUM = re.compile(r"[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?")


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _clock(value: str | None) -> float | None:
    """A SMIL clock value ("2s", "500ms", "1.5", "0:01.5") in seconds; None for "indefinite", events, or junk."""
    if not value:
        return None
    value = value.split(";")[0].strip()
    m = re.fullmatch(r"([-+]?[\d.]+)\s*(ms|s|min|h)?", value)
    if m:
        try:
            return float(m.group(1)) * {"ms": 0.001, "s": 1, "min": 60, "h": 3600, None: 1}[m.group(2)]
        except ValueError:
            return None
    m = re.fullmatch(r"(?:(\d+):)?(\d+):([\d.]+)", value)
    if m:
        return int(m.group(1) or 0) * 3600 + int(m.group(2)) * 60 + float(m.group(3))
    return None


def _rgb(value: str) -> tuple[float, float, float] | None:
    v = value.strip().lower()
    if re.fullmatch(r"#[0-9a-f]{3}", v):
        return tuple(int(c * 2, 16) for c in v[1:])
    if re.fullmatch(r"#[0-9a-f]{6}", v):
        return tuple(int(v[i:i + 2], 16) for i in (1, 3, 5))
    m = re.fullmatch(r"rgb\(\s*([\d.]+)\s*,\s*([\d.]+)\s*,\s*([\d.]+)\s*\)", v)
    return tuple(float(x) for x in m.groups()) if m else None


def _fmt(x: float) -> str:
    return f"{x:.3f}".rstrip("0").rstrip(".") if x != int(x) else str(int(x))


def _lerp(a: str, b: str, f: float) -> str:
    """Between two attribute values: colours blend, numbers (alone or inside lists, paths, matrices) interpolate
    when both values have the same shape; anything else switches halfway."""
    ca, cb = _rgb(a), _rgb(b)
    if ca and cb:
        return "#" + "".join(f"{round(x + (y - x) * f):02x}" for x, y in zip(ca, cb))
    na, nb = _NUM.findall(a), _NUM.findall(b)
    if na and len(na) == len(nb) and _NUM.split(a) == _NUM.split(b):
        out = iter(_fmt(float(x) + (float(y) - float(x)) * f) for x, y in zip(na, nb))
        return _NUM.sub(lambda _: next(out), a)
    return a if f < 0.5 else b


def _bezier(x1: float, y1: float, x2: float, y2: float, x: float) -> float:
    """Cubic-bezier easing (keySplines): y for x, by bisection on the curve's x."""
    lo, hi = 0.0, 1.0
    for _ in range(30):
        t = (lo + hi) / 2
        bx = 3 * (1 - t) ** 2 * t * x1 + 3 * (1 - t) * t ** 2 * x2 + t ** 3
        lo, hi = (t, hi) if bx < x else (lo, t)
    t = (lo + hi) / 2
    return 3 * (1 - t) ** 2 * t * y1 + 3 * (1 - t) * t ** 2 * y2 + t ** 3


@dataclass
class Animation:
    target: ET.Element
    attr: str
    values: list[str]
    begin: float
    dur: float | None  # None: holds its first value forever (a <set> without dur)
    repeat: float  # float("inf") for indefinite
    freeze: bool
    mode: str = "linear"
    key_times: list[float] = field(default_factory=list)
    splines: list[tuple[float, ...]] = field(default_factory=list)
    transform: str = ""  # animateTransform's type
    additive: bool = False

    def value(self, t: float) -> str | None:
        """The value at time `t`, or None when the animation isn't active (the base value shows)."""
        if self.dur is None:
            return self.values[0] if t >= self.begin else None
        local = t - self.begin
        if self.repeat == float("inf"):
            # looping forever: as if it had always been running, so a positive begin doesn't break the loop
            return self._at((local % self.dur) / self.dur)
        if local < 0:
            return None
        if local >= self.dur * self.repeat:
            return self._at(1.0) if self.freeze else None
        return self._at((local % self.dur) / self.dur)

    def _at(self, p: float) -> str:
        vals = self.values
        if len(vals) == 1:
            return vals[0]
        n = len(vals)
        kt = self.key_times if len(self.key_times) == n else (
            [i / n for i in range(n)] if self.mode == "discrete" else [i / (n - 1) for i in range(n)])
        if self.mode == "discrete":
            return next(vals[i] for i in range(n - 1, -1, -1) if kt[i] <= p or i == 0)
        if p >= kt[-1]:
            return vals[-1]
        i = max(j for j in range(n - 1) if kt[j] <= p)
        span = kt[i + 1] - kt[i]
        f = (p - kt[i]) / span if span > 0 else 1.0
        if self.mode == "spline" and i < len(self.splines):
            f = _bezier(*self.splines[i], f)
        return _lerp(vals[i], vals[i + 1], f)


class Player:
    """An animated SVG that can be read out as a still SVG at any moment."""

    def __init__(self, svg: str, loop: float):
        try:
            self.root = ET.fromstring(svg)
        except ET.ParseError as e:
            raise RuntimeError(f"Gemini's animated SVG isn't valid XML: {e}") from e
        parents = {child: parent for parent in self.root.iter() for child in parent}
        ids = {el.get("id"): el for el in self.root.iter() if el.get("id")}
        self.animations: list[Animation] = []
        for el in list(self.root.iter()):
            name = _local(el.tag)
            if name in UNSUPPORTED:
                parents[el].remove(el)
            if name not in ANIMATIONS:
                continue
            parents[el].remove(el)
            href = el.get("href") or el.get(f"{{{XLINK_NS}}}href") or ""
            target = ids.get(href[1:]) if href.startswith("#") else parents[el]
            anim = self._parse(el, name, target, loop)
            if anim:
                self.animations.append(anim)
        # an attribute repeated inside style="" would win over the animated presentation attribute
        for target in {id(a.target): a.target for a in self.animations}.values():
            style = target.get("style")
            if not style:
                continue
            animated = {a.attr for a in self.animations if a.target is target}
            keep = []
            for decl in style.split(";"):
                prop, _, val = decl.partition(":")
                if prop.strip() in animated:
                    target.set(prop.strip(), val.strip())
                elif decl.strip():
                    keep.append(decl.strip())
            target.set("style", ";".join(keep))
        # the default filter region (10% around the shape) cuts soft glows off in a hard square, worse once they move
        for f in self.root.iter(f"{{{SVG_NS}}}filter"):
            if not any(f.get(k) for k in ("x", "y", "width", "height")) and f.get("filterUnits") != "userSpaceOnUse":
                f.attrib.update(x="-50%", y="-50%", width="200%", height="200%")
        self.base = [(a.target, a.attr, a.target.get(a.attr)) for a in self.animations]

    @staticmethod
    def _parse(el: ET.Element, name: str, target: ET.Element | None, loop: float) -> Animation | None:
        attr = el.get("attributeName") or ("transform" if name == "animateTransform" else "")
        if target is None or not attr or ":" in attr:
            return None
        base = target.get(attr) or ""
        if el.get("values"):
            values = [v.strip() for v in el.get("values").split(";") if v.strip()]
        elif name == "set":
            values = [el.get("to", "")]
        elif el.get("to") is not None:
            values = [el.get("from", base), el.get("to")]
        elif _NUM.fullmatch(el.get("by", "").strip()) and _NUM.fullmatch(el.get("from", base).strip()):
            start = float(el.get("from", base))
            values = [_fmt(start), _fmt(start + float(el.get("by")))]
        else:
            return None
        if not values or (name != "animateTransform" and not all(values)):
            return None
        dur = _clock(el.get("dur"))
        rc = el.get("repeatCount", "")
        repeat = float("inf") if rc == "indefinite" or el.get("repeatDur") == "indefinite" else (
            float(rc) if re.fullmatch(r"[\d.]+", rc) else 1.0)
        if dur is None or dur <= 0:
            if name != "set":
                return None  # SMIL: an animation without a duration does nothing
            dur, repeat = None, 1.0
        elif repeat == float("inf"):
            # snap to the nearest whole fraction of the loop so the clip comes back to its first frame
            dur = loop / max(1, round(loop / dur))
        splines = []
        for s in (el.get("keySplines") or "").split(";"):
            nums = [float(x) for x in _NUM.findall(s)]
            if len(nums) == 4:
                splines.append(tuple(nums))
        key_times = [float(x) for x in _NUM.findall(el.get("keyTimes") or "")]
        return Animation(
            target=target, attr=attr, values=values, begin=_clock(el.get("begin")) or 0.0, dur=dur, repeat=repeat,
            freeze=el.get("fill") == "freeze", mode=el.get("calcMode") or ("discrete" if name == "set" else "linear"),
            key_times=key_times, splines=splines, transform=el.get("type") or "translate",
            additive=el.get("additive") == "sum")

    def frame(self, t: float) -> str:
        """The SVG as it looks at `t` seconds, with no animation left in it."""
        for target, attr, value in self.base:
            if value is None:
                target.attrib.pop(attr, None)
            else:
                target.set(attr, value)
        for anim in self.animations:
            value = anim.value(t)
            if value is None:
                continue
            if anim.attr == "transform" and anim.transform:
                step = f"{anim.transform}({value})"
                current = anim.target.get("transform") or ""
                anim.target.set("transform", f"{current} {step}".strip() if anim.additive else step)
            else:
                anim.target.set(anim.attr, value)
        return ET.tostring(self.root, encoding="unicode")


def _render_frame(job: tuple[str, int, int, str]) -> None:
    import resvg_py

    svg, w, h, out = job
    png = resvg_py.svg_to_bytes(svg_string=svg, width=w, height=h, skip_system_fonts=True)
    Path(out).write_bytes(bytes(png))


def render_loop(svg: str, size: tuple[int, int], out: Path, loop: float = 6.0, fps: int = FPS,
                grain: int = 4, budget: float = 90.0, log=print) -> Path:
    """Play the animated `svg` for `loop` seconds at `size` and write it to `out` as an mp4 that loops seamlessly.

    Heavy designs (big blurs) can take seconds per frame: when the first frame says the whole clip would take more
    than `budget` seconds, frames are drawn smaller (down to half size) and scaled up, which soft artwork hides."""
    player = Player(svg, loop)
    if not player.animations:
        raise RuntimeError("Gemini's design came back without any animation. Try again.")
    W, H = size
    count = round(loop * fps)
    workers = max(1, min((os.cpu_count() or 2) - 2, 10))
    tmp = Path(tempfile.mkdtemp(prefix="motion-", dir=out.parent if out.parent.exists() else None))
    try:
        frames = [player.frame(i / fps) for i in range(count)]
        started = time.perf_counter()
        _render_frame((frames[0], W, H, str(tmp / "f00000.png")))
        # cores share memory bandwidth: count on about half of them really working in parallel
        estimate = (time.perf_counter() - started) * count / max(1, workers / 2)
        scale = max(0.5, min(1.0, (budget / estimate) ** 0.5)) if estimate > budget else 1.0
        w, h = (W, H) if scale == 1 else (round(W * scale / 2) * 2, round(H * scale / 2) * 2)
        jobs = [(f, w, h, str(tmp / f"f{i:05d}.png")) for i, f in enumerate(frames) if i or scale != 1]
        log(f"      animating {len(player.animations)} properties: {count} frames at {w}x{h} on {workers} cores")
        with ProcessPoolExecutor(max_workers=workers) as pool:
            list(pool.map(_render_frame, jobs, chunksize=4))
        vf = (f"scale={W}:{H}:flags=lanczos," if (w, h) != (W, H) else "") + (
            f"noise=alls={grain}:allf=t,format=yuv420p" if grain else "format=yuv420p")
        out.parent.mkdir(parents=True, exist_ok=True)
        proc = subprocess.run(
            ["ffmpeg", "-v", "error", "-y", "-framerate", str(fps), "-i", str(tmp / "f%05d.png"), "-vf", vf,
             "-c:v", "libx264", "-preset", "medium", "-crf", "22", "-movflags", "+faststart", str(out)],
            stdin=subprocess.DEVNULL, capture_output=True, text=True, encoding="utf-8", errors="replace")
        if proc.returncode != 0:
            raise RuntimeError(f"ffmpeg couldn't encode the animation: {proc.stderr[-800:]}")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return out
