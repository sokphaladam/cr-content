"""Topic (or script file) in -> finished vertical video + post metadata out."""
import json
import random
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Callable

from . import thumbs
from .captions import build_ass, build_thumbnail_ass
from .config import ASSETS_DIR, LANGS, OUTPUT_DIR, ROOT, SCENE_PAD_SEC, WINDOWS_FONTS
from .render import concat, duration, finalize, render_scene, thumbnail
from .script import VideoScript, generate_script
from .tts import synthesize
from .visuals import IMAGE_EXTS, FootagePicker


def slugify(text: str, limit: int = 40) -> str:
    slug = re.sub(r"[^\w]+", "-", text.lower(), flags=re.ASCII).strip("-")
    return (slug or "video")[:limit]


def pick_music(music: str | None) -> Path | None:
    if music == "none":
        return None
    if music:
        return Path(music)
    tracks = list((ASSETS_DIR / "music").glob("*.mp3")) if (ASSETS_DIR / "music").exists() else []
    return random.choice(tracks) if tracks else None


def _install_font(profile, fonts_dir: Path) -> None:
    fonts_dir.mkdir(exist_ok=True)
    for candidate in (ASSETS_DIR / "fonts" / profile.font_file, WINDOWS_FONTS / profile.font_file):
        if candidate.exists():
            shutil.copy(candidate, fonts_dir / candidate.name)
            return
    print(f"  ! font {profile.font_file} not found; captions will use a fallback font")


def thumbnail_source(job: Path) -> Path:
    """The caption-free work/joined.mp4 when it's still there, so the video's own captions don't show through."""
    joined = job / "work" / "joined.mp4"
    return joined if joined.exists() else job / "video.mp4"


def draw_thumbnail(job: Path, text: str, at: float, lang: str, out: Path,
                   style: str = "bold", emphasis: str = "") -> float:
    """Draw the frame at `at` seconds with `text` as a big headline (no text = plain frame) into `out`.

    Returns the frame time actually used (clamped to the video).
    """
    profile = LANGS.get(lang, LANGS["en"])
    work = job / "work"
    work.mkdir(exist_ok=True)
    source = thumbnail_source(job)
    at = max(0.0, min(at, duration(source) - 0.1))
    ass_name = None
    if text.strip():
        ass_name = f"{out.stem}.ass"
        (work / ass_name).write_text(build_thumbnail_ass(text, profile, style, emphasis), encoding="utf-8")
        if not (work / "fonts" / profile.font_file).exists():
            _install_font(profile, work / "fonts")
    out.parent.mkdir(exist_ok=True)
    thumbnail(source, at, out, work, ass_name)
    return at


def make_thumbnail(job: Path, text: str, at: float, lang: str, style: str = "bold", emphasis: str = "") -> Path:
    """(Re)draw job/thumbnail.jpg and remember the choices in meta.json."""
    out = job / "thumbnail.jpg"
    at = draw_thumbnail(job, text, at, lang, out, style, emphasis)
    meta_path = job / "meta.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else {}
    meta.update(thumb_text=text, thumb_at=round(at, 2), thumb_style=style, thumb_emphasis=emphasis)
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    return out


def suggest_thumbnails(job: Path, lang: str, count: int = 4) -> tuple[list[dict], str]:
    """Render `count` cover ideas (Claude headline x best frame x style) to job/suggest/ and save the list."""
    script = VideoScript.load(job / "script.json")
    ideas, note = thumbs.suggestions(thumbnail_source(job), script, lang, count)
    folder = job / "suggest"
    if folder.exists():
        shutil.rmtree(folder)
    for i, idea in enumerate(ideas):
        idea["file"] = f"suggest/thumb_{i}.jpg"
        idea["at"] = round(draw_thumbnail(job, idea["text"], idea["at"], lang, job / idea["file"],
                                          idea["style"], idea["emphasis"]), 2)
    (folder / "suggestions.json").write_text(json.dumps({"items": ideas, "note": note}, ensure_ascii=False, indent=2),
                                             encoding="utf-8")
    return ideas, note


