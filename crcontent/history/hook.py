"""History hook judge (spec 6.4, H3): is the opening of a history Short a specific, truthful question that the first
picture and the ending live up to? Plain rules on the plan (and its approved research), so the same hook always gets
the same answer; this is advice in the pre-render check, never a verdict. The wildlife hook judge (shorts/judge.py,
animal motion) is never used for history.

Checks: no_intro, concrete (a named place/object/person or a date in the hook), curiosity (a question or a
curiosity cue), clarity (the subject or the question within the first ~2 seconds), truthful (no hype words; a
disputed or uncertain claim stated with qualifying words), first_visual (the first shot shows what the hook names,
and isn't a reconstruction), payoff (the plan has a revelation that answers the hook)."""
import re

from .sources import names

FIRST_WORDS = 6  # about two seconds of narration at 2.6 words per second
INTRO = re.compile(r"^\s*(hi|hello|hey|welcome|in this video|today (we|i)|did you know|have you ever wondered|"
                   r"let me tell you|this is hidden history)\b", re.I)
CUES = re.compile(r"\?|\b(why|how|what|who|where|hidden|lost|buried|vanished|disappeared|abandoned|secret|forgotten|"
                  r"never|only|first|last|still|until|mystery|clue|found|discovered|revealed|missing)\b", re.I)
NUMBER = re.compile(r"\b\d{1,4}\b|\b(centur(y|ies)|BC|BCE|AD|CE)\b")
HYPE = re.compile(r"\b(cursed|curse|aliens?|impossible|terrifying|shocking|creepy|they don'?t want you|nobody knows|"
                  r"no one knows|unsolved|unexplained|forbidden)\b", re.I)
HEDGE = re.compile(r"\b(may|might|perhaps|probably|possibly|likely|some (historians|scholars|experts|sources)|"
                   r"disputed|debated|records disagree|it is thought|believed)\b", re.I)
STOP = {"this", "that", "with", "from", "they", "their", "there", "were", "was", "have", "into", "under", "over", "what",
        "most", "people", "never", "still", "only", "about", "which", "when", "where", "would", "could"}


def _words(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z]{4,}", text.lower()) if w not in STOP}


def judge(plan, brief=None) -> list[dict]:
    """[{key, status: pass|warning|fail|not_checked, title, fix}] for the plan's first scene."""
    if not plan.scenes:
        return []
    scene = plan.scenes[0]
    hook = scene.narration.strip()
    first = re.split(r"(?<=[.!?])\s+", hook)[0] if hook else ""
    opening = " ".join(hook.split()[:FIRST_WORDS])
    out = []

    def add(key, ok, title_ok, title_bad, fix, bad="warning"):
        out.append({"key": key, "status": "pass" if ok else bad, "title": title_ok if ok else title_bad,
                    "fix": "" if ok else fix})

    add("no_intro", not INTRO.search(hook), "Starts on the story, no channel intro",
        "Opens with an intro or a stock opener", "Cut the greeting or 'did you know': open on the evidence or the question.",
        bad="fail")
    concrete = bool(names(first) or NUMBER.search(first))
    add("concrete", concrete, "The hook names a concrete place, object, person or date",
        "The hook names nothing concrete", "Name the site, artifact, person or year in the first sentence.")
    add("curiosity", bool(CUES.search(first)), "The hook raises a specific question",
        "The hook states a fact without raising a question", "Turn it into a gap: what was found, what was missing, why.")
    add("clarity", bool(names(opening) or NUMBER.search(opening) or CUES.search(opening)),
        "The subject or the question comes in the first two seconds",
        f"The first {FIRST_WORDS} words don't say what this is about", "Move the subject or the question to the very start.")

    hype = sorted({m.group(0).lower() for m in HYPE.finditer(hook)})
    shaky = [c for c in (brief.claims if brief else []) if c.id in scene.claim_ids and c.status in ("disputed", "uncertain")]
    if hype:
        add("truthful", False, "", f"The hook uses hype words ({', '.join(hype)})",
            "Say what the evidence shows; 'unsolved' or 'nobody knows' only if the research says so.")
    elif shaky and not HEDGE.search(hook):
        add("truthful", False, "", "The hook states a disputed or uncertain claim as fact",
            f"Qualify it ('some historians argue', 'probably'): {shaky[0].claim_text}", bad="fail")
    else:
        add("truthful", True, "The hook's wording is measured", "", "")

    shots = [s for s in plan.shots if s.scene_id == scene.id]
    if not shots or plan.planned_by != "ai":
        out.append({"key": "first_visual", "status": "not_checked", "title": "First picture not planned yet", "fix": ""})
    elif shots[0].visual_origin == "reconstruction":
        add("first_visual", False, "", "The Short opens on a reconstruction",
            "Open on real evidence (the site, an artifact, an archive image) and bring the reconstruction in later.")
    else:
        seen = _words(" ".join([shots[0].subject, shots[0].visual_description, *shots[0].footage_queries]))
        add("first_visual", bool(seen & _words(hook)), "The first shot shows what the hook talks about",
            "The first shot doesn't show what the hook names", "Plan the opening shot on the hook's subject.")

    if plan.planned_by != "ai":
        out.append({"key": "payoff", "status": "not_checked", "title": "Payoff not planned yet", "fix": ""})
    else:
        add("payoff", bool(plan.story.payoff and any(s.phase == "payoff" for s in plan.scenes)),
            "The hook's question is answered by a revelation", "Nothing in the plan answers the hook",
            "End with what the evidence shows, or say clearly what remains uncertain.")
    return out


def score(findings: list[dict]) -> int:
    """Share of the checked rules the hook passes, 0-100 (a guide for comparing drafts, not a gate)."""
    checked = [f for f in findings if f["status"] != "not_checked"]
    return round(100 * sum(f["status"] == "pass" for f in checked) / len(checked)) if checked else 0
