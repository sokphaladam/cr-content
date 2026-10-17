"""FFmpeg rendering: per-scene clips -> concatenated video -> captions + music burned in."""
import json
import math
import random
import subprocess
from pathlib import Path

from .config import FPS, HEIGHT, WIDTH
from .visuals import IMAGE_EXTS

GRADIENT_PALETTES = [
    ("0x1e3c72", "0x2a5298", "0x6a11cb"),
    ("0x0f2027", "0x203a43", "0x2c5364"),
    ("0x42275a", "0x734b6d", "0xb24592"),
    ("0x134e5e", "0x71b280", "0x0b3d2e"),
    ("0x232526", "0x414345", "0x8e0e00"),
]


def run(cmd: list[str], cwd: Path | None = None) -> None:
    # stdin=DEVNULL: ffmpeg reads stdin for key commands; it must never touch ours (the desktop app's keep-alive pipe)
    proc = subprocess.run(cmd, cwd=cwd, stdin=subprocess.DEVNULL, capture_output=True, text=True,
                          encoding="utf-8", errors="replace")
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg failed ({proc.returncode}):\n{' '.join(cmd)}\n{proc.stderr[-2000:]}")


def run_progress(cmd: list[str], seconds: float, progress, cwd: Path | None = None) -> None:
    """run(), calling `progress` with 0..1 as FFmpeg gets through `seconds` of output (read from -progress)."""
    import tempfile

    with tempfile.TemporaryFile() as err:
        proc = subprocess.Popen([cmd[0], "-progress", "pipe:1", "-nostats", *cmd[1:]], cwd=cwd,
                                stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=err, text=True,
                                encoding="utf-8", errors="replace")
        for line in proc.stdout:
            key, _, value = line.strip().partition("=")
            if key in ("out_time_us", "out_time_ms") and value.isdigit() and seconds > 0:
                progress(min(int(value) / 1e6 / seconds, 1.0))  # both are microseconds (FFmpeg's naming)
        code = proc.wait()
        if code != 0:
            err.seek(0)
            raise RuntimeError(f"ffmpeg failed ({code}):\n{' '.join(cmd)}\n"
                               f"{err.read().decode('utf-8', 'replace')[-2000:]}")


def duration(path: Path) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", str(path)],
        stdin=subprocess.DEVNULL, capture_output=True, text=True, check=True,
    ).stdout
    return float(json.loads(out)["format"]["duration"])


def _media_input(media: Path | None, length: float, start: float, size: tuple[int, int]) -> list[str]:
    """ffmpeg input args for a scene's clip (looped from `start`), photo (held for `length`) or, with no media,
    a slowly moving gradient."""
    W, H = size
    if media and media.suffix.lower() in IMAGE_EXTS:
        return ["-framerate", str(FPS), "-loop", "1", "-t", f"{length:.3f}", "-i", str(media)]
    if media:
        return ["-stream_loop", "-1", *(["-ss", f"{start:.3f}"] if start > 0 else []), "-i", str(media)]
    c0, c1, c2 = random.choice(GRADIENT_PALETTES)
    return ["-f", "lavfi", "-i", f"gradients=s={W}x{H}:r={FPS}:c0={c0}:c1={c1}:c2={c2}:n=3:speed=0.015"]


CUT_ZOOMS = [1.0, 1.28, 1.12, 1.4, 1.18]  # the framings a clip punches between at its cuts (like fx.FRAMINGS)


def _pace_filter(W: int, H: int, impacts: list[float], cuts: list[float]) -> str:
    """Filter for a scene's pacing (pacing.impacts / pacing.cuts): at each cut the shot punches in or out to the next
    framing; on each hit it zooms in hard, shakes and flashes white for a few frames. "null" without either."""
    impacts = [b for b in impacts if b >= 0]
    cuts = [c for c in cuts if c > 0]
    if not impacts and not cuts:
        return "null"
    T = f"(in/{FPS})"  # zoompan counts input frames; eq has the time itself (t)

    def hits(time: str) -> str:
        return "+".join(f"if(gte({time},{b:.3f}),exp(-({time}-{b:.3f})*7),0)" for b in impacts) or "0"

    strike = hits(T)
    n = "+".join(f"gte({T},{c:.3f})" for c in cuts) or "0"
    framing = "1"
    for k in range(len(CUT_ZOOMS) - 1, 0, -1):
        framing = f"if(eq(mod({n},{len(CUT_ZOOMS)}),{k}),{CUT_ZOOMS[k]},{framing})"
    z = f"({framing})*(1+0.11*({strike}))"
    x = f"iw/2-iw/zoom/2+iw/zoom*0.025*({strike})*sin({T}*91)"
    y = f"ih/2-ih/zoom/2+ih/zoom*0.02*({strike})*sin({T}*73)"
    flash = f"0.85*pow({hits('t')},4)" if impacts else "0"
    return (f"zoompan=z='{z}':x='{x}':y='{y}':d=1:s={W}x{H}:fps={FPS},"
            f"eq=brightness='{flash}':eval=frame,setsar=1,format=yuv420p")


