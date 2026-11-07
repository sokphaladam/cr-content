"""History gate (spec 11.2, H7 core): may this history video be rendered and published? Plain rules on the plan, its
research and the creator's recorded decisions; never an AI score.

  blocked          research not approved (central claims unchecked), or an evidence/archive shot whose picture is
                   clearly the wrong period. Nothing overrides these: fix them.
  review_required  items the creator must look at. Most can be approved with a note (kept as an audit record): a
                   disputed or uncertain claim the narration states, a picture standing in for real evidence, a shot
                   with no picture, a hook rule that fails. A picture whose licence isn't stated can't be waved
                   through: confirm its rights (with what you checked) or replace it.
  ready            nothing left: no item, or every review item approved.

Approvals live in history_review.json beside the project, keyed by what they approved (the claim, or the shot and its
picture's page), so changing the picture or the claim asks again."""
import json
from datetime import datetime
from pathlib import Path

FILE = "history_review.json"
NOTE_MIN = 10  # a reason, not "ok"
WRONG_PERIOD = 5  # the visual check's period score under which an evidence shot is misleading


def _item(key, level, title, detail="", overridable=True, fix=""):
    return {"key": key, "level": level, "title": title, "detail": detail, "overridable": overridable, "fix": fix}


def items(plan, brief) -> list[dict]:
    """Everything the creator must fix or look at, before approvals."""
    from .hook import judge

    out = []
    if brief is None or brief.research_status != "approved":
        out.append(_item("research", "blocked", "The research isn't approved",
                         "The video's claims haven't been checked against sources.", False,
                         "Open the Research tab, attach sources to the central claims and approve it."))
    else:
        claims = {c.id: c for c in brief.claims}
        for i, scene in enumerate(plan.scenes, 1):
            for cid in scene.claim_ids:
                c = claims.get(cid)
                if c is None:
                    out.append(_item(f"noclaim:{cid}", "blocked", f"Scene {i} points at a claim that's no longer in the research",
                                     cid, False, "Run the Director again, or re-approve the research."))
                elif c.status == "unsupported":
                    out.append(_item(f"unsupported:{cid}", "blocked", f"Scene {i} states a claim no source supports",
                                     c.claim_text, False, "Attach a source to it in the Research tab, or cut it from the narration."))
                elif c.status in ("disputed", "uncertain"):
                    out.append(_item(f"claim:{cid}", "review", f"Scene {i} states a {c.status} claim", c.claim_text,
                                     fix="Make sure the narration qualifies it ('some historians argue', 'probably')."))
    for s in plan.shots:
        f = s.footage
        if f is None:
            if s.shot_type != "graphic":
                out.append(_item(f"nofootage:{s.id}", "review", f"{s.id} has no picture", s.subject,
                                 fix="Find footage, pick an alternative or add your own file."))
            continue
        where = f.page or f.file
        if s.visual_origin == "reconstruction" and f.asset_type != "reconstruction":
            out.append(_item(f"notrebuilt:{s.id}:{where}", "review", f"{s.id}: found footage where a reconstruction was planned",
                             where, fix="Draw the reconstruction, or approve this footage as what the shot shows."))
        if f.asset_type == "reconstruction" and f.kind == "video":
            out.append(_item(f"label:{s.id}:{where}", "review", f"{s.id}: your reconstruction video needs an on-screen label",
                             where, fix="Burn 'AI reconstruction' into it, then approve saying so."))
        if f.rights == "rights_unknown":
            out.append(_item(f"rights:{s.id}:{where}", "review", f"{s.id}: the picture's licence isn't stated",
                             f"{f.licence or 'no licence given'} · {where}", False,
                             "Check the source page and confirm the rights with what you found, or replace it."))
        if f.period_score is not None and f.period_score < WRONG_PERIOD:
            evidence = s.visual_origin in ("archive", "evidence")
            out.append(_item(f"period:{s.id}:{where}", "blocked" if evidence else "review",
                             f"{s.id}: the picture may be from the wrong period ({f.period_score}/10)",
                             f.problem, not evidence, "Replace it with a picture of the right period."))
        if s.visual_origin in ("archive", "evidence") and f.match == "weak":
            out.append(_item(f"mismatch:{s.id}:{where}", "review", f"{s.id}: the picture may not show {s.subject or 'the evidence'}",
                             f"{f.subject_score}/10 · {f.problem}", fix="Replace it, or approve it saying what it does show."))
        if s.visual_origin in ("archive", "evidence") and f.depicts == "illustrative":
            out.append(_item(f"standin:{s.id}:{where}", "review", f"{s.id}: a stand-in picture for {s.subject or 'the evidence'}",
                             where, fix="Replace it with the real thing, or approve it as illustrative (say how it's "
                                        "presented, e.g. labelled on screen)."))
    for h in judge(plan, brief):
        if h["status"] == "fail":
            out.append(_item(f"hook:{h['key']}", "review", f"Hook: {h['title']}", h["fix"]))
    return out


