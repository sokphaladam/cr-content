"""Scheduled uploads: a queue in <ROOT>/schedule.json that the engine works through while it runs.

Times are local wall-clock times on this computer ("2026-10-13T09:00"). If the app is closed when an upload is
due, it goes out as soon as the app is open again.

Facebook publishes scheduled posts itself, so a Facebook upload goes out EARLY: as soon as its time is within
EARLY (and at least EARLY_MARGIN away) it is uploaded with that time, and Facebook makes it public then, whether or
not this computer is on. Closer than that, it is posted at its time like the others.
"""
import json
import threading
import time
import traceback
import uuid
from datetime import datetime, timedelta
from typing import Callable

from .config import ROOT

FILE = ROOT / "schedule.json"
CHECK_SEC = 20
EARLY = {"facebook": timedelta(days=28)}  # platforms that publish at a set time themselves: how far ahead
EARLY_MARGIN = timedelta(minutes=15)  # Facebook needs 10 minutes; the upload itself takes a few
_lock = threading.Lock()
_started = False


def _load() -> list[dict]:
    try:
        return json.loads(FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []


def _save(items: list[dict]) -> None:
    FILE.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")


def parse_time(value: str) -> datetime:
    """A local time from the UI ("2026-10-13T09:00"); any timezone suffix is converted to local time."""
    at = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    if at.tzinfo:
        at = at.astimezone().replace(tzinfo=None)
    return at.replace(second=0, microsecond=0)


def items(video: str = "") -> list[dict]:
    """Upcoming uploads first (soonest first), then finished ones (newest first). Queued comments aren't listed."""
    all_items = [i for i in _load() if (not video or i["video"] == video) and i.get("action", "upload") == "upload"]
    pending = sorted((i for i in all_items if i["status"] in ("scheduled", "uploading")), key=lambda i: i["at"])
    rest = sorted((i for i in all_items if i["status"] not in ("scheduled", "uploading")), key=lambda i: i["at"], reverse=True)
    return pending + rest[:50]


def add(video: str, platform: str, at: datetime, source: str = "manual", action: str = "upload",
        channel: str = "", privacy: str = "") -> dict:
    """Queue an upload (or, action "comment", the YouTube comment of a video that goes public later).
    `channel`: the YouTube channel id ("" = the default channel when it runs). `privacy`: the visibility it is posted
    with (a TikTok privacy level; "" = the platform's setting when it runs)."""
    item = {"id": uuid.uuid4().hex[:10], "video": video, "platform": platform, "action": action, "channel": channel,
            "privacy": privacy,
            "at": at.isoformat(timespec="minutes"), "status": "scheduled", "source": source,
            "created": datetime.now().isoformat(timespec="seconds"), "url": "", "error": "", "tries": 0}
    with _lock:
        data = _load()
        data.append(item)
        _save(data)
    return item


def cancel(item_id: str) -> bool:
    with _lock:
        data = _load()
        keep = [i for i in data if not (i["id"] == item_id and i["status"] == "scheduled")]
        _save(keep)
        return len(keep) != len(data)


def forget_video(video: str) -> None:
    """A deleted video can't be uploaded: drop its pending uploads."""
    with _lock:
        _save([i for i in _load() if not (i["video"] == video and i["status"] == "scheduled")])


def mark(item_id: str, **fields) -> None:
    with _lock:
        data = _load()
        for i in data:
            if i["id"] == item_id:
                i.update(fields)
        _save(data)


def next_slot(platform: str, times: list[str], after: datetime | None = None) -> datetime:
    """The next posting time (from the daily `times`, "HH:MM") that no other upload to `platform` has taken."""
    after = (after or datetime.now()) + timedelta(minutes=2)
    # (done counts too: an early Facebook upload is done long before its time)
    taken = {i["at"] for i in _load() if i["platform"] == platform and i["status"] in ("scheduled", "uploading", "done")
             and i.get("action", "upload") == "upload"}
    slots = sorted(t for t in times if len(t) == 5) or ["09:00"]
    day = after.date()
    for _ in range(366):
        for t in slots:
            at = datetime.combine(day, datetime.strptime(t, "%H:%M").time())
            if at > after and at.isoformat(timespec="minutes") not in taken:
                return at
        day += timedelta(days=1)
    return after


def goes_early(item: dict, now: datetime) -> bool:
    """Can this queued upload be handed now to a platform that publishes it at its time itself (EARLY)?"""
    early = EARLY.get(item["platform"]) if item.get("action", "upload") == "upload" else None
    at = datetime.fromisoformat(item["at"])
    return bool(early) and now + EARLY_MARGIN <= at <= now + early


def start(run: Callable[[dict], None]) -> None:
    """Check the queue every CHECK_SEC seconds and hand each due upload to `run` (once)."""
    global _started
    if _started:
        return
    _started = True
    with _lock:  # the engine stopped mid-upload last time: try those again
        data = _load()
        for i in data:
            if i["status"] == "uploading":
                i["status"] = "scheduled"
        _save(data)

    def loop() -> None:
        while True:
            try:
                now = datetime.now().replace(second=0, microsecond=0)
                with _lock:
                    data = _load()
                    waiting = [i for i in data if i["status"] == "scheduled"]
                    due = [i for i in waiting if i["at"] <= now.isoformat(timespec="minutes")]
                    if not due and not any(i["status"] == "uploading" for i in data):
                        # nothing else to send: one early upload per check, so they never hold up one that's due
                        due = sorted((i for i in waiting if goes_early(i, now)), key=lambda i: i["at"])[:1]
                    for i in due:
                        i["status"] = "uploading"
                    if due:
                        _save(data)
                for item in due:
                    run(item)
            except Exception:
                traceback.print_exc()
            time.sleep(CHECK_SEC)

    threading.Thread(target=loop, daemon=True, name="upload-schedule").start()
