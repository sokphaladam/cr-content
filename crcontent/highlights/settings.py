"""Smart Highlights settings: score weights, clip lengths and switches, kept in <data folder>/highlights.json.

The file is written with the defaults the first time it's needed; edit it to tune the ranking. Keys missing from it
fall back to the defaults below, so older files keep working when new settings are added.
"""
import copy
import json

from ..config import ROOT

PATH = ROOT / "highlights.json"

DEFAULTS: dict = {
    "clip": {
        "min_seconds": 15,
        "max_seconds": 30,
        "ideal_seconds": 22,     # lengths near this get a small bonus (long enough to land the hook, short to loop)
        "count": 3,              # clips rendered
        "tail_seconds": 0.6,     # music kept after the last sung word (ends on the next beat after it)
        "repeat_penalty": 0.15,  # mark-down for a clip singing the same lines as a better one (the chorus again)
    },
    # how much each analysis counts in a clip's score (they're normalised, so only the ratios matter)
    "weights": {"structure": 0.35, "lyrics": 0.30, "visual": 0.15, "hook": 0.20},
    "structure": {
        "parts": {"section": 0.50, "energy": 0.25, "repetition": 0.15, "drop": 0.10},
        # how attractive each kind of section is as a short
        "labels": {"chorus": 1.0, "hook": 1.0, "drop": 0.9, "post-chorus": 0.8, "pre-chorus": 0.6, "bridge": 0.5,
                   "verse": 0.35, "instrumental": 0.25, "intro": 0.1, "outro": 0.1},
    },
    "lyrics": {"parts": {"repeat": 0.55, "title": 0.30, "density": 0.15}},
    "visual": {"parts": {"motion": 0.25, "sharpness": 0.25, "colour": 0.20, "faces": 0.15, "cuts": 0.15},
               "samples_per_second": 2},
    "hook": {"window_seconds": 2.0, "parts": {"line": 0.6, "drop": 0.4}},
    "ai_judge": {"enabled": True, "candidates": 5, "frames": 4},
    "covers": {"per_clip": 3, "samples": 24},
    "render": {"encoder": "auto", "source": "auto"},  # encoder: auto | nvenc | cpu; source: auto | clean | video
}


def _merge(base: dict, over: dict) -> dict:
    out = copy.deepcopy(base)
    for k, v in over.items():
        out[k] = _merge(out[k], v) if isinstance(v, dict) and isinstance(out.get(k), dict) else v
    return out


def load() -> dict:
    """The settings: the user's file over the defaults (the file is created with the defaults if missing)."""
    if not PATH.exists():
        PATH.write_text(json.dumps(DEFAULTS, indent=2), encoding="utf-8")
        return copy.deepcopy(DEFAULTS)
    try:
        return _merge(DEFAULTS, json.loads(PATH.read_text(encoding="utf-8")))
    except (ValueError, OSError) as e:
        print(f"  ! {PATH.name} couldn't be read ({e}); using the default weights")
        return copy.deepcopy(DEFAULTS)


def blend(parts: dict[str, float], weights: dict[str, float]) -> float:
    """Weighted mean of the named 0..1 parts (weights normalised over the parts present)."""
    total = sum(w for k, w in weights.items() if k in parts)
    return sum(parts[k] * w for k, w in weights.items() if k in parts) / total if total else 0.0
