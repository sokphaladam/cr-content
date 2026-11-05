"""Sound suggestions for the timeline (attention roadmap M6, section 12.2): a few sound events tied to the story's
beats and the shots, each with when, which sound, how loud, fades, whether it ducks the music, whether it's essential,
and why. Gemini proposes them from the Director Plan when a key is set; otherwise (or when it fails) clear rules do.
Either way they're only suggestions: the editor adds the ones the creator ticks, as ordinary, undoable clips.

Restraint is part of the job: no sound on every cut, never one that implies an action the footage doesn't show
(wings, footsteps) unless a shot's notes say it's seen, ambience under the scenes that name a place's sound.
"""
import json
import math
import re

from . import sfx
from .plan_render import SOUND_WORDS

GAP = 1.5          # seconds between two accents (ambience beds don't count)
PER_SECONDS = 6    # at most one accent per this many seconds of video
AMBIENT_WORDS = {k: SOUND_WORDS[k] for k in ("rain", "wind", "water", "birds", "thunder")}

SCHEMA = {
    "type": "object",
    "properties": {"events": {"type": "array", "items": {
        "type": "object",
        "properties": {"scene": {"type": "integer"}, "offset": {"type": "number"}, "sound": {"type": "string"},
                       "duration": {"type": "number"}, "gain": {"type": "number"}, "fade_in": {"type": "number"},
                       "fade_out": {"type": "number"}, "duck": {"type": "boolean"}, "essential": {"type": "boolean"},
                       "reason": {"type": "string"}},
        "required": ["scene", "offset", "sound", "duration", "gain", "fade_in", "fade_out", "duck", "essential", "reason"],
        "additionalProperties": False}}},
    "required": ["events"], "additionalProperties": False,
}
SYSTEM = """You are the sound designer of a short vertical documentary video. The narration is fixed; you choose a
FEW sound effects from the library given, tied to the story's beats and what the shots show. Rules:
- Sound emphasises meaningful moments only: the payoff, a mini-payoff, a key reveal, the build into it, a place's
  ambience. Never a sound on every cut or every word; quiet beats and explanations get nothing.
- Never imply an action the footage doesn't show: "action" sounds (wings, footsteps) only when a shot's notes say the
  subject is seen doing it. Prefer ambience and tonal accents.
- The voice must stay clear: gain 0.3-1.0 (ambience 0.4-0.7); duck the music under a reveal or payoff accent.
- scene: the scene number; offset: seconds into that scene; duration: at most the sound's length; fades in seconds.
- essential = true only for the one or two sounds the story really needs. reason: one short line, specific to this
  video (what the sound does for the viewer).
Return at most the number of events you are told."""


def _scene_index(script, plan) -> dict[int, object]:
    """Script scene index -> its Director Plan scene, when there's a plan: by narration, and for a line edited since
    the plan was made, by position when the script still has the plan's number of scenes (an edit, not a re-order)."""
    if not plan:
        return {}
    by_text = {s.narration.strip(): s for s in plan.scenes}
    out = {i: by_text[sc.narration.strip()] for i, sc in enumerate(script.scenes) if sc.narration.strip() in by_text}
    if len(script.scenes) == len(plan.scenes):
        used = {id(v) for v in out.values()}
        out |= {i: plan.scenes[i] for i in range(len(script.scenes)) if i not in out and id(plan.scenes[i]) not in used}
    return out


def _notes(plan, pscene) -> str:
    if not plan or not pscene:
        return ""
    return " ".join(n for s in plan.shots if s.scene_id == pscene.id for n in s.sound_design)


def _event(start, sound, length, gain, reason, *, fade_in=0.0, fade_out=0.15, duck=False, essential=False, scene=0):
    dur = min(length, max(sfx_length(sound), 0.1))
    return {"start": round(max(start, 0), 2), "sound": sound, "duration": round(dur, 2), "gain": gain, "fade_in": fade_in,
            "fade_out": min(fade_out, dur / 2), "duck": duck, "essential": essential, "scene": scene, "reason": reason}


_LENGTHS: dict[str, float] = {}


def sfx_length(name: str) -> float:
    if name not in _LENGTHS:
        from .render import duration

        _LENGTHS[name] = duration(sfx.sound(name))
    return _LENGTHS[name]


def rules(script, plan, lengths: list[float]) -> list[dict]:
    """Suggestions from the plan's beats and the scenes' words alone (no AI)."""
    starts = [sum(lengths[:i]) for i in range(len(lengths))]
    matched = _scene_index(script, plan)
    out = []
    for i, sc in enumerate(script.scenes):
        if not lengths[i]:
            continue
        p = matched.get(i)
        text = f"{sc.narration} {sc.visual_query} {_notes(plan, p)}".lower()
        place = next((n for n, words in AMBIENT_WORDS.items()
                      if any(re.search(rf"\b{w}(?:s|es|ed|ing|y|fall)?\b", text) for w in words)), "")
        if place == "thunder":
            out.append(_event(starts[i], "thunder", lengths[i], 0.8, f"Scene {i + 1} talks of a storm: thunder as it starts.", scene=i))
        elif place:
            out.append(_event(starts[i], place, lengths[i], 0.6, f"Scene {i + 1} names {place}: its ambience under the scene.",
                              fade_in=0.4, fade_out=1.0, scene=i))
        role = p.beat_role if p else ""
        if role == "final_payoff":
            out.append(_event(starts[i] + 0.1, "chime", lengths[i], 0.8, f"Scene {i + 1} is the payoff: one clear accent as it lands.",
                              duck=True, essential=True, scene=i))
            if i and lengths[i - 1] >= 2.2:  # the build into it
                out.append(_event(starts[i] - 2.0, "riser", 2.0, 0.6, f"A build out of scene {i} into the payoff.", scene=i - 1))
        elif role in ("mini_payoff", "evidence") and p and p.phase in ("tension", "payoff"):
            out.append(_event(starts[i] + 0.05, "impact", lengths[i], 0.7, f"Scene {i + 1} delivers a {role.replace('_', ' ')}: a hit on it.",
                              duck=True, scene=i))
        elif role == "delayed_reveal":
            out.append(_event(starts[i], "pulse", lengths[i], 0.7, f"Scene {i + 1} holds the answer back: a pulse of anticipation.", scene=i))
    return out


