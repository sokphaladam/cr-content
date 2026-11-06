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
        "phase": {"type": "string", "enum": list(dp.PHASES)},
        "beat_role": {"type": "string", "enum": list(dp.BEAT_ROLES)},
        "viewer_question": _str,
        "opens": _strs,
        "resolves": _strs,
        "tension": {"type": "number"},
        "shots": {"type": "array", "items": SHOT},
    },
    "required": ["scene_id", "purpose", "viewer_objective", "emotion", "transition_out", "phase", "beat_role",
                 "viewer_question", "opens", "resolves", "tension", "shots"],
}
SCHEMA = {
    "type": "object",
    "properties": {
        "story": {"type": "object", "properties": {
            "hook": _str, "central_idea": _str, "emotional_arc": _strs, "payoff": _str, "audience": _str,
            "key_facts": _strs,
            "loops": {"type": "array", "items": {"type": "object", "properties": {
                "id": _str, "question": _str, "left_open": {"type": "boolean"}}, "required": ["id", "question", "left_open"]}}},
            "required": ["hook", "central_idea", "emotional_arc", "payoff", "audience", "key_facts", "loops"]},
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

Story structure: Setup -> Tension -> Payoff, as narrative functions, not fixed time slots. Give every scene its
phase and its beat role: setup (pattern_interrupt, curiosity_gap, context), tension (stakes, evidence, escalation,
complication, contrast, relief, mini_payoff, delayed_reveal) or payoff (final_payoff, explanation, callback). The
viewer_question is the question active in the viewer's mind during that beat. List the video's open loops in
story.loops (short ids like "q1" and the exact question or promise); each scene names the loop ids it opens and
resolves. Every loop the video opens must be answered later, or marked left_open when a deliberate loop back to the
start needs it. Tension (0-100) is the relative anticipation of the beat; it need not rise every scene (quiet beats
and relief are fine). Use only the techniques the subject supports: a plain fact needs a crisp question and answer,
not invented danger or fake suspense. Each escalation must add new information or evidence. If the script doesn't
fit this structure, say why in suggestions instead of forcing it.

Edit by story intent (a phase is not an effect preset; fit the subject): curiosity, a strong opening image and
clean framing; investigation, detail and evidence shots with controlled movement; rising tension, tighter framing and
more purposeful shot changes; a key action, show the actual action clearly (slow motion only when the clip was filmed
for it); an explanation, a stable composition the viewer can read; the payoff, hold the reveal long enough to
understand it; a callback, reuse the opening's subject or framing. An exact action outranks a pretty shot.

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


# Hidden History Files (spec 6.2-6.3): added to SYSTEM for history projects only; other documentaries are untouched
HISTORY = """This is a HISTORY documentary Short for the channel Hidden History Files: cinematic, measured, curious and
authoritative; never a horror trailer. One central historical mystery or discovery. Story model: hook (0-3 s:
surprising evidence, a consequence or a specific question; no channel intro), context (who, where, when, quickly),
investigation (clues, records, artifacts or conflicting explanations, in a meaningful order), revelation (what the
evidence actually shows), resonance (why it matters, or what genuinely remains uncertain). These are guides, not
fixed scene boundaries. A loop back to the start is optional: never force one if it makes the conclusion confusing.

Visuals are evidence first. Prefer, in order: authentic archive footage or photographs of the actual subject;
museum, library, university or excavation imagery; the real site or landscape today; close-ups of artifacts,
inscriptions, documents and maps; then context stock (period-neutral landscape, texture, light); a graphic or map;
and only when nothing authentic can exist, a reconstruction. Give every shot its visual_origin: "archive" (genuine
historical material of the subject), "evidence" (the artifact, document, site or record the narration cites, as it
is today), "context" (atmosphere or setting that shows no specific event), "graphic" (map, timeline, date card,
document excerpt), "reconstruction" (an illustration of something no camera recorded; always labelled as such).
Never present context footage or a reconstruction as the event itself: generic "ancient temple" or "old ship"
footage must not imply that a specific event happened there. Never plan animal, wildlife or nature-documentary
footage unless the narration is about that animal. Footage searches name the entity, the place and the period
(e.g. "Phnom Kulen plateau aerial", "Angkor temple lidar map", "Mary Celeste brigantine painting").
Avoid artificial danger, exaggerated claims and conspiracy framing. Distinguish evidence from dramatization. Plan
sound design to support the story (low ambience, impacts only on real story beats), not constant noise. Keep shots
readable on a phone: one clear subject per frame, text-friendly space for dates and names."""

HISTORY_SHORT = """Format: vertical 9:16 YouTube Short, usually 30-50 seconds. The first 1-2 seconds must show and
say something specific that raises a clear question (a concrete object, place, date or person), not a vague tease.
1-3 purposeful shots per scene framed for a vertical screen; a still image needs a slow push-in or pan. A single
shot held longer than about 4 seconds loses viewers: split longer narration into shots that each add evidence."""


def is_history(plan: DirectorPlan) -> bool:
    """History direction for the Hidden History Files profile, or a project given the history look."""
    p = plan.project
    return p.channel_profile_id == "hidden_history_files" or p.visual_style == "cinematic_history"


def _system(plan: DirectorPlan) -> str:
    return f"{SYSTEM}\n\n{HISTORY}" if is_history(plan) else SYSTEM


def _schema(plan: DirectorPlan) -> dict:
    if not is_history(plan):
        return SCHEMA
    schema = json.loads(json.dumps(SCHEMA))  # a copy: the shared schema stays as every other project needs it
    shot = schema["properties"]["scenes"]["items"]["properties"]["shots"]["items"]
    shot["properties"]["visual_origin"] = {"type": "string", "enum": list(dp.VISUAL_ORIGINS)}
    shot["required"] = [*shot["required"], "visual_origin"]
    return schema


def _research_block(brief) -> str:
    """The approved research the narration rests on: what the pictures must not contradict or overstate."""
    if not brief or brief.research_status != "approved":
        return ""
    lines = [f"- [{c.status}] {c.claim_text}" for c in brief.claims if c.status != "unsupported"]
    return ("Approved research (statuses come from attached sources; never show a disputed or uncertain claim as "
            "settled fact, and never add facts beyond these):\n" + "\n".join(lines)) if lines else ""


def link_research(plan: DirectorPlan, brief) -> DirectorPlan:
    """Put an approved brief's claims into the plan: each scene's claim ids (from the claims' scene ids) and the
    story's key facts. Deterministic: no model involved. A brief that isn't approved links nothing."""
    if not brief or brief.research_status != "approved":
        return plan
    out = plan.model_copy(deep=True)
    usable = [c for c in brief.claims if c.status != "unsupported"]
    for scene in out.scenes:
        scene.claim_ids = [c.id for c in usable if scene.id in c.script_scene_ids]
    out.story.key_facts = [c.claim_text for c in usable if c.importance == "central"] or out.story.key_facts
    out.story.research_revision = brief.approved_revision
    return out


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


def _task(plan: DirectorPlan, only: set[str] | None, note: str, research=None) -> str:
    p = plan.project
    history = is_history(plan)
    rules = HISTORY_SHORT if history and p.format == "short" else FORMAT_RULES[p.format]
    task = (f"Title: {p.title!r}\nLanguage of the narration: {p.language}\nVisual style: {p.visual_style}\n"
            f"{rules}\n\nScenes (id, estimated narration seconds, the fewest shots it needs, narration):\n{_listing(plan, only)}")
    from .shorts.analytics import director_brief

    # the imported channel numbers are the wildlife channel's (hook styles, animals): not evidence for history
    if not history and (brief := director_brief()[0]):
        task += f"\n\n{brief}"
    if history and (facts := _research_block(research)):
        task += f"\n\n{facts}"
    if p.target_seconds:
        task += (f"\n\nThe creator aims for about {round(p.target_seconds)} seconds in total; the narration above is fixed, "
                 "so pace the shots (holds, cuts) for that length.")
    if only:
        story = plan.story.model_dump_json()
        task += (f"\n\nRe-plan ONLY the scenes marked [PLAN THIS]; return only those scenes. Keep this story and "
                 f"continuity: {story} {plan.continuity.model_dump_json()}")
    if note:
        task += f"\n\nThe creator's direction: {note}"
    return task


def _ask(plan: DirectorPlan, only: set[str] | None, note: str, client, research=None) -> tuple[dict, Path]:
    task = _task(plan, only, note, research)
    system = _system(plan)
    key = hashlib.sha256(json.dumps([LLM_MODEL, system, task]).encode()).hexdigest()[:20]
    cached = CACHE / f"{key}.json"
    if cached.exists():  # same script, same request: no second Gemini call (a retry after a failed render, a reload)
        return json.loads(cached.read_text(encoding="utf-8")), cached
    if client is None:
        from .script import make_client

        client = make_client()
    response = client.beta.messages.create(
        model=LLM_MODEL, max_tokens=32000,
        output_config={"effort": "medium", "format": {"type": "json_schema", "schema": _schema(plan)}},
        system=system, messages=[{"role": "user", "content": task}])
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
            visual_origin=_pick(r.get("visual_origin"), dp.VISUAL_ORIGINS, ""),
            factual_requirements=[str(x).strip() for x in r.get("factual_requirements", []) if str(x).strip()],
            sound_design=[str(x).strip() for x in r.get("sound_design", []) if str(x).strip()],
            alternatives=[str(x).strip() for x in r.get("alternatives", []) if str(x).strip()],
            visual_priority=_pick(r.get("visual_priority"), ("low", "normal", "high"), "normal"),
            transition_out=_pick(r.get("transition_out"), dp.TRANSITIONS, "hard_cut")))
    return shots


