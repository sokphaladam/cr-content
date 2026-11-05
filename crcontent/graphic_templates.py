"""The timeline's motion-graphics templates (attention roadmap M5): typed, versioned definitions of the Remotion
compositions in remotion/src, the checks every graphic clip's props go through, and preview frames.

A template lists its fields (type, default, limits). Every placeable template also takes the shared placement
fields (remotion/src/Placed.tsx): position, scale, rotation, opacity, entry and exit. `validate` fills defaults and
reports what's wrong in plain words; the render leaves an invalid graphic out and says so, the editor shows the
errors next to the field. The editor's inspector is built from the same definitions (GET /api/timeline/catalog).
"""
import hashlib
import json
import re
import subprocess
import threading
from pathlib import Path

from .config import CACHE_DIR

ENTERS = ["none", "fade", "pop", "slide_up", "slide_left", "wipe"]  # remotion/src/Placed.tsx
ACCENT = "#FACC15"
FPS = 30
HEX = re.compile(r"#[0-9A-Fa-f]{6}")


def _f(key, kind, default, label="", **limits) -> dict:
    return {"key": key, "type": kind, "default": default, "label": label or key.replace("_", " ").capitalize(), **limits}


def _text(key, default, max_len, label="", required=False, group="content"):
    return _f(key, "text", default, label, max_len=max_len, required=required, group=group)


def _num(key, default, lo, hi, label="", step=None, group="content"):
    return _f(key, "number", default, label, min=lo, max=hi, step=step, group=group)


def _choice(key, default, options, label="", group="content"):
    return _f(key, "choice", default, label, options=options, group=group)


def _color(key="accent", default=ACCENT, label="Accent colour"):
    return _f(key, "color", default, label, group="style")


def placement(x=0.5, y=0.5, enter="pop", exit="fade") -> list[dict]:
    # at_x / at_y, not x / y: Fact has its own y (px, Shorts mode sets it)
    return [_num("at_x", x, 0, 1, "Across", 0.01, "position"), _num("at_y", y, 0, 1, "Down", 0.01, "position"),
            _num("scale", 1, 0.2, 3, "Scale", 0.05, "position"), _num("rotation", 0, -180, 180, "Rotation", 1, "position"),
            _num("opacity", 1, 0, 1, "Opacity", 0.05, "position"),
            _choice("enter", enter, ENTERS, "Comes in", "motion"), _choice("exit", exit, ENTERS, "Goes out", "motion")]


def _t(label, description, seconds, fields, version=1, fixed=None, place=None):
    return {"version": version, "label": label, "description": description, "seconds": seconds,
            "fields": fields + (placement(**place) if place is not None else []), "fixed": fixed or {}}


