"""Edit Director (attention roadmap M7): the story's beats turned into a few editing decisions, each with its reason.

From the Director Plan's phases and beat roles, the shots' evidence and how well their footage matches, and the
scenes' timing, it proposes:
- calm scenes   explanations, context and relief get no automatic hits or flash and slower re-framing; the final
                payoff is held so the reveal can be understood (Scene.calm = "auto")
- graphics      only where they clarify: the subject named once, early (lower third); a number the voice says in an
                evidence / stakes / payoff beat (fact); a short sequence in an explanation (process)
- sounds        the sound director's accents and ambience (sound_director.py), no sound repeated close together
- gaps          a shot that must show an exact action whose footage doesn't: reported, never covered with a graphic
                or an accent (those scenes get no emphasis at all)

Nothing is applied here. The editor shows the decisions; the creator ticks the ones to apply. Applied clips carry
origin "director" and are replaced when the Edit Director runs again, unless the creator changed them ("edited") or
they're on a locked lane; a scene's calm is only changed while it's "" or "auto" (the creator's "on"/"off" stands).
"""
import math
import re

from . import graphic_templates as gt
from . import sfx, sound_director

GRAPHIC_EVERY = 8      # at most one graphic per this many seconds of video
SAME_TEMPLATE_GAP = 8  # the same template not again within this many seconds
SAME_SOUND_GAP = 8     # the same accent sound not again within this many seconds
GOOD_MATCH = ("own", "drawn", "exact", "good")
CALM_ROLES = {"explanation": "An explanation: a stable picture and no hits, so the words land.",
              "context": "Context the viewer needs: no hits competing with it.",
              "relief": "A moment of relief after the tension: let it breathe."}
NUMBER = re.compile(r"\b(\d[\d,.]*)(?:\s+([A-Za-z]+))?")
STEPS = re.compile(r"\b(first|then|next|after that|finally)\b", re.I)


def _gaps(plan, matched: dict[int, object]) -> tuple[list[dict], set[int]]:
    """Shots that must show an exact action but whose footage doesn't (yet): the gap, and the scenes it's in."""
    out, weak = [], set()
    by_plan = {p.id: i for i, p in matched.items()}
    for shot in plan.shots if plan else []:
        i = by_plan.get(shot.scene_id)
        if i is None or shot.evidence != "exact_action":
            continue
        f = shot.footage
        if f and f.match in GOOD_MATCH:
            continue
        what = (shot.action or shot.purpose or "a specific action").rstrip(".")
        found = ("has no footage yet" if not f else
                 f"only shows the subject, not the action ({f.match.replace('_', ' ')})" if f.match in ("subject_only", "weak") else
                 "hasn't been checked against the narration")
        out.append({"scene": i, "shot": shot.id,
                    "text": f"Scene {i + 1} ({shot.id}) must show: {what}. Its footage {found}. Find a clip of the action "
                            "or reword the line; a graphic over it wouldn't prove it, so none is added there."})
        weak.add(i)
    return out, weak


def _graphic(template: str, start: float, seconds: float, props: dict, scene: int, reason: str) -> dict:
    clean, errors = gt.validate(template, props)
    if errors:
        return {}
    keep = {f["key"]: clean[f["key"]] for f in gt.TEMPLATES[template]["fields"]}
    return {"kind": "graphic", "scene": scene, "reason": reason, "essential": False,
            "clip": {"track": "graphics", "template": template, "template_version": gt.TEMPLATES[template]["version"],
                     "start": round(start, 2), "duration": round(seconds, 2), "props": keep, "note": reason}}


