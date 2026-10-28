"""Shorts Mode: a 1080x1920 YouTube Short per episode of a content plan (.xlsx), held to the channel's rules.

plan.py (Scripts / Plan sheets -> ShortPlan) -> Script to Video's own steps at 9:16 (settings.py, shorts.json):
voice per beat -> timing.py (the timeline from the real audio; hook and length rules) -> footage.py (your media, then
Pixabay, then a placeholder card; the hook beat re-picked by hook.py for an animal in motion) -> preflight.py (the
rule checks, Claude's hook judge ranked by analytics.py, a storyboard) ... you approve ... -> render.py (captions.py
text layer, the loop tail, -14 LUFS, NVENC/CPU) -> extras.py (cover.png, metadata.txt, post.txt).

make_job() runs steps 1-5 for one episode and stops at the pre-flight report; render_job() only runs once it's
approved (make.py --approve <job>).
"""
import json
import shutil
from datetime import datetime
from pathlib import Path

STEPS = 7


def media_folder(slug: str, cfg: dict) -> Path:
    from ..longform.settings import folder

    return folder(cfg["footage"]["media_dir"]) / slug


def make_job(ep, log=print, job: Path | None = None) -> Path:
    """Steps 1-5 for one ShortPlan, in a new output folder (or again in `job`). Returns the job folder."""
    from ..config import OUTPUT_DIR
    from ..longform import storyboard, voice
    from ..pipeline import slugify
    from . import footage, preflight, settings, timing

    cfg = settings.load()
    script = ep.script
    log(f"[1/{STEPS}] Ep {ep.ep}: \"{ep.title}\" ({script.lang}, {len(script.scenes)} beats)")
    for note in ep.notes:
        log(f"      note: {note}")
    if job is None:
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        job = OUTPUT_DIR / f"{stamp}-{script.lang}-ep{ep.ep:02d}-{slugify(ep.title)}"
        job.mkdir(parents=True)
        (job / "meta.json").write_text(json.dumps({
            "kind": "short", "lang": script.lang, "title": ep.title, "topic": ep.title, "ep": ep.ep,
            "created": datetime.now().isoformat(timespec="seconds"),
        }, ensure_ascii=False, indent=2), encoding="utf-8")
    (job / storyboard.APPROVAL).unlink(missing_ok=True)  # a new pre-flight needs approving again
    ep.save(job / "episode.json")
    script.save(job / "scenes.json")
    media = media_folder(script.slug, cfg)

    log(f"[2/{STEPS}] Voiceover ({cfg['voice']['engine']})")
    voices = voice.make_voices(script, media, job / "voice", cfg, log=log)

    log(f"[3/{STEPS}] Timing")
    tl = timing.timeline(script, voices, cfg)
    (job / "voice.json").write_text(json.dumps([v.to_json() for v in voices], ensure_ascii=False), encoding="utf-8")
    (job / "timeline.json").write_text(json.dumps(tl.to_json(), ensure_ascii=False, indent=2), encoding="utf-8")
    log(f"      {tl.total:.1f}s from the real voiceover (the sheet planned {tl.planned_total:.0f}s)")

    log(f"[4/{STEPS}] Footage (your files in {media}, then {', '.join(cfg['footage']['sources'])})")
    entries = footage.choose(ep, tl, media, job / "storyboard", cfg, log=log)
    ep.save(job / "episode.json")  # with its animal named
    (job / "footage.json").write_text(json.dumps(entries, ensure_ascii=False, indent=2), encoding="utf-8")

    log(f"[5/{STEPS}] Pre-flight")
    preflight.write(job, ep, tl, voices, entries, cfg, media, log=log)
    log(f"      {job / 'preflight.html'}")
    log(f"      check it, then render: python make.py --approve \"{job}\"")
    return job


FIELDS = {"line": "First line", "text": "On-screen hook"}


