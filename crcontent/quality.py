"""Video Quality Inspector, final-render stage: checks the exported file itself (not the project) with ffprobe and one
ffmpeg analysis pass, and saves a report next to it in quality/<stem>.json. Never writes to the video.

Every check ends as pass / warning / fail / not_checked; a check that couldn't run is not_checked, never pass.
"""
import hashlib
import json
import re
import shutil
import subprocess
import threading
import traceback
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, HTTPException

from .config import FPS, OUTPUT_DIR, frame_size

router = APIRouter()

# Per-workflow thresholds. Size comes from the video's own settings (aspect), not from here.
PROFILES = {
    "short": {"label": "Shorts", "black_sec": 0.5, "freeze_sec": 2.0, "silence_sec": 1.5, "silence_db": -50,
              "peak_dbtp": -1.0, "av_drift_warn": 0.3, "av_drift_fail": 2.0},
    # songs often open quietly and hold still pictures longer
    "lyric": {"label": "Lyric video", "black_sec": 1.0, "freeze_sec": 4.0, "silence_sec": 3.0, "silence_db": -50,
              "peak_dbtp": -1.0, "av_drift_warn": 0.3, "av_drift_fail": 2.0},
}
LOUDNESS_GUIDE = -14.0  # YouTube plays back louder mixes turned down to about this; guidance, not a rule
NOT_YET = [  # shown as not_checked so nobody reads the report as covering them
    ("visual", "Blur, exposure and colour"), ("visual", "Letterboxing and crop"),
    ("captions", "Caption / lyric placement and timing"), ("storytelling", "Hook, pacing and payoff"),
    ("rights", "Music and footage rights (YouTube Studio runs Content ID)"),
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
    item = {"id": detector if start is None else f"{detector}@{start:.2f}", "stage": "render", "category": category,
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


def analyze(path: Path, has_video: bool, has_audio: bool, total: float, rules: dict,
            cancel: threading.Event | None = None, report=None) -> dict:
    """One decode of the whole file: black and frozen stretches, silence, loudness, decode errors."""
    cmd = ["ffmpeg", "-hide_banner", "-nostdin", "-i", str(path)]
    if has_video:
        cmd += ["-vf", f"blackdetect=d={rules['black_sec']}:pix_th=0.10,freezedetect=n=-60dB:d={rules['freeze_sec']}"]
    if has_audio:
        cmd += ["-af", f"silencedetect=n={rules['silence_db']}dB:d={rules['silence_sec']},"
                       "ebur128=peak=true:framelog=quiet"]
    cmd += ["-f", "null", "-"]
    found = {"black": [], "freeze": [], "silence": [], "errors": [], "lufs": None, "lra": None, "peak": None}
    proc = subprocess.Popen(cmd, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
                            text=True, encoding="utf-8", errors="replace")  # text mode splits ffmpeg's \r stats lines
    freeze = silence = None
    in_summary = None
    try:
        for line in proc.stderr:
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
            elif "Summary:" in line:
                in_summary = True
            elif in_summary and (m := re.match(r"\s*(I|LRA|Peak):\s+(-?[\d.]+|-inf)", line)):
                found[{"I": "lufs", "LRA": "lra", "Peak": "peak"}[m[1]]] = _num(m[2]) if m[2] != "-inf" else None
            elif m := re.search(r"time=(\d+):(\d+):([\d.]+)", line):
                if report and total:
                    report(min(1.0, (int(m[1]) * 3600 + int(m[2]) * 60 + float(m[3])) / total))
            elif re.search(r"error|corrupt|invalid data|non-existing|concealing", line, re.I) and len(found["errors"]) < 20:
                found["errors"].append(line.strip())
        code = proc.wait()
    finally:
        if proc.poll() is None:
            proc.kill()
    # a stretch still running at the end of the file has no end line
    if freeze is not None:
        found["freeze"].append((freeze, total))
    if silence is not None:
        found["silence"].append((silence, total))
    found["exit_code"] = code
    return found


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


def inspect_file(path: Path, profile: str, expect: dict, cancel: threading.Event | None = None, report=None) -> dict:
    """The report for the rendered file at `path`. expect: width, height, fps, and optionally duration (seconds the
    video should last, e.g. the song's length)."""
    rules = PROFILES[profile]
    checks: list[dict] = []
    result = {"stage": "render", "profile": profile, "profile_label": rules["label"], "file": path.name,
              "created": datetime.now().isoformat(timespec="seconds"), "expect": expect, "checks": checks,
              "cancelled": False, "sampled": "every frame decoded once (ffmpeg); no frame-by-frame image analysis"}
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
    detected = ("decode.errors", "visual.black", "visual.freeze", "audio.silence", "audio.loudness", "audio.peak")
    if not (video or audio) or total <= 0:
        for d in detected:
            _check(checks, d, "technical", "not_checked", d, "No stream to analyse.")
        return _finish(result)
    try:
        say(0.05, "Decoding the whole file (black, frozen, silent, loudness)")
        found = analyze(path, bool(video), bool(audio), total, rules, cancel,
                        lambda f: say(0.05 + 0.85 * f, f"Analysing {_clock(f * total)} / {_clock(total)}"))
    except Cancelled:
        result["cancelled"] = True
        for d in detected:
            _check(checks, d, "technical", "not_checked", d, "Cancelled before this ran.")
        return _finish(result)

    if found["exit_code"] != 0 or found["errors"]:
        _check(checks, "decode.errors", "technical", "fail", f"Decode errors ({len(found['errors'])})",
               "\n".join(found["errors"][:5]) or f"ffmpeg exited with {found['exit_code']}", "critical",
               "The file is damaged. Render it again.")
    else:
        _check(checks, "decode.errors", "technical", "pass", "Decodes cleanly from start to end")

    evidence_dir = path.parent / "quality"
    evidence_dir.mkdir(exist_ok=True)
    shots = 0

    def issue(detector, category, title, desc, rec, a, b, severity="medium"):
        nonlocal shots
        item = _check(checks, detector, category, "warning", title, desc, severity, rec, a, b)
        if video and shots < 10:  # keep the folder small
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
    return _finish(result)


def _finish(result: dict) -> dict:
    for n, (category, title) in enumerate(NOT_YET):
        _check(result["checks"], f"later.{category}.{n}", category, "not_checked", title, "Not part of this inspector yet: review it yourself.")
    counts = {s: sum(c["status"] == s for c in result["checks"]) for s in ("fail", "warning", "pass", "not_checked")}
    result["counts"] = counts
    result["verdict"] = "fail" if counts["fail"] else "warning" if counts["warning"] else "pass"
    if result["cancelled"]:
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


def _run(job_id: str, path: Path, profile: str, expect: dict) -> None:
    job = _jobs[job_id]

    def say(fraction, detail=""):
        with _lock:
            job.update(progress=fraction, detail=detail)

    with _lock:
        job["status"] = "running"
    try:
        rep = inspect_file(path, profile, expect, _cancel.get(job_id), say)
        rp = _report_path(path)
        rp.parent.mkdir(exist_ok=True)
        rp.write_text(json.dumps(rep, ensure_ascii=False, indent=2), encoding="utf-8")
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
    _pool.submit(_run, job_id, path, profile, expect)
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
    rep["base"] = base  # evidence frames: <API><base>/<evidence>
    return {"report": rep, "job": job}
