"""Step 1 — audio structure: beats, bars, sections (intro / verse / chorus / bridge...) and drops, scored per second.

allin1 (a music-structure model) is used when it's installed; it isn't on Windows (it needs NATTEN and madmom,
which have no Windows builds), so the usual path is librosa: beats and bars from the onsets, sections from the song's
own plan (song.json + lyric timing) or, for a song we know nothing about, from where the music repeats.
"""
import math
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

# section name (as written in song.json, or allin1's label) -> kind; checked in order, so "pre-chorus" wins
KINDS = [
    (("pre-chorus", "pre chorus", "prechorus", "pre-hook", "build"), "pre-chorus"),
    (("post-chorus", "post chorus", "postchorus"), "post-chorus"),
    (("chorus", "refrain"), "chorus"),
    (("hook",), "hook"),
    (("drop",), "drop"),
    (("bridge",), "bridge"),
    (("intro", "start"), "intro"),
    (("outro", "end", "fade"), "outro"),
    (("inst", "solo", "break", "interlude"), "instrumental"),
    (("verse",), "verse"),
]


def kind(name: str) -> str:
    n = name.lower()
    return next((k for keys, k in KINDS if any(key in n for key in keys)), "verse")


@dataclass
class Structure:
    duration: float
    bpm: float
    beats: list[float]
    bars: list[float]                 # downbeats: the first beat of every bar
    sections: list[dict]              # {"start", "end", "name", "kind"}
    drops: list[float]                # times where the energy jumps (a beat drop / the band kicks in)
    per_second: dict[str, list[float]] = field(default_factory=dict)  # section / energy / repetition / drop, 0..1
    method: str = "librosa"

    def section_at(self, t: float) -> dict | None:
        return next((s for s in self.sections if s["start"] <= t < s["end"]), self.sections[-1] if self.sections else None)

    def to_json(self) -> dict:
        return {"duration": round(self.duration, 3), "bpm": round(self.bpm, 1), "method": self.method,
                "beats": [round(b, 3) for b in self.beats], "bars": [round(b, 3) for b in self.bars],
                "sections": self.sections, "drops": [round(d, 2) for d in self.drops],
                "per_second": {k: [round(v, 3) for v in vals] for k, vals in self.per_second.items()}}


def _norm(x: np.ndarray, lo: float = 10, hi: float = 95) -> np.ndarray:
    """0..1 by percentiles (a few loud or quiet moments don't squash the rest)."""
    a, b = np.percentile(x, lo), np.percentile(x, hi)
    return np.clip((x - a) / (b - a), 0, 1) if b > a else np.zeros_like(x)


def _per_second(times: np.ndarray, values: np.ndarray, n: int) -> np.ndarray:
    """Mean of a curve sampled at `times` over each second 0..n-1."""
    out = np.zeros(n)
    idx = np.clip(times.astype(int), 0, n - 1)
    np.add.at(out, idx, values)
    count = np.bincount(idx, minlength=n)[:n]
    filled = count > 0
    out[filled] /= count[filled]
    if not filled.all() and filled.any():  # seconds without samples: interpolate
        secs = np.arange(n)
        out[~filled] = np.interp(secs[~filled], secs[filled], out[filled])
    return out


def _bars(beats: np.ndarray, beat_frames: np.ndarray, kick: np.ndarray, chroma: np.ndarray) -> np.ndarray:
    """Downbeats: of the 4 ways to group beats into bars (4/4), the one whose first beats have the most chord changes
    and the strongest kick. Chords decide most: four-on-the-floor dance music kicks on every beat. (Sung lines are no
    guide: they often start with a pickup before the bar.)"""
    if len(beats) < 8:
        return beats
    import librosa

    per_beat = librosa.util.sync(chroma, beat_frames, aggregate=np.median)[:, 1:]  # column k: beat k to k+1
    per_beat = per_beat / (np.linalg.norm(per_beat, axis=0, keepdims=True) + 1e-9)
    change = np.r_[0.0, 1 - (per_beat[:, 1:] * per_beat[:, :-1]).sum(axis=0)]
    hits = kick[np.clip(beat_frames, 0, len(kick) - 1)]
    scores = [change[p::4].mean() / (change.mean() + 1e-9) + 0.6 * hits[p::4].mean() / (hits.mean() + 1e-9)
              for p in range(4)]
    return beats[int(np.argmax(scores))::4]


def _allin1(audio: Path, log) -> dict | None:
    try:
        import allin1
    except ImportError:
        return None
    try:
        r = allin1.analyze(str(audio))
        return {"bpm": float(r.bpm or 0), "beats": [float(b) for b in r.beats], "bars": [float(b) for b in r.downbeats],
                "sections": [{"start": float(s.start), "end": float(s.end), "name": s.label, "kind": kind(s.label)}
                             for s in r.segments]}
    except Exception as e:  # a broken install falls back to librosa
        log(f"      ! allin1 failed ({e.__class__.__name__}: {e}); using librosa")
        return None


def _song_sections(song, lines: list, total: float) -> list[dict]:
    from ..align import section_spans, spans_from_lines

    spans = spans_from_lines(song, lines, total) if lines else section_spans(song, total)
    return [{"start": round(a, 2), "end": round(b, 2), "name": s.name, "kind": kind(s.name)}
            for s, (a, b) in zip(song.sections, spans) if b - a > 0.5]


