"""Read a content-plan workbook (.xlsx) and turn each episode into a VideoScript.

Expected layout (sheets are found by their header row, not their names; extra columns are ignored):
- Plan:         Ep | Animal/Topic | Hook | YouTube Title | Length | Music / Mood | Key Visual | Status | ...
                Music / Mood picks the background track from assets/music; Key Visual is the shot the footage is
                planned around and the cover is taken from.
- Scripts:      Ep | ... | Time | Visual | On-screen Text | Voiceover      (one row per scene)
- Descriptions: Ep | Title | Description | Hashtags                         (optional)
- Fact Check:   Ep | ... | Note                                             (optional, copied to notes.txt)

Voiceover is used word for word. Sound cues in brackets, like "(Chainsaw sound only, 1.5s)", are not spoken;
a scene that is only a sound cue becomes a silent scene as long as its Time span.
"""
import json
import os
import re
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from . import llm
import openpyxl

from .config import ASSETS_DIR, LLM_MODEL
from .facts import pinned_comment, sources_line
from .importer import _keywords, detect_lang, strip_emoji
from .script import Scene, VideoScript, make_client

CUE = re.compile(r"\([^)]*\)")  # "(Car alarm sound)": a production note, not narration
SPAN = re.compile(r"(\d+(?:\.\d+)?)\s*[–-]\s*(\d+(?:\.\d+)?)")


@dataclass
class Episode:
    ep: int
    topic: str
    title: str  # as written in the sheet, emoji included (for post.txt)
    status: str
    script: VideoScript
    notes: list[str] = field(default_factory=list)  # mood, key visual, sound cues, fact checks
    visuals: list[str] = field(default_factory=list)  # each scene's Visual description
    music: str = ""  # the assets/music track that fits the Music / Mood column ("" = by keywords at render time)


def _norm(h) -> str:
    return re.sub(r"[^a-z]", "", str(h or "").lower())


def _table(ws) -> list[dict]:
    """Rows under the first header row that starts with "Ep", as {normalized header: value}."""
    rows = list(ws.iter_rows(values_only=True))
    for i, row in enumerate(rows):
        if row and _norm(row[0]) in ("ep", "episode", "no", "id"):
            heads = [_norm(h) for h in row]
            out = []
            for r in rows[i + 1:]:
                if r and isinstance(r[0], (int, float)):
                    out.append({h: v for h, v in zip(heads, r) if h})
            return out
    return []


def _get(row: dict, *names: str) -> str:
    for n in names:
        for key, value in row.items():
            if key.startswith(n) and value not in (None, ""):
                return str(value).strip()
    return ""


def _seconds(span: str, default: float = 3.0) -> float:
    m = SPAN.search(span or "")
    return max(float(m.group(2)) - float(m.group(1)), 1.0) if m else default


