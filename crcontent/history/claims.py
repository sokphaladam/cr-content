"""Claims: split narration (or a research answer) into atomic factual claims, map each to evidence segments, then
settle() decides its status from the evidence alone (spec 5.3). A model may propose which excerpt backs a claim; it
can't add a source, an excerpt or a "supported" of its own: unknown ids are dropped, and a claim without attached
evidence is unsupported whatever the model said."""
import hashlib
import json
import os
import re

from .models import CLAIM_TYPES, Contradiction, Evidence, HistoricalClaim, ResearchBrief, ResearchSource, TimelineEvent

EXTRACT = """Split the text into atomic historical claims: one checkable statement each (a date, person, place,
event, cause, consequence, quantity or interpretation). Keep the original meaning; do not add facts. importance:
"central" if the story depends on it, "supporting" for context, "optional" for colour. Skip opinions and questions
that assert nothing. scene_ids: the ids of the scenes the claim comes from (when the text lists scenes)."""

MAP = """You check historical claims against evidence excerpts. For each claim, list ONLY the excerpt ids whose text
directly states or directly contradicts the claim, with stance "supports" or "disputes". An excerpt about a related
but different fact is not evidence. If no excerpt addresses a claim, give it no evidence. Never use your own
knowledge as evidence. Also give: the period, places, people, a two-sentence neutral summary of what the excerpts
establish, a short dated timeline from the excerpts, contradictions between excerpts (claim id and a note), and open
questions the excerpts leave unanswered."""

EXTRACT_SCHEMA = {"type": "object", "required": ["claims"], "properties": {"claims": {"type": "array", "items": {
    "type": "object", "required": ["text", "type", "importance"], "properties": {
        "text": {"type": "string"}, "type": {"type": "string", "enum": list(CLAIM_TYPES)},
        "importance": {"type": "string", "enum": ["central", "supporting", "optional"]},
        "scene_ids": {"type": "array", "items": {"type": "string"}}}}}}}

MAP_SCHEMA = {"type": "object", "required": ["claims"], "properties": {
    "claims": {"type": "array", "items": {"type": "object", "required": ["id", "evidence"], "properties": {
        "id": {"type": "string"},
        "evidence": {"type": "array", "items": {"type": "object", "required": ["excerpt_id", "stance"], "properties": {
            "excerpt_id": {"type": "string"}, "stance": {"type": "string", "enum": ["supports", "disputes"]}}}}}}},
    "period": {"type": "string"}, "places": {"type": "array", "items": {"type": "string"}},
    "people": {"type": "array", "items": {"type": "string"}}, "summary": {"type": "string"},
    "timeline": {"type": "array", "items": {"type": "object", "properties": {
        "date": {"type": "string"}, "event": {"type": "string"}}}},
    "contradictions": {"type": "array", "items": {"type": "object", "properties": {
        "claim_id": {"type": "string"}, "note": {"type": "string"}}}},
    "open_questions": {"type": "array", "items": {"type": "string"}}}}


def _norm(text: str) -> str:
    return " ".join(re.findall(r"\w+", text.lower()))


def claim_id(text: str) -> str:
    return "claim-" + hashlib.sha256(_norm(text).encode()).hexdigest()[:8]


def _ask(system: str, task: str, schema: dict, client) -> dict:
    from .. import llm

    client = client or llm.make_client()
    r = client.beta.messages.create(max_tokens=8192, system=system, messages=[{"role": "user", "content": task}],
                                    output_config={"effort": "low", "format": {"type": "json_schema", "schema": schema}})
    if r.stop_reason != "end_turn":
        raise RuntimeError(f"Gemini didn't finish ({r.stop_reason}).")
    return json.loads(r.content[0].text)


def basic_split(scenes: list[tuple[str, str]]) -> list[HistoricalClaim]:
    """Without Gemini: one claim per sentence that holds a number or a capitalised name (something checkable)."""
    out = []
    for sid, text in scenes:
        for s in re.split(r"(?<=[.!?])\s+", text.strip()):
            if s and re.search(r"\d|\s[A-Z]", " " + s[1:]):
                out.append(HistoricalClaim(id=claim_id(s), claim_text=s.strip(), script_scene_ids=[sid] if sid else []))
    return dedupe(out)


def extract(scenes: list[tuple[str, str]], client=None, most: int = 0) -> list[HistoricalClaim]:
    """scenes: (scene id or "", text). Gemini when set up, else basic_split. most: keep at most this many (0 = all)."""
    if client is None and not os.getenv("GEMINI_API_KEY"):
        return basic_split(scenes)
    listing = "\n".join(f"[{sid}] {text}" if sid else text for sid, text in scenes if text.strip())
    system = EXTRACT + (f"\n\nReturn at most {most} claims: the ones a 40-second history Short would rely on, the "
                        "central ones first." if most else "")
    data = _ask(system, listing, EXTRACT_SCHEMA, client)
    known = {sid for sid, _ in scenes if sid}
    out = []
    for c in data.get("claims") or []:
        text = str(c.get("text", "")).strip()
        if not text:
            continue
        out.append(HistoricalClaim(
            id=claim_id(text), claim_text=text,
            claim_type=c.get("type") if c.get("type") in CLAIM_TYPES else "event",
            importance=c.get("importance") if c.get("importance") in ("central", "supporting", "optional") else "supporting",
            script_scene_ids=[s for s in c.get("scene_ids") or [] if s in known]))
    return dedupe(out)[: most or None]  # the model may ignore the limit