def make_song(topic: str | None = None, *, song: "SongScript | None" = None, song_path: Path | None = None,
              lang: str = "en", seconds: int = 45, style: str = "", vocal: str = "",
              backend: str = "elevenlabs", stems: bool = True, script_only: bool = False,
              log: Callable[[str], None] = print) -> Path:
    """Topic (or song.json) in -> job folder with song.json, song.mp3 and optional vocal/instrumental stems."""
    from .lyrics import SongScript, generate_song
    from .song import get_backend

    if song:
        log(f"[1/2] Using edited song: {song.title}")
    elif song_path:
        song = SongScript.load(song_path)
        log(f"[1/2] Loaded song: {song.title}")
    else:
        log(f"[1/2] Writing song with Claude: {topic!r} ({LANGS[lang].name}, {seconds}s)")
        song = generate_song(topic, lang=lang, seconds=seconds, style=style, vocal=vocal)
        log(f"      -> {song.title} ({song.genre}, {song.bpm} bpm, {len(song.sections)} sections, {song.seconds}s)")

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    job = OUTPUT_DIR / f"{stamp}-{lang}-song-{slugify(topic or song.title)}"
    job.mkdir(parents=True)
    song.save(job / "song.json")
    meta = {"kind": "song", "lang": lang, "topic": topic or "", "backend": backend,
            "created": datetime.now().isoformat(timespec="seconds")}
    (job / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    if script_only:
        log(f"Song saved: {job / 'song.json'}")
        return job / "song.json"

    log(f"[2/2] Composing with {backend}" + (" + stem separation" if stems else ""))
    result = get_backend(backend).generate(song, job, stems=stems)
    meta.update(song_id=result.song_id, duration=round(duration(result.mix), 2),
                vocals=result.vocals.relative_to(job).as_posix() if result.vocals else "",
                instrumental=result.instrumental.relative_to(job).as_posix() if result.instrumental else "")
    (job / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    log(f"Done: {result.mix}  ({meta['duration']:.1f}s)")
    return result.mix


def make_music_video(job: Path, log: Callable[[str], None] = print) -> Path:
    """Composed song job folder in -> video.mp4: beat-cut footage per section, karaoke lyrics, the song as audio."""
    from .align import align_lyrics, save_lines, section_spans
    from .beats import beat_times, plan_shots
    from .captions import build_karaoke_ass
    from .lyrics import SongScript

    song = SongScript.load(job / "song.json")
    meta_path = job / "meta.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    lang = meta.get("lang", "en")
    profile = LANGS.get(lang, LANGS["en"])
    mix = job / "song.mp3"
    if not mix.exists():
        raise RuntimeError("This song hasn't been composed yet.")
    vocals = job / meta["vocals"] if meta.get("vocals") and (job / meta["vocals"]).exists() else None
    total = duration(mix)
    work = job / "work"
    if work.exists():
        shutil.rmtree(work)  # a re-render starts clean
    work.mkdir()

    # 1. When each word is sung (isolated vocals align far better than the full mix)
    log(f"[1/4] Lyric timing ({'vocals stem' if vocals else 'full mix, no vocals stem'})")
    lines, timing = align_lyrics(vocals or mix, song, lang, total, log=log)
    save_lines(lines, work / "lyrics.json")
    log(f"      -> {len(lines)} lines timed ({timing})")

    # 2. Cuts on the beat, footage per section; one clip can cover several shots of its section
    log("[2/4] Beats and footage")
    beats, beat_method = beat_times(mix, song.bpm, total, log=log)
    spans = section_spans(song, total)
    shots = plan_shots(song, spans, beats, total)
    log(f"      -> {len(shots)} shots ({beat_method})")
    picker = FootagePicker()
    per_section: dict[int, list[list]] = {}  # section -> [[clip, seconds used], ...]
    clips = []
    for i, shot in enumerate(shots):
        section = song.sections[shot.section]
        pool = per_section.setdefault(shot.section, [])
        if len(pool) < 3:  # up to 3 different clips per section, then cycle through them
            query = section.visual_query or f"{song.mood} {song.genre}"
            footage = picker.pick(query)
            pool.append([footage, 0.0])
            log(f"      {section.name}: {query!r} -> {footage.name if footage else 'gradient'}")
        entry = pool[len(clips) % len(pool)] if len(pool) >= 3 else pool[-1]
        footage, used = entry
        start = 0.0
        if footage and footage.suffix.lower() not in IMAGE_EXTS:
            length = duration(footage)
            start = used % length if length > shot.length + 0.5 else 0.0
        entry[1] = used + shot.length
        clip = work / f"shot_{i:02d}.mp4"
        render_scene(footage, None, shot.length, clip, start=start)
        clips.append(clip)
    concat(clips, work, "joined.mp4")

    # 3. Karaoke captions
    log("[3/4] Captions")
    (work / "captions.ass").write_text(build_karaoke_ass(lines, profile), encoding="utf-8")
    _install_font(profile, work / "fonts")

    # 4. Final render with the song as the soundtrack + cover + post text
    log("[4/4] Final render")
    final = job / "video.mp4"
    finalize(work, "joined.mp4", "captions.ass", final, None, soundtrack=mix)
    try:
        cover_at = thumbs.best_frames(work / "joined.mp4", 1)[0]
    except Exception:
        cover_at = min(1.0, total / 2)
    hook = next((l.text for l in lines), "")
    make_thumbnail(job, song.title, cover_at, lang)
    tags = " ".join(f"#{h}" for h in song.hashtags)
    (job / "post.txt").write_text(
        f"{song.title}\n\n{song.caption}\n\n{tags}\n\nMusic and vocals are AI-generated.\n", encoding="utf-8")
    meta = json.loads(meta_path.read_text(encoding="utf-8"))  # make_thumbnail updated it
    meta.update(timing=timing, beats=beat_method, shots=len(shots), hook=hook)
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    log(f"Done: {final}  ({total:.1f}s)")
    return final


def make_video(topic: str | None = None, *, script_path: Path | None = None, lang: str = "en",
               voice: str | None = None, scenes: int = 6, seconds: int = 45, style: str = "",
               music: str | None = None, rate: str = "+5%", script_only: bool = False,
               script: VideoScript | None = None, log: Callable[[str], None] = print) -> Path:
    profile = LANGS[lang]
    voice = voice or profile.voices[0]

    # 1. Script
    if script:
        log(f"[1/5] Using edited script: {script.title}")
    elif script_path:
        script = VideoScript.load(script_path)
        log(f"[1/5] Loaded script: {script.title}")
    else:
        log(f"[1/5] Writing script with Claude: {topic!r} ({profile.name})")
        script = generate_script(topic, lang=lang, scenes=scenes, seconds=seconds, style=style)
        log(f"      -> {script.title} ({len(script.scenes)} scenes)")

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    job = OUTPUT_DIR / f"{stamp}-{lang}-{slugify(topic or script.title)}"
    work = job / "work"
    work.mkdir(parents=True)
    script.save(job / "script.json")
    (job / "meta.json").write_text(json.dumps(
        {"lang": lang, "voice": voice, "topic": topic or "", "created": datetime.now().isoformat(timespec="seconds")},
        ensure_ascii=False, indent=2), encoding="utf-8")
    if script_only:
        log(f"Script saved: {job / 'script.json'}")
        return job / "script.json"

    # 2. Voiceover per scene (per-scene audio keeps visuals and narration aligned)
    log(f"[2/5] Voiceover ({voice})")
    timed = []
    for i, scene in enumerate(script.scenes):
        mp3 = work / f"voice_{i:02d}.mp3"
        words = synthesize(scene.narration, voice, mp3, rate=rate)
        timed.append((mp3, words, duration(mp3) + SCENE_PAD_SEC))

    # 3. Footage + scene clips
    log("[3/5] Footage and scene clips")
    picker = FootagePicker()
    clips = []
    for i, (scene, (mp3, _, length)) in enumerate(zip(script.scenes, timed)):
        chosen = (ROOT / scene.media) if scene.media else None
        if chosen and chosen.exists():
            footage = chosen
            log(f"      scene {i + 1}: your pick -> {footage.name}")
        else:
            if chosen:
                log(f"      scene {i + 1}: chosen file {scene.media} is missing, picking automatically")
            footage = picker.pick(scene.visual_query)
            log(f"      scene {i + 1}: {scene.visual_query!r} -> {footage.name if footage else 'gradient'}")
        clip = work / f"scene_{i:02d}.mp4"
        render_scene(footage, mp3, length, clip)
        clips.append(clip)
    concat(clips, work, "joined.mp4")

    # 4. Captions (timings are offset by each scene's start in the joined video)
    log("[4/5] Captions")
    caption_scenes, t = [], 0.0
    for scene, (_, words, length) in zip(script.scenes, timed):
        caption_scenes.append((t, t + length, words, scene.on_screen_text))
        t += length
    (work / "captions.ass").write_text(build_ass(caption_scenes, profile), encoding="utf-8")
    _install_font(profile, work / "fonts")

    # 5. Final render + post metadata
    log("[5/5] Final render")
    final = job / "video.mp4"
    track = pick_music(music)
    finalize(work, "joined.mp4", "captions.ass", final, track)
    try:
        cover_at = thumbs.best_frames(work / "joined.mp4", 1)[0]
    except Exception:
        cover_at = min(1.0, t / 2)
    make_thumbnail(job, script.title, cover_at, lang)

    tags = " ".join(f"#{h}" for h in script.hashtags)
    (job / "post.txt").write_text(
        f"{script.title}\n\n{script.caption}\n\n{tags}\n", encoding="utf-8")
    log(f"Done: {final}  ({t:.1f}s)")
    return final
