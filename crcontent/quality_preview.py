"""Video Quality Inspector, preview stage: checks the project before it renders (a Shorts draft's script as the
editor holds it, or a Lyric Studio song folder). Quick checks read only the project; a full check also probes every
media file it uses. A preview report is no proof the rendered file is right: the Final Render Inspector (quality.py)
checks that.
"""
import hashlib
import json
import re
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter
from pydantic import BaseModel

from .config import ASSETS_DIR, LANGS, ROOT, frame_size
from .quality import _check, _finish, _num, _read_samples, analyze, has_filter, probe, rules_for
from .script import VideoScript

router = APIRouter()

SHORT_RULES = {
    "max_sec": 180,  # YouTube Shorts' limit; longer uploads become regular videos
    "long_scene_sec": 12,  # one shot held this long may feel static
    "headline_chars": 40,
    "safe_x": (0.05, 0.95),  # text centre / edges inside these fractions of the frame
    "safe_y": (0.08, 0.80),  # the platforms' top bar and bottom buttons/description cover the rest
    "min_media_px": 720,  # shorter side; smaller footage is upscaled and looks soft
}
SHORT_RULES["caption_changes_per_sec"] = 3.5  # faster than this, captions flicker past unread
# retention heuristics (editorial advice, not platform rules; quality_rules.json can change them)
SHORT_RULES |= {"hook_sec": 4.0,       # the first shot held this long before any cut or cutaway
                "repeat_overlap": 0.7,  # share of content words two sentences have in common to count as a repeat
                "still_run": 3}         # this many still pictures in a row reads as a slideshow
HEADLINE_H, CAPTION_HALF = 0.11, 0.05  # the headline card's height (2 lines), half a caption's: shares of the height
DEFAULT_CAPTION_Y, DEFAULT_HEADLINE_Y = 0.62, 0.13  # styles.CaptionStyle's
STOP = set("a an the and or but of to in on at is are was were be it its this that these those for with as by from "
           "than then so very can could will would has have had do does did not no they them their there here".split())
LYRIC_RULES = {"max_chars": 42, "min_line_sec": 0.7, "gap_sec": 12, "min_font_px": 48, "font_px": 66,
               "sync_sec": 0.8, "vocal_silence_db": -35}  # a line this far from the singing is off
TERMINAL = re.compile(r"[.!?。]['\"”’)]*$")
CHAR_W = 0.55  # average glyph width as a share of the font size (latin bold), for the text-width estimate

SHORT_NOT_YET = [("audio", "The finished mix (ducking, sound effects): run the Quality check after rendering"),
                 ("storytelling", "Whether the footage shows what the narration says: run the AI footage check below")]
LOOK_FRAMES = 3  # frames sampled from each media file, one a second from where the scene starts it
LYRIC_NOT_YET = [("lyrics", "Word-level sync accuracy (only line start times are known)"), ("lyrics", "Lyric spelling"),
                 ("visual", "Picture quality and how distracting the motion is"), ("rights", "Song and picture rights")]


def _fp(data) -> str:
    return hashlib.sha256(json.dumps(data, sort_keys=True, default=str).encode()).hexdigest()


def _scene(item: dict, i: int) -> dict:
    item["scene"] = i  # the UI opens this scene in the editor
    return item


def _library_file(rel: str) -> Path | None:
    """A media path from the script, only when it's inside the library folder."""
    try:
        f = (ROOT / rel).resolve()
    except (OSError, ValueError):
        return None
    return f if f.is_relative_to(ROOT.resolve()) else None


def _probe_media(f: Path) -> dict | None:
    try:
        info = probe(f)
    except (ValueError, OSError, subprocess.SubprocessError):
        return None
    v = next((s for s in info.get("streams", []) if s.get("codec_type") == "video"), {})
    return {"w": v.get("width", 0), "h": v.get("height", 0), "dur": _num(info.get("format", {}).get("duration")),
            "still": v.get("codec_name") in ("mjpeg", "png", "webp", "bmp", "gif") or not _num(info.get("format", {}).get("duration"))}


