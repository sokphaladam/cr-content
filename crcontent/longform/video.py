"""Render an approved storyboard: 1920x1080, 30 fps, H.264 + AAC.

Each scene is rendered on its own (render.render_scene: the clip cropped to the frame, photos with a slow Ken Burns
push-in) with an extra crossfade's worth of picture at its end, then all are joined with short dissolves (xfade)
that start exactly at each scene's real time. The voice is laid out on its own track at those same times, so the
dissolves never shift it. On-screen text is drawn from an ASS file: a "#N NAME" line as a title card (big, centred,
over a dimmed frame), anything else as a lower third. finalize() then mixes your music ducked under the voice, brings
it to -14 LUFS and encodes (NVENC when the GPU has it, else x264).
"""
import hashlib
import json
import shutil
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from ..captions import _esc, _ts
from ..config import LANGS, SYSTEM_FONT_DIRS
from ..render import duration, finalize, nvenc_available, render_scene, run
from ..visuals import IMAGE_EXTS
from ..styles import font_path
from ..tts import Word
from .parse import Script
from .timing import Timeline

MUSIC_EXTS = (".mp3", ".wav", ".m4a", ".flac", ".ogg")
ACCENT = "&H00009FF5&"        # #F59F00 (ASS colours are BGR)
CUE_CHARS, CUE_SECONDS = 42, 4.5  # a caption cue: one readable line, at most this long on screen


def encoder(cfg: dict) -> str:
    choice = str(cfg["render"]["encoder"]).lower()
    if choice in ("cpu", "x264"):
        return "x264"
    return "nvenc" if nvenc_available() else "x264"


# ---------- captions (burned in, optional, and captions.srt) ----------

def cues(script: Script, tl: Timeline, voices: dict[int, list[Word]]) -> list[tuple[float, float, str]]:
    """The voiceover as caption cues on the video's timeline: one line of up to CUE_CHARS, split at sentence ends
    and pauses, never running into the next cue."""
    out = []
    for scene, slot in zip(script.scenes, tl.slots):
        words = voices.get(scene.n) or []
        line, start, end = [], 0.0, 0.0
        for k, w in enumerate(words):
            ws, we = slot.start + w.start, slot.start + w.end
            if line and (len(" ".join(line + [w.text])) > CUE_CHARS or we - start > CUE_SECONDS or ws - end > 0.6):
                out.append((start, end, " ".join(line)))
                line = []
            if not line:
                start = ws
            line.append(w.text)
            end = we
            if w.text[-1:] in ".?!" and len(" ".join(line)) >= 12:
                out.append((start, end, " ".join(line)))
                line = []
        if line:
            out.append((start, end, " ".join(line)))
    # each cue stays a little after its last word, up to the next one
    return [(s, min(e + 0.3, out[k + 1][0] - 0.04) if k + 1 < len(out) else e + 0.3, t)
            for k, (s, e, t) in enumerate(out)]


def _srt_time(t: float) -> str:
    ms = int(round(max(t, 0) * 1000))
    return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"


def srt(cue_list: list[tuple[float, float, str]]) -> str:
    return "\n".join(f"{k}\n{_srt_time(s)} --> {_srt_time(e)}\n{t}\n" for k, (s, e, t) in enumerate(cue_list, 1))


# ---------- on-screen text ----------

def _fonts(lang: str) -> tuple[tuple[str, str], tuple[str, str]]:
    """((family, file) for lower thirds and captions, (family, file) for title cards)."""
    if lang == "km":
        profile = LANGS["km"]
        title = ("Khmer OS Muol Light", "KhmerOSmuollight.ttf") if font_path("KhmerOSmuollight.ttf") else \
            (profile.font_name, profile.font_file)
        return (profile.font_name, profile.font_file), title
    have = lambda f: any((d / f).exists() for d in SYSTEM_FONT_DIRS)
    body = ("Segoe UI Semibold", "seguisb.ttf") if have("seguisb.ttf") else ("Arial", "arialbd.ttf")
    title = ("Segoe UI Black", "seguibl.ttf") if have("seguibl.ttf") else ("Arial Black", "ariblk.ttf")
    return body, title


