"""Stock searches for every beat, written by Claude from the Visual column.

Stock libraries tag clips with a few plain words ("wet cat", "cat bath"), so each beat gets QUERIES_MIN-QUERIES_MAX
short searches of 2-3 words, always naming the animal, most specific first; plus the planned shot's key objects (what
must be in frame for the clip to show this beat: water, splash, towel, sand), and whether the beat just cuts back to
the opening shot. simpler() is the fallback for beats nothing matched: a plainer shot stock footage likely has, with
its own searches.
"""
import json
import re

from ..config import CLAUDE_MODEL
from ..importer import _keywords

QUERIES_MIN, QUERIES_MAX = 4, 6
REUSE_OPENING = re.compile(r"\b(cut back to|back to|same) (the )?(opening|first|same|start)", re.I)

BEAT = {
    "type": "object",
    "properties": {
        "beat": {"type": "integer"},
        "shot": {"type": "string"},
        "queries": {"type": "array", "items": {"type": "string"}},
        "key_objects": {"type": "array", "items": {"type": "string"}},
        "reuse_opening": {"type": "boolean"},
    },
    "required": ["beat", "shot", "queries", "key_objects", "reuse_opening"],
    "additionalProperties": False,
}
PLAN_SCHEMA = {"type": "object", "properties": {"beats": {"type": "array", "items": BEAT}}, "required": ["beats"],
               "additionalProperties": False}

RULES = (f"queries: {QUERIES_MIN}-{QUERIES_MAX} stock-video searches of 2-3 words each, ALWAYS including the animal's "
         "search word, most specific first, as Pixabay/Pexels tag clips (\"cat bath\", \"wet cat\", \"cat faucet\"); "
         "no adjectives like 'happy' or 'slow-mo', no camera words. key_objects: 1-3 things besides the animal that "
         "MUST be visible for a clip to show this shot (\"water\", \"tap\", \"sand\"); [] when the animal alone is "
         "the shot (a close-up, a cat walking).")


def _ask(prompt: str, schema: dict, max_tokens: int = 4000) -> dict:
    from ..script import make_client

    response = make_client().beta.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=max_tokens,
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
        output_config={"effort": "low", "format": {"type": "json_schema", "schema": schema}},
        messages=[{"role": "user", "content": prompt}],
    )
    if response.stop_reason == "refusal":
        raise RuntimeError("Claude declined")
    return json.loads(next(b.text for b in response.content if b.type == "text"))


def _clean(plan: dict, animal: str) -> dict:
    """2-3 word queries, the animal in every one, no repeats, at most QUERIES_MAX."""
    qs = []
    for q in plan["queries"]:
        q = " ".join(re.sub(r"[^\w\s'-]", " ", q.lower()).split()[:4])
        if q and animal and animal not in q.split():
            q = f"{animal} {q}"
        if q and q not in qs:
            qs.append(q)
    plan["queries"] = qs[:QUERIES_MAX] or [animal]
    plan["key_objects"] = [o.strip().lower() for o in plan["key_objects"] if o.strip()][:3]
    return plan


def local_plan(scene, animal: str) -> dict:
    """Searches from the Visual column's words alone (no Claude)."""
    words = [w for w in _keywords(scene.visual).split() if w != animal][:4]
    queries = [f"{animal} {w}" for w in words] + [animal]
    return {"beat": scene.n, "shot": scene.visual, "queries": queries[:QUERIES_MAX], "key_objects": [],
            "reuse_opening": bool(REUSE_OPENING.search(scene.visual)) and scene.n > 1}


def plan(ep, log=print) -> list[dict]:
    """[{beat, shot, queries, key_objects, reuse_opening}] for every beat of `ep` (ep.animal_search must be set)."""
    animal = ep.animal_search or "animal"
    scenes = ep.script.scenes
    listing = "\n".join(f"{s.n}. VISUAL: {s.visual} | TEXT: {s.text} | VO: {s.voiceover}" for s in scenes)
    try:
        got = _ask(
            f"A YouTube Short about: {ep.animal or animal} (stock search word: \"{animal}\").\nIts beats:\n{listing}\n\n"
            f"For every beat: shot: the planned shot in a few plain words. {RULES} reuse_opening: true only when the "
            "Visual says to cut back to the opening / same shot as the start (never for beat 1).", PLAN_SCHEMA)
        by_beat = {b["beat"]: b for b in got["beats"]}
        out = []
        for s in scenes:
            b = by_beat.get(s.n)
            out.append(_clean(b, animal) if b else local_plan(s, animal))
        out[0]["reuse_opening"] = False
        return out
    except Exception as e:
        log(f"      ! couldn't plan the searches with Claude ({type(e).__name__}); using the Visual column's words")
        return [local_plan(s, animal) for s in scenes]


def simpler(ep, failed: list[tuple[dict, str]], log=print) -> dict[int, dict]:
    """{beat: plan} with a plainer shot stock footage likely has, for beats nothing matched. failed: (beat plan, what
    was found instead)."""
    if not failed:
        return {}
    animal = ep.animal_search or "animal"
    listing = "\n".join(f"Beat {p['beat']}: planned \"{p['shot']}\" (key objects: {', '.join(p['key_objects']) or '-'})."
                        f" Searched: {', '.join(p['queries'])}. Best found: {seen}" for p, seen in failed)
    try:
        got = _ask(
            f"Stock footage of a {ep.animal or animal} didn't have these planned shots:\n{listing}\n\nFor each, pick a "
            "SIMPLER shot that tells the same thing and that stock libraries very likely have (\"cat drinking from a "
            "tap\" instead of \"cat pawing at a running tap\"; \"wet cat\" instead of \"soaked cat looking grumpy, fur "
            f"dripping\"). shot: the simpler shot. {RULES} The simpler shot's key_objects are only what the beat's "
            "POINT needs (\"water\" for a beat about water), never a particular prop the original named (not \"tap\" "
            "when a cat drinking water from a glass or bowl tells the same thing). reuse_opening: false.", PLAN_SCHEMA)
        return {b["beat"]: _clean(b, animal) for b in got["beats"]}
    except Exception as e:
        log(f"      ! couldn't ask Claude for simpler shots ({type(e).__name__})")
        return {}