def _media_look(f: Path, start: float, still: bool) -> dict | None:
    """Median sharpness and brightness and the mean colour offset of a few frames of a media file (quality.py's
    measurements), or None when FFmpeg can't decode it."""
    blur = "blurdetect," if has_filter("blurdetect") else ""
    with tempfile.TemporaryDirectory(prefix="crq-") as tmp:
        cmd = ["ffmpeg", "-hide_banner", "-nostdin", *([] if still else ["-ss", f"{start:.2f}"]), "-i", str(f.resolve()),
               "-vf", f"{'' if still else 'fps=1,'}scale=480:-2,signalstats,{blur}metadata=mode=print:file=frames.txt",
               "-frames:v", str(1 if still else LOOK_FRAMES), "-f", "null", "-"]
        try:  # run in the temp folder: the frame log is named relative to it (a Windows "C:" breaks the filter graph)
            subprocess.run(cmd, cwd=tmp, stdin=subprocess.DEVNULL, capture_output=True, timeout=60, check=True)
        except (OSError, subprocess.SubprocessError):
            return None
        samples = _read_samples(Path(tmp) / "frames.txt")
    if not samples:
        return None
    mid = lambda xs: sorted(xs)[len(xs) // 2] if xs else None  # noqa: E731
    # blurdetect gives nan on a frame with no edges; flat frames (low contrast) have nothing to judge sharpness by
    blurs = [x["blur"] for x in samples if x.get("blur") is not None and x["blur"] == x["blur"]
             and x.get("yhigh", 0) - x.get("ylow", 0) > 30]
    us = [x["uavg"] - 128 for x in samples if x.get("uavg") is not None]
    vs = [x["vavg"] - 128 for x in samples if x.get("vavg") is not None]
    return {"blur": mid(blurs), "yavg": mid([x["yavg"] for x in samples if x.get("yavg") is not None]),
            "u": sum(us) / len(us) if us else 0.0, "v": sum(vs) / len(vs) if vs else 0.0}


def look_checks(checks: list, looks: list[tuple[int, str, dict]]) -> None:
    """Sharpness, exposure and colour cast of each scene's media (scene, label, _media_look()), with the final
    inspector's thresholds. Warnings to review, never fails: footage can be soft, dark or graded on purpose."""
    rules, flagged = rules_for("short"), False
    for i, label, m in looks:
        if m["blur"] is not None and m["blur"] > rules["blur"]:
            flagged = _scene(_check(checks, f"visual.sharpness.{i}.{label}", "visual", "warning",
                                    f"Scene {i + 1}: {label} looks soft or blurry",
                                    f"Blur score {m['blur']:.0f} (sharp footage is about 4; threshold {rules['blur']:.0f}).",
                                    "low", "Fine for a deliberate soft look; otherwise pick a sharper clip."), i)
        if m["yavg"] is not None and not rules["dark"] <= m["yavg"] <= rules["bright"]:
            dark = m["yavg"] < rules["dark"]
            flagged = _scene(_check(checks, f"visual.exposure.{i}.{label}", "visual", "warning",
                                    f"Scene {i + 1}: {label} is very {'dark' if dark else 'bright'}",
                                    "Details may be lost on phone screens." if dark else "Highlights may be blown out.",
                                    "low", "Fine for the intended look; otherwise pick another clip."), i)
        if max(abs(m["u"]), abs(m["v"])) > rules["cast"]:
            u, v = m["u"], m["v"]
            tint = ("blue" if u > 0 else "yellow") if abs(u) >= abs(v) else ("red/magenta" if v > 0 else "green")
            flagged = _scene(_check(checks, f"visual.colour.{i}.{label}", "visual", "warning",
                                    f"Scene {i + 1}: {label} has a {tint} colour cast",
                                    f"Average chroma offset U {u:+.0f}, V {v:+.0f}. A deliberate grade can look like this.",
                                    "low", "Ignore it if it's the intended look."), i)
    if looks and not flagged:
        _check(checks, "visual.footage", "visual", "pass", "Footage looks sharp and well exposed",
               f"{len(looks)} media files, up to {LOOK_FRAMES} frames each: no strong blur, exposure or colour problem.")


def rights_checks(checks: list, script: VideoScript, music: str) -> None:
    """What the app knows about each file's licence (rights.py) and the music's, before rendering. Your own record:
    YouTube's copyright checks only run after upload."""
    from . import rights
    from .music import track_use

    seen, unknown, own = set(), [], 0
    for n, sc in enumerate(script.scenes, 1):
        for rel in [sc.media, sc.media2 if sc.layout == "split" else "", *(b.media for b in sc.broll)]:
            if not rel or rel in seen or not (f := _library_file(rel)) or not f.is_file():
                continue
            seen.add(rel)
            a = rights._media_asset(rel, n)
            if a.source == "Your upload":
                own += 1
            elif not (a.source and a.license):
                unknown.append(n)
                _scene(_check(checks, f"rights.media.{rel}", "rights", "warning", f"Scene {n}: no licence on record for {Path(rel).name}",
                              "The app doesn't know where this file came from.", "medium",
                              "Use footage from the app's search or your uploads, or note its source in the rights checklist after rendering."), n - 1)
    if seen and not unknown:
        stock = len(seen) - own
        _check(checks, "rights.media", "rights", "pass", "Every media file's source is known",
               ", ".join(x for x in (f"{stock} with a licence on record" if stock else "",
                                     f"{own} your own upload{'s' if own != 1 else ''}" if own else "") if x) + ".")
    if script.art_style:
        _check(checks, "rights.art", "rights", "warning", "AI scene pictures", "Drawn on this computer with Stable Diffusion XL.",
               "low", "Check the model licence's terms for commercial use.")
    if music and music != "none":
        use = track_use(music)
        if use in ("nc", "nd"):
            _check(checks, "rights.music", "rights", "warning",
                   "Music licence is non-commercial" if use == "nc" else "Music licence forbids adaptations",
                   "Not for a monetized video." if use == "nc" else "Creative Commons counts putting music to video as an adaptation.",
                   "high", "Pick another track.")
        else:
            _check(checks, "rights.music", "rights", "pass" if use == "ok" else "not_checked",
                   "Music licence allows this use" if use == "ok" else "Music licence unknown",
                   "" if use == "ok" else "No licence saved with the track: check where it came from.")
    _check(checks, "rights.youtube", "rights", "not_checked", "Copyright (Content ID) and ad suitability",
           "Only YouTube Studio can check these: upload privately or unlisted and wait for its checks.")


MUSIC_LRA_MAX = 15.0  # LU; past this the track's loud parts rise over the voice even with the ducking


def music_level_checks(checks: list, track: Path | None, full: bool) -> None:
    """The music track's own loudness and loudness range. The render sets the voice and the music under it
    (render._mix_audio), but can raise the music only so far, and can't tame a track that swings from soft to loud."""
    from .render import MUSIC_BELOW, VOICE_LUFS

    if not full or track is None:
        _check(checks, "audio.music_level", "audio", "not_checked", "Music loudness",
               "Run a Full check: it measures the track." if track else "The track is picked at render.")
        return
    found = analyze(track, False, True, 0, {"silence_db": -50, "silence_sec": 2, "sample_fps": 1})
    lufs, lra = found["lufs"], found["lra"]
    if found["exit_code"] != 0 or lufs is None or lufs <= -69:
        _check(checks, "audio.music_level", "audio", "fail", "Music track can't be measured (unreadable or silent)",
               track.name, "high", "Pick another track.")
        return
    shown = f"{lufs:.1f} LUFS, loudness range {lra or 0:.1f} LU"
    bad = False
    if VOICE_LUFS - MUSIC_BELOW - lufs > 24:  # render._gain raises a track by 24 dB at most
        bad = True
        _check(checks, "audio.music_quiet", "audio", "warning", "Music will sit too low under the voice",
               f"The track is very quiet ({shown}); the render can't raise it far enough.", "medium", "Pick a louder track.")
    if lra and lra > MUSIC_LRA_MAX:
        bad = True
        _check(checks, "audio.music_range", "audio", "warning", "Music swings from soft to loud",
               f"{shown}: its loud parts may rise over the voice even with the ducking.", "medium",
               "Pick a steadier track or lower the music volume.")
    if not bad:
        _check(checks, "audio.music_level", "audio", "pass", "Music level fits under the voice", shown)


# ---------- Shorts ----------

def _fix(item: dict, label: str, **change) -> dict:
    """A safe, one-click change for the editor: `captions` (fields of the caption style) or `text` (the scene's k-th
    overlay) with `set` (its fields). The editor applies it as one undoable edit."""
    item["fix"] = {"label": label, **change}
    return item


def _collides(caption_y: float, headline_y: float) -> bool:
    return caption_y + CAPTION_HALF > headline_y and caption_y - CAPTION_HALF < headline_y + HEADLINE_H


def _content(text: str) -> set[str]:
    return {w for w in re.findall(r"[^\W_]+", text.lower()) if w not in STOP and (len(w) > 2 or w.isdigit())}


def retention_checks(checks: list, scenes: list, lengths: list[float], starts: list[float], cs, rules: dict) -> None:
    """Deterministic retention checks from the project data alone (no AI key needed): a long first shot, a fact said
    twice, a run of stills, a headline that only repeats the voice or sits on the captions. All advice: stillness or a
    repeat can be deliberate."""
    from .visuals import IMAGE_EXTS

    # the opening: how long the first picture holds before a cut or a cutaway changes it
    if lengths[0]:
        change = min([b.at for b in scenes[0].broll if b.at > 0] + [lengths[0]])
        if change > rules["hook_sec"]:
            _scene(_check(checks, "pacing.opening", "storytelling", "warning",
                          f"The first shot holds {change:.1f} s before anything changes",
                          "Viewers decide in the first seconds; one unchanging picture through the hook gives them "
                          "nothing new to look at.", "low",
                          "Cut to the behavior the hook talks about, or add a cutaway early in scene 1.", 0, change), 0)
        else:
            _check(checks, "pacing.opening", "storytelling", "pass", f"The picture changes within {change:.1f} s")
    else:
        _check(checks, "pacing.opening", "storytelling", "not_checked", "Opening pace",
               "Scene 1 has no voiceover yet, so its length isn't known.")

    # the same fact said twice: sentences sharing most of their content words
    sentences = [(i, s.strip()) for i, sc in enumerate(scenes) for s in re.split(r"(?<=[.!?。])\s+", sc.narration)
                 if len(_content(s)) >= 4]
    repeats = set()
    for a, (i, s) in enumerate(sentences):
        for j, t in sentences[a + 1:]:
            x, y = _content(s), _content(t)
            if j != i and len(x & y) / min(len(x), len(y)) >= rules["repeat_overlap"] and (i, j) not in repeats:
                repeats.add((i, j))
                _scene(_check(checks, f"story.repeat.{i}.{j}", "storytelling", "warning",
                              f"Scene {j + 1} repeats what scene {i + 1} already said",
                              f"“{t[:70]}” after “{s[:70]}”: a repeated beat is where viewers swipe away.", "low",
                              "Cut it, or use the line for a new detail that moves the story on.",
                              starts[j], starts[j] + lengths[j]), j)
    if not repeats and len(sentences) > 1:
        _check(checks, "story.repeat", "storytelling", "pass", "Every scene says something new")

    # a run of still pictures (a drawn card or a photo held on purpose is fine on its own)
    run = 0
    for i, sc in enumerate(scenes):
        run = run + 1 if sc.media and Path(sc.media).suffix.lower() in IMAGE_EXTS and not sc.broll else 0
        if run == rules["still_run"]:
            first = i - run + 1
            _scene(_check(checks, f"visual.stills.{first}", "visual", "warning",
                          f"Scenes {first + 1}–{i + 1} are all still pictures",
                          f"{run} stills in a row can read as a slideshow, even with motion added.", "low",
                          "Swap one for a video clip, or add a moving cutaway in the middle.",
                          starts[first], starts[i] + lengths[i]), first)

    caption_y = cs.y
    clash = _collides(caption_y, cs.headline_y)
    # the safe way out: captions back to their default, or (when that's where the headline was moved) the headline
    unclash = ({"label": f"Move the captions to {DEFAULT_CAPTION_Y:.0%}", "captions": {"y": DEFAULT_CAPTION_Y}}
               if not _collides(DEFAULT_CAPTION_Y, cs.headline_y) else
               {"label": f"Move the headlines to {DEFAULT_HEADLINE_Y:.0%}", "captions": {"headline_y": DEFAULT_HEADLINE_Y}})
    for i, sc in enumerate(scenes):
        head = sc.on_screen_text.strip()
        if head and clash:
            _scene(_fix(_check(checks, f"captions.collide.{i}", "captions", "warning",
                               f"Scene {i + 1}: the captions run into the headline",
                               f"Captions centred at {caption_y:.0%}, headline from {cs.headline_y:.0%} to "
                               f"{cs.headline_y + HEADLINE_H:.0%} of the height.", "medium",
                               "Move the captions or the headline in the Captions panel.", starts[i],
                               starts[i] + lengths[i]), **unclash), i)
        for k, t in enumerate(sc.texts):
            if t.text.strip() and abs(t.y - caption_y) < 0.06:
                y = 0.4 if abs(0.4 - caption_y) >= 0.12 else 0.75  # TextOverlay's default spot, else under the captions
                _scene(_fix(_check(checks, f"captions.collide.{i}.{k}", "captions", "warning",
                                   f"Scene {i + 1}: text “{t.text[:24]}” sits on the captions",
                                   f"Both at about {caption_y:.0%} of the height.", "medium", "Move the text up or down."),
                            f"Move the text to {y:.0%}", text=k, set={"y": y}), i)
        words = _content(head)
        if len(words) >= 3 and words <= _content(sc.narration):
            _scene(_check(checks, f"captions.echo.{i}", "captions", "warning",
                          f"Scene {i + 1}: the headline only repeats the narration",
                          f"“{head[:40]}” is said word for word.", "info",
                          "A headline earns its place with what the voice doesn't say: a number, a twist, a question."), i)


def plan_story_checks(checks: list, plan, scenes: list, starts: list[float], lengths: list[float]) -> None:
    """The Director Plan's Setup / Tension / Payoff findings (director_plan.story_findings), tied to the editor's
    scenes by their narration. Rules over the beats the AI Director labelled, so they're marked "inferred"."""
    from .director_plan import story_findings

    label = "Story beats (Setup / Tension / Payoff, open questions)"
    if plan is None:
        _check(checks, "plan.story", "storytelling", "not_checked", label, "This draft has no Director Plan.")
        return
    if plan.planned_by != "ai" or not any(s.phase for s in plan.scenes):  # unplanned, or planned before story beats
        _check(checks, "plan.story", "storytelling", "not_checked", label,
               "Plan the whole video with the AI Director to get story beats to check.")
        return
    where = {sc.narration.strip(): i for i, sc in reversed(list(enumerate(scenes)))}
    index = {s.id: where.get(s.narration.strip()) for s in plan.scenes}
    found = [f for f in story_findings(plan) if f["key"] != "repeat"]  # retention_checks already finds repeats
    for n, f in enumerate(found):
        i = index.get(f["scene"])
        span = (starts[i], starts[i] + lengths[i]) if i is not None and lengths[i] else ()
        item = _check(checks, f"plan.story.{f['key']}.{n}", "storytelling", "warning", f["title"],
                      "Found in the Director Plan's story beats (phases, questions and answers the AI Director "
                      "labelled); the narration itself isn't judged here.", "low", f["fix"], *span)
        if i is not None:
            _scene(item, i)
    if not found:
        _check(checks, "plan.story", "storytelling", "pass", "Every question the video raises is answered, and it reaches its payoff",
               f"{len(plan.scenes)} beats checked in the Director Plan.")


def timeline_checks(checks: list, script: VideoScript, total: float) -> None:
    """The timeline's graphics and sound clips (M4): the ones the render would leave out, said before it renders."""
    from . import timeline
    from .shorts import motion

    for n, w in enumerate(timeline.check(script.clips)):
        _check(checks, f"timeline.clip.{n}", "technical", "warning", w, "It won't be in the render.", "medium",
               "Pick one in the inspector, or delete the clip.")
    late = [c.id for c in script.clips if total and c.start >= total]
    if late:
        _check(checks, "timeline.late", "technical", "warning", f"{len(late)} clip(s) start after the video ends",
               ", ".join(late), "medium", "Move them earlier on the timeline; they won't play.")
    drawn = [c for c in script.clips if c.track == "graphics"] and not script.track("graphics").hidden
    if drawn and not ((motion.PROJECT / "node_modules").is_dir() and motion.node()):
        _check(checks, "timeline.remotion", "technical", "warning", "Graphics can't be drawn on this computer",
               f"Remotion (Node and its packages in {motion.PROJECT}) isn't available, so the timeline's graphics "
               "would be left out of the render.", "high", "Run `npm install` at the project root, or remove the graphics.")


def label_methods(checks: list) -> None:
    """How each finding was reached, for the UI: measured from the project or media, a heuristic rule of thumb,
    inferred from the AI Director's labels, AI-assisted, or not checked."""
    rules = ("story.", "pacing.", "visual.stills", "captions.echo", "captions.speed", "audio.music_level")
    for c in checks:
        d = c["detector"]
        c["method"] = ("not_checked" if c["status"] == "not_checked" else "ai" if d.startswith("ai.")
                       else "inferred" if d.startswith("plan.") else "heuristic" if d.startswith(rules) else "measured")


def history_hook_checks(checks: list, plan, research=None) -> None:
    """A history project's hook, judged by history rules (history/hook.py), never by the wildlife hook judge."""
    from .ai_director import is_history
    from .history import hook

    if not is_history(plan):
        return
    for f in hook.judge(plan, research):
        _check(checks, f"history.hook.{f['key']}", "storytelling", f["status"], f["title"], "",
               "medium" if f["status"] == "fail" else "low", f["fix"])
    history_footage_checks(checks, plan)


def history_footage_checks(checks: list, plan) -> None:
    """Where each shot's picture came from (spec 7.3, H4): rights not stated, and stand-ins for real evidence."""
    shots = [s for s in plan.shots if s.footage and s.footage.source not in ("own", "card")]
    unknown = [s for s in shots if s.footage.rights == "rights_unknown"]
    for s in unknown:
        _check(checks, f"history.rights.{s.id}", "rights", "warning", f"{s.id}: the source states no licence",
               s.footage.page, "medium", "Check the item page and confirm the rights, or replace the picture.")
    if shots and not unknown:
        _check(checks, "history.rights", "rights", "pass", "Every sourced picture states a licence")
    stand_ins = [s for s in shots if s.visual_origin in ("archive", "evidence") and s.footage.depicts == "illustrative"]
    for s in stand_ins:
        what = "stock footage" if s.footage.asset_type == "stock" else "a similar picture"
        _check(checks, f"history.visual.{s.id}", "visual", "warning",
               f"{s.id}: {what} stands in for {s.subject or 'the evidence'}", s.footage.page, "medium",
               "Don't present it as the real thing: find authentic material, or say it's illustrative.")
    if shots and not stand_ins:
        _check(checks, "history.visual", "visual", "pass", "No evidence shot uses a stand-in picture")


def inspect_short(script: VideoScript, lang: str, music: str, lengths: list[float], full: bool, plan=None,
                  research=None) -> dict:
    """lengths: each scene's length in seconds as the editor's timeline has it (0 = not voiced yet).
    plan: the draft's Director Plan (None: the story-beat checks say not checked)."""
    rules, checks = rules_for("short_preview"), []
    W, H = frame_size("9:16")
    from .profiles import stamp

    result = {"stage": "preview", "profile": "short", "profile_label": "Shorts", "mode": "full" if full else "quick",
              "channel_profile": stamp({}, plan).get("channel_profile_name", ""),
              "created": datetime.now().isoformat(timespec="seconds"), "checks": checks, "cancelled": False,
              "sampled": "project data" + (" and a probe and a few frames of every media file" if full else " only (no media decoded)")}
    profile = LANGS.get(lang, LANGS["en"])
    scenes = script.scenes
    lengths = [*lengths, *[0.0] * len(scenes)][: len(scenes)]

    _check(checks, "project.size", "technical", "pass", f"Renders at {W}×{H} (9:16)")
    if not scenes:
        _check(checks, "structure.scenes", "storytelling", "fail", "No scenes", "", "critical", "Add a scene.")
        return _finish(result, SHORT_NOT_YET)

    # --- timing ---
    starts = [sum(lengths[:i]) for i in range(len(scenes))]
    unvoiced = [i for i, sc in enumerate(scenes) if sc.narration.strip() and not lengths[i]]
    for i, sc in enumerate(scenes):
        if not sc.narration.strip() and sc.seconds <= 0:
            _scene(_check(checks, f"timing.empty.{i}", "technical", "warning", f"Scene {i + 1} has no voiceover and no length",
                          "It adds nothing to the video.", "medium", "Write its voiceover, give it a length, or remove it."), i)
        elif lengths[i] > rules["long_scene_sec"]:
            _scene(_check(checks, f"pacing.long.{i}", "storytelling", "warning", f"Scene {i + 1} runs {lengths[i]:.0f} s on one shot",
                          "Possible pacing issue: a long hold can feel static.", "low",
                          "Consider a cutaway (B-roll) or splitting the scene.", starts[i], starts[i] + lengths[i]), i)
    if unvoiced:
        _check(checks, "timing.total", "technical", "not_checked", "Total length unknown",
               f"Scenes {', '.join(str(i + 1) for i in unvoiced)} have no voiceover generated yet.")
    else:
        total = sum(lengths)
        status = "fail" if total > rules["max_sec"] else "pass"
        _check(checks, "timing.total", "technical", status, f"Length about {int(total // 60)}:{total % 60:04.1f}",
               f"Over {rules['max_sec'] // 60} min it won't be a Short." if status == "fail" else "From the voiceover timeline.",
               "high" if status == "fail" else "info", "Shorten the script." if status == "fail" else "")

    # --- media references ---
    seen: dict[str, int] = {}
    probes: dict[Path, dict | None] = {}
    looks: list[tuple[int, str, dict]] = []
    looked: set[Path] = set()
    for i, sc in enumerate(scenes):
        refs = [("media", sc.media), ("second clip", sc.media2 if sc.layout == "split" else "")]
        refs += [(f"cutaway {k + 1}", b.media) for k, b in enumerate(sc.broll)]
        for label, rel in refs:
            if not rel:
                continue
            f = _library_file(rel)
            if not f or not f.is_file():
                _scene(_check(checks, f"media.missing.{i}.{label}", "technical", "fail", f"Scene {i + 1}: {label} file is missing",
                              rel, "critical", "Pick the footage again."), i)
                continue
            if label == "media":
                if rel in seen:
                    _scene(_check(checks, f"media.repeat.{i}", "visual", "warning",
                                  f"Scene {i + 1} reuses scene {seen[rel] + 1}'s footage", "Repeated shots can feel lazy.",
                                  "low", "Pick a different clip unless the repeat is deliberate."), i)
                seen.setdefault(rel, i)
            if not full:
                continue
            if f not in probes:
                probes[f] = _probe_media(f)
            p = probes[f]
            if p is None:
                _scene(_check(checks, f"media.unreadable.{i}.{label}", "technical", "fail", f"Scene {i + 1}: {label} can't be read",
                              rel, "critical", "Replace the file."), i)
                continue
            if p["w"] and min(p["w"], p["h"]) < rules["min_media_px"]:
                _scene(_check(checks, f"media.lowres.{i}.{label}", "visual", "warning",
                              f"Scene {i + 1}: {label} is only {p['w']}×{p['h']}", "It will be upscaled and may look soft.",
                              "low", "Use a sharper clip if one exists."), i)
            if label == "media" and not p["still"] and p["dur"] and sc.media_start >= p["dur"]:
                _scene(_check(checks, f"media.start.{i}", "technical", "fail",
                              f"Scene {i + 1}: footage starts at {sc.media_start:.1f} s, past the clip's end ({p['dur']:.1f} s)",
                              "", "high", "Move the start point back in the timeline."), i)
            elif f not in looked:  # each file once: from where this scene starts it
                looked.add(f)
                start = max(sc.media_start, 0.0) if label == "media" else 0.0
                if m := _media_look(f, start, p["still"]):
                    looks.append((i, label, m))
    auto = [i + 1 for i, sc in enumerate(scenes) if not sc.media and not script.art_style]
    _check(checks, "media.refs", "technical", "pass" if not any(c["detector"].startswith("media.missing") for c in checks) else "fail",
           "Media references", f"Footage picked automatically at render for scenes {', '.join(map(str, auto))}." if auto
           else "Every scene has its media chosen.", "info")

    if full:
        look_checks(checks, looks)
    else:
        _check(checks, "visual.footage", "visual", "not_checked", "Footage quality (blur, exposure, colour)",
               "Run a Full check: it samples frames from every media file.")

    # --- overlays: timing and safe area (estimated from the font size) ---
    sx, sy = rules["safe_x"], rules["safe_y"]
    for i, sc in enumerate(scenes):
        for k, t in enumerate(sc.texts):
            if not t.text.strip():
                continue
            fs = profile.font_size * {"s": 0.6, "m": 0.85, "l": 1.2}.get(t.size, 0.85)  # captions.OVERLAY_SIZES
            half = len(t.text) * fs * CHAR_W / 2 / W
            centre = {"x": 0.5, "y": round(min(max(t.y, sy[0] + 0.02), sy[1] - 0.02), 2)}
            if t.x - half < 0 or t.x + half > 1:
                item = _check(checks, f"captions.clip.{i}.{k}", "captions", "warning", f"Scene {i + 1}: text “{t.text[:24]}” may run off the frame",
                              "Estimated from its length and size.", "medium", "Shorten it, make it smaller or move it to the middle.")
                # centred is the most room it can get; only offered when that's enough
                _scene(_fix(item, "Centre the text", text=k, set=centre) if half <= 0.5 - sx[0] else item, i)
            elif t.x - half < sx[0] or t.x + half > sx[1] or not sy[0] <= t.y <= sy[1]:
                _scene(_fix(_check(checks, f"captions.safe.{i}.{k}", "captions", "warning", f"Scene {i + 1}: text “{t.text[:24]}” is outside the safe area",
                                   "The platform's buttons, title or top bar may cover it.", "low", "Move it toward the middle."),
                            "Move it into the safe area", text=k, set=centre), i)
            if lengths[i] and t.at >= lengths[i]:
                _scene(_fix(_check(checks, f"captions.late.{i}.{k}", "captions", "warning", f"Scene {i + 1}: text “{t.text[:24]}” starts after the scene ends",
                                   f"At {t.at:.1f} s, scene is {lengths[i]:.1f} s.", "medium", "Move it earlier; it won't show."),
                            "Show it from the scene's start", text=k, set={"at": 0}), i)
        for k, b in enumerate(sc.broll):
            if lengths[i] and b.at >= lengths[i]:
                _scene(_check(checks, f"media.broll_late.{i}.{k}", "technical", "warning", f"Scene {i + 1}: cutaway {k + 1} starts after the scene ends",
                              "", "medium", "Move it earlier; it won't show."), i)
        if len(sc.on_screen_text) > rules["headline_chars"]:
            _scene(_check(checks, f"captions.headline.{i}", "captions", "warning", f"Scene {i + 1}: headline is {len(sc.on_screen_text)} characters",
                          "Long headlines wrap to several lines and are hard to read in a second.", "low", "Cut it to a few words."), i)
    cs = script.captions
    if not sy[0] <= cs.y <= sy[1]:
        _fix(_check(checks, "captions.position", "captions", "warning", f"Captions sit at {cs.y:.0%} of the height",
                    "Outside the safe area: the platform's buttons or description may cover them.", "medium",
                    "Drag them up in the Captions panel."),
             f"Move the captions to {DEFAULT_CAPTION_Y:.0%}", captions={"y": DEFAULT_CAPTION_Y})
    else:
        _check(checks, "captions.position", "captions", "pass", "Captions inside the safe area")
    per = cs.words or profile.words_per_caption
    fast = []
    for i, sc in enumerate(scenes):
        words = len(sc.narration.split())
        if lengths[i] > 0.5 and words:
            rate = words / per / lengths[i]
            if rate > rules["caption_changes_per_sec"]:
                fast.append(i)
                _scene(_check(checks, f"captions.speed.{i}", "captions", "warning",
                              f"Scene {i + 1}: captions change {rate:.1f} times a second",
                              f"{words} words in {lengths[i]:.1f} s, {per} per caption: hard to read.", "low",
                              "Show more words per caption, slow the voice, or cut words.", starts[i], starts[i] + lengths[i]), i)
    if any(lengths) and not fast:
        _check(checks, "captions.speed", "captions", "pass", "Captions change at a readable pace",
               f"Under {rules['caption_changes_per_sec']} changes a second in every voiced scene.")

    # --- audio ---
    voiced = sum(bool(sc.narration.strip()) for sc in scenes)
    _check(checks, "audio.voice", "audio", "pass" if voiced else "warning",
           f"Voiceover in {voiced} of {len(scenes)} scenes" if voiced else "No voiceover at all", "",
           "low" if voiced else "medium")
    if music == "none":
        _check(checks, "audio.music", "audio", "pass", "No background music (your choice)")
    elif music and not (ASSETS_DIR / "music" / Path(music).name).is_file():
        _check(checks, "audio.music", "audio", "fail", f"Music track missing: {music}", "", "high", "Pick another track.")
    else:
        _check(checks, "audio.music", "audio", "pass", f"Music: {music or 'picked at render'}")
        music_level_checks(checks, ASSETS_DIR / "music" / Path(music).name if music else None, full)

    retention_checks(checks, scenes, lengths, starts, cs, rules)
    timeline_checks(checks, script, sum(lengths) if not unvoiced else 0)
    plan_story_checks(checks, plan, scenes, starts, lengths)

    # --- storytelling (advice, never a verdict) ---
    first = scenes[0].narration.strip()
    from .packaging import fluff_opening

    if fluff := fluff_opening(script.narration):
        _scene(_check(checks, "story.hook", "storytelling", "warning", f"The opening warms up instead of hooking ({', '.join(fluff)})",
                      f"“{first[:60]}”", "low", "Consider opening with the claim or the most surprising detail.", 0, lengths[0] or 0), 0)
    elif first:
        _check(checks, "story.hook", "storytelling", "pass", "Opens without a warm-up phrase")
    if plan is not None:
        history_hook_checks(checks, plan, research)
    last = scenes[-1].narration.strip()
    if last and TERMINAL.search(last):
        _check(checks, "story.loop", "storytelling", "pass", "Ends on a complete sentence",
               "If you want a seamless loop, end mid-sentence so it runs into the opening.")
    elif last:
        _scene(_check(checks, "story.loop", "storytelling", "warning", "Ends mid-sentence",
                      f"“…{last[-60:]}”", "low", "Fine if it runs into the opening as a loop on purpose; "
                      "otherwise finish the thought.", starts[-1], starts[-1] + lengths[-1]), len(scenes) - 1)

    # --- publishing ---
    for field, label, sev in (("title", "Title", "medium"), ("caption", "Description", "low")):
        if not getattr(script, field).strip():
            _check(checks, f"publish.{field}", "rights", "warning", f"{label} is empty", "", sev, f"Write a {label.lower()} in the Post tab.")
    if not script.hashtags:
        _check(checks, "publish.hashtags", "rights", "warning", "No hashtags", "", "info")
    rights_checks(checks, script, music)
    result["fingerprint"] = _fp([script.model_dump(), lang, music, lengths, full, plan.model_dump() if plan else None])
    _finish(result, SHORT_NOT_YET)
    label_methods(checks)
    return result


# ---------- Lyric Studio ----------

def _song_inputs(folder: Path) -> list:
    """What a lyric preview depends on: change any and the report is outdated."""
    files = [folder / "song.json", folder / "lyrics.lrc", folder / "pictures.json"]  # neonmekong.pictures.NAME
    pics = folder / "pictures"  # neonmekong.pictures.DIR
    files += sorted(pics.iterdir()) if pics.is_dir() else []
    files += [f for f in folder.iterdir() if f.suffix.lower() in (".mp3", ".wav")]
    return [(f.name, f.stat().st_size, f.stat().st_mtime) for f in files if f.is_file()]


def inspect_song(folder: Path, full: bool) -> dict:
    try:
        from neonmekong import analyze, pictures, songjson
    except ImportError as e:  # the installed app doesn't bundle the lyric pipeline
        result = {"stage": "preview", "profile": "lyric", "profile_label": "Lyric video", "mode": "full" if full else "quick",
                  "file": folder.name, "created": datetime.now().isoformat(timespec="seconds"), "checks": [],
                  "cancelled": False, "fingerprint": "", "sampled": "nothing"}
        _check(result["checks"], "lyrics.pipeline", "lyrics", "not_checked", "Lyric checks unavailable",
               f"The lyric video pipeline isn't installed here ({e.name}).")
        return _finish(result, LYRIC_NOT_YET)

    rules, checks = rules_for("lyric_preview"), []
    result = {"stage": "preview", "profile": "lyric", "profile_label": "Lyric video", "mode": "full" if full else "quick",
              "file": folder.name, "created": datetime.now().isoformat(timespec="seconds"), "checks": checks,
              "cancelled": False, "fingerprint": _fp(_song_inputs(folder)),
              "sampled": "song files" + (" and the lyric layout measured with the video's font" if full else " only")}
    _check(checks, "project.size", "technical", "pass", "Lyric video renders at 1920×1080; chorus Short at 1080×1920")

    audio = analyze.find_audio(folder)[0]
    song_len = None
    if not audio:
        _check(checks, "audio.song", "audio", "fail", "No song file", "", "critical", "Upload the mp3 or wav.")
    else:
        try:
            from .render import duration

            song_len = duration(audio)
            _check(checks, "audio.song", "audio", "pass", f"Song {audio.name}: {int(song_len // 60)}:{song_len % 60:04.1f}")
        except Exception:
            _check(checks, "audio.song", "audio", "fail", f"{audio.name} can't be read", "", "critical", "Upload it again.")

    try:
        data = json.loads((folder / "song.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        data = {}
    lrc = folder / "lyrics.lrc"
    if not data or not lrc.exists():
        _check(checks, "lyrics.analyzed", "lyrics", "fail", "Song not analysed yet", "No lyric timing to check.", "critical",
               "Run Analyze in Lyric Studio.")
        return _finish(result, LYRIC_NOT_YET)
    lines = [ln for ln in analyze.parse_lrc(lrc.read_text(encoding="utf-8")) if ln["text"]]
    if not lines:
        _check(checks, "lyrics.present", "lyrics", "fail", "No timed lyric lines", "", "high", "Paste the lyrics and analyse again.")
        return _finish(result, LYRIC_NOT_YET)
    _check(checks, "lyrics.present", "lyrics", "pass", f"{len(lines)} timed lyric lines")

    # --- timing ---
    order = [ln["start"] for ln in lines]
    if order != sorted(order):
        bad = next(i for i in range(1, len(order)) if order[i] < order[i - 1])
        _check(checks, "lyrics.order", "lyrics", "fail", f"Line {bad + 1} is timed before the line above it",
               f"“{lines[bad]['text'][:40]}”", "high", "Fix its time in the lyric timing editor.", order[bad])
    else:
        _check(checks, "lyrics.order", "lyrics", "pass", "Lines are in time order")
    if song_len:
        late = [ln for ln in lines if ln["start"] >= song_len]
        for ln in late:
            _check(checks, "lyrics.beyond", "lyrics", "fail", f"“{ln['text'][:30]}” starts after the song ends",
                   f"At {ln['start']:.1f} s; the song is {song_len:.1f} s.", "high", "Fix or remove the line.", ln["start"])
        if not late:
            _check(checks, "lyrics.beyond", "lyrics", "pass", "Every line starts within the song")
    flashes = [ln for ln in lines if ln["end"] - ln["start"] < rules["min_line_sec"]]
    for ln in flashes[:10]:
        _check(checks, "lyrics.flash", "lyrics", "warning", f"“{ln['text'][:30]}” shows for only {ln['end'] - ln['start']:.1f} s",
               "Too quick to read.", "low", "Check its timing; merge it with the next line if they're sung together.", ln["start"], ln["end"])
    for a, b in zip(lines, lines[1:]):
        if a["text"].lower() == b["text"].lower() and b["start"] - a["start"] < 1.0:
            _check(checks, "lyrics.duplicate", "lyrics", "warning", f"“{a['text'][:30]}” appears twice in a row",
                   "Possibly a duplicated line.", "medium", "Remove one if it's not sung twice.", a["start"], b["end"])
        elif b["start"] - a["start"] > rules["gap_sec"]:
            _check(checks, "lyrics.gap", "lyrics", "warning", f"No lyrics for {b['start'] - a['start']:.0f} s after “{a['text'][:24]}”",
                   "Fine for an instrumental break; otherwise lines are missing.", "info", "", a["end"], b["start"])
    long_lines = [ln for ln in lines if len(ln["text"]) > rules["max_chars"]]
    for ln in long_lines[:10]:
        _check(checks, "lyrics.long", "lyrics", "warning", f"Long line ({len(ln['text'])} characters)",
               f"“{ln['text'][:60]}”", "low", "Split it so it reads at a glance.", ln["start"], ln["end"])
    if not flashes and not long_lines:
        _check(checks, "lyrics.readable", "lyrics", "pass", "Lines are a readable length and stay on screen long enough")
    chorus = data.get("chorus") or {}
    if song_len and chorus.get("end") and chorus["end"] > song_len:
        _check(checks, "lyrics.chorus", "lyrics", "warning", "Chorus ends after the song", "", "medium", "Re-run Analyze.")

    # --- layout with the real font (full) ---
    if full:
        try:
            from neonmekong import lyricvideo as lv
            from neonmekong import thumbnail

            maxw = int(lv.FULL[0] * 0.82)  # lyricvideo.Scene's wrap_frac
            shrunk = []
            for ln in lines:
                _, px = lv.wrap(ln["text"], rules["font_px"], maxw, 2, thumbnail.lyric_font)
                if px < rules["min_font_px"]:
                    shrunk.append((ln, px))
            for ln, px in shrunk[:10]:
                _check(checks, "lyrics.font", "lyrics", "warning", f"“{ln['text'][:30]}” shrinks to {px} px to fit",
                       "Smaller than the other lines and harder to read.", "low", "Split the line.", ln["start"], ln["end"])
            if not shrunk:
                _check(checks, "lyrics.font", "lyrics", "pass", "Every line fits on two lines at full size")
        except Exception as e:  # the music-video extras (PIL/cv2) aren't installed
            _check(checks, "lyrics.font", "lyrics", "not_checked", "Lyric layout", f"Couldn't measure: {e}")

    # --- sync against the sung vocal (full) ---
    if full:
        sync_checks(checks, folder, lines, song_len, rules)

    # --- pictures ---
    plan = pictures.load(folder)
    slots = plan.get("slots", [])
    missing = [s for s in slots if s.get("file") and not (folder / pictures.DIR / s["file"]).is_file()]
    for s in missing:
        _check(checks, "media.picture", "visual", "fail", f"Picture for {s.get('tag') or s['id']} is missing", s["file"],
               "high", "Draw or upload it again.", float(s.get("start", 0)))
    empty = [s for s in slots if not s.get("file")]
    if slots and not missing:
        _check(checks, "media.picture", "visual", "pass" if not empty else "warning",
               f"{len(slots) - len(empty)} of {len(slots)} section pictures ready",
               "Sections without a picture show the cover." if empty else "", "info")

    # --- publishing ---
    for w in songjson.warnings(data):
        _check(checks, f"publish.{_fp(w)[:6]}", "rights", "warning", w.split(":")[0], w, "medium")
    return _finish(result, LYRIC_NOT_YET)


def vocal_silences(vocals: Path, db: float) -> list[tuple[float, float]]:
    out = subprocess.run(["ffmpeg", "-hide_banner", "-nostdin", "-i", str(vocals), "-af", f"silencedetect=n={db}dB:d=0.5",
                          "-f", "null", "-"], stdin=subprocess.DEVNULL, capture_output=True, text=True, errors="replace")
    spans, start = [], None
    for line in out.stderr.splitlines():
        if m := re.search(r"silence_start: (-?[\d.]+)", line):
            start = max(0.0, float(m[1]))
        elif (m := re.search(r"silence_end: ([\d.]+)", line)) and start is not None:
            spans.append((start, float(m[1])))
            start = None
    if start is not None:
        spans.append((start, float("inf")))
    return spans


def sync_checks(checks: list, folder: Path, lines: list[dict], song_len: float | None, rules: dict) -> None:
    """Line start times against where the vocal stem (vocals.wav, from the vocal separation) actually has singing:
    a line shown while the singer is silent is early; singing that starts with no line near it means a late line."""
    vocals = folder / "vocals.wav"
    if not vocals.is_file():
        _check(checks, "lyrics.sync", "lyrics", "not_checked", "Lyric sync against the singing",
               "No vocal stem (vocals.wav): the AI add-on separates it when the song is analysed.")
        return
    gaps = vocal_silences(vocals, rules["vocal_silence_db"])
    tol = rules["sync_sec"]
    off = 0
    for ln in lines:
        gap = next(((a, b) for a, b in gaps if a <= ln["start"] < b), None)
        if gap and gap[1] - ln["start"] > tol and gap[1] - gap[0] < 30:  # not a whole instrumental break
            off += 1
            if off <= 10:
                _check(checks, "lyrics.sync", "lyrics", "warning", f"“{ln['text'][:30]}” shows {gap[1] - ln['start']:.1f} s before the singing",
                       "The vocal stem is silent when this line appears.", "medium",
                       "Move the line later in the lyric timing editor.", ln["start"], gap[1])
    starts = [ln["start"] for ln in lines]
    for a, b in gaps:  # b = singing starts again
        if b == float("inf") or (song_len and b >= song_len - 0.5):
            continue
        if not any(b - tol <= t <= b + tol for t in starts):
            later = [t for t in starts if t > b]
            if later and later[0] - b > tol and later[0] - b < 15:
                off += 1
                if off <= 10:
                    _check(checks, "lyrics.sync", "lyrics", "warning", f"Singing starts at {b:.1f} s, its line {later[0] - b:.1f} s later",
                           "Possibly a late line (or a sung part without lyrics).", "medium",
                           "Check the timing of the next line.", b, later[0])
    if not off:
        _check(checks, "lyrics.sync", "lyrics", "pass", "Line starts match the singing",
               f"Measured against the vocal stem, within {tol} s. Line level only, not word by word.")


# ---------- API ----------

class ShortPreviewRequest(BaseModel):
    script: VideoScript
    lang: str = "en"
    music: str = ""
    lengths: list[float] = []
    full: bool = False
    draft: str = ""  # its Director Plan feeds the story-beat checks


STORY_ASPECTS = ("hook", "promise", "early_payoff", "purpose", "narration_footage", "structure", "ending")
STORY_SCHEMA = {
    "type": "object",
    "properties": {"items": {"type": "array", "items": {
        "type": "object",
        "properties": {"aspect": {"type": "string", "enum": list(STORY_ASPECTS)},
                       "ok": {"type": "boolean"}, "title": {"type": "string"}, "note": {"type": "string"},
                       "scene": {"type": "integer"}},
        "required": ["aspect", "ok", "title", "note", "scene"], "additionalProperties": False}}},
    "required": ["items"], "additionalProperties": False,
}
STORY_SYSTEM = """You are an editorial assistant reviewing the script of a short vertical video (YouTube Shorts,
Reels, TikTok) before it is rendered. Give exactly one item per aspect:
- hook: is there an immediate reason to keep watching in the first line?
- promise: does the opening set up a clear question, event or claim?
- early_payoff: is something of the promise delivered early, not only at the end?
- purpose: is there a scene with no clear narrative purpose? (scene = its 1-based number, else 0)
- narration_footage: does each scene's footage search (visual_query) / headline fit what the narration says? (name the worst scene)
- structure: is there a hook, development and payoff?
- ending: does it end complete, abruptly, or loop back to the opening on purpose?
ok = true when it works. title: one short line. note: one or two sentences, specific to this script, phrased as advice
("consider...", "possible pacing issue..."). Never predict views, retention or virality, and never promise an edit will
improve them. Write in English; quote the script in its own language."""


class StoryRequest(BaseModel):
    script: VideoScript
    lang: str = "en"


@router.post("/api/inspect/preview/short/story")
def story_review(req: StoryRequest):
    """Optional AI review of the script text (no media is sent). Advisory only: every item is pass or warning."""
    from fastapi import HTTPException

    from .config import LLM_MODEL
    from .script import make_client

    sc = req.script
    if not sc.scenes:
        raise HTTPException(400, "The script has no scenes.")
    text = {"title": sc.title, "language": LANGS.get(req.lang, LANGS["en"]).name,
            "scenes": [{"n": i + 1, "narration": x.narration, "visual_query": x.visual_query,
                        "headline": x.on_screen_text} for i, x in enumerate(sc.scenes)]}
    try:
        response = make_client().beta.messages.create(
            model=LLM_MODEL, max_tokens=2500, system=STORY_SYSTEM,
            output_config={"effort": "low", "format": {"type": "json_schema", "schema": STORY_SCHEMA}},
            messages=[{"role": "user", "content": json.dumps(text, ensure_ascii=False)}])
        items = json.loads(next(b.text for b in response.content if b.type == "text"))["items"]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(502, f"The AI review didn't work: {e}. The other checks don't need it.")
    checks = []
    result = {"stage": "preview", "profile": "short", "profile_label": "AI story review (Gemini)", "mode": "full",
              "created": datetime.now().isoformat(timespec="seconds"), "checks": checks, "cancelled": False,
              "sampled": "the script text only (title, narration, footage searches, headlines), reviewed by Gemini; "
                         "advice for a human to weigh, not a prediction of views"}
    seen = set()
    for it in items:
        if it["aspect"] in seen or it["aspect"] not in STORY_ASPECTS:
            continue
        seen.add(it["aspect"])
        n = it["scene"] - 1 if 0 < it["scene"] <= len(sc.scenes) else None
        item = _check(checks, f"ai.story.{it['aspect']}", "storytelling", "pass" if it["ok"] else "warning",
                      it["title"][:120], f"{it['note'][:500]}\n(AI-assisted: review it yourself.)", "info" if it["ok"] else "low")
        if n is not None:
            _scene(item, n)
    for a in STORY_ASPECTS:
        if a not in seen:
            _check(checks, f"ai.story.{a}", "storytelling", "not_checked", a.replace("_", " ").capitalize(), "The AI gave no answer.")
    _finish(result, [])
    label_methods(checks)
    return result


FOOTAGE_PASS = 7  # shorts.match.PASS: footage that shows what's said
FOOTAGE_SCHEMA = {
    "type": "object",
    "properties": {"score": {"type": "integer"}, "seen": {"type": "string"}, "problem": {"type": "string"}},
    "required": ["score", "seen", "problem"], "additionalProperties": False,
}


def footage_verdict(f: Path, narration: str, start: float, length: float, client=None) -> dict | None:
    """Gemini's {score 0-10, seen, problem} for whether the frames shown in this window match the narration; cached
    next to the clip per narration and window. None when no frame could be read."""
    from .shorts.match import frames

    key = hashlib.sha1(f"{narration}|{start:.2f}|{length:.2f}".encode()).hexdigest()[:12]
    note = f.with_name(f"{f.stem}.story-{key}.json")
    if note.exists():
        return json.loads(note.read_text(encoding="utf-8"))
    shots = frames(f, start, length)
    if not shots:
        return None
    if client is None:
        from .script import make_client

        client = make_client()
    content = [{"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": d}} for d in shots]
    content.append({"type": "text", "text": (
        f"Frames (start, middle, end) of the footage shown while a short video's voiceover says:\n\"{narration}\"\n"
        "score 0-10, does the footage show what the narration is talking about? 9-10 = exactly what's said; "
        "7-8 = the right subject, fitting; 4-6 = loosely related; 0-3 = something else. seen: what the footage shows, "
        "in a few words. problem: what doesn't match, or \"\". Write in English.")})
    from .config import LLM_MODEL

    response = client.beta.messages.create(
        model=LLM_MODEL, max_tokens=600,
        output_config={"effort": "low", "format": {"type": "json_schema", "schema": FOOTAGE_SCHEMA}},
        messages=[{"role": "user", "content": content}])
    data = json.loads(next(b.text for b in response.content if b.type == "text"))
    verdict = {"score": max(0, min(int(data["score"]), 10)), "seen": str(data["seen"]).strip(),
               "problem": str(data.get("problem", "")).strip()}
    note.write_text(json.dumps(verdict), encoding="utf-8")
    return verdict


class FootageRequest(BaseModel):
    script: VideoScript
    lengths: list[float] = []


@router.post("/api/inspect/preview/short/footage")
def footage_review(req: FootageRequest):
    """Optional AI check of each scene's footage against its narration: three frames of the part shown go to
    Gemini. Advisory only: every item is pass, warning or not checked."""
    from fastapi import HTTPException

    scenes = req.script.scenes
    if not scenes:
        raise HTTPException(400, "The script has no scenes.")
    lengths = [*req.lengths, *[0.0] * len(scenes)][: len(scenes)]
    checks = []
    result = {"stage": "preview", "profile": "short", "profile_label": "AI footage check (Gemini)", "mode": "full",
              "created": datetime.now().isoformat(timespec="seconds"), "checks": checks, "cancelled": False,
              "sampled": "three frames of each scene's footage (the part shown) and its narration, reviewed by Gemini; "
                         "cutaways not included"}
    for i, sc in enumerate(scenes):
        f = _library_file(sc.media) if sc.media else None
        if not sc.narration.strip():
            continue
        if not f or not f.is_file():
            _scene(_check(checks, f"ai.footage.{i}", "storytelling", "not_checked", f"Scene {i + 1}: no footage picked yet",
                          "Footage picked at render can't be checked here."), i)
            continue
        length = lengths[i] or max(sc.seconds, 2.0)
        try:
            v = footage_verdict(f, sc.narration.strip(), max(sc.media_start, 0.0), length)
        except Exception as e:
            raise HTTPException(502, f"The AI footage check didn't work: {e}. The other checks don't need it.")
        if v is None:
            _scene(_check(checks, f"ai.footage.{i}", "storytelling", "not_checked", f"Scene {i + 1}: footage can't be read", sc.media), i)
        elif v["score"] >= FOOTAGE_PASS:
            _scene(_check(checks, f"ai.footage.{i}", "storytelling", "pass", f"Scene {i + 1}: footage fits the narration",
                          f"Shows: {v['seen']}\n(AI-assisted: review it yourself.)", "info"), i)
        else:
            _scene(_check(checks, f"ai.footage.{i}", "storytelling", "warning",
                          f"Scene {i + 1}: footage may not show what the narration says",
                          f"Shows: {v['seen']}. {v['problem']}\n(AI-assisted: review it yourself.)", "low",
                          "Pick footage that shows what's said, or reword the line.",
                          *((sum(lengths[:i]), sum(lengths[:i + 1])) if lengths[i] else ())), i)
    _finish(result, [])
    label_methods(checks)
    return result


@router.post("/api/inspect/preview/short")
def preview_short(req: ShortPreviewRequest):
    from . import drafts

    plan = None
    if req.draft:
        try:
            plan = drafts.load(req.draft).plan
        except (KeyError, ValueError, OSError):
            pass  # a deleted or unreadable draft: the story-beat checks say not checked
    research = None
    if plan is not None and req.draft:
        from .history import research as hr

        try:
            research = hr.load(drafts.DRAFTS_DIR / req.draft / "research.json")
        except (ValueError, OSError):
            pass  # an unreadable brief: the hook is judged without it
    return inspect_short(req.script, req.lang, req.music, req.lengths, req.full, plan, research)


def _song_report(folder: Path) -> Path:
    return folder / "quality" / "preview.json"


@router.post("/api/inspect/preview/song/{slug}")
def preview_song(slug: str, full: bool = False):
    from . import lyricvideo

    folder = lyricvideo._folder(slug)
    rep = inspect_song(folder, full)
    _song_report(folder).parent.mkdir(exist_ok=True)
    _song_report(folder).write_text(json.dumps(rep, ensure_ascii=False, indent=2), encoding="utf-8")
    return {**rep, "outdated": False}


@router.get("/api/inspect/preview/song/{slug}")
def get_preview_song(slug: str):
    from . import lyricvideo

    folder = lyricvideo._folder(slug)
    try:
        rep = json.loads(_song_report(folder).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"report": None}
    rep["outdated"] = rep.get("fingerprint") != _fp(_song_inputs(folder))
    return {"report": rep}
