"""How well a clip shows a beat's planned shot, 0-10, judged by Gemini on three frames of the part that will be shown.

Not only "is the animal there": the planned action and its key objects (water, splash, towel, sand) count. A clip
without the key objects can't score above GENERIC_MAX, whatever Gemini says, so a generic shot of the animal never
passes for a specific beat. The same look answers the hook rules too: does the animal move, is there a logo, text or
an intro, and where is its head (the 9:16 crop is framed on it). Cached next to the clip, per shot and window.
"""
import base64
import hashlib
import json
import subprocess
from pathlib import Path

from ..config import LLM_MODEL
from ..visuals import IMAGE_EXTS

PASS = 7          # a clip that shows the planned shot
GENERIC_MAX = 5   # the most a clip without the shot's key objects can score
SCHEMA = {
    "type": "object",
    "properties": {
        "score": {"type": "integer"},
        "objects_seen": {"type": "array", "items": {"type": "string"}},
        "animal": {"type": "boolean"},
        "in_motion": {"type": "boolean"},
        "logo_or_text": {"type": "boolean"},
        "intro_or_title": {"type": "boolean"},
        "x": {"type": "number"},
        "y": {"type": "number"},
        "seen": {"type": "string"},
        "problem": {"type": "string"},
    },
    "required": ["score", "objects_seen", "animal", "in_motion", "logo_or_text", "intro_or_title", "x", "y", "seen",
                 "problem"],
    "additionalProperties": False,
}


def frames(path: Path, start: float, length: float) -> list[str]:
    """Three jpgs (base64) across the window that will be shown: start, middle, end (one for a photo)."""
    times = [0.0] if path.suffix.lower() in IMAGE_EXTS else \
        [start + 0.15, start + length / 2, start + max(length - 0.15, 0.3)]
    out = []
    for t in times:
        seek = [] if path.suffix.lower() in IMAGE_EXTS else ["-ss", f"{t:.2f}"]
        raw = subprocess.run(["ffmpeg", "-v", "error", *seek, "-i", str(path), "-frames:v", "1", "-vf", "scale=-2:480",
                              "-f", "image2pipe", "-vcodec", "mjpeg", "-"], stdin=subprocess.DEVNULL,
                             capture_output=True).stdout
        if raw:
            out.append(base64.b64encode(raw).decode())
    return out


def capped(data: dict, key_objects: list[str]) -> dict:
    """GENERIC_MAX for a clip missing any of the key objects; 0 when the animal isn't there."""
    seen = " ".join(data.get("objects_seen", [])).lower()
    missing = [o for o in key_objects if o.lower() not in seen]
    score = max(0, min(int(data.get("score", 0)), 10))
    if not data.get("animal", True):
        score = 0
    elif missing:
        score = min(score, GENERIC_MAX)
    return {**data, "score": score, "missing": missing}


def unchecked() -> dict:
    """The result for a clip Gemini was not asked about (shorts.json footage.check): it passes, centred."""
    return {"score": PASS, "objects_seen": [], "missing": [], "animal": True, "in_motion": None,
            "logo_or_text": False, "intro_or_title": False, "x": 0.5, "y": 0.5,
            "seen": "(not checked)", "problem": ""}


def check(path: Path, animal: str, shot: str, key_objects: list[str], start: float, length: float) -> dict:
    """{score, objects_seen, missing, animal, in_motion, logo_or_text, intro_or_title, x, y, seen, problem}."""
    key = hashlib.sha1(f"{animal}|{shot}|{','.join(key_objects)}|{start:.2f}|{length:.2f}".encode()).hexdigest()[:12]
    note = path.with_name(f"{path.stem}.match-{key}.json")
    if note.exists():
        return capped(json.loads(note.read_text(encoding="utf-8")), key_objects)
    from ..script import make_client

    content = [{"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": d}}
               for d in frames(path, start, length)]
    content.append({"type": "text", "text": (
        f"Frames from a stock clip (start, middle, end of the {length:.1f}s that would be shown) for one beat of a "
        f"YouTube Short about a {animal}.\nThe planned shot: {shot}\n"
        + (f"Key objects that must be visible: {', '.join(key_objects)}\n" if key_objects else "")
        + "score 0-10, how well these frames show the PLANNED SHOT (not just the animal): 9-10 = the planned action "
          "with its key objects; 7-8 = the animal with the key objects, a different but fitting action; 4-5 = the "
          "right animal but none of the planned action or key objects; 0 = a different animal or no animal. "
          "objects_seen: the things in frame besides the animal, in plain words; when a key object is there, use its "
          "word exactly as listed above (say \"tap\" for a faucet if \"tap\" is listed). "
          "animal: is it the right animal (not a big cat, not another species)? in_motion: does the animal itself "
          "move between the frames (not only the camera)? logo_or_text: any logo, watermark or text overlay? "
          "intro_or_title: a title card, intro, fade or black frame? x, y: the animal's head in the middle frame, as "
          "fractions 0..1. seen: what the clip shows, in a few words. problem: what's missing for the planned shot, "
          "or \"\".")})
    response = make_client().beta.messages.create(
        model=LLM_MODEL,
        max_tokens=800,
        output_config={"effort": "low", "format": {"type": "json_schema", "schema": SCHEMA}},
        messages=[{"role": "user", "content": content}],
    )
    data = json.loads(next(b.text for b in response.content if b.type == "text"))
    data["x"], data["y"] = (min(max(float(data[k]), 0.0), 1.0) for k in ("x", "y"))
    note.write_text(json.dumps(data), encoding="utf-8")
    return capped(data, key_objects)
