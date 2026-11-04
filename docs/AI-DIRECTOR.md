# CR Content Studio — AI Director & Script-to-Cinematic Video Implementation Prompt

**Target repository:** https://github.com/sokphaladam/cr-content

**Project objective:** Transform CR Content Studio into an AI-powered cinematic video production tool. The creator pastes a finished script, chooses YouTube Shorts or Long Video, and the application automatically directs, plans, assembles, edits, and renders a professional-looking video.

**Primary product principle:**

> I provide the script. The AI acts as the director, cinematographer, editor, and post-production assistant. I should not have to manually build every scene or assemble the video myself.

---

# 1. Your role

Act as a senior video-production software architect, AI video engineer, cinematic film director, FFmpeg specialist, Python engineer, Next.js/TypeScript engineer, and QA engineer.

Work directly inside the existing `cr-content` repository.

Your responsibility is to inspect the actual code, design the implementation around the existing architecture, implement the functionality, run tests, and verify the complete production workflow.

**Do not only write a proposal, roadmap, or documentation. Implement working software.**

Do not assume file paths, APIs, schemas, or architecture from this prompt. Inspect the current source code first.

# 2. Main product vision

The main application should have one simple creation workflow:

```text
                 PASTE FINISHED SCRIPT
                          |
                          v
                  SELECT VIDEO FORMAT
                          |
                +---------+---------+
                |                   |
                v                   v
            YOUTUBE SHORT       LONG VIDEO
                |                   |
                +---------+---------+
                          |
                          v
                   AI DIRECTOR
                          |
             Understand the complete story
                          |
             Analyze narration and pacing
                          |
               Create cinematic shot plan
                          |
                Generate visual searches
                          |
                Find and evaluate footage
                          |
                Plan audio and transitions
                          |
                          v
                  BUILD STORYBOARD
                          |
                 CREATE VOICEOVER
                          |
                 ASSEMBLE TIMELINE
                          |
                   LIVE PREVIEW
                          |
                 AUTOMATIC RENDER
                          |
                   QUALITY INSPECTION
                          |
                   FINAL VIDEO
```

The desired experience is simple:

1. Open CR Content Studio.
2. Paste a finished script.
3. Choose Shorts or Long Video.
4. Choose language, visual style, narration voice, and optional music.
5. Click **Create Video**.
6. AI Director plans the production and assembles the video.
7. Preview, make optional corrections, and render.
8. Inspect the final video and prepare it for YouTube.

Do not make users choose technical editing details before production begins.

# 3. Product structure

Consolidate the main video creation experience into these two primary workflows:

## A. Script to Video

This is the main product and primary entry point.

It must support:

- YouTube Shorts (9:16).
- YouTube Long Videos (16:9).
- English and Khmer.
- Finished scripts supplied by the user.
- Cinematic documentary, wildlife, educational, storytelling, and other configurable visual styles.

The user should be able to paste an entire script without manually splitting every paragraph into scenes.

The AI Director must understand the script and create the scenes, shots, footage requirements, editing decisions, and timing.

## B. Lyric Studio

Keep Lyric Studio as a separate workflow.

Do not break or replace the existing song creation, lyric synchronization, animated cover, or music-video functionality.

## Simplify the main navigation

The main creation experience should not be fragmented into multiple unrelated entry points.

Use one primary **Create Video** experience with the Shorts/Long Video selection.

Audit the existing navigation and remove or consolidate obsolete entry points where appropriate. Do not delete working backend modules, data, or features merely to simplify the interface.

Keep legacy workflows compatible during migration.

# 4. First task: inspect and understand the repository

Before changing code, inspect:

- `README.md`
- `package.json`
- `frontend/package.json`
- `requirements.txt`
- `crcontent/`
- `crcontent/longform/`
- `crcontent/shorts/`
- `frontend/app/`
- `frontend/components/`
- `frontend/lib/`
- `web/`
- `src-tauri/`
- `tests/`
- `make.py`
- Existing API routes, settings, storage, render jobs, and project schemas.

The repository currently documents a Next.js/TypeScript frontend, a Python engine/API, and a Tauri desktop application. Revalidate this architecture against the actual code.

Investigate the existing:

1. Script import and parsing system.
2. Shorts production pipeline.
3. Long-form script-to-video pipeline.
4. Gemini/LLM integration.
5. Footage search and evaluation.
6. Voiceover generation and timing.
7. Storyboard and approval workflow.
8. FFmpeg rendering system.
9. Preview and timeline editor.
10. Video Quality Inspector.
11. Storage and project persistence.
12. Job progress, cancellation, and error recovery.

Produce a concise architecture audit and file-by-file implementation plan.

**Important:** Reuse existing functionality whenever possible. Do not create another renderer, another footage downloader, another voice generator, or another project-storage system if an existing implementation can be extended.

# 5. Build the AI Director Engine

This is the most important feature.

The existing approach of turning a scene's visual description into stock-footage search keywords is not sufficient.

The AI Director must think like a real documentary filmmaker.

It must understand:

- What is happening in the story?
- What does the viewer need to understand?
- What should the viewer feel?
- What is the most important visual moment?
- What should the camera show?
- What shot should come next?
- Why should the viewer continue watching?
- How should the scene transition into the next scene?

A scene is not simply a paragraph with one stock-video search term.

A scene may require several shots with different purposes.

## 5.1 Script understanding

Analyze the complete script before producing visual instructions.

Extract:

- Main subject.
- Main story and central idea.
- Audience expectations.
- Narrative structure.
- Important facts and claims.
- Emotional progression.
- Important actions.
- Key visual moments.
- Hook and payoff.
- Scene relationships.
- Ending.

Do not rewrite or change the user's narration without permission.

By default, preserve the supplied voiceover word for word.

The director can recommend improvements, but script changes must remain optional.

## 5.2 Narrative beat planning

Divide the script into meaningful narrative beats.

Each beat should have:

- Purpose.
- Narration text.
- Viewer information or emotional objective.
- Main subject.
- Visual action.
- Required footage.
- Shot sequence.
- Target duration.
- Transition into the next beat.

Avoid dividing the script into arbitrary equal-length scenes.

Breaks should follow narrative meaning and actual narration timing.

## 5.3 Cinematic shot planning

Every shot should have a clear visual purpose.

Support the following shot types:

| Shot                     | Purpose                                 |
| ------------------------ | --------------------------------------- |
| Extreme wide             | Establish the environment               |
| Wide                     | Show the subject and surroundings       |
| Medium                   | Show the subject's behavior             |
| Close-up                 | Reveal important details                |
| Extreme close-up / Macro | Show eyes, textures, small movements    |
| Tracking                 | Follow movement                         |
| Establishing             | Introduce a new location                |
| Reaction                 | Show a meaningful response              |
| Cutaway                  | Add supporting visual evidence          |
| Montage                  | Compress time or show multiple examples |
| Graphic                  | Explain information visually            |

Camera movement options:

- Static.
- Slow push-in.
- Pull-out.
- Pan left/right.
- Tilt up/down.
- Tracking.
- Aerial movement.
- Handheld.
- Slow-motion when source material supports it.

Camera instructions must be practical.

For example, do not tell FFmpeg to perform a physical tracking shot on a static photograph. Use a suitable moving clip or an explicitly supported animation technique.

## 5.4 Cinematography decisions

For each shot, plan:

- Framing.
- Subject placement.
- Camera angle.
- Camera movement.
- Depth and perspective.
- Lighting direction.
- Lighting mood.
- Foreground/background relationship.
- Colour treatment.
- Visual emphasis.
- Desired transition.

Avoid generating generic descriptions filled with words such as "cinematic", "beautiful", "masterpiece", or "8K".

Specify what the viewer should actually see.

## 5.5 Continuity management

Create a continuity record for each project.

Maintain consistency in:

- Species or character identity.
- Location.
- Time of day.
- Environment.
- Lighting.
- Colour treatment.
- Subject appearance.
- Action progression.
- Direction of movement.

Do not use visually unrelated footage merely because it contains a similar keyword.

# 6. Wildlife documentary visual intelligence

Wildlife documentary production is a major target use case.

The director must distinguish between:

- Correct species.
- Correct animal.
- Correct behavior.
- Correct action.
- General habitat footage.
- Supporting scientific or explanatory footage.
- Illustrative or metaphorical footage.

**Factual accuracy is more important than visual attractiveness.**

