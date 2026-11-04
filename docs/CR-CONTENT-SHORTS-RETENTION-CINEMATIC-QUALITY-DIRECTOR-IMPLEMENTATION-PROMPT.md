# CR Content — Shorts Retention & Cinematic Quality Director

## Implementation milestone

**Milestone name:** Shorts Retention & Cinematic Quality Director  
**Target area:** Short mode only  
**Primary goal:** Turn the existing AI Director and Video Quality Inspector into one practical, explainable review workflow that helps a creator improve a Short before export and verifies the exported MP4 afterward.

---

## 1. Context and product direction

CR Content is a script-to-video production tool. The creator's desired workflow is simple:

1. Paste a finished script.
2. Let CR Content plan the story and visuals.
3. Review or adjust the generated scenes.
4. Preview and render the video.
5. Inspect the final MP4 before uploading.

The product should behave like an AI-assisted video editor and documentary-style creative director, not merely a clip assembler.

The current repository already contains relevant foundations, including the AI Director / shot-planning experience, storyboard and scene editing, live preview, timeline, captions, voiceover/music controls, and the `crcontent/quality.py` quality-analysis area. Extend those foundations. Do not build a second video-generation pipeline or a disconnected inspector application.

### Existing architecture areas to inspect first

Before changing code, inspect the current `main` branch and trace the real implementation, including (but not limited to):

- `crcontent/quality.py` — current rendered-video inspection and report model.
- `crcontent/captions.py` and `crcontent/styles.py` — caption generation and positioning.
- `frontend/components/LivePreview.tsx` — rendered-like live preview behavior.
- `frontend/app/page.tsx` — main frontend state and workflow.
- `frontend/components/` — current AI Director, storyboard, scene cards, preview, timeline, and inspector components. Discover their actual current names; do not assume names from this prompt.
- `frontend/lib/api.ts` — API client and shared types.
- Existing FastAPI routes, draft persistence, render jobs, tests, and quality-report consumers.

The paths above are discovery starting points, not permission to duplicate logic. Follow the repository's current patterns and actual names if they have changed.

### Scope constraints

- Implement this milestone for **Short mode**.
- Preserve the current Lyric mode behavior. Add regression tests where shared code is touched.
- Do not expand Campaign, topic-generation, script-paste, Excel-plan, or music-video workflows as part of this milestone. Keep unrelated product areas untouched.
- Preserve the current script wording unless the creator explicitly accepts a suggested rewrite.
- Keep the application local-first. Reuse existing configured AI/provider integrations. Do not add a required paid API, cloud service, or new account requirement.
- Keep current draft, render, storage, and export formats backward compatible.

---

## 2. Product outcome

Add a single **Retention & Quality** review experience to the existing Short editor.

It has two connected passes:

### Pass A — Pre-render Editorial Inspection

Analyze the script, narration timing, scene plan, selected footage metadata, overlays, and timeline before the video is rendered.

Answer these questions:

- Does the opening create a clear reason to keep watching?
- Does the script establish a question, mystery, promise, or interesting behavior?
- Does every scene contribute a new story beat?
- Does the selected visual support the narration at that moment?
- Is the shot sequence visually varied without feeling random?
- Are there sections with excessive repetition, weak pacing, or dead time?
- Does the video deliver the promised payoff?
- Does the ending feel complete or connect naturally to the opening?
- Are captions, headlines, and overlays likely to be readable and safely positioned?

### Pass B — Post-render Media Inspection

Analyze the actual exported MP4, not just the draft metadata.

Check:

- Resolution, aspect ratio, frame rate, duration, codec, and audio stream.
- Black frames, frozen/repeated frames, severe corruption, and unexpected blank sections.
- Audio silence, clipping/peaks, and missing or unexpectedly short audio.
- Caption placement, clipping, and timing where measurable.
- Visual continuity and subject framing where supported by available analysis.
- Whether the export corresponds to the latest reviewed draft/render settings.

Keep technical inspection in the existing quality subsystem. Connect its results to the same review experience.

---

## 3. Inspection principles — critical

