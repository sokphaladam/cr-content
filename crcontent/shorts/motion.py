"""Motion graphics drawn by Remotion (remotion/: React components rendered in headless Chrome), for what the ASS
shapes in graphics.py can't do: glow, sparks, blur, springy type, photos, maps. Each graphic is rendered as its own
short transparent clip (only the frames it's on screen) and laid over the picture before the captions are burned in.

- facts_remotion  a number the voice says pops up (remotion/src/Fact.tsx)
- size_compare    a length the voice says ("6 metres") shown as the animal, a frame of its own footage, growing to
                  scale next to a person (a phone under 40 cm): remotion/src/SizeCompare.tsx
- map_zoom        the place the voice names ("the Arctic Ocean"), found by Gemini once per Short (cached in
                  <job>/map.json): a globe spins to it and dives in, the country lit up: remotion/src/MapZoom.tsx

Where it runs from: the desktop app ships its own Node, a prebuilt bundle and the renderer with its headless Chrome
(scripts/build_remotion.py; the app passes the folder in CRCONTENT_REMOTION). In development: remotion/ in the repo
with the system's Node (`npm install` at the root sets it up). Anything failing returns None: the caller falls back
(the fact pop-ups to their ASS version; the others are left out), so a Short never fails to render over this.
"""
import base64
import hashlib
import json
import os
import re
import shutil
from pathlib import Path

from ..config import LLM_MODEL
from ..render import run
from ..visuals import IMAGE_EXTS
from . import graphics

# Tauri's resource_dir is a \\?\C:\... verbatim path on Windows, which Node can't load a script from
PROJECT = Path((os.getenv("CRCONTENT_REMOTION") or "").removeprefix("\\\\?\\") or Path(__file__).resolve().parents[2] / "remotion")
NAMES = ("facts_remotion", "size_compare", "map_zoom")  # the graphics.NAMES drawn here
ACCENT = "#FACC15"  # the captions' spoken-word amber
SIZE_SECONDS, MAP_SECONDS = 3.4, 3.2
LENGTHS = {"metre": 1, "metres": 1, "meter": 1, "meters": 1, "m": 1, "foot": 0.3048, "feet": 0.3048, "ft": 0.3048,
           "centimetre": 0.01, "centimetres": 0.01, "centimeter": 0.01, "centimeters": 0.01, "cm": 0.01,
           "inch": 0.0254, "inches": 0.0254, "millimetre": 0.001, "millimetres": 0.001, "millimeter": 0.001,
           "millimeters": 0.001, "mm": 0.001}
ZOOMS = ("world", "continent", "country", "region", "city")
PLACE_SCHEMA = {
    "type": "object",
    "properties": {"found": {"type": "boolean"}, "place": {"type": "string"}, "lat": {"type": "number"},
                   "lon": {"type": "number"}, "zoom": {"type": "string", "enum": list(ZOOMS)},
                   "words": {"type": "string"}},
    "required": ["found", "place", "lat", "lon", "zoom", "words"],
    "additionalProperties": False,
}


def node() -> str | None:
    """The desktop app's own Node (next to render.mjs), else the system's."""
    own = PROJECT / ("node.exe" if os.name == "nt" else "node")
    return str(own) if own.is_file() else shutil.which("node")


def _data_url(path: Path, mime: str) -> str:
    return f"data:{mime};base64,{base64.b64encode(path.read_bytes()).decode()}"


def font_url(path: Path | None) -> str:
    """A font file as a data: URL for the props ("" without one: Remotion's system sans)."""
    if not path or not path.is_file():
        return ""
    return _data_url(path, "font/otf" if path.suffix.lower() == ".otf" else "font/ttf")


def metres(shown: str, unit: str) -> float | None:
    """A spoken length in metres ("6", "METRES" -> 6.0); None for anything else, or sizes no comparison can show."""
    if unit.lower() not in LENGTHS or not re.fullmatch(r"[\d,]+(\.\d+)?", shown):
        return None
    m = float(shown.replace(",", "")) * LENGTHS[unit.lower()]
    return m if 0.005 <= m <= 100 else None


def photo(chosen: dict, work: Path, k: int) -> str:
    """A 2:1 frame of a beat's own footage around its subject (data: URL), "" when it has none (a card)."""
    if chosen.get("source") in ("card", "placeholder") or not chosen.get("file"):
        return ""
    src = Path(chosen["file"])
    fx, fy = chosen.get("focus") or (0.5, 0.5)
    seek = [] if src.suffix.lower() in IMAGE_EXTS else ["-ss", f"{float(chosen.get('start') or 0) + 0.3:.2f}"]
    out = work / f"subject_{k:02d}.jpg"
    crop = (f"crop=w='min(iw,ih*2)':h='min(iw,ih*2)/2':x='clip({float(fx)}*iw-ow/2,0,iw-ow)'"
            f":y='clip({float(fy)}*ih-oh/2,0,ih-oh)',scale=640:320")
    try:
        run(["ffmpeg", "-y", "-v", "error", *seek, "-i", str(src), "-frames:v", "1", "-vf", crop, "-q:v", "3", str(out)])
        return _data_url(out, "image/jpeg")
    except (RuntimeError, OSError):
        return ""


