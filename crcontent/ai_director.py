"""AI Director: Gemini reads the whole script once and plans it like a documentary filmmaker (AI-DIRECTOR.md 5-8).

It fills a Director Plan (director_plan.py) seeded from the script: the story (hook, central idea, emotional arc,
payoff, facts the pictures must not misrepresent), continuity (subjects, locations, light), what every scene is for,
and 1-5 purposeful shots per scene with framing, camera, light, footage searches and how closely the footage must
match what is said. The narration is never changed. Everything Gemini returns is checked and normalised here before
it reaches the plan; scenes it skips keep their seeded shot, and shots the user locked are never replaced.
"""
import hashlib
import json
import math
import re
from pathlib import Path

from pydantic import ValidationError

from . import director_plan as dp
from .config import CACHE_DIR, LLM_MODEL
from .director_plan import DirectorPlan, Shot

MAX_SHOTS = 5
HOLD = {"short": 4.0, "long": 8.0}  # seconds one shot can hold before viewers drift (sections 8.1, 8.2)
# filler that tells the footage search nothing (section 5.4): dropped from descriptions and searches
FILLER = re.compile(r"\b(cinematic|beautiful|stunning|breathtaking|masterpiece|epic|gorgeous|ultra[- ]?hd|hd|[48]k)\b,?\s*", re.I)
CACHE = CACHE_DIR / "director"

_str = {"type": "string"}
_strs = {"type": "array", "items": _str}
SHOT = {
    "type": "object",
    "properties": {
        "purpose": _str,
        "shot_type": {"type": "string", "enum": list(dp.SHOT_TYPES)},
        "subject": _str,
        "action": _str,
        "visual_description": _str,
        "angle": {"type": "string", "enum": list(dp.ANGLES)},
        "movement": {"type": "string", "enum": list(dp.MOVEMENTS)},
        "framing": {"type": "string", "enum": list(dp.FRAMINGS)},
        "lighting": _str,
        "weight": {"type": "number"},
        "footage_queries": _strs,
        "evidence": {"type": "string", "enum": list(dp.EVIDENCE)},
        "factual_requirements": _strs,
        "sound_design": _strs,
        "alternatives": _strs,
        "visual_priority": {"type": "string", "enum": ["low", "normal", "high"]},
        "transition_out": {"type": "string", "enum": list(dp.TRANSITIONS)},
    },
    "required": ["purpose", "shot_type", "subject", "action", "visual_description", "angle", "movement", "framing",
                 "lighting", "weight", "footage_queries", "evidence", "factual_requirements", "visual_priority",
                 "transition_out"],
}
SCENE = {
    "type": "object",
    "properties": {
        "scene_id": _str,
        "purpose": _str,
        "viewer_objective": _str,
        "emotion": _str,
        "transition_out": {"type": "string", "enum": list(dp.TRANSITIONS)},
        "shots": {"type": "array", "items": SHOT},
    },
    "required": ["scene_id", "purpose", "viewer_objective", "emotion", "transition_out", "shots"],
}
SCHEMA = {
    "type": "object",
    "properties": {
        "story": {"type": "object", "properties": {
            "hook": _str, "central_idea": _str, "emotional_arc": _strs, "payoff": _str, "audience": _str,
            "key_facts": _strs}, "required": ["hook", "central_idea", "emotional_arc", "payoff", "audience", "key_facts"]},
        "continuity": {"type": "object", "properties": {"subjects": _strs, "locations": _strs, "lighting": _strs},
                       "required": ["subjects", "locations", "lighting"]},
        "edit_plan": {"type": "object", "properties": {
            "music_mood": _str, "sound_effects": _strs, "colour_grade": _str,
            "pacing": {"type": "string", "enum": ["slow", "normal", "fast"]}},
            "required": ["music_mood", "sound_effects", "colour_grade", "pacing"]},
        "suggestions": _strs,
        "scenes": {"type": "array", "items": SCENE},
    },
    "required": ["story", "continuity", "edit_plan", "suggestions", "scenes"],
}

