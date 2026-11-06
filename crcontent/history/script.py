"""A history Short's script from an approved research brief (spec 6.3, H3): hook -> context -> investigation ->
revelation -> resonance, written only from the brief's claims. The creator asks for it explicitly and reviews the
text before creating the video; after that the narration is never rewritten. Every scene names the claim ids it
states; ids the model invents are dropped, and a scene resting on an unsupported claim is reported."""
import re

from .claims import _ask
from .hook import CUES
from .models import ResearchBrief

STAGES = ("hook", "context", "investigation", "revelation", "resonance")
MATCH = 0.4  # share of a claim's key words and numbers a scene must repeat to count as stating it


def _terms(text: str) -> set[str]:
    """Key words (5+ letters) and numbers: what makes a claim recognisable in reworded narration."""
    return set(re.findall(r"[a-z]{5,}|\d+", text.lower()))


WRITE = """You write narration for Hidden History Files, a YouTube Shorts channel: cinematic, measured, curious and
authoritative; never a horror trailer. Write ONE Short from the approved research claims given, and nothing else.

Structure (guides, not rigid boundaries): hook (0-3 s: a surprising piece of evidence, a consequence or a specific
question about a concrete place, object, date or person; no channel intro, no "did you know", no greeting) ->
context (who, where, when) -> investigation (clues, records, artifacts or conflicting explanations, in a meaningful
order) -> revelation (what the evidence actually shows) -> resonance (why it matters, or what genuinely remains
uncertain). One central mystery or discovery. The FIRST sentence must open a gap the viewer wants closed: a
question, or something found, missing, hidden or never explained, named concretely; a plain description ("This
codex has 230 pages") is not a hook.

Truth rules: use only the claims listed. A "disputed" claim needs qualified wording ("some historians argue",
"records disagree"); an "uncertain" one careful wording ("probably", "may have"). Never add dates, numbers, names,
quotes or explanations that aren't in the claims. Don't call something unsolved or say "nobody knows" if the claims
show it was resolved; "no surviving evidence" is not "nobody knows". No conspiracy framing or invented danger.

Spoken English, short sentences, about 2.6 words per second. For each scene: the stage, the narration, a short
visual note (what the viewer should see: the actual site, artifact, document, map, archive photo; say
"reconstruction" if only an illustration could show it), and the ids of the claims the narration states."""

SCHEMA = {"type": "object", "required": ["title", "scenes"], "properties": {
    "title": {"type": "string"},
    "scenes": {"type": "array", "items": {"type": "object", "required": ["stage", "narration", "visual", "claim_ids"],
                                          "properties": {
        "stage": {"type": "string", "enum": list(STAGES)}, "narration": {"type": "string"},
        "visual": {"type": "string"}, "claim_ids": {"type": "array", "items": {"type": "string"}}}}}}}


def write(brief: ResearchBrief, target_seconds: float = 40, client=None) -> dict:
    """{"text": the script in the Scene / Visual / Voiceover layout Script to Video reads, "scenes": [{stage,
    narration, visual, claim_ids}], "warnings": [...]}. The brief must be approved."""
    if brief.research_status != "approved":
        raise ValueError("Approve the research first: the script is written only from approved claims.")
    usable = [c for c in brief.claims if c.status != "unsupported"]
    if not usable:
        raise ValueError("The research has no sourced claims to write from.")
    words = round((target_seconds or 40) * 2.6)
    task = (f"Topic: {brief.topic or brief.summary}\nTarget: about {round(target_seconds or 40)} seconds "
            f"(about {words} words in total).\n\nApproved claims:\n" +
            "\n".join(f"{c.id} [{c.status}, {c.importance}]: {c.claim_text}" for c in usable))
    if brief.open_questions:
        task += "\n\nOpen questions the sources leave unanswered:\n" + "\n".join(f"- {q}" for q in brief.open_questions)
    data = _ask(WRITE, task, SCHEMA, client)
    status = {c.id: c.status for c in brief.claims}
    terms = {c.id: _terms(c.claim_text) for c in usable}
    scenes, warnings = [], []
    for i, s in enumerate(data.get("scenes") or [], 1):
        narration = " ".join(str(s.get("narration", "")).split())
        if not narration:
            continue
        ids = [x for x in s.get("claim_ids") or [] if x in status]
        if not ids:  # the model left them out (a live run did, for most scenes): claims the narration repeats
            said = _terms(narration)
            ids = [cid for cid, t in terms.items() if t and len(t & said) / len(t) >= MATCH]
        if any(status[x] == "unsupported" for x in ids):
            warnings.append(f"Scene {i} uses a claim without a source; reword or remove it.")
        scenes.append({"stage": s.get("stage") if s.get("stage") in STAGES else "", "narration": narration,
                       "visual": " ".join(str(s.get("visual", "")).split()), "claim_ids": ids})
    if not scenes:
        raise RuntimeError("Gemini returned no script. Try again.")
    first = re.split(r"(?<=[.!?])\s+", scenes[0]["narration"])[0]
    if not CUES.search(first):  # the same rule the pre-render hook check uses
        warnings.append("The opening states a fact without raising a question: consider rewording the first line.")
    if not any(s["claim_ids"] for s in scenes):
        warnings.append("No scene names the claims it states: check the facts against the research by hand.")
    title = " ".join(str(data.get("title", "")).split()) or brief.topic or "History Short"
    text = title + "\n\n" + "\n\n".join(f"Scene {i}\nVisual: {s['visual']}\nVoiceover: {s['narration']}"
                                         for i, s in enumerate(scenes, 1)) + "\n"
    return {"title": title, "text": text, "scenes": scenes, "warnings": warnings}


def attach(brief: ResearchBrief, scenes: list[dict], plan_scene_ids: list[str], narrations: list[str]) -> ResearchBrief:
    """The topic brief for the project made from its script: each claim gets the plan scene ids whose narration came
    from a script scene that stated it (matched by narration text, so a re-split script still links)."""
    out = brief.model_copy(deep=True)
    norm = lambda t: " ".join(t.lower().split())  # noqa: E731

    def ids_for(text: str) -> set[str]:  # written scenes this plan scene came from (whole, split or joined)
        t = norm(text)
        return {x for s in scenes if t and (norm(s["narration"]) in t or t in norm(s["narration"])) for x in s["claim_ids"]}

    linked = {sid: ids_for(text) for sid, text in zip(plan_scene_ids, narrations)}
    for c in out.claims:
        c.script_scene_ids = [sid for sid in plan_scene_ids if c.id in linked[sid]]
    return out