def _cover(W: int, H: int) -> str:
    return f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},setsar=1,fps={FPS},format=yuv420p"


def render_scene(footage: Path | None, voice: Path | None, length: float, out: Path, start: float = 0.0,
                 size: tuple[int, int] = (WIDTH, HEIGHT), look: str = "", drift: int = 0, layout: str = "fill",
                 footage2: Path | None = None, broll: list[tuple[Path, float, float]] = (),
                 bright: bool = False, impacts: list[float] = (), cuts: list[float] = ()) -> None:
    """One scene: background cropped to `size` (9:16 by default) and looped/trimmed to the narration length.

    voice=None renders a silent track (music videos add the song in finalize); `start` skips into a video
    clip, so one clip can fill several shots without repeating the same frames. `look`: a colour grade from
    styles.LOOKS (music videos), so clips from different sources look like one film. `drift`: 1 or -1 slowly
    pans a video clip right or left across the shot, like a camera move; 0 keeps it still.
    `layout`: fill (cropped to the frame), fit (the whole clip over a blurred copy of itself) or split (`footage`
    on top, `footage2` below). `broll`: (clip or photo, at, seconds) cutaways that cover the frame for a while.
    """
    W, H = size
    fit = _cover(W, H)
    if drift:
        # 6% bigger than the frame, then the crop window glides from one side to the other over the shot
        frames = max(round(length * FPS), 1)
        x = f"(iw-ow)*n/{frames}" if drift > 0 else f"(iw-ow)*(1-n/{frames})"
        fit = (f"scale={round(W * 1.06) // 2 * 2}:{round(H * 1.06) // 2 * 2}:force_original_aspect_ratio=increase,"
               f"fps={FPS},crop={W}:{H}:x='{x}':y='(ih-oh)/2',setsar=1,format=yuv420p")
    if look:
        from .styles import look_filter
        grade = look_filter(look)
    elif bright:
        # the opening shot is what people see in the feed for under a second: lift it instead of darkening it
        # (the hook and captions have their own box and outline, so they stay readable)
        grade = "eq=brightness=0.03:contrast=1.06:saturation=1.25"
    else:
        grade = "eq=brightness=-0.06:saturation=1.1"  # slight darken so white captions always stay readable
    photo = bool(footage and footage.suffix.lower() in IMAGE_EXTS)
    inputs = _media_input(footage, length, start, size)
    if layout == "split":
        inputs += _media_input(footage2, length, 0.0, size)
        half = H // 2 // 2 * 2
        vf = f"[0:v]{_cover(W, half)}[top];[1:v]{_cover(W, H - half)}[bot];[top][bot]vstack,{grade}[base]"
    elif layout == "fit" and footage:
        vf = (f"[0:v]fps={FPS},split[a][b];[a]{_cover(W, H)},boxblur=24:2,eq=brightness=-0.18[bg];"
              f"[b]scale={W}:{H}:force_original_aspect_ratio=decrease,setsar=1[fg];"
              f"[bg][fg]overlay=(W-w)/2:(H-h)/2,format=yuv420p,{grade}[base]")
    elif photo:
        # still photo: slow "Ken Burns" push-in so the scene doesn't look frozen
        frames = round(length * FPS)
        vf = (f"[0:v]scale={W * 2}:{H * 2}:force_original_aspect_ratio=increase,"
              f"crop={W * 2}:{H * 2},"
              f"zoompan=z='min(1+{0.18 / max(frames, 1):.6f}*on,1.18)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
              f":d=1:s={W}x{H}:fps={FPS},setsar=1,format=yuv420p,"
              + (f"{grade}[base]" if look or bright else "eq=brightness=-0.06[base]"))
    elif footage:
        vf = f"[0:v]{fit},{grade}[base]"
    else:
        vf = f"[0:v]{fit}[base]"

    # cutaways: each one timed to start `at` seconds in and laid over the frame while it lasts
    current = "base"
    for k, (clip, at, seconds) in enumerate(broll):
        n_inputs = sum(1 for a in inputs if a == "-i")
        inputs += _media_input(clip, seconds, 0.0, size)
        vf += (f";[{n_inputs}:v]{_cover(W, H)},trim=duration={seconds:.3f},setpts=PTS-STARTPTS+{at:.3f}/TB,{grade}[b{k}];"
               f"[{current}][b{k}]overlay=enable='between(t,{at:.3f},{at + seconds:.3f})':eof_action=pass[o{k}]")
        current = f"o{k}"
    vf += f";[{current}]{_pace_filter(W, H, impacts, cuts)}[v]"

    audio_index = sum(1 for a in inputs if a == "-i")
    audio_in = ["-i", str(voice)] if voice else ["-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo"]
    run(["ffmpeg", "-y", "-hide_banner", *inputs, *audio_in,
         "-filter_complex", f"{vf};[{audio_index}:a]aresample=44100,apad[a]",
         "-map", "[v]", "-map", "[a]", "-t", f"{length:.3f}",
         "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
         "-c:a", "aac", "-b:a", "192k", "-ar", "44100", "-ac", "2",
         str(out)])


