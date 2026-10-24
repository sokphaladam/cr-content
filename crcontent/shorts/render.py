"""Render a Short: 1080x1920, 30 fps, H.264 + AAC at -14 LUFS (NVENC, CPU fallback), hard cuts.

Every beat is its clip cropped to 9:16 around the animal (the hook's own 2 s window, where Gemini placed the animal),
then rule 3's loop tail: the last rules.loop_tail seconds cut back to the hook clip, ending on the very frame the
Short opens with, so when YouTube loops it the motion carries straight on into the first line. The voice, the music
bed (your tracks, no fade-out: a fade would mark the loop) and the text layer (captions.py) go on top.
"""
import shutil
from pathlib import Path

from ..config import FPS, LANGS
from ..longform.parse import Script
from ..longform.timing import Timeline
from ..longform.video import _fonts, encoder, music_bed, playlist, voice_track
from ..pipeline import _install_font, progress_reporter
from ..render import duration, finalize, render_scene, run
from ..tts import Word
from ..visuals import IMAGE_EXTS
from . import captions


def _start(chosen: dict, length: float) -> float:
    """Where a beat's clip starts: the hook's chosen window, else past a stock clip's fade-in when there's room."""
    if "start" in chosen:
        return float(chosen["start"])
    path = Path(chosen["file"])
    return 0.0 if path.suffix.lower() in IMAGE_EXTS else min(0.5, max(duration(path) - length, 0.0))


def beat_clip(chosen: dict, length: float, out: Path, size: tuple[int, int], look: str, start: float | None = None,
              bright: bool = False) -> None:
    focus = tuple(chosen["focus"]) if chosen.get("focus") else None
    render_scene(Path(chosen["file"]), None, length, out, start=_start(chosen, length) if start is None else start,
                 size=size, look=look, bright=bright, focus=focus)


def frame_lengths(ends: list[float]) -> list[float]:
    """Clip lengths in whole frames for clips ending at `ends` (seconds into the video): each edge is rounded to its
    nearest frame on the running timeline, so the cuts never drift from the voice, and the stream-copy join keeps an
    even 30 fps (clips cut between frames leave it with uneven timestamps)."""
    edges = [0, *(round(e * FPS) for e in ends)]
    return [(b - a) / FPS for a, b in zip(edges, edges[1:])]


def join(clips: list[Path], work: Path, out_name: str) -> Path:
    """The clips' pictures back to back, every frame kept, at a constant 30 fps. The concat demuxer (render.concat)
    places each clip after its audio, which runs a few ms past the picture, and a frame is lost at that seam; the
    concat filter joins the pictures by their own lengths. Re-encoded near-lossless, once: seconds for a Short."""
    inputs = [a for c in clips for a in ("-i", c.name)]
    streams = "".join(f"[{k}:v]" for k in range(len(clips)))
    run(["ffmpeg", "-y", "-hide_banner", *inputs, "-filter_complex",
         f"{streams}concat=n={len(clips)}:v=1:a=0,fps={FPS}[v]", "-map", "[v]",
         "-c:v", "libx264", "-preset", "veryfast", "-crf", "10", "-pix_fmt", "yuv420p", out_name], cwd=work)
    return work / out_name


def loop_tail(hook: dict, tail: float) -> float:
    """Where in the hook clip the tail starts: `tail` seconds before the Short's first frame, so the cut back to the
    start continues the motion (from the first frame on when the clip has nothing before it)."""
    start = _start(hook, tail)
    return start - tail if start >= tail else start


def render(job: Path, script: Script, tl: Timeline, entries: list[dict], voices: dict[int, list[Word]], cfg: dict,
           log=print) -> dict:
    """work/ -> job/video.mp4. Returns {music, encoder, tail}."""
    rc = cfg["render"]
    size = (int(rc["width"]), int(rc["height"]))
    look = str(rc.get("look") or "")
    tail = min(float(cfg["rules"]["loop_tail"]), tl.slots[-1].length / 2)
    work = job / "work"
    if work.exists():
        shutil.rmtree(work)
    work.mkdir()

    log(f"      {len(tl.slots)} beats at {size[0]}x{size[1]}, loop tail {tail:.1f}s")
    lengths = frame_lengths([s.end for s in tl.slots[:-1]] + [tl.total - tail, tl.total])
    tail = lengths.pop()
    clips = []
    for k, (entry, slot, length) in enumerate(zip(entries, tl.slots, lengths)):
        clip = work / f"beat_{slot.scene:02d}.mp4"
        beat_clip(entry["chosen"], length, clip, size, look, bright=k == 0)  # the opening frame is lifted for the feed
        clips.append(clip)
    hook = entries[0]["chosen"]
    if hook["source"] not in ("card", "placeholder") and tail > 0:
        clip = work / "loop_tail.mp4"
        beat_clip(hook, tail, clip, size, look, start=loop_tail(hook, tail), bright=True)
        clips.append(clip)
    else:  # no hook clip to loop into: the last beat runs to the end
        render_scene(Path(entries[-1]["chosen"]["file"]), None, tail, work / "loop_tail.mp4", size=size, look=look)
        clips.append(work / "loop_tail.mp4")
    join(clips, work, "joined.mp4")
    for c in clips:
        c.unlink(missing_ok=True)

    voice_track(tl, job / "voice", work / "voice.wav")
    run(["ffmpeg", "-y", "-hide_banner", "-i", "joined.mp4", "-i", "voice.wav", "-map", "0:v", "-map", "1:a",
         "-c:v", "copy", "-c:a", "pcm_s16le", "picture.mkv"], cwd=work)

    tracks = playlist(cfg, script.title)
    bed, used = None, []
    if tracks:
        bed, used = music_bed(tracks, tl.total, work / "music.wav")
        log(f"      music: {', '.join(t.stem for t in used)}")
    else:
        from ..longform.settings import folder
        log(f"      ! no music: {folder(cfg['music']['dir'])} has no tracks (mp3, wav, m4a, flac)")

    (work / "text.ass").write_text(captions.build(script, tl, voices), encoding="utf-8")
    profile = LANGS.get(script.lang, LANGS["en"])
    for _, file in _fonts(script.lang):
        _install_font(profile, work / "fonts", file)

    enc = encoder(cfg)
    log(f"      encoding ({'NVENC' if enc == 'nvenc' else 'x264'}), -14 LUFS, captions burned in")
    final = job / "video.mp4"
    kw = dict(music=bed, music_volume=float(cfg["music"]["volume"]), fade_out=0.0, progress=progress_reporter(log))
    try:
        finalize(work, "picture.mkv", "text.ass", final, encoder=enc, **kw)
    except RuntimeError as e:
        if enc != "nvenc":
            raise
        log(f"      ! NVENC failed ({str(e).splitlines()[0][:100]}); encoding on the CPU")
        enc = "x264"
        finalize(work, "picture.mkv", "text.ass", final, encoder=enc, **kw)
    return {"music": [str(t) for t in used], "encoder": enc, "tail": tail}