TEMPLATES = {
    "KineticTitle": _t("Kinetic title", "A short hook or section headline, its words punching in one by one.", 2.5, [
        _text("text", "WAIT FOR IT", 60, "Text", required=True), _choice("style", "bold", ["bold", "box", "outline"], "Style"),
        _color()], place={"y": 0.24, "enter": "none", "exit": "fade"}),
    "Fact": _t("Fact / statistic", "A number counting up with its unit: the figure the voice says.", 2.5, [
        _text("shown", "3", 16, "Number", required=True), _text("unit", "hearts", 24, "Unit"), _color()],
        fixed={"y": 960}, place={"y": 0.3, "enter": "none", "exit": "none"}),
    "Callout": _t("Callout", "A circle, arrow or box that draws itself around a detail, with a label.", 2.5, [
        _choice("shape", "circle", ["circle", "arrow", "box"], "Shape"), _text("label", "LOOK HERE", 32, "Label"),
        _num("size", 180, 60, 450, "Size", 5), _color()], place={"y": 0.45, "enter": "none", "exit": "fade"}),
    "LowerThird": _t("Lower third", "The subject, species or place, with a short line under it.", 3, [
        _text("title", "Common octopus", 32, "Title", required=True), _text("subtitle", "Octopus vulgaris", 48, "Line under it"),
        _color()], place={"y": 0.74, "enter": "slide_left", "exit": "fade"}),
    "Spotlight": _t("Freeze-frame spotlight", "The picture holds still and dims around the subject, to point it out.", 2, [
        _num("spot_x", 0.5, 0, 1, "Subject across", 0.01), _num("spot_y", 0.45, 0, 1, "Subject down", 0.01),
        _num("radius", 0.22, 0.05, 0.5, "Spot size", 0.01), _num("dim", 0.7, 0, 0.95, "Darken", 0.05),
        _text("label", "", 32, "Label"), _choice("freeze", "yes", ["yes", "no"], "Freeze the picture"), _color(),
        _choice("enter", "fade", ENTERS, "Comes in", "motion"), _choice("exit", "fade", ENTERS, "Goes out", "motion")]),
    "SplitCompare": _t("Split comparison", "Two subjects, sizes, actions or states side by side.", 3, [
        _text("title", "", 40, "Title"), _text("left_label", "Octopus", 24, "Left", required=True),
        _text("left_value", "3", 16, "Left value"), _text("right_label", "Human", 24, "Right", required=True),
        _text("right_value", "1", 16, "Right value"), _color()], place={"y": 0.42, "enter": "none", "exit": "fade"}),
    "Process": _t("Process / steps", "Up to five steps in order, one after another (separate them with ;).", 3.5, [
        _text("title", "How it works", 40, "Title"), _text("steps", "Bend the wire; Hook the food; Pull it out", 240, "Steps", required=True),
        _color()], place={"y": 0.45, "enter": "none", "exit": "fade"}),
    "MapZoom": _t("Map / location", "A globe that turns to a place and dives in, its name labelled.", 3.2, [
        _text("place", "Iceland", 32, "Place", required=True), _num("lat", 64.9, -90, 90, "Latitude", 0.1),
        _num("lon", -19.0, -180, 180, "Longitude", 0.1), _choice("zoom", "country", ["world", "continent", "country", "region", "city"], "Zoom")],
        place={"enter": "none", "exit": "none"}),
    "SizeCompare": _t("Size comparison", "The subject's length next to a person (or a phone, under 40 cm).", 3.4, [
        _num("metres", 1.0, 0.005, 100, "Length (m)", 0.01), _text("shown", "1", 12, "As said", required=True),
        _text("unit", "metre", 16, "Unit")], fixed={"photo": ""}, place={"enter": "none", "exit": "none"}),
}


def defaults(template: str) -> dict:
    return {f["key"]: f["default"] for f in TEMPLATES[template]["fields"]}


def validate(template: str, props: dict, version: int = 0) -> tuple[dict, list[str]]:
    """(props with defaults filled in, problems in plain words). Unknown keys are dropped; nothing is clamped."""
    t = TEMPLATES.get(template)
    if not t:
        return {}, [f"Unknown template '{template}'."]
    if version > t["version"]:
        return {}, [f"This {t['label']} was made by a newer version of the app (v{version}). Update the app."]
    out, errors = {}, []
    for f in t["fields"]:
        k, label, v = f["key"], f["label"], props.get(f["key"], f["default"])
        if f["type"] == "number":
            if isinstance(v, bool) or not isinstance(v, (int, float)):
                try:
                    v = float(v)
                except (TypeError, ValueError):
                    errors.append(f"{label}: not a number.")
                    continue
            if not f["min"] <= v <= f["max"]:
                errors.append(f"{label}: {v:g} is outside {f['min']:g}-{f['max']:g}.")
        elif f["type"] == "choice":
            if v not in f["options"]:
                errors.append(f"{label}: '{v}' isn't one of {', '.join(f['options'])}.")
        elif f["type"] == "color":
            if not isinstance(v, str) or not HEX.fullmatch(v):
                errors.append(f"{label}: '{v}' isn't a colour like #FACC15.")
        else:
            v = "" if v is None else str(v)
            if f.get("required") and not v.strip():
                errors.append(f"{label} is empty.")
            elif len(v) > f["max_len"]:
                errors.append(f"{label}: {len(v)} characters, at most {f['max_len']}.")
        out[k] = v
    return {**out, **t["fixed"], **_derived(template, out)}, errors


