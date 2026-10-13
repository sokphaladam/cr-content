"""Fact-check notes from a content plan (its Fact Check sheet): the sources line for the description and a pinned
comment that shares the notes with viewers."""
import re

# a note that cites something: an author list, a year in brackets, a journal, a university, a link or a DOI
_CITES = re.compile(r"\bet al\b|\(\d{4}\)|https?://|\bdoi\b|\bjournal\b|\buniversity\b|\breports\b", re.I)
_LEAD = re.compile(r"^(based on|source[s]?:|from|according to)\s+", re.I)


def sources_line(notes: list[str]) -> str:
    """The cited works in `notes`, for a "Sources:" line: each citing note's first sentence, without "Based on"."""
    found = []
    for note in notes:
        if not _CITES.search(note):
            continue
        # first sentence; "et al. (2020)" isn't a sentence end because "(" follows it, not a capital letter
        first = re.split(r"(?<=[.!?])\s+(?=[A-Z])", note.strip())[0]
        found.append(_LEAD.sub("", first).rstrip(". "))
    return "; ".join(dict.fromkeys(f for f in found if f))


def pinned_comment(notes: list[str]) -> str:
    """A comment to pin under the video: the notes as a short list (the sheet's column is "Note for comments")."""
    notes = [n.strip() for n in notes if n.strip()]
    if not notes:
        return ""
    return "📌 Fact check & sources:\n" + "\n".join(f"• {n}" for n in notes)
