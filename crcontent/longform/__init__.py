"""Script to Video: a long-form YouTube video (1920x1080) from a script .md.

parse.py (scene tables -> scenes.json) -> voice.py (voiceover per scene) -> timing.py (scene = voice + padding;
every timestamp, chapters included, recomputed from the real audio) -> footage.py (your media, then stock, then a
placeholder card) -> storyboard.py (storyboard.html to check and swap footage) ... you approve ... -> render.py
(scenes, crossfades, text cards, ducked music, -14 LUFS) -> extras.py (captions.srt, description.txt, credits.txt).
Settings: <data folder>/longform.json (settings.py).

make_storyboard() runs everything up to the storyboard and stops; render_video() only runs on an approved one.
"""
import json
import shutil
from datetime import datetime
from pathlib import Path

STEPS = 7


def media_folder(slug: str, cfg: dict) -> Path:
    from .settings import folder

    return folder(cfg["footage"]["media_dir"]) / slug


def make_storyboard(script_md: Path, log=print, job: Path | None = None) -> Path:
    """Steps 1-5 for `script_md`, in a new output folder (or again in `job`). Returns the job folder."""
    from ..config import OUTPUT_DIR
    from ..pipeline import slugify
    from . import footage, settings, storyboard, timing, voice
    from .parse import parse, stamp

    cfg = settings.load()
    log(f"[1/{STEPS}] Reading {Path(script_md).name}")
    script = parse(Path(script_md))
    for note in script.notes:
        log(f"      note: {note}")
    from ..packaging import fluff_opening

    fluff = fluff_opening(" ".join(s.voiceover for s in script.scenes[:2]))
    if fluff:
        log(f"      ! the opening has {' and '.join(fluff)}: viewers leave in the first seconds; start with the payoff")
    log(f"      \"{script.title}\" ({script.lang}): {len(script.scenes)} scenes, "
        f"{sum(1 for s in script.scenes if s.rank)} title cards, {len(script.chapters)} chapters, "
        f"planned {stamp(script.scenes[-1].planned)}+")
    if job is None:
        stamp_now = datetime.now().strftime("%Y%m%d-%H%M%S")
        job = OUTPUT_DIR / f"{stamp_now}-{script.lang}-{slugify(script.title)}"
        job.mkdir(parents=True)
        (job / "meta.json").write_text(json.dumps({
            "kind": "long_video", "lang": script.lang, "title": script.title, "topic": script.title,
            "script": str(Path(script_md).resolve()), "created": datetime.now().isoformat(timespec="seconds"),
        }, ensure_ascii=False, indent=2), encoding="utf-8")
    (job / storyboard.APPROVAL).unlink(missing_ok=True)  # a new storyboard needs approving again
    shutil.copy(script_md, job / "script.md")
    script.save(job / "scenes.json")
    media = media_folder(script.slug, cfg)

    log(f"[2/{STEPS}] Voiceover ({cfg['voice']['engine']})")
    voices = voice.make_voices(script, media, job / "voice", cfg, log=log)
    (job / "voice.json").write_text(json.dumps([v.to_json() for v in voices], ensure_ascii=False), encoding="utf-8")

    log(f"[3/{STEPS}] Timing")
    tl = timing.build(script, voices, cfg)
    (job / "timeline.json").write_text(json.dumps(tl.to_json(), ensure_ascii=False, indent=2), encoding="utf-8")
    log(f"      {stamp(tl.total)} long (planned {stamp(tl.planned_total)}); chapters: "
        + ", ".join(f"{stamp(c['at'])} {c['title']}" for c in tl.chapters))
    for note in tl.notes:
        log(f"      ! {note}")

    log(f"[4/{STEPS}] Footage ({', '.join(cfg['footage']['sources'])}; your files in {media})")
    plans = footage.plan_queries(script, log=log)
    entries = footage.choose(script, plans, tl.slots, media, job / "storyboard", cfg, log=log)
    (job / "footage.json").write_text(json.dumps(entries, ensure_ascii=False, indent=2), encoding="utf-8")
    flagged = sum(1 for e in entries if e["flags"])
    log(f"      {sum(1 for e in entries if e['chosen']['source'] == 'own')} of yours, "
        f"{sum(1 for e in entries if e['chosen']['source'] not in ('own', 'placeholder', 'card', 'montage'))} "
        f"from libraries, {sum(1 for e in entries if e['chosen']['source'] == 'card')} cards, "
        f"{sum(1 for e in entries if e['chosen']['source'] == 'montage')} montages; {flagged} flagged")

    log(f"[5/{STEPS}] Storyboard")
    page = storyboard.write(job, media)
    log(f"      {page}")
    log("      check it, swap what's wrong, then approve: python make.py --storyboard \"" + str(job) + "\"")
    return job