def concat(clips: list[Path], workdir: Path, out_name: str) -> Path:
    listing = workdir / "concat.txt"
    listing.write_text("".join(f"file '{c.name}'\n" for c in clips), encoding="utf-8")
    run(["ffmpeg", "-y", "-hide_banner", "-f", "concat", "-safe", "0", "-i", listing.name,
         "-c", "copy", out_name], cwd=workdir)
    return workdir / out_name


MAX_RATE, BUF_SIZE = "12M", "24M"  # the final video's bitrate ceiling

# Loudness. Shorts and Reels play back to back at about -14 LUFS; a quieter video sounds weak next to them (the
# platforms turn loud videos down, but never quiet ones up). The voice is set to VOICE_LUFS first and the music
# MUSIC_BELOW dB under it (then ducked further while the voice speaks), so the voice always stays on top; the
# finished mix is then brought to TARGET_LUFS with its peaks held under TRUE_PEAK.
TARGET_LUFS = -14.0
TRUE_PEAK = -1.0  # dBTP
VOICE_LUFS = -16.0
MUSIC_BELOW = 13.0  # dB under the voice


def loudness(path: Path, stream: str = "a:0") -> float:
    """Integrated loudness (LUFS) of a file's audio; -70 for silence or no audio."""
    proc = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(path), "-map", f"0:{stream}?",
                           "-af", "loudnorm=print_format=json", "-f", "null", "-"],
                          stdin=subprocess.DEVNULL, capture_output=True, text=True, encoding="utf-8", errors="replace")
    tail = proc.stderr[proc.stderr.rfind("{"):]
    try:
        value = float(json.loads(tail[:tail.find("}") + 1])["input_i"])
    except (ValueError, KeyError):
        return -70.0
    return value if value > -70 else -70.0


def _gain(measured: float, target: float, most: float = 24.0) -> float:
    """dB to move `measured` LUFS to `target`, at most `most` dB up (silence is left alone)."""
    return 0.0 if measured <= -69 else min(target - measured, most)


def _mix_audio(workdir: Path, video_name: str, music: Path | None, music_volume: float,
               soundtrack: Path | None, effects: list[tuple[Path, float, float]]) -> str:
    """Mix the voice (the video's own audio), ducked music and sound effects, or a music video's song, into a WAV
    at TARGET_LUFS. Returns its name in workdir."""
    raw, final = "mix_raw.wav", "mix.wav"
    stereo = "aresample=44100,aformat=channel_layouts=stereo"
    cmd = ["ffmpeg", "-y", "-hide_banner"]
    if soundtrack:
        cmd += ["-i", str(soundtrack.resolve()), "-filter_complex", f"[0:a]{stereo}[a]"]
    else:
        voice_db = _gain(loudness(workdir / video_name), VOICE_LUFS)
        parts = [f"[0:a]{stereo},volume={voice_db:.2f}dB[voice]"]
        cmd += ["-i", video_name]
        mixed = ["[voice]"]
        if music:
            # music_volume (0.25 by default, as before) nudges the level around MUSIC_BELOW
            music_db = _gain(loudness(music), VOICE_LUFS - MUSIC_BELOW) + 20 * math.log10(max(music_volume, 0.01) / 0.25)
            cmd += ["-stream_loop", "-1", "-i", str(music.resolve())]
            parts[0] = f"[0:a]{stereo},volume={voice_db:.2f}dB,asplit=2[voice][key]"
            parts += [f"[1:a]{stereo},volume={music_db:.2f}dB[bg]",
                      "[bg][key]sidechaincompress=threshold=0.03:ratio=6:attack=15:release=350[duck]"]
            mixed.append("[duck]")
        for k, (path, at, vol) in enumerate(effects):
            idx = (2 if music else 1) + k  # inputs: 0 the video, 1 the music (if any), then the effects
            cmd += ["-i", str(path.resolve())]
            ms = max(round(at * 1000), 0)
            # effects sit at voice level, a little under it (vol 1 = the hook's hit)
            parts.append(f"[{idx}:a]{stereo},adelay={ms}|{ms},volume={vol * 0.55:.3f}[fx{k}]")
            mixed.append(f"[fx{k}]")
        if len(mixed) > 1:
            parts.append(f"{''.join(mixed)}amix=inputs={len(mixed)}:duration=first:normalize=0[a]")
        else:
            parts[-1] = parts[-1].rsplit("[", 1)[0] + "[a]"
        cmd += ["-filter_complex", ";".join(parts)]
    run([*cmd, "-map", "[a]", "-c:a", "pcm_s16le", raw], cwd=workdir)
    # the finished mix to TARGET_LUFS, its peaks limited (the gain is measured, so it's exact rather than pumping)
    gain = _gain(loudness(workdir / raw), TARGET_LUFS)
    limit = 10 ** (TRUE_PEAK / 20)
    run(["ffmpeg", "-y", "-hide_banner", "-i", raw, "-af",
         f"volume={gain:.2f}dB,alimiter=limit={limit:.4f}:attack=5:release=60:level=false",
         "-c:a", "pcm_s16le", final], cwd=workdir)
    (workdir / raw).unlink(missing_ok=True)
    return final