def place(job: Path, tl, words: dict, log=print) -> dict | None:
    """The place the voiceover names, {place, lat, lon, zoom, at} (`at`: when it's said), or None. Asked of Gemini
    once per voiceover: kept in <job>/map.json until the words change."""
    said = [(slot.start + w.start, w.text) for slot in tl.slots for w in words.get(slot.scene) or []]
    text = " ".join(t for _, t in said)
    if not text:
        return None
    key = hashlib.sha1(text.encode()).hexdigest()[:16]
    cache = job / "map.json"
    try:
        data = json.loads(cache.read_text(encoding="utf-8"))
        data = data if data.get("key") == key else None
    except (OSError, ValueError):
        data = None
    if data is None:
        try:
            from ..script import make_client

            response = make_client().beta.messages.create(
                model=LLM_MODEL,
                max_tokens=300,
                output_config={"effort": "low", "format": {"type": "json_schema", "schema": PLACE_SCHEMA}},
                messages=[{"role": "user", "content": (
                    f"A short video's voiceover:\n\"{text}\"\n\nDoes it name a real place on Earth: where the animal "
                    "lives, or where the story happens (a country, region, ocean, river, city...)? If so: place = its "
                    "name for an on-screen label (2-4 words), lat and lon of its centre, zoom = how far a map must "
                    "zoom in to show it (world: a whole ocean or a worldwide range; continent; country; region; city), "
                    "words = the exact 1-4 words of the voiceover that name it, as written there. If it names "
                    "several, the first. found = false when it names no place (\"the ocean\" alone is not a place).")}],
            )
            data = {"key": key, **json.loads(next(b.text for b in response.content if b.type == "text"))}
            cache.write_text(json.dumps(data), encoding="utf-8")
        except Exception as e:  # noqa: BLE001 - no Gemini: no map
            log(f"      ! couldn't find the place with Gemini ({type(e).__name__}); no map zoom")
            return None
    if not data.get("found") or not (-90 <= data["lat"] <= 90 and -180 <= data["lon"] <= 180):
        return None
    norm = lambda t: re.sub(r"[^a-z0-9']", "", t.lower())  # noqa: E731
    target = [norm(t) for t in data["words"].split() if norm(t)]
    spoken = [norm(t) for _, t in said]
    for i in range(len(spoken)):
        if target and spoken[i:i + len(target)] == target:
            return {"place": data["place"], "lat": data["lat"], "lon": data["lon"],
                    "zoom": data["zoom"] if data["zoom"] in ZOOMS else "country", "at": said[i][0]}
    return None


def plan(tl, words: dict, font: str, wanted, photo_of=lambda k: "", where: dict | None = None) -> list[dict]:
    """The clips to render: {id, props, at} with `at` the second it starts, one at a time (a graphic never covers
    another). `photo_of(k)`: beat k's subject frame, asked only for beats with a length to compare."""
    todo = []
    for at, end, shown, value, unit, k in graphics.fact_times(tl, words):
        m = metres(shown, unit) if "size_compare" in wanted else None
        if m:
            todo.append({"id": "SizeCompare", "at": at, "props": {
                "metres": m, "shown": shown, "unit": unit, "photo": photo_of(k), "font": font,
                "seconds": round(min(SIZE_SECONDS, tl.total - at), 3)}})
        elif "facts_remotion" in wanted:
            todo.append({"id": "Fact", "at": at, "props": {
                "shown": shown, "value": value, "unit": unit, "y": graphics.FACT_Y, "font": font, "accent": ACCENT,
                "seconds": round(end - at, 3)}})
    if "map_zoom" in wanted and where:
        todo.append({"id": "MapZoom", "at": where["at"], "props": {
            **{k: where[k] for k in ("place", "lat", "lon", "zoom")}, "font": font,
            "seconds": round(min(MAP_SECONDS, tl.total - where["at"]), 3)}})
    out, free = [], 0.0
    for c in sorted(todo, key=lambda c: c["at"]):
        if c["at"] >= free and c["props"]["seconds"] >= 0.6:
            out.append(c)
            free = c["at"] + c["props"]["seconds"]
    return out


def overlay(work: Path, picture: str, todo: list[dict], log=print) -> str | None:
    """work/<picture> with the clips laid over it, as a new file name in work/; None when there's nothing to draw, or
    Remotion isn't available or failed (logged)."""
    if not todo:
        return None
    exe = node()
    if not (PROJECT / "node_modules").is_dir() or not exe:
        log(f"      ! Remotion graphics need Node and `npm install` (at the project root) for {PROJECT}: they're "
            "left out (fact pop-ups use the built-in ones)")
        return None
    for k, c in enumerate(todo):
        c["out"] = str(work / f"gfx_{k:02d}.webm")
    (work / "gfx.json").write_text(json.dumps({"clips": todo}), encoding="utf-8")
    inputs, chain, last = [], [], "0:v"
    for k, c in enumerate(todo):
        inputs += ["-c:v", "libvpx", "-i", Path(c["out"]).name]  # libvpx: the built-in vp8 decoder drops the alpha
        chain.append(f"[{k + 1}:v]setpts=PTS+{c['at']:.3f}/TB[g{k}];[{last}][g{k}]overlay=eof_action=pass[o{k}]")
        last = f"o{k}"
    out = "picture_gfx.mkv"
    try:
        log(f"      Remotion: {', '.join(c['id'] for c in todo)}")
        run([exe, str(PROJECT / "render.mjs"), str(work / "gfx.json")], cwd=PROJECT, timeout=900)
        run(["ffmpeg", "-y", "-hide_banner", "-v", "error", "-i", picture, *inputs, "-filter_complex", ";".join(chain),
             "-map", f"[{last}]", "-map", "0:a?", "-c:v", "libx264", "-preset", "veryfast", "-crf", "10",
             "-pix_fmt", "yuv420p", "-c:a", "copy", out], cwd=work)
    except Exception as e:  # noqa: BLE001 - any failure: the Short renders without these
        log(f"      ! Remotion failed ({type(e).__name__}: {str(e)[:200]}); rendering without its graphics")
        return None
    return out
