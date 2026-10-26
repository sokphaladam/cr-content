"""A Short's edit choices, kept in <job>/edit.json: the mood (colour grade), the caption look and the cut style.

Chosen on the pre-flight page's Edit panel and used by render.py; nothing here changes the checks, so a new choice
only asks for the approval again. preview() draws one frame of a beat the way the render will (grade + captions).
"""
import json
import subprocess
from pathlib import Path

from ..styles import LOOKS, look_filter
from . import captions

TRANSITIONS = {"cut": "Hard cut", "flash": "Flash on the cut", "dip": "Dip to black"}
DEFAULT = {"look": "", "caption": "classic", "transition": "cut", "graphics": []}
FLASH, DIP = 0.09, 0.1   # seconds


def options() -> dict:
    return {"look": {"": "Channel default", **{k: v["label"] for k, v in LOOKS.items()}},
            "caption": {k: v["label"] for k, v in captions.STYLES.items()},
            "transition": TRANSITIONS}


def graphics_names() -> dict:
    from . import graphics

    return graphics.NAMES


def load(job: Path, cfg: dict | None = None) -> dict:
    """The job's choices over the defaults (the look falls back to shorts.json render.look)."""
    out = dict(DEFAULT)
    if cfg:
        out["look"] = str(cfg["render"].get("look") or "")
    try:
        saved = json.loads((Path(job) / "edit.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        saved = {}
    for k, allowed in options().items():
        if saved.get(k) in allowed:
            out[k] = saved[k]
    if isinstance(saved.get("graphics"), list):
        out["graphics"] = [g for g in saved["graphics"] if g in graphics_names()]
    return out


def save(job: Path, choice: dict) -> dict:
    """Keep the valid parts of `choice`; unknown names raise ValueError."""
    job = Path(job)
    edit = load(job)
    for k, allowed in options().items():
        if k in choice:
            if choice[k] not in allowed:
                raise ValueError(f"Unknown {k}: {choice[k]!r}.")
            edit[k] = choice[k]
    if "graphics" in choice:
        if not isinstance(choice["graphics"], list) or any(g not in graphics_names() for g in choice["graphics"]):
            raise ValueError("Unknown motion graphic.")
        edit["graphics"] = list(dict.fromkeys(choice["graphics"]))
    (job / "edit.json").write_text(json.dumps(edit, indent=2), encoding="utf-8")
    return edit


# ---- the "Suggest edit" button: what fits this Short, from what it is about and how fast it moves
HABITAT = {   # words in the title / voiceover / animal -> the mood (look) that suits the place or the feeling
    "teal": ("ocean", "sea", "fish", "shark", "whale", "dolphin", "octopus", "squid", "reef", "underwater", "turtle",
             "jellyfish", "crab", "seal"),
    "ice": ("arctic", "polar", "penguin", "snow", "ice", "winter", "frozen", "cold", "antarctic"),
    "golden": ("savanna", "safari", "desert", "lion", "giraffe", "elephant", "sunrise", "sunset", "zebra", "camel",
               "golden", "meerkat"),
    "moody": ("night", "owl", "bat", "dark", "nocturnal", "raven", "crow", "wolf", "midnight", "shadow"),
    "pastel": ("baby", "puppy", "kitten", "cute", "tiny", "fluffy", "bunny", "rabbit", "duckling", "hamster", "panda"),
    "noir": ("deadly", "venom", "venomous", "poison", "predator", "scary", "danger", "kill", "snake", "spider"),
    "vibrant": ("parrot", "colorful", "colourful", "peacock", "butterfly", "frog", "rainbow", "tropical", "toucan",
                "chameleon", "flamingo"),
    "cinematic": ("fastest", "speed", "dive", "falcon", "eagle", "hunt", "cheetah", "strongest", "biggest", "largest"),
}
CALM = ("sleep", "relax", "gentle", "calm", "peace", "quiet", "slow", "soft", "cozy", "sloth", "koala")
DRAMA = ("deadly", "danger", "venom", "poison", "predator", "kill", "scary", "shocking", "terrifying", "never", "secret")
NIGHT = ("night", "owl", "bat", "dark", "midnight", "nocturnal", "neon", "glow", "firefly", "jellyfish")


def _hits(text: str, words: tuple[str, ...]) -> list[str]:
    import re

    return [w for w in words if re.search(rf"(?<!\w){re.escape(w)}(?!\w)", text)]


def suggest(job: Path) -> dict:
    """The mood, captions, cuts and motion graphics that fit this Short, from its subject and its pace:
    {look, caption, transition, graphics, reasons: {field: why}, summary}. Nothing is saved: the Edit panel fills in
    the suggestion for you to preview and keep."""
    from . import _load

    cfg, ep, tl, voices, entries, media = _load(Path(job))
    text = " ".join([ep.title, ep.animal or "", ep.animal_search or "", ep.hook_idea or "",
                     *[s.voiceover for s in ep.script.scenes]]).lower()
    lengths = [s.length for s in tl.slots]
    avg = sum(lengths) / max(len(lengths), 1)
    pace = "fast" if avg <= 2.6 else "calm" if avg >= 4.5 else "steady"
    bangs = text.count("!") + text.count("?")
    reasons: dict[str, str] = {}

    def best(table: dict[str, tuple[str, ...]]) -> tuple[str, list[str]]:
        scored = {k: _hits(text, w) for k, w in table.items()}
        k = max(scored, key=lambda x: len(scored[x]))
        return (k, scored[k]) if scored[k] else ("", [])

    look, why = best(HABITAT)
    if look:
        reasons["look"] = f"{', '.join(why[:2])} → {LOOKS[look]['label']}"
    else:
        look = "teal"
        reasons["look"] = "no strong setting in the script: a clean teal & orange grade flatters most animal footage"

    night = _hits(text, NIGHT)
    if night and look in ("moody", "noir"):
        caption, reasons["caption"] = "neon", f"{night[0]} / dark mood → Neon captions glow against it"
    elif pace == "fast" or bangs >= 4:
        caption, reasons["caption"] = "pop", f"{avg:.1f} s beats{' and lots of ! and ?' if bangs >= 4 else ''} → Pop captions keep up"
    elif pace == "calm" or _hits(text, CALM):
        caption, reasons["caption"] = "minimal", f"{'calm' if _hits(text, CALM) else 'slow'} pace → Minimal captions stay out of the way"
    else:
        caption, reasons["caption"] = "classic", f"a steady {avg:.1f} s per beat → Classic captions read best"

    drama = _hits(text, DRAMA)
    if pace == "fast":
        transition, reasons["transition"] = "flash", f"cuts every {avg:.1f} s → a flash on each cut gives them punch"
    elif drama:
        transition, reasons["transition"] = "dip", f"{drama[0]} → a dip to black adds weight to the cuts"
    else:
        transition, reasons["transition"] = "cut", "a steady pace → hard cuts look cleanest"

    # one kit, never a pile: the same thin shapes, only as many as the pace carries
    if pace == "fast":
        graphics = ["progress", "burst", "sweep"]
        reasons["graphics"] = "fast cuts → progress bar, a ring burst and a light sweep on each cut"
    elif pace == "calm":
        graphics = ["progress"]
        reasons["graphics"] = "a calm pace → just the progress bar"
    else:
        graphics = ["progress", "burst"] if len(lengths) >= 5 else ["progress", "brackets"]
        reasons["graphics"] = ("a steady pace → progress bar and a ring burst on the cuts" if len(lengths) >= 5
                               else "few beats → progress bar and a quiet inset frame")
    if tl.total < 12:
        graphics = [g for g in graphics if g != "progress"] or ["brackets"]
        reasons["graphics"] += " (too short for a progress bar)"

    summary = (f"{LOOKS[look]['label']} mood, {captions.STYLES[caption]['label']} captions, "
               f"{TRANSITIONS[transition].lower()}, {', '.join(graphics_names()[g].lower() for g in graphics)}")
    return {"look": look, "caption": caption, "transition": transition, "graphics": graphics, "reasons": reasons,
            "summary": summary, "pace": pace}


def cut_filter(boundaries: list[float], transition: str) -> str:
    """An ffmpeg filter chain for the cuts at `boundaries` (seconds): "" for a hard cut. Brightness is eased around
    each cut, so the picture's length and the voice sync don't change."""
    if transition == "flash":
        return ",".join(f"eq=brightness='0.55*max(0,1-(t-{b:.3f})/{FLASH})':eval=frame:"
                        f"enable='between(t,{b:.3f},{b + FLASH:.3f})'" for b in boundaries)
    if transition == "dip":
        return ",".join(f"eq=brightness='-1*max(0,1-abs(t-{b:.3f})/{DIP})':eval=frame:"
                        f"enable='between(t,{b - DIP:.3f},{b + DIP:.3f})'" for b in boundaries)
    return ""


def grade(look: str) -> str:
    return look_filter(look) if look else ""


def preview(job: Path, n: int, choice: dict, out: Path, log=print) -> Path:
    """beat `n` as one 360x640 jpg with `choice`'s grade and caption look (the text layer as at 60% of the beat)."""
    from ..config import LANGS
    from ..longform.video import _fonts
    from ..pipeline import _install_font
    from . import _load

    job = Path(job)
    cfg, ep, tl, voices, entries, _ = _load(job)
    if not 1 <= n <= len(entries):
        raise ValueError(f"There's no beat {n}.")
    chosen, slot = entries[n - 1]["chosen"], tl.slots[n - 1]
    work = job / "work_preview"
    work.mkdir(exist_ok=True)
    try:
        words = {v.scene: v.words for v in voices}
        (work / "text.ass").write_text(captions.build(ep.script, tl, words, choice.get("caption", "classic"), choice.get("graphics", [])),
                                       encoding="utf-8")
        profile = LANGS.get(ep.script.lang, LANGS["en"])
        for _, file in _fonts(ep.script.lang):
            _install_font(profile, work / "fonts", file)
        path = Path(chosen["file"])
        fx, fy = chosen.get("focus") or (0.5, 0.5)
        shown = min(0.3, slot.length * 0.6)   # early in the beat: its cut graphics are still moving
        at = float(chosen.get("start", 0.0)) + shown
        crop = (f"scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920:"
                f"x='min(max(iw*{fx:.3f}-ow/2,0),iw-ow)':y='min(max(ih*{fy:.3f}-oh/2,0),ih-oh)'")
        vf = ",".join(x for x in (crop, grade(choice.get("look", "")), "ass=text.ass:fontsdir=fonts:shaping=complex",
                                  "scale=360:640") if x)
        still = path.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp")
        src = ["-loop", "1", "-i", str(path)] if still else ["-ss", f"{at:.2f}", "-i", str(path)]
        # the text layer runs on the beat's own clock: the frame is given the time it has in the Short
        shift = ["-itsoffset", f"{slot.start + shown:.3f}"]
        subprocess.run(["ffmpeg", "-y", "-v", "error", *shift, *src, "-vf", vf, "-frames:v", "1", "-q:v", "3",
                        str(out.resolve())], cwd=work, stdin=subprocess.DEVNULL, check=True, capture_output=True)
    except subprocess.CalledProcessError as e:
        raise RuntimeError((e.stderr or b"").decode(errors="replace")[-300:] or "ffmpeg failed")
    finally:
        import shutil

        shutil.rmtree(work, ignore_errors=True)
    return out
