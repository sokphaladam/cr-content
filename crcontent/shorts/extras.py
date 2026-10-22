"""What goes up with a Short: the cover frame and the metadata.

cover.png: the sharpest, most colourful frame of the animal (from the text-free picture, work/joined.mp4: never a
card, never the loop tail), with the title in big type inside the safe zone (highlights.covers.render_cover, which
shapes Khmer and keeps clear of the subject). thumbnail.jpg is the same cover for the app's Upload card.
metadata.txt: title, description, hashtags and pinned comment, ready to paste into YouTube Studio; post.txt is the
app's own upload text (title line, description, #tags).
"""
from pathlib import Path

from ..highlights.covers import render_cover, score_frame
from ..highlights.visual import frames
from ..importer import strip_emoji
from ..longform.timing import Timeline
from ..pipeline import post_body
from .footage import PLACEHOLDERS

SIZE = (1080, 1920)
SAMPLES_PER_SECOND = 3


def cover_score(bgr) -> dict:
    """An animal cover's frame: sharp and colourful first (no face weighting: covers.score_frame looks for people),
    with contrast, and neither dark nor blown out."""
    f = score_frame(bgr)
    p = f["parts"]
    bright = float(bgr.mean() / 255)
    exposure = max(0.0, 1 - abs(bright - 0.5) / 0.42)
    f["score"] = round((0.45 * p["sharpness"] + 0.35 * p["colour"] + 0.2 * p["contrast"]) * (0.6 + 0.4 * exposure), 4)
    return f


def best_cover_frame(picture: Path, tl: Timeline, entries: list[dict], tail: float) -> dict:
    """{t, score, subject, ...} of the best frame in the beats that show footage of the animal."""
    rows = []
    for entry, slot in zip(entries, tl.slots):
        if entry["chosen"]["source"] in PLACEHOLDERS:
            continue
        end = min(slot.end, tl.total - tail) - 0.15
        start = slot.start + 0.15
        if end - start < 0.3:
            continue
        for t, bgr in frames(picture, SIZE, SAMPLES_PER_SECOND, start, end - start, 540, 960):
            rows.append({"t": round(t, 2), "beat": entry["scene"], **cover_score(bgr)})
    if not rows:  # every beat is a card: the middle of the video
        return {"t": tl.total / 2, "beat": 0, "score": 0.0, "subject": (0.5, 0.5), "face": None}
    return max(rows, key=lambda r: r["score"])


def make_cover(job: Path, title: str, tl: Timeline, entries: list[dict], tail: float) -> dict:
    """job/cover.png and job/thumbnail.jpg; returns the frame used."""
    from PIL import Image

    picture = job / "work" / "joined.mp4"
    best = best_cover_frame(picture, tl, entries, tail)
    out = job / "cover.png"
    render_cover(picture, SIZE, best["t"], strip_emoji(title), "", out, best["subject"], best["face"])
    Image.open(out).convert("RGB").save(job / "thumbnail.jpg", quality=92)
    return {k: best[k] for k in ("t", "beat", "score")}


def metadata(ep) -> str:
    tags = " ".join(f"#{t}" for t in ep.hashtags)
    return (f"TITLE\n{ep.title}\n\nDESCRIPTION\n{ep.description}\n\n{tags}\n\nHASHTAGS\n{tags}\n\n"
            f"PINNED COMMENT\n{ep.pinned_comment}\n")


def write(job: Path, ep, tl: Timeline, entries: list[dict], made: dict, log=print) -> dict:
    """cover.png, thumbnail.jpg, metadata.txt and post.txt; returns the cover frame used."""
    cover = make_cover(job, ep.title, tl, entries, made["tail"])
    log(f"      cover: beat {cover['beat']} at {cover['t']:.1f}s -> cover.png")
    (job / "metadata.txt").write_text(metadata(ep), encoding="utf-8")
    tags = " ".join(f"#{t}" for t in ep.hashtags)
    (job / "post.txt").write_text(post_body(ep.title, ep.description, tags, (made.get("music") or [None])[0]),
                                  encoding="utf-8")
    return cover