def _width(text: str, file: str, px: float) -> float:
    """How wide libass draws `text` from font `file` at ASS size `px` (ascent+descent, not the em)."""
    from PIL import ImageFont

    path = font_path(file)
    if not path:
        return px * 0.56 * len(text)
    f = ImageFont.truetype(str(path), 200)
    asc, desc = f.getmetrics()
    return f.getlength(text) * px / (asc + desc)


def _box(x: float, y: float, w: float, h: float) -> str:
    return f"m {x:.0f} {y:.0f} l {x + w:.0f} {y:.0f} l {x + w:.0f} {y + h:.0f} l {x:.0f} {y + h:.0f}"


def text_ass(script: Script, tl: Timeline, cfg: dict, cue_list: list | None, carded: set[int] = frozenset()) -> str:
    """The on-screen text as ASS. `carded`: scenes showing a card that already has their text on it (no lower third)."""
    rc = cfg["render"]
    W, H = int(rc["width"]), int(rc["height"])
    (body, body_file), (title, title_file) = _fonts(script.lang)
    k = H / 1080  # sizes are designed at 1080p
    lower_px, cap_px, rank_px, name_px = round(50 * k), round(44 * k), round(92 * k), round(124 * k)
    events = []
    ev = lambda layer, s, e, style, text: events.append(f"Dialogue: {layer},{_ts(s)},{_ts(e)},{style},,0,0,0,,{text}")
    bottom = H - round((200 if cue_list else 120) * k)  # lower thirds sit above burned-in captions
    for scene, slot in zip(script.scenes, tl.slots):
        if not scene.text or (scene.n in carded and not scene.rank):
            continue
        if scene.rank:  # title card: "#10" over "GREEN HERON", the frame dimmed behind
            s = slot.start + 0.15
            e = s + min(float(rc["title_card_seconds"]), slot.length - 0.2)
            name = scene.name.upper()
            px = name_px
            while _width(name, title_file, px) > W * 0.86 and px > 40:
                px -= 4
            ev(0, s, e, "Card", f"{{\\an7\\pos(0,0)\\1c&H000000&\\1a&H70&\\bord0\\shad0\\fad(300,350)\\p1}}{_box(0, 0, W, H)}")
            ev(1, s, e, "Rank", f"{{\\an2\\pos({W / 2:.0f},{H * 0.44:.0f})\\fad(250,350)}}#{scene.rank}")
            ev(1, s, e, "Name", f"{{\\an8\\pos({W / 2:.0f},{H * 0.46:.0f})\\fs{px}\\fad(250,350)"
                                f"\\fscx94\\fscy94\\t(0,450,\\fscx100\\fscy100)}}{_esc(name)}")
            continue
        s = slot.start + min(0.45, slot.length * 0.1)
        e = s + max(min(float(rc["lower_third_seconds"]), slot.length - 0.6), 1.2)
        text, px = _esc(scene.text), lower_px
        while _width(text, body_file, px) > W * 0.6 and px > 30:
            px -= 2
        pad_x, pad_y = round(30 * k), round(20 * k)
        w = _width(text, body_file, px) + pad_x * 2
        h = px * 1.25 + pad_y * 2
        x0, y0 = round(96 * k), bottom - h
        slide = f"\\move({x0 - 40:.0f},{y0:.0f},{x0:.0f},{y0:.0f},0,300)"
        ev(0, s, e, "Box", f"{{\\an7{slide}\\1c&H141414&\\1a&H30&\\bord0\\shad0\\fad(250,300)\\p1}}{_box(0, 0, w, h)}")
        ev(1, s, e, "Box", f"{{\\an7{slide}\\1c{ACCENT}\\bord0\\shad0\\fad(250,300)\\p1}}{_box(0, 0, round(8 * k), h)}")
        ev(2, s, e, "Lower", f"{{\\an4\\move({x0 - 40 + pad_x + 8 * k:.0f},{y0 + h / 2:.0f},"
                             f"{x0 + pad_x + 8 * k:.0f},{y0 + h / 2:.0f},0,300)\\fs{px}\\fad(250,300)}}{text}")
    for s, e, t in cue_list or []:
        ev(3, s, e, "Caption", _esc(t))
    styles = [
        f"Style: Lower,{body},{lower_px},&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,0,0,7,0,0,0,1",
        f"Style: Box,{body},10,&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,0,0,7,0,0,0,1",
        f"Style: Card,{body},10,&H00000000,&H00000000,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,0,0,7,0,0,0,1",
        f"Style: Rank,{title},{rank_px},{ACCENT},&H00FFFFFF,&H00000000,&H80000000,0,0,0,0,100,100,2,0,1,0,3,2,0,0,0,1",
        f"Style: Name,{title},{name_px},&H00FFFFFF,&H00FFFFFF,&H00000000,&H80000000,0,0,0,0,100,100,2,0,1,0,4,8,0,0,0,1",
        f"Style: Caption,{body},{cap_px},&H00FFFFFF,&H00FFFFFF,&H00000000,&H90000000,0,0,0,0,100,100,0,0,1,"
        f"{3 * k:.1f},1,2,{round(160 * k)},{round(160 * k)},{round(48 * k)},1",
    ]
    return "\n".join([
        "[Script Info]", "ScriptType: v4.00+", f"PlayResX: {W}", f"PlayResY: {H}", "WrapStyle: 2",
        "ScaledBorderAndShadow: yes", "", "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, "
        "Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, "
        "MarginR, MarginV, Encoding", *styles, "", "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text", *events, ""])


