"""Step 6 — AI judge (optional, "ai_judge" in highlights.json): Gemini ranks the top candidates by hook strength.

Each candidate goes as its lyrics plus a few frames of its 9:16 window; Gemini returns, per candidate, its rank, why,
an on-screen hook (max 8 words) and the upload text: a hook-first title, the description's opening line and
question, hashtags and a pinned comment. The key comes from GEMINI_API_KEY (.env or the
environment), like every other Gemini call in the app.
"""
import base64
import json
from pathlib import Path

from ..config import LLM_MODEL, LANGS
from .visual import frames

SYSTEM = """You are a short-form music editor who picks which 15-30 second section of a song to post as a YouTube
Short / Instagram Reel. You judge hook strength: does the clip grab a scrolling viewer in its first 2 seconds (a
memorable, singable line or a beat drop right away), is it the part people would remember and replay, does the
picture look good, does it end on a satisfying line so it loops well. Be concrete and honest in your reasons: name
the line or moment that makes it work or not. Never name or compare to real artists.

For each clip you also write what goes with it when it's posted. A scrolling viewer reacts to a feeling or a
situation, not to a song name or a section label, so:
- hook_text: on-screen text for the first seconds, max 8 words: a teaser that makes people stay (a POV, a situation,
  a feeling), not the lyric itself.
- title: max 45 characters, the feeling or situation first ("When she only wants a trial run"), 0-2 emoji at the
  end. Not the song's name (it's added after it), no hashtags, no "#shorts", no section labels.
- line: the description's first line: the same feeling in other words (title and description show together).
- question: one short question that's easy to answer, to get comments ("Have you ever been someone's test drive?").
- hashtags: 5-8 without the # sign: the song's name as one tag, the artist as one tag (when known), 2-3 genre or mood
  tags and 1-2 broad music tags. Never shorts, fyp, viral, foryou or trending.
- comment: the pinned comment, a playful question or prompt that gets replies, under 100 characters.
Everything must fit the song; no claims about the artist or how the music was made."""

SCHEMA = {
    "type": "object",
    "properties": {
        "ranking": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "candidate": {"type": "integer", "description": "the candidate's number"},
                    "rank": {"type": "integer", "description": "1 = strongest hook"},
                    "reason": {"type": "string", "description": "1-2 sentences: why this rank"},
                    "hook_text": {"type": "string", "description": "on-screen hook text, max 8 words"},
                    "title": {"type": "string", "description": "upload title, the feeling first, max 45 characters"},
                    "line": {"type": "string", "description": "description line 1, worded differently from the title"},
                    "question": {"type": "string", "description": "an easy question that gets comments"},
                    "hashtags": {"type": "array", "items": {"type": "string"}},
                    "comment": {"type": "string", "description": "pinned comment that invites replies"},
                },
                "required": ["candidate", "rank", "reason", "hook_text", "title", "line", "question", "hashtags",
                             "comment"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["ranking"],
    "additionalProperties": False,
}


def _jpegs(video: Path, size: tuple[int, int], start: float, end: float, count: int) -> list[str]:
    import cv2

    length = end - start
    out = []
    for _, bgr in frames(video, size, count / length, start, length, 360, 640):
        ok, buf = cv2.imencode(".jpg", bgr, [cv2.IMWRITE_JPEG_QUALITY, 82])
        if ok:
            out.append(base64.b64encode(buf.tobytes()).decode())
    return out[:count]


def _clock(t: float) -> str:
    return f"{int(t // 60)}:{t % 60:05.2f}"


def rank(cands: list, video: Path, size: tuple[int, int], title: str, artist: str, lang: str, cfg: dict,
         about: str = "", log=print) -> list[dict] | None:
    """Gemini's ranking of `cands` ({candidate, rank, reason, hook_text, title, line, question, hashtags, comment,
    caption} each, by candidate index into
    `cands`), or None when Gemini isn't available (no key, offline, declined): the score ranking then stands."""
    from ..script import make_client

    n_frames = cfg["ai_judge"]["frames"]
    content: list[dict] = []
    for k, c in enumerate(cands, 1):
        content.append({"type": "text", "text": (
            f"Candidate {k}: {_clock(c.start)}-{_clock(c.end)} ({c.length:.1f} s), {c.section or c.kind}.\n"
            f"Lyrics sung in it:\n" + "\n".join(f"  {line}" for line in c.lyrics) +
            f"\nFrames from its first second to its last ({n_frames}):")})
        for data in _jpegs(video, size, c.start, c.end, n_frames):
            content.append({"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": data}})
    language = LANGS.get(lang, LANGS["en"]).name
    content.append({"type": "text", "text": (
        f"Song: \"{title}\"" + (f" by {artist}" if artist else "") + (f" ({about})" if about else "") + ".\n"
        f"Rank all {len(cands)} candidates by hook strength for a Short / Reel (1 = post this one). For each give "
        f"the reason, the hook text and the upload text (title, line, question, hashtags, comment). Write the hook "
        f"text and the upload text in {language}.")})
    try:
        response = make_client().beta.messages.create(
            model=LLM_MODEL,
            max_tokens=4000,
            output_config={"effort": "medium", "format": {"type": "json_schema", "schema": SCHEMA}},
            system=SYSTEM,
            messages=[{"role": "user", "content": content}],
        )
    except Exception as e:  # no key, no credits, offline: the scores alone still rank the clips
        log(f"      ! AI judge unavailable ({e.__class__.__name__}: {str(e)[:160]}); using the score ranking")
        return None
    if response.stop_reason == "refusal":
        log("      ! Gemini declined to judge the clips; using the score ranking")
        return None
    data = json.loads(next(b.text for b in response.content if b.type == "text"))
    out = []
    for r in data["ranking"]:
        k = r["candidate"] - 1
        if 0 <= k < len(cands) and all(o["candidate"] != k for o in out):
            words = r["hook_text"].split()
            tags = [t.lstrip("#").replace(" ", "") for t in r["hashtags"] if t.strip("# ")]
            tags = [t for t in tags if t.lower() not in ("shorts", "short", "fyp", "viral", "foryou", "trending")]
            line, question = r["line"].strip(), r["question"].strip()
            out.append({"candidate": k, "rank": r["rank"], "reason": r["reason"].strip(),
                        "hook_text": " ".join(words[:8]), "title": r["title"].strip(), "line": line,
                        "question": question, "hashtags": tags[:8], "comment": r["comment"].strip(),
                        "caption": "\n".join(t for t in (line, question) if t)})
    return sorted(out, key=lambda o: o["rank"])
