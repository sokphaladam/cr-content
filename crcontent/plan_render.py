"""Director Plan -> the existing renderers (AI-DIRECTOR.md 11; milestone 4). Not a renderer of its own.

A scene's shots become what each renderer already knows how to cut:
  Short (pipeline.py): the first shot with footage is the scene's `media`, the later ones `broll` cutaways at their
  planned times, hard cuts between them; a still photo gets the shot's camera move (fx.MOTIONS).
  Long video (longform/video.py): the scene's chosen footage gets `parts` (every shot's file, in order) and
  `weights` (their planned lengths), so the scene cuts through its shots instead of holding one clip.
Footage the user chose by hand in the editor or the storyboard is never replaced. Captions, voice and timing stay
with the renderers, so they remain in sync with the narration.
"""
from pathlib import Path

from .config import ROOT
from .director_plan import DirectorPlan, Footage, Shot

# camera moves a renderer can do to a still photo; moving-camera shots on a photo get a slow push in (shot_footage
# warns about those)
PHOTO_MOVES = {"static": "still", "slow_push_in": "push_in", "pull_out": "pull_out", "pan_left": "pan_left",
               "pan_right": "pan_right", "tilt_up": "tilt_up", "tilt_down": "tilt_down"}
TAIL = 0.5  # the last cutaway runs past the scene's estimated end, so no gap opens if the voice runs long
DISSOLVE = 0.4  # seconds a cutaway planned with a cross dissolve fades in over
# a shot's sound notes -> the sound effects the app can make (sfx.SOUNDS); only clear matches, nothing invented
SOUND_WORDS = {"impact": ("impact", "hit", "thud", "slam", "boom", "crash", "strike"),
               "thunder": ("thunder", "storm", "rumble"),
               "whoosh": ("whoosh", "swoosh", "swish", "rush")}


def cut_sound(before: Shot, shot: Shot) -> str:
    """The sound on the cut into `shot`: a whip pan gets a whoosh; else what its sound notes clearly ask for."""
    if before.transition_out == "whip":
        return "whoosh"
    notes = " ".join(shot.sound_design).lower()
    return next((name for name, words in SOUND_WORDS.items() if any(w in notes for w in words)), "")


def project_path(file: str) -> str:
    """How the Short editor stores media: relative to the data folder, else absolute (pipeline._existing reads both)."""
    path = Path(file).resolve()
    try:
        return path.relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _plan_files(plan: DirectorPlan) -> set[str]:
    """Every file the plan could have put in a scene: a scene showing one of these was filled by the plan."""
    files = set()
    for s in plan.shots:
        for f in [s.footage, *s.candidates]:
            if f and f.file:
                files.add(project_path(f.file))
    return files


def _with_footage(shots: list[Shot]) -> list[tuple[Shot, Footage, float]]:
    """(shot, footage, start second in the scene) for the shots that have footage; a shot without any is covered by
    the one before it."""
    out, at = [], 0.0
    for s in shots:
        if s.footage and s.footage.file and Path(s.footage.file).is_file():
            out.append((s, s.footage, at))
        at += s.duration_seconds
    return out


def _match(plan: DirectorPlan, narrations: list[str]) -> dict[int, str]:
    """script scene index -> plan scene id: by position when the narration is unchanged, else by equal narration
    (scenes added, removed or reordered in the editor). A scene whose narration was rewritten has no plan."""
    by_text = {}
    for p in plan.scenes:
        by_text.setdefault(p.narration.strip(), p.id)
    out = {}
    for i, text in enumerate(narrations):
        if i < len(plan.scenes) and plan.scenes[i].narration.strip() == text.strip():
            out[i] = plan.scenes[i].id
        elif text.strip() in by_text:
            out[i] = by_text[text.strip()]
    return out