def read_plan(path: Path) -> list[Episode]:
    wb = openpyxl.load_workbook(path, data_only=True, read_only=True)
    tables = {ws.title: _table(ws) for ws in wb.worksheets}
    wb.close()

    def find(*cols: str) -> list[dict]:
        for rows in tables.values():
            if rows and all(any(k.startswith(c) for k in rows[0]) for c in cols):
                return rows
        return []

    plan = find("hook") or find("youtubetitle") or find("title", "status")
    scripts = find("voiceover") or find("narration")
    descs = find("description")
    facts = find("note")
    if not scripts:
        raise ValueError(f"{path.name}: no sheet with a header row 'Ep | ... | Voiceover' was found.")

    episodes: list[Episode] = []
    eps = list(dict.fromkeys(int(r["ep"]) for r in (plan or scripts)))
    for ep in eps:
        info = next((r for r in plan if int(r["ep"]) == ep), {})
        desc = next((r for r in descs if int(r["ep"]) == ep), {})
        rows = [r for r in scripts if int(r["ep"]) == ep]
        if not rows:
            continue
        topic = _get(info, "animal", "topic", "subject") or _get(rows[0], "animal", "topic", "subject")
        title = _get(info, "youtubetitle", "title") or _get(desc, "title") or topic
        mood, key_visual = _get(info, "music", "mood"), _get(info, "keyvisual")
        notes = [f"{label}: {v}" for label, v in (("Music / mood", mood), ("Key visual", key_visual),
                                                  ("Length", _get(info, "length"))) if v]
        scenes, visuals = [], []
        for i, r in enumerate(rows, 1):
            spoken = _get(r, "voiceover", "narration")
            for cue in CUE.findall(spoken):
                notes.append(f"Scene {i} sound cue: {cue.strip('()')}")
            narration = strip_emoji(CUE.sub("", spoken))
            visual = _get(r, "visual")
            scenes.append(Scene(
                narration=narration,
                visual_query=_fallback_query(topic, visual),
                on_screen_text=strip_emoji(_get(r, "onscreen", "text")),
                seconds=0 if narration else _seconds(_get(r, "time")),
            ))
            visuals.append(visual)
        checks = [_get(r, "note") for r in facts if int(r["ep"]) == ep and _get(r, "note")]
        notes += [f"Fact check: {n}" for n in checks]
        tags = _get(desc, "hashtag") or _get(info, "hashtag")
        episodes.append(Episode(
            ep=ep, topic=topic, title=title, status=_get(info, "status"), notes=notes, visuals=visuals,
            script=VideoScript(
                title=strip_emoji(title),
                scenes=scenes,
                caption=_get(desc, "description") or _get(info, "hook"),
                hashtags=[h.lstrip("#") for h in re.split(r"[\s,]+", tags) if h.strip("#")],
                mood=mood, key_visual=key_visual, key_scene=_key_scene(key_visual, visuals),
                facts=checks, sources=sources_line(checks), pinned_comment=pinned_comment(checks),
            ),
        ))
    return episodes


def _fallback_query(topic: str, visual: str) -> str:
    subject = re.sub(r"\(.*?\)", "", topic).strip().lower()
    words = [w for w in _keywords(visual).split() if w not in subject.split()]
    return " ".join([subject, *words[:2]]).strip() or "nature background"


def _key_scene(key_visual: str, visuals: list[str]) -> int:
    """The scene (1-based) whose Visual shares the most words with the Key Visual; scene 1 (the hook) when none does."""
    want = set(_keywords(key_visual).split())
    if not want or not visuals:
        return 0
    overlap = [len(want & set(_keywords(v).split())) for v in visuals]
    return overlap.index(max(overlap)) + 1


def music_tracks() -> list[str]:
    folder = ASSETS_DIR / "music"
    return sorted(p.name for p in folder.glob("*.mp3")) if folder.exists() else []


PLAN_SCHEMA = {
    "type": "object",
    "properties": {
        "queries": {"type": "array", "items": {"type": "string"}},
        "key_scene": {"type": "integer"},
        "music": {"type": "string"},
    },
    "required": ["queries", "key_scene", "music"],
    "additionalProperties": False,
}


