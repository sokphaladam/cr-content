"""Video Quality Inspector, final-render stage: checks the exported file itself (not the project) with ffprobe and one
ffmpeg analysis pass, and saves a report next to it in quality/<stem>.json. Never writes to the video.

Every check ends as pass / warning / fail / not_checked; a check that couldn't run is not_checked, never pass.
"""
import hashlib
import json
import re
import shutil
import subprocess
import tempfile
import threading
import traceback
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from functools import lru_cache
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from .config import FPS, OUTPUT_DIR, ROOT, frame_size

router = APIRouter()

# Per-workflow thresholds. Size comes from the video's own settings (aspect), not from here.
VISUAL = {"sample_fps": 2, "blur": 10.0, "blur_sec": 1.5, "border": 0.94, "border_share": 0.6, "cast": 18,
          "loud_jump_lu": 12, "quiet_lufs": -30, "imbalance_db": 3.0, "mono_loss_db": 6.0}
PROFILES = {
    "short": {"label": "Shorts", "black_sec": 0.5, "freeze_sec": 2.0, "silence_sec": 1.5, "silence_db": -50,
              "peak_dbtp": -1.0, "av_drift_warn": 0.3, "av_drift_fail": 2.0, **VISUAL,
              "dark": 35, "bright": 215, "exposure_sec": 2.0, "duplicates": True},
    # songs often open quietly, hold still pictures longer, use dark neon looks and repeat the cover by design
    "lyric": {"label": "Lyric video", "black_sec": 1.0, "freeze_sec": 4.0, "silence_sec": 3.0, "silence_db": -50,
              "peak_dbtp": -1.0, "av_drift_warn": 0.3, "av_drift_fail": 2.0, **VISUAL,
              "dark": 22, "bright": 225, "exposure_sec": 4.0, "duplicates": False},
}
RULES_FILE = ROOT / "quality_rules.json"  # your overrides: {"short": {"blur": 12}, "lyric_preview": {...}}


def defaults() -> dict:
    """Every editable rule set: the render profiles here, the preview ones in quality_preview."""
    from .quality_preview import LYRIC_RULES, SHORT_RULES

    return {**PROFILES, "short_preview": SHORT_RULES, "lyric_preview": LYRIC_RULES}


def editable(value) -> bool:
    return isinstance(value, (int, float, bool))  # labels and ranges (safe_x) stay fixed


