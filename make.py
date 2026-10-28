"""CLI: generate ready-to-post vertical short videos.

Examples:
  python make.py "3 weird facts about octopuses"
  python make.py "ប្រវត្តិប្រាសាទអង្គរវត្ត" --lang km
  python make.py --script examples/octopus.en.json
  python make.py --batch topics.txt --lang en
  python make.py --excel plan.xlsx                           (one video per episode of a content plan)
  python make.py --excel plan.xlsx --eps 1,3-5 --script-only
  python make.py --script output/<job>/script.json --to km   (translate, then render)
  python make.py --import examples/pasted-octopus.txt      (any pasted script format)
  python make.py --voices km
  python make.py "summer love in Phnom Penh" --song --style "dreamy synth-pop" --seconds 40
  python make.py --song-file output/<job>/song.json          (re-compose an edited song)
  python make.py "..." --song --video                          (song + karaoke music video)
  python make.py --music-video output/<job>                    (music video from a composed song)
  python make.py --highlights output/<mv job>                  (best 15-30 s clips + covers + report)
  python make.py --highlights song.mp4 --lyrics lyrics.txt --title "..." --artist "..."
  python make.py --script-video scripts/smartest-birds.md    (long YouTube video: stops at the storyboard)
  python make.py --storyboard output/<job>                   (check / swap footage / approve in the browser)
  python make.py --approve output/<job>                      (approve the storyboard as it is and render)
  python make.py --shorts plan.xlsx --eps 1                  (Shorts Mode: stops at the pre-flight report)
  python make.py --approve output/<short job>                (render an approved Short)
  python make.py --shorts-analytics "Table data.csv" --plan plan.xlsx   (which hooks keep viewers)
"""
import argparse
import sys
from pathlib import Path

from dotenv import load_dotenv

