"""The pictures of a lyric video: one per sung section, shown behind its lyrics, kept in <song>/pictures.json.

pictures.json = {"cover_prompt", "meaning", "slots": [{"id", "tag", "kind", "start", "end", "lyrics", "prompt", "file"}]}, times in song
seconds, files in <song>/pictures/. The cover is the song's background picture (background.png/.jpg: thumbnail and
fallback). A slot without a file shows the cover (or the drawn city). prompts() writes the suggested prompts.
"""
import json
import re
from pathlib import Path
from types import SimpleNamespace

from . import analyze, songjson

NAME = "pictures.json"
DIR = "pictures"
FADE = 1.0   # seconds a picture dissolves into the next
KIND_FEEL = {
    "chorus": "the brightest moment of the song: wider, more colour, glowing neon, a sense of release",
    "pre-chorus": "rising tension, light building, the camera leaning in",
    "verse": "calmer and quieter, intimate details, softer light",
    "bridge": "a turn: warmer amber light, a change of place or time of day",
    "outro": "fading, the light settling, empty space",
}


# The camera move over a section's picture (the 2D ones of crcontent/fx.py MOTIONS: this video draws them itself).
# "" = the default slow drift. Each slot carries its suggested move; one you pick stays ("motion_edited").
MOTIONS = {
    "": "Slow drift",
    "push_in": "Push in",
    "pull_out": "Pull out",
    "pan_left": "Pan left",
    "pan_right": "Pan right",
    "tilt_up": "Tilt up",
    "tilt_down": "Tilt down",
    "breathe": "Breathe",
    "still": "Hold",
}
KIND_MOTIONS = {   # what suits each part of a song, in the order they are used when it comes round again
    "intro": ("push_in", "tilt_down"),
    "verse": ("push_in", "pan_right", "pan_left", "tilt_up"),
    "pre-chorus": ("push_in",),
    "chorus": ("pull_out", "breathe"),
    "bridge": ("pan_left", "tilt_up", "pan_right"),
    "outro": ("pull_out", "tilt_up"),
}


def suggest_motion(kind: str, nth: int = 0) -> str:
    """The camera move that suits a section: pushing in as tension builds, pulling out for a chorus's release, panning
    for a bridge; the same kind sung again gets the next move on its list, so neighbours differ."""
    options = KIND_MOTIONS.get((kind or "").lower(), ("push_in", "pan_right", "pull_out"))
    return options[nth % len(options)]


def path(folder: Path) -> Path:
    return Path(folder) / NAME


def load(folder: Path) -> dict:
    try:
        plan = json.loads(path(folder).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"slots": []}
    plan.setdefault("slots", [])
    return plan


def save(folder: Path, plan: dict) -> None:
    path(folder).write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")


def _lyrics_between(lines: list[dict], start: float, end: float) -> str:
    return " / ".join(ln["text"] for ln in lines if start - 0.01 <= ln["start"] < end)


# The channel's look, after the big lofi channels: calm illustrated scenes with one clear subject, a palette chosen
# for the mood, soft glowing light and small cosy details. Added to every picture prompt (the drawing tool adds the
# medium itself, so this names no art style).
LOOK = ("one clear focal subject, seen from behind or in profile; calm slice-of-life scene; a limited palette "
        "that fits the mood; soft glowing light (a lamp, sunset or moonlight); a few small cosy details such as "
        "plants, books or a cat")


def prompt_for(data: dict, kind: str, lyrics: str) -> str:
    """A text-to-image prompt for one section: the song's place and mood (pipeline.suggest_background_prompt, no
    Gemini), what this part of the song feels like, and no text in the picture."""
    from crcontent.pipeline import suggest_background_prompt

    song = SimpleNamespace(title=data.get("title") or "",
                           mood=f"{data.get('mood_phrase') or ''}, {data.get('genre') or ''}")
    base = suggest_background_prompt(song, data.get("scene_theme") or "", lyrics)
    base = base.replace("Cinematic background video for a lyric video", "Cinematic still frame for a lyric video, 16:9")
    base = base.rsplit(". seamless loop", 1)[0]   # a still needs no loop or length
    base = re.sub(r";\s*[^;.]*camera[^;.]*", "", base)   # ...nor a camera move
    feel = KIND_FEEL.get(kind)
    base = f"{base}. {feel}" if feel else base
    return f"{base}. {LOOK}"