def dedupe(claims: list[HistoricalClaim]) -> list[HistoricalClaim]:
    seen, out = set(), []
    for c in claims:
        if _norm(c.claim_text) not in seen:
            seen.add(_norm(c.claim_text))
            out.append(c)
    return out


def segments(sources: list[ResearchSource]) -> dict[str, tuple[str, str]]:
    """Every usable excerpt: id -> (source id, text). A page that couldn't be read gives none."""
    out = {}
    for s in sources:
        for i, text in enumerate(s.excerpts):
            if text.strip():
                out[f"{s.id}#{i}"] = (s.id, text)
    return out


def map_evidence(brief: ResearchBrief, client=None) -> ResearchBrief:
    """Ask Gemini which excerpts back or dispute each unlocked claim; keep only real excerpt ids."""
    segs = segments(brief.sources)
    todo = [c for c in brief.claims if not c.locked]
    if not todo or not segs:
        return brief
    names = {s.id: s.publisher or s.title for s in brief.sources}
    listing = ("Claims:\n" + "\n".join(f"{c.id}: {c.claim_text}" for c in todo) + "\n\nExcerpts:\n" +
               "\n".join(f"{k} ({names[sid]}): {text}" for k, (sid, text) in segs.items()))
    data = _ask(MAP, listing, MAP_SCHEMA, client)
    by_id = {c.id: c for c in todo}
    for row in data.get("claims") or []:
        claim = by_id.get(row.get("id"))
        if claim is None:
            continue
        claim.evidence = []
        for e in row.get("evidence") or []:
            seg = segs.get(e.get("excerpt_id", ""))
            if seg and not any(x.source_id == seg[0] and x.excerpt == seg[1] for x in claim.evidence):
                claim.evidence.append(Evidence(source_id=seg[0], excerpt=seg[1],
                                               stance="disputes" if e.get("stance") == "disputes" else "supports"))
    if data.get("period"):
        brief.period = str(data["period"])
    brief.places = [str(x) for x in data.get("places") or []] or brief.places
    brief.people = [str(x) for x in data.get("people") or []] or brief.people
    brief.summary = str(data.get("summary") or brief.summary)
    brief.timeline_events = [TimelineEvent(date=str(t.get("date", "")), event=str(t.get("event", "")))
                             for t in data.get("timeline") or [] if t.get("event")] or brief.timeline_events
    ids = {c.id for c in brief.claims}
    brief.contradictions = [Contradiction(claim_id=c.get("claim_id", ""), note=str(c.get("note", "")))
                            for c in data.get("contradictions") or [] if c.get("note") and c.get("claim_id", "") in ids | {""}]
    brief.open_questions = [str(q) for q in data.get("open_questions") or [] if str(q).strip()]
    return brief


def _wikipedia_only(claim: HistoricalClaim, sources: dict[str, ResearchSource]) -> bool:
    return all("wikipedia.org" in sources[e.source_id].url for e in claim.evidence if e.stance == "supports")


def settle(brief: ResearchBrief) -> ResearchBrief:
    """Each claim's status from its evidence (spec 5.3), and contradictions for claims with both stances.
    - evidence must point at a stored source and carry an excerpt (else it's dropped);
    - backing and disputing evidence -> disputed; only disputing -> disputed;
    - backing only -> supported, except a central claim backed by Wikipedia alone -> uncertain;
    - no evidence -> unsupported (or uncertain when the creator marked it so);
    - the creator may always mark a claim less sure (uncertain / disputed), never more sure than its evidence."""
    sources = {s.id: s for s in brief.sources}
    for c in brief.claims:
        c.evidence = [e for e in c.evidence if e.source_id in sources and e.excerpt.strip()]
        c.source_ids = list(dict.fromkeys(e.source_id for e in c.evidence))
        backs = [e for e in c.evidence if e.stance == "supports"]
        disputes = [e for e in c.evidence if e.stance == "disputes"]
        wiki_note = "Backed by Wikipedia only: add an independent source for a central claim."
        c.notes = c.notes.replace(wiki_note, "").strip()
        if disputes:
            derived = "disputed"
        elif backs and c.importance == "central" and _wikipedia_only(c, sources):
            derived = "uncertain"
            c.notes = f"{c.notes} {wiki_note}".strip()
        elif backs:
            derived = "supported"
        else:
            derived = "unsupported"
        chosen = c.status if c.locked else derived
        if derived == "supported":
            c.status = chosen if chosen in ("disputed", "uncertain") else "supported"
        elif derived == "unsupported":
            c.status = "uncertain" if chosen == "uncertain" else "unsupported"
        else:
            c.status = chosen if derived == "uncertain" and chosen == "disputed" else derived
        if backs and disputes and not any(x.claim_id == c.id for x in brief.contradictions):
            brief.contradictions.append(Contradiction(
                claim_id=c.id, note="Sources disagree on this claim.",
                source_ids=list(dict.fromkeys(e.source_id for e in disputes + backs))))
    return brief
