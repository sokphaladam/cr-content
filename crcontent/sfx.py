"""Sound effects, synthesized (no downloads, no licences): a hit with a low boom and a sharp crack, a whoosh that
swells into it, thunder, and short ambience beds (rain, wind, water, birds) for a planned shot's sound notes. Made once
into the cache, then mixed under the voice by finalize()."""
import json
import math
import re
import wave
from pathlib import Path

from .config import ASSETS_DIR, CACHE_DIR, CODE_DIR

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


def _riser():
    """A build into a moment: noise and a tone that rise for 2 s, then stop."""
    import numpy as np

    rng = np.random.default_rng(5)
    n = int(RATE * 2.0)
    t = np.arange(n) / RATE
    p = t / t[-1]
    tone = np.sin(2 * math.pi * np.cumsum(180 + 900 * p ** 2) / RATE) * 0.35
    air = _lowpass(rng.standard_normal(n), 400 + 5000 * p ** 2) * 0.8
    return (tone + air) * p ** 2.5 * np.clip((t[-1] - t) / 0.03, 0, 1)


def _drone():
    """Suspense under a scene: a low, slowly beating chord, faded in and out (4 s)."""
    import numpy as np

    n = int(RATE * 4.0)
    t = np.arange(n) / RATE
    chord = sum(np.sin(2 * math.pi * f * t) * a for f, a in ((55, 1.0), (55.6, 0.8), (82.4, 0.5), (110.3, 0.25)))
    swell = 0.75 + 0.25 * np.sin(2 * math.pi * 0.35 * t)
    return chord * swell * np.clip(t / 0.8, 0, 1) * np.clip((t[-1] - t) / 1.2, 0, 1)


def _pulse():
    """A heartbeat-like pulse: three low double thumps (2.4 s)."""
    import numpy as np

    n = int(RATE * 2.4)
    t = np.arange(n) / RATE
    out = np.zeros(n)
    for beat in (0.0, 0.8, 1.6):
        for k, at in enumerate((beat, beat + 0.24)):
            d = np.clip(t - at, 0, None)
            out += np.where(t >= at, np.sin(2 * math.pi * (52 + 30 * np.exp(-d * 30)) * d) * np.exp(-d * 18)
                            * np.clip(d / 0.004, 0, 1), 0) * (1 if k == 0 else 0.7)  # a 4 ms attack: no click
    return out


def _chime():
    """A reveal: a soft bell (1.6 s), bright partials that ring out."""
    import numpy as np

    n = int(RATE * 1.6)
    t = np.arange(n) / RATE
    bell = sum(np.sin(2 * math.pi * f * t) * a * np.exp(-t * d) for f, a, d in
               ((880, 1.0, 2.6), (1318.5, 0.55, 3.4), (2217, 0.3, 5.0), (3520, 0.12, 7.0)))
    return bell * np.clip(t / 0.004, 0, 1)


def _flap():
    """Wings: four soft, airy flaps (1.2 s), for a bird or bat taking off on screen."""
    import numpy as np

    rng = np.random.default_rng(13)
    n = int(RATE * 1.2)
    t = np.arange(n) / RATE
    env = np.zeros(n)
    for k, at in enumerate((0.05, 0.31, 0.56, 0.8)):
        d = t - at
        env += np.where(d >= 0, np.sin(np.clip(d / 0.16, 0, 1) * math.pi) ** 2, 0) * (1 - 0.15 * k)
    return _lowpass(rng.standard_normal(n), 1400) * env


SOUNDS = {"impact": _impact, "whoosh": _whoosh, "thunder": _thunder,
          "rain": _rain, "wind": _wind, "water": _water, "birds": _birds,
          "riser": _riser, "drone": _drone, "pulse": _pulse, "chime": _chime, "flap": _flap}
AMBIENT = {"rain", "wind", "water", "birds"}
QUIET = {"drone": 0.4}  # peak of a bed that sits under the voice (ambience: AMBIENT_LEVEL)

