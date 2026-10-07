"""Turn a pasted, free-form script (e.g. from a chat assistant) into a VideoScript.

Claude handles any layout; a basic parser covers the common
"[0–3s] Hook / Visual: / On-screen text: / Voiceover:" layout when Claude isn't available.
"""
import json
import re

import anthropic

from .config import CLAUDE_MODEL, LANGS
from .script import KHMER_NOTE, SCHEMA, Scene, VideoScript, make_client

KHMER_CHARS = re.compile(r"[ក-៿]")
# emoji & pictographs: the caption fonts can't draw them, they'd render as empty boxes
EMOJI = re.compile(
    "[\U0001F000-\U0001FAFF\U00002600-\U000027BF\U00002B00-\U00002BFF\U0001F1E6-\U0001F1FF"
    "\U0000FE0F\U0000200D\U000020E3]+"
)
STOPWORDS = set("""close a an the of to and or with on in at by for from into onto then simple animation appearing
appear each its it is are be being close-up closeup shot shots camera staring scene showing shows show while
that this these those very like as up down out over under some more most almost just""".split())


def strip_emoji(text: str) -> str:
    return re.sub(r"\s{2,}", " ", EMOJI.sub("", text)).strip()


def detect_lang(text: str) -> str:
    return "km" if len(KHMER_CHARS.findall(text)) > 20 else "en"


IMPORT_SYSTEM = """You convert a pasted script for a short vertical video (TikTok / Reels / Shorts) into structured scenes.

Rules:
- One output scene per scene/section/beat in the input, in order. Ignore production tips, timing notes, and any chat
  text that is not part of the script (e.g. "Want me to translate this?").
- narration: the exact voiceover words. Do not rewrite, shorten, or translate them. If a scene has no voiceover, use
  its on-screen text as the narration.
- visual_query: 2-4 concrete ENGLISH words a stock footage site would have, based on the scene's visual description
  (e.g. "Close-up of an octopus eye staring at the camera" -> "octopus eye closeup"). Never describe animations,
  icons or text overlays; pick the real-world subject instead.
- on_screen_text: the scene's on-screen text without emojis, or "" if none.
- title: the script's title, or a short catchy one if missing.
- caption: the post caption if the script has one; otherwise write a 1-2 sentence caption in the script's language
  that ends with a question.
- hashtags: from the script if present, otherwise 5-8 fitting tags; no # sign."""


def import_with_claude(text: str, lang: str, client: anthropic.Anthropic | None = None) -> VideoScript:
    client = client or make_client()
    system = IMPORT_SYSTEM + (
        "\n- The script is in Khmer. You may add normal spaces between phrases (every 2-5 words) so captions can be "
        "timed, but do not change any words." if lang == "km" else ""
    )
    response = client.beta.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=16000,
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
        output_config={"effort": "low", "format": {"type": "json_schema", "schema": SCHEMA}},
        system=system,
        messages=[{"role": "user", "content": f"Script language: {LANGS[lang].name}\n\n<script>\n{text}\n</script>"}],
    )
    if response.stop_reason == "refusal":
        raise RuntimeError("Claude declined to convert this script.")
    if response.stop_reason == "max_tokens":
        raise RuntimeError("The script is too long to convert in one go; split it into parts.")
    data = json.loads(next(b.text for b in response.content if b.type == "text"))
    return _clean(VideoScript.model_validate(data))


# ---------- Basic parser (no Claude needed) ----------

FIELD = re.compile(r"^\s*(?:[-*•]\s*)?\**\s*(visual|b-?roll|footage|on[- ]?screen(?: text)?|text overlay|text|"
                   r"voice ?over|vo|narration|script|caption|hashtags?|title)\s*\**\s*[:：]\s*(.*)$", re.I)
SECTION = re.compile(r"^\s*(?:\[[^\]]*\]|\(?\d{1,2}[:.]?\d{0,2}\s*[–-]\s*\d{1,2}[:.]?\d{0,2}\s*s?\)?|#+\s|scene\s*\d+|"
                     r"\*\*\s*\[)", re.I)
END_MARKERS = re.compile(r"^\s*(production tips|notes?|tips|want me to|would you like|let me know)\b", re.I)


def _keywords(visual: str) -> str:
    words = re.findall(r"[A-Za-z]+", visual.lower())
    picked = [w for w in words if w not in STOPWORDS and len(w) > 2]
    return " ".join(list(dict.fromkeys(picked))[:3])  # first 3 distinct content words


def parse_basic(text: str) -> VideoScript:
    title, caption, hashtags = "", "", []
    scenes: list[dict] = []
    current: dict | None = None
    last_field = None

    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        if END_MARKERS.match(line):
            break
        m = FIELD.match(line)
        if m:
            key, value = m.group(1).lower().replace("-", " "), m.group(2).strip().strip('"“”')
            if key == "title":
                title = value
                continue
            if key == "caption":
                caption = value
                continue
            if key.startswith("hashtag"):
                hashtags = [h.lstrip("#") for h in re.split(r"[\s,]+", value) if h.strip("#")]
                continue
            if current is None:
                current = {"narration": "", "visual": "", "text": ""}
                scenes.append(current)
            field = ("visual" if key in ("visual", "b roll", "broll", "footage")
                     else "text" if key.startswith(("on", "text")) else "narration")
            if current[field] and field == "narration":  # a second voiceover line means a new scene
                current = {"narration": "", "visual": "", "text": ""}
                scenes.append(current)
            current[field] = (current[field] + " " + value).strip()
            last_field = field
            continue
        if SECTION.match(line):
            current = {"narration": "", "visual": "", "text": ""}
            scenes.append(current)
            last_field = None
            continue
        if current is not None and last_field:  # continuation line of the previous field
            current[last_field] = (current[last_field] + " " + line.strip('"“”')).strip()

    scenes = [s for s in scenes if s["narration"] or s["text"]]
    if not scenes:
        raise ValueError("Couldn't find any scenes. Label lines with “Voiceover:”, “Visual:” and “On-screen text:”, "
                         "or connect Claude to import scripts in any format.")
    return _clean(VideoScript(
        title=title or strip_emoji(scenes[0]["text"]) or "Imported script",
        scenes=[Scene(narration=s["narration"].strip('"“”') or strip_emoji(s["text"]),
                      visual_query=_keywords(s["visual"]) or "abstract background",
                      on_screen_text=s["text"]) for s in scenes],
        caption=caption,
        hashtags=hashtags,
    ))


def _clean(script: VideoScript) -> VideoScript:
    for s in script.scenes:
        s.on_screen_text = strip_emoji(s.on_screen_text)
        s.narration = strip_emoji(s.narration)
    script.title = strip_emoji(script.title)
    script.hashtags = [h.lstrip("#").replace(" ", "") for h in script.hashtags if h.strip("#")]
    return script


def import_script(text: str, lang: str = "auto", use_claude: bool = True) -> tuple[VideoScript, str, str]:
    """Returns (script, lang, method) where method is "claude" or "basic"."""
    text = text.strip()
    if not text:
        raise ValueError("Paste a script first.")
    lang = detect_lang(text) if lang not in LANGS else lang
    if use_claude:
        try:
            return import_with_claude(text, lang), lang, "claude"
        except (anthropic.APIError, RuntimeError):
            pass  # fall back to the basic parser below
    return parse_basic(text), lang, "basic"
