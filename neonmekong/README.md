# Neon Mekong song pipeline

One Suno song in; out come a hook-first 16:9 lyric video, a 9:16 chorus Short / Reel, a 1280x720 thumbnail,
`upload.txt` and `checklist.md`. Runs on this PC (ffmpeg + OpenCV + stable-ts). No Suno login or API is used.

## Install once (Windows)

- Python 3.11 (the project's `.venv` is 3.11.9) and ffmpeg + ffprobe on PATH.
- NVIDIA driver + CUDA build of torch (RTX 3060 12 GB is plenty):
  ```powershell
  .venv\Scripts\python -m pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu124
  .venv\Scripts\python -m pip install -r requirements.txt -r requirements-music.txt -r requirements-highlights.txt -r requirements-neonmekong.txt
  ```
  The first lyric alignment downloads the Whisper model (about 1.5 GB, once).
- Optional: [Ollama](https://ollama.com) + `ollama pull qwen2.5:7b-instruct` for `--ai local`.
- Optional: put `GEMINI_API_KEY=...` in the project `.env` for `--ai gemini` (never needed otherwise).

## Folder layout

```
brand/                  optional, shared: logo.png, fonts/*.ttf (a bold font), used by thumbnails and videos
songs/<song-slug>/
  audio.wav|mp3         from Suno (required)
  vocals.wav            optional stem: lyric timing is more accurate with it
  instrumental.wav      optional stem: gives the instrumental video
  suno.txt              you paste this (format below)
  song.json             made by the tool, you edit it
  lyrics.lrc  upload.txt  checklist.md
  out/                  thumbnail.jpg, lyric_full.mp4, short_chorus.mp4,
                        instrumental.mp4, hook/ (hook audio + timing)
```

In the app (the Lyrics tab) songs live in the `songs` folder of the data folder chosen in Settings > Storage, and
move with it. The command line works on any `songs/<slug>` path you give it, so from a shell use that folder, e.g.
`python make_song.py E:\ShortStudio\songs\<slug>`.

Anything the tool rewrites is first kept as `<name>.bak-<time>`. Nothing is overwritten silently.

## suno.txt

```
Title: Slow Motion City
Style: nu-disco, dreamy, female vocal      (the Suno style prompt; the genre is picked from it)
Plan: Premier                              (Pro or Premier; only paid-plan songs can be monetized)
Generated: 2026-10-01

[Verse 1]
first lyric line
...
[Chorus]
...
```
The tags `[Verse] [Chorus] [Bridge] [Intro] [Outro] [Pre-Chorus]` are used; other `[bracketed notes]` are ignored.

## Make a song (Suno download to upload)

1. Download `audio` (and the stems if you have them) from Suno into `songs/<slug>/`; paste `suno.txt`.
2. `python make_song.py songs/<slug>`. First run: it times the lyrics, measures bpm / beats / energy, fills
   `song.json`, then **stops** so you can edit it.
3. Open `song.json`: set `plan` and `generated_on` (warned if missing), check `genre`, `mood_phrase`, `scene_theme`,
   `palette`, `subscribe_line` and the `chorus` start/end. Check `lyrics.lrc` by ear if a warning says so.
4. Run the same command again (or add `--go` to never pause). It writes the text, checklist, thumbnail and videos.
   If the first vocal is after 10 s you get two videos to compare: `lyric_trim.mp4` (starts just before the vocal)
   and `lyric_preview.mp4` (8 s chorus preview, then the song). Keep one.
5. Open `upload.txt` and `checklist.md`. Replace the two link placeholders (subscribe, playlist) in the description.
6. Upload in YouTube Studio: the chosen lyric video + `thumbnail.jpg`, paste title / description / tags, add to the
   playlist named in `upload.txt`, set the end screen (best video left, Subscribe right, in the last 20 s), pin the
   comment, answer the AI-disclosure question. Post `short_chorus.mp4` as a Short (Related video = the full song)
   and as a Reel.
7. `python make_song.py schedule songs/a songs/b ...` gives the week: lyric videos Tue + Fri, Shorts / Reels
   Mon, Wed, Thu, Sat.

## One command per step

| Command | Does |
|---|---|
| `init songs/<slug>` | `suno.txt` -> `song.json` (never overwrites; `--force` backs up first) |
| `analyze songs/<slug>` | lyric timing (stable-ts on `vocals.wav`, else the mix), bpm, beats, energy, chorus, `lyrics.lrc` |
| `text songs/<slug> [--ai template\|local\|gemini] [--refresh]` | `upload.txt` |
| `checklist songs/<slug>` | `checklist.md` |
| `thumbnail songs/<slug>` | `out/thumbnail.jpg` |
| `hook songs/<slug>` | optional hook-first edits (trim / chorus preview); `video --hook trim\|preview` makes them |
| `video songs/<slug> [--hook auto\|full\|trim\|preview]` | 16:9 lyric video(s) |
| `short songs/<slug>` | 9:16 chorus Short / Reel |
| `instrumental songs/<slug>` | same visuals, no lyrics, from `instrumental.wav` |
| `schedule songs/a songs/b [--start YYYY-MM-DD]` | weekly posting plan |
| `songs/<slug>` (or `all`) | everything above, in order |

Add `--dry-run` before the command to test without audio, network or AI (draft-size silent videos, mock data from
`tests/fixtures/`). `--draft` renders half size / 15 fps; `--seconds N` renders only the first N seconds.
Run the tests: `python -m pytest tests -k neonmekong`.

## Upload text and AI

Default is free fixed templates: no AI, no network. `--ai local` asks Ollama on this PC. `--ai gemini` makes one small
call to Google Gemini (Flash-Lite has a free tier). Put these lines in the project `.env` (system environment
variables are never read):

```
# key from Google AI Studio (aistudio.google.com)
GEMINI_API_KEY=paste-your-key-here
# optional: the default is a rolling alias that Google keeps current
GEMINI_MODEL=gemini-flash-lite-latest
```

The AI writes only the one-line hook and the pinned-comment question; the title, tags, description and lyrics always
come from the templates. Results are cached in `ai_cache.json` and never requested again unless `--refresh`.
If an AI call fails the template text is used.

## What the videos contain

- 16:9, 1920x1080, 30 fps: slow zoom / pan over a neon city on a river, shimmering river, drifting particles,
  a pulse on the real beat times, large lyrics (chorus lines bigger with a glow), the channel badge in the same corner,
  a title card for the first 5 s, a small subscribe pill for 4 s after the first chorus, and in the last 20 s the lyrics
  move up so the bottom half is clean for the end screen.
- 9:16 Short, 1080x1920: starts on the chorus with the first lyric already on screen, double-size lyrics, no title card.
  15 to 58 s long.
- Thumbnail: same background style, big mood phrase, song title, badge. Same layout for every song.

## Troubleshooting

- `ffmpeg` not found: install it and reopen the terminal.
- Lyrics out of sync: edit `lyrics.lrc` (`[mm:ss.xx]text` per line), then run `video` again. Adding `vocals.wav` helps.
- Wrong chorus in the Short: fix `chorus.start` / `chorus.end` in `song.json`.
- Re-running `analyze` keeps the fields you edited (title, mood phrase, palette, plan ...) and replaces the measured
  ones (bpm, beats, chorus, sections).
