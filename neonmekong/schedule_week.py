"""Weekly posting plan: full lyric videos on Tuesday and Friday, chorus Shorts / Reels on Mon, Wed, Thu and Sat."""
from datetime import date, timedelta

FULL_DAYS = (1, 4)        # Tue, Fri  (Monday = 0)
SHORT_DAYS = (0, 2, 3, 5)  # Mon, Wed, Thu, Sat


def next_monday(today: date) -> date:
    return today + timedelta(days=(7 - today.weekday()) % 7 or 7)


def plan(titles: list[str], start: date) -> list[tuple[date, str, str]]:
    """[(day, kind, title)] for one week from the Monday `start`. Full videos go out in song order; each Short
    promotes the latest song already released that week (or the first song before any release)."""
    if not titles:
        return []
    rows, released, nxt = [], None, 0
    for offset in range(7):
        day = start + timedelta(days=offset)
        if day.weekday() in FULL_DAYS:
            released = titles[nxt % len(titles)]
            nxt += 1
            rows.append((day, "Lyric video 16:9", released))
        elif day.weekday() in SHORT_DAYS:
            rows.append((day, "Short + Reel 9:16", released or titles[0]))
    return rows


def render(rows: list[tuple[date, str, str]]) -> str:
    out = ["# Weekly schedule", "", "| Day | Post | Song |", "|---|---|---|"]
    out += [f"| {d:%a %Y-%m-%d} | {kind} | {title} |" for d, kind, title in rows]
    return "\n".join(out) + "\n"