def saved_rules() -> dict:
    try:
        data = json.loads(RULES_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def rules_for(name: str) -> dict:
    """A rule set with your overrides applied (only known keys, of the default's type)."""
    base = defaults()[name]
    own = saved_rules().get(name) or {}
    return {**base, **{k: type(base[k])(v) for k, v in own.items()
                       if k in base and editable(base[k]) and isinstance(v, (int, float, bool))}}


LOUDNESS_GUIDE = -14.0  # YouTube plays back louder mixes turned down to about this; guidance, not a rule
NOT_YET = [  # shown as not_checked so nobody reads the report as covering them
    ("visual", "Subject framing and colour match between shots"),
    ("captions", "Caption / lyric placement and timing"), ("storytelling", "Hook, pacing and payoff"),
]

_jobs = None
_lock = None
_cancel: dict[str, threading.Event] = {}
_pool = ThreadPoolExecutor(max_workers=1)  # its own queue: an inspection doesn't wait behind a render


def bind(jobs: dict, lock) -> None:
    global _jobs, _lock
    _jobs, _lock = jobs, lock


class Cancelled(Exception):
    pass


# ---------- engine ----------

def _check(checks: list, detector: str, category: str, status: str, title: str, description: str = "",
           severity: str = "info", recommendation: str = "", start: float | None = None, end: float | None = None):
    item = {"id": detector if start is None else f"{detector}@{start:.2f}", "category": category,
            "severity": severity, "status": status, "title": title, "description": description, "detector": detector}
    if recommendation:
        item["recommendation"] = recommendation
    if start is not None:
        item["start"], item["end"] = round(start, 2), round(end if end is not None else start, 2)
    checks.append(item)
    return item


def fingerprint(path: Path) -> dict:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    st = path.stat()
    return {"sha256": h.hexdigest(), "size": st.st_size, "mtime": st.st_mtime}


def probe(path: Path) -> dict:
    out = subprocess.run(["ffprobe", "-v", "error", "-show_format", "-show_streams", "-of", "json", str(path)],
                         stdin=subprocess.DEVNULL, capture_output=True, text=True)
    if out.returncode != 0:
        raise ValueError(out.stderr.strip()[-500:] or "ffprobe couldn't read the file")
    return json.loads(out.stdout)


def _rate(text: str | None) -> float:
    try:
        n, _, d = (text or "0/1").partition("/")
        return float(n) / float(d or 1)
    except (ValueError, ZeroDivisionError):
        return 0.0


def _num(value) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


@lru_cache
def has_filter(name: str) -> bool:
    out = subprocess.run(["ffmpeg", "-hide_banner", "-filters"], stdin=subprocess.DEVNULL, capture_output=True, text=True)
    return f" {name} " in out.stdout


SIG = 16  # side of the tiny grey thumbnail compared to find repeated shots


def analyze(path: Path, has_video: bool, has_audio: bool, total: float, rules: dict,
            cancel: threading.Event | None = None, report=None, channels: int = 0) -> dict:
    """One decode of the whole file: black and frozen stretches, sampled frames (sharpness, brightness, colour, borders,
    a tiny thumbnail for repeated shots), silence, loudness over time, channel levels, decode errors."""
    found = {"black": [], "freeze": [], "silence": [], "errors": [], "lufs": None, "lra": None, "peak": None,
             "samples": [], "sigs": [], "momentary": [], "rms": {}, "mono_rms": None}
    tmp = Path(tempfile.mkdtemp(prefix="crq-"))
    meta = tmp / "frames.txt"
    graph, maps = [], []
    if has_video:
        sample = (f"fps={rules['sample_fps']},scale=480:-2,split[s1][s2];"
                  f"[s1]signalstats,{'blurdetect,' if has_filter('blurdetect') else ''}cropdetect=round=2:reset=1:skip=0,"
                  f"metadata=mode=print:file=frames.txt[fo];[s2]scale={SIG}:{SIG},format=gray[ro]")
        graph.append(f"[0:v]split[v1][v2];[v1]blackdetect=d={rules['black_sec']}:pix_th=0.10,"
                     f"freezedetect=n=-60dB:d={rules['freeze_sec']}[vo];[v2]{sample}")
        maps += ["-map", "[vo]", "-f", "null", "-", "-map", "[fo]", "-f", "null", "-"]
    if has_audio:
        a = (f"silencedetect=n={rules['silence_db']}dB:d={rules['silence_sec']},ebur128=peak=true:framelog=info")
        if channels >= 2:
            graph.append(f"[0:a]asplit[a1][a2];[a1]{a},astats@ch=measure_perchannel=RMS_level:measure_overall=none[ao];"
                         "[a2]pan=mono|c0=0.5*c0+0.5*c1,astats@mono=measure_perchannel=RMS_level:measure_overall=none[mo]")
            maps += ["-map", "[ao]", "-f", "null", "-", "-map", "[mo]", "-f", "null", "-"]
        else:
            graph.append(f"[0:a]{a}[ao]")
            maps += ["-map", "[ao]", "-f", "null", "-"]
    if has_video:
        maps += ["-map", "[ro]", "-f", "rawvideo", "pipe:1"]
    cmd = ["ffmpeg", "-hide_banner", "-nostdin", "-i", str(path.resolve()), "-filter_complex", ";".join(graph), *maps]
    # run in the temp folder: the frame log is named relative to it (a Windows "C:" would break the filter graph)
    proc = subprocess.Popen(cmd, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=tmp)
    raw = bytearray()
    reader = threading.Thread(target=lambda: raw.extend(proc.stdout.read()), daemon=True)  # thumbnails, alongside the log
    reader.start()
    freeze = silence = None
    in_summary = False
    stats = None  # which astats instance the next "RMS level" line belongs to
    try:
        for b in proc.stderr:  # bytes split on \n; ffmpeg's \r stats lines stay joined, so split them here
            for line in b.decode("utf-8", "replace").split("\r"):
                if cancel and cancel.is_set():
                    proc.kill()
                    raise Cancelled()
                if m := re.search(r"black_start:([\d.]+) black_end:([\d.]+)", line):
                    found["black"].append((float(m[1]), float(m[2])))
                elif m := re.search(r"freeze_start: ([\d.]+)", line):
                    freeze = float(m[1])
                elif (m := re.search(r"freeze_end: ([\d.]+)", line)) and freeze is not None:
                    found["freeze"].append((freeze, float(m[1])))
                    freeze = None
                elif m := re.search(r"silence_start: (-?[\d.]+)", line):
                    silence = max(0.0, float(m[1]))
                elif (m := re.search(r"silence_end: ([\d.]+)", line)) and silence is not None:
                    found["silence"].append((silence, float(m[1])))
                    silence = None
                elif m := re.search(r"\] t: ([\d.]+)\s+TARGET.*?M:\s*(-?[\d.]+)", line):
                    found["momentary"].append((float(m[1]), float(m[2])))
                elif m := re.search(r"\[astats@(ch|mono) @ \w+\] Channel: (\d+)", line):
                    stats = (m[1], int(m[2]))
                elif (m := re.search(r"\[astats@(?:ch|mono) @ \w+\] RMS level dB: (-?[\d.]+|-inf)", line)) and stats:
                    v = _num(m[1]) if m[1] != "-inf" else -120.0
                    if stats[0] == "mono":
                        found["mono_rms"] = v
                    else:
                        found["rms"][stats[1]] = v
                elif "Summary:" in line:
                    in_summary = True
                elif in_summary and (m := re.match(r"\s*(I|LRA|Peak):\s+(-?[\d.]+|-inf)", line)):
                    found[{"I": "lufs", "LRA": "lra", "Peak": "peak"}[m[1]]] = _num(m[2]) if m[2] != "-inf" else None
                elif m := re.search(r"time=(\d+):(\d+):([\d.]+)", line):
                    if report and total:
                        report(min(1.0, (int(m[1]) * 3600 + int(m[2]) * 60 + float(m[3])) / total))
                elif (re.search(r"error|corrupt|invalid data|non-existing|concealing", line, re.I)
                      and not re.search(r"Parsed_|astats@", line) and len(found["errors"]) < 20):
                    found["errors"].append(line.strip())
        code = proc.wait()
        reader.join(timeout=5)
        found["samples"] = _read_samples(meta)
    finally:
        if proc.poll() is None:
            proc.kill()
        shutil.rmtree(tmp, ignore_errors=True)
    step = 1 / rules["sample_fps"]
    found["sigs"] = [(i * step, bytes(raw[i * SIG * SIG:(i + 1) * SIG * SIG])) for i in range(len(raw) // (SIG * SIG))]
    # a stretch still running at the end of the file has no end line
    if freeze is not None:
        found["freeze"].append((freeze, total))
    if silence is not None:
        found["silence"].append((silence, total))
    found["exit_code"] = code
    return found


def _read_samples(meta: Path) -> list[dict]:
    """The sampled frames' measurements from metadata=print: [{t, blur, yavg, ylow, yhigh, uavg, vavg, cw, ch}]."""
    out, cur = [], None
    try:
        text = meta.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return out
    keys = {"lavfi.blur": "blur", "lavfi.signalstats.YAVG": "yavg", "lavfi.signalstats.YLOW": "ylow",
            "lavfi.signalstats.YHIGH": "yhigh", "lavfi.signalstats.YMIN": "ymin", "lavfi.signalstats.YMAX": "ymax",
            "lavfi.signalstats.UAVG": "uavg", "lavfi.signalstats.VAVG": "vavg", "lavfi.cropdetect.w": "cw",
            "lavfi.cropdetect.h": "ch"}
    for line in text.splitlines():
        if m := re.match(r"frame:\s*\d+\s+pts:\s*\S+\s+pts_time:([\d.]+)", line):
            cur = {"t": float(m[1])}
            out.append(cur)
        elif cur is not None and "=" in line:
            k, _, v = line.partition("=")
            if k in keys:
                cur[keys[k]] = _num(v)
    return out


def stretches(times: list[float], step: float, min_sec: float) -> list[tuple[float, float]]:
    """Runs of consecutive sample times (no gap above one step), at least min_sec long."""
    runs, out = [], []
    for t in times:
        if runs and t - runs[-1][1] <= step * 1.5:
            runs[-1][1] = t
        else:
            runs.append([t, t])
    for a, b in runs:
        if b + step - a >= min_sec:
            out.append((a, b + step))
    return out


def repeated_shots(sigs: list[tuple[float, bytes]], cut: float = 30, same: float = 8) -> list[tuple[float, float]]:
    """(later shot's start, earlier shot's start) for shots that look the same as an earlier, non-neighbouring shot.
    Shots are runs of similar tiny thumbnails; flat frames (black, one colour) are ignored."""
    def diff(a: bytes, b: bytes) -> float:
        return sum(abs(x - y) for x, y in zip(a, b)) / len(a)

    shots = []  # [start, middle signature]
    run = []
    for k, (t, sig) in enumerate(sigs):
        if run and diff(sig, run[-1][1]) > cut:
            shots.append(run)
            run = []
        run.append((t, sig))
    if run:
        shots.append(run)
    reps = []
    for r in shots:
        sig = r[len(r) // 2][1]
        if max(sig) - min(sig) > 40:  # a flat frame matches every other flat frame
            reps.append((r[0][0], sig))
    out = []
    for j in range(len(reps)):
        for i in range(j - 1):  # skip the neighbour: a cut back to the same shot right away is a jump cut, not a repeat
            if diff(reps[j][1], reps[i][1]) < same:
                out.append((reps[j][0], reps[i][0]))
                break
    return out


def _evidence(path: Path, at: float, out: Path) -> str:
    try:
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", f"{at:.2f}", "-i", str(path), "-frames:v", "1",
                        "-vf", "scale=320:-2", str(out)], stdin=subprocess.DEVNULL, capture_output=True, timeout=30,
                       check=True)
        return out.name
    except (subprocess.SubprocessError, OSError):
        return ""


def _clock(t: float) -> str:
    return f"{int(t // 60)}:{t % 60:04.1f}"


def inspect_file(path: Path, profile: str, expect: dict, cancel: threading.Event | None = None, report=None,
                 rights_of: tuple[str, str] | None = None) -> dict:
    """The report for the rendered file at `path`. expect: width, height, fps, and optionally duration (seconds the
    video should last, e.g. the song's length)."""
    rules = rules_for(profile)
    checks: list[dict] = []
    result = {"stage": "render", "profile": profile, "profile_label": rules["label"], "file": path.name,
              "created": datetime.now().isoformat(timespec="seconds"), "expect": expect, "checks": checks,
              "cancelled": False, "rights_of": rights_of, "sampled": (f"every frame decoded once for black/frozen/sound; sharpness, exposure, colour, borders and repeats from {rules['sample_fps']} sampled frames per second, not every frame")}
    say = report or (lambda f, d="": None)

    if not shutil.which("ffprobe") or not shutil.which("ffmpeg"):
        raise RuntimeError("FFmpeg/FFprobe not found. Install FFmpeg and make sure `ffmpeg` and `ffprobe` are on PATH "
                           "(macOS: brew install ffmpeg), then run the check again.")
    if not path.is_file() or path.stat().st_size == 0:
        _check(checks, "file.exists", "technical", "fail", "Output file is missing or empty", f"{path.name} has no data.",
               "critical", "Render the video again.")
        return _finish(result)
    say(0.0, "Fingerprinting the file")
    result["fingerprint"] = fingerprint(path)
    _check(checks, "file.exists", "technical", "pass", "Output file exists",
           f"{result['fingerprint']['size'] / 1e6:.1f} MB")

    say(0.02, "Reading the streams")
    try:
        info = probe(path)
    except ValueError as e:
        _check(checks, "file.readable", "technical", "fail", "The file can't be read as a video", str(e), "critical",
               "The render was probably interrupted. Render it again.")
        return _finish(result)
    fmt = info.get("format", {})
    video = next((s for s in info.get("streams", []) if s.get("codec_type") == "video"), None)
    audio = next((s for s in info.get("streams", []) if s.get("codec_type") == "audio"), None)
    total = _num(fmt.get("duration")) or 0.0
    result["media"] = {"container": fmt.get("format_name"), "duration": round(total, 3),
                       "bitrate": int(fmt["bit_rate"]) if fmt.get("bit_rate", "").isdigit() else None}

    # --- streams and format ---
    if video:
        w, h, fps = video.get("width", 0), video.get("height", 0), _rate(video.get("avg_frame_rate"))
        result["media"].update(width=w, height=h, fps=round(fps, 3), video_codec=video.get("codec_name"),
                               pix_fmt=video.get("pix_fmt"), color_space=video.get("color_space"))
        _check(checks, "stream.video", "technical", "pass", "Video stream present", f"{video.get('codec_name')}")
        ew, eh = expect.get("width"), expect.get("height")
        if ew and eh:
            if (w, h) == (ew, eh):
                _check(checks, "format.resolution", "technical", "pass", f"Resolution {w}×{h}", "Matches the video's settings.")
            elif (w > h) != (ew > eh):
                _check(checks, "format.resolution", "technical", "fail", f"Wrong orientation: {w}×{h}",
                       f"Expected {ew}×{eh}.", "critical", "Check the aspect ratio setting and render again.")
            else:
                _check(checks, "format.resolution", "technical", "fail", f"Resolution {w}×{h}, expected {ew}×{eh}",
                       "The file doesn't match the size this video was set up for.", "high", "Render it again.")
        else:
            _check(checks, "format.resolution", "technical", "not_checked", f"Resolution {w}×{h}", "No target size known.")
        efps = expect.get("fps")
        if not fps:
            _check(checks, "format.fps", "technical", "not_checked", "Frame rate unknown")
        elif efps and abs(fps - efps) > 0.5:
            _check(checks, "format.fps", "technical", "warning", f"Frame rate {fps:.2f} fps (settings: {efps})",
                   "Not wrong in itself; confirm it's intended.", "low")
        else:
            _check(checks, "format.fps", "technical", "pass", f"Frame rate {fps:.2f} fps")
        if video.get("pix_fmt") not in ("yuv420p", "yuvj420p"):
            _check(checks, "format.pix_fmt", "technical", "warning", f"Pixel format {video.get('pix_fmt')}",
                   "Most players and YouTube expect yuv420p.", "medium", "Export with -pix_fmt yuv420p.")
        else:
            _check(checks, "format.pix_fmt", "technical", "pass", "Pixel format yuv420p")
        if not video.get("color_space"):
            _check(checks, "format.color", "technical", "warning", "No colour-space tag",
                   "Players will assume BT.709; usually fine for SDR. Review only if colours look off after upload.", "info")
        else:
            _check(checks, "format.color", "technical", "pass", f"Colour space {video['color_space']}")
    else:
        _check(checks, "stream.video", "technical", "fail", "No video stream", "", "critical", "Render it again.")
    if audio:
        result["media"].update(audio_codec=audio.get("codec_name"), sample_rate=_num(audio.get("sample_rate")),
                               channels=audio.get("channels"), channel_layout=audio.get("channel_layout"))
        _check(checks, "stream.audio", "audio", "pass", "Audio stream present",
               f"{audio.get('codec_name')}, {audio.get('sample_rate')} Hz, {audio.get('channel_layout') or audio.get('channels')}")
    else:
        _check(checks, "stream.audio", "audio", "fail", "No audio stream", "The video is silent.", "critical",
               "Check the voice-over / song and render again.")

    # --- duration ---
    vdur, adur = (_num(s.get("duration")) if s else None for s in (video, audio))
    if total <= 0:
        _check(checks, "duration.length", "technical", "fail", "Duration is zero", "", "critical", "Render it again.")
    elif expect.get("duration"):
        gap = total - expect["duration"]
        if gap < -1.0:
            _check(checks, "duration.length", "technical", "warning",
                   f"Video is {-gap:.1f} s shorter than expected ({_clock(total)} vs {_clock(expect['duration'])})",
                   "The ending may be cut off.", "high", "Watch the ending; render again if it stops early.",
                   start=total, end=expect["duration"])
        else:
            _check(checks, "duration.length", "technical", "pass", f"Duration {_clock(total)}",
                   f"Expected about {_clock(expect['duration'])}.")
    else:
        _check(checks, "duration.length", "technical", "pass", f"Duration {_clock(total)}")
    if vdur and adur:
        drift = abs(vdur - adur)
        status = "fail" if drift > rules["av_drift_fail"] else "warning" if drift > rules["av_drift_warn"] else "pass"
        _check(checks, "sync.av_duration", "technical", status,
               f"Audio and video lengths differ by {drift:.2f} s" if status != "pass" else "Audio and video lengths match",
               f"video {vdur:.2f} s, audio {adur:.2f} s", "high" if status == "fail" else "medium",
               "One track ends early: check the ending." if status != "pass" else "",
               **({"start": min(vdur, adur), "end": max(vdur, adur)} if status != "pass" else {}))
    elif video and audio:
        _check(checks, "sync.av_duration", "technical", "not_checked", "Audio/video lengths",
               "The container doesn't report per-stream durations.")

    # --- one decode pass ---
    detected = ("decode.errors", "visual.black", "visual.freeze", "visual.sharpness", "visual.exposure", "visual.colour",
                "visual.border", "visual.repeat", "audio.silence", "audio.loudness", "audio.peak", "audio.jumps",
                "audio.balance", "audio.mono")
    if not (video or audio) or total <= 0:
        for d in detected:
            _check(checks, d, "technical", "not_checked", d, "No stream to analyse.")
        return _finish(result)
    try:
        say(0.05, "Decoding the whole file (picture, sound, loudness)")
        found = analyze(path, bool(video), bool(audio), total, rules, cancel,
                        lambda f: say(0.05 + 0.85 * f, f"Analysing {_clock(f * total)} / {_clock(total)}"),
                        channels=int(audio.get("channels") or 0) if audio else 0)
    except Cancelled:
        result["cancelled"] = True
        for d in detected:
            _check(checks, d, "technical", "not_checked", d, "Cancelled before this ran.")
        return _finish(result)
    except (OSError, subprocess.SubprocessError, ValueError) as e:  # keep what was checked; say what wasn't
        result["error"] = f"{type(e).__name__}: {e}"
        for d in detected:
            _check(checks, d, "technical", "not_checked", d, f"The analysis stopped: {e}")
        return _finish(result)

    if found["exit_code"] != 0 or found["errors"]:
        _check(checks, "decode.errors", "technical", "fail", f"Decode errors ({len(found['errors'])})",
               "\n".join(found["errors"][:5]) or f"ffmpeg exited with {found['exit_code']}", "critical",
               "The file is damaged. Render it again.")
    else:
        _check(checks, "decode.errors", "technical", "pass", "Decodes cleanly from start to end")

    evidence_dir = path.parent / "quality"
    try:
        evidence_dir.mkdir(exist_ok=True)
    except OSError:
        pass  # no evidence frames then; the checks still run
    shots = 0

    def issue(detector, category, title, desc, rec, a, b, severity="medium"):
        nonlocal shots
        item = _check(checks, detector, category, "warning", title, desc, severity, rec, a, b)
        if video and shots < 16:  # keep the folder small
            shots += 1
            name = _evidence(path, min(a + 0.1, max(0.0, total - 0.05)),
                             evidence_dir / f"{path.stem}-{item['id'].replace('@', '-').replace('.', '_')}.jpg")
            if name:
                item["evidence"] = f"quality/{name}"

    if video:
        for a, b in found["black"]:
            issue("visual.black", "visual", f"Black screen {_clock(a)}–{_clock(b)}", f"{b - a:.1f} s of black.",
                  "Fine if it's a deliberate fade; otherwise a clip is missing here.", a, b,
                  "high" if b - a > 2 else "medium")
        blacks = found["black"]
        for a, b in found["freeze"]:
            if any(x <= a + 0.1 and b <= y + 0.1 for x, y in blacks):
                continue  # already reported as black
            issue("visual.freeze", "visual", f"Frozen picture {_clock(a)}–{_clock(b)}", f"No change for {b - a:.1f} s.",
                  "Fine for a deliberate hold; otherwise a clip stalled or a still is on screen too long.", a, b)
        for det, what, sec in (("visual.black", "black", "black_sec"), ("visual.freeze", "frozen", "freeze_sec")):
            if not any(c["detector"] == det for c in checks):
                _check(checks, det, "visual", "pass", f"No {what} stretches", f"Threshold: {rules[sec]} s")
        found["frame"] = (480, round(480 * video.get("height", 1) / max(video.get("width", 1), 1) / 2) * 2)  # scale=480:-2
        visual_checks(checks, found, rules, total, issue)
    if audio:
        for a, b in found["silence"]:
            ending = b >= total - 0.1 and a > 0
            issue("audio.silence", "audio",
                  f"Audio stops {_clock(a)} before the end" if ending else f"Silence {_clock(a)}–{_clock(b)}",
                  f"{b - a:.1f} s below {rules['silence_db']} dB.",
                  "Check the ending: the voice/song may run out early." if ending
                  else "Fine if intended (a pause or quiet intro); otherwise audio is missing here.", a, b,
                  "high" if ending else "medium")
        if not found["silence"]:
            _check(checks, "audio.silence", "audio", "pass", "No long silences", f"Threshold: {rules['silence_sec']} s")
        lufs, peak = found["lufs"], found["peak"]
        if lufs is None:
            _check(checks, "audio.loudness", "audio", "not_checked", "Loudness", "ffmpeg didn't report a value.")
        else:
            louder = lufs > LOUDNESS_GUIDE + 1
            _check(checks, "audio.loudness", "audio", "warning" if lufs < -20 else "pass",
                   f"Integrated loudness {lufs:.1f} LUFS" + (f", range {found['lra']:.1f} LU" if found["lra"] is not None else ""),
                   ("Quiet: YouTube won't turn it up, so it will sound weaker than other videos." if lufs < -20 else
                    f"YouTube will turn this down to about {LOUDNESS_GUIDE:.0f} LUFS." if louder else "A typical level for YouTube."),
                   "low", "Raise the mix level, then listen." if lufs < -20 else "")
        if peak is None:
            _check(checks, "audio.peak", "audio", "not_checked", "Peak level", "ffmpeg didn't report a value.")
        elif peak >= 0:
            _check(checks, "audio.peak", "audio", "warning", f"True peak {peak:.1f} dBTP: likely clipping",
                   "Samples reach full scale; listen for crackles on loud parts.", "high", "Lower the mix gain.")
        elif peak > rules["peak_dbtp"]:
            _check(checks, "audio.peak", "audio", "warning", f"True peak {peak:.1f} dBTP",
                   f"Above {rules['peak_dbtp']} dBTP: may distort after YouTube's re-encode.", "low", "Leave ~1 dB headroom.")
        else:
            _check(checks, "audio.peak", "audio", "pass", f"True peak {peak:.1f} dBTP")
        audio_checks(checks, found, rules, issue)
    return _finish(result)


def visual_checks(checks: list, found: dict, rules: dict, total: float, issue) -> None:
    """Sharpness, exposure, colour cast, borders and repeated shots from the sampled frames. Everything here is a
    heuristic: a warning to review, never a fail (footage can be soft, dark or graded on purpose)."""
    step = 1 / rules["sample_fps"]
    in_black = lambda t: any(a - step <= t <= b + step for a, b in found["black"])  # noqa: E731
    samples = [x for x in found["samples"] if not in_black(x["t"])]
    note = f"{len(found['samples'])} frames sampled ({rules['sample_fps']} per second), not every frame."
    if not samples:
        for d, title in (("visual.sharpness", "Sharpness"), ("visual.exposure", "Exposure"), ("visual.colour", "Colour"),
                         ("visual.border", "Borders")):
            _check(checks, d, "visual", "not_checked", title, "No frames could be sampled.")
        return
    # flat frames (one colour, title cards fading) have no edges to judge sharpness by
    textured = [x for x in samples if x.get("blur") is not None and (x.get("yhigh", 0) - x.get("ylow", 0)) > 30]
    for x in textured:  # blurdetect gives nan when it finds no edges at all: on a frame with contrast that's the softest
        if x["blur"] != x["blur"]:
            x["blur"] = float("inf")
    if not has_filter("blurdetect"):
        _check(checks, "visual.sharpness", "visual", "not_checked", "Sharpness", "This FFmpeg has no blurdetect filter (needs 5.1+).")
    elif not textured:
        _check(checks, "visual.sharpness", "visual", "not_checked", "Sharpness", "No detailed frames to judge.")
    else:
        soft = stretches([x["t"] for x in textured if x["blur"] > rules["blur"]], step, rules["blur_sec"])
        for a, b in soft:
            worst = max(x["blur"] for x in textured if a <= x["t"] < b)
            issue("visual.sharpness", "visual", f"Soft or blurry picture {_clock(a)}–{_clock(b)}",
                  f"Blur score up to {'max (no edges found)' if worst == float('inf') else f'{worst:.0f}'} (sharp footage is about 4; threshold {rules['blur']:.0f}). {note}",
                  "Fine for a deliberate soft look or motion blur; otherwise use a sharper clip.", a, min(b, total), "low")
        if not soft:
            _check(checks, "visual.sharpness", "visual", "pass", "Picture is sharp", note)
    dark = stretches([x["t"] for x in samples if x.get("yavg", 128) < rules["dark"]], step, rules["exposure_sec"])
    bright = stretches([x["t"] for x in samples if x.get("yavg", 128) > rules["bright"]], step, rules["exposure_sec"])
    for a, b in dark:
        issue("visual.exposure", "visual", f"Very dark picture {_clock(a)}–{_clock(b)}",
              "Average brightness is low; details may be lost on phone screens.",
              "Fine for a night or moody look; otherwise brighten the clip or pick another.", a, min(b, total), "low")
    for a, b in bright:
        issue("visual.exposure", "visual", f"Very bright picture {_clock(a)}–{_clock(b)}",
              "Average brightness is very high; highlights may be blown out.",
              "Check the clip for washed-out areas.", a, min(b, total), "low")
    if not dark and not bright:
        _check(checks, "visual.exposure", "visual", "pass", "Exposure looks normal", note)
    us = [x["uavg"] - 128 for x in samples if x.get("uavg") is not None]
    vs = [x["vavg"] - 128 for x in samples if x.get("vavg") is not None]
    if us and vs:
        u, v = sum(us) / len(us), sum(vs) / len(vs)
        tint = ("blue" if u > 0 else "yellow") if abs(u) >= abs(v) else ("red/magenta" if v > 0 else "green")
        cast = max(abs(u), abs(v)) > rules["cast"]
        _check(checks, "visual.colour", "visual", "warning" if cast else "pass",
               f"Possible {tint} colour cast" if cast else "No strong colour cast",
               f"Average chroma offset U {u:+.0f}, V {v:+.0f} over the whole video. A deliberate grade can look like this.",
               "low" if cast else "info", "Review the colour; ignore if it's the intended look." if cast else "")
    framed = [x for x in samples if x.get("cw") and x.get("ch") and x.get("yavg", 0) > 30]
    if framed:
        full_w, full_h = found["frame"]  # the sampled frame's size (scaled to 480 wide)
        bars = [x for x in framed if x["cw"] < full_w * rules["border"] or x["ch"] < full_h * rules["border"]]
        if len(bars) >= rules["border_share"] * len(framed):
            kind = "top and bottom" if sum(x["ch"] < full_h * rules["border"] for x in bars) >= len(bars) / 2 else "left and right"
            a = bars[0]["t"]
            issue("visual.border", "visual", f"Black bars ({kind}) through most of the video",
                  f"In {len(bars)} of {len(framed)} sampled frames the picture doesn't fill the frame.",
                  "Use fill/crop instead of fit, or footage in the video's orientation.", a, min(a + step, total), "medium")
        else:
            _check(checks, "visual.border", "visual", "pass", "Picture fills the frame", note)
    else:
        _check(checks, "visual.border", "visual", "not_checked", "Borders", "No bright-enough frames to measure.")
    if not rules["duplicates"]:
        _check(checks, "visual.repeat", "visual", "not_checked", "Repeated shots", "Not used for this profile (the cover repeats by design).")
    elif len(found["sigs"]) < 2:
        _check(checks, "visual.repeat", "visual", "not_checked", "Repeated shots", "Too few frames sampled.")
    else:
        reps = repeated_shots(found["sigs"])
        for later, earlier in reps[:5]:
            issue("visual.repeat", "visual", f"Shot at {_clock(later)} repeats the one at {_clock(earlier)}",
                  "The two shots look nearly the same (compared as tiny thumbnails).",
                  "Fine for a callback or loop; otherwise use a different clip.", later, min(later + step, total), "low")
        if not reps:
            _check(checks, "visual.repeat", "visual", "pass", "No repeated shots", note)


def audio_checks(checks: list, found: dict, rules: dict, issue) -> None:
    """Sudden loudness jumps, left/right balance and mono compatibility. Measured on the final mix: without stems
    nothing here can say whether the voice or the music is the cause."""
    m = [(t, v) for t, v in found["momentary"] if v > -70]
    secs: dict[int, list[float]] = {}
    for t, v in m:
        secs.setdefault(int(t), []).append(v)
    level = {k: sum(v) / len(v) for k, v in secs.items() if len(v) >= 5}
    # A drop into quiet is a pause or the ending fading out, which every video has: not counted. Coming out of a pause,
    # the sound is compared with how loud it was before the pause, so the voice resuming isn't a jump but an effect
    # or the music bursting in is (also after a quiet opening, where there's nothing louder to compare with).
    jumps, before = [], None  # before: the last second that wasn't quiet
    for k in sorted(level):
        if k - 1 in level and level[k - 1] > -60:
            quiet_then = level[k - 1] < rules["quiet_lufs"]
            ref = before if quiet_then and before is not None else level[k - 1]
            d = level[k] - ref
            if abs(d) > rules["loud_jump_lu"] and not (d < 0 and level[k] < rules["quiet_lufs"]):
                jumps.append((k, d))
        if level[k] >= rules["quiet_lufs"]:
            before = level[k]
    if not level:
        _check(checks, "audio.jumps", "audio", "not_checked", "Loudness changes", "No loudness readings.")
    for k, d in jumps[:5]:
        _check(checks, "audio.jumps", "audio", "warning", f"Sudden {'jump' if d > 0 else 'drop'} of {abs(d):.0f} LU at {_clock(k)}",
               "Loudness changes sharply from one second to the next.", "low",
               "Listen here: fine for a drop or a punch-in; otherwise smooth the transition.", k - 1, k + 1)
    if level and not jumps:
        _check(checks, "audio.jumps", "audio", "pass", "No sudden loudness jumps", f"Threshold: {rules['loud_jump_lu']} LU within a second (drops into a pause and the ending aren't counted)")
    rms = found["rms"]
    if len(rms) >= 2:
        left, right = rms.get(1, -120.0), rms.get(2, -120.0)
        gap = left - right
        if abs(gap) > rules["imbalance_db"]:
            _check(checks, "audio.balance", "audio", "warning", f"{'Left' if gap > 0 else 'Right'} channel is {abs(gap):.1f} dB louder",
                   f"RMS left {left:.1f} dB, right {right:.1f} dB.", "medium", "Check the pan of the voice and music.")
        else:
            _check(checks, "audio.balance", "audio", "pass", "Left and right are balanced", f"{abs(gap):.1f} dB apart")
        mono = found["mono_rms"]
        if mono is not None:
            loss = (left + right) / 2 - mono
            if loss > rules["mono_loss_db"]:
                _check(checks, "audio.mono", "audio", "warning", f"Sound drops {loss:.0f} dB when played in mono",
                       "Left and right partly cancel (phase). Phone speakers often play mono.", "high",
                       "Check for an inverted channel or a too-wide stereo effect.")
            else:
                _check(checks, "audio.mono", "audio", "pass", "Plays fine in mono", f"{max(loss, 0):.1f} dB lower in mono")
    else:
        _check(checks, "audio.balance", "audio", "not_checked", "Stereo balance", "Mono audio track: nothing to balance.")


def _finish(result: dict, not_yet=NOT_YET) -> dict:
    if result["stage"] == "render" and not any(c["category"] == "rights" for c in result["checks"]):
        owner = result.pop("rights_of", None)
        if owner:
            from . import rights

            rights.check(*owner, result["checks"], _check)
        else:
            _check(result["checks"], "rights.youtube", "rights", "not_checked", "Copyright (Content ID) and ad suitability",
                   "Only YouTube Studio can check these: upload privately or unlisted and wait for its checks.")
    for n, (category, title) in enumerate(not_yet):
        _check(result["checks"], f"later.{category}.{n}", category, "not_checked", title, "Not part of this inspector yet: review it yourself.")
    for c in result["checks"]:
        c["stage"] = result["stage"]
    return _recount(result)


def _recount(result: dict) -> dict:
    counts = {s: sum(c["status"] == s for c in result["checks"]) for s in ("fail", "warning", "pass", "not_checked")}
    result["counts"] = counts
    result["verdict"] = "fail" if counts["fail"] else "warning" if counts["warning"] else "pass"
    if result["cancelled"] or result.get("error"):
        result["verdict"] = "incomplete"
    return result


def outdated(report: dict, path: Path) -> bool:
    """True when `path` is no longer the file the report was made from (re-rendered, replaced or deleted)."""
    fp = report.get("fingerprint")
    if not fp or not path.is_file():
        return True
    st = path.stat()
    if st.st_size == fp["size"] and st.st_mtime == fp["mtime"]:
        return False
    return st.st_size != fp["size"] or fingerprint(path)["sha256"] != fp["sha256"]  # touched but maybe identical


# ---------- targets (which file, which profile) ----------

def _target(scope: str, name: str, file: str = "") -> tuple[Path, str, dict, str]:
    """(video path, profile, expected format, URL prefix of its folder) for a client-chosen video; only finished
    videos in the library, never an arbitrary path."""
    if scope == "video":
        folder = (OUTPUT_DIR / name).resolve()
        if folder.parent != OUTPUT_DIR.resolve() or not folder.is_dir():
            raise HTTPException(404, "Video not found.")
        try:
            meta = json.loads((folder / "meta.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            meta = {}
        kind = meta.get("kind", "video")
        w, h = frame_size(meta.get("aspect", "16:9" if kind == "long_video" else "9:16"))
        profile = "lyric" if kind == "music_video" else "short"
        return folder / "video.mp4", profile, {"width": w, "height": h, "fps": FPS}, f"/media/{folder.name}"
    if scope == "song":
        from . import lyricvideo

        folder = lyricvideo._folder(name)
        sizes = {"lyric_full.mp4": (1920, 1080), "instrumental.mp4": (1920, 1080), "short_chorus.mp4": (1080, 1920)}
        if file not in sizes:
            raise HTTPException(400, "Unknown lyric video file.")
        expect = {"width": sizes[file][0], "height": sizes[file][1], "fps": 30}
        song = lyricvideo._audio(folder)
        if file == "lyric_full.mp4" and song:
            try:
                from .render import duration

                expect["duration"] = round(duration(song), 2)
            except Exception:
                pass  # unreadable song: the length check just has no target
        return folder / "out" / file, "lyric" if file != "short_chorus.mp4" else "short", expect, f"/songs/{folder.name}/out"
    raise HTTPException(400, "Unknown video type.")


def _report_path(video: Path) -> Path:
    return video.parent / "quality" / f"{video.stem}.json"


HISTORY = 10  # earlier reports kept per video


def _history_dir(rp: Path) -> Path:
    return rp.parent / "history" / rp.stem


def archive(rp: Path) -> None:
    """Move the current report into history (without its evidence frames, which the next run replaces)."""
    try:
        rep = json.loads(rp.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return
    for c in rep.get("checks", []):
        c.pop("evidence", None)
    folder = _history_dir(rp)
    folder.mkdir(parents=True, exist_ok=True)
    stamp = re.sub(r"[^0-9T]", "", rep.get("created", "")) or "unknown"
    (folder / f"{stamp}.json").write_text(json.dumps(rep, ensure_ascii=False), encoding="utf-8")
    for extra in sorted(folder.glob("*.json"))[:-HISTORY]:
        extra.unlink(missing_ok=True)


def _review_path(rp: Path) -> Path:
    return rp.with_name(f"{rp.stem}.review.json")


def _reviews(rp: Path) -> dict:
    try:
        data = json.loads(_review_path(rp).read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def apply_reviews(rep: dict, reviews: dict) -> dict:
    """Your dispositions on the report's issues, by stable id. "fixed" holds only until a check made after you
    marked it: if that check still finds the issue it's reopened; if not, it's listed as resolved."""
    found = {c["id"] for c in rep["checks"] if c["status"] in ("warning", "fail")}
    for c in rep["checks"]:
        r = reviews.get(c["id"])
        if not r or c["status"] not in ("warning", "fail"):
            continue
        if r["disposition"] == "fixed" and rep["created"] > r["at"]:
            c["disposition"], c["reopened"] = "unreviewed", True  # re-checked and still there
        else:
            c["disposition"] = r["disposition"]
    rep["resolved"] = [{"id": i, "title": r.get("title", i)} for i, r in reviews.items()
                       if r["disposition"] == "fixed" and rep["created"] > r["at"] and i not in found]
    return rep


def _run(job_id: str, path: Path, profile: str, expect: dict, rights_of: tuple[str, str] | None = None) -> None:
    job = _jobs[job_id]

    def say(fraction, detail=""):
        with _lock:
            job.update(progress=fraction, detail=detail)

    with _lock:
        job["status"] = "running"
    try:
        rp = _report_path(path)
        archive(rp)
        for old in rp.parent.glob(f"{path.stem}-*.jpg"):  # the last run's evidence frames
            old.unlink(missing_ok=True)
        rep = inspect_file(path, profile, expect, _cancel.get(job_id), say, rights_of)
        try:
            rp.parent.mkdir(exist_ok=True)
            rp.write_text(json.dumps(rep, ensure_ascii=False, indent=2), encoding="utf-8")
        except OSError as e:
            raise RuntimeError(f"Couldn't save the report ({e.strerror or e}). Is the disk full or the folder read-only?") from e
        with _lock:
            job.update(status="done", step=1, progress=1.0, detail="Cancelled: partial report" if rep["cancelled"] else "Done")
    except Exception as e:
        traceback.print_exc()
        with _lock:
            job.update(status="error", error=str(e).strip().splitlines()[-1] if str(e).strip() else repr(e))
    finally:
        _cancel.pop(job_id, None)


# ---------- API ----------

@router.post("/api/inspect/{scope}/{name}")
def start_inspection(scope: str, name: str, file: str = ""):
    path, profile, expect, _ = _target(scope, name, file)
    if not path.is_file():
        raise HTTPException(404, "This video hasn't been rendered.")
    job_id = uuid.uuid4().hex[:10]
    _cancel[job_id] = threading.Event()
    with _lock:
        _jobs[job_id] = {"id": job_id, "kind": "inspect", "status": "queued", "step": 0, "log": [],
                         "title": f"Quality check: {path.name}", "target": f"{scope}/{name}/{file}"}
    _pool.submit(_run, job_id, path, profile, expect, (scope, name))
    return {"id": job_id}


@router.post("/api/inspect/jobs/{job_id}/cancel")
def cancel_inspection(job_id: str):
    event = _cancel.get(job_id)
    if not event:
        raise HTTPException(404, "No inspection running with that id.")
    event.set()
    return {"cancelled": job_id}


@router.get("/api/inspect/{scope}/{name}")
def get_inspection(scope: str, name: str, file: str = ""):
    path, _, _, base = _target(scope, name, file)
    rp = _report_path(path)
    target = f"{scope}/{name}/{file}"
    with _lock:  # a run still going for this video
        job = next((j["id"] for j in _jobs.values() if j.get("kind") == "inspect" and j.get("target") == target
                    and j["status"] in ("queued", "running")), None)
    try:
        rep = json.loads(rp.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"report": None, "job": job}
    rep["outdated"] = outdated(rep, path)
    apply_reviews(rep, _reviews(rp))
    if scope in ("video", "song"):  # the rights rows follow the checklist, which can change without the file changing
        from . import rights

        rep["checks"] = [c for c in rep["checks"] if c["category"] != "rights"]
        fresh: list = []
        rights.check(scope, name, fresh, _check)
        rep["checks"] += [{**c, "stage": "render"} for c in fresh]
        _recount(rep)
    rep["base"] = base  # evidence frames: <API><base>/<evidence>
    return {"report": rep, "job": job}


@router.get("/api/inspect/rules")
def get_rules():
    return {name: {"rules": rules_for(name), "defaults": {k: v for k, v in d.items() if editable(v)}}
            for name, d in defaults().items()}


@router.put("/api/inspect/rules")
def put_rules(body: dict):
    """Overrides per rule set; a key back at its default (or null) is dropped. Unknown sets/keys are refused."""
    known, out = defaults(), {}
    for name, values in body.items():
        if name not in known or not isinstance(values, dict):
            raise HTTPException(400, f"Unknown rule set: {name}")
        for k, v in values.items():
            base = known[name].get(k)
            if base is None or not editable(base):
                raise HTTPException(400, f"{name}.{k} can't be changed.")
            if v is None or v == base:
                continue
            if isinstance(base, bool) != isinstance(v, bool) or not isinstance(v, (int, float)):
                raise HTTPException(400, f"{name}.{k} must be {'true/false' if isinstance(base, bool) else 'a number'}.")
            if not isinstance(base, bool) and isinstance(base, (int, float)) and base > 0 and v <= 0:
                raise HTTPException(400, f"{name}.{k} must be above 0.")
            out.setdefault(name, {})[k] = v
    RULES_FILE.write_text(json.dumps(out, indent=2), encoding="utf-8")
    return get_rules()


DISPOSITIONS = ("unreviewed", "reviewed", "dismissed", "fixed")


class Review(BaseModel):
    disposition: str


@router.put("/api/inspect/{scope}/{name}/issues/{issue_id}")
def review_issue(scope: str, name: str, issue_id: str, body: Review, file: str = ""):
    """Mark one issue of the current report reviewed / dismissed / fixed (or back to unreviewed)."""
    if body.disposition not in DISPOSITIONS:
        raise HTTPException(400, f"disposition must be one of {', '.join(DISPOSITIONS)}")
    path, _, _, _ = _target(scope, name, file)
    rp = _report_path(path)
    try:
        rep = json.loads(rp.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        raise HTTPException(404, "No report for this video yet.")
    issue = next((c for c in rep["checks"] if c["id"] == issue_id), None)
    if not issue:
        raise HTTPException(404, "That issue isn't in the current report.")
    reviews = _reviews(rp)
    if body.disposition == "unreviewed":
        reviews.pop(issue_id, None)
    else:
        reviews[issue_id] = {"disposition": body.disposition, "title": issue["title"],
                             "at": datetime.now().isoformat(timespec="seconds")}
    _review_path(rp).write_text(json.dumps(reviews, ensure_ascii=False, indent=2), encoding="utf-8")
    return get_inspection(scope, name, file)


@router.get("/api/inspect/{scope}/{name}/history")
def inspection_history(scope: str, name: str, file: str = ""):
    path, _, _, _ = _target(scope, name, file)
    out = []
    for f in sorted(_history_dir(_report_path(path)).glob("*.json"), reverse=True):
        try:
            rep = json.loads(f.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        out.append({"id": f.stem, "created": rep.get("created"), "verdict": rep.get("verdict"), "counts": rep.get("counts")})
    return {"history": out}


@router.get("/api/inspect/{scope}/{name}/history/{entry}")
def inspection_history_entry(scope: str, name: str, entry: str, file: str = ""):
    if not re.fullmatch(r"[0-9T]+|unknown", entry):
        raise HTTPException(400, "Bad history entry.")
    path, _, _, _ = _target(scope, name, file)
    try:
        rep = json.loads((_history_dir(_report_path(path)) / f"{entry}.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        raise HTTPException(404, "No such earlier report.")
    rep["outdated"], rep["archived"] = True, True
    return {"report": rep}