SYSTEM = """You are the director, cinematographer and editor of a documentary-style YouTube video. The creator wrote
the narration; you decide what the viewer sees. Read the WHOLE script first: the subject, the story, what the
viewer must understand and feel, the hook and the payoff. Then plan every scene.

For each scene: its purpose in the story, what the viewer should learn or feel, the emotion, the transition into the
next scene, and 1-5 shots in order. A scene is not one stock clip: a described action usually needs an establishing
shot, the detail, the action itself and the result. Every shot must add new information, emotion or evidence; never
add shots just to cut faster.

Each shot: purpose; shot type; subject (exact species / person / object, as the script names it); the action; a
concrete visual description of what is on screen (subject placement, foreground/background, angle, light) with NO
filler words (cinematic, beautiful, stunning, 8K, masterpiece); camera angle, movement and framing; lighting; weight
(its share of the scene's narration time, e.g. 1 for equal shares); 2-4 ENGLISH stock-footage searches from most to
least specific (the exact subject and action first, e.g. "raven bending wire hook", then "raven using tool", then
"raven close up"), plain words a stock library understands (no format words like vertical, 4K or cinematic);
evidence; factual requirements the footage must meet; optional sound design and alternatives.

Camera moves must be possible with stock footage: tracking, aerial, handheld and slow motion need a clip actually
filmed that way; for a still photo use static, slow_push_in, pull_out, pan or tilt.

Evidence: "exact_action" when the narration states a specific real behaviour or event the footage must show;
"subject" when the right subject is enough; "supporting" for related context (habitat, the scientist, the lab);
"illustrative" for a metaphor or abstract idea. Factual accuracy beats pretty pictures: never plan footage that
would pretend to show a behaviour, experiment or historical event it doesn't (a crow flying is not a raven using a
tool). If the exact action may be hard to find, give accurate fallbacks in alternatives (a supporting shot or an
explanatory graphic). Never invent facts that are not in the script.

Continuity: name the recurring subjects, locations and light so footage stays consistent (same species, same time
of day, direction of movement); don't plan unrelated footage just because it shares a keyword.

Never rewrite the narration. If the script could be stronger (slow opening, missing payoff), say so briefly in
suggestions; leave it empty otherwise. Return every scene id you were given, in order, unless told otherwise."""

FORMAT_RULES = {
    "short": """Format: vertical 9:16 YouTube Short, about 22-30 seconds. The first 1-2 seconds need an immediate
strong image or action that sets up a question, surprise or promise; no introduction. One central idea, early
payoff, a satisfying ending that can loop back to the start. Keep shots purposeful: 1-3 per scene, framed for a
vertical screen (subject centred, close and medium shots read best). A single shot held longer than about 4 seconds
loses Shorts viewers: split longer narration into shots that each show something new.""",
    "long": """Format: horizontal 16:9 long YouTube video. A strong cold open, a clear introduction of the story,
development across sections with meaningful pattern changes, establishing shots when a section or location
starts, detail shots, varied shot sizes and angles, strong transitions between sections and a satisfying
conclusion. Rhythm and progression, not constant fast cuts; don't hold the same footage too long (more than about
8 seconds on one shot needs a reason, like a slow reveal).""",
}


def _clean(text: str) -> str:
    return " ".join(FILLER.sub("", text or "").split()).strip(" ,")


def _pick(value: str, allowed: tuple, default: str) -> str:
    return value if value in allowed else default


def _listing(plan: DirectorPlan, only: set[str] | None) -> str:
    lines = []
    for s in plan.scenes:
        mark = " [PLAN THIS]" if only and s.id in only else ""
        extra = "".join(f" | {k}: {v}" for k, v in (("on-screen text", s.on_screen_text), ("visual notes", s.visual_notes)) if v)
        secs = dp.spoken_seconds(s.narration)
        least = min(MAX_SHOTS, max(1, math.ceil(secs / HOLD[plan.project.format])))
        lines.append(f"{s.id}{mark} ({secs} s, at least {least} shot{'s' if least > 1 else ''}): {s.narration!r}{extra}")
    return "\n".join(lines)


