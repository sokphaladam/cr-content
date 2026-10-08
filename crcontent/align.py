"""Lyric timing: when each sung word starts and ends in the song, for karaoke captions.

Uses stable-ts (Whisper forced alignment) when it's installed: the lyrics are already known, so it only has to
line them up with the vocals. Without it, lines are spread evenly over their section, which is rough but usable.
"""
import json
import os
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


def section_spans(song: SongScript, total: float) -> list[tuple[float, float]]:
    """(start, end) of each section in the real audio. ElevenLabs keeps section lengths, so scale the plan to fit."""
    planned = max(song.seconds, 1)
    spans, t = [], 0.0
    for s in song.sections:
        length = s.seconds * total / planned
        spans.append((t, t + length))
        t += length
    return spans


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


def whisper_timing(audio: Path, song: SongScript, lang: str) -> list[LyricLine]:
    """Forced alignment with stable-ts. Raises ImportError when it isn't installed."""
    lines = _lines(song)
    if not lines:
        return []
    result = _load_model().align(str(audio), "\n".join(text for _, text in lines), language=lang,
                                 original_split=True)
    # Whisper may split tokens differently from our spaces (punctuation, Khmer clusters), so map by
    # character position: every non-space character of the lyrics gets the timing of the aligned word holding it.
    chars = [(w.start, w.end) for seg in result.segments for w in seg.words for c in w.word if not c.isspace()]
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


def align_lyrics(audio: Path, song: SongScript, lang: str, total: float, log=print) -> tuple[list[LyricLine], str]:
    """Best available timing for the lyrics; returns (lines, method) where method is 'whisper' or 'even'."""
    try:
        return whisper_timing(audio, song, lang), "whisper"
    except ImportError:
        log("      stable-ts isn't installed, so lyrics are spaced evenly (pip install -r requirements-music.txt)")
    except Exception as e:  # a bad alignment shouldn't block the video
        log(f"      ! lyric alignment failed ({e.__class__.__name__}: {e}); spacing lyrics evenly")
    return even_timing(song, total), "even"


def save_lines(lines: list[LyricLine], path: Path) -> None:
    path.write_text(json.dumps([asdict(l) for l in lines], ensure_ascii=False, indent=2), encoding="utf-8")
