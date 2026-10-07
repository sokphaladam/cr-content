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
| `thumbnail.jpg` | cover frame |
| `script.json` | editable script, re-render with `--script` |

Background music: drop royalty-free `.mp3` files into `assets/music/` (one is picked at random and ducked under the voice), or pass `--music file.mp3` / `--music none`.

## Layout

| Module | Job |
|---|---|
| `crcontent/script.py` | Claude prompt + JSON schema for hook, scenes, caption and hashtags |
| `crcontent/tts.py` | Edge TTS voiceover with word timings |
| `crcontent/visuals.py` | Pexels search/download (cached), local footage, gradient fallback |
| `crcontent/captions.py` | Word-highlight `.ass` captions and scene headlines |
| `crcontent/render.py` | FFmpeg scene clips, concat, burn-in, music ducking |
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
