"""A Short's timeline from the real voiceover (longform.timing.build), and the length rules on it.

Rule 1: the hook beat (beat 1) lasts at most rules.hook_max seconds of real audio.
Rule 2: the Short is rules.length.min to .max seconds; over it, the beat to cut is suggested: never the hook or the
looping last beat, and the one that brings the Short back under the limit while losing the least (the shortest such
beat; when no single beat is enough, the longest one).
"""
from ..longform.parse import Script
from ..longform.timing import Timeline, build
from ..longform.voice import Voice


TAIL_KEEP = 0.08  # seconds kept after a beat's last word (the TTS files end on ~0.35 s of silence)


def spoken_end(voice: Voice) -> float:
    """When the beat's last word ends (its audio length when the words aren't timed)."""
    return voice.words[-1].end if voice.words else voice.seconds


def tighten(voices: list[Voice]) -> list[Voice]:
    """Each voice as long as its speech: the silence a TTS file ends on would only slow every cut. (The file itself is
    untouched: the voice track lays it at the beat's start, and its silent tail is mixed under the next beat.)"""
    for v in voices:
        if v.audio and v.words:
            v.seconds = round(min(v.seconds, spoken_end(v) + TAIL_KEEP), 3)
    return voices


def timeline(script: Script, voices: list[Voice], cfg: dict) -> Timeline:
    """The timeline from the tightened voices, with Shorts notes in place of the long-video ones (8-15 min,
    chapters)."""
    tl = build(script, tighten(voices), cfg)
    tl.chapters, tl.notes = [], []
    return tl


def cut_suggestion(script: Script, tl: Timeline, limit: float) -> dict | None:
    """{beat, length, total_after, text} for the beat to cut when the Short runs over `limit`; None when it fits or
    there's nothing that may be cut."""
    if tl.total <= limit:
        return None
    middle = list(zip(script.scenes, tl.slots))[1:-1]
    if not middle:
        return None
    over = tl.total - limit
    enough = [(s, slot) for s, slot in middle if slot.length >= over]
    scene, slot = min(enough, key=lambda p: p[1].length) if enough else max(middle, key=lambda p: p[1].length)
    return {"beat": scene.n, "length": round(slot.length, 2), "total_after": round(tl.total - slot.length, 2),
            "text": scene.text, "voiceover": scene.voiceover}


def checks(script: Script, tl: Timeline, voices: list[Voice], cfg: dict) -> list[dict]:
    """The timing checks: [{check, ok, detail}] (rules 1 and 2), plus the suggested cut when it's too long."""
    rules = cfg["rules"]
    lo, hi, hook_max = float(rules["length"]["min"]), float(rules["length"]["max"]), float(rules["hook_max"])
    first = next((v for v in voices if v.scene == script.scenes[0].n), None)
    said = spoken_end(first) if first and first.audio else 0.0
    out = [{
        "check": "hook beat", "ok": said <= hook_max,
        "detail": f"the hook line ends at {said:.2f}s, the beat cuts at {tl.slots[0].length:.2f}s "
                  f"(the line must end by {hook_max:.0f}s)" + ("" if said <= hook_max else ": shorten the first line"),
    }]
    total = tl.total
    detail = f"{total:.1f}s from the real voiceover (target {lo:.0f}-{hi:.0f}s, planned {tl.planned_total:.0f}s)"
    cut = cut_suggestion(script, tl, hi)
    if cut:
        detail += (f": cut beat {cut['beat']} (\"{cut['text'] or cut['voiceover'][:40]}\", {cut['length']:.1f}s)"
                   f" -> {cut['total_after']:.1f}s")
    elif total < lo:
        detail += ": shorter than the target (fine if it holds; a longer beat 2-3 adds watch time)"
    out.append({"check": "length", "ok": lo <= total <= hi, "detail": detail, **({"cut": cut} if cut else {})})
    return out
