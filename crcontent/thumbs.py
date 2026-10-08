"""Smart covers: find the most eye-catching frames and ask Claude for click-worthy headlines."""
import json
import subprocess
from pathlib import Path

import anthropic

from .captions import THUMB_STYLES, auto_emphasis
from .config import CLAUDE_MODEL, LANGS
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
        capture_output=True, check=True)
    size = SAMPLE_W * SAMPLE_H * 3
    scored = []
    for k in range(len(proc.stdout) // size):
        t = k / rate
        if 0.2 <= t <= length - 0.3:
            scored.append((_frame_score(proc.stdout[k * size:(k + 1) * size]), round(t, 2)))
    scored.sort(reverse=True)
    gap = length / (count * 2.5)
    picks: list[float] = []
    for _, t in scored:
        if all(abs(t - p) >= gap for p in picks):
            picks.append(t)
        if len(picks) == count:
            break
    return picks or [min(1.0, length / 2)]


HEADLINES_SCHEMA = {
    "type": "object",
    "properties": {
        "headlines": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"text": {"type": "string"}, "emphasis": {"type": "string"}},
                "required": ["text", "emphasis"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["headlines"],
    "additionalProperties": False,
}

HEADLINES_SYSTEM = """You write the text overlaid on thumbnails (covers) of short vertical videos for YouTube Shorts, TikTok and Reels.

What makes a cover get clicked:
- 2-5 words. It's read in a split second at thumbnail size.
- Open a curiosity gap or make a bold promise; don't summarise the video or give away the payoff.
- Proven patterns: a surprising number ("90% GET THIS WRONG"), a bold claim ("THIS CHANGES EVERYTHING"),
  a direct challenge ("YOU'RE DOING IT WRONG"), a short question ("WHY DO CATS PURR?"), a contrast ("CHEAP vs EXPENSIVE").
- Complement the title rather than repeating it word for word.
- No emoji, no hashtags, no quotation marks, no clickbait that the video doesn't deliver.

Return varied options using different patterns. For each, `emphasis` is the 1-2 words copied exactly from `text`
that carry the punch (the number, the surprising word); they get highlighted in a bright colour."""


def suggest_headlines(script: VideoScript, lang: str, count: int = 4,
                      client: anthropic.Anthropic | None = None) -> list[dict]:
    profile = LANGS.get(lang, LANGS["en"])
    client = client or make_client()
    brief = {
        "title": script.title,
        "hook": script.scenes[0].narration if script.scenes else "",
        "scene_headlines": [s.on_screen_text for s in script.scenes if s.on_screen_text],
        "caption": script.caption,
    }
    system = HEADLINES_SYSTEM
    if lang == "km":
        system += ("\n\nWrite in natural Khmer. Keep each headline under about 25 characters, with a normal space "
                   "between phrases so it can be broken into lines; `emphasis` is one whole space-separated phrase.")
    response = client.beta.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=2000,
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
        output_config={"effort": "low", "format": {"type": "json_schema", "schema": HEADLINES_SCHEMA}},
        system=system,
        messages=[{"role": "user", "content":
                   f"Language: {profile.name}\nWrite {count} cover headlines for this video:\n"
                   f"{json.dumps(brief, ensure_ascii=False, indent=2)}"}],
    )
    if response.stop_reason == "refusal":
        raise RuntimeError("Claude declined to suggest thumbnail headlines.")
    data = json.loads(next(b.text for b in response.content if b.type == "text"))
    return [h for h in data["headlines"] if h["text"].strip()][:count]


def basic_headlines(script: VideoScript, count: int = 4) -> list[dict]:
    """Without Claude: the title and the scene headlines, each with its strongest word highlighted."""
    seen, out = set(), []
    for text in [script.title, *(s.on_screen_text for s in script.scenes)]:
        if text.strip() and text.lower() not in seen:
            seen.add(text.lower())
            out.append({"text": text.strip(), "emphasis": auto_emphasis(text)})
    return out[:count]


def suggestions(video: Path, script: VideoScript, lang: str, count: int = 4) -> tuple[list[dict], str]:
    """Pair headlines with the best frames, rotating through the cover styles.

    Returns (suggestions, note); the note says why Claude wasn't used, if it wasn't.
    """
    note = ""
    try:
        heads = suggest_headlines(script, lang, count)
    except Exception as e:  # no key, no credits, offline...: covers still work from the script itself
        heads, note = basic_headlines(script, count), "Claude was unavailable, so these headlines come from your script."
        print(f"  ! thumbnail headlines: {type(e).__name__}: {e}")
    heads = heads or [{"text": script.title, "emphasis": auto_emphasis(script.title)}]
    frames = best_frames(video, count)
    return [{"text": h["text"], "emphasis": h["emphasis"], "style": THUMB_STYLES[i % len(THUMB_STYLES)],
             "at": frames[i % len(frames)]} for i, h in enumerate(heads)], note
