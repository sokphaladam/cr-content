"""Pacing for shorts: where the picture hits (impacts on the punchy words, one in the hook) and where it cuts to a new
framing, so something changes on screen every 1-2 seconds instead of one picture sitting there for 8."""
import re

# words that land with a hit: a zoom punch, a shake and a flash (plus a sound on the bigger ones)
IMPACT_WORDS = re.compile(
    r"^(fast(er|est)?|quick(er|est|ly)?|instant(ly)?|boil(s|ed|ing)?|flash(es)?|smash(es|ed|ing)?|crack(s|ed|ing)?|"
    r"punch(es|ed|ing)?|hit(s|ting)?|strik(e|es|ing)|struck|explod(e|es|ed|ing)|explosion|boom|bang|slam(s|med)?|"
    r"crash(es|ed)?|break(s|ing)?|broke|shatter(s|ed|ing)?|snap(s|ped)?|burst(s)?|blast(s|ed)?|kill(s|ed)?|deadly|"
    r"kick(s|ed)?|bite(s)?|zap(s|ped)?|pow|bam|whack(s|ed)?|destroy(s|ed)?|rip(s|ped)?|tear(s)?|launch(es|ed)?|"
    r"supersonic|lightning|bullet|shock(s|ed|wave)?)$", re.I)
HOOK_BY = 2.0  # the hook's hit lands within the first 2 seconds
HOOK_FALLBACK = 0.6  # ...here, when no punchy word is spoken in time
IMPACT_GAP = 1.2  # seconds between two hits in one scene
MAX_IMPACTS = 2  # per scene (more is noise)
CUT_EVERY = 1.8  # a new framing at least this often on a held picture
CUT_CLEAR = 0.45  # no cut this close to a hit (the hit is the change)
SOUND_GAP = 3.0  # hits with a sound effect are at least this far apart (the rest are visual only)
MAX_SOUNDS = 4


def _clean(word: str) -> str:
    return re.sub(r"[^\w']", "", word).lower()


def impacts(words: list, marked: list[str] | None = None, length: float = 0.0, hook: bool = False) -> list[float]:
    """Seconds (from the scene's start) to hit: the punchy words (IMPACT_WORDS, plus `marked`, the words the script
    marked), at most MAX_IMPACTS, IMPACT_GAP apart. The hook scene always gets one within HOOK_BY seconds."""
    marked_set = {_clean(w) for w in marked or [] if w.strip()}
    hits: list[float] = []
    for w in words:
        word = _clean(w.text)
        if word and (word in marked_set or IMPACT_WORDS.match(word)):
            t = round(max(w.start, 0.0), 2)
            if not hits or t - hits[-1] >= IMPACT_GAP:
                hits.append(t)
    hits = hits[:MAX_IMPACTS]
    if hook and not any(t <= HOOK_BY for t in hits):
        early = HOOK_FALLBACK if length <= 0 else min(HOOK_FALLBACK, length / 3)
        hits = [early] + [t for t in hits if t - early >= IMPACT_GAP][:MAX_IMPACTS - 1]
    return [t for t in hits if length <= 0 or t < length - 0.15]


def cuts(length: float, hits: list[float], every: float = CUT_EVERY) -> list[float]:
    """Seconds (from the scene's start) to cut to a new framing of the same shot, so no framing is held longer
    than about `every` seconds. Hits count as changes, so the cuts fill the gaps between them."""
    changes = sorted({0.0, *hits, length})
    out: list[float] = []
    for a, b in zip(changes, changes[1:]):
        n = int((b - a) // every)  # cuts needed to keep each piece under `every`
        for k in range(1, n + 1):
            t = round(a + (b - a) * k / (n + 1), 2)
            if all(abs(t - h) >= CUT_CLEAR for h in hits) and CUT_CLEAR <= t <= length - CUT_CLEAR:
                out.append(t)
    return out


def sound_times(hits: list[float]) -> list[float]:
    """Of all the video's hits (seconds from its start), the ones that also get a sound effect: the hook's, then
    others SOUND_GAP apart, MAX_SOUNDS in all (a boom on every word would be noise)."""
    out: list[float] = []
    for t in sorted(hits):
        if not out or t - out[-1] >= SOUND_GAP:
            out.append(t)
    return out[:MAX_SOUNDS]
