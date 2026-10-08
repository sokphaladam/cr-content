# cr-content — short video generator

Topic in → ready-to-post 9:16 video out (TikTok, Reels, YouTube Shorts), in English or Khmer.

```
topic → Claude script → Edge TTS voiceover → Pexels footage → FFmpeg (captions + music) → video.mp4 + post.txt
```

## Setup

```powershell
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
copy .env.example .env      # then fill in the keys
```

Requires FFmpeg on PATH. Keys:
- `ANTHROPIC_API_KEY`: Claude writes the scripts. Not needed with `--script`.
- `PIXABAY_API_KEY` (or `PEXELS_API_KEY`): free stock footage. Without one you get animated gradient backgrounds, or clips from `assets/footage/`. Pixabay key: sign up, then see https://pixabay.com/api/docs/

## Desktop app (Tauri)

The same UI in a native window. A small Rust shell (`src-tauri/`) opens the window and starts the Python engine
on a free port next to it. The engine stops when the app closes, even if the app crashes.

```powershell
npm install                  # project root, first time only (Tauri CLI); also run npm install in frontend/
npm run dev                  # desktop app with hot reload: Next.js dev server + engine from .venv
```

In dev the app uses this project folder for drafts, output and `.env`, the same as the web UI.

**Installer** (needs Rust, plus `.venv\Scripts\pip install -r requirements-build.txt`):

```powershell
npm run build                # → src-tauri\target\release\bundle\nsis\Shorts Studio_<version>_x64-setup.exe
```

