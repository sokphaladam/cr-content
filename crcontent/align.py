"""Lyric timing: when each sung word starts and ends in the song, for karaoke captions.

Uses stable-ts (Whisper forced alignment) when it's installed: the lyrics are already known, so it only has to
line them up with the vocals. Without it, lines are spread evenly over their section, which is rough but usable.
"""
import difflib
import json
import os
import re
import subprocess
import tempfile
import traceback
import unicodedata
from dataclasses import asdict, dataclass
from pathlib import Path

from .lyrics import SongScript
from .tts import Word

_model = None


@dataclass
class LyricLine:
    section: int  # index into song.sections
    text: str
    start: float  # seconds from the start of the song
    end: float
    words: list[Word]  # absolute times; one Word per space-separated token of `text`
    check: bool = False  # the automatic timing isn't sure about this line: worth checking by ear


def section_spans(song: SongScript, total: float) -> list[tuple[float, float]]:
    """(start, end) of each section in the real audio. ElevenLabs keeps section lengths, so scale the plan to fit."""
    # an uploaded song has no planned lengths: share the time by how much is sung (instrumental parts count as 2 lines)
    weights = [s.seconds for s in song.sections] if song.seconds else \
        [len(s.lyrics) or 2 for s in song.sections]
    planned = max(sum(weights), 1)
    spans, t = [], 0.0
    for w in weights:
        length = w * total / planned
        spans.append((t, t + length))
        t += length
    return spans


def spans_from_lines(song: SongScript, lines: list["LyricLine"], total: float) -> list[tuple[float, float]]:
    """(start, end) of each section from when its lyrics are actually sung: for songs we didn't compose, so
    there are no planned section lengths. A section starts half a second before its first line; sections
    without lyrics (intro, solo) begin when the previous section's singing ends."""
    n = len(song.sections)
    first: list[float | None] = [None] * n
    last: list[float | None] = [None] * n
    for line in lines:
        if 0 <= line.section < n:
            i = line.section
            first[i] = line.start if first[i] is None else min(first[i], line.start)
            last[i] = line.end if last[i] is None else max(last[i], line.end)
    starts: list[float] = []
    for i in range(n):
        if i == 0:
            starts.append(0.0)
        elif first[i] is not None:
            starts.append(min(max(starts[-1], first[i] - 0.5), total))
        else:
            prev_end = next((last[j] for j in range(i - 1, -1, -1) if last[j] is not None), starts[-1])
            starts.append(min(max(starts[-1], prev_end + 0.5), total))
    return [(starts[i], starts[i + 1] if i + 1 < n else total) for i in range(n)]


def _lines(song: SongScript) -> list[tuple[int, str]]:
    return [(i, " ".join(line.split())) for i, s in enumerate(song.sections) for line in s.lyrics if line.strip()]


def _weighted(tokens: list[str], start: float, end: float) -> list[Word]:
    """Split [start, end] across tokens in proportion to their length."""
    weights = [len(t) + 1 for t in tokens]
    total, t, out = sum(weights), start, []
    for tok, w in zip(tokens, weights):
        step = (end - start) * w / total
        out.append(Word(tok, t, t + step))
        t += step
    return out


def even_timing(song: SongScript, total: float) -> list[LyricLine]:
    """Fallback: each section's lines share its span (with a short lead-in), words weighted by length."""
    spans = section_spans(song, total)
    out = []
    for i, section in enumerate(song.sections):
        lines = [" ".join(l.split()) for l in section.lyrics if l.strip()]
        if not lines:
            continue
        start, end = spans[i]
        start += min(0.4, (end - start) * 0.05)
        weights = [len(l) + 4 for l in lines]
        t = start
        for line, w in zip(lines, weights):
            length = (end - start) * w / sum(weights)
            words = _weighted(line.split(), t, t + length * 0.92)  # small breath before the next line
            out.append(LyricLine(i, line, words[0].start, words[-1].end, words))
            t += length
    return out


def _load_model():
    global _model
    if _model is None:
        import stable_whisper
        import torch

        cuda = torch.cuda.is_available()
        name = os.getenv("WHISPER_MODEL", "medium" if cuda else "base")
        _model = stable_whisper.load_model(name, device="cuda" if cuda else "cpu")
    return _model


def demucs_available() -> bool:
    try:
        import demucs  # noqa: F401
        return True
    except ImportError:
        return False


