"""Neon Mekong pipeline: python make_song.py [--dry-run] <step> songs/<slug>

Steps are added one at a time; `init` parses suno.txt into song.json.
"""
import argparse
import json
import sys
from pathlib import Path

from neonmekong import config, songjson, suno


def cmd_init(args) -> int:
    folder = Path(args.song)
    src = folder / "suno.txt"
    if not src.exists():
        print(f"missing {src}")
        return 1
    data = songjson.from_suno(suno.parse(src.read_text(encoding="utf-8")), slug=folder.name)
    try:
        kept = songjson.save(folder / "song.json", data, force=args.force)
    except FileExistsError as e:
        print(e)
        return 1
    if kept:
        print(f"backed up old song.json -> {kept.name}")
    print(f"wrote {folder / 'song.json'}")
    for w in songjson.warnings(data):
        print(f"WARNING: {w}")
    return 0


def cmd_analyze(args) -> int:
    from neonmekong import analyze
    folder = Path(args.song)
    src = folder / "suno.txt"
    if not src.exists():
        print(f"missing {src}")
        return 1
    try:
        data, notes = analyze.run(folder, suno.parse(src.read_text(encoding="utf-8")),
                                  separate=not getattr(args, "no_separate", False))
    except FileNotFoundError as e:
        print(e)
        return 1
    shown = {**data, "beat_times": f"[{len(data['beat_times'])} beats, first {data['beat_times'][:3]}]"}
    print(json.dumps(shown, indent=2, ensure_ascii=False))
    print(f"wrote {folder / 'lyrics.lrc'} and {folder / 'song.json'} (edit song.json before rendering)")
    for w in notes:
        print(f"WARNING: {w}")
    return 0


def _load(folder: Path):
    src, sj = folder / "suno.txt", folder / "song.json"
    if not src.exists() or not sj.exists():
        print(f"need {src.name} and {sj.name} in {folder} (run init / analyze first)")
        return None
    return suno.parse(src.read_text(encoding="utf-8")), songjson.load(sj)


def _write(path: Path, text: str) -> None:
    kept = songjson.backup(path)
    path.write_text(text, encoding="utf-8")
    print(f"wrote {path}" + (f" (old one kept as {kept.name})" if kept else ""))


def cmd_text(args) -> int:
    from neonmekong import ai, uploadtext
    folder = Path(args.song)
    loaded = _load(folder)
    if not loaded:
        return 1
    s, data = loaded
    chorus = next((sec.lines for sec in s.sections if sec.kind == "chorus"), [])
    try:
        extra = ai.generate(folder, data, chorus, args.ai, refresh=args.refresh, model=args.model)
    except Exception as e:  # network, missing key, bad reply: fall back to the free template
        print(f"WARNING: --ai {args.ai} failed ({e.__class__.__name__}: {e}); using the template text")
        extra = {}
    _write(folder / "upload.txt", uploadtext.render(uploadtext.build(data, s, extra)))
    return 0


def cmd_checklist(args) -> int:
    from neonmekong import uploadtext
    folder = Path(args.song)
    loaded = _load(folder)
    if not loaded:
        return 1
    _write(folder / "checklist.md", uploadtext.checklist(loaded[1]))
    return 0


def cmd_thumbnail(args) -> int:
    from neonmekong import thumbnail
    folder = Path(args.song)
    sj = folder / "song.json"
    if not sj.exists():
        print(f"missing {sj} (run init / analyze first)")
        return 1
    out = thumbnail.render(songjson.load(sj), folder / "out" / "thumbnail.jpg")
    size = out.stat().st_size
    print(f"wrote {out} ({thumbnail.W}x{thumbnail.H}, {size // 1024} KB)")
    if size > thumbnail.MAX_BYTES:
        print("WARNING: over YouTube's 2 MB thumbnail limit")
    return 0


def cmd_hook(args) -> int:
    from neonmekong import hook
    try:
        hook.run(Path(args.song), force=True)
    except (FileNotFoundError, RuntimeError) as e:
        print(e)
        return 1
    return 0


def cmd_video(args) -> int:
    from neonmekong import hook, lyricvideo
    folder = Path(args.song)
    sj = folder / "song.json"
    if not sj.exists() or not (folder / "lyrics.lrc").exists():
        print(f"need song.json and lyrics.lrc in {folder} (run analyze first)")
        return 1
    data = songjson.load(sj)
    # one video, the song as it is (original music from the first second); trim / preview only when asked for
    options = ["full"] if args.hook in ("auto", "both") else [args.hook]
    if any(o in ("trim", "preview") for o in options):
        hook.run(folder, force=True)
    draft = args.draft or args.dry_run
    try:
        for option in options:
            out = lyricvideo.render(folder, option, seconds=args.seconds, draft=draft)
            print(f"wrote {out}")
    except (FileNotFoundError, RuntimeError) as e:
        print(e)
        return 1
    return 0


