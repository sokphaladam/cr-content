# Local Voice Clone — Plan

Record your own voice once (30 s – 2 min), and every Short / long-form voiceover can be spoken in it, generated on
this PC's GPU. Free per video, nothing uploaded.

Status: **plan only** (2026-11-05). Nothing below is built yet.

## Goal

- A new voice kind next to the Edge voices: `local:<name>` (e.g. `local:me`).
- Picked in the same voice dropdown as today; preview, transcript editor, captions and render all work unchanged.
- English first. Khmer: see [Khmer](#khmer) — not covered by the clone, uses your recordings instead.

## Engine choice

| Model | Why / why not |
|---|---|
| **Chatterbox** (Resemble AI, MIT) | **Pick.** Most natural of the free ones, needs ~10 s of reference, emotion control (`exaggeration`), runs on a gaming GPU. |
| F5-TTS | Fallback if Chatterbox sounds off on your voice. Good rhythm; CC-BY-NC weights (non-commercial — matters if the channel is monetised). |
| CosyVoice 2 / XTTS-v2 | Skip. XTTS weights are non-commercial and the project is unmaintained. |

Before building anything: confirm Chatterbox's current version, license and torch/transformers pins on its repo
(things may have moved since mid-2026).

## How it fits the code we already have

The one seam every voice goes through is `crcontent/tts.py: synthesize(text, voice, out_path, rate) -> list[Word]`.
Its callers already handle caching, captions and render:

- `crcontent/voiceover.py: scene_voice()` — Shorts and the transcript editor (cached by `voice_key(text, voice, rate)`)
- `crcontent/web.py` — `/api/voice-preview` (line ~508) and `/api/voiceover` (line ~538)
- `crcontent/longform/voice.py` — long-form engines (`edge`, `elevenlabs`, `files`)

Edge reports word timings itself. A clone does not, so its words come from **forced alignment** of the known text,
the same way `longform/voice.py: _recorded()` times your own recordings (stable-ts, already in the AI add-on).

So the change is: `synthesize()` sees `voice.startswith("local:")` → generate with the clone → align → return
`list[Word]`. Everything downstream stays as it is.

## Steps

### 1. Spike (half a day, decides go / no-go)
- Separate venv `addons/voice/` (Chatterbox pins its own torch/transformers; the AI add-on pins
  `transformers==5.19.0` for LTX — don't mix them).
- Script in the scratchpad: your sample + 5 real scene lines → wavs. Listen.
- Measure: seconds per scene on this GPU, VRAM use, how often a take glitches.
- **Go** if it sounds like you and a 30 s Short voices in under ~1 min. Otherwise try F5-TTS, then stop.

### 2. Voice library
- Data folder (from `locations.json`, not the repo): `voices/<name>/reference.wav` + `voice.json`
  (`{"name", "lang", "engine": "chatterbox", "exaggeration": 0.5}`).
- Clean the sample on import: mono 24 kHz, trim silence, loudness-normalise; reject under 8 s or clipped audio.
- `list_voices()` (or `web.py: _voices()`) adds `local:<name>` for each folder whose `lang` matches.

### 3. Generator (child process)
- `crcontent/voiceclone.py`: `synthesize_local(text, name, out_path) -> list[Word]`.
- Runs Chatterbox in a **child process** using the `addons/voice` python (same reason as LTX: GPU memory is
  freed when it exits, and a crash doesn't take the engine down). Keep the worker alive for a whole job so the model
  loads once, not per scene.
- Text in sentence-sized chunks (long text drifts), joined with ~120 ms gaps.
- Word timings: stable-ts alignment of the known text against the wav (reuse what `_recorded()` calls); fall back to
  spreading words by length if alignment fails, like `_recorded()` does.
- Output mp3 like Edge so `voiceover.scene_voice()` caches it unchanged.

### 4. Wire it in
- `tts.synthesize()`: `if voice.startswith("local:")` → `voiceclone.synthesize_local(...)`. `rate` → apply with
  ffmpeg `atempo` after generation (Chatterbox has no speed knob).
- `web.py` lines ~514 and ~541 reject any voice without `"Neural"` in it — allow `local:` too.
- Long-form: new engine `local` in `longform/voice.py` (`voice.local.name` in `longform.json`).
- Glitch control: a "Re-generate this scene" button in the transcript editor changes a seed in the cache key, so one
  bad take can be redone without redoing the rest.

### 5. UI
- Settings → **My voice**: record in the browser (MediaRecorder) or upload a file, name it, hear a test line.
- Show a short recording guide: quiet room, no music, steady mic distance, speak the way the Shorts should sound;
  a clean 30–60 s beats a noisy 2 min.
- Add-on install row "Voice clone (~2–3 GB)" via the existing `addons.py` install flow.

### 6. Tests
- `voiceclone` with the model mocked: chunking, timings are monotonic and inside the audio length, fallback timing.
- `tts.synthesize("…", "local:me", …)` routes to the clone; Edge voices untouched.
- web: `local:` voices accepted by preview / voiceover endpoints.

## Khmer

No free clone speaks Khmer well, and training one is a large project. For Khmer, use your own recordings per scene:
long-form already supports it (`media/<script>/scene-XX.wav`, aligned automatically). Follow-up task: bring the same
"use my recording for this scene" option to Shorts.

## Risks

- **Quality varies by sample** — the spike decides; don't build steps 2–6 before it passes.
- **GPU contention** with LTX — never run both at once; queue voice generation before/after footage.
- **Licence** — check the chosen model's weights allow commercial use before monetised uploads.
- **Consent** — only clone voices you own or have permission for; the UI should say so.

## Out of scope

Voice design / mixing voices, real-time voice conversion, cloud fallback (ElevenLabs path already exists for
long-form).