This freezes the engine with PyInstaller (`scripts/build_engine.py` → `src-tauri/engine-dist/`), exports the UI to
static files (`frontend/out/`), and bundles both. The installed app keeps its data in
`%APPDATA%\com.crcontent.shorts-studio\`: `.env` (created from `.env.example` on first run, put your API keys there
and restart), `drafts/`, `output/`, `uploads/`, `cache/`, `assets/music|fonts|footage/`, and `engine.log` for
troubleshooting. FFmpeg must still be on PATH. The music-video extras (torch / stable-ts / librosa) aren't bundled,
so the installed app uses even lyric spacing and bpm-based cuts.

| Part | Where |
|---|---|
| Window, engine start/stop | `src-tauri/src/main.rs` |
| App name, window, bundle settings | `src-tauri/tauri.conf.json` (+ `tauri.bundle.json` for installer resources) |
| Engine URL in the UI | `window.__ENGINE_URL__`, set by the Rust side, read in `frontend/lib/api.ts` |

## Web UI (Next.js)

```powershell
cd frontend
npm install          # first time only
npm run dev          # starts the Python engine (:8000) and the Next.js UI (:3000)
```

Open http://localhost:3000. The UI (`frontend/`, Next.js 16 + TypeScript + Tailwind) talks to the Python
engine's API directly; `NEXT_PUBLIC_API_URL` (see `frontend/.env.example`) changes the engine address.
Edits to the UI hot-reload; edits to `crcontent/` restart the engine automatically.

| Part | Where |
|---|---|
| Page and state | `frontend/app/page.tsx` |
| Components | `frontend/components/` (CreateForm, Storyboard, SceneCard, PreviewPane, Library, TopBar) and shared `ui.tsx` (Button, Tabs, Segmented, Toast, Drawer) |
| API client and types | `frontend/lib/api.ts` |
| Theme (colours, fonts) | `frontend/app/globals.css` |

### Where things are saved (all on this PC)

| What | Folder |
|---|---|
| Drafts (scripts being edited, auto-saved ~1 s after each change) | `drafts/<id>/draft.json` |
| Rendered videos (+ script, caption, thumbnail) | `output/<date>-<lang>-<title>/` |
| Your uploaded photos/videos | `uploads/` |
| Downloaded stock footage, voice previews | `cache/` |

Drafts include scenes, backgrounds, caption, hashtags, language, voice, speed and music. New scripts and
translations become drafts immediately; opening a rendered video and editing it starts a new draft (the
video is never changed). Rendering keeps the draft, and the video's `meta.json` records which draft it came from.

## Simple web UI (no Node needed)

```powershell
.venv\Scripts\python app.py            # opens http://127.0.0.1:8000
.venv\Scripts\python app.py --reload   # dev mode: auto-restarts when you edit code
```

Write a topic, let Claude draft the script, edit scenes in the storyboard, pick voice/speed/music,
then render and watch progress live.

Each scene's background can be:
- **Auto**: footage found from the scene's search words (Pixabay/Pexels, or a gradient without a key)
- **Find footage**: search stock videos or photos and click one; **Ask Claude for ideas** suggests better search words
- **Upload video or photo**: your own clip or image (photos get a slow zoom)

**Listen** previews speech before rendering: next to the Voice picker (first scene, with the chosen voice
and speed) and on every scene (that scene's narration). Click again to stop.

**Paste a script** (on the start screen) imports a script written anywhere, e.g. from a chat assistant:
`Title:` / `[0–3s] Hook` / `Visual:` / `On-screen text:` / `Voiceover:` blocks, or any other layout. Voiceover
is kept word for word, visual notes become footage searches, emojis are removed from on-screen text, and
production tips or chat text are ignored. Claude does the conversion; without Claude a basic reader handles
the `Visual / On-screen text / Voiceover` layout. CLI: `python make.py --import script.txt`.

**Translate to ខ្មែរ / English** (top of the storyboard) rewrites the title, narration, headlines, caption
and hashtags in the other language with Claude, keeping every scene's background. Render it as a new video;
the original stays in the library.

**Thumbnail → Suggest covers** (on a rendered video) scores frames for sharpness, colour, contrast and exposure,
asks Claude for 4 short click-worthy headlines (numbers, questions, bold claims), and renders each on a top frame
in a different style (Bold / Box / Stacked) with its key word highlighted. Click one to use it, then fine-tune the
headline, highlighted word, style or frame. Without Claude the headlines come from the script. New renders also
pick the best-looking frame for the default cover automatically.

Uploads are stored in `uploads/`, downloaded stock in `cache/stock/`. Past videos are in the left sidebar (preview, copy caption, download, delete).
In VS Code: Run and Debug → **Web UI** → F5.

## Command line

```powershell
.venv\Scripts\python make.py "3 weird facts about octopuses"
.venv\Scripts\python make.py "ប្រវត្តិប្រាសាទអង្គរវត្ត" --lang km
.venv\Scripts\python make.py "why cats purr" --style "funny, for kids" --seconds 30
.venv\Scripts\python make.py "why cats purr" --script-only          # review/edit script.json first...
.venv\Scripts\python make.py --script output\<job>\script.json      # ...then render it
.venv\Scripts\python make.py --script output\<job>\script.json --to km   # translate, then render
.venv\Scripts\python make.py --batch topics.example.txt             # a month of content in one run
.venv\Scripts\python make.py --voices km                            # list voices
```

Each run creates `output/<time>-<lang>-<slug>/` with:
| File | Use |
|---|---|
| `video.mp4` | 1080×1920, H.264, ready to upload |
| `post.txt` | title, caption, hashtags to paste |
| `thumbnail.jpg` | cover: best-looking frame + headline (`suggest/` holds cover ideas from the web UI) |
| `script.json` | editable script, re-render with `--script` |

Background music: drop royalty-free `.mp3` files into `assets/music/` (one is picked at random and ducked under the voice), or pass `--music file.mp3` / `--music none`.

## Music video from your own song

Have a finished song? **New video → Music video → Use my song**: pick the mp3 (or wav/m4a/flac), paste the lyrics
(one sung line per row, `[Verse]` / `[Chorus]` headings optional), choose **16:9** (YouTube) or **9:16**, and upload.
Other `[square bracket]` lines, like `[Soft synth swell]` or `[Drums drop out]`, are sound notes: they're never shown
as lyrics, and Claude reads them when picking footage.

1. Claude reads the lyrics and picks a stock-footage search for each part of the song (without Claude: general scenery).
2. Whisper times every lyric from what's actually sung. Demucs strips the music first so the words are heard
   clearly; the song is transcribed in short overlapping chunks (one long pass often stops halfway), and the heard
   words are matched to your lyrics in order, allowing for mishearings, so a repeated chorus lines up with the
   right repeat. Lines it couldn't make out (soft, reverb-heavy singing) are aligned again on their own, between
   the lines around them, and if that fails they're taken from a forced alignment of the whole song. Lines no
   method could confirm are marked to check by ear. The result is the same every time you sync.
3. The **lyric timing** editor opens: play the song and watch the line above the player. Nudge a line with − / +,
   type its start and end (`1:23.45`), or pause where it really starts and press **Start here** / **End here**.
   Open a line's word timing to time each word (type it, or click the target while the song plays). Add a missing
   line at the playhead or after any line, delete lines (with undo), and fix the text. Changes save automatically
   (`lyrics.json` in the song's output folder).
4. **Make music video**: footage cut on the beat (tempo detected from the song), karaoke lyrics (16:9 shows the next
   line dimmed underneath), the whole song as the soundtrack. Full-length songs take several minutes.
   Optionally write a **Video idea** first ("a woman driving through neon Tokyo at night, rain on the windshield"):
   Claude plans the footage search for every section around it (without Claude, the idea's words are searched). The
   idea is remembered on the song for the next version, and each version records the idea it was made with.

Songs live under **Drafts**: their lyrics and timing stay editable. Every **Make music video** creates a new version in
its own `output/<time>-<lang>-mv-<title>/` folder, listed under the song and in **Videos**; earlier versions are kept.
A music video's **Edit lyric timing** opens the song it was made from. Deleting a song keeps its videos.

Needs the music extras below; without them the lyrics are spaced evenly and you set the timing by hand.
The first sync downloads the Whisper and Demucs models (about 2 GB, once).

## AI songs and music videos

Claude writes original lyrics, ElevenLabs Music composes and sings them, and the song becomes a vertical music video
with footage cut on the beat and karaoke lyrics. In the web UI: **New video → Make a song**, compose, then
**Make music video**. Needs `ELEVENLABS_API_KEY` in `.env` (an ElevenLabs plan with Music API access).

```powershell
.venv\Scripts\python make.py "summer love in Phnom Penh" --song --style "dreamy synth-pop" --seconds 40 --video
.venv\Scripts\python make.py "..." --song --script-only           # write lyrics only, edit song.json, then:
.venv\Scripts\python make.py --song-file output\<job>\song.json --video
.venv\Scripts\python make.py --music-video output\<job>            # (re-)render the video of a composed song
```

For accurate lyric timing and beat detection, install the optional extras (an NVIDIA GPU makes timing much faster):

```powershell
.venv\Scripts\python -m pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu124
.venv\Scripts\python -m pip install -r requirements-music.txt
```

Without them, lyrics are spread evenly over each section and cuts follow the song's bpm. Timing uses the
vocals stem, so keep "split vocals and instrumental" on when composing (your own songs are separated with Demucs). `WHISPER_MODEL` in `.env` overrides the
alignment model (default `medium` on GPU, `base` on CPU). Describe a sound, not a real singer: lyrics and styles
never name real artists, and `post.txt` notes the music is AI-generated.

## Layout

| Module | Job |
|---|---|
| `crcontent/script.py` | Claude prompt + JSON schema for hook, scenes, caption and hashtags |
| `crcontent/tts.py` | Edge TTS voiceover with word timings |
| `crcontent/visuals.py` | Pexels search/download (cached), local footage, gradient fallback |
| `crcontent/captions.py` | Word-highlight `.ass` captions and scene headlines |
| `crcontent/render.py` | FFmpeg scene clips, concat, burn-in, music ducking |
| `crcontent/lyrics.py` | Claude prompt + schema for original songs (sections, lyrics, sound) |
| `crcontent/song.py` | ElevenLabs Music: compose + vocal/instrumental stems |
| `crcontent/align.py` | Lyric timing (stable-ts forced alignment + repair of stray words, even-spacing fallback) |
| `crcontent/beats.py` | Beat detection and beat-synced shot plan |
| `crcontent/web.py` + `web/` | FastAPI backend and the browser UI |
| `crcontent/config.py` | Voices, fonts, sizes per language |

## Roadmap ideas

1. **Auto-publish**: schedule `video.mp4` + `post.txt` via Metricool / YouTube API / TikTok Content Posting API.
2. **Trend input**: pull trending topics (vidIQ, Google Trends) into `--batch` automatically.
3. **AI images**: generate a picture per scene (image-generation API) when stock footage doesn't fit.
4. **Premium voice**: ElevenLabs option for more natural or cloned voices.
5. **Templates**: per-channel brand presets (fonts, colours, logo watermark, intro/outro).
6. **Web dashboard**: queue topics, preview and edit scripts, approve before posting.
7. **Analytics loop**: feed best-performing videos back into the script prompt.
