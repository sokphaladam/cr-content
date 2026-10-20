"""Voiceover per scene, from the engine set in longform.json: edge (free), elevenlabs, or files (your recordings).

Every engine gives the same thing back: one audio file per scene and its words with timings (for the captions and
the .srt). Edge and ElevenLabs report the timings themselves; a recording is force-aligned to the scene's voiceover
text (stable-ts, as for song lyrics), or spread over its length by word size when that isn't installed.
"""
import base64
import hashlib
import json
import os
import shutil
from dataclasses import dataclass, field
from pathlib import Path

import requests

from .. import voiceover
from ..config import CACHE_DIR, LANGS
from ..render import duration
from ..tts import Word
from .parse import Script

AUDIO_EXTS = (".wav", ".mp3", ".m4a", ".flac")
ELEVENLABS_TTS = "https://api.elevenlabs.io/v1/text-to-speech/{voice}/with-timestamps"
ELEVEN_CACHE = CACHE_DIR / "voiceover-elevenlabs"


@dataclass
class Voice:
    scene: int
    audio: str          # file name in the job's voice/ folder ("" = a scene with nothing to say)
    seconds: float      # the audio's length
    words: list[Word] = field(default_factory=list)
    timing: str = ""    # where the word times come from: engine | aligned | estimated

    def to_json(self) -> dict:
        return {**self.__dict__, "words": [w.__dict__ for w in self.words]}

    @classmethod
    def from_json(cls, data: dict) -> "Voice":
        return cls(**{**data, "words": [Word(**w) for w in data["words"]]})


def recording(media: Path, n: int) -> Path | None:
    """Your recording of scene `n`: <media>/scene-XX.wav (or .mp3 / .m4a / .flac; scene-7 works too)."""
    for stem in (f"scene-{n:02d}", f"scene-{n}"):
        for ext in AUDIO_EXTS:
            if (path := media / f"{stem}{ext}").is_file():
                return path
    return None


def punctuated(text: str, words: list[Word]) -> list[Word]:
    """The timed words as written in `text`: Edge TTS reports "brain" for '"brain"' and "stupid" for "stupid.", which
    leaves captions without punctuation (and sentence ends unknown). Each word takes the whole space-separated token
    of the text it falls in; words sharing a token ("multi" and "part" of "multi-part") become one."""
    spans, pos = [], 0
    for tok in text.split():
        at = text.index(tok, pos)
        spans.append((at, at + len(tok)))
        pos = at + len(tok)
    out: list[Word] = []
    last_token, cursor = -1, 0
    for w in words:
        at = text.lower().find(w.text.lower(), cursor) if w.text else -1
        if at < 0:  # not found as written (numbers read out, symbols): keep the engine's word
            out.append(Word(w.text, w.start, w.end))
            continue
        cursor = at + len(w.text)
        k = next(i for i, (a, b) in enumerate(spans) if a <= at < b)
        if k == last_token:
            out[-1] = Word(out[-1].text, out[-1].start, w.end)
            continue
        out.append(Word(text[spans[k][0]:spans[k][1]], w.start, w.end))
        last_token = k
    return out


def _edge(text: str, lang: str, cfg: dict) -> tuple[Path, list[Word]]:
    edge = cfg["voice"]["edge"]
    return voiceover.scene_voice(text, edge.get(lang) or LANGS[lang].voices[0], edge.get("rate", "+0%"))


def _words_from_chars(chars: list[str], starts: list[float], ends: list[float]) -> list[Word]:
    """ElevenLabs times each character; a word runs from its first character's start to its last one's end."""
    words, cur, t0, t1 = [], "", 0.0, 0.0
    for c, s, e in zip(chars, starts, ends):
        if c.isspace():
            if cur:
                words.append(Word(cur, t0, t1))
            cur = ""
            continue
        if not cur:
            t0 = s
        cur, t1 = cur + c, e
    if cur:
        words.append(Word(cur, t0, t1))
    return words


