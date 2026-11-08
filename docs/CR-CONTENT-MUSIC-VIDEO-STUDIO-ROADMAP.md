# CR Content — Music Video Studio and Anim Studio Integration Roadmap

**Repository:** sokphaladam/cr-content  
**Target:** Production-ready full-song music videos using editable animated scenes from Anim Studio  
**Status:** Implementation plan; no application code changes are included in this document  
**Baseline reviewed:** main branch, November 8, 2026

## 1. Product goal

Extend CR Content into a **Music Video Studio** that combines its existing song, lyrics, timing, beat analysis and final rendering workflow with character-level animations generated in Anim Studio.

The target production is a polished illustrated music video: one coherent animated world, natural characters and animals, carefully controlled atmosphere, tasteful branding, optional synchronized karaoke lyrics and the original song mixed into the final export. The creator should not have to manually stitch an external animation editor, audio editor and caption renderer together.

CR Content remains the music and final-render authority. Anim Studio remains the animation authoring authority. The projects should exchange validated files and metadata, not become one tightly coupled application.

## 2. Current foundation and gaps

The current CR Content code already provides:

- Song upload and AI song creation workflows.
- Song analysis, BPM/beat timing and lyric synchronization with Whisper/Demucs or returned word timestamps.
- Song sections, lyric timing editor, word timing, waveform and timeline UI.
- Per-section pictures and transitions.
- A full-song lyric renderer in neonmekong/lyricvideo.py.
- Animated cover support through crcontent/coverloop.py, loop.mp4, loop state and optional GPU/living modes.
- A renderer that reads an animated cover as a repeating source and overlays lyrics, beat effects, title/now-playing information and channel branding.
- Existing quality checks and pre-render checks for song and video output.

The key current gap is that the animated-cover pipeline is not yet a general-purpose, project-aware handoff from Anim Studio. It accepts clips and repeats them behind the song, but does not yet import a portable scene package, retain source-project identity/version, map song analysis into an animation project, or expose a dedicated full-song Music Video Studio workflow that combines all modes and validation coherently.

Do not replace the working lyric-video renderer. Extend it in small, reversible steps.

## 3. Product experience: Music Video Studio

Create a focused workspace for songs rather than a separate generic video editor. Reuse the existing song folder, jobs/progress system, audio and lyric timing data, preview player, timeline and render pipeline.

### Proposed workflow

1. **Select song:** upload an existing song or create a song using the current AI song workflow.
2. **Analyze:** reuse existing BPM, beat timestamps, sections, lyrics and word timings. Do not run duplicate audio analysis just for Anim Studio.
3. **Create animation:** launch/open Anim Studio or export a music-analysis handoff file for it. The user generates and edits a scene there.
4. **Import animation:** upload a portable animation package or a silent MP4 loop. Validate all files and metadata before changing the song's active visual source.
5. **Choose presentation:** Pure Music Visualizer, Animated Lyric Video or Advanced Visualizer.
6. **Customize:** title/artist, logo/channel badge, optional now-playing panel, lyric style, music-reactive effects, color look and safe areas.
7. **Preview:** scrub the full song with audio and animation in sync; show the current section and active lyric when enabled.
8. **Preflight:** run asset, timeline, lyric, loop, audio and export checks.
9. **Render:** compose the final video and mux the original song exactly once.
10. **Inspect:** run the existing final render inspector and present actionable warnings with timestamps.

### Presentation modes

- **Pure Music Visualizer:** no karaoke lyrics; use the animated scene, restrained visualizer/effects, track title and artist/channel identity.
- **Animated Lyric Video:** the same animated scene with existing synchronized line/word lyrics.
- **Advanced Visualizer:** the same scene plus optional waveform/spectrum, particles and carefully tuned beat-reactive lighting or camera effects.

All modes must use one canonical animation source and one audio mix. Modes change overlays and presentation, not song timing or the source animation file.

## 4. Milestones

### M11 — Shared animation package import (MVP bridge)

**Goal:** Bring an Anim Studio export into a CR Content song without requiring Anim Studio to be installed or running during final rendering.

Scope:

