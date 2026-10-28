"""Smart covers: find the most eye-catching frames and ask Gemini for click-worthy headlines."""
import base64
import json
import subprocess
from pathlib import Path

from . import llm

from .captions import THUMB_STYLES, auto_emphasis
from .config import LLM_MODEL, LANGS
from .render import duration
from .script import VideoScript, make_client

SAMPLE_W, SAMPLE_H = 72, 128


def _frame_score(px: bytes) -> float:
    """0..1 appeal of one small RGB frame: sharp, colourful, contrasty, and neither too dark nor blown out."""
    n = len(px) // 3
    r, g, b = px[0::3], px[1::3], px[2::3]
    luma = [(299 * r[i] + 587 * g[i] + 114 * b[i]) // 1000 for i in range(n)]
    mean = sum(luma) / n
    contrast = (sum((y - mean) ** 2 for y in luma) / n) ** 0.5
    # sharpness: average gradient to the right and lower neighbour (blurry frames score low)
    edges = sum(abs(luma[i] - luma[i + 1]) + abs(luma[i] - luma[i + SAMPLE_W])
                for i in range(n - SAMPLE_W) if (i + 1) % SAMPLE_W)
    sharp = edges / (2 * n)
    # Hasler & Süsstrunk colourfulness
    rg = [r[i] - g[i] for i in range(n)]
    yb = [(r[i] + g[i]) / 2 - b[i] for i in range(n)]

    def stats(v):
        m = sum(v) / n
        return m, (sum((x - m) ** 2 for x in v) / n) ** 0.5

    (mrg, srg), (myb, syb) = stats(rg), stats(yb)
    colour = (srg ** 2 + syb ** 2) ** 0.5 + 0.3 * (mrg ** 2 + myb ** 2) ** 0.5
    exposure = max(0.0, 1 - abs(mean - 120) / 110)
    return (0.35 * min(sharp / 14, 1) + 0.25 * min(colour / 90, 1)
            + 0.2 * min(contrast / 60, 1) + 0.2 * exposure)


def opening_score(video: Path, seconds: float = 1.5, samples: int = 6) -> float:
    """0..1 how well a clip works as a video's first frame in the feed: its opening is bright, colourful and sharp
    (frame appeal), and moving (a still or near-still opening reads as a photo and gets scrolled past)."""
    proc = subprocess.run(
        ["ffmpeg", "-v", "error", "-t", f"{seconds:.2f}", "-i", str(video), "-an", "-vf",
         f"fps={samples / seconds:.3f},scale={SAMPLE_W}:{SAMPLE_H}:force_original_aspect_ratio=increase,"
         f"crop={SAMPLE_W}:{SAMPLE_H}", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
        stdin=subprocess.DEVNULL, capture_output=True, check=True)
    size = SAMPLE_W * SAMPLE_H * 3
    frames = [proc.stdout[k * size:(k + 1) * size] for k in range(len(proc.stdout) // size)]
    if not frames:
        return 0.0
    appeal = sum(_frame_score(f) for f in frames) / len(frames)
    lumas = [f[1::3] for f in frames]  # green is close enough to luma for brightness and change
    bright = sum(sum(y) / len(y) for y in lumas) / len(lumas)
    motion = (sum(sum(abs(a - b) for a, b in zip(lumas[k], lumas[k + 1])) / len(lumas[k])
                  for k in range(len(lumas) - 1)) / (len(lumas) - 1)) if len(lumas) > 1 else 0.0
    return 0.55 * appeal + 0.25 * min(motion / 18, 1) + 0.2 * min(bright / 130, 1)


def best_frames(video: Path, count: int = 4, samples: int = 32) -> list[float]:
    """Times (s) of the `count` best-looking frames, spread across the video so the picks aren't near-duplicates."""
    length = duration(video)
    if length < 0.5:
        return [0.0]
    rate = samples / length
    proc = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(video), "-an", "-vf",
         f"fps={rate:.5f},scale={SAMPLE_W}:{SAMPLE_H}:force_original_aspect_ratio=increase,"
         f"crop={SAMPLE_W}:{SAMPLE_H}", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
        stdin=subprocess.DEVNULL, capture_output=True, check=True)
    size = SAMPLE_W * SAMPLE_H * 3
    frames = [proc.stdout[k * size:(k + 1) * size] for k in range(len(proc.stdout) // size)]
    # brightness of each sample (green ~ luma) and how much of it is blown out to white
    means = [sum(f[1::3]) / (len(f) // 3) for f in frames]
    blown = [sum(1 for g in f[1::3] if g > 245) / (len(f) // 3) for f in frames]
    scored = []
    for k, f in enumerate(frames):
        t = k / rate
        if 0.2 <= t <= length - 0.3:
            score = _frame_score(f)
            # a white flash / impact frame: much brighter than the samples either side of it (a scene that is just
            # bright stays bright next door) or largely blown out; a cover caught mid-flash looks washed out
            near = [means[j] for j in (k - 1, k + 1) if 0 <= j < len(means)]
            jump = means[k] - (sum(near) / len(near) if near else means[k])
            if jump > 18:
                score *= max(0.15, 1 - (jump - 18) / 40)
            if blown[k] > 0.2:
                score *= max(0.3, 1 - blown[k])
            scored.append((score, round(t, 2)))
    scored.sort(reverse=True)
    gap = length / (count * 2.5)
    picks: list[float] = []
    for _, t in scored:
        if all(abs(t - p) >= gap for p in picks):
            picks.append(t)
        if len(picks) == count:
            break
    return picks or [min(1.0, length / 2)]


COVERS_SCHEMA = {
    "type": "object",
    "properties": {
        "covers": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "text": {"type": "string"},
                    "emphasis": {"type": "string"},
                    "style": {"type": "string", "enum": list(THUMB_STYLES)},
                    "frame": {"type": "integer"},
                    "photo_query": {"type": "string"},
                    "direction": {"type": "string"},
                },
                "required": ["text", "emphasis", "style", "frame", "photo_query", "direction"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["covers"],
    "additionalProperties": False,
}

HEADLINES_SYSTEM = """You design the covers (thumbnails) of short videos and music videos for YouTube, Shorts, TikTok and Reels.

What makes a cover get clicked:
- 2-5 words of headline. It's read in a split second at thumbnail size.
- Open a curiosity gap or make a bold promise; don't summarise the video or give away the payoff.
- Proven patterns: a surprising number ("90% GET THIS WRONG"), a bold claim ("THIS CHANGES EVERYTHING"),
  a direct challenge ("YOU'RE DOING IT WRONG"), a short question ("WHY DO CATS PURR?"), a contrast ("CHEAP vs EXPENSIVE").
  For a song: the hook line, the song's title, or a short emotional phrase from the lyrics.
- Complement the title rather than repeating it word for word.
- No emoji, no hashtags, no quotation marks, no clickbait that the video doesn't deliver.
- The picture matters as much as the words: one clear subject, strong light and colour, room for the headline.

`emphasis` is the 1-2 words copied exactly from `text` that carry the punch (the number, the surprising word); they
get highlighted in a bright colour. `style`: bold (white, heavy outline), box (black on yellow boxes), stacked
(a word or two per line, large). When the user describes the cover they want, follow their idea first.

Each cover is then laid out by a designer, so also give it a `direction`: one or two sentences of art direction that
suit the subject and differ between the covers, e.g. "neon cyberpunk: magenta/cyan glow, photo in a tilted frame,
headline stacked left", "clean editorial: photo full-bleed, bold white type on a black band, red accent tag",
"split screen: photo top 60%, solid yellow block below with huge black type", "cinematic: teal-orange grade,
letterboxed photo, thin elegant serif title with a glowing highlight"."""


def brief(job: Path) -> dict:
    """What the cover is for: title, hook and the rest, from the job's script.json or song.json."""
    if (job / "script.json").exists():
        script = VideoScript.load(job / "script.json")
        info = {"kind": "video", "title": script.title,
                "hook": script.scenes[0].narration if script.scenes else "",
                "scene_headlines": [s.on_screen_text for s in script.scenes if s.on_screen_text],
                "caption": script.caption}
        if script.key_visual:  # from the content plan: the cover should show this shot
            info["key_visual"] = script.key_visual
        if script.mood:
            info["mood"] = script.mood
        return info
    if (job / "song.json").exists():
        from .lyrics import SongScript

        song = SongScript.load(job / "song.json")
        lines = [l.strip() for s in song.sections for l in s.lyrics if l.strip()]
        return {"kind": "music video", "title": song.title, "genre": song.genre, "mood": song.mood,
                "lyrics_start": lines[:6], "caption": song.caption}
    return {"kind": "video", "title": job.name}


def _frame_jpeg(video: Path, at: float, width: int = 360) -> bytes:
    return subprocess.run(
        ["ffmpeg", "-v", "error", "-ss", f"{at:.2f}", "-i", str(video), "-frames:v", "1",
         "-vf", f"scale={width}:-2", "-q:v", "4", "-f", "image2", "-c:v", "mjpeg", "-"],
        stdin=subprocess.DEVNULL, capture_output=True, check=True).stdout


def plan_covers(video: Path, info: dict, lang: str, frames: list[float], count: int = 4, idea: str = "",
                client: llm.Client | None = None) -> list[dict]:
    """Gemini looks at the candidate frames and plans `count` covers: headline, highlight, style, and which frame
    (or, when the user's idea shows something no frame has, a stock photo search instead)."""
    profile = LANGS.get(lang, LANGS["en"])
    client = client or make_client()
    content: list[dict] = []
    for i, at in enumerate(frames):
        content.append({"type": "text", "text": f"Frame {i + 1} (at {at:.1f} s):"})
        content.append({"type": "image", "source": {"type": "base64", "media_type": "image/jpeg",
                                                    "data": base64.b64encode(_frame_jpeg(video, at)).decode()}})
    ask = (f"Language for the headlines: {profile.name}\n"
           f"About the {info.get('kind', 'video')}:\n{json.dumps(info, ensure_ascii=False, indent=2)}\n\n")
    if idea.strip():
        ask += (f"The user's idea for the cover:\n<idea>\n{idea.strip()}\n</idea>\n"
                f"Follow it: the words, the picture and the mood it asks for.\n\n")
    ask += (f"Plan {count} different covers. For each, pick the frame (1-{len(frames)}) whose picture fits best: a clear "
            f"subject, good light, nothing blurry. Use different frames when they're good enough. "
            f"Only if the user's idea asks for a picture that none of the frames shows, set frame to 0 and "
            f"photo_query to an ENGLISH stock photo search of 2-5 words for that picture; otherwise photo_query is "
            f"\"\". Vary the headline patterns and styles.")
    if lang == "km":
        ask += ("\nWrite the headlines in natural Khmer, each under about 25 characters, with a normal space between "
                "phrases; `emphasis` is one whole space-separated phrase.")
    content.append({"type": "text", "text": ask})
    response = client.beta.messages.create(
        model=LLM_MODEL,
        max_tokens=3000,
        output_config={"effort": "low", "format": {"type": "json_schema", "schema": COVERS_SCHEMA}},
        system=HEADLINES_SYSTEM,
        messages=[{"role": "user", "content": content}],
    )
    if response.stop_reason == "refusal":
        raise RuntimeError("Gemini declined to suggest thumbnails.")
    covers = json.loads(next(b.text for b in response.content if b.type == "text"))["covers"]
    out = []
    for c in covers:
        if not c["text"].strip() and not c["photo_query"].strip():
            continue
        k = c["frame"] - 1
        query = c["photo_query"].strip() if not 0 <= k < len(frames) else ""
        out.append({"text": c["text"].strip(), "emphasis": c["emphasis"].strip(),
                    "style": c["style"] if c["style"] in THUMB_STYLES else "bold",
                    "at": frames[k] if 0 <= k < len(frames) else frames[0], "photo_query": query,
                    "direction": c["direction"].strip()})
    return out[:count]


def basic_headlines(info: dict, count: int = 4, idea: str = "") -> list[dict]:
    """Without Gemini: the idea's own words, the title and the scene headlines (or first lyric lines), each with
    its strongest word highlighted."""
    seen, out = set(), []
    first = " ".join(idea.split()[:5]) if idea.strip() else ""
    for text in [first, info.get("title", ""), *info.get("scene_headlines", []), *info.get("lyrics_start", [])]:
        if text.strip() and text.lower() not in seen:
            seen.add(text.lower())
            out.append({"text": text.strip(), "emphasis": auto_emphasis(text)})
    return out[:count]


def suggestions(video: Path, info: dict, lang: str, count: int = 4, idea: str = "") -> tuple[list[dict], str]:
    """Cover ideas: Gemini picks frames and writes headlines (following `idea` when given); without Gemini, the
    best frames paired with headlines from the script, rotating through the styles.

    Returns (suggestions, note); the note says why Gemini wasn't used, if it wasn't.
    """
    frames = best_frames(video, max(count * 2, 6))
    try:
        covers = plan_covers(video, info, lang, frames, count, idea)
        if covers:
            return covers, ""
        note = "Gemini didn't return any covers, so these come from your script."
    except Exception as e:  # no key, no credits, offline...: covers still work from the script itself
        note = "Gemini was unavailable, so these headlines come from your script."
        print(f"  ! thumbnail ideas: {type(e).__name__}: {e}")
    heads = basic_headlines(info, count, idea) or [{"text": info.get("title", ""), "emphasis": ""}]
    return [{"text": h["text"], "emphasis": h["emphasis"], "style": THUMB_STYLES[i % len(THUMB_STYLES)],
             "at": frames[i % len(frames)], "photo_query": ""} for i, h in enumerate(heads)], note