For example, if the narration says:

"A raven bends a wire into a hook to retrieve food."

The visual plan should prefer:

1. A wide shot establishing the raven.
2. A close-up of the wire.
3. A close-up of the raven manipulating the wire.
4. A clear shot of the food retrieval.
5. A reaction or result shot.

Do not substitute generic footage of a crow flying and pretend it shows the described behavior.

If the exact action is unavailable:

- Search alternative sources.
- Try alternative queries.
- Use accurate supporting footage.
- Use an explanatory graphic where appropriate.
- Mark the missing exact action for review.

Never fabricate real animal behavior, scientific evidence, or historical footage.

The footage confidence system must distinguish an exact visual match from a general subject match.

# 7. AI Director output

Create a structured, versioned Director Plan.

Adapt the actual project schema after auditing the repository.

The following is the conceptual structure, not a requirement to duplicate existing schemas:

```json
{
  "version": 1,
  "project": {
    "title": "Example documentary",
    "format": "short",
    "aspect_ratio": "9:16",
    "language": "en",
    "visual_style": "cinematic_wildlife"
  },
  "story": {
    "hook": "Opening hook",
    "central_idea": "Main story",
    "emotional_arc": [],
    "payoff": "Final reveal"
  },
  "continuity": {
    "subjects": [],
    "locations": [],
    "lighting": [],
    "visual_style": "cinematic_wildlife"
  },
  "shots": [
    {
      "id": "shot-001",
      "scene_id": "scene-001",
      "purpose": "Establish the subject",
      "shot_type": "extreme_close_up",
      "subject": "Raven",
      "action": "Looks directly into camera",
      "visual_description": "Detailed visual description",
      "camera": {
        "angle": "eye_level",
        "movement": "slow_push_in",
        "framing": "tight"
      },
      "lighting": "Natural directional light",
      "duration_seconds": 2.0,
      "narration_reference": "Opening narration",
      "footage_queries": [],
      "sound_design": [],
      "transition_out": "hard_cut",
      "visual_priority": "high",
      "factual_requirements": [],
      "alternatives": []
    }
  ],
  "edit_plan": {
    "music_mood": "tense_documentary",
    "sound_effects": [],
    "colour_grade": "cinematic",
    "pacing": "fast"
  }
}
```

The actual schema must be validated and stored with the project.

Requirements:

- Stable scene and shot IDs.
- Schema validation.
- Versioning and migration.
- Recoverable generation.
- Editing without losing user changes.
- Compatibility with existing draft and rendering systems.

Do not use unvalidated free-form LLM output directly in the renderer.

# 8. Retention-focused storytelling

The system should be optimized for audience engagement and the opportunity to produce high-performing YouTube videos.

The goal is to make videos that people choose to watch, continue watching, and find satisfying.

A million views is an ambition, not a guaranteed technical outcome. Never represent an AI score as a prediction or guarantee of views.

## 8.1 Shorts direction

Preserve and extend the existing Shorts-specific capabilities.

Default target: approximately 22–30 seconds, with configurable duration.

The director should prioritize:

- A compelling first 1–2 seconds.
- An immediate visual action or strong image.
- A clear question, surprise, or promise.
- One focused central idea.
- Purposeful visual changes.
- Strong narration pacing.
- Early payoff.
- No unnecessary introduction.
- A satisfying ending.
- A natural loop when appropriate.

Do not add random cuts or effects simply to make the video faster.

Each shot must provide new information, emotion, or visual evidence.

Preserve existing Shorts capabilities such as hook evaluation, hook footage checks, analytics-based hook suggestions, vertical crops, word-level captions, and looping endings.

## 8.2 Long Video direction

Preserve the existing long-form pipeline and its script-to-video behavior.

Default target: the existing 8–15 minute workflow, with configurable duration.

The director should support:

- Strong cold open.
- Clear story introduction.
- Narrative development.
- Multiple story sections.
- Supporting visual evidence.
- Varied shot sizes and angles.
- Cinematic establishing shots.
- Detail shots.
- Meaningful pattern changes.
- Proper pacing.
- Strong transitions between story sections.
- Satisfying conclusion.

Avoid using the same footage for too long.

Avoid making every paragraph a separate generic stock-video scene.