def plan_footage(episode: Episode, client: llm.Client | None = None) -> None:
    """Ask Gemini to turn each scene's Visual description into a stock-footage search, built around the Key Visual,
    and to pick the background track that fits the Music / Mood (one call per episode)."""
    client = client or make_client()
    script = episode.script
    lines = "\n".join(f"{i}. {v or s.narration}" for i, (s, v) in enumerate(zip(script.scenes, episode.visuals), 1))
    tracks = music_tracks()
    prompt = (
        f"Video subject: {episode.topic}\n"
        + (f"Key visual (the shot the whole video is built around): {script.key_visual}\n" if script.key_visual else "")
        + (f"Music / mood: {script.mood}\n" if script.mood else "")
        + f"\nScene visual descriptions:\n{lines}\n\n"
        f"Return exactly {len(script.scenes)} ENGLISH stock-footage search queries, one per scene, in order. "
        "2-4 concrete words each that Pixabay/Pexels realistically has (e.g. 'octopus eye closeup'). Always name the "
        "real animal or subject; never describe animations, icons, split screens or text. For black screens or "
        "graphics, pick a fitting real-world shot of the subject instead. Keep one consistent look (setting, light, "
        "colour) across the scenes that suits the mood.\n"
        + ("key_scene: the scene number (1-based) that shows the key visual; make its query the most precise search "
           "for that exact shot.\n" if script.key_visual else "key_scene: 0.\n")
        + ("music: the file from this list that best fits the mood, or \"\" if none fits:\n" + "\n".join(tracks)
           if script.mood and tracks else "music: \"\".")
    )
    response = client.beta.messages.create(
        model=LLM_MODEL,
        max_tokens=2000,
        output_config={"effort": "low", "format": {"type": "json_schema", "schema": PLAN_SCHEMA}},
        messages=[{"role": "user", "content": prompt}],
    )
    if response.stop_reason == "refusal":
        raise RuntimeError("Gemini declined to plan footage.")
    plan = json.loads(next(b.text for b in response.content if b.type == "text"))
    for scene, q in zip(script.scenes, plan["queries"]):
        if q.strip():
            scene.visual_query = q.strip()
    if script.key_visual and 1 <= plan["key_scene"] <= len(script.scenes):
        script.key_scene = plan["key_scene"]
    if plan["music"] in tracks:
        episode.music = plan["music"]


def plan_all(episodes: list[Episode], log: Callable[[str], None] = print) -> None:
    """plan_footage for several episodes at once; without Gemini the keyword searches stay."""
    if not episodes:
        return
    if not os.getenv("GEMINI_API_KEY"):
        log("  footage searches from the Visual column (Gemini isn't connected)")
        return
    client = make_client()
    with ThreadPoolExecutor(max_workers=min(len(episodes), 6)) as pool:
        for e, err in zip(episodes, pool.map(lambda e: _try_plan(e, client), episodes)):
            if err:
                log(f"  Ep {e.ep}: footage searches from the Visual column ({err})")


def _try_plan(e: Episode, client: llm.Client) -> str:
    try:
        plan_footage(e, client)
        return ""
    except Exception as err:
        return err.__class__.__name__


def render_episode(e: Episode, log: Callable[[str], None] = print, **kw) -> Path:
    """make_video for one episode, then post.txt with the sheet's own title and notes.txt. Returns video.mp4."""
    from . import music
    from .pipeline import _meta, make_video, post_body

    if not kw.get("music") and not e.music and e.script.mood and not music.local_match(e.script.mood):
        # nothing in the library fits the Music / Mood: fetch a matching track from Jamendo (when it's set up)
        e.music = music.for_mood(e.script.mood)
    if not kw.get("music") and e.music:  # random music chosen: use the track that fits the Music / Mood
        kw["music"] = str(ASSETS_DIR / "music" / e.music)
        log(f"  music for \"{e.script.mood}\": {e.music}")
    out = make_video(f"ep{e.ep:02d} {e.topic}", script=e.script, lang=episode_lang(e), log=log, **kw)
    job = out.parent
    tags = " ".join(f"#{h}" for h in e.script.hashtags)
    # the sheet's title keeps its emoji (fine on YouTube; only the burned-in text can't draw them)
    (job / "post.txt").write_text(post_body(e.title, e.script.caption, tags, _meta(job).get("music"), e.script.sources),
                                  encoding="utf-8")
    if e.notes:
        (job / "notes.txt").write_text("\n".join(e.notes) + "\n", encoding="utf-8")
    return out


def episode_lang(e: Episode) -> str:
    return detect_lang(" ".join(s.narration for s in e.script.scenes))


def pick_episodes(episodes: list[Episode], spec: str = "", include_posted: bool = False) -> list[Episode]:
    """spec like "1,3-5"; empty = all. Rows whose Status is Posted are skipped unless include_posted."""
    if spec:
        wanted: set[int] = set()
        for part in spec.split(","):
            a, _, b = part.strip().partition("-")
            wanted.update(range(int(a), int(b or a) + 1))
        return [e for e in episodes if e.ep in wanted]
    return [e for e in episodes if include_posted or e.status.lower() != "posted"]