1. **Evidence before score.** Every finding must show the reason, affected time range or scene, severity, and a suggested fix.
2. **No fake virality prediction.** Do not claim a Short will go viral or assign a misleading probability of reaching a particular view count.
3. **No unsupported visual claims.** A search query, filename, or AI-generated shot description is not proof that the downloaded clip shows the requested action.
4. **Separate verified from inferred.** Label checks as `verified`, `inferred`, `not_checked`, or `not_supported` where applicable. Show confidence only when the underlying method provides a meaningful confidence value.
5. **No automatic destructive edits.** Recommendations must not silently rewrite narration, replace footage, reorder scenes, or change timing. The creator chooses whether to apply a proposed fix.
6. **Warnings are not blockers by default.** The creator can proceed after reviewing warnings. Block export only for genuine technical failures already treated as blocking by the existing app.
7. **Explainability.** Avoid vague findings such as “bad pacing.” Say what is happening, where, why it may hurt comprehension or attention, and what to try.
8. **No arbitrary rules presented as universal.** Timing thresholds should be configurable and treated as heuristics, not platform rules.
9. **Respect story intent.** Do not force a cut every two seconds, constant zooms, sound effects, or transitions. Stillness can be intentional.
10. **Graceful degradation.** If an optional AI/vision provider is unavailable, the core deterministic inspection must still work and clearly mark the missing checks.

---

## 4. Pre-render inspection requirements

Create or extend a backend service that consumes the existing normalized draft/storyboard representation. Do not create a second representation of the project.

### 4.1 Story structure

Inspect and report:

- **Hook:** Is the first line/shot understandable and attention-worthy without requiring context that arrives later?
- **Premise:** Can a viewer understand what the Short is about?
- **Curiosity gap:** Is there a question, contrast, mystery, surprising behavior, or promised explanation?
- **Progression:** Does each beat move the story forward?
- **Payoff:** Does the script actually answer or fulfill the opening promise?
- **Ending:** Is the last beat satisfying, memorable, or intentionally loopable?

For the usual wildlife/nature Short, suggest—but do not require—this flexible pattern:

- Opening hook / strongest relevant image.
- Set up the behavior or mystery.
- Show evidence or behavior.
- Explain why it happens.
- Deliver the surprising fact or payoff.
- End with a concise conclusion or natural loop.

Do not force this structure on every subject or every script.

### 4.2 Timing and pacing

Use actual word timings / voiceover duration when available. Otherwise, use estimates and label them as estimates.

Detect:

- Long opening setup before the first meaningful visual or information payoff.
- Scene duration that appears disproportionate to its narration or story purpose.
- Long silence or dead air, excluding intentional pauses that have been marked as intentional.
- Repeated narration or repeated information.
- Multiple consecutive scenes with the same visual composition or role.
- A payoff that arrives too late relative to the promise made in the hook.
- An ending that cuts off a sentence or idea.

Default duration profile should suit the creator's common 25–35 second Shorts, but it must support other durations. Treat the profile as a configurable recommendation, never a hard limit.

### 4.3 Visual-to-narration relevance

For each scene, compare the narration's meaning with the selected asset and the shot instruction.

Use the strongest available evidence in this order:

1. Existing visual-analysis / vision capability already configured in the project.
2. Actual sampled frames from the selected asset, analyzed by an already-supported model/provider.
3. Asset metadata and scene/footage labels as weak evidence only.

Do not add a mandatory paid vision API. If only metadata is available, say **“Visual match not verified”** rather than reporting a match as fact.

Each scene finding should include:

- Narration excerpt or beat summary.
- Intended subject/action.
- Selected asset / source identifier.
- Shot role (establishing, close-up, action, behavior evidence, reaction, payoff, cutaway, etc.).
- Match status and evidence source.
- A better search query or replacement direction when the match is weak.

For wildlife content, recognize the difference between a species being present and the requested behavior actually being visible. For example, a standing falcon is not evidence of a falcon diving.

### 4.4 Cinematic shot variety

Evaluate the sequence, not each shot in isolation.

Use normalized shot labels when available:

- Extreme close-up / close-up / medium / wide / aerial / macro.
- Static / pan / tilt / tracking / handheld / slow motion / speed ramp.
- Establishing / behavior / action / reaction / evidence / transition / payoff.

Flag only patterns that are genuinely repetitive or confusing. Recommend a specific alternative where helpful, such as “replace the third consecutive close-up with a wide habitat shot” or “show the animal performing the behavior during this line.”

Never add camera movement or effects simply to increase the effects count.

### 4.5 Captions and overlays

Use the existing caption and style models. Inspect:

- Text outside the safe frame or clipped by the canvas.
- Captions overlapping important subjects where subject-location data exists.
- Headline and caption collisions.
- Excessive words per caption segment or unreadable duration, using configurable heuristics.
- Inconsistent font, size, outline, color, or placement.
- On-screen text that duplicates the narration without adding emphasis.

Do not rewrite caption rendering in a new subsystem. Reuse the existing rendering and positioning logic.

---

## 5. Post-render inspection requirements

Extend `crcontent/quality.py` or the actual existing quality module. Reuse its current FFmpeg/FFprobe implementation and report conventions.

### 5.1 Technical checks

At minimum, return structured results for:

- File readable / decode succeeds.
- Video stream exists.
- Audio stream exists when expected by the draft.
- Width, height, aspect ratio, FPS, duration, video codec, audio codec, and sample rate.
- Expected vertical format (normally 9:16) and target resolution.
- Black-frame intervals, with timestamps and duration.
- Freeze/repeated-frame intervals, with timestamps and duration.
- Unexpected long silent intervals, accounting for voice/music expectations.
- Audio peaks/clipping where measurable.
- Decode errors and incomplete/corrupt output.

Use tolerances. Do not flag ordinary low-motion wildlife footage as frozen merely because the subject is still. Compare changes across frames and use duration thresholds.

### 5.2 Visual checks

Where feasible with existing dependencies, sample frames from the actual render and evaluate:

- Unexpected letterboxing, pillarboxing, or subject cropped out.
- Caption/headline clipping and safe-area violations.
- Large unintended blank regions.
- Unplanned abrupt visual changes.
- Actual visual diversity across adjacent scenes.

If a check cannot be reliably measured, show `not_checked` / `not_supported`; do not turn it into a pass.

### 5.3 Caption timing checks

Where caption timing or subtitle assets are available, compare them with the rendered timeline:

- Caption starts before or after the corresponding spoken word by an excessive amount.
- Caption ends too early or remains long after speech.
- Caption overlaps another overlay.
- Caption text is clipped or outside the safe area.

If direct OCR is not part of the existing stack, do not introduce a heavy OCR dependency just for a superficial pass. First use known caption render coordinates, subtitle timing, and deterministic geometry checks.

### 5.4 Draft/render consistency

Store enough metadata to identify:

- Draft ID and draft revision/hash used for the render.
- Render ID / output file identity.
- Inspector version.
- Inspection timestamp.
- Settings relevant to the output.

If the draft changes after rendering, mark the previous report as belonging to an older revision. Do not imply the old MP4 passed inspection for the new draft.

---

## 6. Findings and scoring model

Provide an overall status and category summaries, but do not collapse the whole report into one unexplained number.

Suggested categories:

- Story & hook.
- Pacing & progression.
- Visual relevance.
- Cinematic variety.
- Captions & composition.
- Audio & sound.
- Export / technical integrity.

Each finding should have a stable machine-readable shape similar to:

```json
{
  "id": "stable-rule-or-finding-id",
  "category": "pacing",
  "severity": "info | warning | error",
  "status": "verified | inferred | not_checked | not_supported",
  "title": "Opening takes too long to reach the main behavior",
  "message": "The first clear behavior appears at 5.8 seconds, after 3.9 seconds of setup.",
  "evidence": {
    "scene_ids": ["scene-2"],
    "start_seconds": 0.0,
    "end_seconds": 5.8,
    "method": "voice_timing_and_scene_plan"
  },
  "recommendation": "Try opening on the behavior, then explain what viewers just saw.",
  "confidence": null,
  "fix_actions": []
}
```

Adapt names and conventions to the existing API. This example is a concept, not a requirement to copy the shape exactly.

Requirements:

- Stable IDs so the UI can track, dismiss, and deep-link findings.
- Severity and status must be separate fields.
- Findings must include timestamps or scene references when applicable.
- Recommendations must be actionable and concise.
- Include `fix_actions` only when a safe, concrete, reversible editor action exists.
- Do not award a “viral score.” If a category score is shown, document its formula and label it as an editorial heuristic.
- Prefer statuses such as `Ready`, `Review recommended`, and `Technical issue found` over false claims like “Guaranteed viral” or “Perfect.”

---

## 7. Frontend experience

Integrate a **Retention & Quality** panel into the existing Short editor. Respect the current UI architecture and design system; do not redesign the whole application in this milestone.

### Main panel

Show:

- Overall review status.
- Last inspection time and the draft/render revision inspected.
- Category summaries.
- Number of errors, warnings, and informational suggestions.
- A clear distinction between pre-render editorial review and post-render technical review.
- Re-run inspection action.

### Findings list

Each finding card should show:

- Severity icon/label.
- Short title.
- Why it matters.
- Exact affected scene and/or timestamp.
- Evidence status (`verified`, `inferred`, `not_checked`, `not_supported`).
- Recommended action.
- Relevant action: **Jump to scene**, **Jump to timestamp**, **Preview section**, or **Apply suggestion** when safe.

### Timeline and preview integration

- Selecting a finding moves the existing preview playhead to its start timestamp or opens its scene.
- Mark affected timeline ranges without replacing the user's current selection unexpectedly.
- Keep all edits in the existing undo/redo system.
- A proposed fix must be previewable before it is applied.
- Do not autoplay audio unexpectedly.

### Actions

Provide:

- `Inspect storyboard` — runs pre-render checks.
- `Inspect rendered video` — runs post-render checks on the selected output.
- `Re-run inspection` — refreshes the relevant report.
- `Apply suggestion` — only for safe, explicit, reversible actions.
- `Dismiss` — hides a finding for the current report, but does not delete evidence or alter the project.

Keep the default workflow understandable for a creator who only wants to paste a script and make a video. Advanced evidence and technical details may be collapsible.

### Loading and failure states

- Show progress and the active inspection stage.
- Handle missing FFmpeg, unavailable AI provider, missing assets, and interrupted renders gracefully.
- Never leave a perpetual spinner after failure.
- Keep existing editor functionality usable if inspection fails.

---

## 8. API and persistence

Follow the repository's existing API route and Pydantic/type conventions.

Add or extend endpoints for:

- Pre-render storyboard inspection.
- Post-render file inspection.
- Fetching the latest report for a draft/render.
- Optional dismissal state if the app has a persistence pattern for it.

Do not invent a parallel draft store. Reuse the current storage location and data-access helpers.

Persistence requirements:

- Version report schemas.
- Backward-compatible defaults for existing drafts and render metadata.
- Never write inspection output into the original script text.
- Store reports separately from user-authored script/story content, or in an established metadata location.
- Do not persist temporary frame images indefinitely. Use existing cache cleanup / retention conventions.
- Avoid storing secrets, API keys, or unnecessary personal data in reports.

---

## 9. AI usage and local-first behavior

- First inspect the providers and model abstractions already in the repository.
- Reuse the current configured provider for semantic story review if available.
- Do not introduce a second mandatory AI provider.
- Deterministic checks must work with no AI key.
- AI output must be validated against the draft's real scene IDs, timeline, narration, and available assets before being shown.
- Ask the model for structured output and validate it with the existing schema system (or Pydantic/Zod patterns already used).
- Reject or safely discard malformed, invented, or out-of-range scene IDs and timestamps.
- Clearly label semantic AI suggestions as editorial recommendations, not objective facts.
- Avoid sending source footage or user content to an external provider unless that provider is already configured and the current product flow makes that behavior clear.

---

## 10. Testing requirements

Add tests in the existing test structure. Do not rely only on a manual checklist.

### Backend unit tests

Cover at least:

1. A strong short script with clear hook, progression, payoff, and concise ending.
2. A weak hook with a long setup.
3. Repeated facts / duplicate story beats.
4. A payoff that never answers the opening promise.
5. A scene with a narration/visual mismatch.
6. A scene with missing footage or missing visual metadata.
7. Consecutive repeated shot types.
8. Long intentional still shot that should not automatically fail.
9. Caption outside the frame.
10. Captions overlapping the headline.
11. Missing optional AI provider — deterministic inspection still succeeds.
12. Malformed AI response / invalid scene ID — safely handled.
13. Old draft with no inspection metadata — loads without migration failure.
14. Draft revision changes after report creation — report becomes stale.

### Rendered-media tests

Use small generated fixture videos where possible. Test:

- Valid 1080x1920 clip with audio.
- Wrong aspect ratio / resolution.
- Black frame interval.
- Frozen frame interval.
- Missing audio when audio is expected.
- Long silence.
- Clipping / decode error fixture where practical.
- Very short file / invalid file.

Tests must not depend on paid APIs or internet access. Skip FFmpeg-dependent tests with a clear reason only when FFmpeg is genuinely unavailable in the test environment.