Long videos need rhythm and narrative progression, not constant fast cuts.

## 8.3 Channel analytics feedback

Reuse the existing Shorts analytics integration.

Use channel performance data to inform future suggestions, such as:

- Hook format.
- Subject.
- Video duration.
- Audience retention.
- Percentage viewed.
- Successful narrative patterns.

Treat actual channel performance as evidence, not universal rules.

Do not optimize solely for clickbait or misleading hooks.

# 9. Cinematic visual production

The main objective is to make the finished video feel like a professionally edited documentary rather than a slideshow of stock clips.

## 9.1 Visual sourcing priority

Use a clear priority order:

1. User-provided footage.
2. Existing local media library.
3. Appropriate stock footage.
4. Existing approved image sources.
5. Existing scene-art capabilities where suitable.
6. Optional configured AI image/video providers.

Reuse the existing Pexels, Pixabay, Wikimedia, iNaturalist, archival, and footage-search integrations where applicable.

Do not introduce a mandatory paid generation API.

Do not silently download footage without recording its source and licence information.

## 9.2 Shot matching

For every candidate visual, evaluate:

- Subject match.
- Action match.
- Species or character match.
- Composition.
- Resolution.
- Sharpness.
- Duration.
- Motion suitability.
- Aspect ratio.
- Visual quality.
- Source and licensing information.

Use the existing AI footage evaluation where possible.

A visually beautiful clip that does not represent the narration is not a suitable replacement.

## 9.3 Visual variation

The director should plan visual variety intentionally.

Avoid:

- Repeating the same clip.
- Excessive static photographs.
- Repeating identical zoom effects.
- Reusing the same shot size continuously.
- Unnecessary transitions.
- Generic footage that contradicts the script.
- Text covering important visual subjects.

Prefer meaningful visual sequences with changes in framing, movement, perspective, and story information.

## 9.4 Motion and animation

Use actual motion footage whenever available.

For still images, use appropriate motion effects:

- Controlled Ken Burns movement.
- Parallax where supported.
- Subtle foreground/background separation.
- Atmospheric motion.
- Crop and framing animation.

Do not pretend that a basic zoom is equivalent to real character or animal animation.

Optional AI image-to-video providers may be added through a provider abstraction, but they must not become a mandatory dependency.

If a provider is unavailable, the application must continue to work using existing footage and rendering capabilities.

# 10. Professional editing and sound design

The AI Director must generate an edit plan, not just a footage list.

## Editing

Support:

- Intentional shot durations.
- Hard cuts.
- Cross dissolves.
- Match cuts where appropriate.
- Montage sequences.
- Cutaways.
- Slow motion when valid source footage exists.
- Controlled speed changes where appropriate.
- Text and graphic overlays.
- Lower thirds.
- Chapter/title cards.
- Cinematic colour treatment.
- Reframing for vertical and horizontal formats.

Transitions should serve the story.

Do not automatically apply a dissolve between every shot.

## Audio

Plan the soundscape:

- Narration.
- Background music.
- Ambient sound.
- Wildlife/environment sound.
- Specific sound effects.
- Impact sounds.
- Silence when useful.
- Audio transitions.

Preserve the existing voice generation and audio-processing infrastructure.

Narration must remain intelligible.

Automatically duck music under narration and avoid clipping.

Use measured loudness and true-peak checks in the existing quality system rather than trusting arbitrary volume settings.

Maintain source and licence records for music and sound effects.

# 11. Unified rendering architecture

Reuse the existing rendering systems:

- `crcontent/shorts/`
- `crcontent/longform/`
- Existing shared rendering and media utilities.
- Existing FFmpeg/FFprobe integration.
- Existing voiceover and caption systems.

Create a shared Director planning layer, not a second video renderer.

The Director Plan should be translated into the existing format-specific render structures.

The Shorts renderer remains responsible for vertical output and Shorts-specific behavior.

The Long Video renderer remains responsible for landscape output and long-form behavior.

Preserve existing CLI behavior unless a deliberate backward-compatible migration is necessary.

## Output targets