# the sound library (roadmap 12.1): what each sound is for, so the editor and the AI pick by purpose
CATEGORIES = ("impact", "transition", "suspense", "ambience", "action", "reveal")
INFO = {
    "impact": ("impact", "A low boom with a sharp crack: an important reveal or visual hit."),
    "thunder": ("impact", "A double strike and a long rolling rumble."),
    "whoosh": ("transition", "Rushing air that lands on a cut or a hit."),
    "riser": ("transition", "A 2 s build that stops dead: into a reveal or a cut."),
    "drone": ("suspense", "A low, slowly beating chord under a tense scene."),
    "pulse": ("suspense", "Three heartbeat-like thumps: anticipation."),
    "rain": ("ambience", "Rain on leaves and ground."),
    "wind": ("ambience", "Wind gusting through an open place."),
    "water": ("ambience", "A stream or gentle surf."),
    "birds": ("ambience", "Birdsong over quiet outdoor air."),
    "flap": ("action", "Wings flapping: only when a bird or bat is seen taking off."),
    "chime": ("reveal", "A soft bell for a payoff or discovery."),
}
SYNTH_LICENCE = "Synthesized by the app (no licence needed)"


def sound(name: str) -> Path:
    """The file of a sound effect: a synthesized one (cached .wav, made on first use) or an imported "user:<id>".
    Raises KeyError for one that doesn't exist (an imported sound deleted from the library)."""
    if name.startswith("user:"):
        return _user_file(name[5:])
    path = SFX_DIR / f"{name}-v{VERSION}.wav"
    if not path.exists():
        if (BUNDLED_DIR / path.name).is_file():
            return BUNDLED_DIR / path.name
        _write(path, SOUNDS[name](), AMBIENT_LEVEL if name in AMBIENT else QUIET.get(name, 0.89))
    return path


def exists(name: str) -> bool:
    try:
        return sound(name).is_file()
    except KeyError:
        return False


# ---------- imported sounds: <data folder>/assets/sfx/<id>.<ext> with <id>.json (category, licence, credit) ----------

USER_DIR = ASSETS_DIR / "sfx"
AUDIO_EXTS = {".wav", ".mp3", ".ogg", ".flac", ".m4a"}
LICENCES = ("CC0 / public domain", "CC BY", "CC BY-SA", "Royalty-free (bought or subscribed)", "My own recording")
NEEDS_CREDIT = {"CC BY", "CC BY-SA"}


def _user_file(sid: str) -> Path:
    if not re.fullmatch(r"[a-z0-9-]{1,40}", sid):
        raise KeyError(sid)
    found = [f for f in USER_DIR.glob(f"{sid}.*") if f.suffix.lower() in AUDIO_EXTS]
    if not found:
        raise KeyError(sid)
    return found[0]


def user_info(sid: str) -> dict | None:
    try:
        return json.loads((USER_DIR / f"{sid}.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def catalog(duration) -> list[dict]:
    """Every sound the timeline can use: the synthesized ones, then the imported ones with their licence and credit.
    `duration(path)`: seconds of a file (render.duration)."""
    out = [{"name": n, "label": n, "category": INFO[n][0], "description": INFO[n][1], "ambient": n in AMBIENT,
            "duration": round(duration(sound(n)), 2), "source": "synthesized", "licence": SYNTH_LICENCE, "credit": ""}
           for n in SOUNDS]
    for meta in sorted(USER_DIR.glob("*.json")) if USER_DIR.is_dir() else []:
        info = user_info(meta.stem)
        if info and exists(f"user:{meta.stem}"):
            out.append({"name": f"user:{meta.stem}", "label": info.get("label") or meta.stem, "category": info.get("category", "action"),
                        "description": info.get("description", ""), "ambient": info.get("category") == "ambience",
                        "duration": info.get("duration", 0), "source": info.get("source", ""), "licence": info.get("licence", ""),
                        "credit": info.get("credit", "")})
    return out


def credits(names) -> list[str]:
    """The description lines imported sounds' licences ask for (one per sound, in order of first use)."""
    out = []
    for name in dict.fromkeys(names):
        info = user_info(name[5:]) if name.startswith("user:") else None
        if info and info.get("licence") in NEEDS_CREDIT and info.get("credit"):
            out.append(f"Sound: {info['credit']} ({info['licence']}){' ' + info['source'] if info.get('source') else ''}")
    return out


def make_all(folder: Path) -> None:
    """Every sound into `folder` (scripts/build_engine.py bundles them)."""
    for name in SOUNDS:
        _write(folder / f"{name}-v{VERSION}.wav", SOUNDS[name](), AMBIENT_LEVEL if name in AMBIENT else QUIET.get(name, 0.89))


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