def _align(audio: Path, lines: list[tuple[int, str]], lang: str, extra: dict, offset: float = 0.0) -> list[LyricLine]:
    """Forced-align `lines` to `audio`; times are shifted by `offset` (where a cut-out stretch begins in the song)."""
    result = _load_model().align(str(audio), "\n".join(text for _, text in lines), language=lang,
                                 original_split=True, **extra)
    # Whisper may split tokens differently from our spaces (punctuation, Khmer clusters), so map by
    # character position: every non-space character of the lyrics gets the timing of the aligned word holding it.
    chars = [(float(w.start) + offset, float(w.end) + offset) for seg in result.segments for w in seg.words
             for c in w.word if not c.isspace()]
    if not chars:
        raise RuntimeError("alignment returned no words")
    total_chars = sum(len(tok) for _, text in lines for tok in text.split())
    out, pos = [], 0
    for section, text in lines:
        words = []
        for tok in text.split():
            a = min(len(chars) - 1, pos * len(chars) // total_chars)
            b = min(len(chars) - 1, (pos + len(tok) - 1) * len(chars) // total_chars)
            words.append(Word(tok, chars[a][0], max(chars[b][1], chars[a][0] + 0.05)))
            pos += len(tok)
        out.append(LyricLine(section, text, words[0].start, words[-1].end, words))
    return out


LOST_GAP_SEC = 12.0  # a line this far from the rest of its section, right after another section, was put in the wrong place


def suspect_lines(lines: list[LyricLine], total: float) -> set[int]:
    """Lines Whisper most likely lost track of:
    - squeezed: half or more of the words have (next to) no length, or the whole line lasts a blink
    - past the end of the song
    - the first line of a section far ahead of the rest of it (or the last line far behind), typically stuck to the
      previous section across an instrumental break. A line that really is sung there aligns to the same place
      again on the second pass, so it's left as it was.
    """
    bad = set()
    for i, line in enumerate(lines):
        short = sum(w.end - w.start <= 0.06 for w in line.words)
        if short * 2 >= len(line.words) or line.end - line.start < 0.2 * len(line.words) or line.start >= total - 0.3:
            bad.add(i)
    for i in range(len(lines) - 1):
        a, b = lines[i], lines[i + 1]
        if a.section != b.section or b.start - a.end < LOST_GAP_SEC:
            continue
        if i == 0 or lines[i - 1].section != a.section:
            bad.add(i)  # first line of its section, far ahead of the rest
        if i + 2 >= len(lines) or lines[i + 2].section != b.section:
            bad.add(i + 1)  # last line of its section, far behind the rest
    return bad


def _cut(audio: Path, start: float, end: float, out: Path) -> Path:
    subprocess.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-ss", f"{start:.3f}", "-to", f"{end:.3f}",
                    "-i", str(audio), "-ac", "1", "-ar", "44100", str(out)], check=True)
    return out


def _realign(audio: Path, lines: list[LyricLine], lang: str, tries: list[dict], total: float,
             bad: set[int] | None = None) -> tuple[list[LyricLine], set[int]]:
    """Second pass: each run of suspect lines is aligned again on its own, against just the stretch of the song between
    the well-timed lines around it. Whisper is far more reliable on a short stretch with only the words sung there.
    Each set of alignment options in `tries` is tried in turn; the first that clears up the stretch is kept.
    `bad`: the lines to redo (default: the suspect ones). Returns the lines and the indexes it managed to redo."""
    bad = suspect_lines(lines, total) if bad is None else bad
    fixed: set[int] = set()
    if not bad:
        return lines, fixed
    out = list(lines)
    runs: list[list[int]] = []
    for i in sorted(bad):
        if runs and runs[-1][-1] == i - 1:
            runs[-1].append(i)
        else:
            runs.append([i])
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        for n, run in enumerate(runs):
            start = out[run[0] - 1].end if run[0] > 0 else 0.0
            end = out[run[-1] + 1].start if run[-1] + 1 < len(out) else total
            if end - start < 0.15 * sum(len(lines[i].words) for i in run):
                continue  # no room to find them in
            try:
                clip = _cut(audio, start, end, Path(tmp) / f"part{n}.wav")
            except Exception:
                continue
            best, best_bad = None, None
            for extra in tries:
                try:
                    again = _align(clip, [(lines[i].section, lines[i].text) for i in run], lang, extra, offset=start)
                except Exception:
                    continue  # keep the first pass for this stretch
                again = [LyricLine(l.section, l.text, l.start, l.end, [Word(w.text, min(w.start, end), min(w.end, end))
                                                                       for w in l.words]) for l in again]
                n_bad = len(suspect_lines(again, end))
                if best_bad is None or n_bad < best_bad:
                    best, best_bad = again, n_bad
                if n_bad == 0:
                    break
            # only a clean result counts: a stretch that comes back squeezed is no better than before
            if best is not None and best_bad * 4 <= len(run) - 1:
                for i, line in zip(run, best):
                    out[i] = LyricLine(line.section, line.text, line.words[0].start, line.words[-1].end, line.words)
                fixed.update(run)
    return out, fixed


