"""Sound effects, synthesized (no downloads, no licences): a hit with a low boom and a sharp crack, a whoosh that
swells into it, thunder, and short ambience beds (rain, wind, water, birds) for a planned shot's sound notes. Made once
into the cache, then mixed under the voice by finalize()."""
import math
import wave
from pathlib import Path

from .config import CACHE_DIR, CODE_DIR

RATE = 44100
SFX_DIR = CACHE_DIR / "sfx"
# the desktop app's engine has no numpy (it comes with the AI add-on), so its build ships every sound made in advance
BUNDLED_DIR = CODE_DIR / "sfx"
VERSION = 1  # bump when the sounds change, so the cached files are made again
WHOOSH_LEAD = 0.32  # the whoosh ends this many seconds after it starts: it is placed to land on the hit


def _write(path: Path, samples, level: float = 0.89) -> Path:
    import numpy as np

    peak = float(np.abs(samples).max()) or 1.0
    pcm = (samples / peak * level * 32767).astype("<i2")
    stereo = np.repeat(pcm[:, None], 2, axis=1)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".part")
    with wave.open(str(tmp), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(stereo.tobytes())
    tmp.replace(path)
    return path


def _lowpass(x, cutoff):
    """One-pole low-pass; `cutoff` in Hz, a number or one value per sample (a sweep)."""
    import numpy as np

    cut = np.broadcast_to(np.asarray(cutoff, dtype=float), x.shape)
    a = 1 - np.exp(-2 * math.pi * cut / RATE)
    y = np.empty_like(x)
    acc = 0.0
    for i in range(len(x)):
        acc += a[i] * (x[i] - acc)
        y[i] = acc
    return y


def _impact():
    import numpy as np

    rng = np.random.default_rng(7)
    n = int(RATE * 0.9)
    t = np.arange(n) / RATE
    # boom: a sine that drops from 110 to 42 Hz, the "weight" of the hit
    freq = 42 + 68 * np.exp(-t * 9)
    boom = np.sin(2 * math.pi * np.cumsum(freq) / RATE) * np.exp(-t * 5.5)
    # body: a short burst of filtered noise, the "thud"
    body = _lowpass(rng.standard_normal(n), 900) * np.exp(-t * 22) * 2.2
    # crack: the first few milliseconds, bright (a crude high-pass: noise minus its low-passed copy)
    noise = rng.standard_normal(n)
    crack = (noise - _lowpass(noise, 2500)) * np.exp(-t * 70) * 0.9
    return boom * 1.0 + body + crack


def _whoosh():
    import numpy as np

    rng = np.random.default_rng(3)
    n = int(RATE * (WHOOSH_LEAD + 0.08))
    t = np.arange(n) / RATE
    p = t / WHOOSH_LEAD
    env = np.where(p < 1, p ** 2.2, np.exp(-(t - WHOOSH_LEAD) * 40))  # swells, then stops on the hit
    sweep = 300 + 3200 * np.clip(p, 0, 1) ** 2  # the air gets brighter as it rushes in
    return _lowpass(rng.standard_normal(n), sweep) * env


def _thunder():
    import numpy as np

    rng = np.random.default_rng(11)
    n = int(RATE * 3.6)
    t = np.arange(n) / RATE
    # crack: a bright burst, then a second strike a moment later (lightning rarely hits just once)
    noise = rng.standard_normal(n)
    bright = noise - _lowpass(noise, 1800)
    crack = bright * (np.exp(-t * 30) + 0.6 * np.where(t > 0.11, np.exp(-(t - 0.11) * 26), 0))
    # rumble: low noise that rolls (slow swells) and dies away over a few seconds
    roll = 0.65 + 0.35 * np.sin(2 * math.pi * 1.7 * t + 0.4) * np.sin(2 * math.pi * 0.6 * t + 1.1)
    rumble = _lowpass(_lowpass(rng.standard_normal(n), 160), 220) * 9 * roll * np.exp(-t * 1.1) \
        * np.clip(t / 0.08, 0, 1)
    return crack * 1.1 + rumble


# shortcut: a bed is a fixed length, not the shot's; it fades out over the next shot when that comes sooner. Make it
# per-shot (sound(name, seconds)) if long held shots need ambience all the way through.
AMBIENT_SEC = 5.0
AMBIENT_LEVEL = 0.3  # peak of a bed against a hit's 0.89: ambience sits well under the voice


def _bed(x):
    """Ambience fading in over 0.4 s and out over the last 1.5 s."""
    import numpy as np

    t = np.arange(len(x)) / RATE
    return x * np.clip(t / 0.4, 0, 1) * np.clip((AMBIENT_SEC - t) / 1.5, 0, 1)


def _rain():
    import numpy as np

    rng = np.random.default_rng(21)
    n = int(RATE * AMBIENT_SEC)
    noise = rng.standard_normal(n)
    hiss = _lowpass(noise, 7000) - _lowpass(noise, 500)  # the steady wash of rain
    drops = np.zeros(n)
    at = rng.integers(0, n - 2000, 260)
    drops[at] = rng.uniform(0.5, 1.0, at.size) * 14
    tick = np.exp(-np.arange(400) / RATE * 900)  # each drop a short bright tick
    drops = np.convolve(drops - _lowpass(drops, 1500), tick)[:n]
    return _bed(hiss + drops * 0.35)


def _wind():
    import numpy as np

    rng = np.random.default_rng(5)
    n = int(RATE * AMBIENT_SEC)
    t = np.arange(n) / RATE
    gust = 0.55 + 0.45 * np.sin(2 * math.pi * 0.23 * t + 0.7) * np.sin(2 * math.pi * 0.11 * t + 2.0)
    howl = _lowpass(rng.standard_normal(n), 250 + 650 * gust)  # brighter as the gust picks up
    return _bed(howl * gust)


def _water():
    import numpy as np

    rng = np.random.default_rng(13)
    n = int(RATE * AMBIENT_SEC)
    noise = rng.standard_normal(n)
    flow = _lowpass(noise, 2600) - _lowpass(noise, 250)
    burble = np.abs(_lowpass(rng.standard_normal(n), 9))  # a stream's uneven bubbling
    return _bed(flow * (0.35 + burble / burble.max()))


def _birds():
    import numpy as np

    rng = np.random.default_rng(17)
    n = int(RATE * AMBIENT_SEC)
    out = np.zeros(n)
    k = 0
    while k < 40:  # chirps in little phrases: a high sine swept down or up, each 50-110 ms
        start = rng.uniform(0.2, AMBIENT_SEC - 1.8)
        base, step = rng.uniform(2600, 4200), rng.choice([-1, 1]) * rng.uniform(600, 1500)
        for j in range(int(rng.integers(2, 5))):
            m = int(RATE * rng.uniform(0.05, 0.11))
            t = np.arange(m) / RATE
            freq = base + step * t / t[-1]
            chirp = np.sin(2 * math.pi * np.cumsum(freq) / RATE) * np.sin(math.pi * t / t[-1]) ** 2
            i = int((start + j * 0.14) * RATE)
            out[i:i + m] += chirp * rng.uniform(0.4, 1.0)
            k += 1
    noise = rng.standard_normal(n)
    return _bed(out + (_lowpass(noise, 3000) - _lowpass(noise, 600)) * 0.04)  # a faint outdoor air under them


SOUNDS = {"impact": _impact, "whoosh": _whoosh, "thunder": _thunder,
          "rain": _rain, "wind": _wind, "water": _water, "birds": _birds}
AMBIENT = {"rain", "wind", "water", "birds"}


def sound(name: str) -> Path:
    """The cached .wav of a sound effect (made on first use)."""
    path = SFX_DIR / f"{name}-v{VERSION}.wav"
    if not path.exists():
        if (BUNDLED_DIR / path.name).is_file():
            return BUNDLED_DIR / path.name
        _write(path, SOUNDS[name](), AMBIENT_LEVEL if name in AMBIENT else 0.89)
    return path


def make_all(folder: Path) -> None:
    """Every sound into `folder` (scripts/build_engine.py bundles them)."""
    for name in SOUNDS:
        _write(folder / f"{name}-v{VERSION}.wav", SOUNDS[name](), AMBIENT_LEVEL if name in AMBIENT else 0.89)


def impact_track(times: list[float]) -> list[tuple[Path, float, float]]:
    """(sound file, start second, volume) for hits at `times`: each gets a whoosh leading into it and the impact on
    it. The first (the hook's) hits hardest."""
    out = []
    for k, t in enumerate(sorted(times)):
        loud = 1.0 if k == 0 else 0.6
        if t >= WHOOSH_LEAD:
            out.append((sound("whoosh"), t - WHOOSH_LEAD, 0.45 * loud))
        out.append((sound("impact"), t, loud))
    return out
