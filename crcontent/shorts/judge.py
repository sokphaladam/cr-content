"""The pre-flight judge: Gemini rates the hook 1-10 and suggests 3 stronger first lines and 3 on-screen hook texts.

Gemini sees the title, the whole voiceover, the hook beat's line and on-screen text, the plan's hook idea and three
frames of the hook clip as it will be shown. Each suggestion is tagged with a hook style (analytics.HOOK_STYLES), and
the suggestions are then ranked by how that style really did on the channel: its Stayed to watch % from the last
Studio import (analytics.py), Gemini's own order breaking ties and ranking styles never measured. Every suggested
first line is voiced to measure it (it must end by the hook rule's 2 s), and has to keep the loop natural.

loop() is the loop check: do the last line and the first line read as one natural sentence when the Short replays?
"""
import base64
import json
import subprocess
from pathlib import Path

from ..config import LLM_MODEL
from . import analytics

SYSTEM = """You judge the first 2 seconds of YouTube Shorts for an animal-facts channel. A scrolling viewer decides in
under 2 seconds. Strong hooks: the animal doing the thing on screen, one surprising claim or a direct question about
the viewer's own pet, no intro, no "did you know", no build-up. Be concrete: name what works and what doesn't.
First lines are spoken in under 2 seconds (at most 7 words). On-screen hook texts are at most 6 words. Never use
hashtags or emoji in a first line. The Short loops: its last line runs straight into the first line, so a first line
must complete the last one as one natural sentence and must not repeat its words."""

SCHEMA = {
    "type": "object",
    "properties": {
        "score": {"type": "integer"},
        "reason": {"type": "string"},
        "first_lines": {"type": "array", "items": {
            "type": "object", "properties": {
                "text": {"type": "string"}, "style": {"type": "string", "enum": list(analytics.HOOK_STYLES)}},
            "required": ["text", "style"], "additionalProperties": False}},
        "hook_texts": {"type": "array", "items": {
            "type": "object", "properties": {
                "text": {"type": "string"}, "style": {"type": "string", "enum": list(analytics.HOOK_STYLES)}},
            "required": ["text", "style"], "additionalProperties": False}},
    },
    "required": ["score", "reason", "first_lines", "hook_texts"],
    "additionalProperties": False,
}


def _frames(chosen: dict, beat: float) -> list[str]:
    """Three jpgs of the hook clip as the Short shows it (9:16 crop around the animal)."""
    path = Path(chosen["file"])
    start = float(chosen.get("start", 0.0))
    fx, fy = chosen.get("focus") or (0.5, 0.5)
    crop = (f"scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920:"
            f"x='min(max(iw*{fx:.3f}-ow/2,0),iw-ow)':y='min(max(ih*{fy:.3f}-oh/2,0),ih-oh)',scale=360:640")
    out = []
    for t in (start + 0.1, start + beat / 2, start + beat - 0.1):
        args = ["-loop", "1", "-i", str(path)] if path.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp") \
            else ["-ss", f"{t:.2f}", "-i", str(path)]
        raw = subprocess.run(["ffmpeg", "-v", "error", *args, "-frames:v", "1", "-vf", crop, "-f", "image2pipe",
                              "-vcodec", "mjpeg", "-"], stdin=subprocess.DEVNULL, capture_output=True).stdout
        if raw:
            out.append(base64.b64encode(raw).decode())
    return out


def opening(line: str) -> str:
    """A suggested first line as the Short starts with it: Gemini often writes it on from the last line, in lower
    case ("water. Most cats..."), but it's the first thing said."""
    line = line.strip()
    return line[:1].upper() + line[1:]


def rank_suggestions(items: list[dict], stats: dict[str, dict]) -> list[dict]:
    """`items` ({text, style}) best first by their style's Stayed to watch %, each with that number (None when the
    style was never measured); Gemini's order breaks ties."""
    out = []
    for k, it in enumerate(items):
        s = stats.get(it["style"]) or {}
        out.append({**it, "stayed": s.get("stayed"), "viewed": s.get("viewed"), "videos": s.get("videos", 0),
                    "claude_rank": k + 1})
    return sorted(out, key=lambda it: (it["stayed"] is None, -(it["stayed"] or 0), it["claude_rank"]))


