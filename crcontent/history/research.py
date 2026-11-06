"""Running and storing research briefs (spec 5.1, 5.4). A brief is research.json beside its project (a draft's folder,
a long video's folder) or <data>/research/<id>.json for a topic researched before any script exists.

Topic: Google-grounded answer + Wikipedia -> claims split from the grounded answer -> evidence mapped -> settled.
Script: the narration is split into claims -> each searched -> evidence mapped -> settled.
Every provider failure is written into provider_notes and the brief stays editable."""
import os
import uuid
from datetime import datetime
from pathlib import Path

from . import claims as cl
from . import sources as src
from .models import ResearchBrief

STEPS = 3


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def new(kind: str, ref: str, topic: str = "") -> ResearchBrief:
    return ResearchBrief(id=uuid.uuid4().hex[:10] if kind == "topic" else ref, topic=topic.strip(), project_kind=kind,
                         project_ref=ref, created_at=_now(), updated_at=_now())


def load(path: Path) -> ResearchBrief | None:
    return ResearchBrief.model_validate_json(path.read_text(encoding="utf-8")) if path.exists() else None


def write(path: Path, brief: ResearchBrief) -> ResearchBrief:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(brief.model_dump_json(indent=2), encoding="utf-8")
    os.replace(tmp, path)
    return brief


def save_edit(path: Path, edited: ResearchBrief) -> ResearchBrief:
    """The creator's edits: claims they touched are locked (a re-check keeps them), statuses are settled from the
    evidence again, and an approved brief needs approving again."""
    stored = load(path)
    before = {c.id: c for c in stored.claims} if stored else {}
    for c in edited.claims:
        if c.id not in before or c.model_dump(exclude={"source_ids", "notes"}) != before[c.id].model_dump(exclude={"source_ids", "notes"}):
            c.locked = True
    out = cl.settle(edited.model_copy(update={
        "id": stored.id if stored else edited.id, "created_at": stored.created_at if stored else _now(),
        "revision": (stored.revision if stored else 0) + 1, "updated_at": _now(),
        "approved_revision": stored.approved_revision if stored else 0,
        "approved_at": stored.approved_at if stored else "",
        "research_status": "needs_review" if (stored and stored.claims) or edited.claims else "draft"}))
    return write(path, out)


def blockers(brief: ResearchBrief) -> list[str]:
    """Why the brief can't be approved yet: central claims with no attached evidence."""
    return [c.claim_text for c in brief.claims if c.importance == "central" and c.status == "unsupported"]


def approve(path: Path) -> ResearchBrief:
    brief = load(path)
    if brief is None:
        raise ValueError("Research this project first.")
    if not brief.claims:
        raise ValueError("The brief has no claims to approve.")
    if missing := blockers(brief):
        raise ValueError("These central claims have no source yet: " + " | ".join(missing[:5]) +
                         ". Add a source, change the wording, or mark them supporting.")
    brief.research_status, brief.approved_revision, brief.approved_at = "approved", brief.revision, _now()
    return write(path, brief)


def add_source(path: Path, brief: ResearchBrief, url: str, note: str, excerpt: str) -> ResearchBrief:
    brief.sources = src.merge(brief.sources, [src.add_url(url, note, excerpt)])
    return save_edit(path, brief)


def run(path: Path, brief: ResearchBrief, scenes: list[tuple[str, str]], log=print, client=None,
        google=None, wikipedia=None) -> ResearchBrief:
    """Research `brief` (kept: its sources, and claims the creator edited) and save it. scenes: the project's
    narration as (scene id, text); empty for a topic brief."""
    google, wikipedia = google or src.google, wikipedia or src.wikipedia
    ai = client is not None or bool(os.getenv("GEMINI_API_KEY"))
    brief.provider_notes = []
    note = brief.provider_notes.append

    log(f"[1/{STEPS}] Finding the claims")
    if scenes and not brief.claims:
        try:
            brief.claims = cl.extract(scenes, client)
        except Exception as e:  # noqa: BLE001  any model failure: the basic splitter instead
            note(f"Claims were split without Gemini ({str(e)[:120]}).")
            brief.claims = cl.basic_split(scenes)
        if not ai:
            note("Claims were split sentence by sentence (no Gemini key). Edit them as needed.")

    log(f"[2/{STEPS}] Searching sources")
    question = brief.topic or "Check these statements:\n" + "\n".join(f"- {c.claim_text}" for c in brief.claims)
    answer, found, why = google(question, client) if ai else ("", [], "Google Search grounding needs a Gemini key (Settings); it was skipped.")
    if why:
        note(why)
    brief.sources = src.merge(brief.sources, found)
    # a topic is looked up as written; a script by the names it mentions (the whole narration finds no article)
    lookups = [brief.topic] if brief.topic else src.names(" ".join(t for _, t in scenes))
    wiki, whys = [], []
    for q in lookups:
        got, why = wikipedia(q) if brief.topic else wikipedia(q, 1)
        wiki += got
        whys += [why] if why else []
    if not lookups:
        note("Wikipedia wasn't searched: the narration names no person or place.")
    elif not wiki:
        note(whys[0])
    brief.sources = src.merge(brief.sources, wiki)
    log(f"      {len(found)} web source(s), {len(wiki)} Wikipedia article(s)")
    if not scenes and not brief.claims and answer:
        try:
            brief.claims = cl.extract([("", answer)], client, most=15)
        except Exception as e:  # noqa: BLE001
            note(f"Couldn't split the research into claims ({str(e)[:120]}).")

    log(f"[3/{STEPS}] Matching claims to evidence")
    if ai:
        try:
            cl.map_evidence(brief, client)
        except Exception as e:  # noqa: BLE001  the brief stays editable without the mapping
            note(f"Couldn't match claims to sources automatically ({str(e)[:120]}). Attach evidence by hand.")
    elif brief.claims:
        note("Claims weren't matched to sources automatically (no Gemini key). Attach evidence by hand.")
    cl.settle(brief)
    brief.revision += 1
    brief.updated_at = _now()
    brief.research_status = "needs_review" if brief.claims or brief.sources else "draft"
    unsupported = sum(c.status == "unsupported" for c in brief.claims)
    log(f"      {len(brief.claims)} claims, {unsupported} without a source")
    return write(path, brief)