CHUNK_SEC, OVERLAP_SEC = 40.0, 6.0


def transcribe_words(audio: Path, lang: str, extra: dict, total: float) -> list[Word]:
    """Every word Whisper hears, with its time, transcribed in overlapping ~40 s chunks.

    On a whole song Whisper often stops writing after a minute or two (or loops); short chunks keep it on track.
    Where chunks overlap, each word is taken from the chunk it sits in the middle of.
    """
    model = _load_model()
    words: list[Word] = []
    step = CHUNK_SEC - OVERLAP_SEC
    starts = [i * step for i in range(max(1, int((total - OVERLAP_SEC) // step) + 1))]
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        for k, start in enumerate(starts):
            end = min(total, start + CHUNK_SEC)
            if end - start < 1.0:
                continue
            clip = _cut(audio, start, end, Path(tmp) / f"chunk{k}.wav")
            # temperature 0 without fallback: the same answer every time, and no "creative" retries that invent
            # lyrics over instrumental parts; each chunk on its own so one misheard chunk can't steer the next
            result = model.transcribe(str(clip), language=lang, temperature=0.0, condition_on_previous_text=False,
                                      **extra)
            keep_from = start + (OVERLAP_SEC / 2 if k > 0 else 0.0)
            keep_to = end - (OVERLAP_SEC / 2 if k + 1 < len(starts) else -1.0)
            for seg in result.segments:
                for w in seg.words:
                    s, e = float(w.start) + start, float(w.end) + start
                    if keep_from <= (s + e) / 2 < keep_to and w.word.strip():
                        words.append(Word(w.word.strip(), s, e))
    return sorted(words, key=lambda w: w.start)


def _norm(token: str) -> str:
    return re.sub(r"[^\w]", "", token.lower().replace("’", "'"))


def _same(a: str, b: str) -> bool:
    """Lyric word vs heard word: equal, or close enough to be a mishearing ("shop" / "sharp")."""
    if not a or not b:
        return False
    if a == b:
        return True
    return min(len(a), len(b)) >= 3 and difflib.SequenceMatcher(None, a, b).ratio() >= 0.75


def _fill_gaps(tokens: list[tuple[int, str]], times: list[tuple[float, float] | None],
               pace: float = 0.4) -> list[tuple[float, float]]:
    """Words with no time of their own (`None`) get one between the timed words around them, by length.
    tokens: (line index, word) per entry of `times`."""
    times = list(times)
    n = len(times)
    # spread unmatched words between the matched ones around them, by length
    i = 0
    while i < n:
        if times[i] is not None:
            i += 1
            continue
        k = i
        while k < n and times[k] is None:
            k += 1
        run = list(range(i, k))
        left = times[i - 1][1] if i > 0 else None
        right = times[k][0] if k < n else None
        if left is None and right is None:
            left, right = 0.0, pace * len(run)
        elif left is None:
            left = max(0.0, right - pace * len(run))
        elif right is None:
            right = left + pace * len(run)
        # a long gap (instrumental) between matches: keep these words next to the line they belong to
        same_left = i > 0 and tokens[i - 1][0] == tokens[i][0]
        same_right = k < n and tokens[k][0] == tokens[k - 1][0]
        if right - left > pace * len(run) * 3:
            if same_right and not same_left:
                left = right - pace * len(run)
            else:
                right = left + pace * len(run)
        for w, idx in zip(_weighted([tokens[x][1] for x in run], left, max(right, left + 0.05)), run):
            times[idx] = (w.start, w.end)
        i = k
    return times


def match_lyrics(lines: list[tuple[int, str]], heard: list[Word]) -> tuple[list[LyricLine], set[int]]:
    """Time the lyrics from what Whisper heard: match lyric words to heard words in order (longest common sequence,
    allowing mishearings), so a repeated chorus lines up with the right repeat. Matched words take the heard times;
    the rest are spread between them. Returns the lines and the indexes of weak lines (under half the words heard),
    whose timing is a guess."""
    tokens = [(li, tok) for li, (_, text) in enumerate(lines) for tok in text.split()]
    a = [_norm(t) for _, t in tokens]
    b = [_norm(w.text) for w in heard]
    n, m = len(a), len(b)
    # LCS table (n, m are a few hundred words: fine)
    score = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(n - 1, -1, -1):
        row, below = score[i], score[i + 1]
        for j in range(m - 1, -1, -1):
            row[j] = below[j + 1] + 1 if _same(a[i], b[j]) else max(below[j], row[j + 1])
    anchor: dict[int, Word] = {}
    i = j = 0
    while i < n and j < m:
        if _same(a[i], b[j]) and score[i][j] == score[i + 1][j + 1] + 1:
            anchor[i] = heard[j]
            i, j = i + 1, j + 1
        elif score[i + 1][j] >= score[i][j + 1]:
            i += 1
        else:
            j += 1
    # a lone short word matched far from any neighbour ("the", "I") is more likely chance than a real match
    for i in list(anchor):
        if len(a[i]) <= 3 and (i - 1) not in anchor and (i + 1) not in anchor:
            del anchor[i]

    times = _fill_gaps(tokens, [(anchor[i].start, anchor[i].end) if i in anchor else None for i in range(n)])

    out, weak, pos = [], set(), 0
    for li, (section, text) in enumerate(lines):
        toks = text.split()
        idxs = range(pos, pos + len(toks))
        words = [Word(tok, times[x][0], max(times[x][1], times[x][0] + 0.05)) for tok, x in zip(toks, idxs)]
        if sum(x in anchor for x in idxs) * 2 < len(toks):
            weak.add(li)
        out.append(LyricLine(section, text, words[0].start, words[-1].end, words))
        pos += len(toks)
    return out, weak


def _letters(text: str) -> str:
    """Letters, marks and digits only, lowercased: what two spellings of the same sung words have in common."""
    return "".join(c for c in text.lower() if unicodedata.category(c)[0] in "LMN")


def load_timestamps(path: Path) -> list[Word] | None:
    """The song generator's own word timings (timestamps.json: [{"word", "start_ms", "end_ms"}]), or None."""
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        words = [Word(str(d.get("word") or d.get("text") or ""), float(d["start_ms"]) / 1000, float(d["end_ms"]) / 1000)
                 for d in data]
    except (ValueError, KeyError, TypeError):
        return None
    return sorted((w for w in words if _letters(w.text)), key=lambda w: w.start) or None


MIN_COVERAGE = 0.6  # share of the lyrics' letters that must be found in the sung words to trust them


def known_timing(lines: list[tuple[int, str]], sung: list[Word]) -> tuple[list[LyricLine], set[int]] | None:
    """Time the lyrics from words whose times are already known (the song generator reports when it sang each word).

    Matching works letter by letter rather than word by word, so it doesn't matter how either side splits words
    (Khmer phrases, "gonna" / "gon na", punctuation), and ad-libs or repeats the singer added are simply skipped.
    Every lyric word takes the time of the sung letters it matched; words with no match are spread between their
    neighbours. Returns None when too little of the lyrics was found (the song isn't singing these lyrics).
    The same input always gives the same timing.
    """
    heard: list[tuple[float, float]] = []  # per sung letter: (start, end)
    sung_text = []
    for w in sung:
        letters = _letters(w.text)
        span = max(w.end - w.start, 0.01)
        for k, c in enumerate(letters):
            sung_text.append(c)
            heard.append((w.start + span * k / len(letters), w.start + span * (k + 1) / len(letters)))
    tokens = [(li, tok) for li, (_, text) in enumerate(lines) for tok in text.split()]
    owner: list[int] = []  # per lyric letter: index of its token
    lyric_text = []
    for ti, (_, tok) in enumerate(tokens):
        for c in _letters(tok):
            lyric_text.append(c)
            owner.append(ti)
    if not lyric_text or not sung_text:
        return None
    matcher = difflib.SequenceMatcher(None, "".join(lyric_text), "".join(sung_text), autojunk=False)
    hit: dict[int, list[tuple[float, float]]] = {}
    found = 0
    for a, b, size in matcher.get_matching_blocks():
        if size < 2:  # a lone letter in common is chance, not the same word
            continue
        found += size
        for k in range(size):
            hit.setdefault(owner[a + k], []).append(heard[b + k])
    if found < MIN_COVERAGE * len(lyric_text):
        return None

    times: list[tuple[float, float] | None] = []
    for ti, (_, tok) in enumerate(tokens):
        spans = hit.get(ti)
        # a word counts as found when most of its letters were
        if spans and len(spans) * 2 >= len(_letters(tok)):
            times.append((spans[0][0], max(spans[-1][1], spans[0][0] + 0.05)))
        else:
            times.append(None)
    times = _fill_gaps(tokens, times)

    out, weak, pos = [], set(), 0
    for li, (section, text) in enumerate(lines):
        toks = text.split()
        idxs = range(pos, pos + len(toks))
        words = [Word(tok, times[x][0], max(times[x][1], times[x][0] + 0.05)) for tok, x in zip(toks, idxs)]
        if sum(x in hit for x in idxs) * 2 < len(toks):
            weak.add(li)
        out.append(LyricLine(section, text, words[0].start, words[-1].end, words))
        pos += len(toks)
    return out, weak


def whisper_timing(audio: Path, song: SongScript, lang: str, isolate_vocals: bool = False,
                   total: float | None = None) -> list[LyricLine]:
    """Lyric timing from what's actually sung. Raises ImportError when stable-ts isn't installed.

    1. Transcribe the song in short chunks and match the heard words to the lyrics (see match_lyrics).
    2. Lines too few words were heard for are aligned again on their own, in the gap between their neighbours.
    3. When hardly anything matches (an unusual recording), fall back to forced alignment of the whole song.
    Lines the timing still isn't sure about are marked `check`.

    isolate_vocals: strip the instruments first with Demucs (when installed). Whisper hears words far better
    without drums and synths, so use it whenever there's no separate vocals stem.
    """
    lines = _lines(song)
    if not lines:
        return []
    extra = {"denoiser": "demucs"} if isolate_vocals and demucs_available() else {}
    if total is None:
        from .render import duration
        total = duration(audio)
    try:
        heard = transcribe_words(audio, lang, extra, total)
    except Exception:  # anything going wrong here still deserves a real alignment, not even spacing
        traceback.print_exc()
        return _forced_timing(audio, lines, lang, extra, total)
    matched, weak = match_lyrics(lines, heard)
    if len(weak) * 2 > len(lines):  # under half the lines recognisable: the transcript can't be trusted
        return _forced_timing(audio, lines, lang, extra, total)
    out = repair(matched)
    # voice detection first: a line nobody recognised often got placed in an instrumental part
    tries = [{**extra, "vad": True}, extra]
    out, fixed = _realign(audio, out, lang, tries, total, bad=weak | suspect_lines(out, total))
    out = repair(out)
    # a stretch can come back mostly right with one line still off (often the last, pushed past the end): once its
    # neighbours are fixed there's room to find that line on its own
    if suspect_lines(out, total):
        out, more = _realign(audio, out, lang, tries, total)
        fixed |= more
        out = repair(out)
    # stretches still not recognised (soft, reverb-heavy singing Whisper can't make out): take them from a forced
    # alignment of the whole song, where they fit between their neighbours and look right there
    still = (weak - fixed) | suspect_lines(out, total)
    unsure = weak - fixed  # timed without hearing the words, nor a clean second pass
    if still:
        forced = _forced_timing(audio, lines, lang, extra, total)
        unsure_forced = suspect_lines(forced, total)
        replaced: set[int] = set()
        runs: list[list[int]] = []
        for i in sorted(still):
            if runs and runs[-1][-1] == i - 1:
                runs[-1].append(i)
            else:
                runs.append([i])
        for run in runs:
            lo = out[run[0] - 1].end if run[0] > 0 else 0.0
            hi = out[run[-1] + 1].start if run[-1] + 1 < len(out) else total
            cand = [forced[i] for i in run]
            in_order = all(a.end <= b.start + 0.5 for a, b in zip(cand, cand[1:]))
            if in_order and lo - 0.5 <= cand[0].start and cand[-1].end <= hi + 0.5 and not unsure_forced & set(run):
                for i in run:
                    out[i] = forced[i]
                    replaced.add(i)
        # where the forced alignment lands on the same spot, two different methods agree: no need to check
        unsure = {i for i in unsure if abs(out[i].start - forced[i].start) > DISAGREE_SEC or i in unsure_forced}
        unsure |= replaced  # only the last-resort method placed these
    return _flag(repair(out), unsure, total)


def _forced_timing(audio: Path, lines: list[tuple[int, str]], lang: str, extra: dict,
                   total: float) -> list[LyricLine]:
    """Forced alignment of the whole song, timed with and without voice detection, plus a second pass over lines
    it lost track of."""
    def refine(first: list[LyricLine], tries: list[dict]) -> list[LyricLine]:
        # repair first: a stray word can drag a good line into a bad stretch and make that stretch too long to retry
        out = repair(first)
        for _ in range(2):  # fixing one stretch can reveal another (a line that only looked fine next to a squeezed one)
            out = repair(_realign(audio, out, lang, tries, total)[0])
        return out

    plain = refine(_align(audio, lines, lang, extra), [extra])
    # Voice detection (Silero VAD, downloaded once) keeps words out of instrumental parts: without it Whisper often
    # "hears" the first lines in the intro. But it can miss soft, reverb-heavy singing and squeeze those lines. So the
    # song is timed both ways and each stretch where they disagree takes the version that holds up better.
    vad = {**extra, "vad": True}
    try:
        voiced = refine(_align(audio, lines, lang, vad), [vad, extra])
    except Exception:  # VAD model unavailable (offline on first use)
        return _flag(plain, set(), total)
    merged, unsure = merge_timings(plain, voiced, total)
    return _flag(repair(merged), unsure, total)


def _flag(lines: list[LyricLine], unsure: set[int], total: float) -> list[LyricLine]:
    """Mark the lines to check by ear: where the two timings disagreed and neither held up better, plus any line
    that still looks wrong (squeezed, out of place). Then make sure no line runs into the next one."""
    for i in unsure | suspect_lines(lines, total):
        lines[i].check = True
    return untangle(lines)


def untangle(lines: list[LyricLine], gap: float = 0.05) -> list[LyricLine]:
    """A line that runs into the next one ends just before it (its words squeezed to fit), so the karaoke never
    shows two lines at once."""
    out = []
    for i, line in enumerate(lines):
        nxt = lines[i + 1].start if i + 1 < len(lines) else float("inf")
        if line.end > nxt - gap and nxt - gap - line.start >= 0.2:
            k = (nxt - gap - line.start) / max(line.end - line.start, 0.01)
            words = [Word(w.text, line.start + (w.start - line.start) * k, line.start + (w.end - line.start) * k)
                     for w in line.words]
            line = LyricLine(line.section, line.text, words[0].start, words[-1].end, words, line.check)
        out.append(line)
    return out


DISAGREE_SEC = 1.5


def merge_timings(plain: list[LyricLine], voiced: list[LyricLine], total: float) -> tuple[list[LyricLine], set[int]]:
    """Line by line: where both timings agree, keep the voice-detected one. Each run of lines where they disagree
    takes the version with fewer suspect lines; on a tie, voice detection wins (it knows where nobody sings).
    Returns the lines and the indexes of the tied ones, which nothing could settle."""
    out: list[LyricLine] = []
    unsure: set[int] = set()
    i, n = 0, min(len(plain), len(voiced))
    while i < n:
        if abs(plain[i].start - voiced[i].start) <= DISAGREE_SEC:
            out.append(voiced[i])
            i += 1
            continue
        j = i
        while j < n and abs(plain[j].start - voiced[j].start) > DISAGREE_SEC:
            j += 1
        a, b = plain[i:j], voiced[i:j]
        bad_a, bad_b = len(suspect_lines(a, total)), len(suspect_lines(b, total))
        out += a if bad_a < bad_b else b
        if bad_a == bad_b:
            unsure.update(range(i, j))
        i = j
    return out, unsure


MAX_WORD_SEC = 4.0
GAP_SEC = 2.5  # a pause this long inside one sung line means Whisper put some of its words in the wrong place


def _pace(lines: list[LyricLine]) -> float:
    """Typical seconds per sung word in this song, from the words Whisper timed believably."""
    lengths = sorted(w.end - w.start for l in lines for w in l.words if 0.1 < w.end - w.start < 1.5)
    return lengths[len(lengths) // 2] if lengths else 0.4


def repair(lines: list[LyricLine]) -> list[LyricLine]:
    """Fix Whisper's usual slips so the karaoke doesn't jump:

    - a word (or a few) seconds away from the rest of its line, often stretched across an instrumental part or
      pinned to the end of the song: the biggest group of believably timed words stays, the strays move next to it.
    - several words sharing one start time: spread them out up to the next word.
    """
    pace = _pace(lines)
    out: list[LyricLine] = []
    for li, line in enumerate(lines):
        words = [Word(w.text, w.start, w.end) for w in line.words]
        prev_end = out[-1].end if out else 0.0
        next_start = lines[li + 1].start if li + 1 < len(lines) else float("inf")

        runs = [[0]]
        for k in range(1, len(words)):
            if words[k].start - words[k - 1].end < GAP_SEC:
                runs[-1].append(k)
            else:
                runs.append([k])
        if len(runs) > 1:
            best = max(runs, key=lambda r: sum(words[k].end - words[k].start > 0.1 for k in r))
            a, b = best[0], best[-1]
            before = [w.text for w in words[:a]]
            after = [w.text for w in words[b + 1:]]
            kept = words[a:b + 1]
            if before:
                start = max(prev_end, kept[0].start - pace * len(before))
                kept = _weighted(before, start, max(kept[0].start, start + 0.05)) + kept
            if after:
                end = min(next_start, kept[-1].end + pace * len(after))
                kept = kept + _weighted(after, kept[-1].end, max(end, kept[-1].end + 0.05))
            words = kept

        k = 0
        while k < len(words):
            m = k
            while m + 1 < len(words) and words[m + 1].start - words[k].start < 0.05:
                m += 1
            if m > k:
                until = words[m + 1].start if m + 1 < len(words) else max(words[m].end, words[k].start + pace * (m - k + 1))
                words[k:m + 1] = _weighted([w.text for w in words[k:m + 1]], words[k].start, min(until, next_start))
            k = m + 1
        # a held note lasts a few seconds; a word "sung" for longer was stretched over an instrumental part
        words = [Word(w.text, w.start, min(w.end, w.start + MAX_WORD_SEC)) for w in words]
        out.append(LyricLine(line.section, line.text, words[0].start, words[-1].end, words, line.check))
    return out


def align_lyrics(audio: Path, song: SongScript, lang: str, total: float, log=print,
                 isolate_vocals: bool = False, known: list[Word] | None = None) -> tuple[list[LyricLine], str]:
    """Best available timing for the lyrics; returns (lines, method) where method is 'exact' (from `known`, the
    word timings the song generator reported), 'whisper' or 'even'."""
    lines = _lines(song)
    if known and lines:
        found = known_timing(lines, known)
        if found:
            timed, weak = found
            log(f"      timed from the song's own word timings ({len(lines) - len(weak)}/{len(lines)} lines matched)")
            return _flag(repair(timed), weak, total), "exact"
        log("      the song's word timings don't match these lyrics (edited after composing?); listening instead")
    try:
        if isolate_vocals and demucs_available():
            log("      separating the vocals from the music first (Demucs)")
        return whisper_timing(audio, song, lang, isolate_vocals, total), "whisper"
    except ImportError:
        log("      stable-ts isn't installed, so lyrics are spaced evenly (Settings → AI features → Install AI add-on)")
    except Exception as e:  # a bad alignment shouldn't block the video
        log(f"      ! lyric alignment failed ({e.__class__.__name__}: {e}); spacing lyrics evenly")
    return even_timing(song, total), "even"


def save_lines(lines: list[LyricLine], path: Path) -> None:
    path.write_text(json.dumps([asdict(l) for l in lines], ensure_ascii=False, indent=2), encoding="utf-8")


def lines_from_json(data: list[dict]) -> list[LyricLine]:
    out = []
    for d in data:
        words = [Word(str(w["text"]), float(w["start"]), float(w["end"])) for w in d.get("words", [])]
        if not words:
            continue
        out.append(LyricLine(int(d.get("section", 0)), str(d.get("text") or " ".join(w.text for w in words)),
                             words[0].start, words[-1].end, words, bool(d.get("check", False))))
    return sorted(out, key=lambda l: l.start)


def load_lines(path: Path) -> list[LyricLine] | None:
    """Saved (possibly hand-corrected) timing, or None when there is none yet."""
    if not path.exists():
        return None
    return lines_from_json(json.loads(path.read_text(encoding="utf-8")))