def judge(ep, entries: list[dict], tl, log=print) -> dict | None:
    """{score, reason, first_lines, hook_texts, ranked_by} or None without Gemini."""
    from ..script import make_client

    script = ep.script
    hook = script.scenes[0]
    content: list[dict] = [{"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": d}}
                           for d in _frames(entries[0]["chosen"], tl.slots[0].length)]
    stats = analytics.style_stats()
    measured = "\n".join(f"- {s}: stayed to watch {r['stayed']}%, viewed {r['viewed']}% ({r['videos']} videos)"
                         for s, r in stats.items() if r.get("stayed") is not None)
    content.append({"type": "text", "text": (
        f"Title: {ep.title}\nThe hook beat (0-{tl.slots[0].length:.1f}s): the frames above, the line \"{hook.voiceover}\""
        f" and the on-screen text \"{hook.text}\".\n" + (f"The plan's idea for the hook: {ep.hook_idea}\n" if ep.hook_idea
                                                         else "")
        + "The whole voiceover:\n" + "\n".join(f"{s.n}. {s.voiceover}" for s in script.scenes)
        + "\nThe last line runs back into the first one when the Short loops; keep that working.\n"
        + (f"\nHow hook styles did on this channel so far:\n{measured}\n" if measured else "")
        + "\nRate this hook 1-10 (10 = nobody scrolls past). Then give 3 stronger first lines and 3 stronger "
          "on-screen hook texts, each tagged with its hook style. Write them in the video's language.")})
    try:
        response = make_client().beta.messages.create(
            model=LLM_MODEL,
            max_tokens=3000,
            output_config={"effort": "medium", "format": {"type": "json_schema", "schema": SCHEMA}},
            system=SYSTEM,
            messages=[{"role": "user", "content": content}],
        )
    except Exception as e:  # no key, offline: the checks still stand
        log(f"      ! hook judge unavailable ({type(e).__name__}: {str(e)[:120]})")
        return None
    if response.stop_reason == "refusal":
        log("      ! Gemini declined to judge the hook")
        return None
    data = json.loads(next(b.text for b in response.content if b.type == "text"))
    return {"score": max(1, min(int(data["score"]), 10)), "reason": data["reason"].strip(),
            "first_lines": rank_suggestions([{**it, "text": opening(it["text"])} for it in data["first_lines"][:3]], stats),
            "hook_texts": rank_suggestions(data["hook_texts"][:3], stats),
            "ranked_by": "your Stayed to watch % by hook style" if measured else "Gemini (no Studio import yet)"}


LOOP_SCHEMA = {
    "type": "object",
    "properties": {"natural": {"type": "boolean"}, "joined": {"type": "string"}, "problem": {"type": "string"},
                   "fix": {"type": "string"}},
    "required": ["natural", "joined", "problem", "fix"],
    "additionalProperties": False,
}
STOP = set("a an the and or but so to of in on at for with is are was it its it's this that you your my me i we "
           "they he she his her them our will just can not no be do does did have has had".split())


def _words(text: str) -> list[str]:
    import re

    return re.findall(r"[a-z']+", text.lower())


def echoes(last: str, first: str) -> list[str]:
    """Content words the end of the last line shares with the start of the first: the loop repeats itself."""
    tail = {w for w in _words(last)[-5:] if w not in STOP and len(w) > 2}
    head = [w for w in _words(first)[:5] if w not in STOP and len(w) > 2]
    return [w for w in head if w in tail]


def loop(ep, log=print) -> dict:
    """{natural, joined, problem, fix, echoes, by}: does the last line run into the first as one natural sentence?
    Repeated words fail it whatever Gemini says."""
    last, first = ep.script.scenes[-1].voiceover.strip(), ep.script.scenes[0].voiceover.strip()
    rep = echoes(last, first)
    out = {"natural": not rep, "joined": f"{last} {first}", "problem": "", "fix": "", "echoes": rep, "by": "rules"}
    try:
        from ..script import make_client

        response = make_client().beta.messages.create(
            model=LLM_MODEL,
            max_tokens=600,
            output_config={"effort": "low", "format": {"type": "json_schema", "schema": LOOP_SCHEMA}},
            messages=[{"role": "user", "content": (
                "A YouTube Short loops: when it ends, it replays from the start, so its last spoken line runs straight "
                f"into its first.\nLast line: \"{last}\"\nFirst line: \"{first}\"\n\nDo they read as ONE natural "
                "sentence (the first line completes the last)? Repeating or echoing words across the join (\"…will "
                "bring you— / Your cat just brought you…\") fails it, and so does a join that doesn't make grammatical "
                "sense. joined: the two as the viewer hears them. problem: what's wrong, or \"\". fix: a new first line "
                "(at most 7 words, spoken in under 2 s) that completes the last line naturally, or \"\" when it "
                "already works.")}],
        )
        data = json.loads(next(b.text for b in response.content if b.type == "text"))
        out.update(natural=bool(data["natural"]) and not rep, joined=data["joined"].strip(),
                   problem=data["problem"].strip(), fix=opening(data["fix"]) if data["fix"].strip() else "",
                   by="Gemini")
    except Exception as e:
        log(f"      ! loop check without Gemini ({type(e).__name__}): repeated words only")
    if rep and not out["problem"]:
        out["problem"] = f"the join repeats \"{', '.join(rep)}\""
    return out


def measure(items: list[dict], lang: str, cfg: dict, limit: float) -> list[dict]:
    """Each suggested first line voiced as the Short would say it: its spoken length, and whether it ends by
    `limit`."""
    from ..longform.voice import _edge
    from ..render import duration

    for it in items:
        try:
            path, words = _edge(it["text"], lang, cfg)
            secs = words[-1].end if words else duration(path)
            it.update(seconds=round(secs, 2), fits=secs <= limit)
        except Exception:
            it.update(seconds=None, fits=None)
    return items
