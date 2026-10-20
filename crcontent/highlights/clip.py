"""Step 7 — render a chosen highlight as a ready-to-post vertical video in the Library (like campaign clips).

The lyric-free picture (when the music video has one) is cut and framed 9:16, the song's lyrics for that stretch are
drawn fresh as vertical karaoke in the video's own lyric style, the hook (from the AI judge) sits at the top for the
first seconds, and render.finalize mixes and encodes it: on the GPU (NVENC) when it can, else on the CPU.
"""
import json
import re
import shutil
from dataclasses import replace
from datetime import datetime
from pathlib import Path

from ..config import FPS, HEIGHT, LANGS, OUTPUT_DIR, WIDTH
from ..render import nvenc_available, run
from .visual import crop_filter

HOOK_SECONDS = 3.0


def encoder(cfg: dict) -> str:
    want = cfg["render"].get("encoder", "auto")
    if want == "cpu":
        return "x264"
    return "nvenc" if nvenc_available() else "x264"


def _shift(lines: list, start: float, end: float) -> list:
    """The lyric lines sung inside [start, end], with times relative to the clip."""
    from ..tts import Word

    out = []
    for line in lines:
        if line.start < start - 0.05 or line.end > end + 0.05:
            continue
        words = [Word(w.text, max(0.0, w.start - start), max(0.0, w.end - start)) for w in line.words]
        out.append(replace(line, start=words[0].start, end=words[-1].end, words=words))
    return out


def _ass_text(text: str) -> str:
    return text.replace("\\", "").replace("{", "(").replace("}", ")").replace("\n", " ")


LYRIC_Y = {"low": 0.64, "middle": 0.5, "high": 0.24}  # where captions.build_karaoke_ass puts a vertical line


HOOK_BORDER = 14   # the hook's dark edge (px), drawn round every line
HOOK_MARGIN = 90   # px kept clear left and right of the hook
GAP = 0.025        # space between the hook and the lyrics (fraction of the height)
SAFE_TOP, SAFE_BOTTOM = 0.06, 0.80  # the apps draw their own buttons and caption over the bottom 20%


def _wrap(text: str, family: str, px: int, lang: str, max_w: float) -> list[str]:
    """`text` in as few lines as fit `max_w`, balanced so no line is much longer than another (at most 3)."""
    from ..captions import _balance, _text_width

    width = lambda s: _text_width(s, family, px, lang)
    words = text.split()
    for n in range(1, 4):
        lines = _balance(words, n, width)
        if max(width(l) for l in lines) <= max_w:
            return lines
    return _balance(words, 3, width)


