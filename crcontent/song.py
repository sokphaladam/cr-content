"""Turn a SongScript into audio: a full mix plus (optionally) vocal and instrumental stems.

Backends share one small interface so another provider (or a local model) can be swapped in later.
"""
import json
import os
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

import requests

from .lyrics import SongScript
from .render import run

ELEVENLABS_API = "https://api.elevenlabs.io/v1"


@dataclass
class SongResult:
    mix: Path
    vocals: Path | None = None
    instrumental: Path | None = None
    song_id: str = ""


class SongBackend(Protocol):
    name: str

    def generate(self, song: SongScript, out_dir: Path, stems: bool = True) -> SongResult: ...


def elevenlabs_key() -> str:
    return os.getenv("ELEVENLABS_API_KEY", "").strip()


class ElevenLabsMusic:
    """ElevenLabs Music API: lyrics + per-section styles in, studio-quality song out."""
    name = "elevenlabs"

    def __init__(self, api_key: str | None = None, model: str = "music_v1",
                 output_format: str = "mp3_44100_128"):
        self.api_key = api_key or elevenlabs_key()
        if not self.api_key:
            raise RuntimeError("ELEVENLABS_API_KEY is not set (add it to .env)")
        self.model = model
        self.output_format = output_format

    @staticmethod
    def composition_plan(song: SongScript) -> dict:
        """SongScript -> the music_v1 composition plan (global styles + timed sections with lyric lines)."""
        return {
            "positive_global_styles": [song.genre, song.mood, f"{song.bpm} bpm", song.vocal, *song.styles],
            "negative_global_styles": song.avoid,
            "sections": [
                {
                    "section_name": s.name[:100],
                    "positive_local_styles": s.styles,
                    "negative_local_styles": [],
                    "duration_ms": s.seconds * 1000,
                    "lines": [line.strip()[:200] for line in s.lyrics if line.strip()][:30],
                }
                for s in song.sections
            ],
        }

    def _post(self, path: str, **kwargs) -> requests.Response:
        r = requests.post(f"{ELEVENLABS_API}{path}", headers={"xi-api-key": self.api_key},
                          params={"output_format": self.output_format}, timeout=600, **kwargs)
        if not r.ok:
            try:
                detail = r.json().get("detail", r.text)
                if isinstance(detail, dict):
                    detail = detail.get("message") or json.dumps(detail)
            except ValueError:
                detail = r.text
            detail = " ".join(str(detail).split())[:1000]
            raise RuntimeError(f"ElevenLabs {path} failed ({r.status_code}): {detail}")
        return r

    def compose(self, song: SongScript, out: Path) -> str:
        """Write the full song to `out`; returns the song id ElevenLabs reports (or "")."""
        r = self._post("/music", json={
            "composition_plan": self.composition_plan(song),
            "model_id": self.model,
            "respect_sections_durations": True,
        })
        out.write_bytes(r.content)
        return next((v for k, v in r.headers.items() if "song" in k.lower() and "id" in k.lower()), "")

    def separate(self, mix: Path, out_dir: Path) -> tuple[Path | None, Path | None]:
        """Split `mix` into stems; returns (vocals, instrumental). Non-vocal stems are mixed into one track."""
        with open(mix, "rb") as f:
            r = self._post("/music/stem-separation", files={"file": (mix.name, f, "audio/mpeg")})
        out_dir.mkdir(parents=True, exist_ok=True)
        archive = out_dir / "stems.zip"
        archive.write_bytes(r.content)
        with zipfile.ZipFile(archive) as z:
            z.extractall(out_dir)
        archive.unlink()

        stems = sorted(p for p in out_dir.rglob("*") if p.is_file())
        vocals = next((p for p in stems if "vocal" in p.stem.lower()), None)
        others = [p for p in stems if p != vocals]
        if not others:
            return vocals, None
        if len(others) == 1:
            return vocals, others[0]
        instrumental = out_dir.parent / "instrumental.mp3"
        inputs = [arg for p in others for arg in ("-i", str(p))]
        run(["ffmpeg", "-y", "-hide_banner", *inputs,
             "-filter_complex", f"amix=inputs={len(others)}:normalize=0", "-b:a", "192k", str(instrumental)])
        return vocals, instrumental

    def generate(self, song: SongScript, out_dir: Path, stems: bool = True) -> SongResult:
        out_dir.mkdir(parents=True, exist_ok=True)
        mix = out_dir / "song.mp3"
        song_id = self.compose(song, mix)
        vocals = instrumental = None
        if stems:
            vocals, instrumental = self.separate(mix, out_dir / "stems")
        return SongResult(mix, vocals, instrumental, song_id)


BACKENDS: dict[str, type] = {"elevenlabs": ElevenLabsMusic}


def get_backend(name: str = "elevenlabs") -> SongBackend:
    if name not in BACKENDS:
        raise ValueError(f"unknown song backend {name!r} (have: {', '.join(BACKENDS)})")
    return BACKENDS[name]()