def _derived(template: str, props: dict) -> dict:
    """Props the composition needs that follow from the others."""
    if template == "Fact":  # it counts up when the number is a whole one
        digits = str(props.get("shown", "")).replace(",", "")
        return {"value": int(digits) if digits.isdigit() else None, "unit": str(props.get("unit", "")).upper()}
    if template == "Spotlight":
        return {"photo": ""}
    return {}


def preview_frame(template: str, seconds: float) -> int:
    """The frame a preview shows: everything in (titles, steps, the map zoomed), just before the exit starts
    (Placed.tsx and the templates take 7 frames to go out)."""
    return max(0, round(FPS * seconds) - 9)


# ---------- preview frames (remotion/still.mjs) ----------

STILLS = CACHE_DIR / "graphics"
_lock = threading.Lock()


def _bundle_dir(project: Path) -> Path:
    """The desktop app's prebuilt bundle, else src/ bundled once into the cache (again when the source changes)."""
    if (project / "bundle" / "index.html").is_file():
        return project / "bundle"
    h = hashlib.sha1()
    for f in sorted((project / "src").glob("*")):
        h.update(f.name.encode() + f.read_bytes())
    return CACHE_DIR / "remotion-bundle" / h.hexdigest()[:12]


def still_key(template: str, props: dict, seconds: float) -> str:
    v = TEMPLATES[template]["version"] if template in TEMPLATES else 0
    return hashlib.sha1(json.dumps([template, v, props, round(seconds, 2)], sort_keys=True).encode()).hexdigest()[:20]


def render_stills(jobs: list[dict], font: str = "", timeout: int = 300) -> dict[str, str]:
    """Preview PNGs for [{template, props (validated), seconds}], cached by everything that changes them.
    Returns {key: "" (made) or the reason it failed}; the PNG is STILLS/<key>.png."""
    from .shorts import motion

    exe = motion.node()
    if not (motion.PROJECT / "node_modules").is_dir() or not exe:
        return {still_key(j["template"], j["props"], j["seconds"]): "Remotion isn't installed (Node and `npm install`)" for j in jobs}
    STILLS.mkdir(parents=True, exist_ok=True)
    result, todo = {}, []
    for j in jobs:
        key = still_key(j["template"], j["props"], j["seconds"])
        if (STILLS / f"{key}.png").is_file():
            result[key] = ""
        elif key not in result:
            result[key] = "not made"
            todo.append({"id": j["template"], "frame": preview_frame(j["template"], j["seconds"]), "out": str(STILLS / f"{key}.png"),
                         "props": {**j["props"], "font": font, "seconds": j["seconds"]}, "key": key})
    if not todo:
        return result
    with _lock:  # one headless Chrome at a time
        spec = STILLS / f"jobs-{todo[0]['key']}.json"
        spec.write_text(json.dumps({"bundle": str(_bundle_dir(motion.PROJECT)), "stills": todo}), encoding="utf-8")
        try:
            out = subprocess.run([exe, str(motion.PROJECT / "still.mjs"), str(spec)], cwd=motion.PROJECT, stdin=subprocess.DEVNULL,
                                 capture_output=True, text=True, timeout=timeout)
            lines = out.stdout.splitlines()
            failed_all = out.returncode != 0 and (out.stderr.strip().splitlines() or ["the renderer stopped"])[-1][:200]
        except (OSError, subprocess.TimeoutExpired) as e:
            lines, failed_all = [], f"{type(e).__name__}"
        finally:
            spec.unlink(missing_ok=True)
    for t in todo:
        ok = (STILLS / f"{t['key']}.png").is_file()
        why = next((ln.split(t["out"], 1)[1].strip() for ln in lines if ln.startswith("failed ") and t["out"] in ln), "")
        result[t["key"]] = "" if ok else (why or failed_all or "no frame was made")
    return result