def _with_emoji(workdir: Path, ass_name: str) -> str:
    """The subtitles to burn: `ass_name` with its emoji drawn in colour (emoji.emojify_ass), as a copy next to it."""
    from .emoji import emojify_ass

    ass = (workdir / ass_name).read_text(encoding="utf-8")
    drawn = emojify_ass(ass, workdir / "fonts")
    if drawn == ass:
        return ass_name
    name = f"{Path(ass_name).stem}.emoji.ass"
    (workdir / name).write_text(drawn, encoding="utf-8")
    return name


def finalize(workdir: Path, video_name: str, ass_name: str, out: Path,
             music: Path | None, music_volume: float = 0.25, soundtrack: Path | None = None,
             fade_out: float = 0.0, effects: list[tuple[Path, float, float]] = (), progress=None) -> None:
    """Burn captions, mix the audio (voice, ducked music, sound effects) at -14 LUFS, and write a web-optimized mp4.

    soundtrack replaces the video's own audio entirely (a music video's song); music is then ignored.
    fade_out: seconds the picture fades to black at the end (a music video's outro).
    effects: (sound file, start second, volume) sound effects (sfx.impact_track).
    progress: called with 0..1 during the final encode (minutes for a full song).
    Runs inside workdir with relative names so the subtitles filter avoids Windows drive-letter escaping.
    """
    # complex (HarfBuzz) shaping is required for Khmer subscripts/vowel reordering; "auto" picks simple
    vf = f"ass={_with_emoji(workdir, ass_name)}:fontsdir=fonts:shaping=complex"
    if fade_out > 0:
        length = duration(workdir / video_name)
        vf += f",fade=t=out:st={max(length - fade_out, 0):.3f}:d={fade_out:.3f}"
    mix = _mix_audio(workdir, video_name, music, music_volume, soundtrack, list(effects))
    cmd = ["ffmpeg", "-y", "-hide_banner", "-i", video_name, "-i", mix,
           "-filter_complex", f"[0:v]{vf}[v]", "-map", "[v]", "-map", "1:a"]
    # quality-based, but capped: film grain and particles otherwise push 1080p to ~37 Mbps (1.3 GB for a song), and
    # YouTube/TikTok re-encode to far less anyway (YouTube recommends 8-12 Mbps for 1080p uploads)
    cmd += ["-c:v", "libx264", "-preset", "medium", "-crf", "20", "-maxrate", MAX_RATE, "-bufsize", BUF_SIZE,
            "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", "-shortest", str(out.resolve())]
    if progress:
        run_progress(cmd, duration(workdir / video_name), progress, cwd=workdir)
    else:
        run(cmd, cwd=workdir)


def thumbnail(video: Path, at: float, out: Path, workdir: Path, ass_name: str | None = None,
              size: tuple[int, int] = (WIDTH, HEIGHT), image: Path | None = None) -> None:
    """One frame of `video` (or the photo `image`) as a JPEG cover, graded, with the headline from `ass_name`
    (in workdir) on top.

    Runs inside workdir with relative names, like finalize(), so the ass filter avoids drive-letter escaping.
    """
    # punchier than the video itself: covers are seen tiny in a feed, so lift contrast/colour and sharpen
    W, H = size
    vf = (f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},setsar=1,"
          f"eq=contrast=1.08:saturation=1.3,unsharp=5:5:0.8")
    if ass_name:
        # darker edges pull the eye to the headline and keep it readable on busy frames
        vf += f",eq=brightness=-0.05,vignette=angle=PI/4.5,ass={_with_emoji(workdir, ass_name)}:fontsdir=fonts:shaping=complex"
    source = ["-i", str(image.resolve())] if image else ["-ss", f"{at:.2f}", "-i", str(video.resolve())]
    run(["ffmpeg", "-y", "-hide_banner", *source,
         "-frames:v", "1", "-vf", vf, "-q:v", "2", str(out.resolve())], cwd=workdir)