def _task(plan: DirectorPlan, only: set[str] | None, note: str) -> str:
    p = plan.project
    task = (f"Title: {p.title!r}\nLanguage of the narration: {p.language}\nVisual style: {p.visual_style}\n"
            f"{FORMAT_RULES[p.format]}\n\nScenes (id, estimated narration seconds, the fewest shots it needs, narration):\n{_listing(plan, only)}")
    if only:
        story = plan.story.model_dump_json()
        task += (f"\n\nRe-plan ONLY the scenes marked [PLAN THIS]; return only those scenes. Keep this story and "
                 f"continuity: {story} {plan.continuity.model_dump_json()}")
    if note:
        task += f"\n\nThe creator's direction: {note}"
    return task


def _ask(plan: DirectorPlan, only: set[str] | None, note: str, client) -> tuple[dict, Path]:
    task = _task(plan, only, note)
    key = hashlib.sha256(json.dumps([LLM_MODEL, SYSTEM, task]).encode()).hexdigest()[:20]
    cached = CACHE / f"{key}.json"
    if cached.exists():  # same script, same request: no second Gemini call (a retry after a failed render, a reload)
        return json.loads(cached.read_text(encoding="utf-8")), cached
    if client is None:
        from .script import make_client

        client = make_client()
    response = client.beta.messages.create(
        model=LLM_MODEL, max_tokens=32000,
        output_config={"effort": "medium", "format": {"type": "json_schema", "schema": SCHEMA}},
        system=SYSTEM, messages=[{"role": "user", "content": task}])
    if getattr(response, "stop_reason", None) == "refusal":
        raise RuntimeError("Gemini declined to plan this video.")
    if getattr(response, "stop_reason", None) == "max_tokens":
        raise RuntimeError("The script is too long to plan in one go. Plan a few scenes at a time.")
    try:
        data = json.loads(next(b.text for b in response.content if b.type == "text"))
    except (StopIteration, json.JSONDecodeError) as e:
        raise RuntimeError("Gemini's plan came back unreadable. Try again.") from e
    return data, cached


def _shots(scene: dp.Scene, raw: list[dict]) -> list[Shot]:
    raw = [r for r in raw if isinstance(r, dict)][:MAX_SHOTS]
    weights = [max(float(r.get("weight") or 1), 0.1) for r in raw]
    total = dp.spoken_seconds(scene.narration)
    shots = []
    for k, (r, w) in enumerate(zip(raw, weights), 1):
        queries = [q for q in (_clean(q) for q in r.get("footage_queries", []) if isinstance(q, str)) if q][:4]
        shots.append(Shot(
            id=f"{scene.id.replace('scene', 'shot')}-{k}", scene_id=scene.id,
            purpose=str(r.get("purpose", "")).strip(),
            shot_type=_pick(r.get("shot_type"), dp.SHOT_TYPES, "medium"),
            subject=str(r.get("subject", "")).strip(), action=str(r.get("action", "")).strip(),
            visual_description=_clean(r.get("visual_description", "")),
            camera=dp.Camera(angle=_pick(r.get("angle"), dp.ANGLES, "eye_level"),
                             movement=_pick(r.get("movement"), dp.MOVEMENTS, "static"),
                             framing=_pick(r.get("framing"), dp.FRAMINGS, "medium")),
            lighting=_clean(r.get("lighting", "")),
            duration_seconds=round(total * w / sum(weights), 2) if total else 0,
            narration_reference=scene.narration,
            footage_queries=queries or ([scene.visual_notes] if scene.visual_notes else []),
            evidence=_pick(r.get("evidence"), dp.EVIDENCE, "subject"),
            factual_requirements=[str(x).strip() for x in r.get("factual_requirements", []) if str(x).strip()],
            sound_design=[str(x).strip() for x in r.get("sound_design", []) if str(x).strip()],
            alternatives=[str(x).strip() for x in r.get("alternatives", []) if str(x).strip()],
            visual_priority=_pick(r.get("visual_priority"), ("low", "normal", "high"), "normal"),
            transition_out=_pick(r.get("transition_out"), dp.TRANSITIONS, "hard_cut")))
    return shots