| Setting            | Shorts                       | Long Video                   |
| ------------------ | ---------------------------- | ---------------------------- |
| Aspect ratio       | 9:16                         | 16:9                         |
| Default resolution | 1080×1920                    | 1920×1080                    |
| Frame rate         | 30 fps                       | 30 fps                       |
| Video codec        | H.264                        | H.264                        |
| Audio              | AAC                          | AAC                          |
| Narration          | Supported                    | Supported                    |
| Captions           | Word-level where supported   | Timed captions               |
| Music ducking      | Supported                    | Supported                    |
| GPU encoding       | Existing NVENC with fallback | Existing NVENC with fallback |

These are defaults, not hard-coded restrictions.

# 12. User interface

Create a professional, simple production interface.

The main screen should prioritize script input.

## Step 1 — Create Video

Provide:

- Script text area.
- Paste script.
- Import script file.
- Video format selector: Shorts / Long Video.
- Language.
- Visual style.
- Narration voice.
- Music preference.
- Optional target duration.
- Create Video button.

Keep advanced settings collapsed by default.

## Step 2 — Director Plan

Show the AI-generated production plan.

The user should be able to:

- See scenes and shots.
- Review the intended visual sequence.
- Inspect footage searches and selected results.
- See footage confidence and warnings.
- Replace footage.
- Edit a shot description.
- Change shot order.
- Adjust durations.
- Approve or regenerate selected shots.

Do not require manual review of every technical detail before continuing.

## Step 3 — Production

Display meaningful progress:

- Script analysis.
- Director planning.
- Voice generation.
- Footage search.
- Footage evaluation.
- Timeline assembly.
- Preview preparation.
- Rendering.

Show which stage is currently running.

Support cancellation and recovery where practical.

Do not freeze the UI while generating large videos.

## Step 4 — Preview and edit

Reuse the existing live preview, storyboard, timeline, and editor components.

The user should be able to:

- Play the entire video.
- Scrub the timeline.
- Edit narration.
- Replace footage.
- Change shot durations.
- Adjust captions.
- Change music.
- Edit text overlays.
- Reorder shots.
- Regenerate selected shots.

Preview and final render must use the same project plan and settings.

## Step 5 — Render and inspect

After rendering:

1. Offer final render inspection.
2. Show the actual rendered video.
3. Show timestamped quality issues.
4. Allow the user to return to the relevant scene.
5. Allow re-rendering and re-inspection.
6. Show upload metadata and licensing information.

Reuse the existing Video Quality Inspector. Do not create a duplicate inspector.

# 13. Backend and API integration

Inspect existing FastAPI routes and frontend API conventions before designing new endpoints.

Add the minimum necessary endpoints for:

- Creating a Director Plan.
- Retrieving a Director Plan.
- Updating a Director Plan.
- Regenerating selected shots.
- Approving a production plan.
- Starting a video production job.
- Reading job progress.
- Cancelling a job.
- Recovering an interrupted job.

Use the existing job and persistence architecture if it supports these needs.

Define typed request and response models.

Requirements:

- Validate all inputs.
- Validate all AI-generated plans.
- Use stable project/job identifiers.
- Persist intermediate results.
- Support cancellation.
- Avoid duplicate jobs from repeated clicks.
- Return useful error messages.
- Keep API calls bounded with appropriate timeouts.
- Never expose API keys to the frontend.

Do not add new endpoints unnecessarily if equivalent functionality already exists.

# 14. Cost, reliability, and provider strategy

Keep the application usable with its current low-cost/default production services.

Reuse:

- Existing Gemini integration.
- Existing Edge TTS option.
- Existing footage sources.
- Existing FFmpeg rendering.
- Existing local media and caches.

Do not require a paid AI video-generation subscription.

Make optional services configurable.

The AI Director should make efficient LLM requests:

- Analyze the script once at the project level where possible.
- Generate structured plans.
- Regenerate only the affected section when the user changes one shot.
- Cache reusable analysis and search results.
- Avoid repeated evaluation of unchanged media.

Handle missing API keys and unavailable services gracefully.

A missing optional AI service must not crash the application.

# 15. Compatibility and migration

This is an evolution of CR Content Studio, not a rewrite.

Preserve:

- Existing projects and drafts.
- Existing rendered videos.
- Existing uploaded media.
- Existing output directories.
- Existing settings.
- Existing storage locations.
- Existing Shorts functionality.
- Existing Long Video functionality.
- Existing Lyric Studio functionality.
- Existing upload integration.
- Existing Quality Inspector.
- Existing CLI commands.