def lyric_box(lines: list, style, profile) -> tuple[float, float]:
    """(top, bottom) of the lyrics, as fractions of the height, for the longest line of the clip: build_karaoke_ass
    centres each line on LYRIC_Y and libass wraps it at the frame width less the margins. Without lines of our own
    (the lyrics are burned into the picture) a two-line block is assumed."""
    from ..captions import KARAOKE_MARGIN, _text_width, karaoke_font

    font = karaoke_font(profile, style, (WIDTH, HEIGHT))
    max_w = WIDTH - 2 * KARAOKE_MARGIN
    rows = 2
    if lines:
        rows = max(max(1, -(-_text_width(" ".join(w.text for w in l.words), style.font, font, profile.code) // max_w))
                   for l in lines)
    # line height ~ the ASS size; plus the outline / glow and the ~16 px the line rises as it comes in
    half = (rows * font * 1.08) / 2 + max(8, font // 6) + 16
    centre = LYRIC_Y.get(style.position, 0.64) * HEIGHT
    return (centre - half) / HEIGHT, (centre + half) / HEIGHT


def place_hook(hook_rows: int, size: int, subject_y: float | None, lyrics: tuple[float, float]) -> float:
    """Top of the hook (fraction of the height): never on the lyrics, inside the safe area, and off the subject
    (a face) when it's near the top. The hook's real height counts: a two-line hook needs twice the room."""
    height = (hook_rows * size * 1.1 + 2 * HOOK_BORDER) / HEIGHT
    top_spot = SAFE_TOP + 0.04
    above = lyrics[0] - GAP - height
    below = lyrics[1] + GAP
    face_up_top = subject_y is not None and subject_y < 0.45
    spots = [above, below, top_spot] if face_up_top else [top_spot, above, below]
    for y in spots:
        clear = y + height <= lyrics[0] - GAP + 1e-6 or y >= lyrics[1] + GAP - 1e-6
        if SAFE_TOP - 1e-6 <= y and y + height <= SAFE_BOTTOM + 1e-6 and clear:
            return y
    return SAFE_TOP  # no clear spot (huge lyrics): the very top keeps the most distance


def _add_hook(ass: str, rows: list[str], font: str, size: int, top: float) -> str:
    """The hook text for the first seconds: white with a heavy dark edge, fading in and out."""
    if not rows:
        return ass
    style = re.search(r"^Style:\s*([^,]+),", ass, re.M)
    name = style.group(1) if style else "Default"
    end = f"0:00:{HOOK_SECONDS:05.2f}"
    # \q2: no wrapping by libass, the lines are already balanced (and counted for the placement)
    tags = (rf"{{\an8\pos({WIDTH // 2},{round(HEIGHT * top) + HOOK_BORDER})\fn{font}\fs{size}\b1\bord{HOOK_BORDER}"
            rf"\shad0\blur0\1c&HFFFFFF&\3c&H141414&\1a&H00&\3a&H30&\4a&HFF&\q2\fad(180,260)}}")
    # BorderStyle 3 (an opaque box) can't be switched on per line, so the box is a thick dark outline instead
    text = r"\N".join(_ass_text(r) for r in rows)
    line = f"Dialogue: 9,0:00:00.00,{end},{name},,0,0,0,,{tags}{text}\n"
    return ass.rstrip("\n") + "\n" + line


TITLE_MAX = 60  # past this, YouTube cuts the title off in the feed and search


def full_song(src) -> tuple[str, str]:
    """(artist, link to the full music video): the artist given for the song, else the YouTube channel the music
    video went up on; the link when the music video is on YouTube."""
    from ..publish import published

    yt = published(src.video.parent).get("youtube", {}) if src.video.name == "video.mp4" else {}
    return src.artist or yt.get("channel_name", ""), yt.get("url", "")


def _tag(text: str) -> str:
    return re.sub(r"[^\w]", "", text, flags=re.UNICODE)


def upload_text(src, cand, ai: dict | None, ai_credit: bool) -> dict:
    """What the clip is posted with: {title, description, hashtags, comment}.

    title: the feeling first, the song's name after it ("When she only wants a trial run 🚗💔 | She Test Drive")
    while that fits 60 characters, else the feeling alone. description: that feeling in other words, a question,
    where the full song is, the AI credit. Without the AI judge: the song's name, and its first lyric line."""
    artist, url = full_song(src)
    by = f" by {artist}" if artist else ""
    where = f"🎧 Full song: {url}" if url else f"🎧 Full song: \"{src.title}\"{by}, on the channel"
    if ai and ai.get("title"):
        feel = ai["title"].strip()
        both = f"{feel} | {src.title}"
        title = both if len(both) <= TITLE_MAX and src.title.lower() not in feel.lower() else feel
        if len(title) > TITLE_MAX:
            title = title[:TITLE_MAX].rsplit(" ", 1)[0]
        opening = [t for t in (ai.get("line", ""), ai.get("question", "")) if t.strip()]
        tags = list(ai.get("hashtags") or [])
        comment = ai.get("comment", "").strip()
    else:
        title = src.title + (f" – {artist}" if artist else "")
        opening = [f"♪ {cand.lyrics[0]}"] if getattr(cand, "lyrics", None) else []
        tags = [_tag(src.title), "newmusic", "music"]
        comment = ""
    for t in (_tag(src.title), _tag(artist)):  # the song and the artist are always tagged, so clips find each other
        if t and t.lower() not in (x.lower() for x in tags):
            tags.insert(0, t)
    parts = ["\n".join(opening), where, "Music and vocals are AI-generated." if ai_credit else ""]
    return {"title": title, "description": "\n\n".join(p for p in parts if p.strip()), "hashtags": tags[:8],
            "comment": comment}


def render(src, cand, rank: int, hook: str, ai: dict | None, cover: Path | None, cfg: dict,
           subject_y: float | None = None, log=print) -> Path:
    """One highlight as an output folder: video.mp4, thumbnail.jpg, post.txt, meta.json (+ song.json, so uploads
    are filed under Music). `subject_y`: how far down the picture's subject is (0..1), to keep the hook off it."""
    from ..captions import build_karaoke_ass
    from ..pipeline import _install_font, slugify
    from ..render import finalize
    from ..styles import FONTS, LyricStyle

    lang = src.lang
    profile = LANGS.get(lang, LANGS["en"])
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    job = OUTPUT_DIR / f"{stamp}-{lang}-hl{rank}-{slugify(src.title, 30)}"
    work = job / "work"
    work.mkdir(parents=True)
    length = cand.end - cand.start
    enc = encoder(cfg)
    use_clean = src.clean is not None and cfg["render"].get("source", "auto") != "video"
    picture = src.clean if use_clean else src.video

    # 1. the picture: the clip's stretch, framed 9:16 (the centre of a landscape frame; the whole of a vertical one).
    # A near-lossless intermediate, like the music video's shots; the one encode that matters is finalize's
    if use_clean or src.size[0] <= src.size[1]:
        vf = f"{crop_filter(src.size, WIDTH, HEIGHT).replace('flags=area', 'flags=lanczos')},setsar=1,fps={FPS}"
    else:  # burned-in landscape lyrics would be cut off by a crop: the whole frame over a blurred fill instead
        vf = (f"split[a][b];[a]scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=increase,crop={WIDTH}:{HEIGHT},"
              f"boxblur=24:2,eq=brightness=-0.12[bg];[b]scale={WIDTH}:-2:flags=lanczos[fg];"
              f"[bg][fg]overlay=(W-w)/2:(H-h)/2,setsar=1,fps={FPS}")
    codec = (["-c:v", "h264_nvenc", "-preset", "p5", "-rc", "constqp", "-qp", "10"] if enc == "nvenc"
             else ["-c:v", "libx264", "-preset", "veryfast", "-crf", "10"])
    run(["ffmpeg", "-y", "-hide_banner", "-ss", f"{cand.start:.3f}", "-t", f"{length:.3f}", "-i", str(picture),
         "-filter_complex", f"[0:v]{vf}[v]", "-map", "[v]", "-an", *codec, "-pix_fmt", "yuv420p", "picture.mp4"],
        cwd=work)

    # 2. the song for that stretch, with a few ms fade in (no click on the first beat) and a short fade out
    fade = min(0.6, max(0.25, length * 0.02))
    run(["ffmpeg", "-y", "-hide_banner", "-ss", f"{cand.start:.3f}", "-t", f"{length:.3f}", "-i", str(src.audio),
         "-af", f"afade=t=in:d=0.03,afade=t=out:st={length - fade:.3f}:d={fade:.3f}", "-ar", "48000", "song.wav"],
        cwd=work)

    # 3. lyrics as vertical karaoke, in the music video's own lyric style, plus the hook on top
    style = LyricStyle.model_validate(src.meta.get("lyric_style") or {}).clean(lang)
    # (from the finished video itself they're already burned in, so none are added)
    lines = _shift(src.lines, cand.start, cand.end) if use_clean else []
    ass = build_karaoke_ass(lines, profile, size=(WIDTH, HEIGHT), style=style)
    hook_size = round(profile.font_size * 0.8)
    rows = _wrap(hook.strip(), profile.font_name, hook_size, lang, WIDTH - 2 * HOOK_MARGIN) if hook.strip() else []
    top = place_hook(len(rows), hook_size, subject_y, lyric_box(lines, style, profile))
    ass = _add_hook(ass, rows, profile.font_name, hook_size, top)
    (work / "captions.ass").write_text(ass, encoding="utf-8")
    _install_font(profile, work / "fonts", FONTS.get(lang, FONTS["en"]).get(style.font, ""))

    log(f"      encoding on the {'GPU (NVENC)' if enc == 'nvenc' else 'CPU (x264)'}")
    try:
        finalize(work, "picture.mp4", "captions.ass", job / "video.mp4", None, soundtrack=work / "song.wav",
                 fade_out=fade, animation=bool(src.meta.get("art_style")), encoder=enc)
    except RuntimeError:
        if enc != "nvenc":
            raise
        log("      ! NVENC failed; encoding on the CPU instead")
        finalize(work, "picture.mp4", "captions.ass", job / "video.mp4", None, soundtrack=work / "song.wav",
                 fade_out=fade, animation=bool(src.meta.get("art_style")), encoder="x264")
        enc = "x264"

    if cover and cover.exists():
        shutil.copy(cover, job / "thumbnail.jpg")
    name = f"{src.title} · Highlight {rank}" + (f" ({cand.section})" if cand.section else "")
    song_json = src.video.parent / "song.json"
    if song_json.exists():  # the Library names a folder after its song.json, so the copy carries the clip's name
        song = json.loads(song_json.read_text(encoding="utf-8"))
        (job / "song.json").write_text(json.dumps({**song, "title": name}, ensure_ascii=False, indent=2),
                                       encoding="utf-8")
    post = (src.video.parent / "post.txt").read_text(encoding="utf-8") if (src.video.parent / "post.txt").exists() else ""
    up = upload_text(src, cand, ai, "AI-generated" in post)
    tags = " ".join(f"#{t}" for t in up["hashtags"])
    (job / "post.txt").write_text(f"{up['title']}\n\n{up['description']}\n\n{tags}\n", encoding="utf-8")
    extra = {"yt_comment": up["comment"]} if up["comment"] else {}  # posted under the YouTube upload (pinning is by hand)
    if hook:
        extra["thumb_text"] = hook  # the cover's headline: the hook, not the clip's library name
    (job / "meta.json").write_text(json.dumps({
        "kind": "clip", "highlight": True, "lang": lang, "aspect": "9:16", "title": name, **extra,
        "source_video": src.video.parent.name if src.video.name == "video.mp4" else str(src.video),
        "song": src.meta.get("song", ""), "start": cand.start, "end": cand.end, "rank": rank, "hook": hook,
        "section": cand.section, "encoder": enc, "duration": round(length, 2),
        "created": datetime.now().isoformat(timespec="seconds"),
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    shutil.rmtree(work, ignore_errors=True)
    return job