def _space(events: list[dict], total: float, existing: list[float]) -> list[dict]:
    """Keep the essential ones first, then the rest, never two accents within GAP s (or of a sound already on the
    timeline), and at most one accent per PER_SECONDS of video."""
    budget = max(1, math.floor(total / PER_SECONDS))
    kept, taken = [], list(existing)
    for e in sorted(events, key=lambda e: (not e["essential"], e["start"])):
        ambient = e["sound"] in sfx.AMBIENT
        if e["start"] >= total or (not ambient and (budget <= 0 or any(abs(e["start"] - t) < GAP for t in taken))):
            continue
        if any(k["sound"] == e["sound"] and abs(k["start"] - e["start"]) < 0.5 for k in kept):
            continue
        kept.append(e)
        if not ambient:
            taken.append(e["start"])
            budget -= 1
    return sorted(kept, key=lambda e: e["start"])


def _ask(script, plan, lengths, sounds: list[dict], budget: int, client) -> list[dict]:
    from .config import LLM_MODEL

    if client is None:
        from .script import make_client

        client = make_client()
    matched = _scene_index(script, plan)
    scenes = [{"scene": i + 1, "seconds": round(lengths[i], 2), "narration": sc.narration,
               "phase": getattr(matched.get(i), "phase", ""), "beat": getattr(matched.get(i), "beat_role", ""),
               "shot_sound_notes": _notes(plan, matched.get(i)), "footage_search": sc.visual_query}
              for i, sc in enumerate(script.scenes) if lengths[i]]
    library = [{"sound": s["name"], "category": s["category"], "what": s["description"], "seconds": s["duration"]} for s in sounds]
    task = json.dumps({"title": script.title, "scenes": scenes, "library": library, "at_most": budget}, ensure_ascii=False)
    response = client.beta.messages.create(
        model=LLM_MODEL, max_tokens=3000, system=SYSTEM,
        output_config={"effort": "low", "format": {"type": "json_schema", "schema": SCHEMA}},
        messages=[{"role": "user", "content": task}])
    data = json.loads(next(b.text for b in response.content if b.type == "text"))
    starts = [sum(lengths[:i]) for i in range(len(lengths))]
    names = {s["name"] for s in sounds}
    out = []
    for e in data.get("events", []):
        i = int(e.get("scene", 0)) - 1
        if not 0 <= i < len(lengths) or not lengths[i] or e.get("sound") not in names:
            continue  # a scene or sound that doesn't exist: dropped, never invented
        offset = min(max(float(e.get("offset", 0)), 0), max(lengths[i] - 0.1, 0))
        length = min(max(float(e.get("duration", 1)), 0.1), sfx_length(e["sound"]))
        out.append({"start": round(starts[i] + offset, 2), "sound": e["sound"], "duration": round(length, 2),
                    "gain": round(min(max(float(e.get("gain", 0.7)), 0.2), 1.2), 2),
                    "fade_in": round(min(max(float(e.get("fade_in", 0)), 0), length / 2), 2),
                    "fade_out": round(min(max(float(e.get("fade_out", 0.15)), 0), length / 2), 2),
                    "duck": bool(e.get("duck")), "essential": bool(e.get("essential")), "scene": i,
                    "reason": str(e.get("reason", "")).strip()[:200]})
    return out


def suggest(script, plan, lengths: list[float], existing: list[float] = (), use_ai: bool = True, client=None) -> dict:
    """{source: "ai" | "rules", note, events: [{start, sound, duration, gain, fade_in, fade_out, duck, essential,
    scene, reason}]}, spaced out and capped. `existing`: start times of sound clips already on the timeline."""
    from .render import duration

    lengths = [*lengths, *[0.0] * len(script.scenes)][: len(script.scenes)]
    total = sum(lengths)
    if not total:
        return {"source": "rules", "note": "Make the voiceover first: suggestions need the scenes' timing.", "events": []}
    budget = max(1, math.floor(total / PER_SECONDS))
    note = ""
    if use_ai:
        try:
            events = _space(_ask(script, plan, lengths, sfx.catalog(duration), budget, client), total, list(existing))
            return {"source": "ai", "note": "Suggested by Gemini from the story beats and shot notes: listen before keeping them.",
                    "events": events}
        except Exception as e:  # noqa: BLE001 - no Gemini (or a bad answer): the rules still work
            note = f"Gemini couldn't suggest sounds ({type(e).__name__}); these come from simple rules. "
    events = _space(rules(script, plan, lengths), total, list(existing))
    beats = "story beats and " if plan and any(s.phase for s in plan.scenes) else ""
    return {"source": "rules", "note": note + f"Rule-based: from the {beats}scenes' words.", "events": events}
