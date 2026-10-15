"""Sound effects for a short's impact moments, synthesized (no downloads, no licences): a hit with a low boom and a
sharp crack, and a whoosh that swells into it. Made once into the cache, then mixed under the voice by finalize()."""
import math
import wave
from pathlib import Path

from .config import CACHE_DIR

RATE = 44100
SFX_DIR = CACHE_DIR / "sfx"
VERSION = 1  # bump when the sounds change, so the cached files are made again
WHOOSH_LEAD = 0.32  # the whoosh ends this many seconds after it starts: it is placed to land on the hit


def _write(path: Path, samples) -> Path:
    import numpy as np

    peak = float(np.abs(samples).max()) or 1.0
    pcm = (samples / peak * 0.89 * 32767).astype("<i2")
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


SOUNDS = {"impact": _impact, "whoosh": _whoosh}


def sound(name: str) -> Path:
    """The cached .wav of a sound effect (made on first use)."""
    path = SFX_DIR / f"{name}-v{VERSION}.wav"
    if not path.exists():
        _write(path, SOUNDS[name]())
    return path


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