- Add an import operation to the existing lyric-video/music-video song workflow. First support a silent MP4 plus manifest; add a ZIP package with editable source scene/assets as the next increment.
- Reuse the existing song folder and existing loop.mp4 active-cover mechanism where possible. Do not create a second competing file convention.
- Store import metadata in a dedicated file such as animation-source.json: source project ID/version, package schema, source repository/app version, duration, FPS, dimensions, SHA-256, loop validation and import timestamp.
- Keep the existing cover still as a thumbnail/fallback. A newly imported loop must not destroy the user's still cover or section images.
- Validate file size, MP4 readability, video stream, codec, FPS, dimensions, duration, color metadata and checksum. Verify actual properties with ffprobe.
- Validate ZIP paths against traversal, reject absolute paths, symlinks and unexpected file types, impose archive/file-size limits, and extract into a temporary folder before atomic promotion.
- Add a new package-aware API route while retaining the existing /api/lyricvideo/{slug}/loop/upload behavior for ordinary video uploads.
- Support re-import as a new version and keep the previous working loop until the new import passes validation.
- Make import errors actionable: unsupported codec, missing manifest, checksum mismatch, no video stream, invalid loop flag, etc.

Acceptance criteria:

- A silent MP4 from Anim Studio can be imported without any Anim Studio runtime or AI model.
- A manifest mismatch or corrupted MP4 cannot replace the currently active loop.
- Re-import preserves previous versions or can be rolled back.
- Existing songs and existing loop upload workflows remain compatible.
- Tests cover large file rejection, malicious ZIP paths, checksum mismatch, invalid media and atomic replacement.

### M12 — Music analysis handoff and scene synchronization

**Goal:** Let Anim Studio author motion against the actual song structure using CR Content's analysis results.

Scope:

- Define a versioned JSON handoff file, for example music-analysis.json, containing song duration, BPM, beat timestamps, section start/end/type/energy, chorus ranges and optional sampled audio-energy envelope.
- Export from CR Content using already stored analysis. Include a stable song/project ID and checksum; exclude the original copyrighted audio unless the user explicitly chooses to share it.
- Add a copy/open workflow so the file can be loaded by Anim Studio. Avoid a hard runtime dependency between applications for the MVP.
- On re-import, compare the animation manifest duration with song duration. A loop animation may be shorter than the song; a non-loop clip must show its duration and chosen fallback behavior.
- Map musical time to animation time explicitly. Looping animation repeats by its own manifest duration; section-specific events use song time.
- Provide an option to align the animation loop length to a phrase/bar count when the source animation supports it.
- Never stretch the original music audio or change existing lyric timing to fit the animation.

Suggested handoff fields:

- Schema version and analysis ID.
- Song duration and BPM.
- Beat timestamps in seconds.
- Sections with type, start, end and normalized energy.
- Chorus ranges and optional energy envelope samples with their sample interval.
- Song title and language as optional descriptive metadata.

Acceptance criteria:

- Handoff data is generated from existing analysis with no second Whisper/Demucs run.
- Invalid or absent data is rejected gracefully and the existing workflow still works.
- Section and beat timestamps use song-local seconds consistently.
- Animation is in sync after seeking, pausing and restarting; no cumulative drift is allowed.

### M13 — Music Video Studio UI and composition modes

**Goal:** Make the whole-song production workflow understandable, flexible and visually professional.

Scope:

- Add a dedicated Music Video Studio step/page within the existing music-video flow rather than scattering controls across unrelated panels.
- Provide a large 16:9 program monitor with clear playback, scrub, zoom-to-fit and safe-area overlays.
- Reuse the existing lyric timeline, waveform, word timing, section metadata and preview clock. Add an animation track that displays loop duration and repeated cycles.
- Add clear source states: no animation, imported animation, animation outdated, import failed, validation warning and ready to render.
- Add mode selector: Pure Music Visualizer, Animated Lyric Video and Advanced Visualizer.
- Keep existing lyric controls, typography presets, thumbnail generation and song edit controls. Hide or disable lyric-specific controls when Pure Music Visualizer is selected rather than deleting existing capabilities.
- Add title/artist/channel identity controls with presets and safe areas. Do not burn in a logo or track metadata by default if the user has not selected it.
- Provide animation controls: fit/crop, scale, position, loop enable, phase offset, brightness/grade, and optional section-picture replacement/disable.
- Preserve the current optional section-specific pictures, but make the default for an imported living scene one consistent scene across the song. Section pictures must not unexpectedly cover the imported scene.
- Provide a preview that uses the same compositing logic as the final render, at a lower preview resolution if needed.