def cmd_instrumental(args) -> int:
    from neonmekong import lyricvideo
    folder = Path(args.song)
    inst = next((folder / n for n in ("instrumental.wav", "instrumental.mp3") if (folder / n).exists()), None)
    if not inst:
        print("no instrumental.wav in the song folder: skipping the instrumental version")
        return 0
    if not (folder / "song.json").exists() or not (folder / "lyrics.lrc").exists():
        print(f"need song.json and lyrics.lrc in {folder} (run analyze first)")
        return 1
    try:
        out = lyricvideo.render(folder, "full", seconds=args.seconds, draft=args.draft or args.dry_run,
                                show_lyrics=False, name="instrumental.mp4", audio=inst)
    except (FileNotFoundError, RuntimeError) as e:
        print(e)
        return 1
    print(f"wrote {out}")
    return 0


def cmd_all(args) -> int:
    """The whole pipeline for one song. Stops after analyze (first time) so you can edit song.json."""
    folder = Path(args.song)
    if not (folder / "suno.txt").exists():
        print(f"missing {folder / 'suno.txt'}")
        return 1

    def run(fn, **kw) -> int:
        return fn(argparse.Namespace(song=args.song, dry_run=args.dry_run, **kw))

    sj = folder / "song.json"
    if not sj.exists() and run(cmd_init, force=False):
        return 1
    if not (songjson.load(sj).get("bpm") and (folder / "lyrics.lrc").exists()) or args.reanalyze:
        print("== analyze")
        if run(cmd_analyze, no_separate=args.no_separate):
            return 1
        if not args.go:
            print(f"\nReview and edit {sj}, then run the same command again to continue "
                  "(or add --go to skip this pause).")
            return 0
    steps = [("text", cmd_text, dict(ai=args.ai, model=args.model, refresh=args.refresh)),
             ("checklist", cmd_checklist, {}), ("thumbnail", cmd_thumbnail, {})]
    if not args.no_video:
        steps += [("video", cmd_video, dict(hook=args.hook, seconds=args.seconds, draft=args.draft)),
                  ("short", cmd_short, dict(seconds=args.seconds, draft=args.draft)),
                  ("instrumental", cmd_instrumental, dict(seconds=args.seconds, draft=args.draft))]
    for name, fn, kw in steps:
        print(f"== {name}")
        if run(fn, **kw):
            print(f"stopped at: {name}")
            return 1
    print(f"\nDone. Outputs are in {folder / 'out'} plus upload.txt and checklist.md in {folder}.")
    return 0


def cmd_short(args) -> int:
    from neonmekong import short
    folder = Path(args.song)
    if not (folder / "song.json").exists() or not (folder / "lyrics.lrc").exists():
        print(f"need song.json and lyrics.lrc in {folder} (run analyze first)")
        return 1
    try:
        out = short.run(folder, seconds=args.seconds, draft=args.draft or args.dry_run)
    except (FileNotFoundError, RuntimeError, ValueError) as e:
        print(e)
        return 1
    print(f"wrote {out}")
    return 0


