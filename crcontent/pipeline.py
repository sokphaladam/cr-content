"""Topic (or script file) in -> finished vertical video + post metadata out."""
import json
import random
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Callable

from .captions import build_ass, build_thumbnail_ass
from .config import ASSETS_DIR, LANGS, OUTPUT_DIR, ROOT, SCENE_PAD_SEC, WINDOWS_FONTS
from .render import concat, duration, finalize, render_scene, thumbnail
from .script import VideoScript, generate_script
from .tts import synthesize
from .visuals import FootagePicker


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


def make_thumbnail(job: Path, text: str, at: float, lang: str) -> Path:
    """(Re)draw job/thumbnail.jpg: the frame at `at` seconds with `text` as a big headline (no text = plain frame).

    Uses the caption-free work/joined.mp4 when it's still there, so the video's own captions don't show through.
    """
    profile = LANGS.get(lang, LANGS["en"])
    work = job / "work"
    work.mkdir(exist_ok=True)
    source = work / "joined.mp4" if (work / "joined.mp4").exists() else job / "video.mp4"
    at = max(0.0, min(at, duration(source) - 0.1))
    ass_name = None
    if text.strip():
        (work / "thumbnail.ass").write_text(build_thumbnail_ass(text, profile), encoding="utf-8")
        if not (work / "fonts" / profile.font_file).exists():
            _install_font(profile, work / "fonts")
        ass_name = "thumbnail.ass"
    out = job / "thumbnail.jpg"
    thumbnail(source, at, out, work, ass_name)

    meta_path = job / "meta.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else {}
    meta.update(thumb_text=text, thumb_at=round(at, 2))
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    return out


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
    make_thumbnail(job, script.title, min(1.0, t / 2), lang)

    tags = " ".join(f"#{h}" for h in script.hashtags)
    (job / "post.txt").write_text(
        f"{script.title}\n\n{script.caption}\n\n{tags}\n", encoding="utf-8")
    log(f"Done: {final}  ({t:.1f}s)")
    return final