def apply_change(job: Path, field: str, value: str, log=print) -> dict:
    """Use a suggestion in this Short: field "line" (beat 1's voiceover) or "text" (its on-screen hook). Beat 1 is
    voiced again and the timeline rebuilt (the other beats' audio is cached), the hook clip keeps its footage but
    gets its best window for the new length, and the pre-flight runs again. Your spreadsheet isn't changed: the
    change is noted on the page. Returns the new report."""
    from ..longform import storyboard, voice
    from . import hook, plan, preflight, settings, timing

    value = " ".join((value or "").split())
    if field not in FIELDS or not value:
        raise ValueError("Nothing to apply.")
    if field == "line":
        from .judge import opening

        value = opening(value)
    job = Path(job)
    cfg = settings.load()
    ep = plan.ShortPlan.load(job / "episode.json")
    scene = ep.script.scenes[0]
    old = scene.voiceover if field == "line" else scene.text
    if field == "line":
        scene.voiceover = value
    else:
        scene.text = value
    ep.notes.append(f"{FIELDS[field]} changed: \"{old}\" → \"{value}\"")
    ep.save(job / "episode.json")
    ep.script.save(job / "scenes.json")
    (job / storyboard.APPROVAL).unlink(missing_ok=True)
    media = media_folder(ep.script.slug, cfg)
    voices = voice.make_voices(ep.script, media, job / "voice", cfg, log=log)
    tl = timing.timeline(ep.script, voices, cfg)
    entries = json.loads((job / "footage.json").read_text(encoding="utf-8"))
    hook_pick = entries[0]["chosen"]
    if hook_pick["kind"] == "video" and hook_pick["source"] not in ("card", "placeholder"):
        # keep the window Claude matched to the shot while the clip is long enough for the new length; only a clip
        # too short for it gets a new window (the best for motion alone could miss what the shot needs: the water)
        from ..render import duration

        if float(hook_pick.get("start", 0.0)) + tl.slots[0].length > duration(Path(hook_pick["file"])):
            s = hook.scan(Path(hook_pick["file"]), tl.slots[0].length)
            hook_pick.update(start=s.start, hook=s.to_json())
        for e in entries[1:]:
            if e.get("reuses_opening"):
                e["chosen"] = dict(hook_pick)
    (job / "voice.json").write_text(json.dumps([v.to_json() for v in voices], ensure_ascii=False), encoding="utf-8")
    (job / "timeline.json").write_text(json.dumps(tl.to_json(), ensure_ascii=False, indent=2), encoding="utf-8")
    (job / "footage.json").write_text(json.dumps(entries, ensure_ascii=False, indent=2), encoding="utf-8")
    log(f"      {FIELDS[field]}: \"{old}\" -> \"{value}\"; {tl.total:.1f}s now")
    return preflight.write(job, ep, tl, voices, entries, cfg, media, log=log)


def _load(job: Path):
    """(cfg, ep, tl, voices, entries, media) of a Short's job folder."""
    from ..longform.timing import Timeline
    from ..longform.voice import Voice
    from . import plan, settings

    cfg = settings.load()
    ep = plan.ShortPlan.load(job / "episode.json")
    tl = Timeline.from_json(json.loads((job / "timeline.json").read_text(encoding="utf-8")))
    voices = [Voice.from_json(v) for v in json.loads((job / "voice.json").read_text(encoding="utf-8"))]
    entries = json.loads((job / "footage.json").read_text(encoding="utf-8"))
    return cfg, ep, tl, voices, entries, media_folder(ep.script.slug, cfg)


def _refresh(job: Path, ep, tl, voices, entries: list[dict], cfg: dict, media: Path, log) -> dict:
    """Save the footage, follow the hook into beats that cut back to it, and run the pre-flight again."""
    from ..longform import footage as lf, storyboard
    from . import preflight

    for e in entries[1:]:
        if e.get("reuses_opening"):
            e["chosen"], e["match"] = dict(entries[0]["chosen"]), entries[0].get("match")
    for e in entries:
        c = e["chosen"]
        lf._thumb(Path(c["file"]), job / "storyboard" / f"scene-{e['scene']:02d}.jpg",
                  float(c.get("start", 0.0)) + 0.5 if c["kind"] == "video" else None)
    (job / storyboard.APPROVAL).unlink(missing_ok=True)  # a changed Short needs approving again
    (job / "footage.json").write_text(json.dumps(entries, ensure_ascii=False, indent=2), encoding="utf-8")
    return preflight.write(job, ep, tl, voices, entries, cfg, media, log=log)