Introduce schema versions and migrations where needed.

Do not delete legacy modules simply because the new interface uses a unified workflow.

Do not break installed Tauri builds or the existing Python engine packaging.

Update packaging dependencies if any new runtime dependency is introduced.

# 16. Testing and acceptance criteria

Do not consider this feature complete just because the UI loads or an AI plan is generated.

Implement unit tests, integration tests, and end-to-end tests using the repository's current testing conventions.

At minimum, verify the following.

## Test A — Wildlife Shorts

Input a completed wildlife script about a raven.

Expected:

- Correctly identifies the main subject.
- Creates an immediate opening hook.
- Creates a structured shot plan.
- Prioritizes matching footage.
- Distinguishes actual tool-use footage from generic raven footage.
- Preserves the narration.
- Produces a vertical video.
- Uses readable captions.
- Supports a suitable payoff and loop.
- Produces a final quality report.

## Test B — Wildlife Long Video

Input a completed long-form script about intelligent birds.

Expected:

- Understands the overall story.
- Divides the script into meaningful sections.
- Produces varied shot types.
- Uses suitable footage for each section.
- Maintains visual continuity.
- Generates narration and timing.
- Creates a reviewable storyboard.
- Produces a landscape video.
- Generates captions, chapters, description, and credits where supported.
- Runs the final inspector.

## Test C — User footage

Supply local video clips and images.

Expected:

- User-provided media is considered before stock.
- Footage matching is evaluated.
- Original source files are not modified.
- Media paths remain valid.
- Rendering can use the selected media.

## Test D — Missing services

Run without optional Gemini or external footage credentials.

Expected:

- The application explains unavailable capabilities.
- Existing fallback functionality works.
- No unhandled crash occurs.
- The user can still produce a video using supported local assets.

## Test E — Regression

Verify:

- Existing Shorts workflow.
- Existing Long Video workflow.
- Existing Lyric Studio workflow.
- Existing preview and timeline editor.
- Existing quality inspection.
- Existing project library.
- Existing Tauri packaging.

## Test F — Build and runtime

Run applicable checks:

- Python unit tests.
- Backend integration tests.
- Frontend type checking.
- Frontend build.
- Relevant Tauri build checks where the environment supports them.
- A real test render using sample media.

Record actual results.

Never claim a build, test, or render succeeded unless it was actually run and verified.

# 17. Implementation milestones

Implement in the following order.

## Milestone 1 — Unified Script-to-Video foundation

- [x] Audit actual source code.
- [x] Create unified creation workflow.
- [x] Add Shorts/Long Video format selection.
- [x] Connect script input to both existing pipelines.
- [x] Preserve Lyric Studio separately.
- [x] Establish shared Director Plan schema.
- [x] Add plan persistence and validation.

**Deliverable:** The user can paste a script and create a valid project in either format.

## Milestone 2 — AI Director Engine

- [x] Whole-script analysis.
- [x] Narrative beat extraction.
- [x] Scene planning.
- [x] Shot planning.
- [x] Camera and composition decisions.
- [x] Visual continuity.
- [x] Structured edit plan.
- [x] Factual accuracy safeguards.

**Deliverable:** A complete, structured Director Plan based on the user's script.

## Milestone 3 — Cinematic footage intelligence

- [x] Shot-specific footage searches.
- [x] Subject and action matching.
- [x] Footage quality scoring.
- [x] Footage alternatives.
- [x] Continuity checking.
- [x] Missing-footage warnings.
- [x] User footage priority.

**Deliverable:** Suitable footage selected for each planned shot, with transparent warnings when the exact visual is unavailable.

## Milestone 4 — Cinematic editing and production

- [x] Translate Director Plan to existing render pipelines.
- [x] Integrate shot-level sequences.
- [x] Improve pacing and transitions.
- [x] Add planned audio cues. (every planned cut, in Shorts and long videos: impact, thunder or whoosh, or a rain, wind, water or birds ambience bed, all synthesized in sfx.py)
- [x] Improve shot variation and visual composition.
- [x] Keep captions synchronized.
- [x] Support preview and user corrections.

