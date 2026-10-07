"""Free neural voiceover via Microsoft Edge TTS, with per-word timings for captions."""
import asyncio
from dataclasses import dataclass
from pathlib import Path

import edge_tts

TICKS_PER_SEC = 10_000_000  # Edge TTS offsets are in 100ns units


@dataclass
class Word:
    text: str
    start: float  # seconds, relative to the start of its audio file
    end: float


async def _synthesize(text: str, voice: str, out_path: Path, rate: str) -> list[Word]:
    communicate = edge_tts.Communicate(text, voice, rate=rate, boundary="WordBoundary")
    words: list[Word] = []
    with open(out_path, "wb") as f:
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                f.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                start = chunk["offset"] / TICKS_PER_SEC
                words.append(Word(chunk["text"], start, start + chunk["duration"] / TICKS_PER_SEC))
    if not words:
        raise RuntimeError(f"TTS returned no word timings for voice {voice}")
    return words


def synthesize(text: str, voice: str, out_path: Path, rate: str = "+0%") -> list[Word]:
    """Write an mp3 to out_path and return the spoken words with timings."""
    return asyncio.run(_synthesize(text, voice, out_path, rate))


def list_voices(prefix: str = "") -> list[str]:
    voices = asyncio.run(edge_tts.list_voices())
    return sorted(v["ShortName"] for v in voices if v["ShortName"].startswith(prefix))
