"""Voiceover with per-word timings for captions: free Microsoft Edge TTS, or Gemini TTS (Google AI Studio, voices
named "en-US-<Name>-Gemini"), which sounds more human but reports no timings, so its audio is force-aligned."""
import asyncio
import base64
import os
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

import aiohttp
import requests
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


GEMINI_TTS = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
GEMINI_VOICES = ("Kore", "Puck", "Charon", "Aoede", "Fenrir", "Leda", "Orus", "Zephyr")
# Gemini TTS takes its delivery from plain words in front of the text
GEMINI_STYLE = "Read this aloud like a native speaker casually telling a friend something interesting, natural and warm:"


def is_voice(voice: str) -> bool:
    return bool(voice) and ("Neural" in voice or voice.endswith("-Gemini"))


def _gemini(text: str, voice: str, out_path: Path, rate: str) -> list[Word]:
    key = os.getenv("GEMINI_API_KEY", "").strip()
    if not key:
        raise ValueError("Gemini voices need GEMINI_API_KEY (add it in Settings).")
    model = os.getenv("GEMINI_TTS_MODEL", "gemini-2.5-flash-preview-tts")
    r = requests.post(GEMINI_TTS.format(model=model), headers={"x-goog-api-key": key}, timeout=120, json={
        "contents": [{"parts": [{"text": f"{GEMINI_STYLE}\n{text}"}]}],
        "generationConfig": {"responseModalities": ["AUDIO"], "speechConfig": {
            "voiceConfig": {"prebuiltVoiceConfig": {"voiceName": voice.split("-")[2]}}}}})
    if r.status_code != 200:  # 429 when the free tier's per-minute limit is hit: synthesize() retries
        raise RuntimeError(f"Gemini TTS failed ({r.status_code}): {r.text[:300]}")
    pcm = base64.b64decode(r.json()["candidates"][0]["content"]["parts"][0]["inlineData"]["data"])
    tempo = 1 + int(rate.strip("%") or 0) / 100  # Edge-style "+5%" as a tempo change
    subprocess.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-f", "s16le", "-ar", "24000", "-ac", "1",
                    "-i", "-", "-af", f"atempo={tempo:.3f}", "-f", "mp3", "-b:a", "128k", str(out_path)],
                   input=pcm, check=True)
    from .align import _align, _weighted
    from .render import duration

    try:  # Gemini reports no word timings, so align the words to its audio
        return _align(out_path, [(0, " ".join(text.split()))], voice.split("-")[0], {})[0].words
    except Exception as e:  # Whisper missing or alignment failed: spread the words over the audio
        print(f"  ! Gemini voice alignment failed ({type(e).__name__}); caption times are estimated")
        return _weighted(text.split(), 0.1, max(duration(out_path) - 0.1, 0.2))


def synthesize(text: str, voice: str, out_path: Path, rate: str = "+0%") -> list[Word]:
    """Write an mp3 to out_path and return the spoken words with timings."""
    gemini = voice.endswith("-Gemini")
    for attempt in range(1, ATTEMPTS + 1):
        try:
            if gemini:
                return _gemini(text, voice, out_path, rate)
            return asyncio.run(asyncio.wait_for(_synthesize(text, voice, out_path, rate), ATTEMPT_TIMEOUT_SEC))
        except (edge_tts.exceptions.EdgeTTSException, aiohttp.ClientError, RuntimeError, OSError, asyncio.TimeoutError):
            if attempt == ATTEMPTS:
                raise
            time.sleep(attempt * (8 if gemini else 1.5))  # Gemini's free tier limits requests per minute


def list_voices(prefix: str = "") -> list[str]:
    voices = asyncio.run(edge_tts.list_voices())
    return sorted(v["ShortName"] for v in voices if v["ShortName"].startswith(prefix))