def propose(script, plan, lengths: list[float], use_ai: bool = False, client=None) -> dict:
    """{decisions: [{kind: calm|graphic|sound, scene, reason, essential, clip? | calm?}], gaps, notes, sound_source}."""
    lengths = [*lengths, *[0.0] * len(script.scenes)][: len(script.scenes)]
    total = sum(lengths)
    if not total:
        return {"decisions": [], "gaps": [], "notes": ["Make the voiceover first: the edits are timed on it."], "sound_source": ""}
    starts = [sum(lengths[:i]) for i in range(len(lengths))]
    matched = sound_director._scene_index(script, plan)
    gaps, weak = _gaps(plan, matched)
    mine = [c for c in script.clips if c.origin != "director"]  # the creator's (and edited) clips stay; ours are redone
    decisions = []

    # --- calm scenes: explanations, context, relief; and the payoff held ---
    for i, sc in enumerate(script.scenes):
        p = matched.get(i)
        if not lengths[i] or i == 0 or not p or sc.calm in ("on", "off"):
            continue  # the hook keeps its energy; the creator's own choice stands
        reason = CALM_ROLES.get(p.beat_role) or (
            "The payoff: hold the reveal long enough to understand it, one accent instead of cuts." if p.beat_role == "final_payoff" else "")
        if reason:
            decisions.append({"kind": "calm", "scene": i, "reason": reason, "essential": p.beat_role == "final_payoff"})

    # --- graphics, only where they clarify ---
    graphics: list[dict] = []
    taken = [(c.start, c.start + c.duration, c.template) for c in mine if c.track == "graphics"]

    def free(start: float, seconds: float, template: str) -> bool:
        return (not any(a < start + seconds and start < b for a, b, _ in taken)
                and not any(t == template and abs(a - start) < SAME_TEMPLATE_GAP for a, _, t in taken))

    def add(d: dict) -> None:
        if d and free(d["clip"]["start"], d["clip"]["duration"], d["clip"]["template"]):
            graphics.append(d)
            taken.append((d["clip"]["start"], d["clip"]["start"] + d["clip"]["duration"], d["clip"]["template"]))

    subject = (plan.continuity.subjects[0] if plan and plan.continuity.subjects else "").strip()
    if subject and not any(c.template == "LowerThird" for c in mine):
        i = 1 if len(lengths) > 1 and lengths[1] >= 2 and 1 not in weak else 0
        if lengths[i] >= 2:
            add(_graphic("LowerThird", starts[i] + 0.3, min(3.0, lengths[i] - 0.3), {"title": subject[:32].capitalize(), "subtitle": ""},
                         i, f"Names the subject ({subject}) once, early, so the viewer knows what they're watching."))
    for i, sc in enumerate(script.scenes):
        p = matched.get(i)
        if not lengths[i] or i in weak or not p:
            continue
        if p.beat_role in ("evidence", "stakes", "escalation", "mini_payoff", "final_payoff") and (m := NUMBER.search(sc.narration)):
            shown = m.group(1).rstrip(".,")
            if shown not in sc.on_screen_text and lengths[i] >= 1.5:
                unit = (m.group(2) or "")[:24]
                add(_graphic("Fact", starts[i] + 0.2, min(2.5, lengths[i] - 0.2), {"shown": shown[:16], "unit": unit}, i,
                             f"The number the voice says in this {p.beat_role.replace('_', ' ')} beat, on screen: evidence the viewer can see."))
        if p.beat_role == "explanation" and len(STEPS.findall(sc.narration)) >= 2:
            steps = [s.strip(" ,.") for s in re.split(r"[.;]|\bthen\b|\bnext\b|\bfinally\b", sc.narration, flags=re.I) if s.strip(" ,.")]
            if 2 <= len(steps) <= 5 and all(len(s) <= 40 for s in steps):
                add(_graphic("Process", starts[i] + 0.3, min(4.0, lengths[i] - 0.3), {"title": "", "steps": "; ".join(steps)}, i,
                             "The voice explains a sequence: the steps on screen make it easy to follow."))
    budget = max(1, math.floor(total / GRAPHIC_EVERY))
    decisions += sorted(graphics, key=lambda d: d["clip"]["start"])[:budget]

    # --- sounds: accents on the beats that matter, ambience; none on a scene with an evidence gap ---
    found = sound_director.suggest(script.model_copy(update={"clips": mine}), plan, lengths,
                                   [c.start for c in mine if c.track == "sfx"], use_ai=use_ai, client=client)
    last: dict[str, float] = {}
    for e in found["events"]:
        accent = e["sound"] not in sfx.AMBIENT
        if accent and e["scene"] in weak:
            continue  # an accent would dress up footage that doesn't show what's said
        if accent and e["sound"] in last and e["start"] - last[e["sound"]] < SAME_SOUND_GAP:
            continue
        if any(c.track == "sfx" and c.sound == e["sound"] and c.start < e["start"] + e["duration"] and e["start"] < c.start + c.duration
               for c in mine):
            continue  # the creator already has this sound here
        last[e["sound"]] = e["start"]
        decisions.append({"kind": "sound", "scene": e["scene"], "reason": e["reason"], "essential": e["essential"],
                          "clip": {"track": "sfx", "sound": e["sound"], "start": e["start"], "duration": e["duration"], "gain": e["gain"],
                                   "fade_in": e["fade_in"], "fade_out": e["fade_out"], "duck": e["duck"], "essential": e["essential"],
                                   "note": e["reason"]}})

    notes = [found["note"]] if found.get("note") else []
    if not plan or not any(s.phase for s in plan.scenes):
        notes.insert(0, "No story beats yet: plan the video with the AI Director for calm scenes and story-aware graphics.")
    notes += list(plan.warnings) if plan else []  # repeated shot sizes, slideshow runs: the plan's own rhythm problems
    for k, d in enumerate(decisions):
        d["id"] = f"d{k + 1}"
    return {"decisions": decisions, "gaps": gaps, "notes": notes, "sound_source": found.get("source", "")}