**Deliverable:** A complete cinematic video assembled automatically.

## Milestone 5 — Production reliability and quality

- [x] Progress reporting.
- [x] Cancellation and recovery.
- [x] Final render inspection.
- [x] Error handling.
- [x] Regression tests.
- [x] Packaging verification. (macOS build 2026-11-04: app and DMG built; the packaged engine renders a Short on an empty library)
- [x] Documentation updates.

**Deliverable:** A reliable production workflow that generates, previews, renders, and inspects videos.

## Progress (updated 2026-11-04)

Code for all five milestones is in, but none of it is committed yet. Work goes one small task at a time: plan it, get approval, then build it.

Done and checked:

- [x] Test A: raven Short, end to end (Gemini on): plan, footage, assemble, render, inspect.
- [x] Footage credits: every licensed photo or clip, including a Short's cutaways, is credited in post.txt.
- [x] Plain prose scripts import without Gemini (Test D, partly).
- [x] Test B: a cut-down long video, end to end. Fixed along the way: a stalled FFmpeg scene render is now stopped after a time limit and tried once more.
- [x] A long video's montage photos are credited in credits.txt and description.txt.
- [x] A card scene now also cuts to the footage the plan found for it. Before, the plan's other shots were dropped.
- [x] Test E: 341 automated tests pass.

Remaining, in the suggested order:

- [x] Sudden volume jumps: every render was flagged for its ending (the voice stopping, the fade-out). Drops into quiet (pauses, the ending) no longer count, and a sound coming back after a pause is compared with how loud it was before the pause; real bursts are still flagged.
- [x] Slow motion from the plan (9.4, 10): a slow_motion shot plays at half speed in Shorts (scene clip and cutaways) and long videos, only from a clip of 48+ fps; a slower clip plays at normal speed with a note.
- [x] Planned sound effects on long videos and on a Short's scene openers.
- [x] The plan's ambient sound notes (rain, wind, water, birds): synthesized beds, no licensed files needed.
- [x] Pre-render check, Visual: Full check samples a few frames of every media file for blur, exposure and colour cast.
- [x] Pre-render check, Rights: flags files with no licence on record and a non-commercial or no-derivatives music track.
- [x] Pre-render check, Audio: Full check measures the music track: too quiet for the render to bring up under the voice, or swinging from soft to loud (loudness range over 15 LU) so it rises over the voice. The finished mix (ducking, sound effects) is still checked only on the rendered file.
- [x] Pre-render check, Storytelling: an optional "Check footage with Gemini" button sends three frames of each scene's footage (the part shown) with its narration; a scene scoring under 7 gets a warning showing what the footage shows. Answers are cached next to the clip. Cutaways and footage picked at render aren't checked.
- [x] Create Video form (12, Step 1): narration voice and music for a Short (saved on its draft; long videos use Settings → Script Video), an optional target length (a live voiceover estimate under the script, a note when it's over 25% off, and a pacing hint for the AI Director; the narration is never cut), and Visual style, Target length and Speed under a closed "Advanced options".
- [x] Per-video voice, speed and music for long videos: chosen in the Create Video form, kept in the video's choice.json and laid over Settings → Script Video when the storyboard is made and when it renders ("No music", one track, or your tracks as before). Videos made before keep the settings. Not editable from the storyboard page yet.
- [x] Analytics feeding the AI Director (8.3): the YouTube Studio Content export (imported from the Director panel's "Your channel's numbers", .zip or .csv, or `make.py --shorts-analytics`) goes to the AI Director as evidence, not rules: hook styles, lengths and subjects with 3+ videos, stayed to watch and % viewed, with "never a misleading or clickbait hook". The plan notes when it was used ("Planned with your channel's numbers: N videos, imported ...").
- [x] Simpler main navigation (3): one "Create video" page (the Script to Video form; rail and Library buttons say Create). Shorts from a content plan (.xlsx) and the script table upload (.md) sit under a closed "Other ways to start". The unreachable topic, paste, Excel plan and music-video forms (hidden since 2 Nov) were removed from the UI; their backend endpoints, ExcelPlanForm.tsx and OutlierFinder.tsx are kept, unused.
- [x] Test C: a video made from the user's own footage (2026-11-05, stand-in clips and a photo, Gemini on). Long video: files in media/test-c-ravens/ (scene-01.mp4, scene-02.jpg) were chosen over stock by the storyboard and by the Director's shot search, rendered, credited as "your own media" and passed the Quality check (0 fail). Short: the clip and photo uploaded in the editor passed the Full pre-render check, the AI footage check judged them (scene 1 fits, scene 2 warned), and the render used them (0 fail). Originals byte-identical with unchanged timestamps; uploads are exact copies; every saved path opens. Findings: on the Director path your own files are used without a match check (match "own"; only the editor's optional footage check judges them); the 9 s long video got 3 "sudden volume" warnings at scene changes.
- [x] Test F: macOS app built; the packaged engine imports every new module and renders a Short with planned sounds on a fresh library. Fixed along the way: the engine has no numpy without the AI add-on, so the sound effects are now made at build time and bundled, and the cover's subject check no longer imports numpy before checking for the add-on. Windows (2026-11-05): 367 Python tests pass, TypeScript clean, frontend production build OK; `npm run build` made Shorts Studio_0.1.0_x64-setup.exe (120.28 MiB, 8 min 45 s, not installed). Its frozen engine.exe, run on a fresh library with only the bundled FFmpeg on PATH and no API keys: starts in 7 s; the new endpoints answer; Create video (Short) falls back to the basic reader and keeps speed, music and target; an uploaded own clip passes the Full pre-render check; the AI footage check without a key fails cleanly (502 with a message); a Short with planned impact/whoosh sounds (bundled .wav, no numpy) renders in 20 s and passes the Quality check (0 fail); no errors in engine.log. Notes: an editor (draft) Short always encodes with x264, by design (finalize's default), though the bundled FFmpeg's NVENC works; PyInstaller can't find the tzdata hidden import; ESLint reports existing errors in PreviewPane.tsx (13, refs read during render) and ShortsForm.tsx (2).

Test leftovers that can be deleted:

- the drafts 20261103-152140-7358 and 20261103-190255-6227 and their videos
- the long video output/20261103-204104-en-smartest-birds-test-cut. Its video predates the card-scene fix.
- Test C: the draft 20261105-004055-5047 (Smart Ravens) and its video output/20261105-004208-en-smart-ravens; the long video output/20261105-003808-en-test-c-ravens with scripts/test-c-ravens.md and media/test-c-ravens/; the uploads 8be8809447c2.* and 480b71faedcc.*

# 18. Definition of done

This implementation is complete only when:

1. The user can paste a finished script.
2. The user can choose Shorts or Long Video.
3. AI Director understands the story.
4. AI Director produces a structured cinematic shot plan.
5. The system searches for appropriate footage.
6. The system evaluates footage suitability.
7. The system plans narration, editing, captions, music, and sound.
8. The system assembles the production using the existing rendering infrastructure.
9. The user can preview and edit the result.
10. The system renders a working final video.
11. The final video can be inspected with the existing Quality Inspector.
12. Existing Lyric Studio and legacy project data remain functional.
13. Relevant tests and builds have actually been run and their results reported.

# 19. Critical instructions

- Do not stop after writing a plan.
- Do not only create new Markdown documentation.
- Do not replace working features with mock interfaces.
- Do not create fake AI progress.
- Do not return placeholder footage as if it were real footage.
- Do not silently rewrite user narration.
- Do not generate unsupported claims about animal behavior or scientific facts.
- Do not promise that any video will reach one million views.
- Do not add mandatory paid services.
- Do not duplicate the existing render engine.
- Do not break Shorts, Long Video, Lyric Studio, the Quality Inspector, or Tauri.
- Do not hide failures behind successful-looking UI states.

Implement the milestones in order. After each milestone, run the relevant tests and fix failures before moving forward.

When finished, provide:

1. Architecture audit.
2. Features implemented.
3. Files created and modified.
4. API and schema changes.
5. Tests executed and their actual results.
6. Build and render verification.
7. Known limitations.
8. Remaining work.

**Final product requirement:**

The main CR Content Studio experience should feel like having an AI documentary video director and editor inside the application.

My workflow should be:

**Paste script → Choose Shorts or Long Video → Create Video → Review → Render → Quality Check → Upload to YouTube.**
