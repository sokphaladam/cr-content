# cr-content — short video generator

Topic in → ready-to-post 9:16 video out (TikTok, Reels, YouTube Shorts), in English or Khmer.

```
topic → Claude script → Edge TTS voiceover → Pexels footage → FFmpeg (captions + music) → video.mp4 + post.txt
```

## Setup

```powershell
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
```

Requires FFmpeg on PATH. In the app, open **Settings** (bottom of the left rail) to add or replace these keys;
they're saved to `.env` in the data folder (created from `.env.example` on first run) and apply right away. Keys:
- `ANTHROPIC_API_KEY`: Claude writes the scripts. Not needed with `--script`.
- `PIXABAY_API_KEY` (or `PEXELS_API_KEY`): free stock footage. Without one you get animated gradient backgrounds, or clips from `assets/footage/`. Pixabay key: sign up, then see https://pixabay.com/api/docs/

## Desktop app (Tauri)

The same UI in a native window. A small Rust shell (`src-tauri/`) opens the window and starts the Python engine
on a free port next to it. The engine stops when the app closes, even if the app crashes.

```powershell
npm install                  # project root, first time only (Tauri CLI); also run npm install in frontend/
npm run dev                  # desktop app with hot reload: Next.js dev server + engine from .venv
```

**Where files are kept.** Dev runs, the web UI, `make.py` and the installed app all share one library, set in
**Settings → Storage** (`crcontent/locations.py`, remembered in `%APPDATA%\com.crcontent.shorts-studio\locations.json`):
- *Data folder* (default `Documents\Shorts Studio`, or `%USERPROFILE%\Shorts Studio` when Documents is synced by
  OneDrive): `.env`, `accounts.json`, `schedule.json`, `drafts/`, `uploads/`, `cache/`, `campaigns/`,
  `assets/music|fonts|footage/`.
- *Finished videos* (default `output/` in the data folder, or any folder of yours).