def direct(plan: DirectorPlan, scene_ids: list[str] | None = None, note: str = "", client=None,
           research=None) -> DirectorPlan:
    """The plan directed by Gemini: the whole video, or just `scene_ids` (the rest is kept as it is).
    Raises llm.APIError / RuntimeError when Gemini can't be reached or answers nonsense; the plan isn't touched then."""
    known = {s.id for s in plan.scenes}
    only = set(scene_ids or []) or None
    if only and only - known:
        raise ValueError(f"Unknown scenes: {', '.join(sorted(only - known))}")
    locked = {s.scene_id for s in plan.shots if s.locked}
    data, cached = _ask(plan, only, note, client, research)
    try:
        out = link_research(_apply(plan, data, only, locked), research)
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
        story = {**story, "loops": [l for l in story.get("loops") or [] if isinstance(l, dict) and str(l.get("id", "")).strip()]}
        out.story = dp.Story(**{k: story[k] for k in dp.Story.model_fields if k in story})
        out.continuity = dp.Continuity(**{k: cont[k] for k in ("subjects", "locations", "lighting") if k in cont},
                                       visual_style=plan.project.visual_style)
        out.edit_plan = dp.EditPlan(music_mood=str(edit.get("music_mood", "")), colour_grade=str(edit.get("colour_grade", "")),
                                    sound_effects=[str(x) for x in edit.get("sound_effects", [])],
                                    pacing=_pick(edit.get("pacing"), ("slow", "normal", "fast"), "normal"))
        out.suggestions = [str(x).strip() for x in data.get("suggestions", []) if str(x).strip()]
        from .shorts.analytics import director_brief

        out.evidence = director_brief()[1]

    planned = {r.get("scene_id"): r for r in data.get("scenes", []) if isinstance(r, dict)}
    shots_by_scene: dict[str, list[Shot]] = {}
    for s in plan.shots:
        shots_by_scene.setdefault(s.scene_id, []).append(s)
    directed = 0
    for scene in out.scenes:
        r = planned.get(scene.id)
        if r is None or (only and scene.id not in only):
            continue
        # story beats are notes about the narration, not footage: a scene with a locked shot gets them too
        scene.phase = _pick(r.get("phase"), dp.PHASES, "")
        scene.beat_role = _pick(r.get("beat_role"), dp.BEAT_ROLES, "")
        scene.viewer_question = str(r.get("viewer_question", "")).strip()
        scene.opens, scene.resolves = ([str(x).strip() for x in r.get(k) or [] if str(x).strip()] for k in ("opens", "resolves"))
        t = r.get("tension")
        scene.tension = max(0, min(100, round(t))) if isinstance(t, (int, float)) and not isinstance(t, bool) else None
        directed += 1
        if scene.id in locked:
            continue
        shots = _shots(scene, r.get("shots") or [])
        if not shots:
            continue  # nothing usable came back: keep what the scene had
        scene.purpose, scene.viewer_objective, scene.emotion = (str(r.get(k, "")).strip() for k in ("purpose", "viewer_objective", "emotion"))
        scene.transition_out = _pick(r.get("transition_out"), dp.TRANSITIONS, "hard_cut")
        shots_by_scene[scene.id] = shots
    if not directed:
        raise RuntimeError("Gemini's plan didn't match any scene of the script. Try again.")
    out.shots = [shot for scene in out.scenes for shot in shots_by_scene.get(scene.id, [])]
    out.planned_by = "ai"
    out = DirectorPlan.model_validate(out.model_dump())  # the same checks as a plan loaded from disk
    out.story_warnings = dp.story_check(out)  # a scene re-plan that breaks a loop or the payoff shows up here
    return out