from crcontent.config import LANGS


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    load_dotenv()
    p = argparse.ArgumentParser(description="Generate short vertical videos for TikTok / Reels / Shorts.")
    p.add_argument("topic", nargs="?", help="what the video is about")
    p.add_argument("--lang", choices=sorted(LANGS), default="en")
    p.add_argument("--voice", help="Edge TTS voice name (see --voices)")
    p.add_argument("--scenes", type=int, default=4)
    p.add_argument("--seconds", type=int, default=20, help="target video length (short ones get watched to the end)")
    p.add_argument("--style", default="", help="extra direction for the script, e.g. 'funny, for teenagers'")
    p.add_argument("--rate", default="+5%", help="speech speed, e.g. +10%% or -5%%")
    p.add_argument("--music", help="mp3 path, or 'none' (default: random file from assets/music)")
    p.add_argument("--script", type=Path, help="render from an existing script.json (no Gemini call)")
    p.add_argument("--import", dest="import_file", type=Path, metavar="TXT",
                   help="pasted script in any format (Title/Visual/On-screen text/Voiceover...) to convert and render")
    p.add_argument("--to", choices=sorted(LANGS), help="translate --script into this language before rendering")
    p.add_argument("--script-only", action="store_true", help="only write the script, to review/edit first")
    p.add_argument("--batch", type=Path, help="text file with one topic per line")
    p.add_argument("--excel", type=Path, metavar="XLSX",
                   help="content plan workbook: one video per episode from its Scripts sheet (see crcontent/sheet.py)")
    p.add_argument("--eps", default="", help="with --excel: episodes to make, e.g. 1,3-5 (default: all not Posted)")
    p.add_argument("--voices", metavar="PREFIX", help="list available voices, e.g. 'km' or 'en-US'")
    p.add_argument("--song", action="store_true",
                   help="write and compose an original AI song about the topic (ElevenLabs Music)")
    p.add_argument("--song-file", type=Path, metavar="JSON", help="compose from an existing song.json (no Gemini call)")
    p.add_argument("--vocal", default="", help="singer voice for --song, e.g. 'breathy female pop vocal'")
    p.add_argument("--no-stems", action="store_true", help="skip vocal/instrumental stem separation")
    p.add_argument("--video", action="store_true", help="with --song/--song-file: also render the music video")
    p.add_argument("--music-video", type=Path, metavar="JOB_DIR",
                   help="render a music video from an already composed song folder (output/<job>)")
    p.add_argument("--highlights", type=Path, metavar="JOB_OR_VIDEO",
                   help="Smart Highlights: pick the best 15-30 s Shorts/Reels clips of a finished video (output/<job> "
                        "or an mp4), with covers and a report (see crcontent/highlights)")
    p.add_argument("--lyrics", type=Path, metavar="TXT", help="with --highlights on a plain video: its lyrics text")
    p.add_argument("--title", default="", help="with --highlights: song title (default: from song.json)")
    p.add_argument("--artist", default="", help="with --highlights: artist name for the covers and captions")
    p.add_argument("--no-render", action="store_true", help="with --highlights: analyse, rank and report only")
    p.add_argument("--no-judge", action="store_true", help="with --highlights: skip the Gemini judge this time")
    p.add_argument("--script-video", type=Path, metavar="MD",
                   help="Script to Video: a 1920x1080 YouTube video from a script .md (voiceover, timing, footage), "
                        "up to the storyboard to approve (see crcontent/longform)")
    p.add_argument("--storyboard", type=Path, metavar="JOB_DIR",
                   help="open a Script to Video storyboard in the browser to swap footage and approve the render")
    p.add_argument("--approve", type=Path, metavar="JOB_DIR",
                   help="approve a Script to Video storyboard as it is now and render it")
    p.add_argument("--port", type=int, default=8000, help="with --storyboard: the engine's port")
    p.add_argument("--shorts", type=Path, metavar="XLSX",
                   help="Shorts Mode: a 1080x1920 Short per episode of a content plan, held to the channel's rules; "
                        "stops at the pre-flight report (see crcontent/shorts)")
    p.add_argument("--shorts-analytics", type=Path, metavar="CSV",
                   help="import a YouTube Studio 'Content' export and summarise which hook styles keep viewers")
    p.add_argument("--plan", type=Path, metavar="XLSX", help="with --shorts-analytics: the plan to match videos to")
    args = p.parse_args()

    if args.shorts or args.shorts_analytics or (args.approve and _is_short(args.approve)):
        from crcontent.config import ROOT
        load_dotenv(ROOT / ".env")  # the app's keys live in the data folder
        return shorts_mode(args)

    if args.script_video or args.storyboard or args.approve:
        from crcontent.config import ROOT
        load_dotenv(ROOT / ".env")  # the app's keys live in the data folder
        from crcontent import longform
        if args.script_video:
            longform.make_storyboard(args.script_video)
            return 0
        if args.approve:
            from crcontent.longform import storyboard
            storyboard.approve(args.approve.resolve())
            longform.render_video(args.approve.resolve())
            return 0
        return open_storyboard(args.storyboard.resolve(), args.port)

    if args.highlights:
        from crcontent.config import ROOT
        from crcontent.highlights import make_highlights
        load_dotenv(ROOT / ".env")  # the app's keys live in the data folder
        make_highlights(args.highlights, args.lyrics, args.title, args.artist,
                        args.lang if "--lang" in sys.argv else "", render=not args.no_render,
                        ai_judge=False if args.no_judge else None)
        return 0

    if args.music_video:
        from crcontent.pipeline import make_music_video
        make_music_video(args.music_video)
        return 0

    if args.voices:
        from crcontent.tts import list_voices
        print("\n".join(list_voices(args.voices)))
        return 0

    if args.song or args.song_file:
        if not args.topic and not args.song_file:
            p.error("--song needs a topic (or use --song-file JSON)")
        from crcontent.pipeline import make_music_video, make_song
        mix = make_song(args.topic, song_path=args.song_file, lang=args.lang, seconds=args.seconds, style=args.style,
                        vocal=args.vocal, stems=not args.no_stems, script_only=args.script_only)
        if args.video and not args.script_only:
            make_music_video(mix.parent)
        return 0

    from crcontent.pipeline import make_video
    common = dict(lang=args.lang, voice=args.voice, scenes=args.scenes, seconds=args.seconds,
                  style=args.style, music=args.music, rate=args.rate, script_only=args.script_only)

    if args.excel:
        return make_from_excel(args.excel, args.eps, common)

    if args.batch:
        topics = [t.strip() for t in args.batch.read_text(encoding="utf-8").splitlines()
                  if t.strip() and not t.startswith("#")]
        failed = []
        for i, topic in enumerate(topics, 1):
            print(f"\n=== {i}/{len(topics)}: {topic} ===")
            try:
                make_video(topic, **common)
            except Exception as e:  # keep the batch going; report at the end
                print(f"  ! failed: {e}")
                failed.append(topic)
        print(f"\nBatch done: {len(topics) - len(failed)} ok, {len(failed)} failed")
        for t in failed:
            print(f"  - {t}")
        return 1 if failed else 0

    if args.import_file:
        from crcontent.importer import import_script
        script, lang, method = import_script(args.import_file.read_text(encoding="utf-8"))
        print(f"Imported {len(script.scenes)} scenes ({LANGS[lang].name}, {method} reader): {script.title}")
        common.update(lang=lang)
        make_video(args.topic, script=script, **common)
        return 0
    if not args.topic and not args.script:
        p.error("give a topic, --script FILE, --import TXT, or --batch FILE")
    if args.to:
        if not args.script:
            p.error("--to needs --script FILE (the script to translate)")
        from crcontent.script import VideoScript, translate_script
        print(f"Translating {args.script} -> {LANGS[args.to].name}")
        translated = translate_script(VideoScript.load(args.script), args.to)
        common.update(lang=args.to)
        make_video(args.topic, script=translated, **common)
        return 0
    make_video(args.topic, script_path=args.script, **common)
    return 0