def cmd_schedule(args) -> int:
    from datetime import date
    from neonmekong import schedule_week
    titles = []
    for f in args.songs:
        sj = Path(f) / "song.json"
        titles.append(songjson.load(sj)["title"] if sj.exists() else Path(f).name)
    start = date.fromisoformat(args.start) if args.start else schedule_week.next_monday(date.today())
    out = Path(args.out) / f"schedule-{start}.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    _write(out, schedule_week.render(schedule_week.plan(titles, start)))
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="make_song.py")
    p.add_argument("--dry-run", action="store_true", help="no network, no AI; mock data from tests/fixtures/")
    sub = p.add_subparsers(dest="step", required=True)
    s = sub.add_parser("init", help="parse suno.txt into song.json")
    s.add_argument("song", help="songs/<slug>")
    s.add_argument("--force", action="store_true", help="replace song.json (old one is backed up)")
    s.set_defaults(fn=cmd_init)
    a = sub.add_parser("analyze", help="time the lyrics, find bpm/beats/chorus, fill song.json")
    a.add_argument("song", help="songs/<slug>")
    a.add_argument("--no-separate", action="store_true",
                   help="do not split the vocals off with Demucs when there is no vocals.wav (less accurate)")
    a.set_defaults(fn=cmd_analyze)
    t = sub.add_parser("text", help="write upload.txt (title, description, tags, pinned comment, playlist)")
    t.add_argument("song", help="songs/<slug>")
    t.add_argument("--ai", choices=("template", "local", "gemini"), default="template",
                   help="template = free fixed text (default); local = Ollama; gemini = Google Gemini (free tier)")
    t.add_argument("--model", help="override the Ollama / Claude model")
    t.add_argument("--refresh", action="store_true", help="ask the AI again instead of using ai_cache.json")
    t.set_defaults(fn=cmd_text)
    c = sub.add_parser("checklist", help="write checklist.md")
    c.add_argument("song", help="songs/<slug>")
    c.set_defaults(fn=cmd_checklist)
    n = sub.add_parser("thumbnail", help="write out/thumbnail.jpg (1280x720)")
    n.add_argument("song", help="songs/<slug>")
    n.set_defaults(fn=cmd_thumbnail)
    h = sub.add_parser("hook", help="hook-first edit: the trim and chorus-preview audio and lyrics")
    h.add_argument("song", help="songs/<slug>")
    h.add_argument("--force", action="store_true", help="kept for old scripts: the edit is always made")
    h.set_defaults(fn=cmd_hook)
    v = sub.add_parser("video", help="render the 16:9 lyric video (out/lyric_<option>.mp4)")
    v.add_argument("song", help="songs/<slug>")
    v.add_argument("--hook", choices=("auto", "both", "full", "trim", "preview"), default="auto",
                   help="auto (default): the one full video with the original music; trim / preview: the hook-first edits")
    v.add_argument("--seconds", type=float, help="render only the first N seconds (for a quick test)")
    v.add_argument("--draft", action="store_true", help="half size, 15 fps, fast encode (always on with --dry-run)")
    v.set_defaults(fn=cmd_video)
    sh = sub.add_parser("short", help="render the 9:16 chorus Short / Reel (out/short_chorus.mp4)")
    sh.add_argument("song", help="songs/<slug>")
    sh.add_argument("--seconds", type=float, help="render only the first N seconds (for a quick test)")
    sh.add_argument("--draft", action="store_true", help="half size, 15 fps, fast encode (always on with --dry-run)")
    sh.set_defaults(fn=cmd_short)
    i = sub.add_parser("instrumental", help="same visuals without lyrics, from instrumental.wav (out/instrumental.mp4)")
    i.add_argument("song", help="songs/<slug>")
    i.add_argument("--seconds", type=float, help="render only the first N seconds (for a quick test)")
    i.add_argument("--draft", action="store_true", help="half size, 15 fps, fast encode (always on with --dry-run)")
    i.set_defaults(fn=cmd_instrumental)
    al = sub.add_parser("all", help="the whole pipeline for one song (also: make_song.py songs/<slug>)")
    al.add_argument("song", help="songs/<slug>")
    al.add_argument("--ai", choices=("template", "local", "gemini"), default="template")
    al.add_argument("--model")
    al.add_argument("--refresh", action="store_true")
    al.add_argument("--hook", choices=("auto", "both", "full", "trim", "preview"), default="auto")
    al.add_argument("--seconds", type=float)
    al.add_argument("--draft", action="store_true")
    al.add_argument("--no-video", action="store_true", help="only the text, checklist and thumbnail")
    al.add_argument("--no-separate", action="store_true", help="skip the Demucs vocal split before lyric timing")
    al.add_argument("--go", action="store_true", help="do not pause after analyze for you to edit song.json")
    al.add_argument("--reanalyze", action="store_true", help="run analyze again (keeps your edits, backs up song.json)")
    al.set_defaults(fn=cmd_all)
    w = sub.add_parser("schedule", help="weekly posting plan for the given songs")
    w.add_argument("songs", nargs="+", help="songs/<slug> folders, in release order")
    w.add_argument("--start", help="a Monday, YYYY-MM-DD (default: next Monday)")
    w.add_argument("--out", default="songs", help="folder for schedule-<date>.md")
    w.set_defaults(fn=cmd_schedule)
    argv = list(sys.argv[1:] if argv is None else argv)
    first = next((i for i, a in enumerate(argv) if not a.startswith("-")), None)
    if first is not None and argv[first] not in sub.choices:   # make_song.py songs/<slug>  ==  ... all songs/<slug>
        argv.insert(first, "all")
    args = p.parse_args(argv)
    config.set_dry_run(args.dry_run)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