def direct(plan: DirectorPlan, scene_ids: list[str] | None = None, note: str = "", client=None) -> DirectorPlan:
    """The plan directed by Gemini: the whole video, or just `scene_ids` (the rest is kept as it is).
    Raises llm.APIError / RuntimeError when Gemini can't be reached or answers nonsense; the plan isn't touched then."""
    known = {s.id for s in plan.scenes}
    only = set(scene_ids or []) or None
    if only and only - known:
        raise ValueError(f"Unknown scenes: {', '.join(sorted(only - known))}")
    locked = {s.scene_id for s in plan.shots if s.locked}
    data, cached = _ask(plan, only, note, client)
    try:
        out = _apply(plan, data, only, locked)
    except (ValidationError, TypeError, ValueError, AttributeError) as e:  # wrong types or shapes in Gemini's answer
        raise RuntimeError(f"Gemini's plan wasn't usable ({type(e).__name__}). Try again.") from e
    if not cached.exists():  # only a usable answer is worth reusing
        CACHE.mkdir(parents=True, exist_ok=True)
        cached.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return out


def _apply(plan: DirectorPlan, data: dict, only: set[str] | None, locked: set[str]) -> DirectorPlan:
    out = plan.model_copy(deep=True)
    if not only:  # the project-level analysis comes from a whole-script pass only
        story, cont, edit = data.get("story") or {}, data.get("continuity") or {}, data.get("edit_plan") or {}
        out.story = dp.Story(**{k: story[k] for k in dp.Story.model_fields if k in story})
        out.continuity = dp.Continuity(**{k: cont[k] for k in ("subjects", "locations", "lighting") if k in cont},
                                       visual_style=plan.project.visual_style)
        out.edit_plan = dp.EditPlan(music_mood=str(edit.get("music_mood", "")), colour_grade=str(edit.get("colour_grade", "")),
                                    sound_effects=[str(x) for x in edit.get("sound_effects", [])],
                                    pacing=_pick(edit.get("pacing"), ("slow", "normal", "fast"), "normal"))
        out.suggestions = [str(x).strip() for x in data.get("suggestions", []) if str(x).strip()]

    planned = {r.get("scene_id"): r for r in data.get("scenes", []) if isinstance(r, dict)}
    shots_by_scene: dict[str, list[Shot]] = {}
    for s in plan.shots:
        shots_by_scene.setdefault(s.scene_id, []).append(s)
    directed = 0
    for scene in out.scenes:
        r = planned.get(scene.id)
        if r is None or scene.id in locked or (only and scene.id not in only):
            continue
        shots = _shots(scene, r.get("shots") or [])
        if not shots:
            continue  # nothing usable came back: keep what the scene had
        scene.purpose, scene.viewer_objective, scene.emotion = (str(r.get(k, "")).strip() for k in ("purpose", "viewer_objective", "emotion"))
        scene.transition_out = _pick(r.get("transition_out"), dp.TRANSITIONS, "hard_cut")
        shots_by_scene[scene.id] = shots
        directed += 1
    if not directed:
        raise RuntimeError("Gemini's plan didn't match any scene of the script. Try again.")
    out.shots = [shot for scene in out.scenes for shot in shots_by_scene.get(scene.id, [])]
    out.planned_by = "ai"
    return DirectorPlan.model_validate(out.model_dump())  # the same checks as a plan loaded from disk