# ---------- sound ----------

def voice_track(tl: Timeline, voice_dir: Path, out: Path) -> Path:
    """Every scene's voiceover at its scene's start, as one WAV as long as the video."""
    placed = [(s.start, voice_dir / s.voice) for s in tl.slots if s.voice]
    cmd, parts = ["ffmpeg", "-y", "-hide_banner"], []
    for k, (at, path) in enumerate(placed):
        cmd += ["-i", str(path)]
        ms = round(at * 1000)
        parts.append(f"[{k}:a]aresample=44100,aformat=channel_layouts=stereo,adelay={ms}|{ms}[v{k}]")
    mix = "".join(f"[v{k}]" for k in range(len(placed)))
    parts.append(f"{mix}amix=inputs={len(placed)}:duration=longest:normalize=0,apad,atrim=0:{tl.total:.3f}[a]")
    run([*cmd, "-filter_complex", ";".join(parts), "-map", "[a]", "-c:a", "pcm_s16le", str(out)])
    return out


def playlist(cfg: dict, seed: str) -> list[Path]:
    """Your tracks (music.dir), in an order that differs per video but is the same every time it's rendered."""
    from .settings import folder

    music_dir = folder(cfg["music"]["dir"])
    tracks = sorted(p for p in music_dir.glob("*") if p.suffix.lower() in MUSIC_EXTS) if music_dir.is_dir() else []
    if not tracks:
        return []
    k = int(hashlib.sha1(seed.encode()).hexdigest(), 16) % len(tracks)
    return tracks[k:] + tracks[:k]


def music_bed(tracks: list[Path], total: float, out: Path) -> tuple[Path, list[Path]]:
    """Tracks back to back with 3 s crossfades until the video is covered, faded in and out. Returns the file and
    the tracks used (for credits.txt)."""
    used, length = [], 0.0
    while length < total + 2 and len(used) < 50:
        track = tracks[len(used) % len(tracks)]
        used.append(track)
        length += duration(track) - (3.0 if len(used) > 1 else 0.0)
    cmd = ["ffmpeg", "-y", "-hide_banner"]
    for t in used:
        cmd += ["-i", str(t)]
    parts = [f"[{k}:a]aresample=44100,aformat=channel_layouts=stereo[m{k}]" for k in range(len(used))]
    last = "m0"
    for k in range(1, len(used)):
        parts.append(f"[{last}][m{k}]acrossfade=d=3:c1=tri:c2=tri[x{k}]")
        last = f"x{k}"
    parts.append(f"[{last}]atrim=0:{total:.3f},afade=t=in:d=1.5,afade=t=out:st={max(total - 4, 0):.3f}:d=4[a]")
    run([*cmd, "-filter_complex", ";".join(parts), "-map", "[a]", "-c:a", "pcm_s16le", str(out)])
    return out, list(dict.fromkeys(used))


