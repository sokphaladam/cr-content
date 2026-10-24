"""Song analyzer: lyric timing (stable-ts forced alignment), BPM / beats / energy (librosa), chorus span.

Everything that needs audio is in `measure()`; `fill()` is pure so it can be tested without audio.
Dry-run reads tests/fixtures/songs/<demo>/mock_analysis.json instead of touching audio.
"""
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

from . import config, songjson
from .suno import Suno

AUDIO_NAMES = ("audio.wav", "audio.mp3")
RMS_HOP = 0.5  # seconds per energy sample


def find_audio(folder: Path) -> tuple[Path | None, Path | None]:
    """(mix, vocals): the mix drives beats and energy; vocals.wav (when present) drives lyric alignment."""
    mix = next((folder / n for n in AUDIO_NAMES if (folder / n).exists()), None)
    vocals = folder / "vocals.wav"
    return mix, vocals if vocals.exists() else None


def read_id3(audio: Path) -> dict:
    try:
        from mutagen import File
        tags = File(str(audio), easy=True)
        return {k: str(v[0]) for k, v in (tags or {}).items() if k in ("title", "artist", "album", "date", "genre") and v}
    except ImportError:
        return {}
    except Exception:
        return {}


def separate_vocals(mix: Path, dest: Path, log=print) -> Path | None:
    """Split the vocals off the mix with Demucs (on the GPU when there is one) and save them as `dest`.
    Forced alignment fails on a full mix with heavy synths and long instrumental parts; the bare vocals work."""
    try:
        import demucs  # noqa: F401
        import torch
    except ImportError:
        log("      Demucs is not installed (pip install -r requirements-music.txt): aligning the full mix instead")
        return None
    device = "cuda" if torch.cuda.is_available() else "cpu"
    log(f"      separating the vocals with Demucs on {device} (first run downloads its model) ...")
    with tempfile.TemporaryDirectory() as tmp:
        proc = subprocess.run([sys.executable, "-m", "demucs", "--two-stems=vocals", "-n", "htdemucs", "-d", device,
                               "-o", tmp, str(mix)], stdin=subprocess.DEVNULL, capture_output=True, text=True,
                              encoding="utf-8", errors="replace")
        found = next(Path(tmp).rglob("vocals.*"), None)
        if proc.returncode or not found:
            log(f"      Demucs failed, aligning the full mix instead:\n{proc.stderr[-800:]}")
            return None
        subprocess.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", str(found), "-ar", "44100",
                        "-c:a", "pcm_s16le", str(dest)], stdin=subprocess.DEVNULL, check=True)
    log(f"      saved {dest.name}")
    return dest


def align_lines(audio: Path, s: Suno, total: float) -> list[dict]:
    """Time the suno.txt lyrics against the audio with the project's stable-ts method (crcontent.align.whisper_timing):
    the song is transcribed in short chunks, the heard words are matched to the lyrics in order (so a repeated chorus
    lines up with the right repeat), weak lines are aligned again between their neighbours, and whole-song forced
    alignment is only the last resort. [{section, text, start, end, check}] - `check`: worth checking by ear."""
    from crcontent.align import suspect_lines, whisper_timing
    from crcontent.lyrics import SongScript, SongSection
    script = SongScript(
        title=s.title, genre="", mood="", bpm=0, vocal="", styles=[], caption="", hashtags=[],
        sections=[SongSection(name=sec.tag, lyrics=sec.lines, seconds=0, visual_query="x") for sec in s.sections])
    timed = whisper_timing(audio, script, "en", isolate_vocals=False, total=total)
    bad = suspect_lines(timed, total)
    return [{"section": x.section, "text": x.text, "start": round(x.start, 2), "end": round(x.end, 2),
             "check": bool(x.check) or i in bad} for i, x in enumerate(timed)]


def audio_features(mix: Path) -> dict:
    import librosa
    import numpy as np
    y, sr = librosa.load(str(mix), sr=22050, mono=True)
    tempo, beats = librosa.beat.beat_track(y=y, sr=sr, units="time")
    hop = int(sr * RMS_HOP)
    rms = librosa.feature.rms(y=y, frame_length=hop * 2, hop_length=hop)[0]
    return {"duration": round(len(y) / sr, 2), "bpm": round(float(np.atleast_1d(tempo)[0])),
            "beats": [round(float(b), 3) for b in beats], "rms": [round(float(v), 5) for v in rms]}


def mock(folder: Path) -> dict:
    path = folder / "mock_analysis.json"
    if not path.exists():
        path = config.FIXTURES / "demo-song" / "mock_analysis.json"
    return json.loads(path.read_text(encoding="utf-8"))


def measure(folder: Path, s: Suno, separate: bool = True) -> dict:
    """Lines + audio features (+ ID3 tags). Dry-run returns the fixture instead."""
    if config.dry_run():
        return mock(folder)
    mix, vocals = find_audio(folder)
    if not mix:
        raise FileNotFoundError(f"no audio.wav / audio.mp3 in {folder}")
    if vocals is None and separate:
        vocals = separate_vocals(mix, folder / "vocals.wav")   # never replaces an existing vocals.wav
    out = audio_features(mix)
    out["lines"] = align_lines(vocals or mix, s, out["duration"])
    out["id3"] = read_id3(mix)
    return out


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def section_spans(s: Suno, lines: list[dict], duration: float) -> list[tuple[float, float] | None]:
    """(start, end) of each section from its sung lines; None for sections without lyrics."""
    n = len(s.sections)
    first, last = [None] * n, [None] * n
    for ln in lines:
        i = ln["section"]
        first[i] = ln["start"] if first[i] is None else min(first[i], ln["start"])
        last[i] = ln["end"] if last[i] is None else max(last[i], ln["end"])
    sung = [i for i in range(n) if first[i] is not None]
    spans: list[tuple[float, float] | None] = [None] * n
    for k, i in enumerate(sung):
        nxt = first[sung[k + 1]] if k + 1 < len(sung) else duration
        spans[i] = (first[i], min(max(last[i] + 0.4, first[i]), nxt))
    return spans


