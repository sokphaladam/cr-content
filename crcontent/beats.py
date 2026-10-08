"""Beat detection and beat-synced shot planning for music videos."""
from dataclasses import dataclass

from .config import FPS
from .lyrics import SongScript

MIN_SHOT_SEC = 1.2


@dataclass
class Shot:
    section: int
    start: float  # seconds; frame-aligned so concatenated clips stay in sync with the song
    end: float

    @property
    def length(self) -> float:
        return self.end - self.start


def beat_times(audio, bpm: int, total: float, log=print) -> tuple[list[float], str]:
    """Beat positions in seconds, and the method used ('librosa' or 'grid' from the song's bpm)."""
    try:
        import librosa

        y, sr = librosa.load(str(audio), sr=22050, mono=True)
        _, beats = librosa.beat.beat_track(y=y, sr=sr, start_bpm=float(bpm or 120), units="time")
        if len(beats) >= 4:
            return [float(b) for b in beats], "librosa"
    except ImportError:
        log("      librosa isn't installed, so cuts follow the song's bpm (pip install -r requirements-music.txt)")
    except Exception as e:
        log(f"      ! beat detection failed ({e.__class__.__name__}); cuts follow the song's bpm")
    step = 60 / max(bpm or 120, 40)
    return [i * step for i in range(int(total / step) + 1)], "grid"


def _snap(t: float, beats: list[float], window: float) -> float:
    near = min(beats, key=lambda b: abs(b - t), default=t)
    return near if abs(near - t) <= window else t


def plan_shots(song: SongScript, spans: list[tuple[float, float]], beats: list[float], total: float) -> list[Shot]:
    """Cut on section boundaries plus every few beats inside them: every 4 beats in a chorus/hook, 8 elsewhere."""
    beat = 60 / max(song.bpm or 120, 40)
    cuts = {0.0, total}
    for i, (start, end) in enumerate(spans):
        name = song.sections[i].name.lower()
        every = beat * (4 if ("chorus" in name or "hook" in name or "drop" in name) else 8)
        every = max(MIN_SHOT_SEC * 1.5, min(6.0, every))
        cuts.add(_snap(start, beats, beat / 2))
        t = start + every
        while t < end - every / 2:
            cuts.add(_snap(t, beats, beat / 2))
            t += every

    # frame-align, drop cuts that would leave a too-short shot
    frames = sorted({round(min(max(c, 0.0), total) * FPS) for c in cuts})
    kept = [frames[0]]
    for f in frames[1:]:
        if (f - kept[-1]) / FPS >= MIN_SHOT_SEC:
            kept.append(f)
    end_frame = round(total * FPS)
    if kept[-1] != end_frame:
        if len(kept) > 1 and (end_frame - kept[-1]) / FPS < MIN_SHOT_SEC:
            kept[-1] = end_frame
        else:
            kept.append(end_frame)

    shots = []
    for a, b in zip(kept, kept[1:]):
        mid = (a + b) / 2 / FPS
        section = next((i for i, (s, e) in enumerate(spans) if s <= mid < e), len(spans) - 1)
        shots.append(Shot(section, a / FPS, b / FPS))
    return shots
