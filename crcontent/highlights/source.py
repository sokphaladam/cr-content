"""What Smart Highlights works from: the finished video, its song audio, the lyrics with word timing, title, artist.

A short-studio music video folder has all of it: song.json (sections + lyrics), lyrics.json (word timing, maybe
corrected by hand), work/joined.mp4 (the picture before the lyrics were burned in) and, in the song folder its
meta.json points to, song.mp3. Any other video works too, given its lyrics: they're forced-aligned to the audio.
"""
import json
from dataclasses import dataclass, field
from pathlib import Path

from ..config import LANGS, OUTPUT_DIR
from ..render import duration, run


@dataclass
class Source:
    video: Path                      # the finished video
    clean: Path | None               # the same picture without burned-in lyrics (short-studio music videos)
    audio: Path                      # the song, in sync with the video
    out: Path                        # where the analysis, covers and report go
    title: str
    artist: str
    lang: str
    song: object | None              # lyrics.SongScript
    lines: list = field(default_factory=list)  # align.LyricLine, absolute times
    timing: str = ""                 # where the lyric timing came from
    meta: dict = field(default_factory=dict)
    duration: float = 0.0
    size: tuple[int, int] = (0, 0)


def _size(video: Path) -> tuple[int, int]:
    import subprocess

    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height",
                          "-of", "csv=p=0", str(video)], capture_output=True, text=True, check=True).stdout
    w, h = out.strip().split(",")[:2]
    return int(w), int(h)


def load(target: Path, lyrics_file: Path | None = None, title: str = "", artist: str = "", lang: str = "",
         log=print) -> Source:
    """`target`: a short-studio output folder, or a video file (then `lyrics_file` is needed for the lyric score)."""
    from ..align import _forced_timing, _lines, demucs_available, load_lines, save_lines
    from ..lyrics import SongScript, parse_lyrics
    from ..pipeline import neon_title

    target = Path(target)
    if target.is_dir():
        job, video = target, target / "video.mp4"
        out = job / "highlights"
    else:
        job, video = target.parent, target
        out = job / f"{target.stem}-highlights"
    if not video.exists():
        raise FileNotFoundError(f"No video at {video}")
    out.mkdir(parents=True, exist_ok=True)
    meta = json.loads((job / "meta.json").read_text(encoding="utf-8")) if (job / "meta.json").exists() else {}
    total = duration(video)

    # the song's audio: the song folder's mix when it lines up with the video, else the video's own sound
    song_dir = OUTPUT_DIR / meta["song"] if meta.get("song") else None
    mix = song_dir / "song.mp3" if song_dir and (song_dir / "song.mp3").exists() else None
    if mix and abs(duration(mix) - total) < 0.5:
        audio = mix
    else:
        audio = out / "audio.wav"
        if not audio.exists():
            run(["ffmpeg", "-y", "-v", "error", "-i", str(video), "-vn", "-ac", "1", "-ar", "44100", str(audio)])

    song, lines, timing = None, [], ""
    if lyrics_file:  # lyrics given: forced alignment to this video's audio (cached; delete lyrics.json to redo)
        song = SongScript(title=title or video.stem, genre="", mood="", bpm=0, vocal="", styles=[], avoid=[],
                          sections=parse_lyrics(Path(lyrics_file).read_text(encoding="utf-8")), caption="", hashtags=[])
        cached = out / "lyrics.json"
        lines = load_lines(cached) or []
        if not lines:
            log("      forced-aligning the lyrics to the audio (stable-ts" +
                (", vocals isolated with Demucs)" if demucs_available() else ")"))
            extra = {"denoiser": "demucs"} if demucs_available() else {}
            lines = _forced_timing(audio, _lines(song), lang or "en", extra, total)
            save_lines(lines, cached)
        timing = "forced alignment (stable-ts)"
    elif (job / "song.json").exists():
        song = SongScript.load(job / "song.json")
        lines = load_lines(job / "lyrics.json") or []
        timing = {"edited": "word timing checked by hand", "exact": "the song generator's word timing",
                  "whisper": "Whisper alignment"}.get(meta.get("timing", ""), meta.get("timing", "")) or "lyrics.json"

    if song is not None and not title:
        title = neon_title(song.title)
    lang = lang or meta.get("lang") or "en"
    clean = job / "work" / "joined.mp4"
    clean = clean if clean.exists() and abs(duration(clean) - total) < 1.0 else None
    return Source(video, clean, audio, out, title or video.stem, artist, lang if lang in LANGS else "en", song,
                  lines, timing, meta, total, _size(video))