def _guess_sections(features: np.ndarray, beats: np.ndarray, rep: np.ndarray, energy: np.ndarray,
                    total: float) -> list[dict]:
    """Sections of a song with no plan: cut where the music changes, then call the parts that repeat most and are
    loudest choruses, the opening an intro, the end an outro."""
    import librosa

    k = int(min(14, max(4, round(total / 18))))
    k = min(k, features.shape[1] - 1)
    bounds = sorted(set(librosa.segment.agglomerative(features, k).tolist()) | {0})
    times = [float(beats[b]) if b < len(beats) else total for b in bounds] + [total]
    times[0] = 0.0
    segs = [(a, b) for a, b in zip(times, times[1:]) if b - a > 1]
    secs = np.arange(len(rep))
    stats = [(float(rep[(secs >= a) & (secs < b)].mean()), float(energy[(secs >= a) & (secs < b)].mean()))
             for a, b in segs]
    z = np.array([0.6 * r + 0.4 * e for r, e in stats])
    cut = np.percentile(z, 65) if len(z) > 2 else z.max()
    out = []
    for i, ((a, b), (r, e)) in enumerate(zip(segs, stats)):
        if i == 0 and e < 0.45:
            name = "Intro"
        elif i == len(segs) - 1 and e < 0.45:
            name = "Outro"
        elif z[i] >= cut and b - a >= 8:
            name = "Chorus"
        elif r < 0.25 and a > total * 0.5:
            name = "Bridge"
        else:
            name = "Verse"
        out.append({"start": round(a, 2), "end": round(b, 2), "name": name, "kind": kind(name)})
    return out


def analyze(audio: Path, cfg: dict, song=None, lines: list | None = None, log=print) -> Structure:
    """Beats, bars, sections and drops of `audio`, plus per-second section / energy / repetition / drop scores."""
    import librosa

    lines = lines or []
    y, sr = librosa.load(str(audio), sr=22050, mono=True)
    total = len(y) / sr
    n = max(1, math.ceil(total))
    hop = 512
    onset = librosa.onset.onset_strength(y=y, sr=sr, hop_length=hop)
    kick = librosa.onset.onset_strength(y=y, sr=sr, hop_length=hop, fmax=160, n_mels=16)
    tempo, beat_frames = librosa.beat.beat_track(onset_envelope=onset, sr=sr, hop_length=hop,
                                                 start_bpm=float(getattr(song, "bpm", 0) or 120))
    beats = librosa.frames_to_time(beat_frames, sr=sr, hop_length=hop)
    bpm = float(np.atleast_1d(tempo)[0])

    sections = _song_sections(song, lines, total) if song is not None and song.sections else []
    model = _allin1(audio, log)
    method = "song plan + librosa" if sections else "librosa"
    if model:
        beats, bpm = np.array(model["beats"]), model["bpm"] or bpm
        beat_frames = librosa.time_to_frames(beats, sr=sr, hop_length=hop)
        method = "song plan + allin1" if sections else "allin1"
        sections = sections or model["sections"]
    chroma = librosa.feature.chroma_cqt(y=y, sr=sr, hop_length=hop)
    bars = np.array(model["bars"]) if model and model["bars"] else _bars(beats, beat_frames, kick, chroma)

    # loudness, per second, 0..1
    rms = librosa.feature.rms(y=y, hop_length=hop)[0]
    db = librosa.amplitude_to_db(rms + 1e-6)
    frame_t = librosa.frames_to_time(np.arange(len(db)), sr=sr, hop_length=hop)
    energy = _norm(_per_second(frame_t, db, n))

    # repetition: how much each beat's harmony and timbre recurs elsewhere in the song (choruses come back)
    mfcc = librosa.feature.mfcc(y=y, sr=sr, hop_length=hop, n_mfcc=13)
    feats = np.vstack([librosa.util.normalize(chroma, axis=0), librosa.util.normalize(mfcc[1:], axis=1)])
    sync = librosa.util.sync(feats, beat_frames, aggregate=np.median)
    rec = librosa.segment.recurrence_matrix(sync, width=8, mode="affinity", sym=True)
    rec = librosa.segment.path_enhance(rec, 9)
    beat_rep = rec.sum(axis=1)
    beat_t = np.concatenate([[0.0], beats])[:len(beat_rep)]
    repetition = _norm(_per_second(beat_t, beat_rep, n), 5, 95)

    if not sections:
        sections = _guess_sections(sync, beats, repetition, energy, total)

    # drops: a bar much louder than the two before it (the beat comes back / the chorus hits)
    bar_db = []
    edges = list(bars) + [total]
    for a, b in zip(edges, edges[1:]):
        m = (frame_t >= a) & (frame_t < b)
        bar_db.append(float(db[m].mean()) if m.any() else -80.0)
    drop = np.zeros(n)
    drops = []
    for i in range(2, len(bar_db)):
        jump = bar_db[i] - (bar_db[i - 1] + bar_db[i - 2]) / 2
        score = float(np.clip(jump / 6.0, 0, 1))
        if score <= 0.15:
            continue
        if score >= 0.5:
            drops.append(float(bars[i]))
        bar_len = edges[i + 1] - edges[i]
        for s in range(int(bars[i]), min(n, int(bars[i] + 2 * bar_len) + 1)):
            drop[s] = max(drop[s], score * (1 - 0.5 * (s - bars[i]) / (2 * bar_len + 1e-9)))

    labels = cfg["structure"]["labels"]
    section = np.array([labels.get(next((x for x in sections if x["start"] <= t + 0.5 < x["end"]),
                                        sections[-1])["kind"], 0.35) for t in range(n)])
    return Structure(total, bpm, [float(b) for b in beats], [float(b) for b in bars], sections, drops,
                     {"section": section.tolist(), "energy": energy.tolist(), "repetition": repetition.tolist(),
                      "drop": drop.tolist()}, method)


def score(st: Structure, cfg: dict) -> list[float]:
    """Per-second structure score: the weighted mix of its parts."""
    from .settings import blend

    w = cfg["structure"]["parts"]
    return [blend({k: st.per_second[k][t] for k in w}, w) for t in range(len(st.per_second["section"]))]