def _elevenlabs(text: str, cfg: dict) -> tuple[Path, list[Word]]:
    key = os.getenv("ELEVENLABS_API_KEY", "").strip()
    if not key:
        raise RuntimeError("The voice engine is elevenlabs but ELEVENLABS_API_KEY isn't set (add it in Settings).")
    el = cfg["voice"]["elevenlabs"]
    name = hashlib.sha1(f"{el['voice_id']}|{el['model']}|{text}".encode()).hexdigest()[:20]
    mp3, words_file = ELEVEN_CACHE / f"{name}.mp3", ELEVEN_CACHE / f"{name}.json"
    if mp3.exists() and words_file.exists():
        return mp3, [Word(**w) for w in json.loads(words_file.read_text(encoding="utf-8"))]
    r = requests.post(ELEVENLABS_TTS.format(voice=el["voice_id"]), params={"output_format": "mp3_44100_128"},
                      headers={"xi-api-key": key}, json={"text": text, "model_id": el["model"]}, timeout=120)
    if r.status_code != 200:
        raise RuntimeError(f"ElevenLabs voice failed ({r.status_code}): {r.text[:300]}")
    data = r.json()
    align = data.get("alignment") or data.get("normalized_alignment") or {}
    words = _words_from_chars(align.get("characters", []), align.get("character_start_times_seconds", []),
                              align.get("character_end_times_seconds", []))
    ELEVEN_CACHE.mkdir(parents=True, exist_ok=True)
    mp3.write_bytes(base64.b64decode(data["audio_base64"]))
    words_file.write_text(json.dumps([w.__dict__ for w in words]), encoding="utf-8")
    return mp3, words


def _recorded(path: Path, text: str, lang: str, seconds: float, log) -> tuple[list[Word], str]:
    """Word timings for your recording: forced alignment to its text, else spread by word length."""
    from ..align import _weighted

    try:
        from ..align import _align

        line = _align(path, [(0, " ".join(text.split()))], lang, {})[0]
        return line.words, "aligned"
    except ImportError:
        pass
    except Exception as e:
        log(f"      ! couldn't align {path.name} ({type(e).__name__}); caption times are estimated")
    tokens = text.split()
    return _weighted(tokens, min(0.15, seconds * 0.05), max(seconds - 0.15, 0.1)), "estimated"


def make_voices(script: Script, media: Path, out: Path, cfg: dict, log=print) -> list[Voice]:
    """One Voice per scene, its audio copied into `out` (the job's voice/ folder)."""
    engine = cfg["voice"]["engine"]
    if engine not in ("edge", "elevenlabs", "files"):
        raise ValueError(f"Unknown voice engine {engine!r} in longform.json (edge, elevenlabs or files).")
    out.mkdir(parents=True, exist_ok=True)
    voices, missing = [], []
    for scene in script.scenes:
        text = scene.voiceover.strip()
        own = recording(media, scene.n)
        if engine == "files" and not own and text:
            missing.append(scene.n)
            continue
        if not text and not own:
            voices.append(Voice(scene.n, "", 0.0))
            continue
        if own:  # your recording always wins, whatever the engine
            name = f"scene-{scene.n:02d}{own.suffix.lower()}"
            shutil.copy(own, out / name)
            seconds = duration(out / name)
            words, timing = _recorded(out / name, text, script.lang, seconds, log) if text else ([], "")
        else:
            src, words = _elevenlabs(text, cfg) if engine == "elevenlabs" else _edge(text, script.lang, cfg)
            name = f"scene-{scene.n:02d}.mp3"
            shutil.copy(src, out / name)
            seconds, timing = duration(out / name), "engine"
            words = punctuated(text, voiceover.with_emoji(text, words))
        voices.append(Voice(scene.n, name, seconds, words, timing))
        log(f"      scene {scene.n:02d}: {seconds:5.1f}s {'(your recording)' if own else ''}".rstrip())
    if missing:
        raise RuntimeError(f"The voice engine is files, but there's no recording for scene(s) "
                           f"{', '.join(map(str, missing))} in {media} (scene-XX.wav).")
    return voices