Acceptance criteria:

- A creator can select a song, import a loop, choose a mode and preview the result without editing JSON.
- The preview player, lyrics and animation share one timebase.
- Seeking backward/forward produces the same visual frame for the same timestamp.
- The imported scene remains the main visual; optional section pictures are explicit overrides.
- Existing lyric video projects can still be opened and rendered without a new setup step.

### M14 — Music-reactive visualizer and motion controls

**Goal:** Add musical responsiveness that enhances rather than distracts from the animated scene.

Scope:

- Reuse CR Content's detected beat timestamps and available audio-energy data. Do not infer beats from wall-clock playback.
- Add independent controls for beat light, camera push, lyric glow, particle intensity and waveform/spectrum display.
- Support section-aware intensity: calm verses, restrained pre-chorus build, stronger chorus and quiet outro.
- Add smoothing, attack/release and maximum-intensity controls to avoid harsh flashing.
- If the imported animation is already beat-aware, allow music-reactive post effects to be disabled to prevent double-pulsing.
- Keep the waveform/spectrum optional and visually subordinate to the character and composition.
- Provide a small set of tested presets, not dozens of arbitrary toggles.

Acceptance criteria:

- All reactive effects are deterministic from song time and analysis data.
- No rapid flashing or excessive frame-to-frame brightness changes are introduced by default.
- Reactive effects can be disabled independently.
- The same song and settings always produce the same sampled frames.

### M15 — Final render, audio mux and production inspector integration

**Goal:** Make the final full-song render technically reliable and easy to verify before upload.

Scope:

- Extend the existing renderer to treat imported animation as a visual source, then composite overlays/lyrics and original song audio in a clearly defined order.
- Mux the original song once; imported Anim Studio MP4 must be silent. Do not accidentally add an animation clip's audio stream.
- Keep final render encoding in the existing FFmpeg-based CR Content pipeline. Use a stable H.264/AAC output profile, correct BT.709 tags for standard SDR output, faststart and the selected resolution/FPS.
- Add configurable 1080p/30 FPS final export and a faster draft preview. Avoid forcing expensive 4K output as the default.
- Validate total duration, video frame rate, audio/video synchronization, silence/audio ending early, black/frozen stretches, decode errors and unexpected loop seams.
- Extend the existing quality report with source-animation manifest details, loop duration, phase, media checksum and import/source version.
- Add warnings for visual checks that cannot be measured reliably; do not label subjective framing, story or aesthetics as passed unless actually evaluated.
- Keep output atomic and preserve the previous successful render if a job is cancelled or fails.

Acceptance criteria:

- Final video length and audio stream match the song within the defined tolerance.
- The song is present exactly once and the animation has no audio stream.
- Loop boundaries show no obvious jump during the full-length render.
- Technical checks are Pass/Warning/Fail/Not checked with evidence and timestamps where applicable.
- An outdated import or changed animation source makes the preview/quality report visibly outdated.

## 5. Shared Anim Studio interchange contract

Coordinate with docs/ANIM-STUDIO-PRODUCTION-QUALITY-ROADMAP.md in Anim Studio. Both repositories must implement the same contract; do not let each app invent different field names or timing conventions.

### MVP media handoff

- animation.mp4: silent H.264, normally 1920×1080 at 30 FPS.
- manifest.json: package schema version, title, source project ID/version, duration, FPS, width, height, frame count, loop flag, codec, pixel format, color metadata, SHA-256 and export timestamp.

### Portable editable package (follow-up)

- animation.mp4.
- manifest.json.
- scene.spec.json with relative asset paths only.
- assets/ with referenced source/derived image files.
- quality-report.json with asset, rig, motion and loop results.

### Contract rules

- The MP4 is the playback source. CR Content does not require Anim Studio at render time.
- The editable project payload is retained for future revision but is not needed for final render.
- Video duration may be an intentional loop length (for example 8, 12, 16 or 24 seconds), not necessarily the full song duration.
- CR Content loops using the manifest duration or probed media duration. Do not hardcode the current 12-second cover-loop assumption for all imported animations.
- The first frame and last-to-first transition must be validated. A manifest loop flag is not proof of a seamless loop.
- No source media may use an absolute path. Use relative paths and validated file names.
- Check checksums and use temporary extraction/import folders before promoting new files.
- The initial package should be an opaque full-frame scene. Alpha-video can be a later extension.