def use_own_clip(job: Path, n: int, upload: Path, name: str, log=print) -> dict:
    """Beat `n` uses your clip or photo: saved as <media>/scene-NN.<ext> (replacing an earlier one), checked by the
    hook rules when it's the hook, and the pre-flight run again. The stock pick it replaces is kept, so removing your
    clip puts it back. Returns the new report."""
    from ..visuals import IMAGE_EXTS, VIDEO_EXTS
    from .footage import own_pick

    ext = Path(name).suffix.lower()
    if ext not in (*VIDEO_EXTS, *IMAGE_EXTS):
        raise ValueError(f"Use a video ({', '.join(sorted(VIDEO_EXTS))}) or a photo ({', '.join(sorted(IMAGE_EXTS))}).")
    job = Path(job)
    cfg, ep, tl, voices, entries, media = _load(job)
    if not 1 <= n <= len(entries):
        raise ValueError(f"There's no beat {n}.")
    media.mkdir(parents=True, exist_ok=True)
    for old in media.glob(f"scene-{n:02d}.*"):  # one file per beat: an earlier one is set aside, not deleted
        (media / "removed").mkdir(exist_ok=True)
        shutil.move(str(old), str(media / "removed" / f"{datetime.now():%Y%m%d-%H%M%S}-{old.name}"))
    dest = media / f"scene-{n:02d}{ext}"
    shutil.copy(upload, dest)
    e = entries[n - 1]
    if e["chosen"]["source"] != "own":
        e["stock"] = {"chosen": e["chosen"], "match": e.get("match"), "flags": e["flags"]}
    # held to the beat's planned shot like stock (a Short built before the planned shots were kept: its Visual)
    shot = (e.get("search") or {}).get("plan") or {"shot": ep.script.scenes[n - 1].visual, "key_objects": []}
    e["chosen"], e["flags"], e["match"] = own_pick(dest, tl.slots[n - 1].length, n == 1,
                                                   ep.animal or ep.animal_search or "animal", shot)
    e["reuses_opening"] = False
    log(f"      beat {n}: your clip {dest.name}")
    return _refresh(job, ep, tl, voices, entries, cfg, media, log)


def remove_own_clip(job: Path, n: int, log=print) -> dict:
    """Beat `n` goes back to the stock pick your clip replaced. Your file isn't deleted (it may be your only copy): it
    moves to <media>/removed/, where the picker doesn't look."""
    job = Path(job)
    cfg, ep, tl, voices, entries, media = _load(job)
    if not 1 <= n <= len(entries):
        raise ValueError(f"There's no beat {n}.")
    e = entries[n - 1]
    if e["chosen"]["source"] != "own":
        raise ValueError(f"Beat {n} isn't using your clip.")
    mine = Path(e["chosen"]["file"])
    if mine.exists():
        (media / "removed").mkdir(parents=True, exist_ok=True)
        shutil.move(str(mine), str(media / "removed" / f"{datetime.now():%Y%m%d-%H%M%S}-{mine.name}"))
    stock = e.pop("stock", None)
    if stock:
        e["chosen"], e["match"], e["flags"] = stock["chosen"], stock["match"], stock["flags"]
    else:  # it was yours from the start: nothing to go back to but a card, until the episode is built again
        from ..longform import footage as lf

        e["chosen"] = lf.make_card(e, ep.script.scenes[n - 1], job / "storyboard", cfg, ep.script.lang)
        e["match"], e["flags"] = 0, ["needs your own clip: build the episode again to search stock for it"]
    log(f"      beat {n}: back to {e['chosen']['source']}")
    return _refresh(job, ep, tl, voices, entries, cfg, media, log)


def report_status(job: Path) -> dict:
    """The pre-flight's {state, reasons} ({} before there is one)."""
    try:
        return json.loads((Path(job) / "preflight.json").read_text(encoding="utf-8")).get("status", {})
    except (OSError, ValueError):
        return {}


def is_short(job: Path) -> bool:
    try:
        return json.loads((Path(job) / "meta.json").read_text(encoding="utf-8")).get("kind") == "short"
    except (OSError, ValueError):
        return False


def render_job(job: Path, log=print) -> Path:
    """Steps 6-7 for an approved Short. Returns video.mp4."""
    from ..longform import storyboard
    from ..longform.parse import Script
    from ..longform.timing import Timeline
    from ..longform.voice import Voice
    from ..render import duration, loudness
    from . import extras, plan, render, settings

    job = Path(job)
    if not storyboard.approved(job):
        raise RuntimeError("The pre-flight isn't approved (or changed since it was): check preflight.html, then "
                           f"python make.py --approve \"{job}\".")
    cfg = settings.load()
    ep = plan.ShortPlan.load(job / "episode.json")
    script = Script.load(job / "scenes.json")
    tl = Timeline.from_json(json.loads((job / "timeline.json").read_text(encoding="utf-8")))
    entries = json.loads((job / "footage.json").read_text(encoding="utf-8"))
    voices = {v.scene: v.words for v in map(Voice.from_json,
                                            json.loads((job / "voice.json").read_text(encoding="utf-8")))}
    log(f"[6/{STEPS}] Render")
    made = render.render(job, script, tl, entries, voices, cfg, log=log)
    log(f"[7/{STEPS}] Cover and metadata")
    extras.write(job, ep, tl, entries, made, log=log)
    shutil.rmtree(job / "work", ignore_errors=True)
    video = job / "video.mp4"
    length, lufs = duration(video), loudness(video)
    hi = float(cfg["rules"]["length"]["max"])
    log(f"Done: {video} ({length:.1f}s, {lufs:.1f} LUFS, {made['encoder']})"
        + ("" if length <= hi else f"  ! over {hi:.0f}s"))
    return video