Changing either one in Settings moves the files there and restarts the engine. The first run gathers the data that
earlier versions kept in the project folder and in `%APPDATA%\com.crcontent.shorts-studio\`. `CRCONTENT_DATA_DIR`
overrides the data folder (tests, a second library).

**Installer** (needs Rust, plus `.venv\Scripts\pip install -r requirements-build.txt`):

```powershell
npm run build                # → src-tauri\target\release\bundle\nsis\Shorts Studio_<version>_x64-setup.exe
```

This freezes the engine with PyInstaller (`scripts/build_engine.py` → `src-tauri/engine-dist/`), downloads FFmpeg
(`scripts/fetch_ffmpeg.py` → `src-tauri/ffmpeg-dist/`), exports the UI to static files (`frontend/out/`), and bundles
all three. The installed app writes `engine.log` (for troubleshooting) to
`%APPDATA%\com.crcontent.shorts-studio\`; its library is in the folders above. The music-video extras (torch / stable-ts / librosa) aren't bundled,
so the installed app uses even lyric spacing and bpm-based cuts.

| Part | Where |
|---|---|
| Window, engine start/stop | `src-tauri/src/main.rs` |
| App name, window, bundle settings | `src-tauri/tauri.conf.json` (+ `tauri.bundle.json` for installer resources) |
| Engine URL in the UI | `window.__ENGINE_URL__`, set by the Rust side, read in `frontend/lib/api.ts` |

### macOS

Same steps, with macOS paths:

```bash
brew install ffmpeg python
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt -r requirements-build.txt
npm install && (cd frontend && npm install)
npm run dev                  # desktop app with hot reload
npm run build                # → src-tauri/target/release/bundle/macos/Shorts Studio.app and bundle/dmg/*.dmg
```

On a Mac the library defaults to `~/Documents/Shorts Studio`, the app's own folder (`locations.json`, `engine.log`)
is `~/Library/Application Support/com.crcontent.shorts-studio/`, the tray icon is in the menu bar, **Open at Login**
adds a LaunchAgent (`~/Library/LaunchAgents/com.crcontent.shorts-studio.plist`), and a click on the Dock icon
reopens a closed window. The app adds Homebrew's folders to the engine's PATH so it finds FFmpeg. Caption fonts
come from the macOS system fonts (Khmer uses Khmer Sangam MN unless you add Khmer OS fonts to `assets/fonts`).
The build is unsigned: the first time, right-click the app → Open. **Settings → AI scene art → Install AI add-on**
(~1.5 GB) adds scene art (Stable Diffusion XL on the Mac's GPU through Metal), Whisper lyric timing, beat detection and
vocal separation: into `.venv` in dev runs, or into `<data folder>/addons/ai` (a portable Python) in the installed app;
no restart needed. Scene art needs Apple Silicon (M1 or newer; 16 GB+ memory recommended, 8 GB works but swaps and is
slow); an Intel Mac gets the music extras only (~1 GB).

### Releases on GitHub (Windows and macOS installers)

`.github/workflows/release.yml` builds the installers on GitHub's machines and attaches them to a release:

```bash
git tag v0.2.0
git push origin v0.2.0     # → Actions builds Windows, macOS Apple Silicon and macOS Intel (about 15–25 min)
```

The tag sets the app's version (`v0.2.0` → 0.2.0). The release is created as a **draft**: check it under
**Releases**, then press **Publish**. **Actions → Release → Run workflow** builds the same installers as
downloadable artifacts without making a release (to try a build first).

Each installer bundles the frozen engine and FFmpeg (`scripts/fetch_ffmpeg.py`: gyan.dev on Windows,
martin-riedl.de on macOS, both with libass), so people only install the app. `npm run build` bundles FFmpeg the same
way locally. The builds aren't code-signed yet: Windows SmartScreen asks to confirm (**More info → Run anyway**), and
macOS asks once (**System Settings → Privacy & Security → Open Anyway**); the release notes say so. Signing later
needs an Apple Developer ID (notarization) and a Windows code-signing certificate, added as repository secrets.

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
- **Auto**: footage found from the scene's search words (Pixabay/Pexels); when none is found, Claude draws the scene
  (gradient only when Claude is unavailable too)
- **Find footage**: search stock videos or photos and click one; **Ask Claude for ideas** suggests better search words;
  **Design with Claude** draws an original background from the search words and narration (no text, calm middle
  band for the captions, slow zoom like a photo; cached in `cache/art/`); **Animate** has Claude design a moving
  background instead (drifting light, particles, parallax) that becomes a seamless 6-second looping clip, about two
  minutes
- **Upload video or photo**: your own clip or image (photos get a slow zoom)

**Listen** previews speech before rendering: next to the Voice picker (first scene, with the chosen voice
and speed) and on every scene (that scene's narration). Click again to stop.

**Music** (`assets/music`, not in git): name tracks by mood (`playful-sneaky-pizzicato_Sneaky-Snitch.mp3`) so
mood matching finds them. A `<track>.json` next to a track holds the credit its licence needs; the render adds it
to the video's description (`post.txt`). The music button next to the Music picker searches free instrumental music
on **Jamendo** (free client ID from devportal.jamendo.com, pasted in Settings), plays previews, and adds the chosen
track to the library with its credit. Jamendo's free licences are Creative Commons; check that a track's licence
allows your use (some are non-commercial) before posting it on a monetized channel.

**Transcript** (the Scenes / Transcript switch under the title) shows the whole voiceover as words with their
timing, made with the chosen voice and speed and cached in `cache/voiceover/`; the render reuses that exact audio.
Click a word to play from it (Space plays and pauses), shift-click to select several, then **H** marks them as
keywords (drawn green in the captions) and **Delete** removes them from the narration (that scene is voiced again).
Pauses of 0.3 s or more show as chips: click one to cut it to 0.12 s, or **Speech cleanup** cuts them all.
Cuts belong to the voiceover they were made on, so editing a scene's narration or changing voice or speed drops them.

**Live preview** (play button under the phone in the Preview pane) plays the whole draft before rendering: the
voiceover, each scene's footage (for automatic scenes, the same stock clips the render will pick, fetched by
`/api/footage/auto`), the headline and word-by-word captions drawn like the render's. Drag the bar to scrub; clicking a
scene card or a transcript word moves the playhead there, since the transcript and the preview share one player. A
chosen music track plays along (a random one is only picked at render time). The final video is still made by FFmpeg,
so the caption look lives in two places: `crcontent/captions.py` and `frontend/components/LivePreview.tsx`.

**Captions panel** (under the preview) sets the look of the whole video's captions: a preset (Classic, Bold, Boxed,
Neon, Minimal), font, size, outline (outline, box, shadow, glow), letter case, words shown at a time and the colours
of the text, the spoken word and keywords. Drag the captions, the scene headline or any text overlay on the preview to
move them; the render puts them in the same place (`script.captions`, `crcontent/styles.py` CaptionStyle).

**Timeline** (under the editor) shows the video on a time axis: each scene's footage as a filmstrip, B-roll and text
tracks, and the voiceover's waveform. Click to jump, zoom with the slider. Drag a scene's left edge to start its
footage later in the clip, drag a scene to reorder it, drag B-roll and text to retime them (the right edge sets how
long they last; they stay inside their scene).

**Per scene** (scene cards): **Layout** Fill (cropped to the frame), Fit (the whole clip over a blurred copy) or Split
(two clips stacked; the bottom one is picked automatically unless you choose it); **Add B-roll** puts a cutaway clip or
photo over the footage for a while; **Add text** puts extra text on screen (size, colour, box, timing). **Undo / Redo**
(top bar, or Ctrl+Z / Ctrl+Shift+Z outside text fields) step through edits; each drag is one step.

**Paste a script** (on the start screen) imports a script written anywhere, e.g. from a chat assistant:
`Title:` / `[0–3s] Hook` / `Visual:` / `On-screen text:` / `Voiceover:` blocks, or any other layout. Voiceover
is kept word for word, visual notes become footage searches, emojis are removed from on-screen text, and
production tips or chat text are ignored. Claude does the conversion; without Claude a basic reader handles
the `Visual / On-screen text / Voiceover` layout. CLI: `python make.py --import script.txt`.

**Translate to ខ្មែរ / English** (top of the storyboard) rewrites the title, narration, headlines, caption
and hashtags in the other language with Claude, keeping every scene's background. Render it as a new video;
the original stays in the library.

**Thumbnail → Suggest covers** (on any rendered video, music videos included) scores frames for sharpness, colour,
contrast and exposure, then shows Claude the best ones: it picks the frames and writes 4 short click-worthy headlines
(numbers, questions, bold claims) in different styles (Bold / Box / Stacked) with the key word highlighted. Write a
**Cover idea** first ("a silhouette against a neon city, the headline asks a question") and the covers follow it; a
picture the video doesn't contain comes from stock photos instead. Click one to use it, then fine-tune the headline,
highlighted word, style or frame, or **Use my own photo** as the background. Without Claude the headlines come from
the script.

With Claude every suggestion is also **Designed**: Claude lays out the whole cover around the frame as SVG (colour
grade, panels, badges, arrows, the headline in real type), renders it, looks at the result once and fixes anything
that's cut off or hard to read. Pick the **Designed** style yourself to get one for your own headline and frame;
changing the words keeps the design, changing the frame or photo re-renders instantly. New renders also
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
.venv\Scripts\python make.py --highlights output\<music video>      # best Shorts/Reels clips (see Smart Highlights)
.venv\Scripts\python make.py --script-video scripts\my-video.md     # long YouTube video (see Script to Video)
.venv\Scripts\python make.py --shorts plan.xlsx --eps 1             # Shorts from a content plan, to your rules (see Shorts Mode)
```