## 6. Integration with the current CR Content implementation

Prefer reusing these existing areas after rechecking their current code at implementation time:

- crcontent/lyricvideo.py: song-level API, picture/loop state, preview, jobs and upload.
- crcontent/coverloop.py: active loop metadata, validation and video-file operations.
- neonmekong/lyricvideo.py: full-song rendering, loop reader, lyrics, beat effects, title and now-playing overlays.
- neonmekong/pictures.py: optional per-section image plan and camera moves.
- frontend/components/LyricPictures.tsx and frontend/components/AnimatedCover.tsx: current picture/loop UI patterns.
- frontend/components/LyricTimeline.tsx, LyricMonitor.tsx and LyricsTiming.tsx: timeline, preview and lyric timing behavior.
- Existing API client types and tests should be extended rather than duplicated.

Before implementation, map the current route names, request schemas and UI state in the current branch. Do not rely only on this roadmap's path list if code has moved.

## 7. UI and usability principles

- Keep the workspace focused on the song and final video, not on exposing every FFmpeg or AI implementation detail.
- Provide a clear status for animation import, validation, preview, render and quality check.
- Separate content controls (title, artist, lyrics) from visual controls (scene, camera, grade, particles) and export controls.
- Show which animation version is being used and when it was last imported.
- When an imported animation changes in Anim Studio, require explicit re-import or refresh; never silently change a render source.
- Provide meaningful empty/error/loading states. Every import or render job can be cancelled without corrupting the current source.
- Keep safe areas for lyrics, title and platform overlays; avoid covering the character's face or focal point.
- Preserve existing keyboard shortcuts, undo/redo behavior and responsive layout patterns.

## 8. Testing strategy

Add pytest tests for backend/audio/render logic and the existing frontend test/e2e approach for UI behavior:

- Import tests: valid manifest, missing manifest, checksum mismatch, bad codecs, path traversal, oversized archives and atomic rollback.
- Timing tests: loop phase, non-integer loop/song duration, seek/pause/resume, beat offsets and lyric/animation synchronization.
- Renderer tests: imported loop, still fallback, optional section pictures, all three presentation modes, overlay safe areas and single audio mux.
- Quality tests: song duration, audio stream count, frame rate, color tags, decode errors, black/frozen frames, loop seam and outdated source metadata.
- Regression tests: existing lyric video render, existing animated cover, old song folders without import metadata and thumbnail generation.
- UI e2e: import a fake valid package, preview, scrub, select mode, preflight, render draft and read the quality report.

Use short deterministic fixtures and fake animation loops in ordinary CI. Full-song and GPU-heavy tests should be opt-in local tests.

## 9. Non-goals and guardrails

- Do not merge the two Git repositories or create a runtime dependency on Anim Studio.
- Do not rewrite the existing lyric renderer from scratch.
- Do not add a second audio-analysis pipeline where CR Content already has usable BPM, beat and lyric data.
- Do not allow an animation MP4's audio to be mixed into the final song by default.
- Do not force per-section still pictures or constant camera moves on top of the consistent animated scene.
- Do not assume every imported clip is 12 seconds; use validated manifest/probe values.
- Do not let a failed import/render destroy the last successful loop or video.
- Do not mark subjective visual quality as passed when the automated inspector cannot reliably judge it.

## 10. Recommended implementation order

1. M11 minimal silent-MP4 + manifest import, with media validation and rollback.
2. M12 music-analysis handoff file for Anim Studio.
3. M13 dedicated Music Video Studio UI and the three composition modes.
4. M14 restrained beat/section-reactive controls.
5. M15 full render/audio mux/quality-inspector integration.
6. Follow-up: import the full portable editable scene package and retain source-project version history.

Finish each milestone separately with backend tests, UI tests, a sample rendered video, a changed-files summary and known limitations. Keep current Short mode and lyric mode working throughout.

## 11. Definition of production-ready

A music video is production-ready when the imported animation is validated and visually stable, the full song and lyrics remain synchronized, music-reactive effects are controlled, typography and branding respect safe areas, audio is muxed once at the intended duration, the render decodes cleanly, and the quality report clearly exposes any unresolved warnings.

**Related plan:** docs/ANIM-STUDIO-PRODUCTION-QUALITY-ROADMAP.md in the Anim Studio repository defines the animation authoring, rigging and export side of this contract.