def short_scenes(plan: DirectorPlan, scenes: list[dict]) -> tuple[list[dict], list[str]]:
    """The editor's scenes with the plan's footage cut in. Returns (scenes, notes)."""
    mine = _plan_files(plan)
    match = _match(plan, [s.get("narration", "") for s in scenes])
    out, notes, filled = [], [], 0
    for i, scene in enumerate(scenes):
        scene = dict(scene)
        out.append(scene)
        sid = match.get(i)
        if sid is None:
            if scene.get("narration", "").strip():
                notes.append(f"Scene {i + 1}: its narration changed since the plan, so its footage was left alone.")
            continue
        cut = _with_footage([s for s in plan.shots if s.scene_id == sid])
        if not cut:
            continue
        media = scene.get("media") or ""
        broll = scene.get("broll") or []
        if (media and media not in mine) or any(b.get("media") not in mine for b in broll):
            notes.append(f"Scene {i + 1}: kept the footage you chose.")
            continue
        first, footage, _ = cut[0]
        scene["media"], scene["media_start"], scene["layout"] = project_path(footage.file), 0, "fill"
        scene["motion"] = PHOTO_MOVES.get(first.camera.movement, "push_in") if footage.kind == "photo" else ""
        scene["broll"] = []
        planned = [s for s in plan.shots if s.scene_id == sid]
        basis = round(sum(s.duration_seconds for s in planned), 2)
        for k, (shot, f, at) in enumerate(cut[1:], 1):
            end = cut[k + 1][2] if k + 1 < len(cut) else at + shot.duration_seconds + TAIL
            before = planned[planned.index(shot) - 1]  # the shot just before it in the plan
            scene["broll"].append({"media": project_path(f.file), "at": round(at, 2), "duration": round(end - at, 2),
                                   "fade": DISSOLVE if before.transition_out == "cross_dissolve" else 0,
                                   "sound": cut_sound(before, shot), "basis": basis})
        filled += 1
    if filled:
        notes.insert(0, f"Put the plan's footage in {filled} scene{'s' if filled != 1 else ''}.")
    return out, notes


def _credit(f: Footage) -> dict:
    return {"source": f.source, "kind": f.kind, "page": f.page, "author": f.author, "licence": f.licence,
            "licence_url": f.licence_url}


def long_entries(plan: DirectorPlan, entries: list[dict], narrations: list[str]) -> tuple[list[dict], list[str]]:
    """A long video's footage.json entries with each scene cutting through its planned shots. Scenes showing your
    own file (scene-XX.*) or a drawn card keep it."""
    match = _match(plan, narrations)
    out, filled = [], 0
    for i, entry in enumerate(entries):
        entry = dict(entry)
        out.append(entry)
        sid = match.get(i)
        chosen = entry.get("chosen") or {}
        carded = entry.get("kind") == "graphic" and chosen.get("source") == "card"
        if (sid is None or chosen.get("source") == "own" or chosen.get("picked")
                or (entry.get("kind") in ("graphic", "montage") and not carded)):
            continue
        shots = [s for s in plan.shots if s.scene_id == sid]
        if carded:
            # a drawn scene the plan also gave real footage: its graphic shots show the storyboard's card
            card = Footage(source="card", kind="photo", file=chosen["file"])
            cut = _with_footage([s.model_copy(update={"footage": card}) if s.shot_type == "graphic" else s
                                 for s in shots])
            if all(f.source == "card" for _s, f, _at in cut):
                continue
        else:
            cut = _with_footage(shots)
        if not cut:
            continue
        first, f, _ = cut[0]
        lengths = [(cut[k + 1][2] if k + 1 < len(cut) else at + shot.duration_seconds) - at
                   for k, (shot, _f, at) in enumerate(cut)]
        parts = {"plan": True, "parts": [c[1].file for c in cut], "weights": [max(x, 0.1) for x in lengths]}
        if carded:  # stays a card scene (text overlay, storyboard): every footage shot gets a credit line
            entry["chosen"] = {**chosen, "file": f.file, **parts}
            entry["credits"] = [_credit(c[1]) for c in cut if c[1].source != "card"]
        else:
            entry["chosen"] = {"source": f.source, "kind": f.kind, "file": f.file, "page": f.page, "author": f.author,
                               "licence": f.licence, "licence_url": f.licence_url, "check": f.subject_score,
                               "problem": f.problem, "duration": f.duration, "width": f.width, "height": f.height,
                               **parts}
            # every part's credit line (extras.py writes credits from chosen + credits)
            entry["credits"] = [_credit(c[1]) for c in cut[1:]]
        entry["flags"] = [w for c in cut for w in c[0].warnings]
        entry["transition"] = next(p.transition_out for p in plan.scenes if p.id == sid)  # into the next scene
        filled += 1
    return out, [f"Put the plan's footage in {filled} scene{'s' if filled != 1 else ''}."] if filled else []
