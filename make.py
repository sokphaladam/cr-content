"""CLI: generate ready-to-post vertical short videos.

Examples:
  python make.py "3 weird facts about octopuses"
  python make.py "ប្រវត្តិប្រាសាទអង្គរវត្ត" --lang km
  python make.py --script examples/octopus.en.json
  python make.py --batch topics.txt --lang en
  python make.py --script output/<job>/script.json --to km   (translate, then render)
  python make.py --import examples/pasted-octopus.txt      (any pasted script format)
  python make.py --voices km
  python make.py "summer love in Phnom Penh" --song --style "dreamy synth-pop" --seconds 40
  python make.py --song-file output/<job>/song.json          (re-compose an edited song)
  python make.py "..." --song --video                          (song + karaoke music video)
  python make.py --music-video output/<job>                    (music video from a composed song)
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
    p.add_argument("--scenes", type=int, default=6)
    p.add_argument("--seconds", type=int, default=45, help="target video length")
    p.add_argument("--style", default="", help="extra direction for the script, e.g. 'funny, for teenagers'")
    p.add_argument("--rate", default="+5%", help="speech speed, e.g. +10%% or -5%%")
    p.add_argument("--music", help="mp3 path, or 'none' (default: random file from assets/music)")
    p.add_argument("--script", type=Path, help="render from an existing script.json (no Claude call)")
    p.add_argument("--import", dest="import_file", type=Path, metavar="TXT",
                   help="pasted script in any format (Title/Visual/On-screen text/Voiceover...) to convert and render")
    p.add_argument("--to", choices=sorted(LANGS), help="translate --script into this language before rendering")
    p.add_argument("--script-only", action="store_true", help="only write the script, to review/edit first")
    p.add_argument("--batch", type=Path, help="text file with one topic per line")
    p.add_argument("--voices", metavar="PREFIX", help="list available voices, e.g. 'km' or 'en-US'")
    p.add_argument("--song", action="store_true",
                   help="write and compose an original AI song about the topic (ElevenLabs Music)")
    p.add_argument("--song-file", type=Path, metavar="JSON", help="compose from an existing song.json (no Claude call)")
    p.add_argument("--vocal", default="", help="singer voice for --song, e.g. 'breathy female pop vocal'")
    p.add_argument("--no-stems", action="store_true", help="skip vocal/instrumental stem separation")
    p.add_argument("--video", action="store_true", help="with --song/--song-file: also render the music video")
    p.add_argument("--music-video", type=Path, metavar="JOB_DIR",
                   help="render a music video from an already composed song folder (output/<job>)")
    args = p.parse_args()

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


if __name__ == "__main__":
    raise SystemExit(main())