def open_storyboard(job: Path, port: int) -> int:
    """The storyboard page from the engine (started here unless the app's engine is already running)."""
    import threading
    import webbrowser
    from urllib.parse import quote

    import requests

    from crcontent.config import OUTPUT_DIR
    if job.parent.resolve() != OUTPUT_DIR.resolve() or not (job / "storyboard.html").exists():
        print(f"No storyboard in {job} (it must be a folder in {OUTPUT_DIR} made by --script-video).")
        return 1
    url = f"http://127.0.0.1:{port}/media/{quote(job.name)}/storyboard.html"
    try:
        requests.get(f"http://127.0.0.1:{port}/api/options", timeout=2).raise_for_status()
        print(f"Opening {url} (the engine is already running)")
        webbrowser.open(url)
        return 0
    except requests.RequestException:
        pass
    import uvicorn

    from crcontent.web import app
    print(f"Storyboard: {url}")
    print("Approve it there to render; Ctrl+C here when you're done.")
    threading.Timer(2.0, webbrowser.open, [url]).start()
    uvicorn.run(app, host="127.0.0.1", port=port, timeout_graceful_shutdown=3)
    return 0


def _is_short(job: Path) -> bool:
    from crcontent.shorts import is_short

    return is_short(job)


def shorts_mode(args) -> int:
    """--shorts (steps 1-5 per episode, up to the pre-flight report), --approve on a Short, --shorts-analytics."""
    from crcontent import shorts
    from crcontent.sheet import pick_episodes
    from crcontent.shorts import analytics, plan

    if args.approve:
        from crcontent.longform import storyboard
        storyboard.approve(args.approve.resolve())
        shorts.render_job(args.approve.resolve())
        return 0
    if args.shorts_analytics:
        episodes = plan.read(args.plan) if args.plan else []
        data = analytics.import_csv(args.shorts_analytics, episodes)
        print(analytics.report(data))
        print(f"\nSaved to {analytics.PATH} (the pre-flight judge ranks its hook suggestions by it)")
        return 0
    episodes = pick_episodes(plan.read(args.shorts), args.eps)
    print(f"{args.shorts.name}: {len(episodes)} episode(s)")
    jobs, failed = [], []
    for i, ep in enumerate(episodes, 1):
        print(f"\n=== {i}/{len(episodes)}: Ep {ep.ep} - {ep.title} ===")
        try:
            jobs.append(shorts.make_job(ep))
        except Exception as err:  # keep going; report at the end
            print(f"  ! failed: {type(err).__name__}: {err}")
            failed.append(ep.ep)
    print(f"\nPre-flight built for {len(jobs)} episode(s)" + (f", {len(failed)} failed ({failed})" if failed else ""))
    for job in jobs:
        st = shorts.report_status(job)
        print(f"  [{st.get('state', '?').upper()}] {job / 'preflight.html'}\n    python make.py --approve \"{job}\"")
    return 1 if failed else 0


def make_from_excel(path: Path, eps: str, common: dict) -> int:
    from crcontent.sheet import pick_episodes, plan_all, read_plan, render_episode

    episodes = pick_episodes(read_plan(path), eps)
    print(f"{path.name}: {len(episodes)} episode(s) to make")
    plan_all(episodes)
    common = {k: v for k, v in common.items() if k != "lang"}  # each episode's language comes from its voiceover
    failed = []
    for i, e in enumerate(episodes, 1):
        print(f"\n=== {i}/{len(episodes)}: Ep {e.ep} - {e.script.title} ({len(e.script.scenes)} scenes) ===")
        try:
            render_episode(e, **common)
        except Exception as err:  # keep going; report at the end
            print(f"  ! failed: {err}")
            failed.append(e.ep)
    print(f"\nExcel done: {len(episodes) - len(failed)} ok, {len(failed)} failed"
          + (f" (episodes {', '.join(map(str, failed))})" if failed else ""))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