# ---------- picture ----------

def aspect(path: Path) -> float:
    """Width / height of a clip or picture (16/9 when it can't be read)."""
    try:
        if path.suffix.lower() in IMAGE_EXTS:
            from PIL import Image
            with Image.open(path) as im:
                return im.width / im.height
        import subprocess
        got = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                              "stream=width,height", "-of", "csv=p=0", str(path)], stdin=subprocess.DEVNULL,
                             capture_output=True, text=True).stdout.strip().split(",")
        return int(got[0]) / int(got[1])
    except Exception:
        return 16 / 9


def scene_clip(chosen: dict, length: float, out: Path, size: tuple[int, int], look: str = "") -> None:
    """A scene's picture: its clip or photo cropped to the frame, or, for an old 4:3 film, a portrait or a painting
    that cropping would cut the head or the frame off, the whole of it over a blurred copy; a montage cuts through
    its parts."""
    footage = Path(chosen["file"])
    start = 0.0
    if footage.suffix.lower() not in IMAGE_EXTS:
        # stock clips often open on a fade from black: skip their first half second when there's room
        start = min(0.5, max(duration(footage) - length, 0.0))
    parts = [Path(p) for p in chosen.get("parts") or []][1:]
    if parts:
        cut = length / (len(parts) + 1)
        broll = [(p, cut * (k + 1), cut + (0.05 if k < len(parts) - 1 else 0.5)) for k, p in enumerate(parts)]
        render_scene(footage, None, length, out, start=start, size=size, look=look, broll=broll)
        return
    narrow = chosen["source"] not in ("own", "card") and aspect(footage) < (1.5 if footage.suffix.lower() not in
                                                                           IMAGE_EXTS else 1.2)
    render_scene(footage, None, length, out, start=start, size=size, look=look, layout="fit" if narrow else "fill")


JOIN_GROUP = 12  # clips dissolved together in one FFmpeg run (each open input holds decoded 1080p frames)


def _dissolve(inputs: list[str], starts: list[float], fade: float, work: Path, out_name: str) -> None:
    """`inputs` (names in work/) dissolved into each other; input k fades in at starts[k] - starts[0]."""
    cmd, parts, last = ["ffmpeg", "-y", "-hide_banner"], [], "0:v"
    for name in inputs:
        cmd += ["-i", name]
    for k in range(1, len(inputs)):
        parts.append(f"[{last}][{k}:v]xfade=transition=fade:duration={fade:.3f}:offset={starts[k] - starts[0]:.3f}[j{k}]")
        last = f"j{k}"
    run([*cmd, "-filter_complex", ";".join(parts) or "[0:v]null[j0]", "-map", f"[{last if parts else 'j0'}]", "-an",
         "-c:v", "libx264", "-preset", "veryfast", "-crf", "10", "-pix_fmt", "yuv420p", out_name], cwd=work)


def join(clips: list[Path], tl: Timeline, fade: float, work: Path, out_name: str) -> Path:
    """The scene clips joined by `fade`-second dissolves, each starting at its scene's real time.

    Every clip but the last carries `fade` seconds of extra picture, so a dissolve into scene k starting at its real
    start time leaves all later times where the timeline put them. A long video is joined in groups (a group ends
    on its last clip's extra tail, so the groups dissolve into each other the same way), keeping memory flat.
    """
    if len(clips) == 1 or fade <= 0:
        from ..render import concat
        return concat(clips, work, out_name)
    starts = [s.start for s in tl.slots]
    if len(clips) <= JOIN_GROUP:
        _dissolve([c.name for c in clips], starts, fade, work, out_name)
        return work / out_name
    groups, group_starts = [], []
    for g in range(0, len(clips), JOIN_GROUP):
        name = f"group_{g // JOIN_GROUP:02d}.mp4"
        _dissolve([c.name for c in clips[g:g + JOIN_GROUP]], starts[g:g + JOIN_GROUP], fade, work, name)
        groups.append(name)
        group_starts.append(starts[g])
    _dissolve(groups, group_starts, fade, work, out_name)
    for name in groups:
        (work / name).unlink(missing_ok=True)
    return work / out_name


