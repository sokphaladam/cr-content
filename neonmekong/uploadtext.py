"""upload.txt (title, description, tags, pinned comment, playlist) and checklist.md, from song.json."""
from . import config
from .suno import Suno

SUBSCRIBE_URL = "https://www.youtube.com/@YOUR_CHANNEL?sub_confirmation=1"  # placeholder: replace once
PLAYLIST_URL = "https://www.youtube.com/playlist?list=YOUR_PLAYLIST_ID"      # placeholder: replace per playlist

HOOKS = {
    "nu-disco": "A nostalgic nu-disco love song for dancing alone in the kitchen at midnight.",
    "psych-pop": "A dreamy psych-pop float through hazy colours and soft synths.",
    "psych-rock": "A trippy night-drive psych-rock song with a chorus that sticks.",
    "late-night": "A late-night love song for walking home when the city goes quiet.",
}
QUESTIONS = {
    "nu-disco": "Which line of the chorus got stuck in your head? Tell me where you'd dance to this.",
    "psych-pop": "What colour does this song feel like to you?",
    "psych-rock": "Where would you play this on a night drive?",
    "late-night": "What time of night are you listening? Where are you right now?",
}
GENRE_TAGS = {
    "nu-disco": ["nu-disco", "nu disco", "disco love songs", "retro disco", "nostalgic music"],
    "psych-pop": ["psych-pop", "psychedelic pop", "dreamy pop", "dream pop"],
    "psych-rock": ["psych-rock", "psychedelic rock", "night drive music", "trippy rock"],
    "late-night": ["late night music", "night walk music", "love songs", "chill vibes"],
}
BASE_TAGS = ["neon mekong", "official lyric video", "lyric video", "new music", "ai music", "suno"]


def title_of(data: dict, ai: dict) -> str:
    """Mood-first title from the template (the AI never writes it: the pattern is fixed on purpose)."""
    mood = data["mood_phrase"] or data["title"]
    mood = mood if mood.lower().rstrip("s").endswith("song") else f"{mood} Song"
    return f"{mood} – {data['title']} (Lyric Video)"[:100]


def tags_of(data: dict) -> list[str]:
    tags = [data["title"].lower(), data["mood_phrase"].lower(), *GENRE_TAGS.get(data["genre"], []), *BASE_TAGS]
    out, size = [], 0
    for t in dict.fromkeys(x for x in tags if x):
        if size + len(t) + 1 > 450:  # YouTube allows 500 characters in total
            break
        out.append(t)
        size += len(t) + 1
    return out


def hashtags_of(data: dict) -> str:
    g = "".join(p.title() for p in data["genre"].split("-")) if data["genre"] else "NewMusic"
    return f"#NeonMekong #{g} #LyricVideo"


def lyrics_block(s: Suno) -> str:
    return "\n\n".join(f"[{sec.tag}]\n" + "\n".join(sec.lines) for sec in s.sections if sec.lines)


def build(data: dict, s: Suno, ai: dict | None = None) -> dict:
    ai = ai or {}
    hook = ai.get("hook") or HOOKS.get(data["genre"], f"{data['mood_phrase']}: a new song from {config.CHANNEL}.")
    links = [f"Subscribe for new songs: {SUBSCRIBE_URL}"]
    if data["playlist"]:
        links.append(f"More like this: {data['playlist']} {PLAYLIST_URL}")
    links.append(f"Instagram: {config.INSTAGRAM}")
    desc = "\n".join([hook, "", *links, "", "Lyrics", lyrics_block(s), "",
                      f"Music created with AI (Suno). Official lyric video by {config.CHANNEL}.", "",
                      hashtags_of(data)])
    return {
        "title": title_of(data, ai),
        "description": desc,
        "tags": tags_of(data),
        "pinned_comment": ai.get("pinned_comment") or QUESTIONS.get(data["genre"], "Which line is your favourite?"),
        "playlist": data["playlist"] or "(set genre in song.json to pick a playlist)",
        "short_title": f"{data['title']} – chorus ({data['mood_phrase']}) #Shorts"[:100],
    }


def render(b: dict) -> str:
    return "\n".join([
        "TITLE", b["title"], "",
        "DESCRIPTION", b["description"], "",
        "TAGS", ", ".join(b["tags"]), "",
        "PINNED COMMENT", b["pinned_comment"], "",
        "ADD TO PLAYLIST", b["playlist"], "",
        "SHORT / REEL TITLE", b["short_title"], "",
    ])


def checklist(data: dict) -> str:
    hook = ("Video opens on the hook within 10s (vocals start at "
            f"{data['vocal_start']:.0f}s: use the trimmed or chorus-preview version)"
            if (data.get("vocal_start") or 0) > 10 else "Video opens on the hook within 10s")
    items = [
        hook,
        "Title, description and tags pasted from upload.txt (replace the subscribe and playlist link placeholders)",
        "Thumbnail uploaded (from the template)",
        f"Added to playlist: {data['playlist'] or '(set genre first)'}",
        "End screen: best video (left) + Subscribe button (right)",
        "Branding watermark on",
        "AI disclosure set where it applies (altered / synthetic content question in YouTube Studio)",
        "Comment pinned (question from upload.txt)",
        "Short posted, with Related video linked to the full song",
        "Reel posted (same 9:16 file)",
    ]
    if not data.get("plan") or not data.get("generated_on"):
        items.insert(0, "Set plan and generated_on in song.json (only songs made on a paid Suno plan can be monetized)")
    return f"# Upload checklist: {data['title']}\n\n" + "\n".join(f"- [ ] {i}" for i in items) + "\n"
