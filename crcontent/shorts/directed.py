"""The AI Director in Shorts Mode: each episode's plan.json (beats -> scenes -> shots), made at step 1.

The plan's shots steer the stock searches (queries.plan gets each beat's shots); footage.choose still picks one clip
per beat with its own checks, and that clip is recorded on the beat's first shot so the Director tab shows it.
The narration is the sheet's voiceover, word for word.
"""
import re
from pathlib import Path

from ..director_plan import DirectorPlan, Footage, from_scenes

FILE = "plan.json"
FRAMING = re.compile(r"\b(?:(?:up )?in(?:to)? )?(?:the )?(?:cent(?:er|re)(?:ed)? )?frame\b(?!-)|\bcent(?:er|re)e?d\b",
                     re.I)
STYLE = "cinematic_wildlife"  # Shorts Mode is the animal channel's format


def seed(ep) -> DirectorPlan:
    return from_scenes(ep.title, "short", ep.script.lang, STYLE,
                       [{"narration": s.voiceover, "visual_query": s.visual, "on_screen_text": s.text}
                        for s in ep.script.scenes])


def load(job: Path) -> DirectorPlan | None:
    path = Path(job) / FILE
    try:
        return DirectorPlan.model_validate_json(path.read_text(encoding="utf-8")) if path.exists() else None
    except ValueError:
        return None  # unreadable: planned again


def save(plan: DirectorPlan, job: Path) -> None:
    path = Path(job) / FILE
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(plan.model_dump_json(indent=2), encoding="utf-8")
    tmp.replace(path)


def plan_for(ep, job: Path, log=print, direct=None) -> DirectorPlan:
    """The job's plan: the one already there while the beats' voiceover is unchanged (your edits are kept), else
    the AI Director's, else one shot per beat from the sheet when Gemini can't be reached."""
    import os

    from .. import ai_director, llm

    old = load(job)
    if old and [s.narration for s in old.scenes] == [s.voiceover for s in ep.script.scenes]:
        log(f"      Director: kept this Short's plan ({len(old.shots)} shots)")
        return old
    plan = seed(ep)
    if direct is None and not os.getenv("GEMINI_API_KEY"):
        log("      Director: Gemini isn't set up, so one shot per beat from the Visual column")
    else:
        try:
            plan = (direct or ai_director.direct)(plan)
            log(f"      Director: {len(plan.shots)} shots planned for {len(plan.scenes)} beats")
        except (llm.APIError, RuntimeError, ValueError) as e:
            log(f"      Director: couldn't plan the shots ({type(e).__name__}); one shot per beat from the sheet")
    save(plan, job)
    return plan


def shot_notes(plan: DirectorPlan | None) -> dict[int, str]:
    """{beat: its planned shots in a line} for the search planner (only a directed plan says more than the sheet)."""
    if not plan or plan.planned_by != "ai":
        return {}
    out = {}
    for n, scene in enumerate(plan.scenes, 1):
        shots = [s for s in plan.shots if s.scene_id == scene.id]
        out[n] = "; then ".join(f"{s.shot_type.replace('_', ' ')}: {_plain(s.visual_description)}" for s in shots)
    return out


def _plain(text: str) -> str:
    """Without the 9:16 framing words ("centered in vertical frame"): clips are judged on what they show."""
    from ..shot_footage import FORMAT_WORDS

    return " ".join(FRAMING.sub(" ", " ".join(FORMAT_WORDS.sub(" ", text).split())).split())


def record(plan: DirectorPlan, entries: list[dict], job: str = "") -> DirectorPlan:
    """Each beat's chosen clip on its first shot (match from footage.choose's 0-10 score). job: the output folder's
    name, for the thumbnail footage.choose drew (served under /media)."""
    from . import match

    firsts = {}
    for s in plan.shots:
        firsts.setdefault(s.scene_id, s)
    for scene, entry in zip(plan.scenes, entries):
        shot, c = firsts.get(scene.id), entry.get("chosen") or {}
        if not shot or not c.get("file"):
            continue
        score = entry.get("match")
        tier = ("own" if c.get("source") == "own" else "unchecked" if score is None
                else "good" if score >= match.PASS else "weak")  # a placeholder card scores 0: weak, flagged
        shot.footage = Footage(source=c.get("source", ""), kind="video" if c.get("kind") == "video" else "photo",
                               file=str(c["file"]), thumb=f"/media/{job}/storyboard/scene-{entry['scene']:02d}.jpg" if job else "",
                               page=c.get("page", ""), author=c.get("author", ""), licence=c.get("licence", ""),
                               query=entry.get("query", ""), match=tier,
                               problem="; ".join(entry.get("flags", [])))
        shot.warnings = list(entry.get("flags", []))
    return plan
