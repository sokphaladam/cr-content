"""Chorus Short / Reel, 9:16 1080x1920 (out/short_chorus.mp4; the same file works as an Instagram Reel).

Cut from song.json's chorus: audio starts on a beat just before the first chorus line, and the first lyric is already
on screen in frame 0. No title card, subscribe pill or end-screen space; lyrics are double size.
"""
import json
from pathlib import Path

from . import analyze, config, hook, lyricvideo, songjson
from .suno import parse as parse_suno

SIZE = (1080, 1920)
DRAFT = (540, 960)
MIN_LEN, MAX_LEN = 15.0, 58.0   # Shorts may be up to 60 seconds
FADE_IN, FADE_OUT = 0.04, 0.6


def plan(data: dict, lines: list[dict]) -> dict:
    """Pure: cut points and re-timed lyrics. Raises ValueError when song.json has no usable chorus."""
    chorus = data.get("chorus") or {}
    if chorus.get("start") is None or chorus.get("end") is None:
        raise ValueError("song.json has no chorus start/end: run analyze or set them by hand")
    dur = float(data["duration"])
    first = next((ln for ln in lines if ln["start"] >= chorus["start"] - 0.5), None)
    if first is None:
        raise ValueError("no lyric line found at the chorus")
    cut = max(0.0, hook.snap_back(first["start"] - 0.1, data.get("beat_times") or [], window=0.4))
    end = min(float(chorus["end"]) + 0.4, dur)
    end = min(max(end, cut + MIN_LEN), cut + MAX_LEN, dur)   # 15..58 seconds
    kept = [ln for ln in lines if cut <= ln["start"] < end - 0.5]
    beats = [round(b - cut, 3) for b in (data.get("beat_times") or []) if cut <= b < end]
    return {"cut": round(cut, 3), "end": round(end, 3), "length": round(end - cut, 2),
            "lyrics": hook.shifted(kept, -cut, hi=end - cut), "beats": beats}


def run(folder: Path, seconds: float | None = None, draft: bool = False, log=print) -> Path:
    data = songjson.load(folder / "song.json")
    lines = analyze.parse_lrc((folder / "lyrics.lrc").read_text(encoding="utf-8"))
    p = plan(data, lines)
    out = folder / "out"
    out.mkdir(parents=True, exist_ok=True)

    mix, _ = analyze.find_audio(folder)
    audio = None
    if mix and not config.dry_run():
        audio = out / "short_audio.wav"
        songjson.backup(audio)
        hook._ffmpeg(["-ss", str(p["cut"]), "-t", str(p["length"]), "-i", str(mix), "-af",
                      f"afade=t=in:d={FADE_IN},afade=t=out:st={p['length'] - FADE_OUT}:d={FADE_OUT}", str(audio)])
    elif not config.dry_run():
        raise FileNotFoundError(f"no audio.wav / audio.mp3 in {folder}")

    suno_file = folder / "suno.txt"
    chorus_lines = [ln for sec in parse_suno(suno_file.read_text(encoding="utf-8")).sections if sec.kind == "chorus"
                    for ln in sec.lines] if suno_file.exists() else []
    v = lyricvideo.Variant("short", audio, p["lyrics"], p["beats"], None, p["length"])
    scene = lyricvideo.Scene(data, v, chorus_lines, DRAFT if draft else SIZE, 15 if draft else lyricvideo.FPS,
                             text_scale=2.0, title_card=False, pill=False, end_screen=False, instant_first=True,
                             lyric_frac=0.5, max_lines=3, wrap_frac=0.88)
    target = out / "short_chorus.mp4"
    songjson.move_aside(target)
    log(f"  short: {scene.W}x{scene.H} @{scene.fps}fps, {p['length']:.1f}s (song {p['cut']:.1f}s-{p['end']:.1f}s)")
    lyricvideo.encode(scene, target, seconds, draft, log)
    (out / "short.json").write_text(json.dumps({k: p[k] for k in ("cut", "end", "length")}, indent=2) + "\n",
                                    encoding="utf-8")
    return target
