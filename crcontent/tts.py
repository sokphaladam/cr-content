"""Free neural voiceover via Microsoft Edge TTS, with per-word timings for captions."""
import asyncio
import time
from dataclasses import dataclass
from pathlib import Path

import aiohttp
import edge_tts

TICKS_PER_SEC = 10_000_000  # Edge TTS offsets are in 100ns units
# Edge TTS is a free service that throttles bursts: a request now and then comes back empty (NoAudioReceived) or
# stalls mid-stream, mostly when several scenes are voiced at once. Such failures pass on a retry.
ATTEMPTS = 4
ATTEMPT_TIMEOUT_SEC = 45


@dataclass
class Word:
    text: str
    start: float  # seconds, relative to the start of its audio file
    end: float


async def _synthesize(text: str, voice: str, out_path: Path, rate: str) -> list[Word]:
    communicate = edge_tts.Communicate(text, voice, rate=rate, boundary="WordBoundary", receive_timeout=20)
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
    for attempt in range(1, ATTEMPTS + 1):
        try:
            return asyncio.run(asyncio.wait_for(_synthesize(text, voice, out_path, rate), ATTEMPT_TIMEOUT_SEC))
        except (edge_tts.exceptions.EdgeTTSException, aiohttp.ClientError, RuntimeError, OSError, asyncio.TimeoutError):
            if attempt == ATTEMPTS:
                raise
            time.sleep(attempt * 1.5)


def list_voices(prefix: str = "") -> list[str]:
    voices = asyncio.run(edge_tts.list_voices())
    return sorted(v["ShortName"] for v in voices if v["ShortName"].startswith(prefix))
