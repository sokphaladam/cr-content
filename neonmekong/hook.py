"""Hook-first edit, for songs whose vocal starts after 10 seconds. Two options are rendered to compare:

  trim     start the song shortly before the first vocal (on a beat), short fade-in
  preview  prepend an 8-second chorus preview, crossfaded into the full song from its beginning

Each option has its own audio (out/hook/audio_<option>.wav) and lyrics (lyrics_<option>.lrc) on the NEW timeline,
and hook.json says how song time maps to video time, so the video steps only read the files for the chosen option.
"""
import json
import subprocess
from pathlib import Path

from . import analyze, config, songjson

LATE_VOCAL = 10.0   # seconds: a later first vocal needs a hook-first edit
LEAD_IN = 1.5       # trim: keep this much music before the first vocal
PREVIEW_LEN = 8.0
CROSSFADE = 0.8
FADE_IN = 0.3


def snap_back(t: float, beats: list[float], window: float = 0.6) -> float:
    """The nearest beat at or before t (within `window`), else t itself."""
    prior = [b for b in beats if b <= t + 1e-6 and t - b <= window]
    return max(prior) if prior else t


def shifted(lines: list[dict], shift: float, lo: float = 0.0, hi: float | None = None) -> list[dict]:
    out = []
    for ln in lines:
        s, e = ln["start"] + shift, ln["end"] + shift
        if s < lo or (hi is not None and s >= hi):
            continue
        out.append({**ln, "start": round(s, 2), "end": round(min(e, hi) if hi is not None else e, 2)})
    return out


def plan(data: dict, lines: list[dict], force: bool = False) -> dict:
    """Pure: both options' cut points and re-timed lyrics. {"needs_edit": False} when the vocal starts early."""
    vs = float(data.get("vocal_start") or 0.0)
    dur = float(data.get("duration") or 0.0)
    if vs <= LATE_VOCAL and not force:
        return {"needs_edit": False, "vocal_start": vs}
    beats = data.get("beat_times") or []

    cut = max(0.0, snap_back(vs - LEAD_IN, beats))
    trim = {"audio_start": round(cut, 3), "fade_in": FADE_IN, "shift": round(-cut, 3),
            "duration": round(dur - cut, 2), "lyrics": shifted(lines, -cut)}

    chorus = data.get("chorus") or {}
    result = {"needs_edit": True, "vocal_start": vs, "trim": trim, "preview": None}
    if chorus.get("start") is not None:
        p0 = snap_back(float(chorus["start"]), beats)
        length = min(PREVIEW_LEN, max(dur - p0, 0.0))
        offset = round(length - CROSSFADE, 3)  # the full song starts here on the new timeline
        result["preview"] = {
            "src_start": round(p0, 3), "length": round(length, 2), "crossfade": CROSSFADE, "song_offset": offset,
            "duration": round(offset + dur, 2),
            "lyrics": shifted(lines, -p0, lo=0.0, hi=length) + shifted(lines, offset),
        }
    return result


def _ffmpeg(args: list[str]) -> None:
    p = subprocess.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", *args], stdin=subprocess.DEVNULL,
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    if p.returncode:
        raise RuntimeError(f"ffmpeg failed:\n{p.stderr[-1500:]}")


def render_audio(audio: Path, option: str, spec: dict, out: Path) -> None:
    if option == "trim":
        _ffmpeg(["-ss", str(spec["audio_start"]), "-i", str(audio), "-af", f"afade=t=in:d={spec['fade_in']}", str(out)])
    else:
        _ffmpeg(["-i", str(audio), "-filter_complex",
                 f"[0:a]atrim=start={spec['src_start']}:duration={spec['length']},asetpts=PTS-STARTPTS[p];"
                 f"[0:a]asetpts=PTS-STARTPTS[m];"
                 f"[p][m]acrossfade=d={spec['crossfade']}:c1=tri:c2=tri[a]", "-map", "[a]", str(out)])


def run(folder: Path, force: bool = False, log=print) -> dict:
    data = songjson.load(folder / "song.json")
    lrc = folder / "lyrics.lrc"
    if not lrc.exists():
        raise FileNotFoundError(f"missing {lrc} (run analyze first)")
    result = plan(data, analyze.parse_lrc(lrc.read_text(encoding="utf-8")), force)
    if not result["needs_edit"]:
        log(f"vocals start at {result['vocal_start']:.1f}s (<= {LATE_VOCAL:.0f}s): no hook edit needed "
            "(use --force to render the options anyway)")
        return result
    out = folder / "out" / "hook"
    out.mkdir(parents=True, exist_ok=True)
    mix, _ = analyze.find_audio(folder)
    for option in ("trim", "preview"):
        spec = result[option]
        if spec is None:
            log(f"  {option}: skipped (no chorus in song.json)")
            continue
        (out / f"lyrics_{option}.lrc").write_text(analyze.lrc(spec["lyrics"]), encoding="utf-8")
        if config.dry_run() or not mix:
            log(f"  {option}: audio not rendered ({'dry-run' if config.dry_run() else 'no audio.wav / audio.mp3'})")
            continue
        target = out / f"audio_{option}.wav"
        songjson.backup(target)
        render_audio(mix, option, spec, target)
        log(f"  {option}: {target.name}, {spec['duration']:.1f}s")
    plan_file = out / "hook.json"
    songjson.backup(plan_file)
    slim = {k: ({kk: vv for kk, vv in v.items() if kk != "lyrics"} if isinstance(v, dict) else v)
            for k, v in result.items()}
    plan_file.write_text(json.dumps(slim, indent=2) + "\n", encoding="utf-8")
    return result
