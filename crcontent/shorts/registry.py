"""Which stock clips other Shorts already use, so episodes don't look alike.

Read from the Shorts in the output folder each time (their footage.json and dates), so it can't drift: deleting a
Short frees its clips. A Short counts from its render (video.mp4), or from when its pre-flight was built while it's
pending. Other versions of the same episode (re-runs of one plan row) don't count against each other, and your own
media is never held back.

Rules: a clip any other Short uses (as anything) is never a hook; any other beat avoids clips used in the last
RECENT_DAYS days, and when only such a clip will do, the report flags it.
"""
import json
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

RECENT_DAYS = 14
STOCK_SKIP = ("own", "card", "placeholder")


@dataclass
class Use:
    key: str
    ep: int
    slug: str        # the episode it's in (plan + Ep): versions of one episode share it
    beat: int
    hook: bool
    when: datetime
    rendered: bool
    job: str

    def label(self) -> str:
        return (f"Ep {self.ep} {'hook' if self.hook else f'beat {self.beat}'} "
                f"({'rendered' if self.rendered else 'pending'} {self.when:%b %d})")


def clip_key(item: dict) -> str:
    """A clip's identity across Shorts (the same file is the same clip, whichever beat or query found it)."""
    return f"{item.get('source')}-{item.get('kind')}-{item.get('id', '')}"


def uses(output: Path, exclude_slug: str = "") -> dict[str, list[Use]]:
    """{clip key: [Use]} for every stock clip in the Shorts in `output`, other than episode `exclude_slug`'s."""
    out: dict[str, list[Use]] = {}
    for job in sorted(p for p in output.iterdir() if p.is_dir()):
        try:
            meta = json.loads((job / "meta.json").read_text(encoding="utf-8"))
            if meta.get("kind") != "short":
                continue
            slug = json.loads((job / "episode.json").read_text(encoding="utf-8"))["script"]["slug"]
            entries = json.loads((job / "footage.json").read_text(encoding="utf-8"))
        except (OSError, ValueError, KeyError):
            continue  # a job still being built, or an older one without these files
        if slug == exclude_slug:
            continue
        video = job / "video.mp4"
        rendered = video.exists()
        when = datetime.fromtimestamp(video.stat().st_mtime) if rendered else \
            datetime.fromisoformat(meta.get("created") or datetime.fromtimestamp(job.stat().st_mtime).isoformat())
        for e in entries:
            c = e.get("chosen") or {}
            if c.get("source") in STOCK_SKIP or not c.get("source"):
                continue
            out.setdefault(clip_key(c), []).append(
                Use(clip_key(c), int(meta.get("ep") or 0), slug, e["scene"], e["scene"] == 1, when, rendered, job.name))
    return out


class Registry:
    """The clips other Shorts use, with the rules for this episode."""

    def __init__(self, output: Path, slug: str, now: datetime | None = None):
        self.used = uses(output, slug)
        self.now = now or datetime.now()

    def hook_block(self, item: dict) -> str:
        """Why `item` can't be a hook ("" when it can): any other Short already uses it."""
        found = self.used.get(clip_key(item))
        return f"already used in {found[0].label()}" if found else ""

    def recent(self, item: dict) -> list[Use]:
        """The other Shorts that used `item` in the last RECENT_DAYS days."""
        since = self.now - timedelta(days=RECENT_DAYS)
        return [u for u in self.used.get(clip_key(item), []) if u.when >= since]