### From an Excel content plan

```powershell
.venv\Scripts\python make.py --excel Animal_Shorts_Content_Plan.xlsx               # every episode not marked Posted
.venv\Scripts\python make.py --excel Animal_Shorts_Content_Plan.xlsx --eps 1,3-5   # just these episodes
```

In the app: **New video → Excel plan**, choose the `.xlsx`, tick episodes (rows marked Posted start unticked), then
**Create drafts** to check each storyboard first, or **Render** them all in one job (each also becomes a draft).

One video per episode. The workbook needs a **Scripts** sheet with a header row `Ep | … | Time | Visual |
On-screen Text | Voiceover` (one row per scene). Optional sheets add the rest: a plan sheet (`Ep | Animal | Hook |
YouTube Title | … | Music / Mood | Key Visual | Status`), **Descriptions** (`Ep | Title | Description | Hashtags`)
and **Fact Check** (`Ep | … | Note`). Sheets are found by their headers, not their names. The voiceover is spoken
word for word; Claude turns each Visual description into a stock-footage search (without Claude, keywords from it).
Sound cues in brackets, like `(Chainsaw sound)`, aren't spoken, and a scene that is only a cue becomes a silent
beat as long as its Time span (add the sound effect yourself). **Music / Mood** picks the background track:
with Music on random, Claude chooses the `assets/music` file that fits the mood (without Claude, a file whose name
shares the most words with it, e.g. `warm-piano.mp3` for "Warm, soft piano"); when nothing in the library fits and a
Jamendo client ID is set, a matching free track is fetched from Jamendo. **Key Visual** is the shot the video is built
around: its scene gets the most precise footage search, the other scenes keep a matching look, and the cover is
taken from that scene and designed to show it. `post.txt` keeps the sheet's title with emoji,
and `notes.txt` lists mood, key visual, sound cues and fact checks for the edit and the pinned comment.
**Fact Check** notes stay with the episode (drafts too): the editor's Fact check section shows and edits them, notes
that cite a work (an author with "et al.", a year in brackets, a journal or university, a link) become the
**Sources** line of the description, and a **pinned comment** listing the notes is ready to copy from the editor or
the video's page. On YouTube it's also posted for you right after upload (Settings → YouTube → "Post the video's
fact-check comment", on by default; needs the comment permission, so connect YouTube again once). A video scheduled to
go public later gets its comment a few minutes after that time (queued in `schedule.json`, retried if YouTube isn't
ready); private videos can't have comments. The API can't pin comments: pin it in YouTube Studio → Comments. TikTok
has no comment API, so copy it there.

**YouTube category**: Settings → YouTube → Category sets the default for every upload (auto-uploads and scheduled ones
too); "Auto" uses Music for music videos and People & Blogs for everything else. The upload card's Category picker
overrides it for one upload.

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
   Optionally write a **Video idea** first ("a woman driving through neon Tokyo at night, rain on the windshield"),
   or press **Suggest ideas** for Claude's concepts (each with a matching look and lyric style): Claude plans the
   footage search for every section around it (without Claude, the idea's words are searched).
   **Footage look** puts one colour grade over every clip (Natural, Cinematic, Warm film, Moody, Vibrant, Black &
   white) plus a slow camera drift, so stock clips look like one film. **Lyrics style** picks a preset (Classic, Neon,
   Bold pop, Cinematic, Minimal, Boxed) with a live preview; **Customize** changes the font, colours, effect (karaoke,
   smooth fill, word pop, fade), edge (outline, shadow, box, glow), size, position and capitals. Idea, look and style
   are remembered on the song for the next version, and each version records the ones it was made with.

Songs live under **Drafts**: their lyrics and timing stay editable. Every **Make music video** creates a new version in
its own `output/<time>-<lang>-mv-<title>/` folder, listed under the song and in **Videos**; earlier versions are kept.
A music video's **Edit lyric timing** opens the song it was made from. Deleting a song keeps its videos.

Needs the music extras below; without them the lyrics are spaced evenly and you set the timing by hand.
The first sync downloads the Whisper and Demucs models (about 2 GB, once).

## AI songs and music videos

Claude writes original lyrics, ElevenLabs Music composes and sings them, and the song becomes a vertical music video
with footage cut on the beat and karaoke lyrics. ElevenLabs reports when it sang each word (`timestamps.json` in the
song folder); the lyrics are timed from those straight after composing, matched letter by letter so ad-libs and
different word splits (Khmer too) don't matter. That timing is exact and the same every time; listening with Whisper
is only the fallback (when no timings came back, or the lyrics were changed after composing). In the web UI: **New video → Make a song**, compose, then
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

## Smart Highlights (Shorts / Reels from a finished video)

Picks the most attractive 15–30 s of a finished music video, renders the best 3 as vertical clips with covers, and
writes a report to compare them.

**In the app**: open a music video and press **Find highlights** on the **Smart Highlights** card, under the video
(optionally with an artist name for the covers, and with or without Claude's judging). It takes a few minutes, and you
can keep working meanwhile. The card then lists the picks in order, each with its covers, Claude's hook and reason, a caption to
copy and **Open clip**, plus a link to the full report. The clips are added to Videos and aren't auto-uploaded: they're
alternatives to choose from. Run it again any time; earlier clips stay.

**Command line** (also works on any video, given its lyrics):

```powershell
.venv\Scripts\pip install -r requirements-highlights.txt      # OpenCV + PySceneDetect (also needs requirements-music.txt)
.venv\Scripts\python make.py --highlights output\<music video folder>
.venv\Scripts\python make.py --highlights song.mp4 --lyrics lyrics.txt --title "Replay" --artist "Your name"
```

Add `--no-judge` to skip Claude this time, `--no-render` to analyse and report only, and `--artist` to put a name on
the covers. On a short-studio music video folder, the lyrics, their word timing (`lyrics.json`, including your
hand corrections) and the song's sections come from the folder itself. For any other video, pass its lyrics: they're
forced-aligned to the audio with stable-ts (vocals isolated with Demucs first). Plain transcription isn't used,
because it mishears AI-generated vocals.

How a clip is chosen (`crcontent/highlights/`):

1. **Audio structure** (`structure.py`): beats and bars (librosa; bars from chord changes and the kick), sections from
   the song's plan or, for an unknown song, from where the music repeats. Choruses, loud parts, repeated parts and beat
   drops score high. allin1 is used when installed, but it can't be installed on Windows (it needs NATTEN and madmom).
2. **Lyrics** (`lyrics_score.py`): lines sung most often and lines with the song's title score high.
3. **Visuals** (`visual.py`): the lyric-free picture (`work/joined.mp4`), cut to the 9:16 window the clip will show,
   is scored for motion, sharpness, colour, faces (OpenCV) and scene cuts (PySceneDetect). Black, blurry or frozen
   stretches score low. A one-cover music video scores about the same throughout, so the audio and lyrics decide.
4. **Ranking** (`rank.py`): every 15–30 s window that starts on a lyric line and ends after one. The start moves back
   to the bar line before the line (keeping a pickup), else the beat, and never cuts into the previous line's last
   word. The end goes to the next bar or beat after the last word, before the next line. A hook bonus goes to clips
   whose first 2 s hold a strong line or a beat drop. The top picks never overlap, and a clip that repeats the lyrics
   of one already picked (the same chorus again) is marked down a little.
5. **AI judge** (`judge.py`, optional): Claude looks at the top 5 (lyrics plus 4 frames each) and ranks them by
   hook strength, with a reason, an on-screen hook (8 words at most) and an Instagram / Shorts caption. Uses
   `ANTHROPIC_API_KEY` from `.env`. Without it, or with the judge off, the score ranking stands.
6. **Covers** (`covers.py`): each clip's frames are scored for sharpness, face size, open eyes, contrast, colour and
   rule of thirds. The best 3 become 1080×1920 covers with the title in big letters, kept out of the bottom 20% and
   right 15% (the apps' buttons and captions). Khmer and English, even mixed in one title, each get their own heavy
   font, and Khmer is shaped correctly.
7. **Render** (`clip.py`): the lyric-free picture framed 9:16, fresh karaoke lyrics in the video's own lyric style,
   the hook for the first 3 s (kept off the subject's face), and the song mixed to −14 LUFS. Encoded with NVENC on an
   NVIDIA GPU at the same quality as the app's x264 renders, falling back to the CPU. A video without a lyric-free
   picture is shown whole over a blurred fill, so its burned-in lyrics stay readable.

Each clip is a normal Library video, `output/<time>-<lang>-hl<rank>-<title>/` (`video.mp4`, `thumbnail.jpg`,
`post.txt` with Claude's caption, `meta.json`), ready for the Upload card. Analysis and covers go to the source video's
`highlights/` folder: `report.html` (open it in a browser: song timeline, score breakdown, Claude's reason, hook,
caption with a copy button, covers and the clip for every candidate), `report.json`, `structure.json`,
`visual.json` and `candidate_<n>/cover_<k>.jpg`.

**Tuning**: `highlights.json` in the data folder (written with the defaults on the first run) holds the weights
(`weights`: structure / lyrics / visual / hook, plus the parts of each), how attractive each section kind is, clip
lengths, `clip.repeat_penalty` (0 = the same chorus may be picked twice), `ai_judge.enabled`, cover counts and `render.encoder` (`auto`, `nvenc` or `cpu`). Change a weight and run
again; the report shows the weights it used.

## Script to Video (long YouTube videos from a script)

Turns a script `.md` into an upload-ready 1920×1080 YouTube video (8–15 min): voiceover per scene, the timeline
recomputed from the real audio, footage for every scene, a storyboard to check and fix, and only then the render.

```powershell
.venv\Scripts\python make.py --script-video scripts\smartest-birds.md   # steps 1-5: stops at the storyboard
.venv\Scripts\python make.py --storyboard output\<job>                   # check, swap footage, approve -> render
.venv\Scripts\python make.py --approve output\<job>                      # or approve it as it is from here
```

**The script** (sample: `scripts/smartest-birds.md`): the title on the first `# ` line, then one or more tables with
the columns `Time | Visual | On-screen Text | Voiceover`. Every such table is the script, in order; other tables
(an Overview) are skipped by their header, so headings and prose around them are free. On-screen Text is shown
without its quotes, and a line like `#10 GREEN HERON` becomes a title card. A packaging section is read too:
`**Thumbnail:**`, `**Title options**` (a list), `**Description ...**` (with a `Chapters: 0:00 Intro · 0:45 Green
heron` line) and `**Shorts ...**`.

The steps (`crcontent/longform/`):

1. **Parse** (`parse.py`): the scene list goes to `scenes.json`.
2. **Voiceover** (`voice.py`): one audio file per scene. `voice.engine` in `longform.json` is `edge` (free, the
   default; English and Khmer voices), `elevenlabs` (`ELEVENLABS_API_KEY`, `voice.elevenlabs.voice_id`) or `files`:
   your own recordings, `media/<script>/scene-XX.wav` (or .mp3 / .m4a / .flac). A recording you put there is used
   whatever the engine; its word timing is force-aligned to the scene's text (stable-ts) for the captions.
3. **Timing** (`timing.py`): a scene lasts as long as its voiceover + 0.4 s. When that differs from the Time column,
   the whole timeline moves, and every chapter goes with the scene its planned time pointed at. A video outside
   8–15 min, or chapters YouTube won't accept (under 10 s, fewer than 3), is flagged.
4. **Footage** (`footage.py`), for each scene in this order:
   1. Your own file, `media/<script>/scene-XX.mp4` (or .mov, .jpg, .png...).
   2. What the scene is, as Claude reads the script (any topic, not only wildlife). Each kind is searched in the
      libraries that suit it:
      - **footage** (everyday shots): Pexels and Pixabay (most popular, full-HD clips first), then Wikimedia
        Commons.
      - **species** (one animal or plant): stock video, then research-grade iNaturalist photos and Wikimedia
        Commons.
      - **archival** (history, people, artworks, events, space): Internet Archive film and newsreels (only
        the Prelinger, Universal Newsreels and FedFlix collections, which are public domain), NASA, Wikimedia Commons
        and the Met's open-access collection.
      - **graphic** (a comparison, a list, a logo sting, an end screen): a card drawn by the app (`cards.py`).
      - **montage** (a cold open, a recap): quick cuts of the footage picked for the other scenes.

      The search words come from the Visual column; Claude names the subject of each section, so "Slow-motion catch"
      under #10 GREEN HERON searches "green heron catching fish".
   3. Nothing good enough: a card with the scene's on-screen text, flagged.

   Claude looks at each pick. Under 7/10 it tries the next match, spread across the libraries, then the broader
   search words. A pick under 5/10 is never used, whatever the libraries had: the scene gets a card and a flag
   instead. Each scene keeps a few alternatives. Every file's source page, author and licence is saved
   (`footage.json`).
5. **Storyboard** (`storyboard.py`): `storyboard.html` lists every scene with its footage, its real and planned
   time, its text, its voiceover (playable) and anything flagged. Open it with `--storyboard` (or from the engine at
   `http://127.0.0.1:8000/media/<job>/storyboard.html`) to pick another alternative, search again with other words,
   or press **Reload my files** after dropping files into `media/<script>/`. **Nothing renders until you press
   Approve and render**, and any change after approving needs approving again.
6. **Render** (`video.py`): each scene is cropped to 1920×1080 at 30 fps, photos with a slow Ken Burns push-in, all
   in one colour grade (`render.look`). Old 4:3 film and portrait pictures are shown whole over a blurred copy, so
   heads aren't cut off; black bars baked into archive film are removed first. The
   scenes are joined with 0.4 s dissolves, and the voice sits at the real scene times. `#N NAME` lines become
   title cards (number and name centred over a dimmed frame); other on-screen text becomes a lower third. Music
   comes from your own tracks in `assets/music/own` (any number, played back to back with crossfades), ducked
   under the voice. The mix goes to −14 LUFS, and the video is H.264 + AAC, on NVENC with a CPU fallback.
7. **Extras** (`extras.py`):
   - `captions.srt` from the voiceover's word timing (`render.captions: true` also burns them in).
   - `description.txt`: the script's description, chapters at their real times, and the credits that must be
     named (Wikimedia and iNaturalist authors and licences, and the archives used).
   - `credits.txt`: every clip, photo and track, with its licence and source.
   - `post.txt` and `thumbnail.jpg` for the app's Upload card.

Everything lands in `output/<time>-<lang>-<title>/`: `video.mp4` and the files above, plus the working files
(`scenes.json`, `voice/`, `timeline.json`, `footage.json`, `storyboard/`).

**Settings**: `longform.json` in the data folder, written with the defaults on the first run:
- `voice`: the engine, and the voices per language.
- `timing.pad_seconds`.
- `footage`: `media_dir`, `sources` and their order (for everyday footage), `by_kind` (the libraries for species
  and archival scenes), `alternatives`, and `check_subject` (Claude's check).
- `render`: size, `crossfade`, `look` (`natural`, `cinematic`, `film`, `moody`, `vibrant` or `mono`), `encoder`
  (`auto`, `nvenc` or `cpu`), `captions`, and how long title cards and lower thirds stay up.
- `music`: `dir` and `volume`.

## Shorts Mode (YouTube Shorts from a content plan, held to your analytics)

One upload-ready 1080×1920 Short per episode of an Excel plan, checked against rules that come from the channel's
own retention numbers, with a pre-flight report to OK before anything renders. It runs Script to Video's steps at
9:16 (`crcontent/shorts/`).

```powershell
.venv\Scripts\python make.py --shorts Jackdaw1715_Improved_Shorts.xlsx --eps 1     # one episode (or 1,3-5; none = all)
#   -> output\<time>-en-ep01-your-cat-brought-you-a-dead-mouse-don-t-\preflight.html : check it, then
.venv\Scripts\python make.py --approve "output\<that folder>"                      # render, cover, metadata
.venv\Scripts\python make.py --shorts-analytics "Table data.csv" --plan Jackdaw1715_Improved_Shorts.xlsx
```

**The workbook**: a **Scripts** sheet `Ep | Time | Visual | On-screen Text | Voiceover`, one row per beat; a row whose
Time is `TITLE` holds the episode's title. An optional **Plan** sheet adds `Old title | New title | Hook (first 2s) |
Description + hashtags | Pinned comment`. The voiceover is spoken word for word; `(sound cues)` and the `[loops]` /
`[loops to start]` marker aren't.

**The rules** (`shorts.json` in the data folder, `rules`):
1. **Hook**: the first beat shows the animal in motion under a big hook text, and its line ends within 2 s. The hook
   clip is picked on its own (`hook.py`): each candidate is scanned for the animal's own motion (optical flow with
   the camera's pan or zoom taken out, so slow zooms and still close-ups are rejected), sharpness and brightness, its
   best 2 s found, and Claude checks those frames for the right animal, real movement, and no logo, text or intro.
   Rejected clips are listed with the reason.
2. **Length**: 22–30 s from the real TTS audio (not the sheet's times; each beat lasts as long as its speech). Over
   30 s, the report names the beat to cut (never the hook or the loop line).
3. **Loop**: the last line ends mid-sentence and runs into the first; the last 0.5 s cut back to the hook clip,
   ending on the frame the Short opens with. No fade-out, music included.
4. **Title**: no hashtags; any found move to the description.

**Footage**, per beat: your file `media\<plan>-epNN\scene-XX.mp4` (or .mov / .jpg...), then Pixabay (vertical
clips, or 4K ones that stay sharp cropped to 9:16), checked by Claude. Stock rarely has the exact action ("cat drops
a toy mouse"), so a beat nothing matches gets a checked general shot of the episode's animal (flagged), and only
when there's none, a placeholder card (flagged). The 9:16 crop is centred on the animal.

**The pre-flight report** (`preflight.html`) lists the checks (hook beat, length, loop line, loop shot, hook shot,
title, placeholders), **Claude's hook judge** (a 1–10 score with its reasons, 3 stronger first lines and 3 stronger
on-screen hooks), and the storyboard: one frame per beat with its text, voiceover, source, Claude's score and
anything flagged. Nothing renders until `--approve`; a re-run needs approving again.

**Each Short's folder**: `video.mp4` (1080×1920, 30 fps, H.264 + AAC, −14 LUFS, NVENC with CPU fallback),
`cover.png` (the sharpest, most colourful frame of the animal with the title, inside the safe zone),
`metadata.txt` (title, description, hashtags, pinned comment), `post.txt` + `thumbnail.jpg` for the Upload card,
and `preflight.html`. Captions follow the voiceover word by word (the spoken word in yellow), big and bold, and all
text stays out of the bottom 20 % and right 15 % (and the top 8 %). English and Khmer both render; emoji too.

**Analytics**: in YouTube Studio, Analytics → Advanced mode → Content, export as CSV, and import it with
`--shorts-analytics` (`--plan` matches the videos to your episodes by new or old title). Each video is tagged with
its hook style (your cat + hidden meaning, shock fact, science explainer, question, myth bust, POV, list), length
and animal, and the summary ranks each tag by Stayed to watch % and % viewed (weighted by views). It's saved as
`shorts-analytics.json`, and from then on the judge's suggestions are ordered by how their hook style really did on
the channel.

## Upload to YouTube, TikTok, Facebook and Instagram

Every rendered video has an **Upload to channels** card under its post text. It uploads `video.mp4` with
`post.txt` (first line = title, the rest = description, `#tags` = hashtags/tags). Tick **Auto-upload** to post
every new render (scripts, Excel episodes and music videos) as soon as it finishes.

Each platform uses your own developer app. Enter its keys in the card (the form shows the redirect URI to
register, with a copy button; the key icon changes them later), then press **Connect**: the sign-in opens in
your browser and comes back to the app. Keys from older `.env` setups are imported once.

- **YouTube**: in Google Cloud Console enable *YouTube Data API v3*, set up the OAuth consent screen (add your
  Google account as a test user), then create an OAuth client ID of type **Desktop app** and enter its
  client ID and secret. Vertical videos get `#Shorts`. The API's default quota allows
  about 6 uploads a day; until Google verifies your app, it may post them as private.
  Several channels can be connected: **Add channel** signs in again (pick the Google account or brand account
  that owns it). One is the default (**Make default**); the Upload card has a channel picker for each upload,
  while auto-uploads and set-time uploads go to the default. All channels share the one developer app and its
  daily quota.
- **TikTok**: at developers.tiktok.com create an app (platform **Desktop**), add *Login Kit* and the
  *Content Posting API* (Direct Post), register the redirect URI `http://localhost:8765/callback/`, and enter
  its client key and secret. Until TikTok audits the app, direct posts can only be
  **Only me**; choose **Send to TikTok drafts** to finish and post publicly from the TikTok app instead.
  Direct posts follow TikTok's Direct Post rules: the Upload card has Comment / Duet / Stitch (off until you tick
  them), **Disclose video content** (Your brand / Branded content) and the Music Usage Confirmation line.
  Auto-uploads and set-time posts allow all three interactions and disclose nothing.
- **Facebook and Instagram** share one Meta app and one sign-in. At developers.facebook.com create an app with the
  use cases for managing a Page and the *Instagram API with Facebook Login*, keep it in **Development mode** (as
  its admin you can grant every permission without App Review; `http://localhost` redirects are allowed there), and
  enter its App ID and secret on the Facebook row. **Connect** asks Facebook for your Pages and the Instagram
  accounts linked to them: Instagram must be a professional (Business or Creator) account linked to a Page.
  Facebook: vertical videos up to 90 s post as public **Reels** on the Page (their audio is converted to 48 kHz for
  Facebook), anything longer or landscape as a regular Page video. Instagram: every video posts as a public
  **Reel** (caption up to 2,200 characters and 30 hashtags; the cover is your thumbnail's frame; **Also show Reels
  in the profile grid** is on by default). With several Pages or accounts, Settings picks the one to post to.
  Both upload with the Page's token, which doesn't expire; Meta allows 30 Reels a day per Page and 100 posts a day
  per Instagram account. `META_GRAPH_VERSION` overrides the Graph API version (default `v25.0`).

Keys and tokens are kept in `accounts.json` (in the data folder, never committed); each video's uploads in its
`published.json`. Port 8765 can be changed with `PUBLISH_CALLBACK_PORT`.

## Campaigns (Whop Content Rewards)

**Campaigns** in the left rail turns a paid clipping campaign into ready-to-post clips:

1. **Add**: open the campaign on Whop, copy the whole page and paste it (plus its link). Claude pulls out the
   brief, the content requirements (length, required hashtags, accounts to tag, phrases the caption must include,
   ad disclosure, rules and don'ts) and the links to the reference materials. Everything stays editable.
2. **Reference materials**: links are downloaded with yt-dlp (YouTube, single Drive/Dropbox files, direct video
   links); folders can't be, so download those files and add them. **Prepare** downloads and transcribes them
   with Whisper (`pip install -r requirements-music.txt`).
3. **Make clips**: Claude reads the transcripts and picks the strongest moments that fit the brief. Each becomes
   a 9:16 clip (whole picture over a blurred fill, or cropped), with captions, an on-screen hook and post text
   that carries every required hashtag, mention, phrase and disclosure. Clips also appear in Videos.
4. **Post**: upload or schedule each clip, or **Schedule new** to spread all unposted clips over your posting
   times. After a clip is live, copy its link from the clip card and submit it on Whop to get paid for views.

### Scheduled uploads

A video's **Upload** card has **Schedule for later**. Auto-upload (Settings, Channels) can post right after a
render or **at set times** (e.g. 09:00 and 18:00): each new video takes the next free time. Settings, **Upload
queue** lists everything scheduled. Uploads go out while the app is open; anything due while it was closed goes
out when you open it. The queue is kept in `schedule.json`, campaigns in `campaigns/`.

## Layout

| Module | Job |
|---|---|
| `crcontent/script.py` | Claude prompt + JSON schema for hook, scenes, caption and hashtags |
| `crcontent/sheet.py` | Reads an Excel content plan into one script per episode (`make.py --excel`) |
| `crcontent/tts.py` | Edge TTS voiceover with word timings |
| `crcontent/visuals.py` | Pexels search/download (cached), local footage, gradient fallback |
| `crcontent/art.py` | Claude as art director: SVG backgrounds and designed covers, rendered with resvg |
| `crcontent/motion.py` | Plays Claude's SMIL-animated SVG frame by frame into a looping mp4 (resvg + FFmpeg) |
| `crcontent/captions.py` | Word-highlight `.ass` captions and scene headlines |
| `crcontent/render.py` | FFmpeg scene clips, concat, burn-in, music ducking |
| `crcontent/lyrics.py` | Claude prompt + schema for original songs (sections, lyrics, sound) |
| `crcontent/song.py` | ElevenLabs Music: compose + vocal/instrumental stems |
| `crcontent/align.py` | Lyric timing (stable-ts forced alignment + repair of stray words, even-spacing fallback) |
| `crcontent/beats.py` | Beat detection and beat-synced shot plan |
| `crcontent/campaigns.py` | Campaigns: read the brief and requirements (Claude), download and transcribe references, pick and cut clips |
| `crcontent/schedule.py` | Scheduled uploads queue and posting-time slots |
| `crcontent/publish.py` | YouTube / TikTok sign-in (OAuth + PKCE) and uploads, auto-upload settings |
| `crcontent/web.py` + `web/` | FastAPI backend and the browser UI |
| `crcontent/highlights/` | Smart Highlights: best Shorts / Reels clips of a music video |
| `crcontent/longform/` | Script to Video: long 16:9 YouTube video from a script `.md`, with a storyboard to approve |
| `crcontent/config.py` | Voices, fonts, sizes per language |

## Roadmap ideas

1. **Trend input**: pull trending topics (vidIQ, Google Trends) into `--batch` automatically.
2. **AI images**: generate a picture per scene (image-generation API) when stock footage doesn't fit.
3. **Premium voice**: ElevenLabs option for more natural or cloned voices.
4. **Templates**: per-channel brand presets (fonts, colours, logo watermark, intro/outro).
5. **Web dashboard**: queue topics, preview and edit scripts, approve before posting.
6. **Analytics loop**: feed best-performing videos back into the script prompt.