### Frontend tests

Cover:

- Empty report state.
- Loading state.
- Findings grouped by category/severity.
- Evidence status displayed correctly.
- Jump-to-scene and jump-to-time behavior.
- Dismiss finding behavior.
- Apply suggestion updates the existing editor state and undo history.
- Stale report warning after draft changes.
- Error state does not break the editor.

### Regression checks

- Existing Short generation, preview, timeline, captions, editing, undo/redo, render, and download flows still work.
- Lyric mode generation, preview, captions/lyrics, and render remain unchanged.
- Existing quality-inspector behavior and API response consumers remain compatible.

---

## 11. Suggested implementation phases

Implement in small, reviewable phases. Do not stop after adding a UI shell.

### Phase 0 — Repository audit

- Trace the existing AI Director, quality inspector, draft schema, preview timeline, render flow, and tests.
- Identify current incomplete checks and any existing retention-related logic.
- Write a short implementation map in the PR description or a temporary development note.
- Do not duplicate or rename existing systems merely to fit this prompt.

### Phase 1 — Shared finding model and deterministic analysis

- Define typed finding/report models.
- Implement deterministic story, pacing, framing, caption geometry, and technical checks using existing data.
- Add unit tests for the report model and rule functions.

### Phase 2 — AI Director integration

- Add semantic story review and per-scene visual relevance recommendations.
- Validate all model output against actual draft content.
- Add verified/inferred/not-checked states.
- Add tests using mocked provider responses.

### Phase 3 — Editor UI integration

- Add the Retention & Quality panel.
- Connect findings to scene cards, transcript, preview, and timeline.
- Add dismiss/apply-suggestion behavior with undo/redo integration.

### Phase 4 — Post-render inspection

- Extend the existing quality analyzer.
- Add timestamped findings and render/draft revision consistency.
- Connect post-render reports to the same UI.

### Phase 5 — Hardening and documentation

- Run focused tests, full tests, lint, type checks, and build.
- Fix regressions rather than weakening tests.
- Update README / feature docs only where needed.
- Document limitations and which inspections require optional AI/vision support.

---

## 12. Definition of done

This milestone is complete only when all of the following are true:

- [ ] A user can paste a script and use the existing Short workflow without learning a new complicated process.
- [ ] The existing AI Director can produce a story/shot plan and the new inspector can review that real plan.
- [ ] Pre-render inspection detects weak opening, pacing/story progression issues, missing payoff, repeated visual roles, and caption geometry issues where the data supports detection.
- [ ] Every finding includes a reason, evidence status, location, and actionable recommendation.
- [ ] Visual relevance is never represented as verified when only a search query or filename was checked.
- [ ] The creator can jump from a finding to its scene/timestamp in the existing preview/timeline.
- [ ] Safe fixes are reversible and participate in the existing undo/redo system.
- [ ] Post-render inspection analyzes the actual exported MP4.
- [ ] Technical findings include timestamps where applicable.
- [ ] Reports are associated with the correct draft revision and rendered file.
- [ ] Missing optional AI services do not break deterministic inspection or normal video creation.
- [ ] Existing Short mode workflows continue to work.
- [ ] Lyric mode behavior remains unchanged and regression-tested.
- [ ] Tests, lint, type checks, and build pass (or any pre-existing unrelated failure is clearly documented with evidence).
- [ ] Documentation accurately describes what is checked, what is inferred, and what is not yet supported.

---

## 13. Non-goals

Do not implement these in this milestone:

- A promise or prediction of views, virality, or monetization.
- Auto-uploading or publishing to YouTube.
- Automatic rewriting of every script.
- Automatic replacement of footage without creator approval.
- A new video editor, timeline engine, or rendering engine.
- A new required cloud AI subscription.
- A full redesign of the entire CR Content UI.
- Changes to Lyric mode features or music-video generation.
- A new analytics system based on YouTube channel performance.

---

## 14. Required final implementation report

When implementation is finished, provide:

1. Summary of what changed.
2. Exact files added and modified.
3. How the pre-render and post-render inspections work.
4. Screenshots or a short screen recording of the integrated inspector, if available.
5. Tests run and their actual results.
6. Any checks still marked `not_supported` and why.
7. Known limitations and recommended next milestone.

Do not claim the milestone is complete if only the UI, prompt, or data model was added without working analysis and tests.