SYSTEM = """You write text-to-image prompts for the pictures behind a lyric video. Read the whole lyrics and work out
what the song is really about: the story, who is singing to whom, the feeling, and its central image or metaphor.
Then write prompts that SHOW that meaning with concrete things (a place, an object, light, weather, time of day), never
a generic mood or "abstract haze". Each prompt is one scene in 25-55 words: subject, setting, light, colour palette,
composition. Rules: all pictures belong to one film (same world, palette and look, so they dissolve into each other
well); the sections follow the song's story from first to last; no text, letters, logos or readable signs; no
close-up faces and no crowds (image models draw them badly), a small distant figure or silhouette is fine; leave calm
empty space in the middle of the frame for the lyrics; 16:9. House look, in every prompt: a calm, cosy
slice-of-life scene with ONE clear focal subject (a figure seen from behind or in profile, or one strong object),
a limited palette chosen for the mood (warm amber and orange for nostalgic or cosy, deep blue and indigo with stars
for night, pastel pink and lavender for hopeful, fresh green and yellow for summer), soft glowing light (a lamp,
sunset, moonlight), and a few small cosy details (plants, books, a cat, a window). Use one recurring character or
motif in all the pictures so the film feels like one world. Do not name an art medium (the drawing tool adds the look)
unless the creator's scene idea does. If the creator gave a scene idea, it is their direction: keep its world,
characters and colours in every prompt, and still carry the song's central metaphor inside that setting (a river
song about orbiting someone: circling ripples around a reflected star, a lantern going round a bridge). Write the prompts in English whatever the lyrics' language."""
SCHEMA = {
    "type": "object",
    "properties": {
        "meaning": {"type": "string"},
        "cover": {"type": "string"},
        "sections": {"type": "array", "items": {
            "type": "object", "properties": {"id": {"type": "string"}, "prompt": {"type": "string"}},
            "required": ["id", "prompt"], "additionalProperties": False}},
    },
    "required": ["meaning", "cover", "sections"],
    "additionalProperties": False,
}


def ai_prompts(data: dict, slots: list[dict], lyrics: str, log=print) -> dict | None:
    """{meaning, cover, sections: {id: prompt}} written by Gemini from the lyrics' meaning, or None without it (no key,
    offline, declined): the keyword prompts stand."""
    from crcontent.config import LLM_MODEL
    from crcontent.script import make_client

    parts = "\n".join(f"{s['id']} ({s['tag']}, {s['start']:.0f}-{s['end']:.0f}s): {s['lyrics']}" for s in slots)
    task = (f"Song: {data.get('title')!r} ({data.get('mood_phrase') or ''} {data.get('genre') or ''}).\n"
            + (f"The creator's scene idea: {data['scene_theme']}\n" if data.get("scene_theme") else "")
            + f"\nFull lyrics:\n{lyrics}\n\nSections, in order:\n{parts}\n\n"
              "Write: meaning (one sentence: what the song is about), cover (the one picture that sums up the whole "
              "song, used behind every lyric), and a prompt for each section id (its own moment of the story).")
    try:
        response = make_client().beta.messages.create(
            model=LLM_MODEL, max_tokens=4000, system=SYSTEM,
            output_config={"effort": "medium", "format": {"type": "json_schema", "schema": SCHEMA}},
            messages=[{"role": "user", "content": task}])
        if response.stop_reason == "refusal":
            return None
        out = json.loads(next(b.text for b in response.content if b.type == "text"))
    except Exception as e:
        log(f"      ! picture prompts without Gemini ({type(e).__name__}: {str(e)[:100]})")
        return None
    return {"meaning": out["meaning"].strip(), "cover": out["cover"].strip(),
            "sections": {x["id"]: x["prompt"].strip() for x in out["sections"] if x["prompt"].strip()}}


