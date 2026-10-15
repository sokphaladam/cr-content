"""Draft voiceovers: each scene's narration is synthesized once, cached by (voice, rate, text) with its word timings,
so the transcript editor plays exactly the audio the render uses. Pauses cut in the editor are removed at render time.
"""
import hashlib
import json
import subprocess
import unicodedata
from array import array
from pathlib import Path

from . import emoji
from .config import CACHE_DIR
from .render import duration, run
from .tts import Word, synthesize

VOICE_CACHE = CACHE_DIR / "voiceover"


def voice_key(text: str, voice: str, rate: str) -> str:
    return hashlib.sha1(f"{voice}|{rate}|{spoken(text)}".encode("utf-8")).hexdigest()[:20]


def spoken(text: str) -> str:
    """What the voice reads: the narration without its emoji (they'd be read out as "face with tears of joy")."""
    if not emoji.EMOJI.search(text):  # unchanged, so voiceovers cached before emoji keep their key (and cuts)
        return text.strip()
    return emoji.strip(text) or text.strip()


def with_emoji(text: str, words: list[Word]) -> list[Word]:
    """The spoken `words` with the narration's emoji put back, each after the word it follows (before the first word
    when it opens the line), so the captions show them."""
    found = list(emoji.EMOJI.finditer(text))
    if not found or not words:
        return words
    ends, cursor = [], 0  # where each word ends in `text`
    for w in words:
        at = text.find(w.text, cursor)
        cursor = at + len(w.text) if at >= 0 else cursor
        ends.append(cursor if at >= 0 else -1)
    out = [Word(w.text, w.start, w.end) for w in words]
    for m in found:
        before = [i for i, end in enumerate(ends) if 0 <= end <= m.start()]
        if not before:
            out[0].text = f"{m.group()} {out[0].text}"
        else:
            k = before[-1]
            out[k].text += m.group() if ends[k] == m.start() else f" {m.group()}"
            ends[k] = m.end()  # a run of emoji stays together
    return out


def keyword(text: str) -> str:
    """A word as the keyword list stores it: lowercase, without punctuation or symbols around it (Khmer vowel signs
    are kept, unlike a \\w match)."""
    edge = lambda c: unicodedata.category(c)[0] in "PSZ"
    start, end = 0, len(text)
    while start < end and edge(text[start]):
        start += 1
    while end > start and edge(text[end - 1]):
        end -= 1
    return text[start:end].lower()


def scene_voice(text: str, voice: str, rate: str) -> tuple[Path, list[Word]]:
    """The cached voiceover of `text` (synthesized on first use) and its word timings."""
    key = voice_key(text, voice, rate)
    mp3, words_file = VOICE_CACHE / f"{key}.mp3", VOICE_CACHE / f"{key}.json"
    if mp3.exists() and words_file.exists():
        return mp3, [Word(**w) for w in json.loads(words_file.read_text(encoding="utf-8"))]
    VOICE_CACHE.mkdir(parents=True, exist_ok=True)
    tmp = mp3.with_suffix(".part")
    try:
        words = synthesize(spoken(text), voice, tmp, rate=rate)
    except Exception:
        tmp.unlink(missing_ok=True)
        raise
    tmp.replace(mp3)
    words_file.write_text(json.dumps([w.__dict__ for w in words]), encoding="utf-8")
    return mp3, words


def transcript(text: str, voice: str, rate: str) -> dict:
    """What the editor shows for one scene: the audio's key and length, and each word with its time and where it
    sits in `text` (character offsets, so deleting a word can edit the narration)."""
    mp3, words = scene_voice(text, voice, rate)
    out, cursor = [], 0
    for w, shown in zip(words, with_emoji(text, words)):
        at = text.find(w.text, cursor)
        span = [at, at + len(w.text)] if at >= 0 else None
        if span:
            cursor = span[1]
        out.append({"text": w.text, "start": round(w.start, 3), "end": round(w.end, 3), "at": span,
                    "caption": shown.text})
    return {"key": voice_key(text, voice, rate), "duration": round(duration(mp3), 3), "words": out}


def _merged(cuts: list[tuple[float, float]], length: float) -> list[tuple[float, float]]:
    spans = sorted((max(0.0, a), min(length, b)) for a, b in cuts if b - a > 0.01)
    merged: list[tuple[float, float]] = []
    for a, b in spans:
        if merged and a <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(b, merged[-1][1]))
        elif b > a:
            merged.append((a, b))
    return merged


def apply_cuts(mp3: Path, words: list[Word], cuts: list[tuple[float, float]], out: Path) -> tuple[Path, list[Word]]:
    """The voiceover with the `cuts` (seconds) removed, written to `out` (.wav), and the word timings moved to match.
    Words that fall inside a cut are dropped. Without cuts, the original file and words."""
    spans = _merged(cuts, duration(mp3))
    if not spans:
        return mp3, words
    keep = "+".join(f"between(t,{a:.3f},{b:.3f})" for a, b in spans)
    run(["ffmpeg", "-y", "-hide_banner", "-i", str(mp3), "-af", f"aselect='not({keep})',asetpts=N/SR/TB",
         str(out)])

    def shift(t: float) -> float:
        return t - sum(min(b, t) - a for a, b in spans if a < t)

    moved = [Word(w.text, shift(w.start), shift(w.end)) for w in words
             if not any(a <= (w.start + w.end) / 2 < b for a, b in spans)]
    return out, moved


PEAKS_PER_SEC = 50


def peaks(mp3: Path) -> dict:
    """Loudness of a voiceover, PEAKS_PER_SEC values per second scaled to 0-1, cached next to it."""
    cached = mp3.with_suffix(".peaks.json")
    if cached.exists():
        return json.loads(cached.read_text(encoding="utf-8"))
    rate = 8000
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(mp3), "-ac", "1", "-ar", str(rate), "-f", "s16le", "-"],
                         stdin=subprocess.DEVNULL, capture_output=True, check=True).stdout
    samples = array("h", raw[: len(raw) // 2 * 2])
    step = rate // PEAKS_PER_SEC
    values = [max((abs(v) for v in samples[i:i + step]), default=0) for i in range(0, len(samples), step)]
    top = max(values, default=0) or 1
    out = {"rate": PEAKS_PER_SEC, "peaks": [round(v / top, 3) for v in values]}
    cached.write_text(json.dumps(out), encoding="utf-8")
    return out