def energy_between(rms: list[float], a: float, b: float) -> float:
    return _mean(rms[int(a / RMS_HOP):max(int(b / RMS_HOP), int(a / RMS_HOP) + 1)])


def fill(data: dict, s: Suno, m: dict) -> tuple[dict, list[str]]:
    """Merge measurements into song.json. Measured fields are replaced; fields you may have edited are only
    filled when empty. Returns (data, warnings)."""
    notes: list[str] = []
    lines, rms, dur = m["lines"], m["rms"], m["duration"]
    peak = max(rms) or 1.0
    mean_all = _mean(rms)
    spans = section_spans(s, lines, dur)

    sections = []
    for i, sec in enumerate(s.sections):
        row = {"tag": sec.tag, "kind": sec.kind, "lines": len(sec.lines)}
        if spans[i]:
            a, b = spans[i]
            e = energy_between(rms, a, b) / peak
            row.update(start=round(a, 2), end=round(b, 2), energy=round(e, 2),
                       level="high" if e >= 0.75 else "mid" if e >= 0.45 else "low")
        sections.append(row)

    data.update(bpm=m["bpm"], beat_times=m["beats"], sections=sections, duration=dur,
                vocal_start=round(min((ln["start"] for ln in lines), default=0.0), 2))

    chorus = next((r for r in sections if r["kind"] == "chorus" and "start" in r), None)
    if chorus:
        data["chorus"] = {"start": chorus["start"], "end": chorus["end"]}
        if energy_between(rms, chorus["start"], chorus["end"]) < mean_all * 1.05:
            notes.append("the first [Chorus] is not louder than the song average: check chorus start/end in song.json")
    else:
        notes.append("no [Chorus] with lyrics found: set chorus start/end in song.json by hand")

    # cross-check: the loudest stretch should overlap the tagged chorus
    if chorus and len(rms) > 8:
        win = int(8 / RMS_HOP)
        best = max(range(len(rms) - win + 1), key=lambda k: _mean(rms[k:k + win]))
        t = best * RMS_HOP
        if not any(r["kind"] == "chorus" and "start" in r and r["start"] - 2 <= t + 4 <= r["end"] + 2 for r in sections):
            notes.append(f"the loudest 8s (at {t:.0f}s) is not inside a [Chorus]: check the section tags")

    doubtful = [i + 1 for i, ln in enumerate(lines) if ln.get("check")]
    if doubtful:
        notes.append(f"timing of {len(doubtful)} lyric line(s) looks doubtful (line numbers in lyrics.lrc: "
                     f"{', '.join(map(str, doubtful))}): check them by ear and fix lyrics.lrc")

    if data["vocal_start"] > 10:
        notes.append(f"vocals start at {data['vocal_start']:.1f}s: the hook-first edit will apply")

    d = config.GENRE_DEFAULTS.get(data.get("genre", ""), {})
    for key in ("mood_phrase", "scene_theme", "palette"):
        if not data.get(key) and key in d:
            data[key] = d[key]
    if not data.get("subscribe_line"):
        data["subscribe_line"] = config.SUBSCRIBE_LINE
    if m.get("id3"):
        data["id3"] = m["id3"]
    return data, notes + songjson.warnings(data)


def lrc(lines: list[dict]) -> str:
    def stamp(t: float) -> str:
        return f"[{int(t // 60):02d}:{t % 60:05.2f}]"
    return "".join(f"{stamp(ln['start'])}{ln['text']}\n" for ln in lines)


def parse_lrc(text: str) -> list[dict]:
    """[{text, start, end}] from lyrics.lrc; a line ends where the next begins (capped at 6s)."""
    rows = []
    for raw in text.splitlines():
        m = re.match(r"\[(\d+):(\d+(?:\.\d+)?)\](.*)", raw)
        if m:
            rows.append({"text": m.group(3).strip(), "start": int(m.group(1)) * 60 + float(m.group(2))})
    for a, b in zip(rows, rows[1:] + [None]):
        a["end"] = round(min(b["start"] if b else a["start"] + 6, a["start"] + 6), 2)
    return rows


def run(folder: Path, s: Suno, separate: bool = True) -> tuple[dict, list[str]]:
    """Analyze one song folder: writes lyrics.lrc, updates song.json (backed up first)."""
    path = folder / "song.json"
    data = songjson.load(path) if path.exists() else songjson.from_suno(s, slug=folder.name)
    m = measure(folder, s, separate)
    lrc_path = folder / "lyrics.lrc"
    songjson.backup(lrc_path)
    data, notes = fill(data, s, m)
    lrc_path.write_text(lrc(m["lines"]), encoding="utf-8")
    songjson.save(path, data, force=True)  # keeps song.json.bak-<time> of the previous file
    return data, notes