def render_video(job: Path, log=print) -> Path:
    """Steps 6-7 for an approved storyboard. Returns video.mp4."""
    from ..tts import Word
    from . import extras, storyboard, video
    from .parse import stamp

    job = Path(job)
    if not storyboard.approved(job):
        raise RuntimeError("The storyboard isn't approved (or changed since it was): check it and approve it first "
                           f"(python make.py --storyboard \"{job}\").")
    cfg, script, tl, entries = _load(job)
    voices = {v["scene"]: [Word(**w) for w in v["words"]]
              for v in json.loads((job / "voice.json").read_text(encoding="utf-8"))}
    log(f"[6/{STEPS}] Render")
    made = video.render(job, script, tl, entries, voices, cfg, log=log)
    log(f"[7/{STEPS}] Captions, description, credits")
    extras.write(job, script, tl, entries, made, log=log)
    shutil.rmtree(job / "work", ignore_errors=True)  # near-lossless intermediates: gigabytes for a long video
    log(f"Done: {job / 'video.mp4'} ({stamp(tl.total)})")
    return job / "video.mp4"


def _load(job: Path):
    from . import settings
    from .parse import Script
    from .timing import Timeline

    cfg = settings.load()
    script = Script.load(job / "scenes.json")
    tl = Timeline.from_json(json.loads((job / "timeline.json").read_text(encoding="utf-8")))
    entries = json.loads((job / "footage.json").read_text(encoding="utf-8"))
    return cfg, script, tl, entries


def _save(job: Path, entries: list[dict], cfg: dict, script) -> None:
    from . import storyboard

    (job / "footage.json").write_text(json.dumps(entries, ensure_ascii=False, indent=2), encoding="utf-8")
    storyboard.write(job, media_folder(script.slug, cfg))


def _index(script, n: int) -> int:
    for i, s in enumerate(script.scenes):
        if s.n == n:
            return i
    raise KeyError(f"No scene {n}.")


def pick_footage(job: Path, n: int, item_key: str, log=print) -> dict:
    """Scene `n` uses its alternative `item_key` (storyboard: "Use this")."""
    from . import footage

    cfg, script, tl, entries = _load(job)
    i = _index(script, n)
    item = next((a for a in entries[i]["alternatives"] if footage.key(a) == item_key), None)
    if item is None:
        raise KeyError(f"Scene {n} has no alternative {item_key}.")
    footage.use(entries[i], item, script.scenes[i], tl.slots[i].length, cfg, job / "storyboard", log=log)
    _save(job, entries, cfg, script)
    return entries[i]


def search_footage(job: Path, n: int, query: str, log=print) -> dict:
    """New alternatives for scene `n` from other search words (storyboard: "Search again")."""
    from . import footage

    cfg, script, tl, entries = _load(job)
    i = _index(script, n)
    taken = {footage.key(e["chosen"]) for e in entries}
    footage.research(entries[i], query, tl.slots[i].length, cfg, taken, log=log)
    _save(job, entries, cfg, script)
    return entries[i]


def use_own_file(job: Path, n: int, upload: Path, name: str) -> dict:
    """Scene `n` uses the clip or photo `upload` (storyboard: "Upload your own"): saved as media/<script>/scene-NN.<ext>,
    an earlier file of yours for that scene is set aside in removed/, not deleted. Returns the scene's new entry."""
    import shutil
    from datetime import datetime

    from ..visuals import IMAGE_EXTS, VIDEO_EXTS
    from . import footage

    ext = Path(name).suffix.lower()
    if ext not in (*VIDEO_EXTS, *IMAGE_EXTS):
        raise ValueError(f"Use a video ({', '.join(sorted(VIDEO_EXTS))}) or a photo ({', '.join(sorted(IMAGE_EXTS))}).")
    cfg, script, tl, entries = _load(job)
    i = _index(script, n)
    media = media_folder(script.slug, cfg)
    media.mkdir(parents=True, exist_ok=True)
    while old := footage.own_media(media, n):
        (media / "removed").mkdir(exist_ok=True)
        shutil.move(str(old), str(media / "removed" / f"{datetime.now():%Y%m%d-%H%M%S}-{old.name}"))
    shutil.copy(upload, media / f"scene-{n:02d}{ext}")
    entries[i]["chosen"]["file"] = ""  # so the reload below sees a new file even when it has the old one's name
    footage.reload_own(entries, script, media, tl.slots, cfg, job / "storyboard")
    _save(job, entries, cfg, script)
    return entries[i]


def reload_media(job: Path) -> tuple[list[dict], int]:
    """Use the files put in media/<script>/ since the storyboard was made (storyboard: "Reload my files")."""
    from . import footage

    cfg, script, tl, entries = _load(job)
    found = footage.reload_own(entries, script, media_folder(script.slug, cfg), tl.slots, cfg, job / "storyboard")
    _save(job, entries, cfg, script)
    return entries, found