def load(folder: Path) -> dict:
    try:
        return json.loads((folder / FILE).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"approvals": {}}


def evaluate(plan, brief, folder: Path | None) -> dict:
    """{status, items (each with `approved` when it was), approved: [{key, title, note, at}]}."""
    approvals = load(folder).get("approvals", {}) if folder else {}
    found = items(plan, brief)
    for it in found:
        a = approvals.get(it["key"])
        it["approved"] = a if a and it["overridable"] and it["level"] == "review" else None
    open_ = [it for it in found if not it["approved"]]
    status = "blocked" if any(it["level"] == "blocked" for it in open_) else "review_required" if open_ else "ready"
    return {"status": status, "items": found, "checked_at": datetime.now().isoformat(timespec="seconds"),
            "approved": [{"key": it["key"], "title": it["title"], **it["approved"]} for it in found if it["approved"]]}


def approve(folder: Path, plan, brief, key: str, note: str) -> dict:
    """Record the creator's approval of one review item (with why); refused for blockers and rights."""
    note = " ".join(note.split())
    found = {it["key"]: it for it in items(plan, brief)}
    it = found.get(key)
    if it is None:
        raise KeyError(key)
    if it["level"] != "review" or not it["overridable"]:
        raise ValueError("This one can't be approved with a note: " + (it["fix"] or "fix it first."))
    if len(note) < NOTE_MIN:
        raise ValueError("Say why it's fine (at least a short sentence); it's kept as your record.")
    data = load(folder)
    data.setdefault("approvals", {})[key] = {"note": note[:500], "at": datetime.now().isoformat(timespec="seconds")}
    (folder / FILE).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return evaluate(plan, brief, folder)


def sources_text(plan, brief) -> str:
    """The research sources behind the claims the video states, one per line, for post.txt (spec 7.5)."""
    if brief is None or brief.research_status != "approved":
        return ""
    used = {cid for s in plan.scenes for cid in s.claim_ids} or {c.id for c in brief.claims}
    ids = [sid for c in brief.claims if c.id in used and c.status != "unsupported" for sid in c.source_ids]
    by_id = {s.id: s for s in brief.sources}
    lines = []
    for sid in dict.fromkeys(ids):
        s = by_id.get(sid)
        if s and s.url:
            lines.append(f"- {s.title or s.publisher}{f' ({s.publisher})' if s.publisher and s.publisher != s.title else ''}: {s.url}")
    return "\n".join(dict.fromkeys(lines))


KIND = {"archival": "archival", "museum": "archival", "photograph": "photograph", "stock": "modern stock",
        "reconstruction": "AI reconstruction", "graphic": "graphic", "own": "your own"}


def trace(plan, brief) -> dict:
    """Spec 11 traceability: each claim the video states -> the scenes that state it and the sources behind it; each
    shot -> what kind of material it shows (archival, modern stock, AI reconstruction...) and where it's from."""
    claims = {c.id: c for c in brief.claims} if brief else {}
    by_id = {s.id: s for s in brief.sources} if brief else {}
    stated: dict[str, list[int]] = {}
    for i, scene in enumerate(plan.scenes, 1):
        for cid in scene.claim_ids:
            stated.setdefault(cid, []).append(i)
    out_claims = []
    for cid, scenes in stated.items():
        c = claims.get(cid)
        out_claims.append({"id": cid, "text": c.claim_text if c else "(no longer in the research)",
                           "status": c.status if c else "unsupported", "importance": c.importance if c else "",
                           "scenes": scenes, "sources": [{"title": by_id[x].title or by_id[x].publisher, "url": by_id[x].url}
                                                         for x in (c.source_ids if c else []) if x in by_id]})
    shots = []
    for s in plan.shots:
        f = s.footage
        shots.append({"id": s.id, "origin": s.visual_origin, "subject": s.subject,
                      "material": KIND.get(f.asset_type, f.asset_type or "unknown") if f else "none",
                      "depicts": f.depicts if f else "", "rights": f.rights if f else "",
                      "source": (f.page or f.source) if f else "", "author": f.author if f else "",
                      "licence": f.licence if f else "", "rights_note": f.rights_note if f else ""})
    return {"claims": out_claims, "shots": shots}


def credits_text(plan, clips=()) -> str:
    """Credit lines the research sources don't cover: AI reconstructions (said plainly) and the maps' sources."""
    lines = []
    rebuilt = [s.id for s in plan.shots if s.footage and s.footage.asset_type == "reconstruction"]
    if rebuilt:
        lines.append(f"- AI reconstruction (illustrative, not archival footage): {', '.join(rebuilt)}")
    for c in clips:
        if getattr(c, "track", "") == "graphics" and c.template == "HistoryMap":
            p = c.props
            if p.get("map_source"):
                lines.append(f"- Map: {p['map_source']}")
            if str(p.get("region_geojson", "")).strip() and p.get("region_source"):
                lines.append(f"- Historical region ({p.get('region_dates', '')}): {p['region_source']}")
    return "\n".join(dict.fromkeys(lines))