def suggest(folder: Path, data: dict, keep: dict | None = None, ai: bool = False) -> dict:
    """A slot per sung section with a suggested prompt (`ai`: written by Gemini from what the lyrics mean, else from
    keywords); `keep` (an earlier plan) keeps the pictures, and the prompts you edited."""
    lines = analyze.parse_lrc((Path(folder) / "lyrics.lrc").read_text(encoding="utf-8"))
    old = {s["id"]: s for s in (keep or {}).get("slots", [])}
    slots, used = [], {}
    for n, sec in enumerate(data.get("sections", [])):
        if "start" not in sec or "end" not in sec:
            continue
        sid = f"s{n + 1}"
        lyrics = _lyrics_between(lines, sec["start"], sec["end"])
        slot = {"id": sid, "tag": sec.get("tag", ""), "kind": sec.get("kind", ""), "start": sec["start"],
                "end": sec["end"], "lyrics": lyrics, "prompt": prompt_for(data, sec.get("kind", ""), lyrics), "file": "",
                "motion": suggest_motion(sec.get("kind", ""), used.get(sec.get("kind", ""), 0))}
        used[sec.get("kind", "")] = used.get(sec.get("kind", ""), 0) + 1
        slots.append(slot)
    whole = " ".join(s["lyrics"] for s in slots)[:600]
    plan = {"slots": slots, "cover_prompt": prompt_for(data, "", whole), "meaning": ""}
    if ai and slots:
        written = ai_prompts(data, slots, "\n".join(ln["text"] for ln in lines))
        if written:
            plan.update(cover_prompt=written["cover"], meaning=written["meaning"])
            for slot in slots:
                if written["sections"].get(slot["id"]):
                    slot["prompt"] = written["sections"][slot["id"]]
    for slot in slots:   # your own words and pictures stay
        was = old.get(slot["id"])
        if was and was.get("tag") == slot["tag"]:
            slot["file"] = was.get("file", "")
            if was.get("motion_edited") and was.get("motion") in MOTIONS:
                slot.update(motion=was["motion"], motion_edited=True)
            if was.get("edited"):
                slot.update(prompt=was["prompt"], edited=True)
    if keep and keep.get("cover_edited"):
        plan.update(cover_prompt=keep["cover_prompt"], cover_edited=True)
    return plan


def with_motions(plan: dict) -> dict:
    """The plan with a camera move on every slot (plans made before moves existed get the suggestion; not saved)."""
    used = {}
    for s in sorted(plan.get("slots", []), key=lambda s: s["start"]):
        n = used.get(s.get("kind", ""), 0)
        used[s.get("kind", "")] = n + 1
        if s.get("motion") not in MOTIONS:
            s["motion"] = suggest_motion(s.get("kind", ""), n)
    return plan


def spans(folder: Path, duration: float) -> list[tuple[float, float, Path, str]]:
    """(start, end, picture, camera move) in song seconds for the slots that have a picture: each holds until the next
    section begins, so a gap between sections doesn't flash the cover."""
    slots = sorted(with_motions(load(folder))["slots"], key=lambda s: s["start"])
    out = []
    for k, s in enumerate(slots):
        file = Path(folder) / DIR / s["file"] if s.get("file") else None
        if file and file.exists():
            out.append((float(s["start"]), float(slots[k + 1]["start"]) if k + 1 < len(slots) else duration, file,
                        s["motion"]))
    return out


def timeline(folder: Path, duration: float) -> list[tuple[float, float, Path]]:
    """(start, end, picture) of `spans`, without the camera move."""
    return [(a, b, f) for a, b, f, _ in spans(folder, duration)]


__all__ = ["load", "save", "suggest", "timeline", "spans", "with_motions", "suggest_motion", "MOTIONS", "prompt_for", "path", "FADE", "DIR", "songjson"]