def render(job: Path, script: Script, tl: Timeline, entries: list[dict], voices: dict[int, list[Word]], cfg: dict,
           log=print) -> dict:
    """work/ -> job/video.mp4. Returns what extras.py needs: {cues, music, encoder}."""
    from ..pipeline import _install_font, progress_reporter

    rc = cfg["render"]
    size = (int(rc["width"]), int(rc["height"]))
    fade = float(rc["crossfade"])
    work = job / "work"
    if work.exists():
        shutil.rmtree(work)
    work.mkdir()

    log(f"      {len(tl.slots)} scenes at {size[0]}x{size[1]}")
    clips = [work / f"scene_{s.scene:02d}.mp4" for s in tl.slots]
    last = len(tl.slots) - 1

    def one(k: int) -> None:
        # every scene but the last runs a dissolve's length longer: the next one fades in over that tail
        scene_clip(entries[k]["chosen"], tl.slots[k].length + (fade if k < last else 0.0), clips[k], size,
                   look=str(rc.get("look") or ""))
        log(f"      scene {tl.slots[k].scene:02d} rendered")

    with ThreadPoolExecutor(3) as pool:
        list(pool.map(one, range(len(clips))))
    log(f"      joining with {fade:.1f}s dissolves")
    join(clips, tl, fade, work, "joined.mp4")
    for c in clips:
        c.unlink(missing_ok=True)

    log("      voice track")
    voice_track(tl, job / "voice", work / "voice.wav")
    run(["ffmpeg", "-y", "-hide_banner", "-i", "joined.mp4", "-i", "voice.wav", "-map", "0:v", "-map", "1:a",
         "-c:v", "copy", "-c:a", "pcm_s16le", "picture.mkv"], cwd=work)

    tracks = playlist(cfg, script.title)
    bed, used = None, []
    if tracks:
        bed, used = music_bed(tracks, tl.total, work / "music.wav")
        log(f"      music: {', '.join(t.stem for t in used)}")
    else:
        from .settings import folder
        log(f"      ! no music: {folder(cfg['music']['dir'])} has no tracks (mp3, wav, m4a, flac)")

    cue_list = cues(script, tl, voices)
    burn = bool(rc["captions"])
    carded = {e["scene"] for e in entries if e["chosen"]["source"] == "card"}
    (work / "text.ass").write_text(text_ass(script, tl, cfg, cue_list if burn else None, carded), encoding="utf-8")
    (_, body_file), (_, title_file) = _fonts(script.lang)
    profile = LANGS[script.lang]
    for f in (body_file, title_file):
        _install_font(profile, work / "fonts", f)

    enc = encoder(cfg)
    log(f"      encoding ({'NVENC' if enc == 'nvenc' else 'x264'}), -14 LUFS"
        + (", music ducked under the voice" if bed else "") + (", captions burned in" if burn else ""))
    final = job / "video.mp4"
    kw = dict(music=bed, music_volume=float(cfg["music"]["volume"]), fade_out=1.0, progress=progress_reporter(log))
    try:
        finalize(work, "picture.mkv", "text.ass", final, encoder=enc, **kw)
    except RuntimeError as e:
        if enc != "nvenc":
            raise
        log(f"      ! NVENC failed ({str(e).splitlines()[0][:100]}); encoding on the CPU")
        enc = "x264"
        finalize(work, "picture.mkv", "text.ass", final, encoder=enc, **kw)
    return {"cues": cue_list, "music": [str(t) for t in used], "encoder": enc}
